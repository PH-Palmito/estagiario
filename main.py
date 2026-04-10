import sys
from copy import deepcopy

from core.context_resolver import resolve_params
from core.executor import execute
from core.normalizer import normalize_action
from core.planner import looks_like_multi_step_request, plan_actions, split_local_steps
from core.router import detect_create_macro_start, route
from core.runtime_state import RuntimeState
from core.validator import validate_command
from memory.macros import add_macro
from memory.session import clear
from voice.windows_voice import listen_once, speak


runtime_state = RuntimeState()
pending_command = None

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


def output_response(message: str, voice_mode: bool):
    print("IA:", message)

    if voice_mode:
        speak(message)


def read_user_input(voice_mode: bool) -> str:
    if not voice_mode:
        return input("Voce: ").strip()

    print("IA: Pode falar...")
    heard = listen_once()

    if heard.ok:
        print(f"Voce (voz): {heard.text}")
        return heard.text.strip()

    print(f"IA: {heard.error}")
    typed = input("Voce (texto): ").strip()
    return typed


def handle_multi_step_request(user_input: str):
    local_steps = split_local_steps(user_input)
    plan = None

    if len(local_steps) > 1:
        plan = [route(step) for step in local_steps]
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


def main():
    global pending_command
    global creating_macro, macro_name, macro_steps

    voice_mode = "--voice" in sys.argv

    clear()

    if voice_mode:
        output_response(
            "Modo voz ativado. Fale um comando ou digite se o microfone falhar.",
            voice_mode=False,
        )

    while True:
        try:
            user_input = read_user_input(voice_mode)
        except KeyboardInterrupt:
            output_response("Encerrando.", voice_mode=False)
            break

        if user_input.lower() in ["sair", "exit"]:
            output_response("Encerrando.", voice_mode)
            break

        if not user_input:
            continue

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

            if raw_action.get("intent") in {"start_macro", "run_macro"}:
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

        if looks_like_multi_step_request(user_input):
            result = handle_multi_step_request(user_input)
            if result:
                output_response(result, voice_mode)
                continue

        raw_action = route(user_input)

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
