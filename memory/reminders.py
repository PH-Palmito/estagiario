from __future__ import annotations

import re
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

from memory.current_topic import load_current_topic
from memory.json_store import read_json_file, update_json_file, write_json_atomic
from memory.supabase_sync import sync_memory_state_safely

REMINDERS_PATH = Path("memory/reminders.json")
PENDING_REMINDER_PATH = Path("memory/pending_reminder.json")


def load_reminders() -> dict:
    data = read_json_file(REMINDERS_PATH, {}, validator=lambda value: isinstance(value, dict))
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return {"items": items}


def save_reminders(data: dict) -> dict:
    payload = {"items": list((data or {}).get("items") or [])}
    write_json_atomic(REMINDERS_PATH, payload, indent=2, trailing_newline=True)
    sync_memory_state_safely("reminders", payload, category="reminders")
    return payload


def _update_reminders(updater) -> dict:
    payload = update_json_file(
        REMINDERS_PATH,
        {"items": []},
        lambda data: {"items": list((updater({"items": list((data or {}).get("items") or [])}) or {}).get("items") or [])},
        validator=lambda value: isinstance(value, dict),
        indent=2,
        trailing_newline=True,
    )
    sync_memory_state_safely("reminders", payload, category="reminders")
    return payload


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip(" .,:;-")


