import math

import requests

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_PRIMARY_TEXT_ENABLED,
    NVIDIA_API_KEY,
    NVIDIA_MODEL,
    NVIDIA_TEXT_FALLBACK_ENABLED,
    OLLAMA_BASE_URL,
    OLLAMA_TEXT_MODEL,
    join_url,
)
from llm.gemini_client import ask_gemini_model
from llm.nvidia_client import ask_nvidia_model

OLLAMA_URL = join_url(OLLAMA_BASE_URL, "/api/generate")


def _should_prefer_gemini(model: str) -> bool:
    normalized_model = str(model or "").strip().lower()
    if normalized_model.startswith("gemini"):
        return True
    return bool(GEMINI_PRIMARY_TEXT_ENABLED and GEMINI_API_KEY)


def _should_try_nvidia(model: str) -> bool:
    normalized_model = str(model or "").strip().lower()
    if normalized_model.startswith("nvidia/") or normalized_model.startswith("meta/"):
        return bool(NVIDIA_API_KEY)
    return bool(NVIDIA_TEXT_FALLBACK_ENABLED and NVIDIA_API_KEY)


def _gemini_output_tokens(num_predict: int) -> int:
    estimate = max(96, int(math.ceil(max(1, num_predict) * 1.35)))
    return min(1024, estimate)


def _cloud_timeout(timeout_seconds: int) -> int:
    return max(4, min(timeout_seconds + 8, 45))


def _resolve_gemini_model(model: str) -> str:
    return model if str(model or "").strip().lower().startswith("gemini") else GEMINI_MODEL


def _resolve_nvidia_model(model: str) -> str:
    normalized_model = str(model or "").strip()
    if normalized_model.lower().startswith(("nvidia/", "meta/")):
        return normalized_model
    return NVIDIA_MODEL


def _ask_cloud_model(
    prompt: str,
    model: str,
    timeout_seconds: int,
    num_predict: int,
    temperature: float,
) -> str:
    last_error: Exception | None = None

    if _should_prefer_gemini(model):
        try:
            return ask_gemini_model(
                prompt,
                model=_resolve_gemini_model(model),
                timeout_seconds=_cloud_timeout(timeout_seconds),
                max_output_tokens=_gemini_output_tokens(num_predict),
                temperature=temperature,
            )
        except Exception as exc:
            last_error = exc

    if _should_try_nvidia(model):
        try:
            return ask_nvidia_model(
                prompt,
                model=_resolve_nvidia_model(model),
                timeout_seconds=_cloud_timeout(timeout_seconds),
                max_output_tokens=_gemini_output_tokens(num_predict),
                temperature=temperature,
            )
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error

    raise RuntimeError("Nenhum provedor de nuvem configurado.")


def _ask_ollama_model(
    prompt: str,
    model: str,
    timeout_seconds: int,
    num_predict: int,
    temperature: float,
) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": num_predict,
                "temperature": temperature,
                "top_p": 0.9,
            },
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    return data["response"]


def ask_model(
    prompt: str,
    model: str = OLLAMA_TEXT_MODEL,
    timeout_seconds: int = 15,
    num_predict: int = 80,
    temperature: float = 0.3,
    provider: str = "auto",
) -> str:
    provider = str(provider or "auto").strip().lower()
    if provider == "nvidia":
        return ask_nvidia_model(
            prompt,
            model=_resolve_nvidia_model(model),
            timeout_seconds=_cloud_timeout(timeout_seconds),
            max_output_tokens=_gemini_output_tokens(num_predict),
            temperature=temperature,
        )

    if provider in {"cloud", "gemini"}:
        return _ask_cloud_model(prompt, model, timeout_seconds, num_predict, temperature)

    if provider != "local" and _should_prefer_gemini(model):
        try:
            return _ask_cloud_model(prompt, model, timeout_seconds, num_predict, temperature)
        except Exception:
            pass

    return _ask_ollama_model(
        prompt,
        model=model,
        timeout_seconds=timeout_seconds,
        num_predict=num_predict,
        temperature=temperature,
    )
