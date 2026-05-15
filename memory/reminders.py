from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from memory.current_topic import load_current_topic
from memory.supabase_sync import sync_memory_state_safely


REMINDERS_PATH = Path("memory/reminders.json")


def _load_json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def load_reminders() -> dict:
    data = _load_json(REMINDERS_PATH)
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return {"items": items}


def save_reminders(data: dict) -> dict:
    payload = {"items": list((data or {}).get("items") or [])}
    _save_json(REMINDERS_PATH, payload)
    sync_memory_state_safely("reminders", payload, category="reminders")
    return payload


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip(" .,:;-")


def _apply_reminder_text_corrections(text: str) -> str:
    corrected = str(text or "")
    corrected = re.sub(r"\bcomar(\s+banho\b)", r"tomar\1", corrected, flags=re.I)
    corrected = re.sub(r"\bcomer(\s+banho\b)", r"tomar\1", corrected, flags=re.I)
    return _compact(corrected)


def _parse_time_fragment(text: str, base: datetime) -> tuple[int, int] | None:
    match = re.search(r"\b(?:as|às)\s*(\d{1,2})(?::|h)?(\d{2})?\b", text, flags=re.I)
    if not match:
        match = re.search(r"\b(\d{1,2})h(\d{2})?\b", text, flags=re.I)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return hour, minute
    return None


def _strip_schedule_text(text: str) -> str:
    cleaned = str(text or "")
    patterns = [
        r"\b(?:daqui a|em)\s+\d+\s+(?:minuto|minutos|hora|horas|dia|dias)\b",
        r"\b(?:hoje|amanha|amanhã)\b(?:\s+(?:as|às)?\s*\d{1,2}(?::|h)?\d{0,2})?",
        r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b(?:\s+(?:as|às)?\s*\d{1,2}(?::|h)?\d{0,2})?",
        r"\b(?:as|às)\s*\d{1,2}(?::|h)?\d{0,2}\b",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.I)
    return _compact(cleaned)


def parse_reminder_request(raw_text: str, now: datetime | None = None) -> tuple[datetime | None, str]:
    now = now or datetime.now()
    text = _compact(raw_text)
    lowered = text.lower()
    if not text:
        return None, ""

    relative = re.search(r"\b(?:daqui a|em)\s+(\d+)\s+(minuto|minutos|hora|horas|dia|dias)\b", lowered)
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        if unit.startswith("minuto"):
            due_at = now + timedelta(minutes=amount)
        elif unit.startswith("hora"):
            due_at = now + timedelta(hours=amount)
        else:
            due_at = now + timedelta(days=amount)
        return due_at.replace(second=0, microsecond=0), _strip_schedule_text(text)

    target_day = now.date()
    if re.search(r"\bamanh[ãa]\b", lowered):
        target_day = target_day + timedelta(days=1)
    elif re.search(r"\bhoje\b", lowered):
        target_day = target_day

    date_match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", lowered)
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year_raw = date_match.group(3)
        year = int(year_raw) if year_raw else now.year
        if year < 100:
            year += 2000
        try:
            target_day = datetime(year, month, day).date()
        except ValueError:
            return None, _strip_schedule_text(text)

    time_fragment = _parse_time_fragment(lowered, now)
    if time_fragment:
        hour, minute = time_fragment
        due_at = datetime.combine(target_day, datetime.min.time()).replace(hour=hour, minute=minute)
        if due_at <= now and not date_match and not re.search(r"\b(?:hoje|amanh[ãa])\b", lowered):
            due_at += timedelta(days=1)
        return due_at, _strip_schedule_text(text)

    return None, _strip_schedule_text(text)


def _format_due_at(due_at: datetime) -> str:
    now = datetime.now()
    if due_at.date() == now.date():
        return f"hoje as {due_at.strftime('%H:%M')}"
    if due_at.date() == (now + timedelta(days=1)).date():
        return f"amanha as {due_at.strftime('%H:%M')}"
    return due_at.strftime("%d/%m/%Y as %H:%M")


def _resolve_deictic_text(text: str) -> str:
    normalized = _compact(text).lower()
    if normalized not in {"isso", "disso", "disto", "sobre isso"}:
        return text

    topic = load_current_topic() or {}
    for key in ("summary", "last_user_question", "topic"):
        value = _compact(topic.get(key, ""))
        if value:
            return value
    return text


def add_reminder(raw_text: str) -> str:
    due_at, text = parse_reminder_request(raw_text)
    text = _apply_reminder_text_corrections(text)
    text = _resolve_deictic_text(text)
    if not text:
        return "O que devo lembrar?"
    if due_at is None:
        return "Quando devo lembrar isso?"

    data = load_reminders()
    items = data.get("items") or []
    reminder = {
        "id": str(time.time_ns()),
        "text": text,
        "due_at": due_at.isoformat(timespec="minutes"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notified_at": "",
    }
    items.append(reminder)
    items.sort(key=lambda item: str(item.get("due_at", "")))
    save_reminders({"items": items})
    return f"Combinado. Vou lembrar { _format_due_at(due_at) }: {text}."


def list_reminders(include_notified: bool = False, limit: int = 8) -> str:
    items = []
    for item in load_reminders().get("items") or []:
        if not include_notified and item.get("notified_at"):
            continue
        try:
            due_at = datetime.fromisoformat(str(item.get("due_at", "")))
        except Exception:
            continue
        items.append((due_at, str(item.get("text", "")).strip()))

    if not items:
        return "Nao ha lembretes pendentes."

    items.sort(key=lambda row: row[0])
    parts = [f"{index}. {_format_due_at(due_at)}: {text}" for index, (due_at, text) in enumerate(items[:limit], start=1)]
    return "Lembretes pendentes: " + " ; ".join(parts) + "."


def remove_reminder(index_text: str) -> str:
    try:
        index = int(str(index_text or "").strip())
    except Exception:
        return "Qual lembrete devo remover?"

    data = load_reminders()
    pending = [item for item in (data.get("items") or []) if not item.get("notified_at")]
    pending.sort(key=lambda item: str(item.get("due_at", "")))
    if index < 1 or index > len(pending):
        return "Nao encontrei esse lembrete."

    removed = pending[index - 1]
    removed_id = removed.get("id")
    remaining = [item for item in (data.get("items") or []) if item.get("id") != removed_id]
    save_reminders({"items": remaining})
    return f"Removi o lembrete: {removed.get('text', 'item sem titulo')}."


def consume_due_reminders(now: datetime | None = None, limit: int = 3) -> list[dict]:
    now = now or datetime.now()
    data = load_reminders()
    items = data.get("items") or []
    due = []
    changed = False

    for item in items:
        if item.get("notified_at"):
            continue
        try:
            due_at = datetime.fromisoformat(str(item.get("due_at", "")))
        except Exception:
            continue
        if due_at <= now:
            item["notified_at"] = now.isoformat(timespec="seconds")
            due.append(dict(item))
            changed = True
        if len(due) >= limit:
            break

    if changed:
        save_reminders({"items": items})
    return due
