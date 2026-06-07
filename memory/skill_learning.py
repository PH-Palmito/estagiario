from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from memory.json_store import read_json_file, update_json_file
from memory.procedural_skills import load_skills, upsert_skill_from_suggestion

SKILL_LEARNING_PATH = Path("memory") / "skill_learning.json"
MAX_OBSERVATIONS = 120
SUGGESTION_THRESHOLD = 4
IGNORED_INTENTS = {"respond", "repeat_last"}
ACTION_STOPWORDS = {
    "abrir",
    "acionar",
    "ativar",
    "bot",
    "comando",
    "executar",
    "fazer",
    "iniciar",
    "ligar",
    "mostrar",
    "rodar",
}


def _default_state() -> dict:
    return {"observations": [], "patterns": {}, "suggestions": []}


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _normalize_words(text: str) -> list[str]:
    normalized = re.sub(r"[^\w\s/-]", " ", str(text or "").lower())
    stopwords = {
        "para",
        "sobre",
        "isso",
        "essa",
        "esse",
        "qual",
        "quais",
        "como",
        "quando",
        "onde",
        "porque",
        *ACTION_STOPWORDS,
    }
    return [token for token in normalized.split() if len(token) >= 4 and token not in stopwords]


def _safe_skill_name(value: str, fallback: str = "procedimento") -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "-", str(value or "").strip().lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-_")
    return normalized or fallback


def _intent_slug(intent: str) -> str:
    parts = [
        token
        for token in re.split(r"[^a-zA-Z0-9]+", str(intent or "").lower())
        if len(token) >= 3 and token not in {"action", "tool", "execute"}
    ]
    return "-".join(parts[:4])


def _example_slug(examples: list[str]) -> str:
    words: list[str] = []
    for example in examples:
        for token in _normalize_words(example):
            if token not in words:
                words.append(token)
            if len(words) >= 4:
                break
        if len(words) >= 4:
            break
    return "-".join(words)


def _suggestion_profile(toolset: str, agent: str, intent: str, examples: list[str]) -> dict:
    slug = _intent_slug(intent) or _example_slug(examples) or _safe_skill_name(toolset or agent)
    skill_name = _safe_skill_name(slug)
    label = skill_name.replace("-", " ")
    return {
        "skill_name": skill_name,
        "title": f"Criar skill: {label}",
    }


def _pattern_key(toolset: str, agent: str, user_input: str, intent: str) -> str:
    payload = {
        "toolset": str(toolset or "").strip(),
        "agent": str(agent or "").strip(),
        "intent": str(intent or "").strip(),
        "words": _normalize_words(user_input)[:5],
    }
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _skill_exists_for_toolset(toolset: str) -> bool:
    normalized = str(toolset or "").strip().lower()
    return any(skill.name == normalized for skill in load_skills())


def _skill_exists_for_name(name: str) -> bool:
    normalized = str(name or "").strip().lower()
    return any(skill.name == normalized for skill in load_skills())


def load_skill_learning() -> dict:
    data = read_json_file(SKILL_LEARNING_PATH, _default_state(), validator=lambda value: isinstance(value, dict))
    state = _default_state()
    state.update(data or {})
    if not isinstance(state.get("observations"), list):
        state["observations"] = []
    if not isinstance(state.get("patterns"), dict):
        state["patterns"] = {}
    if not isinstance(state.get("suggestions"), list):
        state["suggestions"] = []
    return state


def _suggestion_exists(suggestions: list[dict], pattern_id: str) -> bool:
    return any(isinstance(item, dict) and item.get("pattern_id") == pattern_id for item in suggestions)


def _enrich_suggestion(item: dict) -> dict:
    suggestion = dict(item)
    examples = [str(example).strip() for example in suggestion.get("examples", []) if str(example).strip()]
    profile = _suggestion_profile(
        str(suggestion.get("toolset") or ""),
        str(suggestion.get("agent") or ""),
        str(suggestion.get("intent") or ""),
        examples,
    )
    skill_name = str(suggestion.get("skill_name") or profile["skill_name"])
    suggestion["skill_name"] = skill_name
    old_title = str(suggestion.get("title") or "").strip().lower()
    if not old_title or re.match(r"^(?:criar|atualizar) skill de ", old_title):
        action = "Atualizar" if _skill_exists_for_name(skill_name) else "Criar"
        suggestion["title"] = str(profile["title"]).replace("Criar skill:", f"{action} skill:", 1)
    return suggestion


