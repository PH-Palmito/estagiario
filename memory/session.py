history = []
turns = []


def add(message: str):
    history.append(message)

    if len(history) > 10:
        del history[0]


def get():
    return history[-3:]


def add_turn(role: str, text: str, *, source: str = "runtime") -> None:
    content = str(text or "").strip()
    if not content:
        return
    turns.append(
        {
            "role": str(role or "unknown").strip() or "unknown",
            "text": content,
            "source": str(source or "runtime").strip() or "runtime",
        }
    )
    if len(turns) > 24:
        del turns[:-24]


def recent_turns(limit: int = 8) -> list[dict]:
    return [dict(item) for item in turns[-max(1, int(limit)) :]]


def format_recent_turns(limit: int = 6) -> str:
    recent = recent_turns(limit)
    if not recent:
        return "Sem memoria curta da sessao."
    rows = []
    for item in recent:
        role = str(item.get("role", "")).strip() or "unknown"
        text = str(item.get("text", "")).strip()
        if text:
            rows.append(f"{role}: {text}")
    return "Memoria curta: " + " | ".join(rows) + "."


def clear():
    history.clear()
    turns.clear()
