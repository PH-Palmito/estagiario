import subprocess

from llm.vision_client import choose_vision_model, vision_status_text


LIGHT_VISION_MODEL = "moondream"


def vision_status() -> str:
    return vision_status_text()


def vision_install_hint() -> str:
    return (
        "Para ativar análise visual semântica, instale um modelo visual no Ollama. "
        "O mais leve para começar: ollama pull moondream. "
        "Depois teste: interpretar imagem da tela."
    )


def start_light_vision_model_download() -> str:
    try:
        subprocess.Popen(
            ["ollama", "pull", LIGHT_VISION_MODEL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return "Não encontrei o comando ollama no PATH. Abra o Ollama ou rode manualmente: ollama pull moondream."
    except Exception as exc:
        return f"Não consegui iniciar o download do modelo visual: {exc}"

    return (
        f"Iniciei o download do modelo visual {LIGHT_VISION_MODEL} em segundo plano. "
        "Quando terminar, diga: status da visão."
    )


def active_vision_model() -> str:
    return f"Modelo visual escolhido: {choose_vision_model()}."
