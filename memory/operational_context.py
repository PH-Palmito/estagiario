import json
import os
import re
import time
from pathlib import Path

from memory.auto_advances import load_auto_advances
from memory.bottlenecks import load_bottlenecks
from memory.profile import load_profile
from memory.self_evolution import load_self_evolution_plan
from memory.ui_state import load_ui_state


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
OPERATIONAL_CONTEXT_PATH = MEMORY_DIR / "operational_context.json"


APP_HINTS = {
    "spotify": "spotify",
    "whatsapp": "whatsapp",
    "chrome": "chrome",
    "edge": "edge",
    "github": "github",
    "youtube": "youtube",
    "android studio": "android studio",
    "code": "vs code",
    "vscode": "vs code",
}

SITE_HINTS = {
    "mercado livre": "mercado livre",
    "mercadolivre": "mercado livre",
    "magalu": "magalu",
    "magazine luiza": "magalu",
    "investidor10": "investidor10",
    "github": "github",
    "youtube": "youtube",
}

STOPWORDS = {
    "para", "com", "sem", "que", "isso", "essa", "esse", "agora", "depois", "antes",
    "tela", "pagina", "página", "site", "app", "aplicativo", "abre", "abrir", "fechar",
    "fecha", "detalha", "detalhar", "resuma", "resumir", "oque", "oque", "tem", "na",
    "no", "de", "do", "da", "em", "pra", "pro", "uma", "um", "mais", "como", "qual",
    "vou", "quero", "gostaria", "axel", "codex",
}


def _save_json(path: Path, payload: dict):
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _normalize(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _collect_recent_user_texts(limit: int = 8) -> list[str]:
    state = load_ui_state()
    history = state.get("history") or []
    recent = []
    for key in ("last_command", "last_heard"):
        text = str(state.get(key, "")).strip()
        if text and text not in recent:
            recent.append(text)
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        text = str(item.get("text", "")).strip()
        if role != "user" or not text:
            continue
        if text not in recent:
            recent.append(text)
        if len(recent) >= limit:
            break
    return list(reversed(recent))


def _collect_recent_assistant_texts(limit: int = 8) -> list[str]:
    state = load_ui_state()
    history = state.get("history") or []
    recent = []
    last_response = str(state.get("last_response", "")).strip()
    if last_response:
        recent.append(last_response)
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        text = str(item.get("text", "")).strip()
        if role != "assistant" or not text:
            continue
        if text not in recent:
            recent.append(text)
        if len(recent) >= limit:
            break
    return list(reversed(recent))


def _extract_keywords(texts: list[str], limit: int = 6) -> list[str]:
    scores = {}
    for text in texts:
        normalized = _normalize(text)
        for token in normalized.split():
            if len(token) < 4 or token.isdigit() or token in STOPWORDS:
                continue
            scores[token] = scores.get(token, 0) + 1
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _count in ranked[:limit]]


def _extract_named_hits(texts: list[str], hints: dict[str, str], limit: int = 4) -> list[str]:
    hits = []
    seen = set()
    for text in texts:
        normalized = _normalize(text)
        for key, value in hints.items():
            if key in normalized and value not in seen:
                seen.add(value)
                hits.append(value)
                if len(hits) >= limit:
                    return hits
    return hits


def generate_operational_context() -> dict:
    profile = load_profile() or {}
    advances = load_auto_advances() or []
    bottlenecks = load_bottlenecks() or []
    self_evolution = load_self_evolution_plan() or {}
    ui_state = load_ui_state() or {}
    user_texts = _collect_recent_user_texts(limit=8)
    assistant_texts = _collect_recent_assistant_texts(limit=8)
    context_texts = user_texts + assistant_texts

    current_focus = str(self_evolution.get("current_focus", "")).strip()
    if not current_focus and advances:
        current_focus = str(advances[0].get("title", "")).strip()

    next_advances = [
        str(item.get("title", "")).strip()
        for item in advances[:3]
        if isinstance(item, dict) and str(item.get("title", "")).strip()
    ]
    active_bottlenecks = [
        str(item.get("title", "")).strip()
        for item in bottlenecks[:3]
        if isinstance(item, dict) and str(item.get("title", "")).strip()
    ]

    recent_apps = _extract_named_hits(context_texts, APP_HINTS, limit=4)
    recent_sites = _extract_named_hits(context_texts, SITE_HINTS, limit=4)
    recent_topics = _extract_keywords(user_texts, limit=6)

    operator = str(profile.get("nome", "")).strip() or "Operador"
    assistant = str((profile.get("assistente") or {}).get("nome", "")).strip() or str(ui_state.get("assistant_name", "")).strip() or "Axel"
    focus_stack = profile.get("foco_profissional") or []

    summary_parts = [
        f"{assistant} acompanhando {operator}.",
    ]
    if current_focus:
        summary_parts.append(f"Foco atual: {current_focus}.")
    if recent_apps:
        summary_parts.append("Apps recentes: " + ", ".join(recent_apps) + ".")
    if recent_sites:
        summary_parts.append("Contexto web: " + ", ".join(recent_sites) + ".")
    if recent_topics:
        summary_parts.append("Topicos recentes: " + ", ".join(recent_topics[:4]) + ".")

    payload = {
        "generated_at": time.time(),
        "assistant_name": assistant,
        "operator_name": operator,
        "current_focus": current_focus,
        "focus_stack": [str(item) for item in focus_stack[:4]],
        "recent_user_requests": user_texts[-5:],
        "recent_apps": recent_apps,
        "recent_sites": recent_sites,
        "recent_topics": recent_topics,
        "conversation_mode": bool(ui_state.get("conversation_mode")),
        "dictation_mode": bool(ui_state.get("dictation_mode")),
        "next_advances": next_advances,
        "active_bottlenecks": active_bottlenecks,
        "summary": " ".join(summary_parts).strip(),
    }
    return payload


def save_operational_context() -> dict:
    payload = generate_operational_context()
    _save_json(OPERATIONAL_CONTEXT_PATH, payload)
    return payload


def load_operational_context() -> dict:
    data = _load_json(OPERATIONAL_CONTEXT_PATH)
    if isinstance(data, dict) and data.get("generated_at"):
        return data
    return save_operational_context()


def format_operational_context() -> str:
    payload = load_operational_context()
    summary = str(payload.get("summary", "")).strip()
    if not summary:
        return "Ainda nao consolidei o contexto operacional atual."

    parts = [summary]
    next_advances = payload.get("next_advances") or []
    if next_advances:
        parts.append("Proximos passos: " + "; ".join(str(item) for item in next_advances[:3]) + ".")
    active_bottlenecks = payload.get("active_bottlenecks") or []
    if active_bottlenecks:
        parts.append("Gargalos vivos: " + "; ".join(str(item) for item in active_bottlenecks[:2]) + ".")
    return " ".join(parts)
