from __future__ import annotations

import difflib
import re

from core.router_utils import normalize_text
from memory.profile import get_value, set_value
from tools.math_tools import calculate_basic_expression, calculate_percentage

BLUETOOTH_TERMS = {
    "bluetooth",
    "blue tooth",
    "blue tu",
    "blu tu",
    "bluetoot",
    "bluetooh",
    "blueto",
    "blutufi",
    "blutufe",
    "blutut",
}

CHATTER_PATTERNS = {
    "ok": "Certo.",
    "okay": "Certo.",
    "okey": "Certo.",
    "boa": "Estou ouvindo.",
    "opa": "Estou aqui.",
    "e ai": "Fala comigo.",
    "oi": "Ola.",
    "ola": "Ola.",
    "axel esta ai": "Estou aqui.",
    "axel ta ai": "Estou aqui.",
    "estagiario esta ai": "Estou aqui.",
    "estagiario ta ai": "Estou aqui.",
    "assistente esta ai": "Estou aqui.",
    "assistente ta ai": "Estou aqui.",
    "voce esta ai": "Estou aqui.",
    "voce ta ai": "Estou aqui.",
    "posso falar": "Pode falar.",
    "ta ouvindo": "Estou ouvindo sim.",
    "esta ouvindo": "Estou ouvindo sim.",
    "tudo bem": "Tudo certo por aqui. Pronto para comecar.",
    "como voce esta": "Estou bem. Com vontade de ser util.",
    "como voce ta": "Estou bem. Pode mandar.",
    "obrigado": "Disponha. Estamos juntos.",
    "obrigada": "Disponha. Estamos juntos.",
    "valeu": "Valeu. Seguimos.",
    "bom trabalho": "Obrigado. Estou pegando o jeito.",
    "muito bom": "Boa. Isso significa que estamos evoluindo.",
    "vamos trabalhar": "Vamos sim. Me diga o que quer fazer.",
    "vamos avancar": "Vamos avancar. Qual frente voce quer puxar agora?",
    "quem e voce": "Sou o Axel, seu assistente local. Eu ajudo no computador, organizo contexto e aprendo seus atalhos para transformar comandos em acao.",
    "o que voce e": "Sou seu assistente local. Ainda em evolucao, mas dedicado.",
    "qual seu nome": "Meu nome e Axel. Local, pratico e com uma paciencia computacional quase elegante.",
    "qual e seu nome": "Meu nome e Axel. Local, pratico e com uma paciencia computacional quase elegante.",
    "o que voce sabe fazer": "Posso abrir aplicativos e sites, controlar janelas, navegar no navegador, controlar midia, lembrar atalhos e responder comandos por voz.",
    "o que voce consegue fazer": "Posso abrir aplicativos e sites, controlar janelas, navegar no navegador, controlar midia, lembrar atalhos e responder comandos por voz.",
    "me conta uma coisa interessante": "Uma coisa interessante: quase toda automacao boa nasce de uma frase irritante repetida muitas vezes. A gente esta transformando irritacao em botao invisivel.",
    "fala uma coisa interessante": "Uma coisa interessante: quase toda automacao boa nasce de uma frase irritante repetida muitas vezes. A gente esta transformando irritacao em botao invisivel.",
}

AXEL_INTRODUCTION = (
    "Prazer, eu sou o Axel, o assistente local do Pedro. "
    "Eu ajudo a controlar o computador por voz, abrir aplicativos e sites, navegar, ler telas, organizar contexto e lembrar preferencias importantes. "
    "A ideia nao e substituir ninguem: e tirar pequenos atritos do caminho para o Pedro pensar, estudar, programar e decidir melhor. "
    "Ainda estou evoluindo, mas ja tenho uma especialidade bem clara: transformar frases soltas em acoes uteis."
)


def _contains_bluetooth(text: str) -> bool:
    normalized = normalize_text(text)
    compact = normalized.replace(" ", "")

    if any(term in normalized for term in BLUETOOTH_TERMS):
        return True

    if any(term.replace(" ", "") in compact for term in BLUETOOTH_TERMS):
        return True

    words = normalized.split()
    for size in range(min(2, len(words)), 0, -1):
        for start in range(0, len(words) - size + 1):
            chunk = "".join(words[start:start + size])
            if difflib.SequenceMatcher(None, chunk, "bluetooth").ratio() >= 0.68:
                return True

    return False


