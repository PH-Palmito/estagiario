from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from memory.contextual_suggestions import agenda_contextual_suggestion, agenda_follow_up_prompt
from memory.json_store import read_json_file, update_json_file, write_json_atomic
from memory.reminders import parse_reminder_request

AGENDA_PATH = Path("memory/agenda.json")
AGENDA_ICS_EXPORT_PATH = Path("memory/axel_agenda.ics")


def _load_agenda() -> dict:
    return read_json_file(AGENDA_PATH, {}, validator=lambda value: isinstance(value, dict))


def _save_agenda(data: dict):
    write_json_atomic(AGENDA_PATH, data, indent=2, trailing_newline=True)


def _update_agenda(updater) -> dict:
    return update_json_file(
        AGENDA_PATH,
        {},
        lambda data: updater(data if isinstance(data, dict) else {}),
        validator=lambda value: isinstance(value, dict),
        indent=2,
        trailing_newline=True,
    )


def _today() -> date:
    return datetime.now().date()


def _date_key(target: date) -> str:
    return target.isoformat()


def _escape_ics_text(text: str) -> str:
    value = str(text or "")
    value = value.replace("\\", "\\\\").replace("\n", "\\n")
    value = value.replace(",", "\\,").replace(";", "\\;")
    return value


def _unescape_ics_text(text: str) -> str:
    value = str(text or "")
    value = value.replace("\\n", "\n").replace("\\;", ";").replace("\\,", ",")
    return value.replace("\\\\", "\\").strip()


