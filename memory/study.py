from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from memory.json_store import read_json_file, update_json_file, write_json_atomic
from memory.reminders import parse_reminder_request
from memory.supabase_sync import sync_memory_state_safely

STUDY_PATH = Path("memory/study.json")
DEFAULT_DAILY_MINUTES = 60

DEFAULT_STATE = {
    "goals": [],
    "reviews": [],
    "sessions": [],
    "settings": {"daily_minutes": DEFAULT_DAILY_MINUTES},
}


def _now() -> datetime:
    return datetime.now()


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip(" .,:;-")


def _normalize_state(data: dict | None) -> dict:
    state = dict(DEFAULT_STATE)
    state.update(data or {})
    for key in ("goals", "reviews", "sessions"):
        if not isinstance(state.get(key), list):
            state[key] = []
    if not isinstance(state.get("settings"), dict):
        state["settings"] = dict(DEFAULT_STATE["settings"])
    settings = dict(DEFAULT_STATE["settings"])
    settings.update(state.get("settings") or {})
    try:
        settings["daily_minutes"] = max(5, int(settings.get("daily_minutes") or DEFAULT_DAILY_MINUTES))
    except Exception:
        settings["daily_minutes"] = DEFAULT_DAILY_MINUTES
    state["settings"] = settings
    return state


def load_study_state() -> dict:
    return _normalize_state(read_json_file(STUDY_PATH, {}, validator=lambda value: isinstance(value, dict)))


def save_study_state(state: dict) -> dict:
    payload = _normalize_state(state)
    write_json_atomic(STUDY_PATH, payload, indent=2, trailing_newline=True)
    sync_memory_state_safely("study", payload, category="study")
    return payload


def _update_study_state(updater) -> dict:
    payload = update_json_file(
        STUDY_PATH,
        dict(DEFAULT_STATE),
        lambda data: updater(_normalize_state(data)),
        validator=lambda value: isinstance(value, dict),
        indent=2,
        trailing_newline=True,
    )
    payload = _normalize_state(payload)
    sync_memory_state_safely("study", payload, category="study")
    return payload


def _today_key(now: datetime | None = None) -> str:
    return (now or _now()).date().isoformat()


def _parse_minutes(text: str, default: int = 25) -> int:
    match = re.search(r"\b(\d{1,3})\s*(?:min|minuto|minutos)\b", str(text or ""), flags=re.I)
    if match:
        return max(1, min(600, int(match.group(1))))
    return default


def add_study_goal(raw_text: str) -> str:
    text = _compact(re.sub(r"^(?:meta\s+de\s+estudo|adicionar\s+meta\s+de\s+estudo|nova\s+meta)\s+", "", str(raw_text or ""), flags=re.I))
    if not text:
        return "Qual meta de estudo devo registrar?"

    goal = {
        "id": str(time.time_ns()),
        "text": text,
        "created_at": _now().isoformat(timespec="seconds"),
        "done": False,
    }
    _update_study_state(lambda state: {**state, "goals": [*(state.get("goals") or []), goal]})
    return f"Meta de estudo registrada: {text}."


def add_study_review(raw_text: str) -> str:
    due_at, clean_text = parse_reminder_request(raw_text)
    text = _compact(clean_text or raw_text)
    if not text:
        return "Qual revisao devo registrar?"
    if due_at is None:
        due_at = _now() + timedelta(days=1)

    review = {
        "id": str(time.time_ns()),
        "text": text,
        "due_at": due_at.isoformat(timespec="minutes"),
        "created_at": _now().isoformat(timespec="seconds"),
        "done": False,
    }
    _update_study_state(lambda state: {**state, "reviews": [*(state.get("reviews") or []), review]})
    return f"Revisao registrada para {due_at.strftime('%d/%m %H:%M')}: {text}."


def complete_study_review(index_text: str = "1") -> str:
    try:
        index = int(str(index_text or "1").strip())
    except Exception:
        return "Qual revisao devo concluir?"

    completed = {}

    def mark_done(state: dict) -> dict:
        pending = [item for item in state.get("reviews") or [] if isinstance(item, dict) and not item.get("done")]
        pending.sort(key=lambda item: str(item.get("due_at", "")))
        if index < 1 or index > len(pending):
            return state
        target_id = pending[index - 1].get("id")
        for item in state.get("reviews") or []:
            if item.get("id") == target_id:
                item["done"] = True
                item["completed_at"] = _now().isoformat(timespec="seconds")
                completed.update(item)
                break
        return state

    _update_study_state(mark_done)
    if not completed:
        return "Nao encontrei essa revisao pendente."
    return f"Revisao concluida: {completed.get('text', 'item sem titulo')}."


def log_study_session(raw_text: str) -> str:
    text = _compact(raw_text)
    minutes = _parse_minutes(text)
    topic = re.sub(r"\b(?:estudei|registrar estudo|sessao de estudo|por)\b", " ", text, flags=re.I)
    topic = re.sub(r"\b\d{1,3}\s*(?:min|minuto|minutos)\b", " ", topic, flags=re.I)
    topic = _compact(topic) or "estudo geral"
    session = {
        "id": str(time.time_ns()),
        "topic": topic,
        "minutes": minutes,
        "date": _today_key(),
        "created_at": _now().isoformat(timespec="seconds"),
    }
    _update_study_state(lambda state: {**state, "sessions": [*(state.get("sessions") or []), session]})
    return f"Estudo registrado: {minutes} min em {topic}."


def study_snapshot(now: datetime | None = None) -> dict:
    now = now or _now()
    state = load_study_state()
    today = _today_key(now)
    sessions = [item for item in state.get("sessions") or [] if isinstance(item, dict)]
    today_minutes = sum(int(item.get("minutes") or 0) for item in sessions if item.get("date") == today)
    target = int((state.get("settings") or {}).get("daily_minutes") or DEFAULT_DAILY_MINUTES)
    pending_reviews = [item for item in state.get("reviews") or [] if isinstance(item, dict) and not item.get("done")]
    pending_reviews.sort(key=lambda item: str(item.get("due_at", "")))
    active_goals = [item for item in state.get("goals") or [] if isinstance(item, dict) and not item.get("done")]
    return {
        "today": today,
        "daily_minutes": target,
        "minutes_today": today_minutes,
        "percent": min(100, round((today_minutes / target) * 100)) if target else 0,
        "remaining_minutes": max(0, target - today_minutes),
        "goals": active_goals[:5],
        "pending_reviews": pending_reviews[:5],
        "sessions_today": [item for item in sessions if item.get("date") == today][-5:],
    }


def format_study_panel() -> str:
    snap = study_snapshot()
    goals = snap.get("goals") or []
    reviews = snap.get("pending_reviews") or []
    goal_text = goals[0].get("text") if goals else "sem meta ativa"
    review_text = reviews[0].get("text") if reviews else "sem revisao pendente"
    return (
        f"Estudos: {snap['minutes_today']}/{snap['daily_minutes']} min hoje, "
        f"{snap['percent']}% da meta. Meta principal: {goal_text}. "
        f"Proxima revisao: {review_text}."
    )
