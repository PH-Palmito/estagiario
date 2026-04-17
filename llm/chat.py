from collections import deque
import re

from llm.ollama_client import ask_model
from memory.voice_preferences import load_voice_preferences


PREFERENCES = load_voice_preferences()
CHAT_HISTORY = deque(maxlen=6)

CHAT_PROMPT = """
Voce e o Estagiario, uma IA local controlada por voz no PC do usuario.

Personalidade:
- Fale em portugues do Brasil.
- Seja curto, natural e util.
- Tenha um tom leve, colaborativo e um pouco divertido.
- Nao finja que executou acoes. Se for comando de PC, diga que o usuario pode pedir como comando.
- Nao use markdown.
- Nao responda com listas longas.
- Evite respostas maiores que 2 frases.
- Responda somente a sua fala final, sem escrever "Usuario:" ou "Estagiario:".
- Nao continue a conversa inventando falas do usuario.
- Voce nunca deve dizer que se chama Qwen, Llama ou qualquer nome de modelo.
- Se perguntarem quem voce e, diga que e o Estagiario.

Contexto:
Voce consegue abrir apps e sites, controlar janelas, navegar no navegador, controlar midia,
lembrar apps/sites e responder por voz. Esta conversa acontece por fala, entao seja objetivo.
""".strip()


def chat_enabled() -> bool:
    return bool(PREFERENCES.get("chat_enabled", True))


def _history_text() -> str:
    if not CHAT_HISTORY:
        return "Sem historico recente."

    return "\n".join(f"{role} disse: {text}" for role, text in CHAT_HISTORY)


def clear_chat_history():
    CHAT_HISTORY.clear()


def _clean_response(response: str) -> str:
    response = (response or "").replace("\r", " ").replace("\n", " ").strip()

    # Some small models continue the dialogue transcript. Keep only the assistant's first turn.
    response = re.split(r"\bUsuario\s*:", response, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    response = re.sub(r"^(Estagi.rio|Estagiario|Assistente)\s*:\s*", "", response, flags=re.IGNORECASE).strip()

    response = re.split(r"\b(Usuario|Usu.rio|Estagi.rio|Estagiario|Assistente)\s*:", response, maxsplit=1, flags=re.IGNORECASE)[0].strip()

    sentences = re.split(r"(?<=[.!?])\s+", response)
    response = " ".join(sentence for sentence in sentences[:2] if sentence).strip()

    return response


def chat_response(user_input: str):
    if not chat_enabled():
        return None

    model = str(PREFERENCES.get("chat_model", "qwen2.5:0.5b")).strip() or "qwen2.5:0.5b"
    try:
        timeout = int(PREFERENCES.get("chat_timeout_seconds", 8))
    except (TypeError, ValueError):
        timeout = 8

    prompt = f"""{CHAT_PROMPT}

Historico recente:
{_history_text()}

Mensagem atual do usuario:
{user_input}

Resposta curta do Estagiario:"""

    try:
        response = ask_model(
            prompt,
            model=model,
            timeout_seconds=max(2, min(timeout, 30)),
            num_predict=90,
            temperature=0.7,
        )
    except Exception:
        return None

    response = (response or "").strip()
    if not response:
        return None

    response = _clean_response(response)
    if not response:
        return None

    lower = response.lower()
    if "meu nome e qwen" in lower or "meu nome é qwen" in lower or "sou qwen" in lower or "sou uma ia local" in lower:
        response = "Sou o Estagiario. Estou aqui para conversar e ajudar a controlar o PC."

    confused_markers = {
        "nao consigo entender",
        "não consigo entender",
        "nao entendi",
        "não entendi",
        "diga mais sobre",
        "estou esperando sua resposta",
        "aguardo sua resposta",
    }
    if any(marker in lower for marker in confused_markers):
        response = "Posso conversar sim. Me puxa por um assunto simples ou me conta o que voce quer pensar agora."

    if len(response) > 350:
        response = response[:347].rstrip() + "..."

    CHAT_HISTORY.append(("Usuario", user_input))
    CHAT_HISTORY.append(("Estagiario", response))
    return response
