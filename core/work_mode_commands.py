from __future__ import annotations

import re
from collections.abc import Callable

from core.project_health import run_estagiario_preflight
from core.performance_mode import (
    PERFORMANCE_MODE_BALANCED,
    PERFORMANCE_MODE_ECONOMY,
    PERFORMANCE_MODE_PERFORMANCE,
    performance_settings,
)
from core.router_utils import normalize_text
from memory.auto_advances import load_auto_advances, save_auto_advances
from memory.operational_context import save_operational_context
from memory.ui_state import update_ui_state


def _pt_display_text(text: str) -> str:
    content = str(text or "")
    replacements = {
        "programacao": "programacao",
        "avancado": "avancado",
        "avancada": "avancada",
        "estagiario": "estagiario",
        "saudavel": "saudavel",
        "atencao": "atencao",
        "compilacao": "compilacao",
        "modulos": "modulos",
        "memorias": "memorias",
        "alteracoes": "alteracoes",
        "verificavel": "verificavel",
        "invalido": "invalido",
        "proximos": "proximos",
        "avancos": "avancos",
        "util": "util",
        "pagina": "pagina",
        "conteudo": "conteudo",
        "visao": "visao",
        "graficos": "graficos",
        "precisao": "precisao",
        "historico": "historico",
        "analises": "analises",
        "ultimas": "ultimas",
        "pratica": "pratica",
        "nao": "nao",
    }

    def replace(match):
        original = match.group(0)
        replacement = replacements.get(original.lower(), original)
        if original[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    pattern = r"\b(" + "|".join(re.escape(word) for word in sorted(replacements, key=len, reverse=True)) + r")\b"
    return re.sub(pattern, replace, content, flags=re.IGNORECASE)


def _compact_items(items, limit: int = 2) -> str:
    clean = [_pt_display_text(str(item).strip().rstrip(".")) for item in items or [] if str(item).strip()]
    if not clean:
        return ""
    return "; ".join(clean[: max(1, limit)])


def start_programming_mode(show_ui_hud: Callable[[], object]) -> str:
    show_ui_hud()
    update_ui_state(
        {
            "visible": True,
            "open_panels": ["contexto", "comandos"],
            "last_command": "modo programacao",
        }
    )
    advances = save_auto_advances(limit=3) or load_auto_advances() or []
    context = save_operational_context() or {}
    focus = _pt_display_text(str(context.get("current_focus", "")).strip())
    next_advances = context.get("next_advances") or [
        str(item.get("title", "")).strip()
        for item in advances
        if isinstance(item, dict) and str(item.get("title", "")).strip()
    ]
    open_tasks = context.get("open_tasks") or []
    bottlenecks = context.get("active_bottlenecks") or []
    preflight = run_estagiario_preflight()

    if preflight.get("compile_error"):
        first_step = "corrigir a falha de compilacao apontada no pre-flight"
    elif preflight.get("json_errors"):
        first_step = "corrigir o JSON invalido antes de evoluir recursos"
    elif next_advances:
        first_step = _pt_display_text(str(next_advances[0]).strip())
    elif open_tasks:
        first_step = _pt_display_text(str(open_tasks[0]).strip())
    else:
        first_step = "seguir pelo menor ajuste verificavel do projeto"

    health = "saudavel"
    if preflight.get("compile_error") or preflight.get("json_errors"):
        health = "precisa de atencao"

    parts = [f"Modo programacao do Estagiario ativado. Projeto {health}."]
    if focus:
        parts.append(f"Foco atual: {focus}.")
    if preflight.get("compile_error"):
        parts.append(f"Compilacao falhou: {preflight['compile_error']}.")
    else:
        parts.append(f"Compilacao ok em {len(preflight.get('compiled_modules') or [])} modulos-chave.")
    json_errors = preflight.get("json_errors") or []
    if json_errors:
        parts.append("Memorias com erro: " + _compact_items(json_errors, limit=2) + ".")
    else:
        parts.append(f"Memorias JSON ok: {preflight.get('json_ok_count', 0)} arquivos.")
    task_text = _compact_items(open_tasks, limit=2)
    if task_text:
        parts.append(f"Tarefas abertas: {task_text}.")
    if bottlenecks:
        parts.append("Gargalos: " + _compact_items(bottlenecks, limit=2) + ".")
    else:
        parts.append("Sem gargalos ativos.")
    parts.append(f"Estado de alteracoes: {preflight.get('change_summary')}.")
    parts.append("Painel de contexto e comandos abertos.")
    parts.append(f"Primeiro passo recomendado: {first_step}.")
    return " ".join(parts)


def set_performance_mode(mode: str, show_ui_hud: Callable[[], object] | None = None) -> str:
    settings = performance_settings(mode)
    update_ui_state(
        {
            "performance_mode": settings.mode,
            "performance_settings": settings.as_dict(),
            "last_command": f"modo {settings.mode}",
        }
    )
    if show_ui_hud is not None:
        show_ui_hud()

    if settings.mode == PERFORMANCE_MODE_ECONOMY:
        return (
            "Modo economia ativado. Vou reduzir animacoes do HUD, aumentar intervalo de polling "
            "e manter tarefas pesadas seguras em segundo plano."
        )
    if settings.mode == PERFORMANCE_MODE_PERFORMANCE:
        return "Modo performance ativado. HUD mais fluido e polling mais frequente."
    return "Modo equilibrado ativado. Voltei para o consumo normal do Axel."


def maybe_handle_work_mode_command(user_input: str, show_ui_hud: Callable[[], object]) -> str | None:
    normalized = normalize_text(user_input)
    programming_modes = {
        "modo programacao",
        "ativar modo programacao",
        "iniciar modo programacao",
        "comecar modo programacao",
        "rotina programacao",
        "modo dev",
        "modo desenvolvimento",
        "modo programacao avancado",
        "ativar modo programacao avancado",
        "iniciar modo programacao avancado",
        "rotina programacao avancada",
        "modo dev avancado",
        "modo desenvolvimento avancado",
    }
    if normalized in programming_modes:
        return start_programming_mode(show_ui_hud)
    if normalized in {
        "modo economia",
        "ativar modo economia",
        "modo leve",
        "ativar modo leve",
        "modo notebook fraco",
        "economizar recursos",
        "economizar bateria",
    }:
        return set_performance_mode(PERFORMANCE_MODE_ECONOMY, show_ui_hud)
    if normalized in {
        "modo equilibrado",
        "modo normal",
        "desativar modo economia",
        "sair do modo economia",
    }:
        return set_performance_mode(PERFORMANCE_MODE_BALANCED, show_ui_hud)
    if normalized in {
        "modo performance",
        "modo rapido",
        "ativar modo performance",
        "ativar modo rapido",
    }:
        return set_performance_mode(PERFORMANCE_MODE_PERFORMANCE, show_ui_hud)
    return None
