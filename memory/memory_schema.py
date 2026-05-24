from __future__ import annotations

import time
from typing import Any

MEMORY_SCHEMA_VERSION = "2026-05-12.1"

MEMORY_BUCKETS = {
    "profile": "Dados relativamente estaveis sobre o operador.",
    "preferences": "Preferencias explicitas de uso, tom, voz e fluxo de trabalho.",
    "operational_context": "Estado consolidado do momento: foco, pedidos recentes, apps, tarefas e lembretes.",
    "current_topic": "Assunto em andamento para follow-ups curtos.",
    "semantic_notes": "Notas longas, projetos, aprendizado e contexto de vault.",
    "execution_evidence": "Eventos reais do uso: entradas, rotas, comandos, duracao, falhas e saidas.",
    "research_sources": "Fontes consultadas ou recuperadas para sustentar respostas.",
}

CONFIDENCE_LEVELS = {"low", "medium", "high"}
SOURCE_KINDS = {"profile", "memory", "log", "doc", "vault", "web", "api", "user"}


def now_ts() -> float:
    return time.time()


def memory_record(
    *,
    bucket: str,
    key: str,
    value: Any,
    source: str,
    confidence: str = "medium",
    evidence: list[dict] | None = None,
    tags: list[str] | None = None,
    ttl_seconds: int | None = None,
) -> dict:
    clean_bucket = str(bucket or "").strip()
    clean_confidence = str(confidence or "").strip().lower()
    if clean_bucket not in MEMORY_BUCKETS:
        raise ValueError(f"bucket desconhecido: {clean_bucket}")
    if clean_confidence not in CONFIDENCE_LEVELS:
        raise ValueError(f"confidence invalida: {clean_confidence}")

    created_at = now_ts()
    payload = {
        "schema_version": MEMORY_SCHEMA_VERSION,
        "bucket": clean_bucket,
        "key": str(key or "").strip(),
        "value": value,
        "source": str(source or "").strip(),
        "confidence": clean_confidence,
        "evidence": evidence or [],
        "tags": [str(item).strip() for item in (tags or []) if str(item).strip()],
        "created_at": created_at,
        "updated_at": created_at,
    }
    if ttl_seconds is not None:
        payload["expires_at"] = created_at + max(0, int(ttl_seconds))
    return payload


def source_card(
    *,
    title: str,
    kind: str,
    excerpt: str,
    locator: str = "",
    confidence: str = "medium",
    retrieved_at: float | None = None,
) -> dict:
    clean_kind = str(kind or "").strip().lower()
    clean_confidence = str(confidence or "").strip().lower()
    if clean_kind not in SOURCE_KINDS:
        raise ValueError(f"source kind desconhecido: {clean_kind}")
    if clean_confidence not in CONFIDENCE_LEVELS:
        raise ValueError(f"confidence invalida: {clean_confidence}")
    return {
        "schema_version": MEMORY_SCHEMA_VERSION,
        "title": str(title or "").strip(),
        "kind": clean_kind,
        "excerpt": " ".join(str(excerpt or "").split()).strip(),
        "locator": str(locator or "").strip(),
        "confidence": clean_confidence,
        "retrieved_at": retrieved_at or now_ts(),
    }


def stance_packet(*, facts: list[str] | None = None, reading: str = "", limits: list[str] | None = None) -> dict:
    return {
        "schema_version": MEMORY_SCHEMA_VERSION,
        "facts": [str(item).strip() for item in (facts or []) if str(item).strip()],
        "reading": str(reading or "").strip(),
        "limits": [str(item).strip() for item in (limits or []) if str(item).strip()],
    }