def _format_ics_datetime(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _parse_ics_datetime(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.rstrip("Z")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            if fmt == "%Y%m%d":
                return parsed.replace(hour=9, minute=0)
            return parsed
        except ValueError:
            continue
    return None


def _parse_target_day_and_text(raw_text: str) -> tuple[date, str]:
    text = str(raw_text or "").strip()
    lowered = text.lower()
    today = _today()

    def clean_schedule_words(value: str) -> str:
        cleaned = re.sub(r"\b(?:me\s+)?lembre\b", " ", value, flags=re.I)
        cleaned = re.sub(r"\blembrete\b", " ", cleaned, flags=re.I)
        return re.sub(r"\s+", " ", cleaned).strip(" .,:;-")

    if lowered.startswith("amanhã "):
        return today + timedelta(days=1), clean_schedule_words(text[7:])
    if lowered.startswith("amanha "):
        return today + timedelta(days=1), clean_schedule_words(text[7:])
    if lowered.startswith("hoje "):
        return today, clean_schedule_words(text[5:])

    if re.search(r"\bamanh[ãa]\b", lowered):
        cleaned = re.sub(r"\bamanh[ãa]\b", " ", text, flags=re.I)
        return today + timedelta(days=1), clean_schedule_words(cleaned) or text

    if re.search(r"\b(?:hoje|hj)\b", lowered):
        cleaned = re.sub(r"\b(?:hoje|hj)\b", " ", text, flags=re.I)
        return today, clean_schedule_words(cleaned) or text

    parts = text.split(" ", 1)
    if parts:
        head = parts[0].strip()
        if len(head) == 5 and head[2] == "/":
            try:
                day = int(head[:2])
                month = int(head[3:])
                target = date(today.year, month, day)
                body = clean_schedule_words(parts[1]) if len(parts) > 1 else ""
                return target, body or text
            except Exception:
                pass

    day_match = re.search(r"\bdia\s+(\d{1,2})\b", lowered)
    if day_match:
        day = int(day_match.group(1))
        try:
            target = date(today.year, today.month, day)
            if target < today:
                next_month = today.month + 1
                year = today.year
                if next_month > 12:
                    next_month = 1
                    year += 1
                target = date(year, next_month, day)
            cleaned = clean_schedule_words(re.sub(r"\bdia\s+\d{1,2}\b", " ", text, flags=re.I))
            return target, cleaned or text
        except Exception:
            pass

    return today, clean_schedule_words(text) or text


def _parse_agenda_request(raw_text: str) -> tuple[date, str, datetime | None]:
    due_at, reminder_text = parse_reminder_request(raw_text)
    if due_at is not None:
        text = reminder_text.strip() or str(raw_text or "").strip()
        return due_at.date(), text, due_at

    target_day, text = _parse_target_day_and_text(raw_text)
    return target_day, text, None


def add_agenda_item(raw_text: str) -> str:
    target_day, text, due_at = _parse_agenda_request(raw_text)
    if not text:
        return "Qual compromisso devo registrar?"

    key = _date_key(target_day)
    item = {
        "text": text,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    if due_at is not None:
        item["due_at"] = due_at.isoformat(timespec="minutes")
        item["notified_at"] = ""

    def add_item(agenda: dict) -> dict:
        items = list(agenda.get(key) or [])
        items.append(item)
        agenda[key] = items
        return agenda

    _update_agenda(add_item)

    time_suffix = f" as {due_at.strftime('%H:%M')}" if due_at is not None else ""

    suggestion = agenda_contextual_suggestion(text, target_day, due_at)
    if target_day == _today():
        return f"Compromisso registrado para hoje{time_suffix}: {text}.{suggestion}"
    if target_day == _today() + timedelta(days=1):
        return f"Compromisso registrado para amanha{time_suffix}: {text}.{suggestion}"
    return f"Compromisso registrado para {target_day.strftime('%d/%m')}{time_suffix}: {text}.{suggestion}"


def _format_agenda_items(items: list[dict]) -> str:
    rows = []
    for index, item in enumerate(items, start=1):
        text = str((item or {}).get("text") or "").strip()
        if text:
            due_at_text = ""
            try:
                due_at = datetime.fromisoformat(str((item or {}).get("due_at") or ""))
                due_at_text = f"{due_at.strftime('%H:%M')} - "
            except Exception:
                due_at_text = ""
            rows.append(f"{index}. {due_at_text}{text}")
    return " ; ".join(rows)


def list_agenda_today() -> str:
    agenda = _load_agenda()
    items = agenda.get(_date_key(_today())) or []
    if not items:
        return "Sua agenda de hoje esta livre por enquanto."
    return "Agenda de hoje: " + _format_agenda_items(items) + "."


def list_agenda_tomorrow() -> str:
    agenda = _load_agenda()
    items = agenda.get(_date_key(_today() + timedelta(days=1))) or []
    if not items:
        return "Sua agenda de amanha ainda esta vazia."
    return "Agenda de amanha: " + _format_agenda_items(items) + "."


def list_agenda_all() -> str:
    agenda = _load_agenda()
    if not agenda:
        return "Ainda nao ha compromissos salvos na agenda."
    rows = []
    for key in sorted(agenda.keys())[:7]:
        items = agenda.get(key) or []
        if not items:
            continue
        rows.append(f"{key}: {_format_agenda_items(items)}")
    if not rows:
        return "Ainda nao ha compromissos salvos na agenda."
    return "Proximos compromissos: " + " | ".join(rows) + "."


def calendar_sync_status() -> str:
    total = 0
    for items in _load_agenda().values():
        if isinstance(items, list):
            total += len([item for item in items if isinstance(item, dict)])
    suffix = f" Ultima exportacao: {AGENDA_ICS_EXPORT_PATH}." if AGENDA_ICS_EXPORT_PATH.exists() else ""
    return (
        "Calendario externo: primeira camada via arquivo ICS. "
        f"Agenda local tem {total} compromisso(s)."
        f"{suffix}"
    )


def export_agenda_ics(path: str | Path | None = None) -> str:
    target = Path(path) if path else AGENDA_ICS_EXPORT_PATH
    agenda = _load_agenda()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Axel//Local Agenda//PT-BR",
        "CALSCALE:GREGORIAN",
    ]
    count = 0
    now_stamp = _format_ics_datetime(datetime.now())
    for day_key in sorted(agenda.keys()):
        items = agenda.get(day_key) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            try:
                start = datetime.fromisoformat(str(item.get("due_at") or ""))
            except Exception:
                try:
                    start = datetime.fromisoformat(day_key).replace(hour=9, minute=0)
                except Exception:
                    continue
            end = start + timedelta(minutes=30)
            uid = str(item.get("uid") or f"axel-{day_key}-{count}-{uuid4().hex[:8]}")
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{now_stamp}",
                    f"DTSTART:{_format_ics_datetime(start)}",
                    f"DTEND:{_format_ics_datetime(end)}",
                    f"SUMMARY:{_escape_ics_text(text)}",
                    "END:VEVENT",
                ]
            )
            count += 1
    lines.append("END:VCALENDAR")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return f"Exportei {count} compromisso(s) para {target}."