def observe_skill_opportunity(
    user_input: str,
    raw_action: dict,
    *,
    toolset: str,
    agent: str,
    source: str = "turn",
    now: float | None = None,
) -> dict | None:
    if not isinstance(raw_action, dict):
        return None
    intent = str(raw_action.get("intent") or "").strip()
    if not intent or intent in IGNORED_INTENTS:
        return None

    text = _compact(user_input)
    if len(text) < 8:
        return None

    timestamp = time.time() if now is None else float(now)
    pattern_id = _pattern_key(toolset, agent, text, intent)
    suggestion: dict | None = None

    def updater(state: dict) -> dict:
        nonlocal suggestion
        current = _default_state()
        current.update(state or {})
        observations = [item for item in current.get("observations", []) if isinstance(item, dict)]
        patterns = dict(current.get("patterns") or {})
        suggestions = [item for item in current.get("suggestions", []) if isinstance(item, dict)]

        observations.append(
            {
                "at": timestamp,
                "source": str(source or "turn"),
                "input": text,
                "intent": intent,
                "toolset": str(toolset or ""),
                "agent": str(agent or ""),
                "pattern_id": pattern_id,
            }
        )
        observations = observations[-MAX_OBSERVATIONS:]

        pattern = dict(patterns.get(pattern_id) or {})
        examples = [item for item in pattern.get("examples", []) if isinstance(item, str)]
        if text not in examples:
            examples.append(text)
        count = int(pattern.get("count") or 0) + 1
        pattern.update(
            {
                "pattern_id": pattern_id,
                "count": count,
                "updated_at": timestamp,
                "intent": intent,
                "toolset": str(toolset or ""),
                "agent": str(agent or ""),
                "examples": examples[-5:],
            }
        )
        patterns[pattern_id] = pattern

        if count >= SUGGESTION_THRESHOLD and not _suggestion_exists(suggestions, pattern_id):
            profile = _suggestion_profile(str(toolset or ""), str(agent or ""), intent, examples[-5:])
            action = "Atualizar" if _skill_exists_for_name(profile["skill_name"]) or _skill_exists_for_toolset(toolset) else "Criar"
            title = str(profile.get("title") or f"{action} skill de {toolset or agent or 'procedimento'}")
            if action == "Atualizar":
                title = title.replace("Criar skill:", "Atualizar skill:", 1)
            suggestion = {
                "pattern_id": pattern_id,
                "skill_name": profile["skill_name"],
                "title": title,
                "reason": f"Padrao procedural apareceu {count} vezes para {agent or 'agente indefinido'}.",
                "toolset": str(toolset or ""),
                "agent": str(agent or ""),
                "intent": intent,
                "examples": examples[-5:],
                "status": "suggested",
                "created_at": timestamp,
            }
            suggestions.append(suggestion)

        return {
            "updated_at": timestamp,
            "observations": observations,
            "patterns": patterns,
            "suggestions": suggestions[-30:],
        }

    update_json_file(
        SKILL_LEARNING_PATH,
        _default_state(),
        updater,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    return suggestion


def pending_skill_suggestions(limit: int = 5) -> list[dict]:
    suggestions = [
        _enrich_suggestion(item)
        for item in load_skill_learning().get("suggestions", [])
        if isinstance(item, dict) and str(item.get("status") or "suggested") == "suggested"
    ]
    suggestions.sort(key=lambda item: float(item.get("created_at") or 0.0), reverse=True)
    return suggestions[: max(1, int(limit))]


def approve_pending_skill_suggestion(index: int = 1) -> str:
    selected = pending_skill_suggestions(limit=max(1, int(index)))
    if len(selected) < max(1, int(index)):
        return "Nao encontrei essa sugestao de skill pendente."

    suggestion = selected[max(1, int(index)) - 1]
    path = upsert_skill_from_suggestion(suggestion)
    pattern_id = str(suggestion.get("pattern_id") or "")

    def updater(state: dict) -> dict:
        current = _default_state()
        current.update(state or {})
        suggestions = []
        for item in current.get("suggestions", []):
            if isinstance(item, dict) and item.get("pattern_id") == pattern_id:
                updated = dict(item)
                updated["status"] = "approved"
                updated["approved_at"] = time.time()
                updated["skill_path"] = str(path)
                suggestions.append(updated)
            elif isinstance(item, dict):
                suggestions.append(item)
        current["suggestions"] = suggestions
        current["updated_at"] = time.time()
        return current

    update_json_file(
        SKILL_LEARNING_PATH,
        _default_state(),
        updater,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    return f"Skill procedural aprovada e salva em {path}."


def reject_pending_skill_suggestion(index: int = 1) -> str:
    selected = pending_skill_suggestions(limit=max(1, int(index)))
    if len(selected) < max(1, int(index)):
        return "Nao encontrei essa sugestao de skill pendente."

    suggestion = selected[max(1, int(index)) - 1]
    pattern_id = str(suggestion.get("pattern_id") or "")

    def updater(state: dict) -> dict:
        current = _default_state()
        current.update(state or {})
        suggestions = []
        for item in current.get("suggestions", []):
            if isinstance(item, dict) and item.get("pattern_id") == pattern_id:
                updated = dict(item)
                updated["status"] = "rejected"
                updated["rejected_at"] = time.time()
                suggestions.append(updated)
            elif isinstance(item, dict):
                suggestions.append(item)
        current["suggestions"] = suggestions
        current["updated_at"] = time.time()
        return current

    update_json_file(
        SKILL_LEARNING_PATH,
        _default_state(),
        updater,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    return "Sugestao de skill rejeitada."


def format_pending_skill_suggestions(limit: int = 3) -> str:
    suggestions = pending_skill_suggestions(limit=limit)
    if not suggestions:
        return "Nenhuma sugestao de skill procedural no momento."
    rows = []
    for item in suggestions:
        title = str(item.get("title") or "").strip()
        examples = [str(example).strip() for example in item.get("examples", []) if str(example).strip()]
        detail = f" exemplos: {', '.join(examples[:2])}" if examples else ""
        rows.append(f"{title}.{detail}")
    return "Sugestoes de skills: " + " ; ".join(rows)
