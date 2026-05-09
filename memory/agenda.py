from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path


AGENDA_PATH = Path("memory/agenda.json")


def _load_agenda() -> dict:
    if not AGENDA_PATH.exists():
        return {}
    try:
        data = json.loads(AGENDA_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_agenda(data: dict):
    AGENDA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _today() -> date:
    return datetime.now().date()


def _date_key(target: date) -> str:
    return target.isoformat()


def _parse_target_day_and_text(raw_text: str) -> tuple[date, str]:
    text = str(raw_text or "").strip()
    lowered = text.lower()
    today = _today()

    if lowered.startswith("amanhã "):
        return today + timedelta(days=1), text[7:].strip()
    if lowered.startswith("amanha "):
        return today + timedelta(days=1), text[7:].strip()
    if lowered.startswith("hoje "):
        return today, text[5:].strip()

    parts = text.split(" ", 1)
    if parts:
        head = parts[0].strip()
        if len(head) == 5 and head[2] == "/":
            try:
                day = int(head[:2])
                month = int(head[3:])
                target = date(today.year, month, day)
                body = parts[1].strip() if len(parts) > 1 else ""
                return target, body or text
            except Exception:
                pass

    return today, text


def add_agenda_item(raw_text: str) -> str:
    target_day, text = _parse_target_day_and_text(raw_text)
    if not text:
        return "Qual compromisso devo registrar?"

    agenda = _load_agenda()
    key = _date_key(target_day)
    items = agenda.get(key) or []
    items.append(
        {
            "text": text,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    agenda[key] = items
    _save_agenda(agenda)

    if target_day == _today():
        return f"Compromisso registrado para hoje: {text}."
    if target_day == _today() + timedelta(days=1):
        return f"Compromisso registrado para amanha: {text}."
    return f"Compromisso registrado para {target_day.strftime('%d/%m')}: {text}."


def _format_agenda_items(items: list[dict]) -> str:
    rows = []
    for index, item in enumerate(items, start=1):
        text = str((item or {}).get("text") or "").strip()
        if text:
            rows.append(f"{index}. {text}")
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

    removed = items.pop(index - 1)
    if items:
        agenda[key] = items
    else:
        agenda.pop(key, None)
    _save_agenda(agenda)
    return f"Removi da agenda: {removed.get('text', 'item sem titulo')}."


def agenda_brief_summary() -> str:
    today_text = list_agenda_today()
    tomorrow_text = list_agenda_tomorrow()
    if "livre" in today_text.lower() and "vazia" in tomorrow_text.lower():
        return "Agenda sem compromissos proximos."
    if "livre" in today_text.lower():
        return tomorrow_text
    return today_text