def _ascii_lower(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _load_pending_reminder() -> str:
    data = read_json_file(PENDING_REMINDER_PATH, {}, validator=lambda value: isinstance(value, dict))
    return _compact((data or {}).get("text", ""))


def _save_pending_reminder(text: str) -> None:
    write_json_atomic(PENDING_REMINDER_PATH, {"text": _compact(text)}, indent=2, trailing_newline=True)


def _clear_pending_reminder() -> None:
    write_json_atomic(PENDING_REMINDER_PATH, {"text": ""}, indent=2, trailing_newline=True)


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
    period_text = text[match.end(): match.end() + 24]
    if re.search(r"\b(?:da\s+tarde|da\s+noite)\b", period_text, flags=re.I) and 1 <= hour <= 11:
        hour += 12
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return hour, minute
    return None


def _strip_schedule_text(text: str) -> str:
    cleaned = str(text or "")
    patterns = [
        r"\b(?:daqui a|em)\s+\d+\s+(?:minuto|minutos|hora|horas|dia|dias)\b",
        r"\b(?:hoje|amanha|amanhã)\b(?:\s+(?:as|às)?\s*\d{1,2}(?::|h)?\d{0,2})?",
        r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b(?:\s+(?:as|às)?\s*\d{1,2}(?::|h)?\d{0,2})?",
        r"\bdia\s+\d{1,2}\b(?:\s+(?:as|às)?\s*\d{1,2}(?::|h)?\d{0,2})?",
        r"\b(?:as|às)\s*\d{1,2}(?::|h)?\d{0,2}\b",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.I)
    cleaned = re.sub(
        r"\b(?:as|às)?\s*\d{1,2}(?::|h)?\d{0,2}\s*(?:da\s+manha|da\s+manhã|da\s+tarde|da\s+noite)?\b",
        " ",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\b(?:da\s+manha|da\s+manhã|da\s+tarde|da\s+noite)\b", " ", cleaned, flags=re.I)
    return _compact(cleaned)


MONTH_NAMES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def _next_annual_datetime(day: int, month: int, now: datetime, hour: int = 9, minute: int = 0) -> datetime | None:
    try:
        candidate = datetime(now.year, month, day, hour, minute)
    except ValueError:
        return None
    if candidate <= now:
        try:
            candidate = datetime(now.year + 1, month, day, hour, minute)
        except ValueError:
            return None
    return candidate


def _strip_annual_schedule_text(text: str, start: int, end: int) -> str:
    cleaned = _compact(f"{text[:start]} {text[end:]}")
    cleaned = re.sub(r"^(?:de|do|da|dos|das|sobre)\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(?:dia\s+)?\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", " ", cleaned, flags=re.I)
    return _compact(cleaned)


def parse_reminder_details(raw_text: str, now: datetime | None = None) -> tuple[datetime | None, str, str]:
    now = now or datetime.now()
    text = _compact(raw_text)
    ascii_lowered = _ascii_lower(text)
    if not text:
        return None, "", ""

    annual_match = re.search(
        r"\b(?:todo\s+(?:ano\s+)?(?:dia\s+)?|anualmente\s+(?:no\s+dia\s+)?)"
        r"(\d{1,2})\s+de\s+"
        r"(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b",
        ascii_lowered,
        flags=re.I,
    )
    if annual_match:
        month = MONTH_NAMES.get(annual_match.group(2))
        due_at = _next_annual_datetime(int(annual_match.group(1)), int(month or 0), now) if month else None
        if due_at is None:
            return None, _strip_schedule_text(text), ""
        return due_at, _strip_annual_schedule_text(text, annual_match.start(), annual_match.end()), "yearly"

    due_at, clean_text = parse_reminder_request(raw_text, now=now)
    return due_at, clean_text, ""


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

    day_match = re.search(r"\bdia\s+(\d{1,2})\b", lowered)
    if day_match and not date_match:
        day = int(day_match.group(1))
        month = now.month
        year = now.year
        try:
            candidate = datetime(year, month, day).date()
            if candidate < now.date():
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                candidate = datetime(year, month, day).date()
            target_day = candidate
        except ValueError:
            return None, _strip_schedule_text(text)

    time_fragment = _parse_time_fragment(lowered, now)
    if time_fragment:
        hour, minute = time_fragment
        due_at = datetime.combine(target_day, datetime.min.time()).replace(hour=hour, minute=minute)
        if due_at <= now and not date_match and not day_match and not re.search(r"\b(?:hoje|amanh[ãa])\b", lowered):
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
    pending_text = _load_pending_reminder()
    due_at, text, repeat = parse_reminder_details(raw_text)
    if pending_text and due_at is not None and not text:
        due_at, text, repeat = parse_reminder_details(f"{pending_text} {raw_text}")
        _clear_pending_reminder()
    text = _apply_reminder_text_corrections(text)
    text = _resolve_deictic_text(text)
    if not text:
        return "O que devo lembrar?"
    if due_at is None:
        _save_pending_reminder(text)
        return "Quando devo lembrar isso?"

    reminder = {
        "id": str(time.time_ns()),
        "text": text,
        "due_at": due_at.isoformat(timespec="minutes"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notified_at": "",
    }
    if repeat:
        reminder["repeat"] = repeat
    _update_reminders(lambda data: {"items": sorted([*(data.get("items") or []), reminder], key=lambda item: str(item.get("due_at", "")))})
    _clear_pending_reminder()
    recurrence = " todo ano" if repeat == "yearly" else ""
    return f"Combinado. Vou lembrar{recurrence} { _format_due_at(due_at) }: {text}."


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
    _update_reminders(lambda current: {"items": [item for item in (current.get("items") or []) if item.get("id") != removed_id]})
    return f"Removi o lembrete: {removed.get('text', 'item sem titulo')}."


def _add_years(value: datetime, years: int = 1) -> datetime:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=3, day=1, year=value.year + years)


def consume_due_reminders(now: datetime | None = None, limit: int = 3) -> list[dict]:
    now = now or datetime.now()
    due = []

    def mark_due(data: dict) -> dict:
        items = data.get("items") or []
        for item in items:
            if item.get("notified_at"):
                continue
            try:
                due_at = datetime.fromisoformat(str(item.get("due_at", "")))
            except Exception:
                continue
            if due_at <= now:
                due.append(dict(item))
                if item.get("repeat") == "yearly":
                    next_due = due_at
                    while next_due <= now:
                        next_due = _add_years(next_due, 1)
                    item["due_at"] = next_due.isoformat(timespec="minutes")
                    item["notified_at"] = ""
                else:
                    item["notified_at"] = now.isoformat(timespec="seconds")
            if len(due) >= limit:
                break
        return {"items": items}

    _update_reminders(mark_due)
    return due
