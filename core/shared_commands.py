from __future__ import annotations

import re
from collections.abc import Callable

from core.axel_brain_commands import format_axel_brain_insights
from core.project_health import format_latency_report, recent_execution_summary
from core.router_utils import normalize_text
from memory.voice_preferences import load_voice_preferences, update_voice_preferences
from memory.capability_ranking import format_capability_rankings
from memory.procedural_skills import format_skill_catalog
from memory.skill_learning import format_pending_skill_suggestions
from memory.task_evaluation import format_task_evaluation_summary


def _shared_normalize(user_input: str) -> str:
    text = normalize_text(user_input)
    return re.sub(r"^/+", "", text).strip()


def _recent_status() -> str:
    summary = recent_execution_summary(limit=80)
    errors = summary.get("recent_errors") or []
    no_match = summary.get("no_match_routes") or []
    slow = summary.get("slow_actions") or []
    parts = ["Status do Axel: operacional."]
    if errors:
        parts.append("Erros recentes: " + "; ".join(str(item) for item in errors[-2:]) + ".")
    else:
        parts.append("Sem erro recente no log operacional.")
    if no_match:
        latest = no_match[-1]
        parts.append(f"Ultima rota sem match claro: {latest.get('input', '')}.")
    if slow:
        latest_slow = slow[-1]
        parts.append(f"Acao lenta recente: {latest_slow.get('action', 'acao')} em {latest_slow.get('duration_ms', 0)} ms.")
    return " ".join(parts)


def _model_status() -> str:
    preferences = load_voice_preferences()
    provider = str(
        preferences.get("ai_text_provider")
        or preferences.get("chat_provider")
        or preferences.get("text_model_provider")
        or "auto"
    ).strip() or "auto"
    model = str(preferences.get("chat_model") or "qwen2.5:0.5b").strip() or "qwen2.5:0.5b"
    return f"Modelo do Axel: provedor {provider}; modelo local/chat {model}."


def _model_changes_for_request(normalized: str) -> tuple[dict, str] | None:
    if normalized in {"model local", "modelo local", "usar modelo local", "usar ia local"}:
        return {"ai_text_provider": "local", "chat_provider": "local", "text_model_provider": "local"}, "Preferencia de modelo alterada para local."
    if normalized in {"model cloud", "modelo cloud", "modelo nuvem", "usar nuvem", "usar gemini", "modelo gemini"}:
        return {"ai_text_provider": "cloud", "chat_provider": "cloud", "text_model_provider": "cloud"}, "Preferencia de modelo alterada para nuvem/Gemini quando disponivel."
    if normalized in {"model auto", "modelo auto", "modelo automatico", "usar modelo automatico", "usar nvidia", "model nvidia", "modelo nvidia"}:
        return {"ai_text_provider": "auto", "chat_provider": "auto", "text_model_provider": "auto"}, "Preferencia de modelo alterada para automatico, respeitando AxelBrain e fallback NVIDIA/Gemini/local."
    match = re.match(r"^(?:model|modelo)\s+(.+)$", normalized)
    if match:
        model = match.group(1).strip()
        if model and model not in {"status", "atual"}:
            return {"chat_model": model}, f"Modelo local/chat alterado para {model}."
    return None


def maybe_handle_shared_command(
    user_input: str,
    *,
    runtime_state=None,
    allow_state_changes: bool = False,
    clear_chat: Callable[[], None] | None = None,
    reset_ui: Callable[[], None] | None = None,
    stop_pending: Callable[[], None] | None = None,
    retry_last: Callable[[], str] | None = None,
    undo_last: Callable[[], str] | None = None,
    refresh_preferences: Callable[[], None] | None = None,
) -> str | None:
    normalized = _shared_normalize(user_input)
    if not normalized:
        return None

    if normalized in {"help", "ajuda", "comandos", "comandos do axel", "slash commands"}:
        return (
            "Comandos comuns: /status, /usage, /insights, /skills, /help, /model, /reset, /stop, /retry e /undo. "
            "No Telegram, comandos que mudam estado ficam limitados por seguranca."
        )

    if normalized in {"status", "status do axel", "axel status"}:
        return _recent_status()

    if normalized in {"usage", "uso", "uso do axel", "consumo", "custos", "latencia", "latencia do axel"}:
        return format_latency_report()

    if normalized in {"skills", "skills do axel", "capacidades", "capacidades do axel"}:
        catalog = format_skill_catalog()
        pending = format_pending_skill_suggestions()
        return catalog + " " + pending

    if normalized in {"insights", "insights do axel", "insights da sessao"}:
        if runtime_state is not None:
            history = getattr(runtime_state, "axel_brain_history", None)
            brain = format_axel_brain_insights(history)
        else:
            brain = "Insights do AxelBrain: indisponiveis fora da sessao local."
        ranking = format_capability_rankings("all", limit=3)
        evaluation = format_task_evaluation_summary(limit=30)
        return " ".join([brain, ranking, evaluation])

    if normalized in {"model", "modelo", "modelo atual", "model status", "status do modelo"}:
        return _model_status()

    model_changes = _model_changes_for_request(normalized)
    if model_changes:
        if not allow_state_changes:
            return "Troca de modelo disponivel apenas no canal local. No Telegram, posso mostrar /model, mas nao altero preferencia."
        changes, message = model_changes
        update_voice_preferences(changes)
        if refresh_preferences:
            refresh_preferences()
        return message + " " + _model_status()

    if normalized in {"reset", "resetar", "reset chat", "resetar conversa", "limpar conversa"}:
        if not allow_state_changes:
            return "Reset de conversa fica disponivel apenas no canal local."
        if clear_chat:
            clear_chat()
        if reset_ui:
            reset_ui()
        return "Conversa e estado visual temporario reiniciados. Memorias permanentes foram preservadas."

    if normalized in {"stop", "parar tarefa", "cancelar pendencia", "cancelar tarefa", "encerrar pendencia"}:
        if not allow_state_changes:
            return "Stop remoto limitado por seguranca. Para cancelar acao pendente no Telegram, responda cancelar quando houver uma confirmacao aberta."
        if stop_pending:
            stop_pending()
        return "Pendencias locais canceladas e modo conversa encerrado. Tarefas de sistema ja iniciadas nao foram forcadas a parar."

    if normalized in {"retry", "tentar novamente", "tente novamente", "tenta novamente", "de novo", "repetir ultimo", "repetir ultima acao"}:
        if retry_last:
            return retry_last()
        return "Nao encontrei uma acao anterior boa para tentar novamente agora."

    if normalized in {"undo", "desfazer", "voltar ultima acao", "desfazer ultima acao", "cancelar ultima acao"}:
        if undo_last:
            return undo_last()
        return "Ainda nao tenho undo real para a ultima acao executada. Posso cancelar pendencias abertas, mas nao vou fingir que desfiz algo ja aplicado."

    return None
