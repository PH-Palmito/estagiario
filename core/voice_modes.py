from __future__ import annotations

from core.router_utils import normalize_text


def is_conversation_stop(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in {
        "parar conversa",
        "para conversa",
        "chega de conversa",
        "sair da conversa",
        "modo comando",
        "voltar comandos",
    }


def is_dictation_start(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in {
        "modo ditado",
        "ativar ditado",
        "ativa ditado",
        "iniciar ditado",
        "inicia ditado",
        "comecar ditado",
        "comecar o ditado",
        "comeca ditado",
        "ditado",
    }


def is_dictation_stop(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in {
        "parar ditado",
        "para ditado",
        "encerrar ditado",
        "encerra ditado",
        "sair do ditado",
        "fechar ditado",
        "modo comando",
        "voltar comandos",
    }


def format_dictation_text(text: str) -> str:
    normalized = normalize_text(text)
    special_tokens = {
        "nova linha": "\r\n",
        "novo paragrafo": "\r\n\r\n",
        "novo parágrafo": "\r\n\r\n",
        "tabulacao": "\t",
        "tabulação": "\t",
        "tab": "\t",
    }
    if normalized in special_tokens:
        return special_tokens[normalized]
    return text.strip()


def is_transcription_artifact(text: str) -> bool:
    normalized = normalize_text(text)
    normalized_without_dots = normalized.replace(".", " ")
    artifacts = {
        "legendas pela comunidade de amara org",
        "legendas pela comunidade de amara.org",
        "aplicativos e sites esperados em portugues do brasil",
        "exemplos e sites esperados",
        "tem que ter o volume correto",
        "comandos curtos em portugues do brasil",
        "transcreva comandos curtos",
        "transcreva comandos curtos em portugues do brasil",
        "assistente local chamado estagiario",
        "vocabulario esperado",
    }

    return any(artifact in normalized or artifact in normalized_without_dots for artifact in artifacts)


def is_unreliable_conversation_text(text: str) -> bool:
    normalized = normalize_text(text)

    if is_transcription_artifact(text):
        return True

    if not normalized:
        return True

    words = normalized.split()
    if len(words) == 1 and len(normalized) <= 2:
        return True

    promptish_fragments = {
        "portugues do brasil",
        "comandos curtos",
        "sites esperados",
        "vocabulario esperado",
        "exemplos",
        "comunidade de amara",
    }
    if any(fragment in normalized for fragment in promptish_fragments):
        return True

    if len(words) >= 18:
        unique_ratio = len(set(words)) / max(1, len(words))
        if unique_ratio < 0.3 and "um dois" not in normalized:
            return True

    return False
