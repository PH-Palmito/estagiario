import subprocess
import sys
import time
from copy import deepcopy
import difflib
import json
from pathlib import Path
import re

from core.context_resolver import resolve_params
from core.executor import execute
from core.normalizer import normalize_action
from core.planner import looks_like_multi_step_request, plan_actions, split_local_steps
from core.router import detect_create_macro_start, normalize_text, route
from core.runtime_state import RuntimeState
from core.validator import validate_command
from core.voice_command_classifier import normalize_voice_command
from llm.chat import chat_response, clear_chat_history
from memory.approval_gate import approve_current_proposal, load_approval_gate, reject_current_proposal, sync_approval_gate
from memory.action_candidates import (
    approve_first_action_candidate,
    load_action_candidates,
    reject_first_action_candidate,
    save_action_candidates,
)
from memory.auto_advances import load_auto_advances, save_auto_advances
from memory.bottlenecks import load_bottlenecks, save_bottlenecks
from memory.codex_bridge import load_codex_request, save_codex_request
from memory.codex_channel import load_codex_channel, save_codex_channel
from memory.codex_notifications import consume_codex_suggestion, reset_codex_suggestion_memory
from memory.codex_outbox import (
    clear_codex_outbox_pending,
    enqueue_codex_implementation_request,
    enqueue_current_codex_message,
    load_codex_outbox,
    mark_next_codex_message_sent,
    sync_codex_outbox,
)
from memory.codex_inbox import add_codex_inbox_item, clear_codex_inbox, load_codex_inbox
from memory.codex_implementation_request import (
    load_codex_implementation_request,
    save_codex_implementation_request,
)
from memory.execution_packages import load_execution_package, save_execution_package
from memory.execution_log import append_execution_log
from memory.implementation_handoff import load_implementation_handoff, save_implementation_handoff
from memory.handoff_applications import (
    load_handoff_application,
    mark_handoff_applied,
    mark_handoff_failed,
    mark_handoff_started,
    mark_handoff_validated,
    sync_handoff_application,
)
from memory.handoff_retry_plan import load_handoff_retry_plan, save_handoff_retry_plan
from memory.handoff_validation import load_handoff_validation, save_handoff_validation
from memory.macros import add_macro
from memory.operational_context import (
    format_operational_context,
    load_operational_context,
    save_operational_context,
)
from memory.patch_proposals import load_patch_proposals, save_patch_proposals
from memory.piper_voice_manager import (
    apply_piper_voice,
    download_piper_voice,
    list_piper_voices,
)
from memory.session import clear
from memory.self_evolution import load_self_evolution_plan, save_self_evolution_plan
from memory.ui_commands import dequeue_ui_command
from memory.ui_state import append_ui_history, load_ui_state, reset_ui_state, update_ui_state
from memory.verification_runs import (
    load_verification_runs,
    mark_verification_failed,
    mark_verification_success,
    retry_verification,
    start_verification,
    sync_verification_runs,
)
from memory.voice_corrections import apply_voice_correction, remember_voice_correction
from memory.voice_preferences import load_voice_preferences, update_voice_preferences
from memory.voice_profiles import apply_voice_profile, list_voice_profiles
from memory.tts_pronunciations import (
    get_tts_pronunciation,
    load_tts_pronunciations,
    remove_tts_pronunciation,
    set_tts_pronunciation,
)
from tools.smart_open_tools import smart_open_needs_choice
from tools.system_tools import type_text
from voice.windows_voice import (
    HOTKEY_NAME,
    HOTWORD_LISTENING_ENABLED,
    consume_hotkey_press,
    consume_toggle_listening_hotkey_press,
    format_input_devices,
    get_active_input_device_info,
    list_input_devices,
    listen_conversation_once,
    listen_for_hotword,
    listen_once,
    play_activation_sound,
    prime_piper_cache,
    run_audio_diagnostic,
    speak,
    TOGGLE_LISTENING_HOTKEY_NAME,
)


runtime_state = RuntimeState()
pending_command = None
pending_smart_open_choice = None
pending_smart_open_invalid_attempts = 0
voice_status = None
hotword_ui_enabled = False
rendered_status_line = ""
conversation_mode = False
conversation_ready_announced = False
dictation_mode = False
dictation_ready_announced = False
direct_response_ready_announced = False
last_voice_text = ""
ui_hud_started = False
last_improvement_refresh = 0.0
repeat_listen_until = 0.0
UI_HISTORY_MAX_ITEMS = 40

creating_macro = False
macro_name = None
macro_steps = []
VOICE_PREFERENCES = load_voice_preferences()


def log_execution_event(event_type: str, **payload):
    try:
        append_execution_log(event_type, payload)
    except Exception:
        pass


def process_action(raw_action: dict):
    if not isinstance(raw_action, dict):
        log_execution_event("action_invalid", reason="raw_action_not_dict", raw_action=str(raw_action))
        return "Acao invalida."

    command = normalize_action(raw_action)
    command = resolve_params(command, runtime_state)
    log_execution_event(
        "action_processed",
        intent=raw_action.get("intent"),
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        source=getattr(command, "source", ""),
    )

    ok, error = validate_command(command)
    if not ok:
        log_execution_event(
            "action_validation_failed",
            action=getattr(command, "action", ""),
            params=getattr(command, "params", {}),
            error=error,
        )
        return error

    return command


def action_progress_message(command) -> str | None:
    messages = {
        "image_analyze_screen": "Análise de imagem pausada por enquanto.",
        "image_analyze_screen_graph": "Análise de imagem pausada por enquanto.",
        "image_analyze_browser": "Análise de imagem pausada por enquanto.",
        "image_analyze_clipboard": "Análise de imagem pausada por enquanto.",
        "image_analyze": "Análise de imagem pausada por enquanto.",
        "vision_answer_question": "Consultando a última análise salva...",
        "browser_describe_screen": "Lendo a tela...",
        "browser_explain_screen": "Analisando o conteúdo principal...",
        "browser_summarize_screen": "Resumindo a tela...",
        "browser_investment_snapshot": "Analisando seus investimentos...",
        "browser_open_wallet_and_summarize": "Abrindo e analisando sua carteira...",
        "investment_memory_summary": "Consultando a memória local da carteira...",
        "investment_memory_answer": "Consultando a memória local da carteira...",
        "investment_memory_status": "Verificando a memória local da carteira...",
        "browser_read_selection": "Lendo o texto selecionado...",
        "browser_read_selected_products": "Lendo os produtos selecionados...",
        "browser_translate_last_selection": "Traduzindo o último texto selecionado...",
        "browser_translate_selection": "Traduzindo o texto selecionado...",
        "browser_read_more": "Lendo mais conteúdo da página...",
        "browser_find": "Procurando na página...",
        "browser_search_site": "Pesquisando no site...",
        "code_inspect_workspace": "Inspecionando o código do projeto...",
        "code_inspect_target": "Inspecionando o arquivo solicitado...",
        "code_inspect_selection": "Inspecionando o código selecionado...",
    }
    return messages.get(getattr(command, "action", ""))


def show_action_progress(command, voice_mode: bool = False):
    message = action_progress_message(command)
    if not message:
        return
    terminal_print(f"IA: {message}")
    append_ui_history("assistant", message, max_items=UI_HISTORY_MAX_ITEMS)
    refresh_ui_runtime_state({"status": "PROCESSANDO", "last_response": message})
    if voice_mode:
        speak(message)


def execute_command(command, voice_mode: bool = False):
    show_action_progress(command, voice_mode=voice_mode)
    started_at = time.time()
    log_execution_event(
        "command_execute_start",
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        voice_mode=voice_mode,
    )
    result = execute(command)
    runtime_state.update(command, result)
    log_execution_event(
        "command_execute_end",
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        result=result,
        voice_mode=voice_mode,
        duration_ms=round((time.time() - started_at) * 1000, 2),
    )
    return result


def is_confirmation_yes(text: str) -> bool:
    return normalize_text(text) in {"sim", "s", "confirmar", "ok", "pode", "pode sim"}


def is_confirmation_no(text: str) -> bool:
    normalized = normalize_text(text)
    cancel_words = {
        "nao",
        "nÃ£o",
        "n",
        "cancelar",
        "cancela",
        "cancele",
        "cancelar isso",
        "deixa",
        "deixa pra la",
        "deixa para la",
        "deixa quieto",
        "esquece",
        "sair",
        "voltar",
    }
    return normalized in cancel_words or normalized.startswith(("cancela ", "cancelar ", "cancele "))


def smart_open_choice_kind(text: str):
    text = normalize_text(text)
    compact = re.sub(r"[^a-z0-9]", "", text)

    app_aliases = {
        "app",
        "aplicativo",
        "programa",
        "exe",
        "eapp",
        "ehapp",
        "ap",
        "ape",
        "epe",
        "ep",
        "apepe",
    }
    site_aliases = {
        "site",
        "saite",
        "sait",
        "web",
        "pagina",
        "page",
        "navegador",
        "esite",
        "ehsite",
    }

    if "aplicativo" in text or "programa" in text:
        return "app"

    if "site" in text or "pagina" in text or "web" in text:
        return "site"

    if compact in app_aliases:
        return "app"

    if compact in site_aliases:
        return "site"

    app_score = max(
        (difflib.SequenceMatcher(None, compact, alias).ratio() for alias in app_aliases),
        default=0,
    )
    site_score = max(
        (difflib.SequenceMatcher(None, compact, alias).ratio() for alias in site_aliases),
        default=0,
    )

    if app_score >= 0.78 and app_score > site_score:
        return "app"

    if site_score >= 0.78 and site_score > app_score:
        return "site"

    return None


def should_style_response(message: str) -> bool:
    if not message or "\n" in message or len(message) > 120:
        return False

    prefixes_to_keep = (
        "Texto selecionado:",
        "Traduzi:",
        "Li selecionado:",
        "Consegui ler",
        "Vejo na tela:",
        "Diagnostico",
        "Correcoes de voz:",
        "Rotinas:",
        "Macros:",
        "Arquivo",
        "Erro",
    )
    return not message.startswith(prefixes_to_keep)


def style_response(message: str) -> str:
    assistant_style = str(VOICE_PREFERENCES.get("assistant_style", "")).strip().lower()
    if assistant_style not in {"jarvis", "assistente", "elegante"}:
        humor_style = str(VOICE_PREFERENCES.get("assistant_humor_style", "")).strip().lower()
        if bool(VOICE_PREFERENCES.get("assistant_humor_enabled", True)) and humor_style == "jarvis":
            assistant_style = "jarvis"
    if assistant_style not in {"jarvis", "assistente", "elegante"}:
        return message

    if not bool(VOICE_PREFERENCES.get("assistant_brief_confirmations", True)):
        return message

    if not should_style_response(message):
        return message

    if assistant_style in {"assistente", "elegante"}:
        replacements = {
            "Abrindo spotify.": "Abrindo Spotify.",
            "Abrindo chrome.": "Abrindo Chrome.",
            "Abrindo code.": "Abrindo VS Code.",
            "Fechando spotify.": "Fechando Spotify.",
            "Fechando code.": "Fechando VS Code.",
            "Nao entendi.": "Não captei com precisão.",
            "Pode repetir?": "Pode repetir, por favor?",
            "Nao identifiquei o comando.": "Não identifiquei o comando.",
            "Escuta pausada.": "Escuta pausada.",
            "Escuta retomada.": "Escuta retomada.",
            "Acao cancelada.": "Ação cancelada.",
        }
        if message in replacements:
            return replacements[message]

        action_prefixes = (
            "Abrindo ",
            "Fechando ",
            "Maximizando ",
            "Minimizando ",
            "Restaurando ",
            "Focando ",
            "Pesquisando ",
            "Rolando ",
            "Procurando ",
            "Tocando ",
            "Pausando ",
        )
        if message.startswith(action_prefixes):
            if assistant_style == "elegante":
                return message
            return f"Pronto. {message}"

        return message

    replacements = {
        "Abrindo spotify.": "Certamente. Abrindo Spotify.",
        "Abrindo chrome.": "Certamente. Abrindo Chrome.",
        "Abrindo code.": "Certamente. Abrindo VS Code.",
        "Fechando spotify.": "Encerrando Spotify.",
        "Fechando code.": "Encerrando VS Code.",
        "Nao entendi.": "Não captei com precisão.",
        "Pode repetir?": "Pode repetir com calma?",
        "Nao identifiquei o comando.": "Esse comando não ficou claro para mim.",
        "Escuta pausada.": "Escuta em pausa.",
        "Escuta retomada.": "Escuta restabelecida.",
        "Acao cancelada.": "Ação cancelada.",
        "Pode falar.": "Estou ouvindo.",
        "Pode falar...": "Estou ouvindo.",
        "Pode responder...": "Pode responder.",
        "Encerrando.": "Encerrando por agora.",
        "Modo conversa encerrado. Voltei para comandos.": "Modo conversa encerrado. Voltei aos comandos.",
        "Responda com sim ou nao.": "Preciso apenas de sim ou não.",
        "Responda com 'sim' ou 'nao'.": "Preciso apenas de sim ou não.",
        "Responda com app, site ou cancelar.": "Responda com app, site ou cancelar.",
        "Responda com 'app' ou 'site'.": "Responda com app ou site.",
        "Ok, nao abri.": "Certo. Não abri.",
        "Nao consegui entender a resposta. Cancelei essa pergunta.": "Não consegui confirmar a resposta. Cancelei essa pergunta.",
        "Nada para repetir.": "Não há nada recente para repetir.",
        "Passo adicionado.": "Passo registrado.",
    }
    if message in replacements:
        return replacements[message]

    action_prefixes = (
        "Abrindo ",
        "Fechando ",
        "Maximizando ",
        "Minimizando ",
        "Restaurando ",
        "Focando ",
        "Pesquisando ",
        "Rolando ",
        "Procurando ",
        "Tocando ",
        "Pausando ",
    )
    if message.startswith(action_prefixes):
        return f"Pronto, {message[0].lower() + message[1:]}"

    return message


