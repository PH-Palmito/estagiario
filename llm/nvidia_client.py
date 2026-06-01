import requests

from config import NVIDIA_API_KEY, NVIDIA_MODEL

NVIDIA_CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def _extract_nvidia_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("NVIDIA retornou resposta vazia.")

    message = choices[0].get("message") or {}
    answer = str(message.get("content", "")).strip()
    if not answer:
        raise RuntimeError("NVIDIA retornou texto vazio.")

    return answer


def ask_nvidia_model(
    prompt: str,
    model: str = NVIDIA_MODEL,
    timeout_seconds: int = 20,
    max_output_tokens: int = 220,
    temperature: float = 0.35,
) -> str:
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA API key nao configurada.")

    session = requests.Session()
    session.trust_env = False
    response = session.post(
        NVIDIA_CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "stream": False,
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return _extract_nvidia_text(response.json())
