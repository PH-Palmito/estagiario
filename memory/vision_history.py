import json
import os
import time
from pathlib import Path

from memory.current_topic import update_current_topic_from_vision
from memory.supabase_sync import sync_memory_state_safely


HISTORY_PATH = Path("memory/vision_history.json")
MAX_ITEMS = 8


def _fix_mojibake(text: str) -> str:
    content = str(text or "")
    if not any(marker in content for marker in ("Ã", "Â", "�")):
        return _pt_display_text(content)
    try:
        content = content.encode("latin1").decode("utf-8")
    except Exception:
        pass
    return _pt_display_text(content)


def _pt_display_text(text: str) -> str:
    replacements = {
        "analise": "análise",
        "analises": "análises",
        "area": "área",
        "conteudo": "conteúdo",
        "grafico": "gráfico",
        "graficos": "gráficos",
        "historico": "histórico",
        "pagina": "página",
        "possivel": "possível",
        "rapida": "rápida",
        "ultimas": "últimas",
        "visao": "visão",
        "visivel": "visível",
    }

    def replace(match):
        original = match.group(0)
        replacement = replacements.get(original.lower(), original)
        if original[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    import re

    pattern = r"\b(" + "|".join(re.escape(word) for word in sorted(replacements, key=len, reverse=True)) + r")\b"
    return re.sub(pattern, replace, str(text or ""), flags=re.IGNORECASE)


def _load_history() -> list[dict]:
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def load_vision_history(limit: int = MAX_ITEMS) -> list[dict]:
    items = _load_history()
    cleaned = []
    for item in items[-max(1, int(limit)):]:
        if not isinstance(item, dict):
            continue
        copy = dict(item)
        copy["source"] = _fix_mojibake(str(copy.get("source", "")))
        copy["summary"] = _fix_mojibake(str(copy.get("summary", "")))
        cleaned.append(copy)
    return cleaned


def _save_history(items: list[dict]):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(items[-MAX_ITEMS:], ensure_ascii=False, indent=2)
    tmp_path = HISTORY_PATH.with_name(f"{HISTORY_PATH.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, HISTORY_PATH)
    sync_memory_state_safely("vision_history", {"items": items[-MAX_ITEMS:]}, category="vision")


def remember_vision_analysis(source: str, summary: str, details: dict | None = None):
    summary = " ".join(str(summary or "").split()).strip()
    if not summary:
        return
    details = details if isinstance(details, dict) else {}
    items = _load_history()
    items.append(
        {
            "created_at": time.time(),
            "source": str(source or "imagem"),
            "summary": summary,
            "details": details,
        }
    )
    _save_history(items)
    update_current_topic_from_vision(summary=summary, details=details, source=source)


def last_vision_analysis() -> str:
    items = load_vision_history(limit=1)
    if not items:
        return "Ainda não tenho análise visual guardada."
    item = items[-1]
    source = str(item.get("source", "imagem")).strip() or "imagem"
    summary = str(item.get("summary", "")).strip()
    if not summary:
        return "A última análise visual ficou vazia."
    return f"Última análise visual ({source}): {summary}"


def format_vision_history(limit: int = 5) -> str:
    items = load_vision_history(limit=limit)
    if not items:
        return "Ainda não tenho histórico visual salvo."

    lines = []
    for index, item in enumerate(reversed(items), start=1):
        source = str(item.get("source", "imagem")).strip() or "imagem"
        summary = " ".join(str(item.get("summary", "")).split()).strip()
        if len(summary) > 220:
            summary = summary[:217].rstrip() + "..."
        lines.append(f"{index}. {source}: {summary}")
    return "Histórico visual recente: " + " | ".join(lines)


def last_vision_item() -> dict | None:
    items = load_vision_history(limit=1)
    if not items:
        return None
    item = items[-1]
    return item if isinstance(item, dict) else None