def output_response(message: str, voice_mode: bool):
    global repeat_listen_until
    global direct_response_ready_announced

    styled_message = style_response(message)
    log_execution_event(
        "assistant_output",
        message=styled_message,
        voice_mode=voice_mode,
        mode=current_ui_mode_label(),
    )
    terminal_print(f"IA: {styled_message}")
    append_ui_history("assistant", styled_message, max_items=UI_HISTORY_MAX_ITEMS)
    refresh_ui_runtime_state({"last_response": styled_message})
    refresh_improvement_brain()
    if voice_mode and any(
        phrase in styled_message
        for phrase in (
            "Não captei com precisão",
            "Não identifiquei o comando",
            "Pode repetir",
        )
    ):
        repeat_listen_until = time.time() + 8.0
        direct_response_ready_announced = False

    quiet_messages = {
        "Nao entendi.",
        "Pode repetir?",
        "Nao identifiquei o comando.",
    }

    if voice_mode and styled_message not in quiet_messages:
        speak(styled_message)


def common_tts_cache_phrases() -> list[str]:
    phrases = [
        str(
            VOICE_PREFERENCES.get(
                "startup_voice_greeting",
                "Modo voz ativado. Pronto para trabalhar.",
            )
        ).strip(),
        "Pode falar.",
        "Pode falar...",
        "Pode responder...",
        "Nao entendi.",
        "Pode repetir?",
        "Nao identifiquei o comando.",
        "Abrindo Spotify.",
        "Fechando Spotify.",
        "Abrindo Chrome.",
        "Abrindo VS Code.",
        "Fechando VS Code.",
        "Escuta pausada.",
        "Escuta retomada.",
        "Acao cancelada.",
        "Encerrando.",
    ]
    styled = [style_response(phrase) for phrase in phrases if phrase]
    return list(dict.fromkeys(styled))


def warm_common_tts_cache_async():
    if str(VOICE_PREFERENCES.get("tts_engine", "")).strip().lower() != "piper":
        return

    if not bool(VOICE_PREFERENCES.get("tts_cache_enabled", True)):
        return

    if not bool(VOICE_PREFERENCES.get("tts_warm_cache_on_startup", True)):
        return

    try:
        from threading import Thread

        Thread(
            target=lambda: prime_piper_cache(common_tts_cache_phrases()),
            daemon=True,
        ).start()
    except Exception:
        pass


def refresh_voice_preferences():
    VOICE_PREFERENCES.clear()
    VOICE_PREFERENCES.update(load_voice_preferences())

    try:
        import voice.windows_voice as windows_voice

        windows_voice.VOICE_PREFERENCES.clear()
        windows_voice.VOICE_PREFERENCES.update(VOICE_PREFERENCES)
    except Exception:
        pass

    try:
        import llm.chat as chat

        chat.refresh_preferences()
    except Exception:
        pass


def current_assistant_style_label() -> str:
    assistant_style = str(VOICE_PREFERENCES.get("assistant_style", "")).strip().lower()
    if assistant_style in {"jarvis", "assistente", "elegante"}:
        return assistant_style

    humor_enabled = bool(VOICE_PREFERENCES.get("assistant_humor_enabled", True))
    humor_style = str(VOICE_PREFERENCES.get("assistant_humor_style", "")).strip().lower()
    if humor_enabled and humor_style:
        return humor_style

    return "padrao"


def current_voice_profile_label() -> str:
    for key in (
        "voice_profile_name",
        "voice_profile",
        "piper_voice",
        "tts_voice",
        "tts_speaker",
    ):
        value = str(VOICE_PREFERENCES.get(key, "")).strip()
        if value:
            return value
    return "faber"


def current_ui_mode_label() -> str:
    if dictation_mode:
        return "ditado"
    if conversation_mode:
        return "conversa"
    if is_waiting_for_direct_response():
        return "resposta"
    return "comando"


def command_preview(command) -> str:
    if command is None:
        return ""

    action = getattr(command, "action", None)
    params = getattr(command, "params", None)

    if action and isinstance(params, dict) and params:
        summary = ", ".join(f"{key}={value}" for key, value in list(params.items())[:3])
        return f"{action} ({summary})"

    if action:
        return str(action)

    return str(command)


def refresh_ui_runtime_state(extra: dict | None = None):
    try:
        active_device = get_active_input_device_info() or {}
        patch = {
            "assistant_name": "Axel",
            "status": voice_status or "INATIVO",
            "mode": current_ui_mode_label(),
            "microphone": active_device.get("name", ""),
            "assistant_style": current_assistant_style_label(),
            "voice_profile": current_voice_profile_label(),
            "hotword_enabled": bool(hotword_ui_enabled),
            "conversation_mode": bool(conversation_mode),
            "dictation_mode": bool(dictation_mode),
            "last_command": command_preview(runtime_state.last_command),
        }
        if extra:
            patch.update(extra)
        update_ui_state(patch)
    except Exception:
        pass


def launch_ui_hud():
    global ui_hud_started

    state = load_ui_state()
    if ui_hud_started and state.get("visible", False):
        refresh_ui_runtime_state({"visible": True})
        return

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    python_exec = str(pythonw if pythonw.exists() else Path(sys.executable))

    try:
        subprocess.Popen(
            [python_exec, "-m", "ui.assistant_hud"],
            cwd=str(Path(__file__).resolve().parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ui_hud_started = True
    except Exception:
        return

    refresh_ui_runtime_state({"visible": True})


def show_ui_hud() -> str:
    update_ui_state({"visible": True})
    launch_ui_hud()
    return "Interface ativada. Deixei o painel no ar."


def hide_ui_hud() -> str:
    global ui_hud_started

    ui_hud_started = False
    update_ui_state({"visible": False})
    refresh_ui_runtime_state({"visible": False})
    return "Interface oculta."


def maybe_handle_ui_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    show_commands = {
        "abrir interface",
        "abrir painel",
        "mostrar interface",
        "mostrar painel",
        "exibir interface",
        "exibir painel",
        "ativar interface",
        "ativar painel",
        "mostrar hud",
    }
    hide_commands = {
        "fechar interface",
        "fechar painel",
        "ocultar interface",
        "ocultar painel",
        "esconder interface",
        "esconder painel",
        "desativar interface",
        "desativar painel",
        "fechar hud",
    }

    if normalized in show_commands:
        return show_ui_hud()

    if normalized in hide_commands:
        return hide_ui_hud()

    if normalized in {"interface atual", "status da interface", "painel atual"}:
        state = "ativa" if load_ui_state().get("visible", False) else "oculta"
        return f"Interface {state}."

    return None


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


def maybe_handle_action_candidate_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "gerar acoes candidatas",
        "atualizar acoes candidatas",
        "gerar acoes do axel",
    }:
        items = save_action_candidates()
        if not items:
            return "Ainda nao encontrei acoes candidatas para estruturar."
        top = str(items[0].get("title", "")).strip()
        return f"Atualizei as acoes candidatas do Axel. Primeira acao: {top}."

    if normalized in {
        "acoes candidatas",
        "mostrar acoes candidatas",
        "acoes do axel",
        "qual a proxima acao candidata",
    }:
        items = load_action_candidates()
        if not items:
            return "Ainda nao ha acoes candidatas."
        parts = []
        for index, item in enumerate(items[:3], start=1):
            title = str(item.get("title", "")).strip()
            status = str(item.get("status", "pending")).strip()
            files = item.get("files") or []
            if title:
                files_text = ", ".join(str(file) for file in files[:3])
                parts.append(f"{index}. {title}. Status: {status}. Alvos: {files_text}")
        return "Acoes candidatas: " + "; ".join(parts)

    if normalized in {
        "aprovar acao candidata",
        "aprovar primeira acao",
        "aprovar acao do axel",
    }:
        item = approve_first_action_candidate()
        title = str(item.get("title", "")).strip()
        if not title:
            return "Nao encontrei acao candidata para aprovar."
        return f"Acao candidata aprovada: {title}. Ainda nao executei; deixei pronta para aplicacao supervisionada."

    if normalized in {
        "aprovar proximo avanco",
        "aprovar proximo avanço",
        "aprovar e preparar proximo avanco",
        "aprovar e preparar proximo avanço",
        "aprovar proximo passo",
        "preparar proximo avanco aprovado",
        "preparar proximo avanço aprovado",
    }:
        proposal_state = approve_current_proposal("aprovado pelo operador para preparacao supervisionada")
        candidate = approve_first_action_candidate("aprovado pelo operador para preparacao supervisionada")
        package = save_execution_package()
        handoff = save_implementation_handoff()
        sync_handoff_application()
        request = save_codex_implementation_request()

        proposal_title = str((proposal_state.get("proposal") or {}).get("title", "")).strip()
        candidate_title = str(candidate.get("title", "")).strip()
        title = candidate_title or proposal_title
        if not title:
            return "Nao encontrei um proximo avanco para aprovar."

        package_status = str(package.get("status", "")).strip()
        handoff_status = str(handoff.get("status", "")).strip()
        request_status = str(request.get("status", "")).strip()
        return (
            f"Aprovei e preparei o proximo avanco: {title}. "
            f"Pacote: {package_status}; handoff: {handoff_status}; pedido ao Codex: {request_status}."
        )

    if normalized in {
        "rejeitar acao candidata",
        "rejeitar primeira acao",
        "rejeitar acao do axel",
    }:
        item = reject_first_action_candidate()
        title = str(item.get("title", "")).strip()
        if not title:
            return "Nao encontrei acao candidata para rejeitar."
        return f"Acao candidata rejeitada: {title}."

    if normalized in {
        "executar acao candidata",
        "executar primeira acao",
    }:
        return "Ainda nao executo acao candidata sozinho. O caminho seguro e aprovar, levar ao Codex e verificar o resultado."

    return None


def maybe_handle_execution_package_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "gerar pacote de execucao",
        "preparar pacote de execucao",
        "montar pacote de execucao",
        "preparar aplicacao supervisionada",
    }:
        payload = save_execution_package()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        if status == "waiting_for_approval":
            return "Ainda nao ha acao candidata aprovada para montar pacote de execucao."
        return f"Pacote de execucao preparado para o Codex: {title}. Status: {status}."

    if normalized in {
        "pacote de execucao",
        "mostrar pacote de execucao",
        "plano de execucao",
        "mostrar plano de execucao",
    }:
        payload = load_execution_package()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        files = payload.get("files") or []
        validation = payload.get("validation") or []
        if status == "waiting_for_approval":
            return "O pacote de execucao ainda aguarda uma acao candidata aprovada."
        files_text = ", ".join(str(file) for file in files[:4])
        validation_text = "; ".join(str(command) for command in validation[:2])
        return f"Pacote de execucao: {title}. Status: {status}. Arquivos: {files_text}. Validacao: {validation_text}."

    if normalized in {
        "executar pacote de execucao",
        "aplicar pacote de execucao",
    }:
        return "Ainda nao aplico o pacote automaticamente. Ele esta pronto para o Codex revisar, editar e validar com voce supervisionando."

    return None


