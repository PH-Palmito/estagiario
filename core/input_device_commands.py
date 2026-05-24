from __future__ import annotations

import difflib
import re
from collections.abc import Callable

from core.router_utils import normalize_text
from memory.voice_preferences import update_voice_preferences
from voice.windows_voice import format_input_devices, get_active_input_device_info, list_input_devices


def _normalize_device_label(text: str) -> str:
    return normalize_text(text).strip()


def maybe_handle_input_device_command(user_input: str, refresh_preferences: Callable[[], None]) -> str | None:
    normalized = normalize_text(user_input).strip(" .,:;!?")
    raw = str(user_input or "").strip()

    if normalized in {
        "listar microfones",
        "listar microfone",
        "mostrar microfones",
        "mostrar microfone",
        "quais microfones",
        "quais microfones voce tem",
        "microfones disponiveis",
        "entradas de audio",
        "listar entradas de audio",
    }:
        return format_input_devices()

    if normalized in {
        "qual microfone esta ativo",
        "qual microfone ativo",
        "microfone atual",
        "microfone em uso",
        "entrada de audio atual",
    }:
        active = get_active_input_device_info()
        if not active:
            return "Nao encontrei um microfone ativo no momento."
        return f"Microfone ativo: {active['name']}."

    if normalized in {
        "usar microfone padrao",
        "usar padrao do windows",
        "usar microfone do windows",
        "limpar microfone preferido",
        "remover microfone preferido",
    }:
        update_voice_preferences({"audio_input_device": ""})
        refresh_preferences()
        active = get_active_input_device_info()
        if active:
            return f"Voltei para o microfone padrao do Windows: {active['name']}."
        return "Voltei para o microfone padrao do Windows."

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
        return "Qual microfone voce quer usar?"

    devices_text = format_input_devices()
    devices = list_input_devices()
    active = get_active_input_device_info()

    if not devices:
        return "Nao encontrei microfones disponiveis para selecionar."

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
        return f"Nao encontrei um microfone parecido com {requested_name}. {devices_text}"

    update_voice_preferences({"audio_input_device": chosen["name"]})
    refresh_preferences()

    if active and active["name"] == chosen["name"]:
        return f"Microfone confirmado: {chosen['name']}."
    return f"Agora vou usar este microfone: {chosen['name']}."
