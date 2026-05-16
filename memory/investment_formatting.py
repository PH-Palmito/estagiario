from datetime import datetime


def format_brl(value: float | None) -> str:
    if value is None:
        return ""
    formatted = f"{float(value):,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: float | None, digits: int = 1) -> str:
    if value is None:
        return ""
    formatted = f"{float(value):,.{digits}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".") + "%"


def parse_currency_value(text: str) -> float | None:
    cleaned = str(text or "").strip().lower().replace("r$", "").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_percent_value(text: str) -> float | None:
    cleaned = str(text or "").strip().replace("%", "").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_iso_datetime(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone()
    except Exception:
        return None


def format_day_month(value: str) -> str:
    parsed = parse_iso_datetime(value)
    if not parsed:
        return ""
    return parsed.strftime("%d/%m")
