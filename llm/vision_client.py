import base64
from pathlib import Path

import requests

from config import OLLAMA_BASE_URL, OLLAMA_VISION_MODEL, join_url

OLLAMA_GENERATE_URL = join_url(OLLAMA_BASE_URL, "/api/generate")
OLLAMA_TAGS_URL = join_url(OLLAMA_BASE_URL, "/api/tags")
DEFAULT_VISION_MODELS = (
    "llama3.2-vision:11b",
    "llava:7b",
    "llava",
    "moondream",
    "bakllava",
)


VISION_PROMPT = """
Você é a visão local do Axel. Analise a imagem de forma semântica e útil, em português do Brasil.

Objetivo:
- Diga o que aparece na imagem, não apenas formato, resolução ou OCR.
- Considere qualquer elemento visual relevante: objetos, animais, pessoas, gráficos, símbolos, interface, cenário, documentos, placas, cores, composição, relações espaciais e sinais de ação.
- Identifique o tipo provável dos elementos e características relevantes.
- Se houver gráfico, interprete tendência, eixos/legendas visíveis, picos, quedas e conclusão provável.
- Se houver tela de site/app, diga o conteúdo principal e ações úteis visíveis.
- Se houver pessoa, descreva quantidade de pessoas, postura, roupa, expressão geral, ação e contexto, mas não identifique quem é a pessoa nem confirme identidade facial.
- Se houver texto legível, use-o como apoio, mas não transforme a resposta numa transcrição longa.
- Se a imagem for ambígua, diga o que parece ser e o nível de confiança.

Responda em até 5 frases, direto e útil.
""".strip()


def _installed_models(timeout_seconds: int = 4) -> list[str]:
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    models = []
    for item in data.get("models", []) or []:
        name = str(item.get("name", "")).strip()
        if name:
            models.append(name)
    return models


def installed_models() -> list[str]:
    return _installed_models()


def installed_vision_models() -> list[str]:
    models = _installed_models()
    vision_models = []
    for model in models:
        lowered = model.lower()
        if any(token in lowered for token in ("vision", "llava", "moondream", "bakllava", "minicpm-v")):
            vision_models.append(model)
    return vision_models


def choose_vision_model() -> str:
    configured = OLLAMA_VISION_MODEL.strip()
    if configured:
        return configured

    installed = _installed_models()
    installed_lower = {model.lower(): model for model in installed}
    for candidate in DEFAULT_VISION_MODELS:
        if candidate.lower() in installed_lower:
            return installed_lower[candidate.lower()]

    for model in installed:
        lowered = model.lower()
        if any(token in lowered for token in ("vision", "llava", "moondream", "bakllava", "minicpm-v")):
            return model

    return DEFAULT_VISION_MODELS[0]


def vision_status_text() -> str:
    models = _installed_models()
    vision_models = installed_vision_models()
    if vision_models:
        chosen = choose_vision_model()
        return f"Visão local pronta. Modelo visual ativo: {chosen}. Modelos visuais encontrados: {', '.join(vision_models)}."
    if models:
        return (
            "Visão local ainda sem modelo visual. Modelos atuais: "
            + ", ".join(models)
            + ". Para ativar visão semântica, instale primeiro: ollama pull moondream."
        )
    return "Não consegui listar modelos do Ollama. Verifique se o Ollama está aberto."


def ask_vision_model(
    image_path: str | Path,
    prompt: str = VISION_PROMPT,
    timeout_seconds: int = 90,
    num_predict: int = 220,
) -> str:
    path = Path(image_path)
    image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    model = choose_vision_model()

    response = requests.post(
        OLLAMA_GENERATE_URL,
        json={
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "num_predict": num_predict,
                "temperature": 0.2,
                "top_p": 0.9,
            },
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    return str(data.get("response", "")).strip()


def vision_unavailable_message(error: Exception) -> str:
    text = str(error)
    if "connection" in text.lower() or "actively refused" in text.lower() or "10061" in text:
        return "Visão local indisponível: o Ollama não parece estar aberto."
    if "not found" in text.lower() or "model" in text.lower():
        model = choose_vision_model()
        return f"Visão local indisponível: não encontrei um modelo visual no Ollama. Modelo tentado: {model}."
    return f"Visão local indisponível: {text}"
