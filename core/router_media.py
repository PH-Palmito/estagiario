from __future__ import annotations

import re

from core.router_utils import normalize_text

MEDIA_TARGETS = {
    "spotify": "spotify",
    "youtube": "youtube",
    "you tube": "youtube",
    "you": "youtube",
    "chrome": "chrome",
    "navegador": "chrome",
}


def detect_media_command(user_input: str):
    lower = normalize_text(user_input)
    media_target_pattern = r"(?:spotify|youtube|you tube|you|chrome|navegador)"
    target_article_pattern = r"(?:(?:o|a|no|na|do|da)\s+)?"

    if re.search(rf"\b(bye|bai)\s+{target_article_pattern}({media_target_pattern})\b", lower):
        target_match = re.search(rf"\b(bye|bai)\s+{target_article_pattern}({media_target_pattern})\b", lower)
        target = MEDIA_TARGETS.get(target_match.group(2), target_match.group(2))
        return {"intent": "media_pause_target", "target": target}

    combo_match = re.search(
        rf"\b(?:pausa|pausar|pause|parar|para|para ai|pare)\s+{target_article_pattern}(?P<first>{media_target_pattern})\b"
        rf".*\b(?:play|toca|tocar|continua|continuar|abre|abrir)\s+{target_article_pattern}(?P<second>{media_target_pattern})\b",
        lower,
    )
    if combo_match:
        first = MEDIA_TARGETS.get(combo_match.group("first"), combo_match.group("first"))
        second = MEDIA_TARGETS.get(combo_match.group("second"), combo_match.group("second"))
        if first and second:
            return {
                "intent": "run_routine",
                "target": [
                    f"pausar {first}",
                    f"play {second}",
                ],
                "name": "troca de midia",
            }

    target_match = re.search(
        rf"\b(?P<action>pausa|pausar|pause|parar|para|para ai|pare|play|toca|tocar|continua|continuar|despausa)\s+"
        rf"{target_article_pattern}(?P<target>{media_target_pattern})\b",
        lower,
    )
    if target_match:
        action_word = target_match.group("action")
        target = MEDIA_TARGETS.get(target_match.group("target"), target_match.group("target"))
        if action_word in {"pausa", "pausar", "pause", "parar", "para", "para ai", "pare"}:
            return {"intent": "media_pause_target", "target": target}
        if action_word in {"play", "toca", "tocar", "continua", "continuar", "despausa"}:
            return {"intent": "media_play_target", "target": target}
        return {"intent": "media_play_pause_target", "target": target}

    next_match = re.search(
        rf"\b(proxima|proximo|passa|passar)\s+(?:musica|video|midia)?\s*(?:no\s+|na\s+|do\s+|da\s+)?({media_target_pattern})\b",
        lower,
    )
    if next_match:
        target = MEDIA_TARGETS.get(next_match.group(2), next_match.group(2))
        return {"intent": "media_next_target", "target": target}

    previous_match = re.search(
        rf"\b(anterior|volta|voltar)\s+(?:musica|video|midia)?\s*(?:no\s+|na\s+|do\s+|da\s+)?({media_target_pattern})\b",
        lower,
    )
    if previous_match:
        target = MEDIA_TARGETS.get(previous_match.group(2), previous_match.group(2))
        return {"intent": "media_previous_target", "target": target}

    if lower in {"pausa", "pausar", "pause", "play", "continua", "continuar", "despausa"}:
        return {"intent": "media_play_pause", "target": None}

    if any(
        phrase in lower
        for phrase in {
            "pausa musica",
            "pausar musica",
            "pausa video",
            "pausar video",
            "continua musica",
            "continuar musica",
            "continua video",
            "continuar video",
        }
    ):
        return {"intent": "media_play_pause", "target": None}

    if any(
        phrase in lower
        for phrase in {
            "proxima musica",
            "proximo video",
            "proxima midia",
            "passa musica",
            "passar musica",
            "passa para proxima",
            "passar para proxima",
        }
    ):
        return {"intent": "media_next", "target": None}

    if any(
        phrase in lower
        for phrase in {
            "musica anterior",
            "video anterior",
            "midia anterior",
            "volta musica",
            "voltar musica",
            "musica de antes",
        }
    ):
        return {"intent": "media_previous", "target": None}

    if any(
        phrase in lower
        for phrase in {
            "aumenta volume",
            "aumentar volume",
            "volume para cima",
            "sobe volume",
            "subir volume",
            "mais volume",
        }
    ):
        return {"intent": "volume_up", "target": None}

    if any(
        phrase in lower
        for phrase in {
            "abaixa volume",
            "abaixar volume",
            "diminui volume",
            "diminuir volume",
            "volume para baixo",
            "menos volume",
        }
    ):
        return {"intent": "volume_down", "target": None}

    if re.search(r"\b(muta|mutar|mudo|silencia|silenciar)\b", lower) or any(
        phrase in lower for phrase in {"tira o som", "ativar mudo"}
    ):
        return {"intent": "volume_mute", "target": None}

    return None


MEDIA_DETECTORS = [
    detect_media_command,
]
