import re
import time
from pathlib import Path

from memory.auto_advances import load_auto_advances
from memory.bottlenecks import load_bottlenecks
from memory.current_topic import load_current_topic
from memory.json_store import read_json_file, write_json_atomic
from memory.obsidian_sync import sync_operational_context_note
from memory.profile import load_profile
from memory.reminders import load_reminders
from memory.self_evolution import load_self_evolution_plan
from memory.supabase_sync import sync_memory_state_safely
from memory.ui_state import load_ui_state
from memory.voice_preferences import load_voice_preferences

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
OPERATIONAL_CONTEXT_PATH = MEMORY_DIR / "operational_context.json"
OPERATIONAL_MEMORY_PATH = MEMORY_DIR / "operational_memory.json"


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
    "fecha", "detalha", "detalhar", "resuma", "resumir", "oque", "tem", "na",
    "no", "de", "do", "da", "em", "pra", "pro", "uma", "um", "mais", "como", "qual",
    "vou", "quero", "gostaria", "axel", "codex",
}

TICKER_RE = re.compile(r"\b[A-Za-z]{4}\d{1,2}\b")

PREFERENCE_KEYS = (
    "assistant_style",
    "assistant_address_user",
    "assistant_brief_confirmations",
    "assistant_humor_enabled",
    "assistant_humor_style",
    "assistant_humor_level",
    "chat_enabled",
    "chat_model",
    "tts_enabled",
    "tts_engine",
    "tts_voice_name",
    "tts_voice_culture",
    "gemini_tts_voice_name",
    "audio_input_device",
    "hotword",
    "trigger_hotkey",
    "toggle_listening_hotkey",
)


def _save_json(path: Path, payload: dict):
    write_json_atomic(path, payload, indent=2)


def _load_json(path: Path):
    return read_json_file(path, {}, validator=lambda value: isinstance(value, dict))


def _fingerprint(payload: dict) -> str:
    stable = dict(payload or {})
    stable.pop("generated_at", None)
    import json

    return json.dumps(stable, ensure_ascii=False, sort_keys=True)


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


def _extract_recent_tickers(texts: list[str], limit: int = 8) -> list[str]:
    seen = set()
    hits = []
    for text in texts:
        for match in TICKER_RE.findall(str(text or "")):
            ticker = str(match).upper().strip()
            if ticker in seen:
                continue
            seen.add(ticker)
            hits.append(ticker)
            if len(hits) >= limit:
                return hits
    return hits


def _load_open_tasks(limit: int = 6) -> list[str]:
    todo_path = MEMORY_DIR / "todo.md"
    try:
        lines = todo_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    tasks = []
    for raw in lines:
        line = str(raw or "").strip()
        if not line.startswith("- [ ]"):
            continue
        task = line[len("- [ ]"):].strip()
        if task:
            tasks.append(task)
        if len(tasks) >= limit:
            break
    return tasks


def _load_pending_reminders(limit: int = 4) -> list[str]:
    reminders = load_reminders().get("items") or []
    pending = []
    for item in sorted(reminders, key=lambda value: str((value or {}).get("due_at", ""))):
        if not isinstance(item, dict) or item.get("notified_at"):
            continue
        text = str(item.get("text", "")).strip()
        due_at = str(item.get("due_at", "")).strip()
        if text and due_at:
            pending.append(f"{due_at}: {text}")
        elif text:
            pending.append(text)
        if len(pending) >= limit:
            break
    return pending


def _collect_operational_preferences() -> dict:
    preferences = load_voice_preferences() or {}
    return {
        key: preferences.get(key)
        for key in PREFERENCE_KEYS
        if key in preferences and preferences.get(key) not in ("", None)
    }


def load_operational_memory() -> dict:
    data = _load_json(OPERATIONAL_MEMORY_PATH)
    if not isinstance(data, dict):
        return {"preferences": [], "notes": []}

    preferences = data.get("preferences")
    notes = data.get("notes")
    data["preferences"] = preferences if isinstance(preferences, list) else []
    data["notes"] = notes if isinstance(notes, list) else []
    return data


def _save_operational_memory(data: dict) -> dict:
    payload = dict(data or {})
    payload["updated_at"] = time.time()
    _save_json(OPERATIONAL_MEMORY_PATH, payload)
    sync_memory_state_safely("operational_memory", payload, category="context")
    return payload


def remember_operational_preference(text: str, kind: str = "preference") -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip(" .")
    if not clean:
        return "Qual preferência operacional devo lembrar?"

    memory = load_operational_memory()
    key = "notes" if kind == "note" else "preferences"
    items = [str(item).strip() for item in memory.get(key, []) if str(item).strip()]
    normalized = _normalize(clean)
    if not any(_normalize(item) == normalized for item in items):
        items.append(clean)
    memory[key] = items[-40:]
    _save_operational_memory(memory)
    save_operational_context()

    if key == "notes":
        return f"Anotei no contexto operacional: {clean}."
    return f"Preferência operacional salva: {clean}."


def forget_operational_preference(text: str) -> str:
    target = _normalize(text)
    if not target:
        return "Qual preferência operacional devo esquecer?"

    memory = load_operational_memory()
    removed = []
    for key in ("preferences", "notes"):
        kept = []
        for item in [str(value).strip() for value in memory.get(key, []) if str(value).strip()]:
            normalized = _normalize(item)
            if target in normalized or normalized in target:
                removed.append(item)
            else:
                kept.append(item)
        memory[key] = kept

    if not removed:
        return "Não encontrei essa preferência operacional."

    _save_operational_memory(memory)
    save_operational_context()
    return "Removi da memória operacional: " + "; ".join(removed[:3]) + "."


