import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_model(
    prompt: str,
    model: str = "qwen2.5:0.5b",
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
