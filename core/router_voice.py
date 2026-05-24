from __future__ import annotations

import re

from core.router_utils import normalize_text
from memory.voice_corrections import (
    forget_voice_correction,
    list_voice_corrections,
    remember_voice_correction,
)


def detect_voice_correction_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {"listar correcoes de voz", "listar correcoes", "ver correcoes de voz", "ver correcoes"}:
        corrections = list_voice_corrections()
        if not corrections:
            return {"intent": "respond", "target": None, "response": "Nenhuma correcao de voz salva."}

        rows = [
            f"{idx}. quando ouvir '{item['heard']}', entender '{item['means']}'"
            for idx, item in enumerate(corrections, start=1)
        ]
        return {"intent": "respond", "target": None, "response": "Correcoes de voz: " + "; ".join(rows)}

    forget_match = re.match(
        r"^(?:esquecer|esquece|apagar|apague|remover|remova)\s+correc(?:ao|oes)\s+(?:de\s+voz\s+)?(.+)$",
        lower,
    )
    if forget_match:
        heard = forget_match.group(1).strip().strip('"').strip("'")
        if forget_voice_correction(heard):
            return {"intent": "respond", "target": None, "response": f"Esqueci a correcao de voz para '{heard}'."}
        return {"intent": "respond", "target": None, "response": f"Nao encontrei correcao de voz para '{heard}'."}

    teach_patterns = [
        r"^(?:aprenda|aprende|lembrar|lembre)\s+que\s+['\"]?(.+?)['\"]?\s+(?:significa|quer dizer|e para entender como|eh para entender como)\s+['\"]?(.+?)['\"]?$",
        r"^quando\s+(?:eu\s+)?(?:disser|falar)\s+['\"]?(.+?)['\"]?\s+(?:entenda|entender|interprete|interpretar)\s+(?:como\s+)?['\"]?(.+?)['\"]?$",
    ]
    for pattern in teach_patterns:
        match = re.match(pattern, lower)
        if not match:
            continue

        heard = match.group(1).strip()
        means = match.group(2).strip()
        if remember_voice_correction(heard, means):
            return {
                "intent": "respond",
                "target": None,
                "response": f"Aprendi: quando ouvir '{heard}', vou entender como '{means}'.",
            }

    return None


VOICE_DETECTORS = [
    detect_voice_correction_command,
]