def format_operational_memory() -> str:
    memory = load_operational_memory()
    preferences = [str(item).strip() for item in memory.get("preferences", []) if str(item).strip()]
    notes = [str(item).strip() for item in memory.get("notes", []) if str(item).strip()]
    parts = []
    if preferences:
        parts.append("Preferências: " + "; ".join(preferences[:6]) + ".")
    if notes:
        parts.append("Notas: " + "; ".join(notes[:4]) + ".")
    return " ".join(parts) if parts else "Ainda não há preferências operacionais salvas."


def _format_preference_summary(preferences: dict) -> str:
    if not preferences:
        return ""

    parts = []
    style = str(preferences.get("assistant_style") or preferences.get("assistant_humor_style") or "").strip()
    if style:
        parts.append(f"estilo {style}")

    address = str(preferences.get("assistant_address_user") or "").strip()
    if address:
        parts.append(f"tratamento '{address}'")

    if "assistant_brief_confirmations" in preferences:
        brief = "confirmacoes breves" if bool(preferences.get("assistant_brief_confirmations")) else "confirmacoes detalhadas"
        parts.append(brief)

    if "assistant_humor_enabled" in preferences:
        if bool(preferences.get("assistant_humor_enabled")):
            humor_style = str(preferences.get("assistant_humor_style") or "seco").strip()
            humor_level = preferences.get("assistant_humor_level", 2)
            parts.append(f"humor {humor_style} nivel {humor_level}")
        else:
            parts.append("humor desligado")

    if "chat_model" in preferences:
        parts.append(f"modelo de chat {preferences.get('chat_model')}")

    tts_engine = str(preferences.get("tts_engine") or "").strip()
    tts_voice = str(preferences.get("tts_voice_name") or preferences.get("gemini_tts_voice_name") or "").strip()
    if tts_engine and tts_voice:
        parts.append(f"voz {tts_engine}/{tts_voice}")
    elif tts_engine:
        parts.append(f"voz {tts_engine}")

    hotword = str(preferences.get("hotword") or "").strip()
    if hotword:
        parts.append(f"hotword '{hotword}'")

    return ", ".join(parts[:8])


def generate_operational_context() -> dict:
    profile = load_profile() or {}
    preferences = _collect_operational_preferences()
    operational_memory = load_operational_memory()
    preference_summary = _format_preference_summary(preferences)
    saved_preferences = [
        str(item).strip()
        for item in operational_memory.get("preferences", [])
        if str(item).strip()
    ]
    saved_notes = [
        str(item).strip()
        for item in operational_memory.get("notes", [])
        if str(item).strip()
    ]
    advances = load_auto_advances() or []
    bottlenecks = load_bottlenecks() or []
    self_evolution = load_self_evolution_plan() or {}
    ui_state = load_ui_state() or {}
    user_texts = _collect_recent_user_texts(limit=8)
    assistant_texts = _collect_recent_assistant_texts(limit=8)
    context_texts = user_texts + assistant_texts

    next_advances = [
        str(item.get("title", "")).strip()
        for item in advances[:3]
        if isinstance(item, dict) and str(item.get("title", "")).strip()
    ]
    current_focus = str(self_evolution.get("current_focus", "")).strip()
    if next_advances and current_focus not in next_advances or not current_focus and next_advances:
        current_focus = next_advances[0]
    active_bottlenecks = [
        str(item.get("title", "")).strip()
        for item in bottlenecks[:3]
        if isinstance(item, dict) and str(item.get("title", "")).strip()
    ]

    recent_apps = _extract_named_hits(context_texts, APP_HINTS, limit=4)
    recent_sites = _extract_named_hits(context_texts, SITE_HINTS, limit=4)
    recent_topics = _extract_keywords(user_texts, limit=6)
    recent_tickers = _extract_recent_tickers(context_texts, limit=8)
    open_tasks = _load_open_tasks(limit=6)
    pending_reminders = _load_pending_reminders(limit=4)
    current_topic = load_current_topic()

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
    if recent_tickers:
        summary_parts.append("Tickers recentes: " + ", ".join(recent_tickers[:4]) + ".")
    if preference_summary:
        summary_parts.append("Preferencias operacionais: " + preference_summary + ".")
    if saved_preferences:
        summary_parts.append("Preferencias salvas: " + "; ".join(saved_preferences[:3]) + ".")
    if saved_notes:
        summary_parts.append("Notas operacionais: " + "; ".join(saved_notes[:2]) + ".")
    topic_name = str(current_topic.get("topic", "")).strip()
    if topic_name:
        summary_parts.append(f"Assunto atual: {topic_name}.")
    if open_tasks:
        summary_parts.append("Tarefas abertas: " + "; ".join(open_tasks[:2]) + ".")
    if pending_reminders:
        summary_parts.append("Lembretes pendentes: " + "; ".join(pending_reminders[:2]) + ".")

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
        "recent_tickers": recent_tickers,
        "operational_preferences": preferences,
        "saved_preferences": saved_preferences,
        "saved_notes": saved_notes,
        "preference_summary": preference_summary,
        "current_topic": current_topic,
        "conversation_mode": bool(ui_state.get("conversation_mode")),
        "dictation_mode": bool(ui_state.get("dictation_mode")),
        "next_advances": next_advances,
        "open_tasks": open_tasks,
        "pending_reminders": pending_reminders,
        "active_bottlenecks": active_bottlenecks,
        "summary": " ".join(summary_parts).strip(),
    }
    return payload


def save_operational_context() -> dict:
    payload = generate_operational_context()
    current = _load_json(OPERATIONAL_CONTEXT_PATH)
    if isinstance(current, dict) and current and _fingerprint(current) == _fingerprint(payload):
        return current
    _save_json(OPERATIONAL_CONTEXT_PATH, payload)
    sync_memory_state_safely("operational_context", payload, category="context")
    sync_operational_context_note(payload)
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
