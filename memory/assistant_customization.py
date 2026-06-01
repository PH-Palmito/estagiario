from __future__ import annotations

from pathlib import Path

from core.router_utils import normalize_text
from memory.json_store import read_json_file, update_json_file, write_json_atomic

CUSTOMIZATION_PATH = Path("memory") / "assistant_customization.json"

DEFAULT_AXEL_INTRODUCTION = (
    "Prazer, eu sou o Axel, o assistente local do Pedro. "
    "Eu escuto comandos por voz, abro aplicativos e sites, controlo o navegador, leio telas, organizo contexto, lembro preferencias e ajudo em estudos, codigo, rotina e investimentos. "
    "Minha funcao e tirar atrito do caminho: transformar frases soltas em acoes uteis, sem perder o contexto do que o Pedro esta tentando construir. "
    "Exemplo de uso: pergunte 'Axel, o que temos para hoje?' e eu preparo um panorama com clima, agenda, carteira e foco do dia."
)


def _load() -> dict:
    return read_json_file(CUSTOMIZATION_PATH, {}, validator=lambda value: isinstance(value, dict))


def get_axel_introduction() -> str:
    introduction = str(_load().get("axel_introduction") or "").strip()
    return introduction or DEFAULT_AXEL_INTRODUCTION


def set_axel_introduction(text: str) -> bool:
    text = str(text or "").strip()
    if not text:
        return False

    def update(data: dict) -> dict:
        data["axel_introduction"] = text
        return data

    update_json_file(CUSTOMIZATION_PATH, {}, update, validator=lambda value: isinstance(value, dict), indent=2)
    return True


def reset_axel_introduction() -> None:
    data = _load()
    data.pop("axel_introduction", None)
    write_json_atomic(CUSTOMIZATION_PATH, data, indent=2, trailing_newline=True)


def remember_direct_response(trigger: str, response: str) -> bool:
    trigger = normalize_text(trigger).strip(" .")
    response = str(response or "").strip()
    if not trigger or not response:
        return False

    def update(data: dict) -> dict:
        responses = data.setdefault("direct_responses", {})
        responses[trigger] = response
        return data

    update_json_file(CUSTOMIZATION_PATH, {}, update, validator=lambda value: isinstance(value, dict), indent=2)
    return True


def get_direct_response(text: str) -> str | None:
    trigger = normalize_text(text).strip(" .")
    response = (_load().get("direct_responses") or {}).get(trigger)
    return str(response).strip() if response else None
