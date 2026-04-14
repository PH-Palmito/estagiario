import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_model(prompt: str, model: str = "qwen2.5:0.5b", timeout_seconds: int = 15) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 80,
                "temperature": 0.3,
                "top_p": 0.9
            }
        },
        timeout=timeout_seconds
    )
    response.raise_for_status()
    data = response.json()
    return data["response"]
