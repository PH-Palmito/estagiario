from __future__ import annotations

import difflib
from collections.abc import Callable

import sounddevice as sd

from voice.recognition_text import normalize_recognized_text


def _normalized_device_name(text: str) -> str:
    return normalize_recognized_text(text or "")


def list_input_devices(sample_rate: int = 16000) -> list[dict]:
    try:
        devices = sd.query_devices()
    except Exception:
        return []

    default_input = None
    try:
        default_input = sd.default.device[0]
    except Exception:
        default_input = None

    rows = []
    for index, device in enumerate(devices):
        try:
            max_inputs = int(device.get("max_input_channels", 0) or 0)
        except Exception:
            max_inputs = 0
        if max_inputs <= 0:
            continue

        rows.append(
            {
                "index": index,
                "name": str(device.get("name", f"Dispositivo {index}")).strip(),
                "channels": max_inputs,
                "default_samplerate": int(device.get("default_samplerate", sample_rate) or sample_rate),
                "is_default": default_input == index,
            }
        )

    return rows


def resolve_input_device(
    preferences: dict,
    devices: list[dict] | None = None,
    device_loader: Callable[[], list[dict]] | None = None,
) -> tuple[int | None, dict | None]:
    if devices is None:
        devices = device_loader() if device_loader is not None else list_input_devices()
    if not devices:
        return None, None

    preferred_name = _normalized_device_name(str(preferences.get("audio_input_device", "")).strip())

    if preferred_name:
        exact_match = next(
            (device for device in devices if _normalized_device_name(device["name"]) == preferred_name),
            None,
        )
        if exact_match:
            return int(exact_match["index"]), exact_match

        contains_match = next(
            (device for device in devices if preferred_name in _normalized_device_name(device["name"])),
            None,
        )
        if contains_match:
            return int(contains_match["index"]), contains_match

        best_match = None
        best_score = 0.0
        for device in devices:
            score = difflib.SequenceMatcher(
                None,
                preferred_name,
                _normalized_device_name(device["name"]),
            ).ratio()
            if score > best_score:
                best_score = score
                best_match = device
        if best_match and best_score >= 0.62:
            return int(best_match["index"]), best_match

    default_device = next((device for device in devices if device.get("is_default")), None)
    if default_device:
        return int(default_device["index"]), default_device

    return int(devices[0]["index"]), devices[0]


def format_input_devices(
    devices: list[dict],
    active: dict | None,
    limit: int = 12,
) -> str:
    if not devices:
        return "Nao encontrei microfones disponiveis."

    rows = []
    for device in devices[:limit]:
        label = device["name"]
        tags = []
        if device.get("is_default"):
            tags.append("padrao do Windows")
        if active and device["index"] == active["index"]:
            tags.append("em uso pelo assistente")
        if tags:
            label += " (" + ", ".join(tags) + ")"
        rows.append(f"{device['index']}. {label}")

    return "Microfones disponiveis: " + "; ".join(rows) + "."