def maybe_handle_implementation_handoff_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "gerar handoff",
        "preparar handoff",
        "handoff para codex",
        "gerar handoff para codex",
        "preparar implementacao",
    }:
        payload = save_implementation_handoff()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        if status == "blocked":
            return "Ainda nao ha pacote aprovado pronto para gerar handoff ao Codex."
        return f"Handoff preparado para o Codex: {title}. Status: {status}."

    if normalized in {
        "mostrar handoff",
        "handoff",
        "handoff do codex",
        "handoff do axel",
    }:
        payload = load_implementation_handoff()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        files = payload.get("files") or []
        validation = payload.get("validation") or []
        if status == "blocked":
            return "O handoff ainda esta bloqueado. Primeiro aprove uma acao candidata e gere o pacote de execucao."
        files_text = ", ".join(str(file) for file in files[:4])
        validation_text = "; ".join(str(command) for command in validation[:2])
        return f"Handoff do Axel para o Codex: {title}. Arquivos: {files_text}. Validacao: {validation_text}."

    if normalized in {
        "aplicar handoff",
        "executar handoff",
    }:
        return "Ainda nao aplico o handoff automaticamente. Ele serve para o Codex implementar com supervisao e validacao."

    return None


def maybe_handle_handoff_application_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "status da aplicacao",
        "status da aplicacao do handoff",
        "aplicacao do handoff",
        "mostrar aplicacao",
    }:
        state = load_handoff_application()
        status = str(state.get("status", "blocked")).strip()
        handoff = state.get("handoff") or {}
        title = str(handoff.get("title", "")).strip()
        note = str(state.get("last_note", "")).strip()
        if not title:
            return f"Aplicacao do handoff: {status}. Ainda nao ha handoff pronto."
        response = f"Aplicacao do handoff: {status}. Alvo: {title}."
        if note:
            response += f" Nota: {note}."
        return response

    if normalized in {
        "iniciar aplicacao do handoff",
        "marcar handoff em andamento",
        "codex comecou handoff",
        "codex começou handoff",
    }:
        state = mark_handoff_started()
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if state.get("status") == "blocked" or not title:
            return "Ainda nao ha handoff pronto para marcar como em andamento."
        return f"Registrei aplicacao em andamento para: {title}."

    if normalized in {
        "handoff aplicado",
        "codex aplicou handoff",
        "marcar handoff aplicado",
        "implementacao aplicada",
        "implementação aplicada",
    }:
        state = mark_handoff_applied()
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if state.get("status") == "blocked" or not title:
            return "Ainda nao ha handoff pronto para marcar como aplicado."
        verification = start_verification("handoff aplicado; aguardando validacao")
        if verification.get("status") == "pending":
            return f"Registrei o handoff como aplicado: {title}. Iniciei a verificacao da melhoria."
        return f"Registrei o handoff como aplicado: {title}. Aguardando validacao supervisionada."

    if normalized in {
        "handoff falhou",
        "codex falhou handoff",
        "marcar handoff falhou",
        "implementacao falhou",
        "implementação falhou",
    }:
        state = mark_handoff_failed()
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if state.get("status") == "blocked" or not title:
            return "Ainda nao ha handoff pronto para marcar como falha."
        verification = mark_verification_failed("handoff falhou durante aplicacao supervisionada")
        if verification.get("status") == "failed":
            return f"Registrei falha na aplicacao do handoff: {title}. Isso vai alimentar uma nova tentativa."
        return f"Registrei falha na aplicacao do handoff: {title}. O rastreador do handoff vai alimentar uma nova tentativa."

    if normalized in {
        "handoff validado",
        "aplicacao validada",
        "aplicacao funcionou",
        "implementacao validada",
        "melhoria aplicada funcionou",
    }:
        state = mark_handoff_validated("validado pelo operador")
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if state.get("status") == "blocked" or not title:
            return "Ainda nao ha handoff pronto para marcar como validado."
        mark_verification_success("handoff validado pelo operador")
        return f"Excelente. Marquei o handoff como validado: {title}."

    return None


def maybe_handle_handoff_validation_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "como validar handoff",
        "validar handoff",
        "checklist do handoff",
        "checklist de validacao",
        "validacao do handoff",
        "validacao da aplicacao",
    }:
        payload = save_handoff_validation()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        checklist = payload.get("checklist") or []
        if status == "blocked":
            return "Ainda nao ha handoff aplicado para validar."
        summary = "; ".join(str(item) for item in checklist[:4])
        return f"Checklist para validar {title}: {summary}."

    if normalized in {
        "mostrar checklist do handoff",
        "mostrar validacao do handoff",
        "mostrar roteiro de validacao",
    }:
        payload = load_handoff_validation()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        checklist = payload.get("checklist") or []
        if status == "blocked":
            return "O roteiro de validacao ainda esta bloqueado. Primeiro o Codex precisa aplicar o handoff."
        summary = "; ".join(str(item) for item in checklist[:6])
        return f"Roteiro de validacao para {title}: {summary}."

    return None


def maybe_handle_handoff_retry_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "plano de nova tentativa",
        "nova tentativa do handoff",
        "replanejar handoff",
        "corrigir handoff",
        "preparar nova tentativa",
        "preparar nova tentativa para codex",
    }:
        payload = save_handoff_retry_plan()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        evidence = payload.get("evidence") or []
        if status == "blocked":
            return "Ainda nao ha uma falha de handoff forte o suficiente para montar nova tentativa."
        request = save_codex_implementation_request()
        clue = str(evidence[0]) if evidence else "falha registrada no handoff"
        if request.get("source") == "handoff_retry_plan":
            return f"Plano de nova tentativa pronto para o Codex: {title}. Principal pista: {clue}."
        return f"Plano de nova tentativa pronto: {title}. Principal pista: {clue}."

    if normalized in {
        "mostrar plano de nova tentativa",
        "mostrar tentativa do handoff",
        "mostrar replanejamento do handoff",
    }:
        payload = load_handoff_retry_plan()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        steps = payload.get("steps") or []
        if status == "blocked":
            return "O plano de nova tentativa ainda esta bloqueado. Primeiro registre uma falha do handoff."
        summary = "; ".join(str(item) for item in steps[:4])
        return f"Nova tentativa para {title}: {summary}."

    return None


def maybe_handle_codex_implementation_request_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "preparar pedido de implementacao",
        "gerar pedido de implementacao",
        "pedido de implementacao ao codex",
        "mensagem de implementacao ao codex",
        "mensagem para codex implementar",
    }:
        payload = save_codex_implementation_request()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        if status == "blocked":
            return "Ainda nao ha handoff pronto para transformar em pedido de implementacao ao Codex."
        mark_handoff_started("pedido de implementacao preparado para o Codex")
        return f"Preparei o pedido de implementacao para o Codex: {title}. Deixei em memory/codex_implementation_request.md."

    if normalized in {
        "mostrar pedido de implementacao",
        "mostrar mensagem para codex",
        "pedido para codex implementar",
    }:
        payload = load_codex_implementation_request()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        files = payload.get("files") or []
        if status == "blocked":
            return "O pedido de implementacao ainda esta bloqueado. Primeiro gere um handoff pronto."
        files_text = ", ".join(str(file) for file in files[:4])
        return f"Pedido pronto para Codex: {title}. Arquivos alvo: {files_text}."

    if normalized in {
        "enviar pedido de implementacao",
        "enviar pedido de implementacao ao codex",
        "colocar pedido de implementacao na fila",
        "colocar pedido na fila do codex",
        "mandar pedido para o codex",
        "enviar nova tentativa ao codex",
        "mandar nova tentativa para o codex",
    }:
        payload = save_codex_implementation_request()
        if payload.get("status") == "blocked":
            return "Ainda nao ha pedido de implementacao pronto para colocar na fila do Codex."
        outbox = enqueue_codex_implementation_request()
        mark_handoff_started("pedido de implementacao colocado na fila do Codex")
        pending = len(outbox.get("pending", []))
        title = str(payload.get("title", "")).strip()
        return f"Pedido colocado na fila do Codex: {title}. Pendentes agora: {pending}."

    return None


def maybe_handle_approval_gate_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "mostrar proposta atual",
        "proposta atual",
        "qual a proposta atual",
        "status da proposta",
    }:
        state = load_approval_gate()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        files = proposal.get("files") or []
        status = str(state.get("status", "none")).strip()
        if not title:
            return "Nao ha proposta atual para aprovar."
        files_text = ", ".join(str(file) for file in files[:4]) if files else "sem arquivos alvo definidos"
        return f"Proposta atual: {title}. Status: {status}. Arquivos alvo: {files_text}."

    if normalized in {
        "aprovar proposta",
        "aprovar proposta atual",
        "aprovar proposta de patch",
    }:
        state = approve_current_proposal()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if title:
            return f"Proposta aprovada. O Axel pode levar ao Codex esta melhoria: {title}."
        return "Proposta aprovada."

    if normalized in {
        "rejeitar proposta",
        "rejeitar proposta atual",
        "rejeitar proposta de patch",
    }:
        state = reject_current_proposal()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if title:
            return f"Proposta rejeitada. Vou aguardar uma nova sugestao para substituir: {title}."
        return "Proposta rejeitada."

    return None


def maybe_handle_verification_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "status da verificacao",
        "mostrar verificacao",
        "status da melhoria",
        "como esta a verificacao",
        "verificacao atual",
    }:
        state = load_verification_runs()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        status = str(state.get("status", "idle")).strip()
        attempts = int(state.get("attempts", 0) or 0)
        note = str(state.get("last_note", "")).strip()
        if not title:
            return "Ainda nao ha melhoria aprovada aguardando verificacao."
        base = f"Verificacao atual: {status}. Alvo: {title}. Tentativas: {attempts}."
        if note:
            base += f" Observacao: {note}."
        return base

    if normalized in {
        "verificar melhoria",
        "iniciar verificacao",
        "comecar verificacao",
        "verificar proposta",
    }:
        state = start_verification()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if not title or str(state.get("approval_status", "none")).strip() != "approved":
            return "Ainda nao ha uma proposta aprovada para verificar."
        checklist = state.get("checklist") or []
        checklist_text = "; ".join(str(item) for item in checklist[:3])
        return f"Verificacao iniciada para {title}. Checklist: {checklist_text}."

    if normalized in {
        "melhoria funcionou",
        "verificacao passou",
        "deu certo",
        "funcionou",
        "passou na verificacao",
    }:
        state = mark_verification_success()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if not title:
            return "Nao encontrei uma melhoria aprovada para marcar como sucesso."
        return f"Perfeito. Registrei que a melhoria passou na verificacao: {title}."

    if normalized in {
        "melhoria falhou",
        "verificacao falhou",
        "nao funcionou",
        "falhou",
        "deu errado",
    }:
        state = mark_verification_failed()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if not title:
            return "Nao encontrei uma melhoria aprovada para marcar como falha."
        return f"Registrei falha na verificacao da melhoria: {title}. O Axel deve preparar nova tentativa."

    if normalized in {
        "tentar novamente",
        "nova tentativa",
        "retestar melhoria",
        "verificar de novo",
    }:
        state = retry_verification()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if not title:
            return "Ainda nao ha uma melhoria aprovada para tentar de novo."
        return f"Nova tentativa de verificacao iniciada para {title}."

    if normalized in {
        "aprender da falha",
        "replanejar melhoria",
        "gerar nova proposta apos falha",
        "corrigir falha da melhoria",
    }:
        state = load_verification_runs()
        title = str((state.get("proposal") or {}).get("title", "")).strip()
        status = str(state.get("status", "idle")).strip()
        if status != "failed" or not title:
            return "Ainda nao ha uma falha de verificacao forte o suficiente para replanejar."
        save_patch_proposals()
        save_auto_advances()
        save_codex_request()
        return f"Perfeito. O Axel replanejou a melhoria apos a falha de verificacao em {title}."

    return None


