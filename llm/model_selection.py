from __future__ import annotations

from dataclasses import dataclass

from core.router_registry import (
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_CONVERSATION,
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
)

PROVIDER_AUTO = "auto"
PROVIDER_LOCAL = "local"
PROVIDER_CLOUD = "cloud"
VALID_PROVIDERS = {PROVIDER_AUTO, PROVIDER_LOCAL, PROVIDER_CLOUD}


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    reason: str
    fallback_provider: str = ""

    @property
    def uses_cloud(self) -> bool:
        return self.provider == PROVIDER_CLOUD


def normalize_provider(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "nuvem": PROVIDER_CLOUD,
        "cloud": PROVIDER_CLOUD,
        "gemini": PROVIDER_CLOUD,
        "remoto": PROVIDER_CLOUD,
        "local": PROVIDER_LOCAL,
        "ollama": PROVIDER_LOCAL,
        "offline": PROVIDER_LOCAL,
        "auto": PROVIDER_AUTO,
        "automatico": PROVIDER_AUTO,
        "automático": PROVIDER_AUTO,
    }
    return aliases.get(normalized, normalized if normalized in VALID_PROVIDERS else PROVIDER_AUTO)


def select_chat_model_route(
    user_input: str,
    *,
    preferences: dict | None,
    local_model: str,
    cloud_model: str,
    cloud_available: bool,
    complex_request: bool,
    intent_level: str = INTENT_LEVEL_CONVERSATION,
) -> ModelRoute:
    prefs = preferences or {}
    provider_preference = normalize_provider(
        prefs.get("ai_text_provider")
        or prefs.get("chat_provider")
        or prefs.get("text_model_provider")
    )

    local_model = str(local_model or "").strip() or "qwen2.5:0.5b"
    cloud_model = str(cloud_model or "").strip() or "gemini"
    intent_level = str(intent_level or INTENT_LEVEL_CONVERSATION)

    if provider_preference == PROVIDER_LOCAL:
        return ModelRoute(PROVIDER_LOCAL, local_model, "preferencia explicita local")

    if provider_preference == PROVIDER_CLOUD:
        if cloud_available:
            return ModelRoute(PROVIDER_CLOUD, cloud_model, "preferencia explicita nuvem", PROVIDER_LOCAL)
        return ModelRoute(PROVIDER_LOCAL, local_model, "nuvem solicitada, mas indisponivel")

    if not cloud_available:
        return ModelRoute(PROVIDER_LOCAL, local_model, "nuvem indisponivel")

    if intent_level == INTENT_LEVEL_DIRECT_COMMAND:
        return ModelRoute(PROVIDER_LOCAL, local_model, "comando direto deve ficar local")

    if intent_level in {INTENT_LEVEL_QUESTION, INTENT_LEVEL_COMPOSITE_TASK} and complex_request:
        return ModelRoute(PROVIDER_CLOUD, cloud_model, "pergunta/tarefa complexa", PROVIDER_LOCAL)

    if intent_level == INTENT_LEVEL_CONVERSATION and complex_request:
        return ModelRoute(PROVIDER_CLOUD, cloud_model, "conversa complexa", PROVIDER_LOCAL)

    return ModelRoute(PROVIDER_LOCAL, local_model, "interacao simples")
