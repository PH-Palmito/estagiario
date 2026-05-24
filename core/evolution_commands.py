from __future__ import annotations

from core.router_utils import normalize_text
from memory.auto_advances import load_auto_advances, save_auto_advances
from memory.bottlenecks import load_bottlenecks, save_bottlenecks
from memory.patch_proposals import load_patch_proposals, save_patch_proposals


def maybe_handle_auto_advance_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "atualizar proximos avancos",
        "gerar proximos avancos",
        "atualizar avancos",
        "gerar avancos",
    }:
        advances = save_auto_advances()
        titles = "; ".join(item.get("title", "") for item in advances[:3])
        if titles:
            return f"Atualizei os proximos avancos do Axel. Destaques: {titles}."
        return "Atualizei os proximos avancos do Axel."

    if normalized in {
        "proximos avancos",
        "mostrar proximos avancos",
        "quais sao os proximos avancos",
    }:
        advances = load_auto_advances()
        if not advances:
            return "Ainda nao encontrei proximos avancos para sugerir."
        lines = [f"{index + 1}. {item.get('title', '')}" for index, item in enumerate(advances[:5])]
        return "Proximos avancos do Axel: " + "; ".join(lines)

    return None


def maybe_handle_bottleneck_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "atualizar gargalos",
        "analisar gargalos",
        "gerar gargalos",
    }:
        items = save_bottlenecks()
        if not items:
            return "Atualizei os gargalos, mas ainda nao encontrei sinais relevantes."
        top = "; ".join(item.get("title", "") for item in items[:3])
        return f"Atualizei os gargalos do Axel. Destaques: {top}."

    if normalized in {
        "mostrar gargalos",
        "quais sao os gargalos",
        "gargalos",
        "diagnostico de gargalos",
    }:
        items = load_bottlenecks()
        if not items:
            return "Ainda nao encontrei gargalos relevantes no uso recente."
        parts = []
        for item in items[:4]:
            title = str(item.get("title", "")).strip()
            count = int(item.get("count", 0) or 0)
            if title:
                parts.append(f"{title} ({count})")
        return "Gargalos detectados: " + "; ".join(parts)

    return None


def maybe_handle_patch_proposal_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "gerar propostas de patch",
        "atualizar propostas de patch",
        "gerar patch proposals",
        "propor patches",
    }:
        items = save_patch_proposals()
        if not items:
            return "Atualizei as propostas de patch, mas ainda nao encontrei algo forte o suficiente."
        top = "; ".join(item.get("title", "") for item in items[:3])
        return f"Atualizei as propostas de patch do Axel. Destaques: {top}."

    if normalized in {
        "mostrar propostas de patch",
        "propostas de patch",
        "patch proposals",
        "quais patches o axel sugere",
    }:
        items = load_patch_proposals()
        if not items:
            return "Ainda nao encontrei propostas de patch relevantes."
        parts = []
        for item in items[:3]:
            title = str(item.get("title", "")).strip()
            files = item.get("files") or []
            if title:
                parts.append(f"{title} em {', '.join(str(file) for file in files[:3])}")
        return "Propostas de patch do Axel: " + "; ".join(parts)

    return None