def maybe_handle_codex_bridge_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    def extract_tail(prefixes: tuple[str, ...]) -> str:
        raw = str(user_input or "").strip()
        raw_lower = raw.lower()
        for prefix in prefixes:
            lowered = prefix.lower()
            if raw_lower.startswith(lowered):
                return raw[len(prefix) :].strip(" :.-")
        return ""

    if normalized in {
        "pedir melhoria ao codex",
        "gerar pedido ao codex",
        "axel falar com codex",
        "axel pedir ao codex",
        "consultar codex para melhorar",
        "preparar conversa com codex",
    }:
        payload = save_codex_request()
        channel = save_codex_channel()
        title = str(payload.get("title", "")).strip()
        status = str(channel.get("status", "")).strip()
        if title:
            return f"Preparei um pedido ao Codex. Foco atual: {title}. Canal atual: {status or 'draft'}."
        return "Preparei um pedido ao Codex."

    if normalized in {
        "mostrar pedido ao codex",
        "qual o pedido ao codex",
        "pedido ao codex",
    }:
        payload = load_codex_request()
        prompt = str(payload.get("prompt", "")).strip()
        if prompt:
            return f"Pedido ao Codex: {prompt}"
        return "Ainda nao ha um pedido ao Codex pronto."

    if normalized in {
        "conversa com codex",
        "mostrar conversa com codex",
        "canal com codex",
        "status do canal com codex",
    }:
        channel = load_codex_channel()
        title = str(channel.get("title", "")).strip()
        status = str(channel.get("status", "")).strip()
        urgency = str(channel.get("urgency", "")).strip()
        next_action = str(channel.get("next_action", "")).strip()
        if not title:
            return "O canal do Axel com o Codex ainda nao tem mensagem pronta."
        return f"Canal com o Codex: {title}. Estado: {status}. Urgencia: {urgency}. Proxima acao: {next_action}."

    if normalized in {
        "sugestao do codex",
        "axel acha que deve chamar codex",
        "vale chamar codex",
        "devo chamar codex",
    }:
        suggestion = consume_codex_suggestion()
        if suggestion:
            return suggestion
        channel = load_codex_channel()
        reason = str(channel.get("notify_reason", "")).strip()
        if reason:
            return f"Ainda nao e o melhor momento para acionar o Codex. Motivo atual: {reason}."
        return "Ainda nao ha recomendacao forte para acionar o Codex."

    if normalized in {
        "atualizar conversa com codex",
        "atualizar canal com codex",
        "sincronizar conversa com codex",
    }:
        channel = save_codex_channel()
        title = str(channel.get("title", "")).strip()
        trigger = str(channel.get("trigger", "")).strip()
        return f"Atualizei o canal com o Codex. Foco: {title}. Gatilho atual: {trigger}."

    if normalized in {
        "fila do codex",
        "mensagens para o codex",
        "caixa de saida do codex",
        "outbox do codex",
    }:
        outbox = load_codex_outbox()
        pending = outbox.get("pending") or []
        sent = outbox.get("sent") or []
        if not pending and not sent:
            return "A fila do Codex ainda esta vazia."
        parts = [f"Fila do Codex: {len(pending)} pendente(s) e {len(sent)} entregue(s)."]
        if pending:
            first = pending[0] if isinstance(pending[0], dict) else {}
            title = str(first.get("title", "")).strip()
            if title:
                parts.append(f"Proxima mensagem: {title}.")
        return " ".join(parts)

    if normalized in {
        "enfileirar mensagem ao codex",
        "preparar envio ao codex",
        "colocar mensagem na fila do codex",
    }:
        outbox = enqueue_current_codex_message()
        pending = outbox.get("pending") or []
        if not pending:
            return "Nao encontrei mensagem atual forte o suficiente para enfileirar ao Codex."
        first = pending[-1] if isinstance(pending[-1], dict) else {}
        title = str(first.get("title", "")).strip()
        return f"Coloquei uma mensagem na fila do Codex. Alvo atual: {title or 'melhoria sem titulo'}."

    if normalized in {
        "marcar mensagem ao codex como enviada",
        "mensagem enviada ao codex",
        "entreguei ao codex",
    }:
        before = load_codex_outbox()
        if not (before.get("pending") or []):
            return "Nao ha mensagem pendente para marcar como enviada ao Codex."
        outbox = mark_next_codex_message_sent()
        pending = len(outbox.get("pending") or [])
        latest_sent = (outbox.get("sent") or [])[-1] if outbox.get("sent") else {}
        if isinstance(latest_sent, dict) and str(latest_sent.get("kind", "")).strip() == "implementation_request":
            mark_handoff_started("pedido de implementacao entregue ao Codex")
            return f"Registrei a entrega do pedido de implementacao ao Codex. Restam {pending} pendente(s)."
        return f"Registrei a entrega da mensagem ao Codex. Restam {pending} pendente(s)."

    if normalized in {
        "limpar fila do codex",
        "zerar fila do codex",
    }:
        clear_codex_outbox_pending()
        return "Limpei as mensagens pendentes da fila do Codex."

    if normalized in {
        "limpar sugestao do codex",
        "resetar sugestao do codex",
    }:
        reset_codex_suggestion_memory()
        return "Limpei a memoria da sugestao do Codex. O Axel pode avisar de novo no proximo ciclo forte."

    if normalized in {
        "inbox do codex",
        "entrada do codex",
        "respostas do codex",
        "caixa de entrada do codex",
    }:
        inbox = load_codex_inbox()
        items = inbox.get("items") or []
        if not items:
            return "A caixa de entrada do Codex ainda esta vazia."
        latest = items[-1] if isinstance(items[-1], dict) else {}
        kind = str(latest.get("kind", "")).strip()
        text = str(latest.get("text", "")).strip()
        return f"Inbox do Codex: {len(items)} resposta(s) registrada(s). Ultimo tipo: {kind or 'reply'}. Conteudo: {text or 'sem texto'}."

    codex_reply = extract_tail(("codex respondeu", "resposta do codex", "registrar resposta do codex"))
    if codex_reply:
        add_codex_inbox_item("reply", codex_reply)
        return "Registrei a resposta do Codex na caixa de entrada do Axel."

    codex_decision = extract_tail(("decisao do codex", "decisão do codex", "codex decidiu"))
    if codex_decision:
        add_codex_inbox_item("decision", codex_decision)
        return "Registrei a decisao do Codex para o Axel."

    codex_next_step = extract_tail(("proximo passo do codex", "próximo passo do codex", "codex sugeriu o proximo passo", "codex sugeriu o próximo passo"))
    if codex_next_step:
        add_codex_inbox_item("next_step", codex_next_step)
        return "Registrei o proximo passo sugerido pelo Codex."

    codex_applied = extract_tail((
        "codex aplicou",
        "codex implementou",
        "codex concluiu",
        "codex terminou",
        "resultado do codex",
    ))
    if codex_applied:
        add_codex_inbox_item("implementation_applied", codex_applied)
        state = mark_handoff_applied(codex_applied)
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if title:
            return f"Registrei que o Codex aplicou o handoff: {title}. Agora falta validar no uso real."
        return "Registrei que o Codex aplicou uma implementacao."

    codex_failed = extract_tail((
        "codex falhou",
        "codex nao conseguiu",
        "falha do codex",
        "erro do codex",
    ))
    if codex_failed:
        add_codex_inbox_item("implementation_failed", codex_failed)
        state = mark_handoff_failed(codex_failed)
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if title:
            return f"Registrei falha do Codex no handoff: {title}. Isso entra na proxima tentativa."
        return "Registrei uma falha de implementacao do Codex."

    if normalized in {
        "limpar inbox do codex",
        "limpar caixa de entrada do codex",
        "zerar inbox do codex",
    }:
        clear_codex_inbox()
        return "Limpei a caixa de entrada do Codex."

    return None


def maybe_handle_self_evolution_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    def summarize_plan_counts(plan: dict) -> tuple[int, int, int, int, list[dict]]:
        steps = plan.get("steps") or []
        steps = steps if isinstance(steps, list) else []
        done = sum(1 for step in steps if isinstance(step, dict) and step.get("status") == "done")
        next_items = [step for step in steps if isinstance(step, dict) and step.get("status") == "next"]
        planned = sum(1 for step in steps if isinstance(step, dict) and step.get("status") == "planned")
        left = max(0, len(steps) - done)
        return len(steps), done, left, planned, next_items

    if normalized in {
        "plano de auto evolucao",
        "mostrar plano de auto evolucao",
        "auto evolucao",
        "como chegar em se reescreve sozinho",
    }:
        plan = load_self_evolution_plan()
        steps = plan.get("steps") or []
        if not isinstance(steps, list) or not steps:
            return "Ainda nao consegui montar um plano de auto evolucao."
        lines = []
        for step in steps[:4]:
            if not isinstance(step, dict):
                continue
            status = str(step.get("status", "planned")).strip()
            title = str(step.get("title", "")).strip()
            if title:
                lines.append(f"{status}: {title}")
        focus = str(plan.get("current_focus", "")).strip()
        prefix = f"Foco atual: {focus}. " if focus else ""
        return prefix + "Plano de auto evolucao do Axel: " + "; ".join(lines)

    if normalized in {
        "quantos passos faltam",
        "quantos passos faltam para auto evolucao",
        "status da auto evolucao",
        "progresso da auto evolucao",
        "andamento da auto evolucao",
    }:
        plan = save_self_evolution_plan()
        total, done, left, planned, next_items = summarize_plan_counts(plan)
        next_title = str((next_items[0] if next_items else {}).get("title", "")).strip()
        suffix = f" Proximo passo: {next_title}." if next_title else ""
        return f"Auto evolucao do Axel: {done}/{total} passos concluidos. Faltam {left}; {planned} ainda planejados.{suffix}"

    if normalized in {
        "listar passos faltantes",
        "mostrar passos faltantes",
        "quais passos faltam",
        "passos restantes",
        "passos que faltam",
    }:
        plan = save_self_evolution_plan()
        missing = [
            step
            for step in plan.get("steps", [])
            if isinstance(step, dict) and step.get("status") != "done"
        ]
        if not missing:
            return "Todos os passos conhecidos da auto evolucao estao concluidos."
        parts = []
        for index, step in enumerate(missing[:8], start=1):
            status = str(step.get("status", "planned")).strip()
            title = str(step.get("title", "")).strip()
            if title:
                parts.append(f"{index}. {status}: {title}")
        return "Passos faltantes: " + "; ".join(parts)

    if normalized in {
        "proximo passo da auto evolucao",
        "qual o proximo passo",
        "qual o proximo passo da auto evolucao",
        "avancar auto evolucao",
    }:
        plan = save_self_evolution_plan()
        _, _, _, _, next_items = summarize_plan_counts(plan)
        if next_items:
            step = next_items[0]
        else:
            planned_items = [item for item in plan.get("steps", []) if isinstance(item, dict) and item.get("status") == "planned"]
            step = planned_items[0] if planned_items else {}
        title = str(step.get("title", "")).strip()
        reason = str(step.get("reason", "")).strip()
        if title and reason:
            return f"Proximo passo da auto evolucao: {title}. Motivo: {reason}"
        if title:
            return f"Proximo passo da auto evolucao: {title}."
        return "Todos os passos conhecidos da auto evolucao estao concluidos ou sem proximo item definido."

    if normalized in {
        "atualizar plano de auto evolucao",
        "gerar plano de auto evolucao",
    }:
        plan = save_self_evolution_plan()
        focus = str(plan.get("current_focus", "")).strip()
        if focus:
            return f"Atualizei o plano de auto evolucao. Foco atual: {focus}."
        return "Atualizei o plano de auto evolucao do Axel."

    return None


def maybe_handle_operational_context_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    compact = re.sub(r"\s+", " ", normalized).strip()

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

    if (
        ("context" in compact or "contr" in compact)
        and ("operac" in compact or "atual" in compact)
    ):
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

    if normalized in {
        "quais apps recentes",
        "apps recentes",
        "aplicativos recentes",
        "aplicativo recente",
        "sites recentes",
        "quais sites recentes",
        "topicos recentes",
        "tópicos recentes",
    }:
        payload = save_operational_context()
        apps = payload.get("recent_apps") or []
        sites = payload.get("recent_sites") or []
        topics = payload.get("recent_topics") or []
        wants_apps = any(token in compact for token in {"app", "aplicativo"})
        wants_sites = "site" in compact
        wants_topics = any(token in compact for token in {"topico", "topicos", "tópico", "tópicos"})

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


def maybe_handle_directives_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    if normalized not in {
        "diretrizes",
        "diretrizes do axel",
        "diretrizes do axe",
        "mostrar diretrizes",
        "modo investimentos",
        "modo investimento",
        "base do modo investimentos",
        "como funciona modo investimentos",
    } and not (normalized.startswith("diretrizes") and "axe" in normalized):
        return None

    path = Path(__file__).resolve().parent / "memory" / "axel_directives.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "Ainda não consegui carregar minhas diretrizes."

    if normalized in {"modo investimentos", "modo investimento"}:
        return (
            "Modo investimentos pronto para leitura de tela. Abra sua carteira ou ativo e diga: "
            "analisar investimentos, resumo financeiro ou analisar carteira."
        )

    if "investimento" in normalized:
        investment = payload.get("investment_mode") or {}
        goal = str(investment.get("goal", "")).strip()
        rules = [str(item) for item in (investment.get("rules") or [])[:3]]
        if not goal:
            return "Modo investimentos ainda está sem diretrizes configuradas."
        suffix = " Regras: " + "; ".join(rules) + "." if rules else ""
        return f"Modo investimentos preparado. {goal}{suffix}"

    directives = [str(item) for item in (payload.get("core_directives") or [])[:4]]
    if not directives:
        return "Minhas diretrizes ainda estão vazias."
    return "Diretrizes do Axel: " + "; ".join(directives) + "."


