from __future__ import annotations

import re

from memory.curated_memory import load_curated_memory
from memory.long_memory import search_long_memory
from memory.session_index import search_session_turns


def _compact(text: str, limit: int = 260) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) > limit:
        return clean[: max(0, limit - 3)].rstrip() + "..."
    return clean


def _query_terms(query: str) -> set[str]:
    normalized = re.sub(r"[^\w\s/-]", " ", str(query or "").lower())
    return {token for token in normalized.split() if len(token) >= 3}


def _curated_hits(query: str) -> list[dict]:
    terms = _query_terms(query)
    memory = load_curated_memory()
    hits = []
    for name, text in (("core", memory.get("core", "")), ("user", memory.get("user", ""))):
        clean = str(text or "").strip()
        if not clean:
            continue
        text_terms = _query_terms(clean)
        overlap = sorted(terms & text_terms)
        score = len(overlap)
        if not terms or score:
            hits.append(
                {
                    "source": f"curated:{name}",
                    "summary": _compact(clean, limit=360),
                    "score": score,
                    "matched_terms": overlap,
                }
            )
    hits.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    return hits[:2]


def layered_memory_recall(
    query: str,
    *,
    semantic_limit: int = 4,
    session_limit: int = 4,
    include_transcript: bool = False,
) -> dict:
    clean_query = _compact(query, limit=220)
    long_matches = search_long_memory(clean_query, limit=semantic_limit)
    session_matches = search_session_turns(clean_query, limit=session_limit)

    semantic = []
    for item in long_matches:
        source = str(item.get("source") or "sem fonte").strip()
        confidence = float(item.get("confidence") or 0.0)
        validity = str(item.get("validity") or "durable").strip()
        reason = str(item.get("reason") or "").strip()
        semantic.append(
            {
                "source": f"long_memory:{item.get('category', 'context')}",
                "origin": source,
                "confidence": confidence,
                "validity": validity,
                "reason": reason,
                "summary": _compact(str(item.get("fact", "")), limit=280),
                "score": float(item.get("score") or 0.0),
                "matched_terms": list(item.get("matched_terms") or []),
            }
        )

    sessions = []
    for item in session_matches:
        sessions.append(
            {
                "source": f"session:{item.get('session_id', '')}:{item.get('id', '')}",
                "role": str(item.get("role", "")),
                "summary": _compact(str(item.get("text", "")), limit=240),
                "score": round(abs(float(item.get("rank") or 0.0)), 3),
                "created_at": float(item.get("created_at") or 0.0),
            }
        )

    expanded = []
    for item in semantic[:2]:
        meta = f"fonte {item.get('origin', 'sem fonte')}, conf {float(item.get('confidence') or 0):.2f}, validade {item.get('validity') or 'durable'}"
        expanded.append(f"{item['source']} ({meta}) -> {item['summary']}")
    for item in sessions[:2]:
        expanded.append(f"{item['source']} {item.get('role', '')} -> {item['summary']}")

    transcript = []
    if include_transcript:
        for item in session_matches[: max(1, min(3, session_limit))]:
            transcript.append(
                {
                    "source": f"session:{item.get('session_id', '')}:{item.get('id', '')}",
                    "role": str(item.get("role", "")),
                    "text": str(item.get("text", "")).strip(),
                    "created_at": float(item.get("created_at") or 0.0),
                }
            )

    return {
        "query": clean_query,
        "curated": _curated_hits(clean_query),
        "semantic": semantic,
        "expanded_summary": expanded,
        "transcript": transcript,
        "has_results": bool(semantic or sessions or transcript),
    }


def format_layered_memory_recall(query: str, *, include_transcript: bool = False) -> str:
    recall = layered_memory_recall(query, include_transcript=include_transcript)
    if not recall.get("has_results") and not recall.get("curated"):
        return "Nao encontrei memoria relevante em camadas sobre isso."

    parts = [f"Recall em camadas para: {recall.get('query', '')}."]

    curated = recall.get("curated") or []
    if curated:
        parts.append("Memoria curta: " + " | ".join(item["summary"] for item in curated[:2]) + ".")

    semantic = recall.get("semantic") or []
    if semantic:
        rows = []
        for item in semantic[:3]:
            reason = str(item.get("reason") or "").strip()
            reason_text = f", motivo {reason}" if reason else ""
            rows.append(
                f"{item['source']}({float(item.get('score') or 0):.2f}, "
                f"fonte {item.get('origin') or 'sem fonte'}, "
                f"conf {float(item.get('confidence') or 0):.2f}, "
                f"validade {item.get('validity') or 'durable'}{reason_text}): {item['summary']}"
            )
        parts.append("Busca semantica/local: " + " ; ".join(rows) + ".")

    expanded = recall.get("expanded_summary") or []
    if expanded:
        parts.append("Resumo expandido: " + " ; ".join(expanded[:4]) + ".")

    transcript = recall.get("transcript") or []
    if transcript:
        rows = [f"{item['role']}: {_compact(item['text'], limit=360)}" for item in transcript[:3]]
        parts.append("Transcript original: " + " | ".join(rows) + ".")
    elif include_transcript:
        parts.append("Transcript original: nenhum trecho bruto encontrado.")

    return " ".join(parts)
