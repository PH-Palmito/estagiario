import requests
from config import OLLAMA_TEXT_MODEL, OLLAMA_BASE_URL, join_url


OLLAMA_URL = join_url(OLLAMA_BASE_URL, "/api/generate")


def ask_model(
    prompt: str,
    model: str = OLLAMA_TEXT_MODEL,
    timeout_seconds: int = 15,
    num_predict: int = 80,
    temperature: float = 0.3,
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
                "top_p": 0.9
            }
        },
        timeout=timeout_seconds
    )
    response.raise_for_status()
    data = response.json()
    return data["response"]