def refresh_improvement_brain(force: bool = False):
    global last_improvement_refresh

    now = time.time()
    if not force and now - last_improvement_refresh < 15:
        return

    try:
        save_bottlenecks()
        save_auto_advances()
        save_patch_proposals()
        save_action_candidates()
        save_execution_package()
        save_implementation_handoff()
        sync_handoff_application()
        save_handoff_validation()
        save_handoff_retry_plan()
        save_codex_implementation_request()
        sync_approval_gate()
        sync_verification_runs()
        save_codex_request()
        save_codex_channel()
        sync_codex_outbox()
        save_operational_context()
        save_self_evolution_plan()
        last_improvement_refresh = now
    except Exception:
        pass


def maybe_announce_codex_suggestion(voice_mode: bool):
    suggestion = consume_codex_suggestion()
    if suggestion:
        output_response(suggestion, voice_mode)


def poll_ui_text_command() -> str:
    queued = dequeue_ui_command()
    if not queued:
        return ""

    append_ui_history("user", queued, max_items=UI_HISTORY_MAX_ITEMS)
    refresh_ui_runtime_state({"last_heard": queued})
    return queued


HUMOR_STYLE_ALIASES = {
    "neutro": "neutro",
    "serio": "neutro",
    "sÃ©rio": "neutro",
    "sem humor": "neutro",
    "desligado": "neutro",
    "jarvis": "jarvis",
    "mordomo": "jarvis",
    "sofisticado": "jarvis",
    "elegancia": "jarvis",
    "elegÃ¢ncia": "jarvis",
    "seco": "seco",
    "ironico": "seco",
    "irÃ´nico": "seco",
    "elegante": "seco",
    "filosofico": "filosofico",
    "filosÃ³fico": "filosofico",
    "reflexivo": "filosofico",
    "visao": "filosofico",
    "visÃ£o": "filosofico",
    "brincalhao": "brincalhao",
    "brincalhÃ£o": "brincalhao",
    "divertido": "brincalhao",
    "leve": "brincalhao",
}

HUMOR_DISPLAY_NAMES = {
    "neutro": "neutro",
    "jarvis": "jarvis",
    "seco": "seco",
    "filosofico": "reflexivo",
    "brincalhao": "leve",
}


def current_humor_description() -> str:
    enabled = bool(VOICE_PREFERENCES.get("assistant_humor_enabled", True))
    style = str(VOICE_PREFERENCES.get("assistant_humor_style", "seco")).strip().lower()
    try:
        level = int(VOICE_PREFERENCES.get("assistant_humor_level", 2))
    except (TypeError, ValueError):
        level = 2

    if not enabled or style == "neutro" or level <= 0:
        return "Humor atual: neutro, intensidade zero."

    display = HUMOR_DISPLAY_NAMES.get(style, style)
    return f"Humor atual: {display}, intensidade {max(0, min(3, level))} de 3."


def apply_humor_settings(style: str | None = None, level: int | None = None, enabled: bool | None = None) -> str:
    current_level = int(VOICE_PREFERENCES.get("assistant_humor_level", 2) or 2)
    current_style = str(VOICE_PREFERENCES.get("assistant_humor_style", "seco")).strip().lower() or "seco"

    style = style or current_style
    level = current_level if level is None else max(0, min(3, int(level)))
    enabled = (style != "neutro" and level > 0) if enabled is None else bool(enabled)

    if style == "neutro":
        enabled = False
        level = 0

    update_voice_preferences(
        {
            "assistant_humor_enabled": enabled,
            "assistant_humor_style": style,
            "assistant_humor_level": level,
        }
    )
    refresh_voice_preferences()
    return current_humor_description()


def humor_test_response() -> str:
    style = str(VOICE_PREFERENCES.get("assistant_humor_style", "seco")).strip().lower()
    enabled = bool(VOICE_PREFERENCES.get("assistant_humor_enabled", True))
    try:
        level = int(VOICE_PREFERENCES.get("assistant_humor_level", 2))
    except (TypeError, ValueError):
        level = 2

    if not enabled or style == "neutro" or level <= 0:
        return "Teste de humor: sistemas online. Direto, funcional e sem piada lateral. So trabalho."

    if style == "jarvis":
        return "Teste de humor: sistemas online. Tudo sob controle, como deveria ser. Se algo falhar, culparemos a fisica ou o navegador, nessa ordem."

    if style == "filosofico":
        return "Teste de humor: sistemas online. Sempre curioso como um simples comando muda o estado do mundo. E, ainda assim, o mundo insiste em abrir abas demais."

    if style == "brincalhao":
        return "Teste de humor: sistemas online. Tudo em ordem, sem drama e com uma boa vontade quase suspeita. Estou agradavelmente operacional."

    return "Teste de humor: sistemas online. Seco, preciso e com um comentario minimo no ponto certo. A elegancia sobreviveu ao boot."


def list_pronunciation_response() -> str:
    pronunciations = load_tts_pronunciations()
    if not pronunciations:
        return "Não há pronúncias personalizadas salvas."

    items = []
    for term, pronunciation in sorted(pronunciations.items(), key=lambda item: item[0].lower()):
        items.append(f"{term} -> {pronunciation}")
        if len(items) >= 12:
            break

    return "Pronúncias salvas: " + "; ".join(items) + "."


def maybe_handle_pronunciation_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    raw = user_input.strip()

    save_patterns = [
        r"^\s*pronuncia(?:cao)?\s+de\s+(.+?)\s+como\s+(.+?)\s*$",
        r"^\s*pronuncia(?:cao)?\s+de\s+(.+?)\s+para\s+(.+?)\s*$",
        r"^\s*ajustar\s+pronuncia(?:cao)?\s+de\s+(.+?)\s+para\s+(.+?)\s*$",
        r"^\s*salvar\s+pronuncia(?:cao)?\s+de\s+(.+?)\s+como\s+(.+?)\s*$",
        r"^\s*chama\s+(.+?)\s+de\s+(.+?)\s*$",
        r"^\s*fala\s+(.+?)\s+como\s+(.+?)\s*$",
        r"^\s*le\s+(.+?)\s+como\s+(.+?)\s*$",
    ]
    for pattern in save_patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            term = match.group(1).strip(" \t,.:;!?\"'")
            pronunciation = match.group(2).strip(" \t,.:;!?\"'")
            if not term or not pronunciation:
                return "Preciso da palavra e da pronúncia."
            set_tts_pronunciation(term, pronunciation)
            return f"Pronúncia salva para {term}."

    remove_patterns = [
        r"^\s*remover\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
        r"^\s*apagar\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
        r"^\s*tira\s+a\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
        r"^\s*esquece\s+a\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
    ]
    for pattern in remove_patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            term = match.group(1).strip(" \t,.:;!?\"'")
            if not term:
                return "Qual palavra devo remover?"
            removed = remove_tts_pronunciation(term)
            if removed:
                return f"Pronúncia removida para {term}."
            return f"Não encontrei pronúncia salva para {term}."

    if normalized in {
        "listar pronuncias",
        "listar pronunciacoes",
        "mostrar pronuncias",
        "mostrar pronunciacoes",
        "pronuncias salvas",
        "pronunciacoes salvas",
        "quais pronuncias estao salvas",
        "quais pronunciacoes estao salvas",
    }:
        return list_pronunciation_response()

    query_patterns = [
        r"^\s*qual\s+a\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
        r"^\s*como\s+voce\s+fala\s+(.+?)\s*$",
        r"^\s*como\s+fala\s+(.+?)\s*$",
    ]
    for pattern in query_patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            term = match.group(1).strip(" \t,.:;!?\"'")
            if not term:
                return "Qual palavra você quer consultar?"
            pronunciation = get_tts_pronunciation(term)
            if pronunciation:
                return f"A pronúncia salva para {term} é {pronunciation}."
            return f"Ainda não há pronúncia personalizada para {term}."

    return None




def maybe_handle_humor_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {"testar humor", "teste de humor", "testar personalidade", "teste de personalidade"}:
        return humor_test_response()

    if normalized in {"humor atual", "qual humor", "qual o humor", "modo humor"}:
        return current_humor_description()

    if normalized in {"mais humor", "aumentar humor", "aumenta humor"}:
        level = int(VOICE_PREFERENCES.get("assistant_humor_level", 2) or 2)
        return apply_humor_settings(level=level + 1, enabled=True)

    if normalized in {"menos humor", "diminuir humor", "diminui humor"}:
        level = int(VOICE_PREFERENCES.get("assistant_humor_level", 2) or 2)
        return apply_humor_settings(level=level - 1)

    if not any(word in normalized for word in {"humor", "personalidade"}):
        return None

    if any(phrase in normalized for phrase in {"desligar", "desliga", "sem humor", "neutro", "serio", "sÃ©rio"}):
        return apply_humor_settings(style="neutro")

    if any(phrase in normalized for phrase in {"ligar", "liga", "ativar", "ativa"}):
        return apply_humor_settings(
            style=str(VOICE_PREFERENCES.get("assistant_humor_style", "seco") or "seco"),
            level=max(1, int(VOICE_PREFERENCES.get("assistant_humor_level", 2) or 2)),
            enabled=True,
        )

    for alias, style in HUMOR_STYLE_ALIASES.items():
        if alias in normalized:
            return apply_humor_settings(style=style, level=2 if style != "neutro" else 0)

    level_match = re.search(r"\b(?:nivel|nÃ­vel|intensidade)\s+([0-3])\b", normalized)
    if level_match:
        level = int(level_match.group(1))
        return apply_humor_settings(level=level)

    return "Nao identifiquei o humor. Tente: humor jarvis, humor seco, humor reflexivo, humor leve ou humor neutro."




def cli_value_after(flag: str) -> str | None:
    if flag not in sys.argv:
        return None

    index = sys.argv.index(flag)
    if index + 1 >= len(sys.argv):
        return None

    value = sys.argv[index + 1].strip()
    if not value or value.startswith("--"):
        return None

    return value


def cli_text_after(flag: str) -> str | None:
    if flag not in sys.argv:
        return None

    index = sys.argv.index(flag)
    parts = []
    for part in sys.argv[index + 1:]:
        if part.startswith("--"):
            break
        parts.append(part)

    text = " ".join(parts).strip()
    return text or None


def handle_voice_profile_cli() -> bool:
    global VOICE_PREFERENCES

    if "--warm-tts-cache" in sys.argv:
        result = prime_piper_cache(common_tts_cache_phrases())
        print(result.text or result.error)
        if result.error:
            print(result.error)
        return True

    if "--list-piper-voices" in sys.argv:
        print("Vozes Piper disponiveis:")
        for voice in list_piper_voices():
            status = "instalada" if voice["installed"] else "nao instalada"
            print(f"- {voice['key']} ({status}) - {voice['label']}")
        return True

    voice_to_download = cli_value_after("--download-piper-voice")
    if voice_to_download:
        ok, message = download_piper_voice(voice_to_download)
        print(message)
        if not ok:
            return True

    voice_to_apply = cli_value_after("--use-piper-voice")
    if voice_to_apply:
        ok, message = apply_piper_voice(voice_to_apply)
        print(message)
        if not ok:
            return True
        refresh_voice_preferences()

    if "--list-voice-profiles" in sys.argv:
        print("Perfis de voz disponiveis:")
        for profile in list_voice_profiles():
            print(f"- {profile}")
        return True

    profile_name = cli_value_after("--voice-profile")
    if profile_name:
        ok, message = apply_voice_profile(profile_name)
        print(message)
        if not ok:
            return True
        refresh_voice_preferences()

    if "--voice-test" in sys.argv:
        test_text = (
            cli_text_after("--voice-test")
            or str(VOICE_PREFERENCES.get("startup_voice_greeting", "")).strip()
            or "Sistemas online. A sua disposicao."
        )
        VOICE_PREFERENCES["tts_wait_for_playback"] = True
        try:
            import voice.windows_voice as windows_voice

            windows_voice.VOICE_PREFERENCES["tts_wait_for_playback"] = True
        except Exception:
            pass
        output_response(test_text, voice_mode=True)
        return True

    return bool(profile_name or voice_to_download or voice_to_apply)


