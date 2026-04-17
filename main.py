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
from memory.session import clear
from tools.smart_open_tools import smart_open_needs_choice
from voice.windows_voice import (
    HOTKEY_NAME,
    HOTWORD_LISTENING_ENABLED,
    consume_hotkey_press,
    consume_toggle_listening_hotkey_press,
    listen_for_hotword,
    listen_once,
    play_activation_sound,
    run_audio_diagnostic,
    speak,
    TOGGLE_LISTENING_HOTKEY_NAME,
)


runtime_state = RuntimeState()
pending_command = None
pending_smart_open_choice = None
voice_status = None
hotword_ui_enabled = False
rendered_status_line = ""
conversation_mode = False
conversation_ready_announced = False

creating_macro = False
macro_name = None
macro_steps = []


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
    return text.lower().strip() in {"sim", "s", "confirmar", "ok", "pode"}


def is_confirmation_no(text: str) -> bool:
    return text.lower().strip() in {"nao", "não", "n", "cancelar"}


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


def output_response(message: str, voice_mode: bool):
    terminal_print(f"IA: {message}")

    quiet_messages = {
        "Nao entendi.",
        "Pode repetir?",
        "Nao identifiquei o comando.",
    }

    if voice_mode and message not in quiet_messages:
        speak(message)


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
) -> str:
    if not voice_mode:
        return terminal_input("Voce: ")

    if announce_ready:
        terminal_print(f"IA: {ready_message}")
    heard = listen_once()

    if heard.ok:
        terminal_print(f"Voce (voz): {heard.text}")
        return heard.text.strip()

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

    raw_action = route(user_input)
    if raw_action.get("intent") != "respond":
        return user_input

    if raw_action.get("response") not in {
        "Nao entendi.",
        "Pode repetir?",
        "Nao identifiquei o comando.",
    }:
        return user_input

    normalized = normalize_voice_command(user_input)
    return normalized or user_input


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
        "transcreva comandos curtos",
        "transcreva comandos curtos em portugues do brasil",
        "assistente local chamado estagiario",
        "vocabulario esperado",
    }

    return any(
        artifact in normalized or artifact in normalized_without_dots
        for artifact in artifacts
    )


def conversation_reply(user_input: str) -> str:
    normalized = normalize_text(user_input)

    if not normalized:
        return "Estou aqui."

    if "um dois" in normalized or "testando" in normalized or "teste de microfone" in normalized:
        return "Teste de microfone recebido. Estou te ouvindo."

    if "tudo bem" in normalized:
        return "Tudo bem por aqui. Estou em modo conversa, sem executar comandos por acidente."

    if "bom dia" in normalized:
        return "Bom dia. Estou aqui, mais para papo do que para apertar botao agora."

    if "boa tarde" in normalized:
        return "Boa tarde. Pode conversar comigo sem cerimônia."

    if "boa noite" in normalized:
        return "Boa noite. Modo conversa tranquilo ativado."

    if difflib.SequenceMatcher(None, normalized, "qual o seu nome").ratio() >= 0.78:
        return "Meu nome e Estagiario. Ainda junior, mas ja com algumas manias de assistente."

    if "estimado usuario" in normalized:
        return "Estimado usuario foi um floreio inesperado, mas confesso que teve seu charme."

    response = chat_response(user_input)
    if response:
        return response

    return "Estou sem acesso ao meu raciocinio local agora, mas ainda consigo te ouvir. Me fala de um jeito simples."


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
            results.append(processed)
            continue

        if processed.requires_confirmation:
            results.append(
                f"Acao sensivel no plano bloqueada: {processed.action} {processed.params}"
            )
            continue

        results.append(execute_command(processed))

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
    global pending_command
    global pending_smart_open_choice
    global creating_macro, macro_name, macro_steps
    global hotword_ui_enabled
    global conversation_mode
    global conversation_ready_announced

    voice_mode = "--voice" in sys.argv
    hotword_mode = "--hotword" in sys.argv
    voice_paused = False
    hotword_ui_enabled = voice_mode and hotword_mode

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
                    announce_ready=True,
                    fallback_to_text=False,
                    ready_message="Pode responder...",
                )
            elif conversation_listen_mode:
                set_voice_status("CONVERSA")
                user_input = read_user_input(
                    voice_mode,
                    announce_ready=not conversation_ready_announced,
                    fallback_to_text=False,
                    ready_message="Pode falar comigo...",
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

        user_input = maybe_normalize_voice_command(user_input, voice_mode)

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
            output_response(
                f"Primeira vez que vejo {pending_smart_open_choice}. Quer abrir como app ou site?",
                voice_mode,
            )
            continue

        if processed.requires_confirmation:
            pending_command = processed
            output_response(
                f"Confirma a acao {processed.action} com {processed.params}?",
                voice_mode,
            )
            continue

        result = execute_command(processed)
        output_response(result, voice_mode)


if __name__ == "__main__":
    main()
