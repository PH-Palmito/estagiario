import subprocess
import sys
import time
from copy import deepcopy
import difflib
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
    enqueue_current_codex_message,
    load_codex_outbox,
    mark_next_codex_message_sent,
    sync_codex_outbox,
)
from memory.codex_inbox import add_codex_inbox_item, clear_codex_inbox, load_codex_inbox
from memory.macros import add_macro
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

creating_macro = False
macro_name = None
macro_steps = []
VOICE_PREFERENCES = load_voice_preferences()


def process_action(raw_action: dict):
    if not isinstance(raw_action, dict):
        return "Acao invalida."

    command = normalize_action(raw_action)
    command = resolve_params(command, runtime_state)

    ok, error = validate_command(command)
    if not ok:
        return error

    return command


def execute_command(command):
    result = execute(command)
    runtime_state.update(command, result)
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
    styled_message = style_response(message)
    terminal_print(f"IA: {styled_message}")
    append_ui_history("assistant", styled_message)
    refresh_ui_runtime_state({"last_response": styled_message})
    refresh_improvement_brain()

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
        "atualizar plano de auto evolucao",
        "gerar plano de auto evolucao",
    }:
        plan = save_self_evolution_plan()
        focus = str(plan.get("current_focus", "")).strip()
        if focus:
            return f"Atualizei o plano de auto evolucao. Foco atual: {focus}."
        return "Atualizei o plano de auto evolucao do Axel."

    return None


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
        sync_approval_gate()
        sync_verification_runs()
        save_codex_request()
        save_codex_channel()
        sync_codex_outbox()
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

    append_ui_history("user", queued)
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
            append_ui_history("user", typed)
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
        append_ui_history("user", text)
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
        append_ui_history("user", typed)
        refresh_ui_runtime_state({"last_heard": typed})
    return typed


def maybe_normalize_voice_command(user_input: str, voice_mode: bool) -> str:
    if not voice_mode:
        return user_input

    learned = apply_voice_correction(user_input)
    if learned:
        return learned

    normalized_candidate = normalize_voice_command(user_input)
    protected_voice_commands = {
        "o que tem na tela",
        "resuma a tela",
        "detalha a tela",
        "proximos avancos",
        "pedido ao codex",
        "conversa com codex",
        "canal com codex",
        "sugestao do codex",
        "fila do codex",
        "inbox do codex",
        "plano de auto evolucao",
        "mostrar gargalos",
        "atualizar gargalos",
        "propostas de patch",
        "mostrar propostas de patch",
        "acoes candidatas",
        "mostrar acoes candidatas",
        "proposta atual",
        "aprovar proposta atual",
        "rejeitar proposta atual",
        "status da verificacao",
        "verificar melhoria",
        "melhoria funcionou",
        "melhoria falhou",
        "replanejar melhoria",
    }
    if normalized_candidate in protected_voice_commands or normalized_candidate.startswith("pesquisar"):
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
    return pending_command is not None or pending_smart_open_choice is not None


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
                user_input = read_user_input(
                    voice_mode,
                    announce_ready=not direct_response_ready_announced,
                    fallback_to_text=False,
                    ready_message="Pode responder...",
                )
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
            elif not direct_response_mode and not conversation_listen_mode and not dictation_listen_mode:
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
                result = execute_command(pending_command)
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

            result = execute_command(processed)
            output_response(result, voice_mode)
            continue

        original_user_input = user_input
        user_input = maybe_normalize_voice_command(user_input, voice_mode)
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
                result = execute_command(pending_command)
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

            result = execute_command(processed)
            output_response(result, voice_mode)
            continue

        if looks_like_multi_step_request(user_input):
            result = handle_multi_step_request(user_input)
            if result:
                output_response(result, voice_mode)
                continue

        raw_action = route(user_input)

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

            result = execute_command(deepcopy(runtime_state.last_command))
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

        result = execute_command(processed)
        output_response(result, voice_mode)


if __name__ == "__main__":
    main()
