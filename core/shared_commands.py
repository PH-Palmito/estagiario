from __future__ import annotations

import re
from collections.abc import Callable

from core.axel_self_check import run_axel_self_check
from core.axel_brain_commands import format_axel_brain_insights
from core.capability_audit import format_real_capabilities_report
from core.humor_commands import current_personality_description
from core.project_health import format_latency_report, format_project_health_panel, recent_execution_summary
from core.router_utils import normalize_text
from memory.ui_state import load_ui_state, update_ui_state
from memory.voice_preferences import load_voice_preferences, update_voice_preferences
from memory.assistant_phrases import (
    ASSISTANT_PHRASE_CATEGORIES,
    generate_and_save_startup_phrases,
    load_learned_startup_phrases,
)
from memory.capability_ranking import format_capability_feedback, format_capability_rankings
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


def _personality_status() -> str:
    return current_personality_description(load_voice_preferences())


def _intent_judge_status() -> str:
    enabled = bool(load_ui_state().get("llm_intent_judge_enabled"))
    return _format_intent_judge_status(enabled)


def _format_intent_judge_status(enabled: bool) -> str:
    state = "ligado" if enabled else "desligado"
    return f"Juiz LLM de intenção: {state}."


def _intent_judge_change_for_request(normalized: str) -> tuple[bool, str] | None:
    on_commands = {
        "ligar juiz llm",
        "ativar juiz llm",
        "ligar juiz de intencao",
        "ativar juiz de intencao",
        "ligar juiz llm de intencao",
        "ativar juiz llm de intencao",
        "llm intent judge on",
    }
    off_commands = {
        "desligar juiz llm",
        "desativar juiz llm",
        "desligar juiz de intencao",
        "desativar juiz de intencao",
        "desligar juiz llm de intencao",
        "desativar juiz llm de intencao",
        "llm intent judge off",
    }
    toggle_commands = {
        "alternar juiz llm",
        "toggle juiz llm",
        "alternar juiz de intencao",
        "toggle intent judge",
    }
    if normalized in on_commands:
        return True, "Juiz LLM de intenção ligado."
    if normalized in off_commands:
        return False, "Juiz LLM de intenção desligado."
    if normalized in toggle_commands:
        enabled = not bool(load_ui_state().get("llm_intent_judge_enabled"))
        return enabled, "Juiz LLM de intenção ligado." if enabled else "Juiz LLM de intenção desligado."
    return None


def _personality_changes_for_request(normalized: str) -> tuple[dict, str] | None:
    if normalized in {"ligar personalidade", "ativar personalidade", "liga personalidade", "ativa personalidade"}:
        return {"assistant_personality_enabled": True}, "Personalidade ligada."
    if normalized in {
        "desligar personalidade",
        "desativar personalidade",
        "desliga personalidade",
        "desativa personalidade",
        "sem personalidade",
    }:
        return {"assistant_personality_enabled": False}, "Personalidade desligada."
    if normalized in {"ligar proatividade", "ativar proatividade", "liga proatividade", "ativa proatividade"}:
        return {"assistant_proactivity_enabled": True}, "Proatividade ligada."
    if normalized in {
        "desligar proatividade",
        "desativar proatividade",
        "desliga proatividade",
        "desativa proatividade",
        "sem proatividade",
    }:
        return {"assistant_proactivity_enabled": False}, "Proatividade desligada."
    return None


def _startup_phrase_category(normalized: str) -> str:
    if "noturna" in normalized or "noturno" in normalized or "dormir" in normalized or "sono" in normalized:
        return "night_sleep_prompt"
    if "curta" in normalized or "short" in normalized:
        return "short_ready"
    if "estudo" in normalized or "codigo" in normalized or "código" in normalized:
        return "study_code"
    return "computer_startup"


def _wants_all_phrase_categories(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in (
            "todas as frases",
            "frases do axel",
            "frases gerais",
            "todas frases",
        )
    )