def import_agenda_ics(path: str | Path) -> str:
    source = Path(str(path or "").strip().strip('"'))
    if not source.exists():
        return "Arquivo ICS nao encontrado."

    content = source.read_text(encoding="utf-8", errors="ignore")
    events = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", content, flags=re.S | re.I)
    imported = 0

    def field(block: str, name: str) -> str:
        match = re.search(rf"^{name}(?:;[^:]*)?:(.+)$", block, flags=re.M | re.I)
        return match.group(1).strip() if match else ""

    def add_events(agenda: dict) -> dict:
        nonlocal imported
        for block in events:
            summary = _unescape_ics_text(field(block, "SUMMARY"))
            start = _parse_ics_datetime(field(block, "DTSTART"))
            if not summary or start is None:
                continue
            key = _date_key(start.date())
            item = {
                "text": summary,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "source": "ics",
                "uid": field(block, "UID") or f"ics-{uuid4().hex}",
                "due_at": start.isoformat(timespec="minutes"),
                "notified_at": "",
            }
            items = list(agenda.get(key) or [])
            uid = str(item["uid"])
            if any(str(existing.get("uid") or "") == uid for existing in items if isinstance(existing, dict)):
                continue
            items.append(item)
            agenda[key] = items
            imported += 1
        return agenda

    _update_agenda(add_events)
    return f"Importei {imported} compromisso(s) de {source}."


def remove_agenda_item(index_text: str, scope: str = "today") -> str:
    try:
        index = int(str(index_text or "").strip())
    except Exception:
        return "Qual item da agenda devo remover?"

    target_day = _today()
    if scope == "tomorrow":
        target_day = _today() + timedelta(days=1)

    agenda = _load_agenda()
    key = _date_key(target_day)
    items = agenda.get(key) or []
    if index < 1 or index > len(items):
        return "Nao encontrei esse item na agenda."

    removed = items[index - 1]

    def remove_item(current: dict) -> dict:
        current_items = list(current.get(key) or [])
        if 1 <= index <= len(current_items):
            current_items.pop(index - 1)
        if current_items:
            current[key] = current_items
        else:
            current.pop(key, None)
        return current

    _update_agenda(remove_item)
    return f"Removi da agenda: {removed.get('text', 'item sem titulo')}."


def agenda_brief_summary() -> str:
    today_text = list_agenda_today()
    tomorrow_text = list_agenda_tomorrow()
    if "livre" in today_text.lower() and "vazia" in tomorrow_text.lower():
        return "Agenda sem compromissos proximos."
    if "livre" in today_text.lower():
        return tomorrow_text
    return today_text


def consume_due_agenda_items(now: datetime | None = None, limit: int = 3) -> list[dict]:
    now = now or datetime.now()
    due: list[dict] = []

    def mark_due(data: dict) -> dict:
        for key, items in list(data.items()):
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict) or item.get("notified_at"):
                    continue
                try:
                    due_at = datetime.fromisoformat(str(item.get("due_at", "")))
                except Exception:
                    continue
                if due_at <= now:
                    item["notified_at"] = now.isoformat(timespec="seconds")
                    due.append(
                        {
                            "text": str(item.get("text") or "").strip(),
                            "due_at": item.get("due_at"),
                            "source": "agenda",
                            "follow_up_prompt": agenda_follow_up_prompt(str(item.get("text") or "")),
                        }
                    )
                if len(due) >= limit:
                    return data
        return data

    _update_agenda(mark_due)
    return due
