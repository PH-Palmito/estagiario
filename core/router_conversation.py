from __future__ import annotations

from core.router_utils import normalize_text
from llm.action_selector import select_read_action
from llm.chat import chat_response

FACTUAL_QUESTION_PREFIXES = (
    "o que e ",
    "oq e ",
    "oque e ",
    "quem e ",
    "quem foi ",
    "qual e ",
    "qual ",
    "quais sao ",
    "quais ",
    "onde ",
    "quando ",
    "por que ",
    "porque ",
    "como funciona ",
    "como ",
)

GENERAL_EXPLANATION_PREFIXES = (
    "me explica ",
    "me explique ",
    "explica ",
    "explique ",
    "detalha ",
    "detalhe ",
)

REPEAT_PATTERNS = {
    "de novo",
    "denovo",
    "mais uma",
    "outra vez",
    "repete",
    "repita",
}


def detect_builtin_general_answer(user_input: str):
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None

    if "alanzoca" in text:
        return {
            "intent": "respond",
            "target": None,
            "response": "Alanzoca, ou Alan Ferreira, e um streamer brasileiro conhecido por lives de jogos, humor e conteudo na Twitch/YouTube.",
        }

    if "tesla" in text:
        return {
            "intent": "respond",
            "target": None,
            "response": "Tesla pode ser a empresa de carros eletricos e energia fundada por Elon Musk e outros socios, ou Nikola Tesla, o inventor associado a corrente alternada. Se quiser, eu diferencio os dois.",
        }

    if "recursao" in text or "recursivo" in text:
        return {
            "intent": "respond",
            "target": None,
            "response": "Recursao em Python e quando uma funcao chama ela mesma para resolver um problema em partes menores. O ponto principal e ter um caso base para parar; sem isso, a funcao entra em repeticao infinita ate estourar o limite de recursao.",
        }

    if "pergunta" in text and "aleatoria" in text and any(word in text for word in {"responde", "responder"}):
        return {
            "intent": "respond",
            "target": None,
            "response": "Sim. Se a pergunta for aleatoria, eu tento responder pelo chat geral; se ela parecer sobre arquivo, tela, agenda ou comando, eu tento encaminhar para a funcao certa.",
        }

    return None


def detect_short_unclear_text(user_input: str):
    text = normalize_text(user_input)

    if text in REPEAT_PATTERNS:
        return {"intent": "repeat_last", "target": None}

    if text in {"faz aquilo", "faz isso", "faz aquele negocio", "faz esse negocio", "abre aquilo", "resolve isso"}:
        return {
            "intent": "respond",
            "target": None,
            "response": "Esse comando ficou vago. Me diga o alvo ou a acao, por exemplo: abrir Chrome, resumir arquivo ou analisar tela.",
        }

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
    text = normalize_text(user_input)
    if text.startswith(FACTUAL_QUESTION_PREFIXES) or "?" in str(user_input or ""):
        return None
    if text.startswith(GENERAL_EXPLANATION_PREFIXES):
        return None

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


def detect_question_fallback(user_input: str):
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None
    if text.startswith(GENERAL_EXPLANATION_PREFIXES):
        return {
            "intent": "respond",
            "target": None,
            "response": "Posso explicar, mas agora nao consegui acionar uma resposta completa do chat. Tente reformular com o tema e o nivel desejado, por exemplo: explique recursao em Python para iniciante.",
        }
    if text.startswith(FACTUAL_QUESTION_PREFIXES) or "?" in str(user_input or ""):
        return {
            "intent": "respond",
            "target": None,
            "response": "Não consegui confirmar uma resposta boa agora. Posso tentar de novo com mais contexto ou usando pesquisa.",
        }
    return None


CONVERSATION_DETECTORS = (
    detect_short_unclear_text,
    detect_builtin_general_answer,
    detect_llm_action_command,
    detect_ollama_chat,
    detect_question_fallback,
    detect_light_conversation,
)
