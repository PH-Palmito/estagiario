from __future__ import annotations

import re

from core.router_utils import normalize_text
from memory.long_memory import curate_recent_ui_history, format_long_memory, maybe_remember_from_user_text
from memory.operational_context import (
    forget_operational_preference,
    format_operational_context,
    format_operational_memory,
    remember_operational_preference,
    save_operational_context,
)


def maybe_handle_operational_context_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    compact = re.sub(r"\s+", " ", normalized).strip()
    raw = str(user_input or "").strip()

    remember_match = re.match(
        r"^(?:lembre|lembra|memorize|salve|guarde)\s+(?:na\s+)?"
        r"(?:mem.ria operacional|contexto operacional|prefer.ncia operacional)\s+(?:que\s+)?(.+)$",
        raw,
        flags=re.I,
    )
    if remember_match:
        return remember_operational_preference(remember_match.group(1), kind="preference")

    note_match = re.match(
        r"^(?:anote|registre)\s+(?:no\s+)?(?:contexto operacional|mem.ria operacional)\s+(?:que\s+)?(.+)$",
        raw,
        flags=re.I,
    )
    if note_match:
        return remember_operational_preference(note_match.group(1), kind="note")

    forget_match = re.match(
        r"^(?:esque.a|esqueca|remova|apague)\s+(?:da\s+)?"
        r"(?:mem.ria operacional|contexto operacional|prefer.ncia operacional)\s+(.+)$",
        raw,
        flags=re.I,
    )
    if forget_match:
        return forget_operational_preference(forget_match.group(1))

    if normalized in {
        "minhas preferencias operacionais",
        "preferencias operacionais",
        "memoria operacional salva",
        "mostrar memoria operacional",
    }:
        return format_operational_memory()

    if normalized in {
        "qual meu foco",
        "qual o meu foco",
        "qual nosso foco",
        "o que estamos fazendo",
        "em que estamos agora",
        "resumir contexto",
        "resuma o contexto",
        "contexto atual",
        "contexto operacional",
        "qual o contexto atual",
        "o que voce sabe sobre mim agora",
    }:
        return format_operational_context()

    if normalized in {
        "atualizar contexto",
        "atualiza contexto",
        "atualizar contexto operacional",
        "recarregar contexto",
    }:
        payload = save_operational_context()
        summary = str(payload.get("summary", "")).strip()
        if summary:
            return "Contexto operacional atualizado. " + summary
        return "Contexto operacional atualizado."

    if ("context" in compact or "contr" in compact) and ("operac" in compact or "atual" in compact):
        return format_operational_context()

    if normalized in {
        "quais apps recentes",
        "apps recentes",
        "aplicativos recentes",
        "aplicativo recente",
        "sites recentes",
        "quais sites recentes",
        "topicos recentes",
    }:
        payload = save_operational_context()
        apps = payload.get("recent_apps") or []
        sites = payload.get("recent_sites") or []
        topics = payload.get("recent_topics") or []
        wants_apps = any(token in compact for token in {"app", "aplicativo"})
        wants_sites = "site" in compact
        wants_topics = any(token in compact for token in {"topico", "topicos"})

        if wants_apps and apps:
            return "Apps recentes: " + ", ".join(str(item) for item in apps[:4]) + "."
        if wants_apps:
            return "Ainda nao tenho apps recentes suficientes para resumir."

        if wants_sites and sites:
            return "Sites recentes: " + ", ".join(str(item) for item in sites[:4]) + "."
        if wants_sites:
            return "Ainda nao tenho sites recentes suficientes para resumir."

        if wants_topics and topics:
            return "Topicos recentes: " + ", ".join(str(item) for item in topics[:5]) + "."
        if wants_topics:
            return "Ainda nao tenho topicos recentes suficientes para resumir."

        parts = []
        if apps:
            parts.append("Apps: " + ", ".join(str(item) for item in apps[:4]) + ".")
        if sites:
            parts.append("Sites: " + ", ".join(str(item) for item in sites[:4]) + ".")
        if topics:
            parts.append("Topicos: " + ", ".join(str(item) for item in topics[:5]) + ".")
        return " ".join(parts) if parts else "Ainda nao tenho atividade recente suficiente para resumir."

    return None


def maybe_handle_long_memory_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    raw = str(user_input or "").strip()

    if normalized in {
        "memoria longa",
        "memoria longa do axel",
        "mostrar memoria longa",
        "listar memoria longa",
        "o que tem na memoria longa",
    }:
        return format_long_memory()

    if normalized in {
        "curar memoria",
        "curar memoria longa",
        "atualizar memoria longa",
        "crescer memoria longa",
    }:
        added = curate_recent_ui_history()
        save_operational_context()
        if added:
            return f"Memoria longa curada. Adicionei {added} item(ns) duraveis."
        return "Memoria longa revisada. Nao encontrei nada novo que merecesse virar memoria duravel."

    remember_match = re.match(
        r"^(?:lembre|lembra|memorize|salve)\s+(?:na\s+)?(?:mem.ria longa)\s+(?:que\s+)?(.+)$",
        raw,
        flags=re.I,
    )
    if remember_match:
        added = maybe_remember_from_user_text("lembre que " + remember_match.group(1), source="manual-long-memory")
        save_operational_context()
        return "Memoria longa atualizada." if added else "Isso ja estava na memoria longa, ou ficou curto demais para salvar."

    return None
