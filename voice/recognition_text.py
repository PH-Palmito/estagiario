from __future__ import annotations

import difflib
import re
import unicodedata

COMMAND_VOCAB = {
    "abre",
    "abrir",
    "abri",
    "abriu",
    "abrei",
    "fecha",
    "fechar",
    "foca",
    "focar",
    "minimiza",
    "maximiza",
    "restaura",
    "pesquisa",
    "pesquisar",
    "procura",
    "procurar",
    "buscar",
    "busca",
    "tela",
    "pagina",
    "janela",
    "resuma",
    "resume",
    "resumir",
    "resumo",
    "detalha",
    "detalhar",
    "explica",
    "github",
    "youtube",
    "spotify",
    "tocar",
    "toque",
    "musica",
    "musicas",
    "alegre",
    "calmo",
    "calma",
    "rock",
    "classico",
    "classica",
    "jazz",
    "gospel",
    "fila",
    "surpreenda",
    "surpreende",
    "filho",
    "meu",
    "blindado",
    "chrome",
    "google",
    "whatsapp",
    "zap",
    "mercado",
    "livre",
    "magalu",
    "bloco",
    "notas",
    "android",
    "studio",
    "vscode",
    "code",
    "edge",
}

ENGLISH_NOISE_TOKENS = {
    "how",
    "did",
    "do",
    "does",
    "you",
    "your",
    "he",
    "she",
    "his",
    "her",
    "me",
    "on",
    "in",
    "the",
    "this",
    "that",
    "whats",
    "what",
    "is",
    "are",
}


def strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def normalize_recognized_text(text: str) -> str:
    normalized = strip_accents(text.lower().strip())
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def command_token_similarity(token: str) -> float:
    if not token:
        return 0.0
    return max((difflib.SequenceMatcher(None, token, candidate).ratio() for candidate in COMMAND_VOCAB), default=0.0)


def command_transcription_score(text: str) -> float:
    normalized = normalize_recognized_text(text)
    tokens = [token for token in normalized.split() if token]
    if not tokens:
        return 0.0

    score = 0.0
    for token in tokens:
        similarity = command_token_similarity(token)
        if similarity >= 0.9:
            score += 2.2
        elif similarity >= 0.78:
            score += 1.2
        elif similarity >= 0.68:
            score += 0.5

        if token in ENGLISH_NOISE_TOKENS:
            score -= 1.4

    if any(token in {"tela", "pagina", "youtube", "github", "spotify", "chrome"} for token in tokens):
        score += 0.8

    return score / max(1, len(tokens))


def should_retry_command_transcription(text: str) -> bool:
    normalized = normalize_recognized_text(text)
    tokens = [token for token in normalized.split() if token]
    if not tokens:
        return False

    if len(tokens) == 1 and command_token_similarity(tokens[0]) >= 0.84:
        return False

    score = command_transcription_score(text)
    english_hits = sum(1 for token in tokens if token in ENGLISH_NOISE_TOKENS)

    if english_hits >= 1 and score < 0.45:
        return True

    if len(tokens) <= 5 and score < 0.28:
        return True

    return False


def is_prompt_hallucination(text: str) -> bool:
    normalized = normalize_recognized_text(text)
    if not normalized:
        return False

    prompt_fragments = {
        "comandos curtos em portugues do brasil",
        "comandos em portugues do brasil",
        "legendas pela comunidade de amara org",
        "legendas pela comunidade amara org",
        "amara org",
        "transcreva sempre em portugues do brasil",
        "conversa casual em portugues do brasil",
        "verbos comuns abrir fechar focar trocar minimizar maximizar restaurar pesquisar ler selecionar",
    }
    if normalized in prompt_fragments:
        return True

    return any(fragment in normalized for fragment in prompt_fragments)


def extract_inline_command(text: str, hotword: str) -> str:
    hotword_normalized = normalize_recognized_text(hotword)
    normalized_text = normalize_recognized_text(text)

    if not normalized_text or not hotword_normalized:
        return ""

    if normalized_text == hotword_normalized:
        return ""

    original_tokens = text.strip().split()
    normalized_tokens = [normalize_recognized_text(token) for token in original_tokens]
    hotword_tokens = hotword_normalized.split()
    hotword_token_count = len(hotword_tokens)

    for start in range(0, len(normalized_tokens) - hotword_token_count + 1):
        window = normalized_tokens[start:start + hotword_token_count]
        if window == hotword_tokens:
            command_tokens = original_tokens[start + hotword_token_count:]
            return " ".join(command_tokens).strip(" ,.!?:;")

        candidate = " ".join(window).strip()
        if difflib.SequenceMatcher(None, candidate, hotword_normalized).ratio() >= 0.74:
            command_tokens = original_tokens[start + hotword_token_count:]
            return " ".join(command_tokens).strip(" ,.!?:;")

    if normalized_text.startswith(hotword_normalized + " "):
        return text[len(text.split()[0]):].strip(" ,.!?:;")

    return ""


def contains_hotword(text: str, hotword: str) -> bool:
    normalized_text = text.lower().strip()
    if hotword in normalized_text:
        return True

    for token in normalized_text.replace(",", " ").replace(".", " ").split():
        if difflib.SequenceMatcher(None, token, hotword).ratio() >= 0.72:
            return True

    if difflib.SequenceMatcher(None, normalized_text, hotword).ratio() >= 0.62:
        return True

    return False
