from __future__ import annotations

import re

from memory.current_topic import load_current_topic
from memory.docs_context import search_docs_context
from memory.memory_schema import source_card
from memory.obsidian_sync import search_vault_context
from memory.operational_context import load_operational_context
from memory.profile import load_profile


def _query_with_topic(user_input: str) -> str:
    topic = load_current_topic() or {}
    parts = [str(user_input or "").strip()]
    for key in ("topic", "summary", "page_title", "last_user_question"):
        value = str(topic.get(key, "")).strip()
        if value:
            parts.append(value)
    return " ".join(parts).strip()


def _profile_sources(query: str) -> list[dict]:
    profile = load_profile() or {}
    normalized = str(query or "").lower()
    hits = []

    if any(term in normalized for term in {"perfil", "pedro", "objetivo", "stack", "faculdade", "curso"}):
        fields = []
        for key in ("nome", "curso", "trabalho_atual"):
            value = str(profile.get(key, "")).strip()
            if value:
                fields.append(f"{key}: {value}")
        foco = profile.get("foco_profissional") or []
        if foco:
            fields.append("foco: " + ", ".join(str(item) for item in foco[:4]))
        objetivos = profile.get("objetivos") or []
        if objetivos:
            fields.append("objetivos: " + "; ".join(str(item) for item in objetivos[:3]))
        if fields:
            hits.append(
                source_card(
                    title="Perfil do operador",
                    kind="profile",
                    excerpt=". ".join(fields),
                    locator="memory/profile.json",
                    confidence="high",
                )
            )
    return hits


def _operational_sources(query: str) -> list[dict]:
    context = load_operational_context() or {}
    summary = str(context.get("summary", "")).strip()
    if not summary:
        return []

    normalized = str(query or "").lower()
    if not any(term in normalized for term in {"agora", "contexto", "memoria", "memória", "preferencia", "preferência", "foco", "proximo", "próximo"}):
        return []

    return [
        source_card(
            title="Contexto operacional consolidado",
            kind="memory",
            excerpt=summary,
            locator="memory/operational_context.json",
            confidence="medium",
        )
    ]


def collect_research_sources(user_input: str, *, limit: int = 5) -> list[dict]:
    query = _query_with_topic(user_input)
    sources: list[dict] = []
    sources.extend(_profile_sources(query))
    sources.extend(_operational_sources(query))

    for item in search_docs_context(query, limit=2, max_chars=360):
        sources.append(
            source_card(
                title=str(item.get("title", "")).strip() or str(item.get("name", "")).strip(),
                kind="doc",
                excerpt=str(item.get("excerpt", "")).strip(),
                locator=str(item.get("path", "")).strip(),
                confidence="high",
            )
        )

    for item in search_vault_context(query, limit=2, max_chars=320):
        sources.append(
            source_card(
                title=str(item.get("name", "")).strip() or "Nota do vault",
                kind="vault",
                excerpt=str(item.get("excerpt", "")).strip(),
                locator=str(item.get("path", "")).strip(),
                confidence="medium",
            )
        )

    deduped = []
    seen = set()
    for source in sources:
        key = (
            re.sub(r"\s+", " ", str(source.get("title", "")).lower()).strip(),
            str(source.get("locator", "")).strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
        if len(deduped) >= max(1, int(limit)):
            break
    return deduped


def format_research_sources(user_input: str, *, limit: int = 5) -> str:
    sources = collect_research_sources(user_input, limit=limit)
    if not sources:
        return "Nenhuma fonte recuperada para esta pergunta."

    parts = []
    for index, source in enumerate(sources, start=1):
        title = str(source.get("title", "")).strip() or "Fonte"
        kind = str(source.get("kind", "")).strip()
        confidence = str(source.get("confidence", "")).strip()
        excerpt = str(source.get("excerpt", "")).strip()
        locator = str(source.get("locator", "")).strip()
        locator_text = f" [{locator}]" if locator else ""
        parts.append(f"{index}. {title} ({kind}, confianca {confidence}){locator_text}: {excerpt}")
    return " ".join(parts)