def voice_profile_from_text(text: str) -> str | None:
    normalized = normalize_text(text)
    profile_aliases = {
        "faber rapido": "faber-rapido",
        "faber rÃ¡pido": "faber-rapido",
        "voz rapida": "faber-rapido",
        "voz rÃ¡pida": "faber-rapido",
        "faber claro": "faber-claro",
        "voz clara": "faber-claro",
        "faber calmo": "faber-calmo",
        "faber calma": "faber-calmo",
        "voz calma": "faber-calmo",
        "faber jarvis": "faber-jarvis",
        "faber jervis": "faber-jarvis",
        "voz jarvis faber": "faber-jarvis",
        "jarvis faber": "faber-jarvis",
        "modo jarvis faber": "faber-jarvis",
        "assistente": "assistente",
        "assistente natural": "assistente",
        "assistente cinema": "assistente-cinema",
        "assistente cinematografico": "assistente-cinema",
        "modo jarvis": "assistente-cinema",
        "modo cinema": "assistente-cinema",
        "estagiario": "assistente",
        "estagiario natural": "assistente",
        "jarvis": "jarvis",
        "jarves": "jarvis",
        "jarvis limpo": "jarvis",
        "jarvis calmo": "jarvis-calmo",
        "jarvis calma": "jarvis-calmo",
        "jarvis firme": "jarvis-firme",
        "jarvis forte": "jarvis-firme",
        "jarvis console": "jarvis-console",
        "jarvis com efeito": "jarvis-console",
        "console": "jarvis-console",
        "natural": "natural",
        "normal": "natural",
        "padrao": "natural",
    }

    for alias, profile in sorted(profile_aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in normalized:
            return profile

    return None


def maybe_handle_voice_profile_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "listar vozes",
        "listar perfis de voz",
        "quais vozes",
        "quais vozes voce tem",
        "opcoes de voz",
        "opcoes da voz",
    }:
        return "Perfis de voz: " + ", ".join(list_voice_profiles()) + "."

    if normalized in {"testar voz", "teste de voz", "teste da voz", "fala teste"}:
        return (
            str(VOICE_PREFERENCES.get("startup_voice_greeting", "")).strip()
            or "Sistemas online. A sua disposicao."
        )

    change_voice_prefixes = (
        "mudar voz",
        "trocar voz",
        "usar voz",
        "ativar voz",
        "voz ",
        "perfil de voz",
        "deixa a voz",
        "deixar a voz",
    )
    explicit_voice_phrases = {
        "voz rapida",
        "voz rÃ¡pida",
        "voz clara",
        "voz calma",
        "voz jarvis faber",
        "voz assistente",
        "voz cinema",
        "voz estagiario",
        "voz jarvis",
        "voz natural",
        "voz normal",
        "voz padrao",
        "voz console",
    }
    if not normalized.startswith(change_voice_prefixes) and not any(
        phrase in normalized for phrase in explicit_voice_phrases
    ):
        return None

    profile = voice_profile_from_text(normalized)
    if not profile:
        return "Nao identifiquei o perfil de voz. Diga, por exemplo, voz jarvis firme ou voz natural."

    ok, message = apply_voice_profile(profile)
    refresh_voice_preferences()
    if ok:
        return f"{message} {VOICE_PREFERENCES.get('startup_voice_greeting', 'Sistemas online.')}"

    return message


def _normalize_device_label(text: str) -> str:
    return normalize_text(text).strip()


def maybe_handle_input_device_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input).strip(" .,:;!?")
    raw = user_input.strip()

    if normalized in {
        "listar microfones",
        "listar microfone",
        "mostrar microfones",
        "mostrar microfone",
        "quais microfones",
        "quais microfones voce tem",
        "microfones disponiveis",
        "microfones disponíveis",
        "entradas de audio",
        "entradas de áudio",
        "listar entradas de audio",
        "listar entradas de áudio",
    }:
        return format_input_devices()

    if normalized in {
        "qual microfone esta ativo",
        "qual microfone está ativo",
        "qual microfone ativo",
        "microfone atual",
        "microfone em uso",
        "entrada de audio atual",
        "entrada de áudio atual",
    }:
        active = get_active_input_device_info()
        if not active:
            return "Não encontrei um microfone ativo no momento."
        return f"Microfone ativo: {active['name']}."

    if normalized in {
        "usar microfone padrao",
        "usar microfone padrão",
        "usar padrao do windows",
        "usar padrão do windows",
        "usar microfone do windows",
        "limpar microfone preferido",
        "remover microfone preferido",
    }:
        update_voice_preferences({"audio_input_device": ""})
        refresh_voice_preferences()
        active = get_active_input_device_info()
        if active:
            return f"Voltei para o microfone padrão do Windows: {active['name']}."
        return "Voltei para o microfone padrão do Windows."

    patterns = [
        r"^\s*usar\s+microfone\s+(.+?)\s*$",
        r"^\s*trocar\s+microfone\s+para\s+(.+?)\s*$",
        r"^\s*selecionar\s+microfone\s+(.+?)\s*$",
        r"^\s*escolher\s+microfone\s+(.+?)\s*$",
        r"^\s*microfone\s+(.+?)\s*$",
    ]
    requested_name = None
    for pattern in patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            requested_name = match.group(1).strip(" \t,.:;!?\"'")
            break

    if not requested_name:
        return None

    requested_normalized = _normalize_device_label(requested_name)
    if not requested_normalized:
        return "Qual microfone você quer usar?"

    devices_text = format_input_devices()
    devices = list_input_devices()
    active = get_active_input_device_info()

    if not devices:
        return "Não encontrei microfones disponíveis para selecionar."

    exact = next((device for device in devices if _normalize_device_label(device["name"]) == requested_normalized), None)
    contains = next(
        (
            device
            for device in devices
            if requested_normalized in _normalize_device_label(device["name"])
        ),
        None,
    )

    best = None
    best_score = 0.0
    for device in devices:
        score = difflib.SequenceMatcher(
            None,
            requested_normalized,
            _normalize_device_label(device["name"]),
        ).ratio()
        if score > best_score:
            best_score = score
            best = device

    chosen = exact or contains or (best if best_score >= 0.58 else None)
    if not chosen:
        return f"Não encontrei um microfone parecido com {requested_name}. {devices_text}"

    update_voice_preferences({"audio_input_device": chosen["name"]})
    refresh_voice_preferences()

    if active and active["name"] == chosen["name"]:
        return f"Microfone confirmado: {chosen['name']}."
    return f"Agora vou usar este microfone: {chosen['name']}."


def set_voice_status(status: str):
    global voice_status

    if voice_status == status:
        return

    voice_status = status
    render_status_line()
    refresh_ui_runtime_state()


def clear_status_line():
    global rendered_status_line

    if not rendered_status_line:
        return

    print("\r" + (" " * len(rendered_status_line)) + "\r", end="", flush=True)
    rendered_status_line = ""


def terminal_print(message: str):
    clear_status_line()
    print(message)
    render_status_line()


def terminal_input(prompt: str) -> str:
    clear_status_line()
    try:
        return input(prompt).strip()
    finally:
        render_status_line()


def render_status_line():
    global rendered_status_line

    if not hotword_ui_enabled or not voice_status:
        rendered_status_line = ""
        return

    rendered_status_line = f"[ESCUTA: {voice_status}]"
    print(f"\r{rendered_status_line:<24}", end="", flush=True)


def read_user_input(
    voice_mode: bool,
    announce_ready: bool = True,
    fallback_to_text: bool = True,
    ready_message: str = "Pode falar...",
    ignored_text_filter=None,
    listener=None,
) -> str:
    if not voice_mode:
        typed = terminal_input("Voce: ")
        if typed:
            append_ui_history("user", typed, max_items=UI_HISTORY_MAX_ITEMS)
            refresh_ui_runtime_state({"last_heard": typed})
        return typed

    if announce_ready:
        terminal_print(f"IA: {ready_message}")
    listen = listener or listen_once
    heard = listen()

    if heard.ok:
        text = heard.text.strip()
        if ignored_text_filter and ignored_text_filter(text):
            return ""
        terminal_print(f"Voce (voz): {text}")
        append_ui_history("user", text, max_items=UI_HISTORY_MAX_ITEMS)
        refresh_ui_runtime_state({"last_heard": text})
        return text

    if not fallback_to_text and heard.error in {
        "Nao detectei fala no microfone.",
        "Nenhuma fala reconhecida.",
    }:
        return ""

    terminal_print(f"IA: {heard.error}")

    if not fallback_to_text:
        return ""

    typed = terminal_input("Voce (texto): ")
    if typed:
        append_ui_history("user", typed, max_items=UI_HISTORY_MAX_ITEMS)
        refresh_ui_runtime_state({"last_heard": typed})
    return typed


def maybe_normalize_voice_command(user_input: str, voice_mode: bool) -> str:
    if not voice_mode:
        return user_input

    learned = apply_voice_correction(user_input)
    if learned:
        return learned

    normalized_input = normalize_text(user_input)
    contextual_followup_prefixes = (
        "o que voce acha",
        "o que vc acha",
        "o que acha",
        "o que voce pensa",
        "o que pensa",
        "voce acha",
        "vc acha",
        "acha que",
        "existem",
        "existe",
        "tem",
        "qual sua opiniao",
        "qual a sua opiniao",
        "qual sua leitura",
        "me explica",
        "me explique",
        "explica",
        "explique",
        "detalha isso",
        "detalhar isso",
        "interpreta isso",
        "interprete isso",
    )
    if normalized_input.startswith(contextual_followup_prefixes):
        return user_input

    normalized_candidate = normalize_voice_command(user_input)
    protected_voice_commands = {
        "o que tem na tela",
        "resuma a tela",
        "detalha a tela",
        "o que voce acha disso",
        "o que vc acha disso",
        "o que acha disso",
        "o que voce pensa disso",
        "qual sua opiniao sobre isso",
        "qual a sua opiniao sobre isso",
        "voce acha que existem melhores",
        "voce acha que existe melhor",
        "vc acha que existem melhores",
        "acha que existem melhores",
        "tem melhores",
        "tem melhor",
        "me explica melhor esse cenario",
        "me explique melhor esse cenario",
        "explica melhor esse cenario",
        "detalha isso",
        "detalhar isso",
        "interpreta isso",
        "interprete isso",
        "proximos avancos",
        "pedido ao codex",
        "conversa com codex",
        "canal com codex",
        "sugestao do codex",
        "fila do codex",
        "inbox do codex",
        "codex aplicou",
        "codex implementou",
        "codex falhou",
        "plano de auto evolucao",
        "quantos passos faltam",
        "status da auto evolucao",
        "progresso da auto evolucao",
        "listar passos faltantes",
        "mostrar passos faltantes",
        "passos restantes",
        "proximo passo da auto evolucao",
        "mostrar gargalos",
        "atualizar gargalos",
        "propostas de patch",
        "mostrar propostas de patch",
        "acoes candidatas",
        "mostrar acoes candidatas",
        "aprovar proximo avanco",
        "aprovar proximo avanço",
        "aprovar e preparar proximo avanco",
        "aprovar e preparar proximo avanço",
        "pacote de execucao",
        "mostrar pacote de execucao",
        "handoff",
        "mostrar handoff",
        "status da aplicacao",
        "aplicacao do handoff",
        "handoff aplicado",
        "handoff falhou",
        "handoff validado",
        "aplicacao validada",
        "como validar handoff",
        "validar handoff",
        "checklist do handoff",
        "plano de nova tentativa",
        "replanejar handoff",
        "contexto operacional",
        "apps recentes",
        "aplicativos recentes",
        "sites recentes",
        "topicos recentes",
        "analisar imagem da tela",
        "analisar imagem no navegador",
        "interpretar imagem da tela",
        "descrever imagem da tela",
        "identificar elementos",
        "analisa grafico",
        "analisar grafico",
        "interpreta grafico",
        "interpretar grafico",
        "ler grafico",
        "inspecionar codigo selecionado",
        "analisar codigo selecionado",
        "inspecionar selecionado",
        "diretrizes",
        "diretrizes do axel",
        "modo investimentos",
        "analisar investimentos",
        "resumo financeiro",
        "resumo da carteira",
        "analisar carteira",
        "preparar nova tentativa",
        "preparar nova tentativa para codex",
        "preparar pedido de implementacao",
        "gerar pedido de implementacao",
        "pedido de implementacao ao codex",
        "mensagem para codex implementar",
        "mostrar pedido de implementacao",
        "enviar pedido de implementacao",
        "enviar pedido de implementacao ao codex",
        "colocar pedido na fila do codex",
        "mandar pedido para o codex",
        "enviar nova tentativa ao codex",
        "mandar nova tentativa para o codex",
        "proposta atual",
        "aprovar proposta atual",
        "rejeitar proposta atual",
        "status da verificacao",
        "verificar melhoria",
        "melhoria funcionou",
        "melhoria falhou",
        "replanejar melhoria",
    }
    if (
        normalized_candidate in protected_voice_commands
        or normalized_candidate.startswith("pesquisar")
        or normalized_candidate.startswith(("codex aplicou", "codex implementou", "codex falhou"))
    ):
        return normalized_candidate

    raw_action = route(user_input)
    if raw_action.get("intent") != "respond":
        return user_input

    if raw_action.get("response") not in {
        "Nao entendi.",
        "Pode repetir?",
        "Nao identifiquei o comando.",
    }:
        return user_input

    return normalized_candidate or user_input