def _has_any_word(text: str, words: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def detect_user_name(user_input: str):
    text = user_input.strip()
    lower = normalize_text(user_input)

    if "meu nome e" in lower:
        idx = lower.find("meu nome e")
        name = text[idx + len("meu nome e"):].strip()

        if name:
            set_value("nome", name)
            return {"intent": "respond", "target": None, "response": f"Ok, vou lembrar que seu nome e {name}."}

    return None


def detect_profile_question(user_input: str):
    text = normalize_text(user_input)
    patterns = [
        "qual meu nome",
        "qual o meu nome",
        "qual e o meu nome",
        "voce sabe meu nome",
        "meu nome",
    ]

    if text in patterns or any(p in text for p in patterns):
        name = get_value("nome")
        if name:
            return {"intent": "respond", "target": None, "response": f"Seu nome e {name}."}
        return {"intent": "respond", "target": None, "response": "Ainda nao sei seu nome."}

    return None


def detect_greeting(user_input: str):
    text = normalize_text(user_input)

    if text in {
        "axel se apresente",
        "axel apresente se",
        "axel apresenta voce",
        "axel se apresenta",
        "axel pode se apresentar",
        "axel pode se apresente",
        "se apresente",
        "apresente se",
        "apresenta voce",
        "apresenta o axel",
        "apresente o axel",
        "quem e o axel",
        "quem e axel",
        "o que e o axel",
        "fale de voce",
        "fala de voce",
        "conte quem voce e",
        "conta quem voce e",
    }:
        return {"intent": "respond", "target": None, "response": AXEL_INTRODUCTION}

    if text.startswith("axel ") and any(phrase in text for phrase in {"se apresente", "apresente se", "quem voce e", "quem e voce"}):
        return {"intent": "respond", "target": None, "response": AXEL_INTRODUCTION}

    if text in CHATTER_PATTERNS:
        return {"intent": "respond", "target": None, "response": CHATTER_PATTERNS[text]}

    if "bom dia" in text:
        return {"intent": "respond", "target": None, "response": "Bom dia. Vamos colocar esse computador em movimento."}

    if "boa tarde" in text:
        return {"intent": "respond", "target": None, "response": "Boa tarde. Estou pronto."}

    if "boa noite" in text:
        return {"intent": "respond", "target": None, "response": "Boa noite. Modo estagiario noturno ativado."}

    if any(phrase in text for phrase in {"voce e legal", "voce e bom", "voce e massa"}):
        return {"intent": "respond", "target": None, "response": "Obrigado. Eu tento compensar a falta de cafe com processamento."}

    if difflib.SequenceMatcher(None, text, "qual o seu nome").ratio() >= 0.78:
        return {"intent": "respond", "target": None, "response": CHATTER_PATTERNS["qual seu nome"]}

    heard_about_match = re.search(r"(?:voce\s+)?(?:ja\s+)?ouviu falar(?:\s+de|\s+sobre)?\s+(.+)", text)
    if heard_about_match:
        subject = heard_about_match.group(1).strip(" .")
        if subject:
            return {
                "intent": "respond",
                "target": None,
                "response": f"Ja ouvi falar de {subject}. O que voce quer saber sobre isso?",
            }

    if any(phrase in text for phrase in {"conversa comigo", "vamos conversar", "quero conversar"}):
        return {"intent": "start_conversation", "target": None}

    if any(phrase in text for phrase in {"parar conversa", "para conversa", "chega de conversa", "sair da conversa", "modo comando", "voltar comandos"}):
        return {"intent": "stop_conversation", "target": None}

    if any(phrase in text for phrase in {"esta funcionando", "funcionou", "deu certo"}):
        return {"intent": "respond", "target": None, "response": "Boa. Pequena vitoria registrada."}

    if any(phrase in text for phrase in {"nao funcionou", "deu errado", "falhou"}):
        return {"intent": "respond", "target": None, "response": "Entendi. Me diga o que aconteceu que eu tento ajustar."}

    return None


def detect_math(user_input: str):
    result = calculate_percentage(user_input)
    if result:
        return {"intent": "respond", "target": None, "response": result}

    result = calculate_basic_expression(user_input)
    if result:
        return {"intent": "respond", "target": None, "response": result}

    return None


def detect_bluetooth_command(user_input: str):
    lower = normalize_text(user_input)

    if not _contains_bluetooth(lower):
        return None

    if _has_any_word(lower, {"desativar", "desativa", "desative", "desligar", "desliga", "desligue", "off"}):
        return {"intent": "bluetooth_off", "target": None}

    if _has_any_word(lower, {"ativar", "ativa", "ative", "ligar", "liga", "ligue", "on"}):
        return {"intent": "bluetooth_on", "target": None}

    if _has_any_word(lower, {"status", "estado", "ligado", "desligado", "consultar", "verificar"}):
        return {"intent": "bluetooth_status", "target": None}

    if _has_any_word(lower, {"abrir", "abre", "abra", "configuracao", "configuracoes", "ajuste", "ajustes", "tela"}):
        return {"intent": "bluetooth_settings", "target": None}

    return {"intent": "bluetooth_settings", "target": None}


BASIC_EARLY_DETECTORS = (
    detect_user_name,
    detect_greeting,
    detect_math,
    detect_bluetooth_command,
)

BASIC_LATE_DETECTORS = (
    detect_profile_question,
)
