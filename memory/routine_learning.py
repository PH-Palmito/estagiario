from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from memory.json_store import read_json_file, update_json_file

ROUTINE_LEARNING_PATH = Path("memory") / "routine_learning.json"
MAX_OBSERVATIONS = 80
PAIR_WINDOW_SECONDS = 300
SUGGESTION_THRESHOLD = 3
IGNORED_INTENTS = {"respond", "repeat_last", "run_routine", "start_macro", "run_macro"}


def _compact(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _stable_signature(raw_action: dict) -> str:
    payload = {
        "intent": str(raw_action.get("intent") or "").strip(),
        "target": raw_action.get("target"),
    }
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _action_label(raw_action: dict, user_input: str) -> str:
    intent = str(raw_action.get("intent") or "").strip()
    target = raw_action.get("target")
    if isinstance(target, str) and target.strip():
        return f"{intent}: {target.strip()}"
    text = _compact(user_input)
    return f"{intent}: {text[:80]}" if text else intent


def _default_state() -> dict:
    return {"observations": [], "pairs": {}, "suggestions": []}


def load_routine_learning() -> dict:
    data = read_json_file(ROUTINE_LEARNING_PATH, _default_state(), validator=lambda value: isinstance(value, dict))
    state = _default_state()
    state.update(data or {})
    if not isinstance(state.get("observations"), list):
        state["observations"] = []
    if not isinstance(state.get("pairs"), dict):
        state["pairs"] = {}
    if not isinstance(state.get("suggestions"), list):
        state["suggestions"] = []
    return state


def _should_observe(raw_action: dict) -> bool:
    if not isinstance(raw_action, dict):
        return False
    intent = str(raw_action.get("intent") or "").strip()
    return bool(intent and intent not in IGNORED_INTENTS)


def _suggestion_exists(suggestions: list[dict], pair_id: str) -> bool:
    return any(isinstance(item, dict) and item.get("pair_id") == pair_id for item in suggestions)


def observe_routine_command(
    user_input: str,
    raw_action: dict,
    *,
    source: str = "turn",
    now: float | None = None,
) -> dict | None:
    if not _should_observe(raw_action):
        return None

    timestamp = time.time() if now is None else float(now)
    signature = _stable_signature(raw_action)
    label = _action_label(raw_action, user_input)
    suggestion: dict | None = None

    def updater(state: dict) -> dict:
        nonlocal suggestion
        current = _default_state()
        current.update(state or {})
        observations = [item for item in current.get("observations", []) if isinstance(item, dict)]
        pairs = dict(current.get("pairs") or {})
        suggestions = [item for item in current.get("suggestions", []) if isinstance(item, dict)]

        previous = observations[-1] if observations else None
        observation = {
            "at": timestamp,
            "source": str(source or "turn"),
            "input": _compact(user_input),
            "intent": str(raw_action.get("intent") or ""),
            "target": raw_action.get("target"),
            "signature": signature,
            "label": label,
        }
        observations.append(observation)
        observations = observations[-MAX_OBSERVATIONS:]

        if previous and timestamp - float(previous.get("at") or 0.0) <= PAIR_WINDOW_SECONDS:
            pair_id = f"{previous.get('signature')}+{signature}"
            pair = dict(pairs.get(pair_id) or {})
            count = int(pair.get("count") or 0) + 1
            pair.update(
                {
                    "pair_id": pair_id,
                    "count": count,
                    "updated_at": timestamp,
                    "steps": [
                        {"label": previous.get("label"), "intent": previous.get("intent"), "target": previous.get("target")},
                        {"label": label, "intent": raw_action.get("intent"), "target": raw_action.get("target")},
                    ],
                }
            )
            pairs[pair_id] = pair
            if count >= SUGGESTION_THRESHOLD and not _suggestion_exists(suggestions, pair_id):
                title = f"Criar rotina para {previous.get('label')} + {label}"
                suggestion = {
                    "pair_id": pair_id,
                    "title": title,
                    "reason": f"Essa sequencia apareceu {count} vezes recentemente. Posso sugerir uma rotina, mas nao vou automatizar sem aprovacao.",
                    "steps": pair["steps"],
                    "status": "suggested",
                    "created_at": timestamp,
                }
                suggestions.append(suggestion)

        return {
            "updated_at": timestamp,
            "observations": observations,
            "pairs": pairs,
            "suggestions": suggestions[-20:],
        }

    update_json_file(
        ROUTINE_LEARNING_PATH,
        _default_state(),
        updater,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    return suggestion


def pending_routine_suggestions(limit: int = 5) -> list[dict]:
    suggestions = [
        item
        for item in load_routine_learning().get("suggestions", [])
        if isinstance(item, dict) and str(item.get("status") or "suggested") == "suggested"
    ]
    suggestions.sort(key=lambda item: float(item.get("created_at") or 0.0), reverse=True)
    return suggestions[: max(1, int(limit))]


def format_pending_routine_suggestions(limit: int = 3) -> str:
    suggestions = pending_routine_suggestions(limit=limit)
    if not suggestions:
        return "Nenhuma sugestao de rotina por repeticao no momento."
    rows = [str(item.get("title") or "").strip() for item in suggestions if str(item.get("title") or "").strip()]
    return "Sugestoes de rotina: " + "; ".join(rows) + "."
