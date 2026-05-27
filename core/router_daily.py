from __future__ import annotations

import re
from urllib.parse import quote_plus

from core.router_utils import normalize_text
from memory.profile import get_value


def _default_profile_location() -> str:
    return str(get_value("cidade") or "").strip() or "Salvador"


def _extract_location_fragment(text: str, prefixes: tuple[str, ...]) -> str | None:
    normalized = normalize_text(text)
    for prefix in prefixes:
        if normalized.startswith(prefix):
            location = text[len(prefix):].strip(" .,:;-")
            if location:
                return location
    return None


def detect_weather_command(user_input: str):
    lower = normalize_text(user_input)
    direct_prefixes = (
        "como esta o clima em ",
        "qual o clima em ",
        "qual e o clima em ",
        "qual a temperatura em ",
        "qual a temperatura de ",
        "temperatura em ",
        "tempo em ",
        "previsao do tempo em ",
        "vai chover em ",
        "como vai ficar o tempo em ",
        "clima em ",
    )
    location = _extract_location_fragment(user_input, direct_prefixes)

    if not location and lower in {
        "como esta o clima",
        "qual o clima",
        "qual e o clima",
        "qual a temperatura",
        "previsao do tempo",
        "tempo agora",
        "vai chover",
        "clima",
    }:
        location = _default_profile_location()

    if not location:
        return None

    return {"intent": "weather_summary", "target": location}


def detect_briefing_command(user_input: str):
    lower = normalize_text(user_input)
    if lower in {
        "briefing em segundo plano",
        "briefing no background",
        "rode o briefing em segundo plano",
        "gerar briefing em segundo plano",
        "preparar briefing em segundo plano",
    }:
        return {"intent": "background_daily_briefing", "target": None}

    if lower in {
        "rotina diaria",
        "minha rotina diaria",
        "comecar o dia",
        "comecar meu dia",
        "iniciar o dia",
        "preparar meu dia",
        "prepara meu dia",
        "bom dia axel",
        "bom dia estagiario",
    }:
        return {"intent": "daily_routine", "target": None}

    if lower in {
        "briefing",
        "briefing do dia",
        "me de o briefing",
        "me da o briefing",
        "me de meu briefing",
        "me da meu briefing",
        "resumo do dia",
        "panorama do dia",
    }:
        return {"intent": "daily_briefing", "target": None}
    return None


def detect_agenda_command(user_input: str):
    lower = normalize_text(user_input)
    add_prefixes = (
        "adicionar na agenda ",
        "adicionar compromisso ",
        "adiciona na agenda ",
        "adiciona compromisso ",
        "marcar na agenda ",
        "marque na agenda ",
        "anotar na agenda ",
        "anote na agenda ",
    )
    for prefix in add_prefixes:
        if lower.startswith(prefix):
            text = user_input[len(prefix):].strip()
            if not text:
                return {"intent": "respond", "target": None, "response": "Qual compromisso devo registrar?"}
            return {"intent": "agenda_add", "target": text}

    if lower in {"agenda de hoje", "compromissos de hoje", "o que eu tenho hoje"}:
        return {"intent": "agenda_list_today", "target": None}

    if lower in {"agenda de amanha", "compromissos de amanha"}:
        return {"intent": "agenda_list_tomorrow", "target": None}

    if lower in {"agenda", "minha agenda", "listar agenda", "meus compromissos", "proximos compromissos"}:
        return {"intent": "agenda_list_all", "target": None}

    remove_match = re.match(
        r"^(?:remover|remove|tirar|tire|apagar|apague)\s+(?:compromisso|item)\s+(\d+)(?:\s+da\s+agenda)?(?:\s+de\s+(hoje|amanha))?$",
        lower,
    )
    if remove_match:
        scope = "tomorrow" if remove_match.group(2) == "amanha" else "today"
        return {
            "intent": "agenda_remove",
            "target": {
                "index": remove_match.group(1),
                "scope": scope,
            },
        }

    return None


def detect_reminder_command(user_input: str):
    lower = normalize_text(user_input)
    add_patterns = (
        r"^(?:me\s+)?(?:lembre|lembra|lembrar)\s+(?:de\s+|que\s+)?(.+)$",
        r"^(?:me\s+)?(?:avise|avisa|avisar)\s+(?:de\s+|que\s+)?(.+)$",
    )
    for pattern in add_patterns:
        match = re.match(pattern, lower)
        if match:
            text = user_input[match.start(1):].strip()
            if not text:
                return {"intent": "respond", "target": None, "response": "O que devo lembrar?"}
            return {"intent": "reminder_add", "target": text}

    if lower in {"lembretes", "meus lembretes", "listar lembretes", "quais lembretes", "lembretes pendentes"}:
        return {"intent": "reminder_list", "target": None}

    remove_match = re.match(
        r"^(?:remover|remove|tirar|tire|apagar|apague)\s+(?:lembrete|aviso)\s+(\d+)$",
        lower,
    )
    if remove_match:
        return {"intent": "reminder_remove", "target": {"index": remove_match.group(1)}}

    return None


def detect_map_command(user_input: str):
    lower = normalize_text(user_input)

    route_match = re.search(r"\brota de (.+?) para (.+)$", lower)
    if route_match:
        origin = route_match.group(1).strip(" .,:;-")
        destination = route_match.group(2).strip(" .,:;-")
        if origin and destination:
            return {
                "intent": "ui_show_map",
                "target": {
                    "kind": "route",
                    "origin": origin,
                    "destination": destination,
                    "label": f"{origin} -> {destination}",
                    "url": (
                        "https://www.google.com/maps/dir/?api=1"
                        f"&origin={quote_plus(origin)}&destination={quote_plus(destination)}"
                    ),
                },
            }

    map_prefixes = (
        "mostrar no mapa ",
        "mostra no mapa ",
        "me mostra no mapa ",
        "mostrar mapa de ",
        "mostrar mapa do ",
        "mostrar mapa da ",
        "mostre o mapa de ",
        "mostre o mapa do ",
        "mostre o mapa da ",
        "mostre mapa de ",
        "mostre mapa do ",
        "mostre mapa da ",
        "mostra mapa de ",
        "mostra mapa do ",
        "mostra mapa da ",
        "abrir o mapa de ",
        "abrir o mapa do ",
        "abrir o mapa da ",
        "abrir mapa de ",
        "abrir mapa do ",
        "abrir mapa da ",
        "mapa de ",
        "mapa do ",
        "mapa da ",
        "onde fica ",
    )
    location = _extract_location_fragment(user_input, map_prefixes)

    if not location and lower in {
        "abrir mapa",
        "mostrar mapa",
        "mostra mapa",
        "onde fica minha cidade",
        "mostrar minha cidade no mapa",
    }:
        location = _default_profile_location()

    if not location:
        return None

    return {
        "intent": "ui_show_map",
        "target": {
            "kind": "place",
            "location": location,
            "label": location,
            "url": f"https://www.google.com/maps/search/?api=1&query={quote_plus(location)}",
        },
    }


DAILY_DETECTORS = [
    detect_weather_command,
    detect_briefing_command,
    detect_reminder_command,
    detect_agenda_command,
    detect_map_command,
]