def _join_startup_phrases_for_response(phrases: list[str] | tuple[str, ...]) -> str:
    cleaned = [str(phrase or "").strip().rstrip(".") for phrase in phrases if str(phrase or "").strip()]
    return "; ".join(cleaned)


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
            "Comandos comuns: /status, /usage, /autoteste, capacidades reais do axel, saude do axel, /insights, /skills, /help, /model, personalidade, juiz de intencao, /reset, /stop, /retry e /undo. "
            "No Telegram, comandos que mudam estado ficam limitados por seguranca."
        )

    if normalized in {"status", "status do axel", "axel status"}:
        return _recent_status()

    if normalized in {"usage", "uso", "uso do axel", "consumo", "custos", "latencia", "latencia do axel"}:
        return format_latency_report()

    if normalized in {
        "saude do axel",
        "saúde do axel",
        "checkup do axel",
        "check-up do axel",
        "diagnostico geral",
        "diagnóstico geral",
        "diagnostico do axel",
        "diagnóstico do axel",
    }:
        return format_project_health_panel()

    if normalized in {
        "autoteste",
        "autoteste do axel",
        "auto teste do axel",
        "self check",
        "selfcheck",
        "check rapido do axel",
        "check rápido do axel",
        "teste rapido do axel",
        "teste rápido do axel",
        "testar axel",
        "testar o axel",
        "verificar axel",
        "verificar o axel",
    }:
        return run_axel_self_check()

    if normalized in {"skills", "skills do axel", "capacidades", "capacidades do axel"}:
        catalog = format_skill_catalog()
        pending = format_pending_skill_suggestions()
        return catalog + " " + pending

    if normalized in {
        "capacidades reais",
        "capacidades reais do axel",
        "o que e real no axel",
        "o que é real no axel",
        "o que funciona de verdade",
        "fachada do axel",
        "auditoria de capacidades",
        "auditoria de capacidades do axel",
    }:
        return format_real_capabilities_report()

    if normalized in {"insights", "insights do axel", "insights da sessao"}:
        if runtime_state is not None:
            history = getattr(runtime_state, "axel_brain_history", None)
            brain = format_axel_brain_insights(history)
        else:
            brain = "Insights do AxelBrain: indisponiveis fora da sessao local."
        ranking = format_capability_feedback("all", limit=3)
        evaluation = format_task_evaluation_summary(limit=30)
        return " ".join([brain, ranking, evaluation])

    if normalized in {"model", "modelo", "modelo atual", "model status", "status do modelo"}:
        return _model_status()

    if normalized in {
        "personalidade",
        "personalidade atual",
        "personalidade do axel",
        "modo personalidade",
        "status da personalidade",
        "proatividade",
        "status da proatividade",
    }:
        return _personality_status()

    if normalized in {
        "frases de inicializacao",
        "frases de inicialização",
        "frases do axel",
        "frases gerais",
        "todas as frases",
        "frases noturnas",
        "frases de dormir",
        "frases de aviso noturno",
        "listar frases de inicializacao",
        "listar frases de inicialização",
        "listar frases do axel",
        "frases aprendidas de inicializacao",
        "frases aprendidas de inicialização",
    }:
        if _wants_all_phrase_categories(normalized):
            parts = []
            for category, info in ASSISTANT_PHRASE_CATEGORIES.items():
                phrases = load_learned_startup_phrases(category)
                if phrases:
                    joined = _join_startup_phrases_for_response(phrases[:4])
                    parts.append(f"{info['title']}: {joined}")
            if not parts:
                return "Ainda não há frases aprendidas."
            return "Frases aprendidas: " + " | ".join(parts) + "."
        category = _startup_phrase_category(normalized)
        phrases = load_learned_startup_phrases(category)
        title = ASSISTANT_PHRASE_CATEGORIES.get(category, {}).get("title", "inicialização")
        if not phrases:
            return f"Ainda não há frases de {title} aprendidas."
        joined = _join_startup_phrases_for_response(phrases[:8])
        return f"Frases aprendidas de {title}: {joined}."

    if normalized in {
        "gerar frases de inicializacao",
        "gerar frases de inicialização",
        "gerar frases do axel",
        "gerar todas as frases",
        "gerar frases gerais",
        "gerar frases noturnas",
        "gerar frases de dormir",
        "gerar frases de aviso noturno",
        "criar frases de inicializacao",
        "criar frases de inicialização",
        "renovar frases de inicializacao",
        "renovar frases de inicialização",
    } or normalized.startswith(
        (
            "gerar frases de inicializacao ",
            "gerar frases de inicialização ",
            "gerar frases do axel ",
            "gerar frases noturnas ",
            "gerar frases de dormir ",
        )
    ):
        if not allow_state_changes:
            return "Gerar frases altera memória local, então deixo isso apenas para o canal local."
        categories = list(ASSISTANT_PHRASE_CATEGORIES) if _wants_all_phrase_categories(normalized) else [_startup_phrase_category(normalized)]
        generated_parts = []
        for category in categories:
            accepted_for_category = generate_and_save_startup_phrases(category)
            if accepted_for_category:
                title = ASSISTANT_PHRASE_CATEGORIES.get(category, {}).get("title", category)
                joined_for_category = _join_startup_phrases_for_response(accepted_for_category[:4])
                if joined_for_category:
                    generated_parts.append(f"{title}: {joined_for_category}")
        accepted = generated_parts
        if not accepted:
            return "Tentei gerar novas frases, mas nenhuma passou no filtro de qualidade agora."
        return "Novas frases aprovadas: " + " | ".join(generated_parts) + "."

    if normalized in {
        "juiz llm",
        "juiz de intencao",
        "juiz llm de intencao",
        "status do juiz llm",
        "status do juiz de intencao",
        "intent judge",
        "llm intent judge",
    }:
        return _intent_judge_status()

    intent_judge_change = _intent_judge_change_for_request(normalized)
    if intent_judge_change:
        if not allow_state_changes:
            return "Juiz LLM de intenção só pode ser alterado no canal local. Aqui posso mostrar o status, mas não mudo essa preferência."
        enabled, message = intent_judge_change
        update_ui_state({"llm_intent_judge_enabled": enabled})
        return message + " " + _format_intent_judge_status(enabled)

    model_changes = _model_changes_for_request(normalized)
    if model_changes:
        if not allow_state_changes:
            return "Troca de modelo disponivel apenas no canal local. No Telegram, posso mostrar /model, mas nao altero preferencia."
        changes, message = model_changes
        update_voice_preferences(changes)
        if refresh_preferences:
            refresh_preferences()
        return message + " " + _model_status()

    personality_changes = _personality_changes_for_request(normalized)
    if personality_changes:
        if not allow_state_changes:
            return "Personalidade e proatividade so podem ser alteradas no canal local. Aqui posso mostrar o status, mas nao mudo essa preferencia."
        changes, message = personality_changes
        update_voice_preferences(changes)
        if refresh_preferences:
            refresh_preferences()
        return message + " " + _personality_status()

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
        return "Não encontrei uma ação anterior boa para tentar novamente agora."

    if normalized in {"undo", "desfazer", "voltar ultima acao", "desfazer ultima acao", "cancelar ultima acao"}:
        if undo_last:
            return undo_last()
        return "Ainda nao tenho undo real para a ultima acao executada. Posso cancelar pendencias abertas, mas nao vou fingir que desfiz algo ja aplicado."

    return None
