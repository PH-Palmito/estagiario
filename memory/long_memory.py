from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

from memory.json_store import read_json_file, update_json_file, write_json_atomic
from memory.obsidian_sync import sync_long_memory_note
from memory.supabase_sync import sync_memory_state_safely
from memory.ui_state import load_ui_state

LONG_MEMORY_PATH = Path("memory/long_memory.json")
MAX_ITEMS = 240
MAX_ITEMS_PER_CATEGORY = 60


def _compact(text: str) -> str:
    text = str(text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,:;-")


def _normalize_key(text: str) -> str:
    normalized = _compact(text).lower()
    normalized = re.sub(r"[^\w\s/-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^\w\s/-]", " ", str(text or "").lower())
    return {token for token in normalized.split() if len(token) >= 3}


def load_long_memory() -> dict:
    data = read_json_file(LONG_MEMORY_PATH, {}, validator=lambda value: isinstance(value, dict))
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return {
        "updated_at": data.get("updated_at", 0.0),
        "items": items,
    }


def _prune_items(items: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    for item in items:
        category = str(item.get("category", "context")).strip() or "context"
        buckets.setdefault(category, []).append(item)

    pruned = []
    for category_items in buckets.values():
        category_items.sort(key=lambda item: float(item.get("updated_at") or item.get("created_at") or 0), reverse=True)
        pruned.extend(category_items[:MAX_ITEMS_PER_CATEGORY])

    pruned.sort(key=lambda item: float(item.get("updated_at") or item.get("created_at") or 0), reverse=True)
    return pruned[:MAX_ITEMS]


def save_long_memory(data: dict) -> dict:
    payload = {
        "updated_at": time.time(),
        "items": _prune_items(list((data or {}).get("items") or [])),
    }
    write_json_atomic(LONG_MEMORY_PATH, payload, indent=2, trailing_newline=True)
    sync_memory_state_safely("long_memory", payload, category="memory")
    sync_long_memory_note(payload)
    return payload


def _update_long_memory(updater) -> dict:
    payload = update_json_file(
        LONG_MEMORY_PATH,
        {"updated_at": 0.0, "items": []},
        lambda data: {
            "updated_at": time.time(),
            "items": _prune_items(list((updater({"items": list((data or {}).get("items") or [])}) or {}).get("items") or [])),
        },
        validator=lambda value: isinstance(value, dict),
        indent=2,
        trailing_newline=True,
    )
    sync_memory_state_safely("long_memory", payload, category="memory")
    sync_long_memory_note(payload)
    return payload


def remember_fact(fact: str, category: str = "context", source: str = "manual", confidence: float = 0.75) -> bool:
    fact = _compact(fact)
    if len(fact) < 12:
        return False

    category = category if category in {"preference", "decision", "project", "future", "context"} else "context"
    key = _normalize_key(f"{category}:{fact}")
    now = time.time()

    created = False

    def remember(data: dict) -> dict:
        nonlocal created
        items = list(data.get("items") or [])
        for item in items:
            if item.get("id") == key:
                item["updated_at"] = now
                item["seen_count"] = int(item.get("seen_count") or 1) + 1
                item["source"] = source
                created = False
                return {"items": items}

        items.append(
            {
                "id": key,
                "category": category,
                "fact": fact,
                "source": source,
                "confidence": float(confidence),
                "created_at": now,
                "updated_at": now,
                "seen_count": 1,
            }
        )
        created = True
        return {"items": items}

    _update_long_memory(remember)
    return created


def _memory_candidate_from_text(text: str) -> tuple[str, str] | None:
    original = _compact(text)
    if len(original) < 12 or len(original) > 260:
        return None

    lower = original.lower()
    if any(lower.startswith(prefix) for prefix in {"abra ", "abre ", "feche ", "fecha ", "toque ", "pausar ", "pause "}):
        return None

    preference_markers = (
        "eu prefiro ",
        "prefiro ",
        "gosto que ",
        "nao gosto que ",
        "não gosto que ",
        "meu padrão é ",
        "meu padrao e ",
        "quero que o axel ",
        "quero que voce ",
        "quero que você ",
    )
    if any(marker in lower for marker in preference_markers):
        return "preference", original

    future_markers = (
        "adicionar a lista de futuros",
        "lista de futuros",
        "futuramente ",
        "mais pra frente ",
        "depois integrar ",
        "quero integrar ",
    )
    if any(marker in lower for marker in future_markers):
        return "future", original

    decision_markers = (
        "decidimos ",
        "ficou decidido ",
        "vamos fazer ",
        "a prioridade é ",
        "a prioridade e ",
        "o proximo passo é ",
        "o proximo passo e ",
    )
    if any(marker in lower for marker in decision_markers):
        return "decision", original

    project_markers = (
        "estou trabalhando em ",
        "o projeto ",
        "esse projeto ",
        "no axel ",
        "para o axel ",
    )
    if any(marker in lower for marker in project_markers):
        return "project", original

    explicit_memory = re.match(r"^(?:lembre|lembra|memorize|salve)\s+que\s+(.+)$", lower)
    if explicit_memory:
        return "context", original

    return None


def maybe_remember_from_user_text(text: str, source: str = "conversation") -> bool:
    candidate = _memory_candidate_from_text(text)
    if not candidate:
        return False
    category, fact = candidate
    return remember_fact(fact, category=category, source=source, confidence=0.7)


def curate_recent_ui_history(limit: int = 20) -> int:
    state = load_ui_state()
    history = state.get("history") if isinstance(state.get("history"), list) else []
    added = 0
    for item in history[-max(1, int(limit)):]:
        if not isinstance(item, dict):
            continue
        if str(item.get("role", "")).strip().lower() != "user":
            continue
        if maybe_remember_from_user_text(str(item.get("text", "")), source="ui-history"):
            added += 1
    return added


def format_long_memory(limit: int = 12) -> str:
    items = list(load_long_memory().get("items") or [])
    if not items:
        return "Memoria longa ainda vazia."
    items.sort(key=lambda item: float(item.get("updated_at") or item.get("created_at") or 0), reverse=True)
    rows = []
    for item in items[: max(1, int(limit))]:
        category = str(item.get("category", "context")).strip()
        fact = str(item.get("fact", "")).strip()
        if fact:
            rows.append(f"{category}: {fact}")
    return "Memoria longa: " + " ; ".join(rows) + "."


def search_long_memory(query: str, limit: int = 5) -> list[dict]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    now = time.time()
    scored = []
    for item in list(load_long_memory().get("items") or []):
        fact = str(item.get("fact", "")).strip()
        if not fact:
            continue
        item_tokens = _tokens(f"{item.get('category', '')} {fact}")
        overlap = query_tokens & item_tokens
        if not overlap:
            continue

        confidence = float(item.get("confidence") or 0.5)
        seen_count = min(5, int(item.get("seen_count") or 1))
        updated_at = float(item.get("updated_at") or item.get("created_at") or 0.0)
        age_days = max(0.0, (now - updated_at) / 86400.0) if updated_at else 365.0
        recency = max(0.0, 1.0 - min(age_days, 90.0) / 90.0)
        score = (len(overlap) * 2.0) + confidence + (seen_count * 0.15) + (recency * 0.5)
        scored.append(
            {
                **item,
                "score": round(score, 3),
                "matched_terms": sorted(overlap),
            }
        )

    scored.sort(key=lambda item: (float(item.get("score") or 0), float(item.get("updated_at") or 0)), reverse=True)
    return scored[: max(1, int(limit))]


def format_relevant_long_memory(query: str, limit: int = 4) -> str:
    matches = search_long_memory(query, limit=limit)
    if not matches:
        return "Nenhuma memoria longa relevante encontrada."
    rows = []
    for item in matches:
        category = str(item.get("category", "context")).strip()
        fact = str(item.get("fact", "")).strip()
        score = float(item.get("score") or 0.0)
        if fact:
            rows.append(f"{category}({score:.2f}): {fact}")
    return "Memorias relevantes: " + " ; ".join(rows) + "."
