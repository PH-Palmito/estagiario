import math

import requests

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_PRIMARY_TEXT_ENABLED,
    OLLAMA_BASE_URL,
    OLLAMA_TEXT_MODEL,
    join_url,
)
from llm.gemini_client import ask_gemini_model

OLLAMA_URL = join_url(OLLAMA_BASE_URL, "/api/generate")


def _should_prefer_gemini(model: str) -> bool:
    normalized_model = str(model or "").strip().lower()
    if normalized_model.startswith("gemini"):
        return True
    return bool(GEMINI_PRIMARY_TEXT_ENABLED and GEMINI_API_KEY)


def _gemini_output_tokens(num_predict: int) -> int:
    estimate = max(96, int(math.ceil(max(1, num_predict) * 1.35)))
    return min(1024, estimate)


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
) -> str:
    if _should_prefer_gemini(model):
        gemini_model = model if str(model or "").strip().lower().startswith("gemini") else GEMINI_MODEL
        try:
            return ask_gemini_model(
                prompt,
                model=gemini_model,
                timeout_seconds=max(4, min(timeout_seconds + 8, 45)),
                max_output_tokens=_gemini_output_tokens(num_predict),
                temperature=temperature,
            )
        except Exception:
            pass

    return _ask_ollama_model(
        prompt,
        model=model,
        timeout_seconds=timeout_seconds,
        num_predict=num_predict,
        temperature=temperature,
    )
