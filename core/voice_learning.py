from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceLearningState:
    pending_command_learning_text: str = ""
    last_voice_text: str = ""


@dataclass(frozen=True)
class PendingVoiceCorrectionResult:
    state: VoiceLearningState
    learned: bool = False
    heard: str = ""
    means: str = ""


@dataclass(frozen=True)
class LastVoiceCorrectionResult:
    state: VoiceLearningState
    response: str | None = None


def maybe_remember_pending_voice_correction(
    command,
    state: VoiceLearningState,
    *,
    command_correction_text: Callable[[object], str],
    normalize_text: Callable[[str], str],
    remember_voice_correction: Callable[[str, str], bool],
) -> PendingVoiceCorrectionResult:
    heard = str(state.pending_command_learning_text or "").strip()
    cleared_state = VoiceLearningState(
        pending_command_learning_text="",
        last_voice_text=state.last_voice_text,
    )
    if not heard:
        return PendingVoiceCorrectionResult(cleared_state)

    means = command_correction_text(command)
    if not means or normalize_text(heard) == normalize_text(means):
        return PendingVoiceCorrectionResult(cleared_state, heard=heard, means=means)

    learned = bool(remember_voice_correction(heard, means))
    return PendingVoiceCorrectionResult(
        cleared_state,
        learned=learned,
        heard=heard,
        means=means,
    )


def maybe_learn_correction_for_last_voice(
    user_input: str,
    state: VoiceLearningState,
    *,
    normalize_text: Callable[[str], str],
    remember_voice_correction: Callable[[str, str], bool],
) -> LastVoiceCorrectionResult:
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
        return LastVoiceCorrectionResult(state)

    if not state.last_voice_text:
        return LastVoiceCorrectionResult(
            state,
            "Ainda nao tenho uma fala de voz para corrigir.",
        )

    remember_voice_correction(state.last_voice_text, target)
    learned_from = state.last_voice_text
    return LastVoiceCorrectionResult(
        VoiceLearningState(
            pending_command_learning_text=state.pending_command_learning_text,
            last_voice_text="",
        ),
        f"Aprendi: quando ouvir '{learned_from}', vou entender como '{target}'.",
    )
