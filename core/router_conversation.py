from __future__ import annotations

from core.router_utils import normalize_text
from llm.action_selector import select_read_action
from llm.chat import chat_response

FACTUAL_QUESTION_PREFIXES = (
    "o que e ",
    "oq e ",
    "oque e ",
    "quem e ",
    "qual e ",
    "quais sao ",
    "como funciona ",
)

REPEAT_PATTERNS = {
    "de novo",
    "denovo",
    "mais uma",
    "outra vez",
    "repete",
    "repita",
}


def detect_short_unclear_text(user_input: str):
    text = normalize_text(user_input)

    if text in REPEAT_PATTERNS:
        return {"intent": "repeat_last", "target": None}

    if len(text) <= 4:
        return {"intent": "respond", "target": None, "response": "Pode repetir?"}
    return None


def detect_light_conversation(user_input: str):
    text = normalize_text(user_input)
    if not text:
        return None

    if any(word in text for word in {"conversavel", "conversar", "bater papo", "inteligente"}):
        return {
            "intent": "respond",
            "target": None,
            "response": "Da para eu ficar mais conversavel sim. Por enquanto eu respondo melhor frases curtas, mas posso aprender respostas e contexto aos poucos.",
        }

    question_prefixes = ("por que ", "porque ", "como ", "qual ", "quando ", "onde ")
    if any(text.startswith(prefix) for prefix in question_prefixes):
        return {
            "intent": "respond",
            "target": None,
            "response": "Essa parte de conversa aberta ainda e limitada. Se voce quiser, posso responder perguntas simples e ir aprendendo respostas mais naturais.",
        }

    return None


def detect_llm_action_command(user_input: str):
    selected = select_read_action(user_input)
    if not selected:
        return None
    return {
        "intent": "action_tool_execute",
        "target": {
            "name": selected["name"],
            "arguments": selected.get("arguments") or {},
        },
    }


def detect_ollama_chat(user_input: str):
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None

    if text.startswith(FACTUAL_QUESTION_PREFIXES):
        response = chat_response(user_input)
        if response:
            return {"intent": "respond", "target": None, "response": response}

    response = chat_response(user_input)
    if response:
        return {"intent": "respond", "target": None, "response": response}

    return None


CONVERSATION_DETECTORS = (
    detect_short_unclear_text,
    detect_llm_action_command,
    detect_ollama_chat,
    detect_light_conversation,
)