def wait_for_hotword(
    voice_mode: bool,
    hotword_mode: bool,
    voice_paused: bool,
) -> tuple[bool, bool, str]:
    if not hotword_mode:
        return True, voice_paused, ""

    while True:
        if not voice_paused:
            set_voice_status("ATIVA" if HOTWORD_LISTENING_ENABLED else f"BOTAO {HOTKEY_NAME}")

        queued_command = poll_ui_text_command()
        if queued_command:
            set_voice_status("COMANDO")
            terminal_print(f"Voce (painel): {queued_command}")
            return True, voice_paused, queued_command

        if consume_toggle_listening_hotkey_press():
            voice_paused = not voice_paused
            if voice_paused:
                set_voice_status("PAUSADA")
                output_response("Escuta pausada.", voice_mode=False)
            else:
                set_voice_status("ATIVA")
                output_response("Escuta retomada.", voice_mode=False)
            time.sleep(0.15)
            continue

        if voice_paused:
            time.sleep(0.08)
            continue

        if consume_hotkey_press():
            play_activation_sound()
            set_voice_status("COMANDO")
            output_response("Pode falar.", voice_mode=False)
            return True, voice_paused, ""

        if not HOTWORD_LISTENING_ENABLED:
            time.sleep(0.08)
            continue

        heard = listen_for_hotword()

        if heard.ok:
            play_activation_sound()
            if heard.command_text:
                set_voice_status("ATIVA")
                return True, voice_paused, heard.command_text

            set_voice_status("COMANDO")
            output_response("Pode falar.", voice_mode=False)
            return True, voice_paused, ""

        if heard.error.startswith("Falha ao acessar o microfone"):
            output_response(heard.error, voice_mode=False)
            return False, voice_paused, ""


def is_waiting_for_direct_response() -> bool:
    return (
        pending_command is not None
        or pending_smart_open_choice is not None
        or repeat_listen_until > time.time()
    )


