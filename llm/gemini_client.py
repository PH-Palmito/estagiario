import requests

from config import GEMINI_API_KEY, GEMINI_MODEL


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _post_gemini(payload: dict, model: str, timeout_seconds: int):
    session = requests.Session()
    session.trust_env = False
    response = session.post(
        GEMINI_API_URL.format(model=model),
        headers={
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response


def _extract_gemini_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini retornou resposta vazia.")

    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    text_parts = [str(part.get("text", "")) for part in parts if str(part.get("text", "")).strip()]
    answer = "".join(text_parts).strip()
    if not answer:
        raise RuntimeError("Gemini retornou texto vazio.")

    return answer


def ask_gemini_model(
    prompt: str,
    model: str = GEMINI_MODEL,
    timeout_seconds: int = 20,
    max_output_tokens: int = 220,
    temperature: float = 0.35,
) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key nao configurada.")

    response = _post_gemini(
        {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        },
        model=model,
        timeout_seconds=timeout_seconds,
    )
    data = response.json()
    return _extract_gemini_text(data)


def ask_gemini_grounded_model(
    prompt: str,
    model: str = GEMINI_MODEL,
    timeout_seconds: int = 30,
    max_output_tokens: int = 260,
    temperature: float = 0.25,
) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key nao configurada.")

    response = _post_gemini(
        {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "tools": [
                {
                    "google_search": {},
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        },
        model=model,
        timeout_seconds=timeout_seconds,
    )
    data = response.json()
    text = _extract_gemini_text(data)

    candidates = data.get("candidates") or []
    metadata = (candidates[0].get("groundingMetadata") or {}) if candidates else {}
    chunks = metadata.get("groundingChunks") or []
    sources = []
    for chunk in chunks:
        web = chunk.get("web") or {}
        uri = str(web.get("uri", "")).strip()
        title = str(web.get("title", "")).strip()
        if not uri:
            continue
        sources.append({"title": title, "url": uri})

    return {
        "text": text,
        "sources": sources,
    }
