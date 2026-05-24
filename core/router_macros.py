from __future__ import annotations

from core.router_utils import normalize_text
from memory.macros import delete_macro, get_macro, list_macros
from memory.routines import get_routine, list_routines


def detect_create_macro_start(user_input: str):
    lower = normalize_text(user_input)
    if lower.startswith("crie macro "):
        name = user_input[len("crie macro "):].strip()
        if name:
            return {"intent": "start_macro", "target": name}
    return None


def detect_run_macro(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["executar ", "execute ", "rode ", "rodar "]:
        if lower.startswith(prefix):
            name = user_input[len(prefix):].strip()
            macro = get_macro(name)
            if macro:
                return {"intent": "run_macro", "target": macro}
    return None


def detect_run_routine(user_input: str):
    lower = normalize_text(user_input)

    if lower in {"listar rotinas", "liste as rotinas", "quais rotinas", "ver rotinas"}:
        names = list_routines()
        if names:
            return {"intent": "respond", "target": None, "response": "Rotinas: " + ", ".join(names)}
        return {"intent": "respond", "target": None, "response": "Nenhuma rotina salva."}

    routine = get_routine(lower)
    if routine:
        return {"intent": "run_routine", "target": routine, "name": lower}

    for prefix in {"modo ", "rotina ", "executar rotina ", "executa rotina ", "rode rotina "}:
        if lower.startswith(prefix):
            name = lower[len(prefix):].strip()
            candidates = [name, f"modo {name}"]
            for candidate in candidates:
                routine = get_routine(candidate)
                if routine:
                    return {"intent": "run_routine", "target": routine, "name": candidate}

    return None


def detect_list_macros(user_input: str):
    lower = normalize_text(user_input)
    if lower in {"listar macros", "liste as macros", "quais macros", "ver macros"}:
        names = list_macros()
        if names:
            return {"intent": "respond", "target": None, "response": "Macros: " + ", ".join(names)}
        return {"intent": "respond", "target": None, "response": "Nenhuma macro salva."}
    return None


def detect_delete_macro(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["delete macro ", "apague macro ", "remova macro "]:
        if lower.startswith(prefix):
            name = user_input[len(prefix):].strip()
            if not name:
                return None
            ok = delete_macro(name)
            if ok:
                return {"intent": "respond", "target": None, "response": f"Macro '{name}' removida."}
            return {"intent": "respond", "target": None, "response": f"Macro '{name}' nao encontrada."}
    return None


MACRO_DETECTORS = (
    detect_create_macro_start,
    detect_run_routine,
    detect_run_macro,
    detect_list_macros,
    detect_delete_macro,
)