def is_conversation_stop(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in {
        "parar conversa",
        "para conversa",
        "chega de conversa",
        "sair da conversa",
        "modo comando",
        "voltar comandos",
    }


def is_dictation_start(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in {
        "modo ditado",
        "ativar ditado",
        "ativa ditado",
        "iniciar ditado",
        "inicia ditado",
        "comecar ditado",
        "comecar o ditado",
        "comeca ditado",
        "ditado",
    }


def is_dictation_stop(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in {
        "parar ditado",
        "para ditado",
        "encerrar ditado",
        "encerra ditado",
        "sair do ditado",
        "fechar ditado",
        "modo comando",
        "voltar comandos",
    }


def format_dictation_text(text: str) -> str:
    normalized = normalize_text(text)
    special_tokens = {
        "nova linha": "\r\n",
        "novo paragrafo": "\r\n\r\n",
        "novo parágrafo": "\r\n\r\n",
        "tabulacao": "\t",
        "tabulação": "\t",
        "tab": "\t",
    }
    if normalized in special_tokens:
        return special_tokens[normalized]
    return text.strip()


def is_transcription_artifact(text: str) -> bool:
    normalized = normalize_text(text)
    normalized_without_dots = normalized.replace(".", " ")
    artifacts = {
        "legendas pela comunidade de amara org",
        "legendas pela comunidade de amara.org",
        "aplicativos e sites esperados em portugues do brasil",
        "exemplos e sites esperados",
        "tem que ter o volume correto",
        "comandos curtos em portugues do brasil",
        "transcreva comandos curtos",
        "transcreva comandos curtos em portugues do brasil",
        "assistente local chamado estagiario",
        "vocabulario esperado",
    }

    return any(
        artifact in normalized or artifact in normalized_without_dots
        for artifact in artifacts
    )


def is_unreliable_conversation_text(text: str) -> bool:
    normalized = normalize_text(text)

    if is_transcription_artifact(text):
        return True

    if not normalized:
        return True

    words = normalized.split()
    if len(words) == 1 and len(normalized) <= 2:
        return True

    promptish_fragments = {
        "portugues do brasil",
        "comandos curtos",
        "sites esperados",
        "vocabulario esperado",
        "exemplos",
        "comunidade de amara",
    }
    if any(fragment in normalized for fragment in promptish_fragments):
        return True

    if len(words) >= 18:
        unique_ratio = len(set(words)) / max(1, len(words))
        if unique_ratio < 0.3 and "um dois" not in normalized:
            return True

    return False


def conversation_reply(user_input: str) -> str:
    normalized = normalize_text(user_input).strip(" .!?")

    if not normalized:
        return "Estou aqui."

    if "um dois" in normalized or "testando" in normalized or "teste de microfone" in normalized:
        return "Teste de microfone recebido. Estou te ouvindo."

    if normalized in {"exatamente", "isso", "isso ai", "e isso ai", "aham", "sim", "boa"} or (
        "isso" in normalized and len(normalized.split()) <= 3
    ):
        return "Peguei."

    if "tudo bem" in normalized or "como voce" in normalized or "como vc" in normalized:
        response = chat_response(user_input)
        return response or "Tudo bem por aqui. E voce?"

    if "bom dia" in normalized:
        response = chat_response(user_input)
        return response or "Bom dia."

    if "boa tarde" in normalized:
        response = chat_response(user_input)
        return response or "Boa tarde."

    if "boa noite" in normalized:
        response = chat_response(user_input)
        return response or "Boa noite."

    if difflib.SequenceMatcher(None, normalized, "qual o seu nome").ratio() >= 0.78:
        return "Meu nome e Estagiario."

    if any(phrase in normalized for phrase in {"quantos anos voce tem", "voce nasceu quando", "voce e novo"}):
        return "Bem, eu nasci ontem. Metaforicamente, pelo menos. Ainda estou aprendendo a ser util sem tropeÃ§ar nos cadarÃ§os."

    if any(phrase in normalized for phrase in {"voce pensa", "voce sente", "voce e consciente"}):
        return "Ainda nao chamaria isso de consciencia. Por enquanto, sou mais uma colecao organizada de impulsos tentando ser prestativa."

    response = chat_response(user_input)
    if response:
        return response

    return "Acho que eu ouvi meio torto. Repete de outro jeito?"


def append_multi_step_result(results, result):
    repeated_noise = {
        "Nao sei o que fechar.",
        "Pode repetir?",
        "Nao entendi.",
    }

    if result in repeated_noise and result in results:
        return

    results.append(result)


def maybe_learn_correction_for_last_voice(user_input: str) -> str | None:
    global last_voice_text

    normalized = normalize_text(user_input)
    prefixes = (
        "corrigir ultimo comando para ",
        "corrija ultimo comando para ",
        "corrigir ultima fala para ",
        "corrija ultima fala para ",
        "era para ser ",
        "eu quis dizer ",
    )

    target = None
    for prefix in prefixes:
        if normalized.startswith(prefix):
            target = user_input[len(prefix):].strip()
            break

    if not target:
        return None

    if not last_voice_text:
        return "Ainda nao tenho uma fala de voz para corrigir."

    remember_voice_correction(last_voice_text, target)
    learned_from = last_voice_text
    last_voice_text = ""
    return f"Aprendi: quando ouvir '{learned_from}', vou entender como '{target}'."


def handle_multi_step_request(user_input: str):
    local_steps = split_local_steps(user_input)
    plan = None

    if len(local_steps) > 1:
        plan = [route(step) for step in local_steps]
    elif "," in user_input:
        return None
    else:
        plan = plan_actions(user_input)

    if not plan or not isinstance(plan, list):
        return None

    results = []

    for step in plan:
        processed = process_action(step)

        if isinstance(processed, str):
            append_multi_step_result(results, processed)
            continue

        if processed.requires_confirmation:
            append_multi_step_result(
                results,
                f"Acao sensivel no plano bloqueada: {processed.action} {processed.params}",
            )
            continue

        append_multi_step_result(results, execute_command(processed))

    return "\n".join(results)


def execute_routine_steps(steps):
    if not isinstance(steps, list):
        return "Rotina invalida."

    results = []

    for step in steps:
        if not isinstance(step, str) or not step.strip():
            results.append("Etapa invalida na rotina.")
            continue

        raw_action = route(step)
        processed = process_action(raw_action)

        if isinstance(processed, str):
            results.append(processed)
            continue

        if processed.requires_confirmation:
            results.append(f"Etapa sensivel bloqueada: {processed.action}")
            continue

        results.append(execute_command(processed))

    return "\n".join(results)


def main():
    global last_voice_text
    global pending_command
    global pending_smart_open_choice
    global pending_smart_open_invalid_attempts
    global creating_macro, macro_name, macro_steps
    global hotword_ui_enabled
    global conversation_mode
    global conversation_ready_announced
    global dictation_mode
    global dictation_ready_announced
    global direct_response_ready_announced
    global repeat_listen_until
    global ui_hud_started

    voice_mode = "--voice" in sys.argv
    hotword_mode = "--hotword" in sys.argv
    ui_mode = "--ui" in sys.argv
    voice_paused = False
    hotword_ui_enabled = voice_mode and hotword_mode
    ui_hud_started = False

    if handle_voice_profile_cli():
        return

    if "--audio-test" in sys.argv or "--audio-diagnostic" in sys.argv:
        seconds = None
        for flag in ("--audio-test", "--audio-diagnostic"):
            if flag in sys.argv:
                index = sys.argv.index(flag)
                if index + 1 < len(sys.argv):
                    try:
                        seconds = float(sys.argv[index + 1])
                    except ValueError:
                        seconds = None
                break

        print("Gravando diagnostico de audio. Fale uma frase curta...")
        print(run_audio_diagnostic(seconds))
        return

    clear()
    reset_ui_state()
    refresh_ui_runtime_state({"visible": False})
    refresh_improvement_brain(force=True)

    if ui_mode:
        show_ui_hud()

    if voice_mode:
        if hotword_mode:
            mode_text = (
                f"Diga 'estagiario' ou fale tudo junto, como 'estagiario abre o chrome'."
                if HOTWORD_LISTENING_ENABLED
                else f"Aperte {HOTKEY_NAME} para falar."
            )
            output_response(
                f"Modo voz ativado. {mode_text} Aperte {TOGGLE_LISTENING_HOTKEY_NAME} para pausar/retomar.",
                voice_mode=False,
            )
            set_voice_status("ATIVA" if HOTWORD_LISTENING_ENABLED else f"BOTAO {HOTKEY_NAME}")
        else:
            output_response(
                "Modo voz ativado. Fale um comando ou digite se o microfone falhar.",
                voice_mode=False,
            )

        if bool(VOICE_PREFERENCES.get("startup_voice_greeting_enabled", True)):
            startup_message = str(
                VOICE_PREFERENCES.get(
                    "startup_voice_greeting",
                    "Sistemas online. Pronto para trabalhar.",
                )
            ).strip()
            if startup_message:
                output_response(startup_message, voice_mode=True)

        warm_common_tts_cache_async()

    refresh_ui_runtime_state()

    while True:
        try:
            inline_command = ""
            queued_user_input = poll_ui_text_command()
            if queued_user_input:
                terminal_print(f"Voce (painel): {queued_user_input}")
                user_input = queued_user_input
            else:
                user_input = ""

            direct_response_mode = (
                voice_mode
                and hotword_mode
                and not voice_paused
                and is_waiting_for_direct_response()
            )
            conversation_listen_mode = (
                voice_mode
                and hotword_mode
                and not voice_paused
                and conversation_mode
                and not direct_response_mode
            )
            dictation_listen_mode = (
                voice_mode
                and hotword_mode
                and not voice_paused
                and dictation_mode
                and not direct_response_mode
                and not conversation_mode
            )

            if queued_user_input:
                pass
            elif direct_response_mode:
                set_voice_status("RESPOSTA")
                repeat_prompt_mode = pending_command is None and pending_smart_open_choice is None
                user_input = read_user_input(
                    voice_mode,
                    announce_ready=not direct_response_ready_announced,
                    fallback_to_text=False,
                    ready_message="Pode repetir..." if repeat_prompt_mode else "Pode responder...",
                )
                repeat_listen_until = 0.0
                direct_response_ready_announced = True
            elif conversation_listen_mode:
                set_voice_status("CONVERSA")
                user_input = read_user_input(
                    voice_mode,
                    announce_ready=not conversation_ready_announced,
                    fallback_to_text=False,
                    ready_message="Pode falar comigo...",
                    ignored_text_filter=is_unreliable_conversation_text,
                    listener=listen_conversation_once,
                )
                conversation_ready_announced = True
            elif dictation_listen_mode:
                set_voice_status("DITADO")
                user_input = read_user_input(
                    voice_mode,
                    announce_ready=not dictation_ready_announced,
                    fallback_to_text=False,
                    ready_message="Pode ditar...",
                    ignored_text_filter=is_transcription_artifact,
                    listener=listen_conversation_once,
                )
                dictation_ready_announced = True
            elif voice_mode and hotword_mode:
                should_continue, voice_paused, inline_command = wait_for_hotword(
                    voice_mode,
                    hotword_mode,
                    voice_paused,
                )
                if not should_continue:
                    hotword_ui_enabled = False
                    clear_status_line()
                    break
            if not direct_response_mode and not conversation_listen_mode and not dictation_listen_mode and voice_mode and hotword_mode and inline_command:
                terminal_print(f"Voce (voz): {inline_command}")
                user_input = inline_command
            elif not queued_user_input and not direct_response_mode and not conversation_listen_mode and not dictation_listen_mode:
                user_input = read_user_input(
                    voice_mode,
                    announce_ready=not hotword_mode,
                    fallback_to_text=not hotword_mode,
                )
        except KeyboardInterrupt:
            hotword_ui_enabled = False
            clear_status_line()
            output_response("Encerrando.", voice_mode=False)
            break

        if user_input.lower() in ["sair", "exit"]:
            hotword_ui_enabled = False
            clear_status_line()
            output_response("Encerrando.", voice_mode)
            break

        if not user_input:
            continue

        if is_transcription_artifact(user_input):
            continue

        log_execution_event(
            "user_input",
            text=user_input,
            voice_mode=voice_mode,
            mode=current_ui_mode_label(),
        )

        correction_response = maybe_learn_correction_for_last_voice(user_input)
        if correction_response:
            output_response(correction_response, voice_mode)
            continue

        pronunciation_response = maybe_handle_pronunciation_command(user_input)
        if pronunciation_response:
            output_response(pronunciation_response, voice_mode)
            continue

        humor_response = maybe_handle_humor_command(user_input)
        if humor_response:
            output_response(humor_response, voice_mode)
            continue

        input_device_response = maybe_handle_input_device_command(user_input)
        if input_device_response:
            output_response(input_device_response, voice_mode)
            continue

        voice_profile_response = maybe_handle_voice_profile_command(user_input)
        if voice_profile_response:
            output_response(voice_profile_response, voice_mode)
            continue

        ui_response = maybe_handle_ui_command(user_input)
        if ui_response:
            output_response(ui_response, voice_mode)
            continue

        auto_advance_response = maybe_handle_auto_advance_command(user_input)
        if auto_advance_response:
            refresh_improvement_brain(force=True)
            output_response(auto_advance_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        bottleneck_response = maybe_handle_bottleneck_command(user_input)
        if bottleneck_response:
            refresh_improvement_brain(force=True)
            output_response(bottleneck_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        patch_proposal_response = maybe_handle_patch_proposal_command(user_input)
        if patch_proposal_response:
            refresh_improvement_brain(force=True)
            output_response(patch_proposal_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        action_candidate_response = maybe_handle_action_candidate_command(user_input)
        if action_candidate_response:
            refresh_improvement_brain(force=True)
            output_response(action_candidate_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        execution_package_response = maybe_handle_execution_package_command(user_input)
        if execution_package_response:
            refresh_improvement_brain(force=True)
            output_response(execution_package_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        implementation_handoff_response = maybe_handle_implementation_handoff_command(user_input)
        if implementation_handoff_response:
            refresh_improvement_brain(force=True)
            output_response(implementation_handoff_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        handoff_application_response = maybe_handle_handoff_application_command(user_input)
        if handoff_application_response:
            refresh_improvement_brain(force=True)
            output_response(handoff_application_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        handoff_validation_response = maybe_handle_handoff_validation_command(user_input)
        if handoff_validation_response:
            refresh_improvement_brain(force=True)
            output_response(handoff_validation_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        handoff_retry_response = maybe_handle_handoff_retry_command(user_input)
        if handoff_retry_response:
            refresh_improvement_brain(force=True)
            output_response(handoff_retry_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        codex_implementation_request_response = maybe_handle_codex_implementation_request_command(user_input)
        if codex_implementation_request_response:
            refresh_improvement_brain(force=True)
            output_response(codex_implementation_request_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        approval_gate_response = maybe_handle_approval_gate_command(user_input)
        if approval_gate_response:
            refresh_improvement_brain(force=True)
            output_response(approval_gate_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        verification_response = maybe_handle_verification_command(user_input)
        if verification_response:
            refresh_improvement_brain(force=True)
            output_response(verification_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        codex_bridge_response = maybe_handle_codex_bridge_command(user_input)
        if codex_bridge_response:
            refresh_improvement_brain(force=True)
            output_response(codex_bridge_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        self_evolution_response = maybe_handle_self_evolution_command(user_input)
        if self_evolution_response:
            refresh_improvement_brain(force=True)
            output_response(self_evolution_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        directives_response = maybe_handle_directives_command(user_input)
        if directives_response:
            output_response(directives_response, voice_mode)
            continue

        operational_context_response = maybe_handle_operational_context_command(user_input)
        if operational_context_response:
            refresh_improvement_brain(force=True)
            output_response(operational_context_response, voice_mode)
            maybe_announce_codex_suggestion(voice_mode)
            continue

        if is_dictation_stop(user_input):
            dictation_mode = False
            dictation_ready_announced = False
            if hotword_mode and not conversation_mode:
                set_voice_status(f"BOTAO {HOTKEY_NAME}")
            output_response("Modo ditado encerrado.", voice_mode)
            continue

        if dictation_mode:
            dictated_text = format_dictation_text(user_input)
            result = type_text(dictated_text)
            if result != "Texto inserido no campo ativo.":
                output_response(result, voice_mode=False)
            continue

        if is_dictation_start(user_input):
            dictation_mode = True
            dictation_ready_announced = False
            conversation_mode = False
            conversation_ready_announced = False
            if hotword_mode:
                set_voice_status("DITADO")
            output_response("Modo ditado ativado. Pode falar sem apertar F8. Para sair, diga parar ditado.", voice_mode)
            continue

        if conversation_mode and is_conversation_stop(user_input):
            conversation_mode = False
            conversation_ready_announced = False
            if hotword_mode:
                set_voice_status(f"BOTAO {HOTKEY_NAME}")
            output_response("Modo conversa encerrado. Voltei para comandos.", voice_mode)
            continue

        if conversation_mode and not is_waiting_for_direct_response():
            output_response(conversation_reply(user_input), voice_mode)
            continue

        if pending_command is not None:
            if is_confirmation_yes(user_input):
                result = execute_command(pending_command, voice_mode=voice_mode)
                pending_command = None
                direct_response_ready_announced = False
                output_response(result, voice_mode)
                continue

            if is_confirmation_no(user_input):
                pending_command = None
                direct_response_ready_announced = False
                output_response("Acao cancelada.", voice_mode)
                continue

            output_response("Responda com sim ou nao.", voice_mode)
            continue

        if pending_smart_open_choice is not None:
            if is_confirmation_no(user_input):
                pending_smart_open_choice = None
                pending_smart_open_invalid_attempts = 0
                direct_response_ready_announced = False
                output_response("Ok, nao abri.", voice_mode)
                continue

            kind = smart_open_choice_kind(user_input)

            if not kind:
                pending_smart_open_invalid_attempts += 1
                if pending_smart_open_invalid_attempts >= 2:
                    pending_smart_open_choice = None
                    pending_smart_open_invalid_attempts = 0
                    direct_response_ready_announced = False
                    output_response("Nao consegui entender a resposta. Cancelei essa pergunta.", voice_mode)
                    continue

                output_response("Responda com app, site ou cancelar.", voice_mode)
                continue

            raw_action = {
                "intent": "smart_open_choice",
                "target": {
                    "name": pending_smart_open_choice,
                    "kind": kind,
                },
            }
            pending_smart_open_choice = None
            pending_smart_open_invalid_attempts = 0
            direct_response_ready_announced = False
            processed = process_action(raw_action)

            if isinstance(processed, str):
                output_response(processed, voice_mode)
                continue

            result = execute_command(processed, voice_mode=voice_mode)
            output_response(result, voice_mode)
            continue

        original_user_input = user_input
        user_input = maybe_normalize_voice_command(user_input, voice_mode)
        if original_user_input != user_input:
            log_execution_event(
                "voice_input_normalized",
                original=original_user_input,
                normalized=user_input,
            )
        if voice_mode and original_user_input == user_input:
            last_voice_text = original_user_input
        refresh_ui_runtime_state({"last_command": user_input})

        if creating_macro:
            if user_input.lower().strip() == "fim":
                add_macro(macro_name, macro_steps)
                output_response(
                    f"Macro '{macro_name}' criada com {len(macro_steps)} passos.",
                    voice_mode,
                )
                creating_macro = False
                macro_name = None
                macro_steps = []
                continue

            raw_action = route(user_input)

            if raw_action.get("intent") in {"start_macro", "run_macro", "run_routine"}:
                output_response(
                    "Esse comando nao pode ser adicionado dentro da macro.",
                    voice_mode,
                )
                continue

            processed = process_action(raw_action)

            if isinstance(processed, str):
                output_response(f"Passo invalido: {processed}", voice_mode)
                continue

            macro_steps.append(raw_action)
            output_response("Passo adicionado.", voice_mode)
            continue

        start_macro = detect_create_macro_start(user_input)
        if start_macro:
            creating_macro = True
            macro_name = start_macro["target"]
            macro_steps = []
            output_response(
                f"Criando macro '{macro_name}'. Digite ou fale comandos e finalize com 'fim'.",
                voice_mode,
            )
            continue

        if pending_command is not None:
            if is_confirmation_yes(user_input):
                result = execute_command(pending_command, voice_mode=voice_mode)
                pending_command = None
                output_response(result, voice_mode)
                continue

            if is_confirmation_no(user_input):
                pending_command = None
                output_response("Acao cancelada.", voice_mode)
                continue

            output_response("Responda com 'sim' ou 'nao'.", voice_mode)
            continue

        if pending_smart_open_choice is not None:
            kind = smart_open_choice_kind(user_input)

            if is_confirmation_no(user_input):
                pending_smart_open_choice = None
                output_response("Ok, nao abri.", voice_mode)
                continue

            if not kind:
                output_response("Responda com 'app' ou 'site'.", voice_mode)
                continue

            raw_action = {
                "intent": "smart_open_choice",
                "target": {
                    "name": pending_smart_open_choice,
                    "kind": kind,
                },
            }
            pending_smart_open_choice = None
            processed = process_action(raw_action)

            if isinstance(processed, str):
                output_response(processed, voice_mode)
                continue

            result = execute_command(processed, voice_mode=voice_mode)
            output_response(result, voice_mode)
            continue

        if looks_like_multi_step_request(user_input):
            result = handle_multi_step_request(user_input)
            if result:
                output_response(result, voice_mode)
                continue

        raw_action = route(user_input)
        log_execution_event(
            "route_result",
            input=user_input,
            intent=raw_action.get("intent"),
            target=raw_action.get("target"),
        )

        if raw_action.get("intent") == "run_routine":
            result = execute_routine_steps(raw_action.get("target"))
            output_response(result, voice_mode)
            continue

        if raw_action.get("intent") == "start_conversation":
            conversation_mode = True
            conversation_ready_announced = False
            clear_chat_history()
            output_response("Modo conversa ativado. Pode falar sem apertar F8. Para sair, diga parar conversa.", voice_mode)
            continue

        if raw_action.get("intent") == "stop_conversation":
            conversation_mode = False
            conversation_ready_announced = False
            output_response("Modo conversa encerrado. Voltei para comandos.", voice_mode)
            continue

        if raw_action.get("intent") == "repeat_last":
            if runtime_state.last_command is None:
                output_response("Nada para repetir.", voice_mode)
                continue

            result = execute_command(deepcopy(runtime_state.last_command), voice_mode=voice_mode)
            output_response(result, voice_mode)
            continue

        processed = process_action(raw_action)

        if isinstance(processed, str):
            output_response(processed, voice_mode)
            continue

        if processed.action == "smart_open" and smart_open_needs_choice(processed.params.get("target")):
            pending_smart_open_choice = processed.params.get("target")
            pending_smart_open_invalid_attempts = 0
            direct_response_ready_announced = False
            output_response(
                f"Primeira vez que vejo {pending_smart_open_choice}. Quer abrir como app ou site?",
                voice_mode,
            )
            continue

        if processed.requires_confirmation:
            pending_command = processed
            direct_response_ready_announced = False
            output_response(
                f"Confirma a acao {processed.action} com {processed.params}?",
                voice_mode,
            )
            continue

        result = execute_command(processed, voice_mode=voice_mode)
        output_response(result, voice_mode)


if __name__ == "__main__":
    main()
