import sys
import time
from copy import deepcopy
import difflib
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
from memory.macros import add_macro
from memory.piper_voice_manager import (
    apply_piper_voice,
    download_piper_voice,
    list_piper_voices,
)
from memory.session import clear
from memory.voice_corrections import apply_voice_correction, remember_voice_correction
from memory.voice_preferences import load_voice_preferences, update_voice_preferences
from memory.voice_profiles import apply_voice_profile, list_voice_profiles
from tools.smart_open_tools import smart_open_needs_choice
from voice.windows_voice import (
    HOTKEY_NAME,
    HOTWORD_LISTENING_ENABLED,
    consume_hotkey_press,
    consume_toggle_listening_hotkey_press,
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
direct_response_ready_announced = False
last_voice_text = ""

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


def pronunciation_test_response() -> str:
    return (
        "Teste de pronúncia. "
        "GitHub, YouTube, WhatsApp Web, Steam, Chrome, Python, Google Colab, OpenAI, PowerShell, Android Studio, Wi-Fi e Bluetooth. "
        "Agora, siglas técnicas. "
        "LLM, CPU, GPU, NFC, SSD, USB, HDMI, OCR, API, URL, HTTP e HTTPS. "
        "E por fim, unidades. "
        "Seis mil e quinhentos miliampere hora. "
        "Cento e vinte watt hora."
    )


def maybe_handle_pronunciation_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    if normalized in {
        "testar pronuncia",
        "teste de pronuncia",
        "teste pronuncia",
        "testar pronunciacao",
        "teste de pronunciacao",
        "testar ingles",
        "teste ingles",
        "testar siglas",
        "teste siglas",
    }:
        return pronunciation_test_response()

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


def set_voice_status(status: str):
    global voice_status

    if voice_status == status:
        return

    voice_status = status
    render_status_line()


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
        return terminal_input("Voce: ")

    if announce_ready:
        terminal_print(f"IA: {ready_message}")
    listen = listener or listen_once
    heard = listen()

    if heard.ok:
        text = heard.text.strip()
        if ignored_text_filter and ignored_text_filter(text):
            return ""
        terminal_print(f"Voce (voz): {text}")
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
    return typed


def maybe_normalize_voice_command(user_input: str, voice_mode: bool) -> str:
    if not voice_mode:
        return user_input

    learned = apply_voice_correction(user_input)
    if learned:
        return learned

    normalized_candidate = normalize_voice_command(user_input)

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
    global direct_response_ready_announced

    voice_mode = "--voice" in sys.argv
    hotword_mode = "--hotword" in sys.argv
    voice_paused = False
    hotword_ui_enabled = voice_mode and hotword_mode

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

    while True:
        try:
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

            if direct_response_mode:
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
            if not direct_response_mode and not conversation_listen_mode and voice_mode and hotword_mode and inline_command:
                terminal_print(f"Voce (voz): {inline_command}")
                user_input = inline_command
            elif not direct_response_mode and not conversation_listen_mode:
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

        voice_profile_response = maybe_handle_voice_profile_command(user_input)
        if voice_profile_response:
            output_response(voice_profile_response, voice_mode)
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
