from __future__ import annotations

import re

from core.router_apps import _strip_leading_articles
from core.router_media import MEDIA_TARGETS
from core.router_utils import normalize_text

MUSIC_SESSION_ALIASES = {
    "alegre": "alegre",
    "animada": "alegre",
    "animado": "alegre",
    "feliz": "alegre",
    "pra cima": "alegre",
    "algo agre": "alegre",
    "igual agre": "alegre",
    "agre": "alegre",
    "calma": "calmo",
    "calmo": "calmo",
    "relaxante": "calmo",
    "tranquila": "calmo",
    "tranquilo": "calmo",
    "rock": "rock",
    "rock n rock": "rock",
    "rock in rock": "rock",
    "roque": "rock",
    "rock and roll": "rock",
    "classica": "classico",
    "classico": "classico",
    "musica classica": "classico",
    "mpb": "mpb",
    "jazz": "jazz",
    "gospel": "gospel",
    "louvor": "gospel",
    "pop": "pop",
    "eletronica": "eletronica",
    "eletronico": "eletronica",
    "rap": "rap",
    "hip hop": "rap",
    "samba": "samba",
    "pagode": "samba",
    "sertanejo": "sertanejo",
    "foco": "foco",
    "concentracao": "foco",
    "estudo": "foco",
    "estudar": "foco",
    "trabalhar": "foco",
    "focar": "foco",
    "treino": "treino",
    "academia": "treino",
    "triste": "triste",
    "melancolica": "triste",
    "melancolico": "triste",
}

SPOTIFY_STANDALONE_SONG_ALIASES = {
    "filho meu": "filho meu",
    "ah filho meu": "filho meu",
    "a filho meu": "filho meu",
    "o filho meu": "filho meu",
    "do meu": "filho meu",
    "filho mil": "filho meu",
}


def _music_command_segment(text: str) -> str:
    phrase = normalize_text(text).strip(" .,:;-")
    if not re.search(r"\b(?:doca|docar|toca|tocar|toque|coloca|coloque|bota|botar)\b", phrase):
        return phrase

    if re.search(
        r"\b(?:doca|docar|toca|tocar|toque|coloca|coloque|bota|botar)\s+"
        r"(?:uma\s+)?(?:musica|música|som|playlist)\s+(?:para|pra)\s+(?:eu\s+)?(?:estudar|trabalhar|focar)\b",
        phrase,
    ):
        return phrase

    for pattern in (
        r"\s+(?:e\s+depois|e|ai|aí|depois)\s+(?:me\s+)?(?:da|dá|de|dê|fala|explique|explica|mostra|mostre|abre|abra)\b",
        r"\s+(?:para|pra)\s+(?:eu\s+)?(?:estudar|treinar|trabalhar|focar)\b",
    ):
        match = re.search(pattern, phrase)
        if match:
            return phrase[: match.start()].strip(" .,:;-")
    return phrase


def _strip_music_polite_prefix(text: str) -> str:
    phrase = normalize_text(text).strip(" .,:;-")
    phrase = re.sub(r"^(?:axel|estagiario|assistente)\s+", "", phrase).strip()
    phrase = re.sub(r"^(?:voce|vc)\s+", "", phrase).strip()
    phrase = re.sub(
        r"^(?:poderia|pode|consegue|conseguiria|daria para|da para|por favor|por gentileza)\s+",
        "",
        phrase,
    ).strip()
    phrase = re.sub(r"^(?:tocar|toca|toque|colocar|coloca|coloque|botar|bota)\s+", "", phrase).strip()
    phrase = re.sub(r"^(?:a\s+musica|uma\s+musica|musica|o\s+som|um\s+som|som)\s+", "", phrase).strip()
    phrase = re.sub(r"\s+(?:no|na)\s+(?:spotify|spotfy|spoti|espotify)$", "", phrase).strip()
    return _strip_leading_articles(phrase).strip(" .,:;-")


def _extract_music_session_vibe(text: str) -> str:
    phrase = _strip_leading_articles(normalize_text(text)).strip(" .,:;-")
    for interjection in ("e ", "eh ", "é ", "cara ", "carai ", "ah ", "a "):
        if phrase.startswith(interjection):
            phrase = phrase[len(interjection):].strip(" .,:;-")
            break
    for prefix in (
        "algo para ",
        "algo pra ",
        "algo ",
        "alguma coisa para ",
        "alguma coisa pra ",
        "alguma coisa ",
        "uma musica para eu ",
        "uma musica para ",
        "uma musica pra eu ",
        "uma musica pra ",
        "uma musica ",
        "musica para eu ",
        "musica para ",
        "musica pra eu ",
        "musica pra ",
        "musica ",
        "umas musicas para eu ",
        "umas musicas para ",
        "umas musicas pra eu ",
        "umas musicas pra ",
        "umas musicas ",
        "musicas para eu ",
        "musicas para ",
        "musicas pra eu ",
        "musicas pra ",
        "musicas ",
        "um som para eu ",
        "um som para ",
        "um som pra eu ",
        "um som pra ",
        "um som ",
        "som para eu ",
        "som para ",
        "som pra eu ",
        "som pra ",
        "som ",
        "uma playlist para eu ",
        "uma playlist para ",
        "uma playlist pra eu ",
        "uma playlist pra ",
        "uma playlist ",
        "playlist para eu ",
        "playlist para ",
        "playlist pra eu ",
        "playlist pra ",
        "playlist ",
        "um estilo ",
        "estilo ",
    ):
        if phrase.startswith(prefix):
            phrase = phrase[len(prefix):].strip(" .,:;-")
            break
    phrase = _strip_leading_articles(phrase).strip(" .,:;-")
    return MUSIC_SESSION_ALIASES.get(phrase, "")


def detect_music_command(user_input: str):
    lower = _music_command_segment(user_input)

    if (
        "spotify" in lower
        and any(token in lower for token in {
            "diagnosticar",
            "diagnostica",
            "diagnosticare",
            "diagnostico",
            "diagnosticar e",
            "diagnostica e",
            "jagnoche",
            "debug",
            "ver spotify",
        })
    ):
        return {"intent": "spotify_diagnostic", "target": None}

    if (
        any(token in lower for token in {"curtir", "curta", "adicionar", "adicione", "salvar", "salve"})
        and any(token in lower for token in {"musicas curtidas", "músicas curtidas", "liked songs", "curtidas"})
    ):
        return {"intent": "spotify_like_current_track", "target": None}

    if "spotify" in lower and "filho" in lower and any(token in lower for token in {"meu", "mil"}):
        return {
            "intent": "browser_search_music",
            "target": {"service": "spotify", "query": "filho meu"},
        }

    music_match = re.match(
        r"^(?:doca|docar|toca|tocar|toque|procure|procurar|pesquise|pesquisar|buscar|busque)\s+(?:a\s+musica\s+|musica\s+)?(.+?)\s+(?:no|na)\s+(spotify|spotfy|spoti|espotify|youtube|you tube)$",
        lower,
    )
    if music_match:
        service = "youtube" if music_match.group(2) in {"youtube", "you tube"} else "spotify"
        return {
            "intent": "browser_search_music",
            "target": {
                "service": service,
                "query": _strip_leading_articles(music_match.group(1).strip()),
            },
        }

    embedded_music_session_match = re.search(
        r"(?:doca|docar|toca|tocar|toque|coloca|coloque|bota|botar)\s+([^?.,!]+)",
        lower,
    )
    if embedded_music_session_match:
        vibe = _extract_music_session_vibe(embedded_music_session_match.group(1))
        if vibe:
            return {
                "intent": "browser_music_session",
                "target": {"service": "spotify", "vibe": vibe},
            }

    has_music_request = (
        "spotify" in lower
        or any(token in lower.split() for token in {"tocar", "toca", "toque", "colocar", "coloca", "coloque", "botar", "bota"})
    )
    polite_music_query = _strip_music_polite_prefix(lower) if has_music_request else ""
    if polite_music_query and polite_music_query != lower and polite_music_query not in MEDIA_TARGETS:
        polite_vibe = _extract_music_session_vibe(polite_music_query)
        if polite_vibe:
            return {
                "intent": "browser_music_session",
                "target": {"service": "spotify", "vibe": polite_vibe},
            }
        return {
            "intent": "browser_search_music",
            "target": {
                "service": "spotify",
                "query": SPOTIFY_STANDALONE_SONG_ALIASES.get(polite_music_query, polite_music_query),
            },
        }

    if lower in {
        "me surpreenda",
        "me surpreende",
        "me surpreenda no spotify",
        "me surpreende no spotify",
        "surpreenda me",
        "surpreenda-me",
        "surpreende me",
        "surpreende-me",
        "surpreendo",
        "surpreenda",
        "surpreende",
        "prinda",
        "toca algo aleatorio",
        "tocar algo aleatorio",
        "toque algo aleatorio",
        "toca qualquer coisa",
        "tocar qualquer coisa",
        "toque qualquer coisa",
        "toca uma musica aleatoria",
        "tocar uma musica aleatoria",
        "toque uma musica aleatoria",
        "toca uma surpresa",
        "tocar uma surpresa",
        "toque uma surpresa",
        "me indica uma musica",
        "indica uma musica",
        "me recomende uma musica",
        "recomende uma musica",
        "me recomenda uma musica",
        "recomenda uma musica",
    }:
        return {
            "intent": "browser_surprise_music",
            "target": {"service": "spotify"},
        }

    standalone_song_query = SPOTIFY_STANDALONE_SONG_ALIASES.get(lower)
    if standalone_song_query:
        return {
            "intent": "browser_search_music",
            "target": {"service": "spotify", "query": standalone_song_query},
        }

    standalone_vibe = _extract_music_session_vibe(lower)
    if standalone_vibe:
        return {
            "intent": "browser_music_session",
            "target": {"service": "spotify", "vibe": standalone_vibe},
        }

    music_session_match = re.match(
        r"^(?:doca|docar|toca|tocar|toque|coloca|coloque|bota|botar)\s+(.+?)(?:\s+(?:no|na)\s+(spotify|spotfy|spoti|espotify))?$",
        lower,
    )
    if music_session_match:
        vibe = _extract_music_session_vibe(music_session_match.group(1))
        if vibe:
            return {
                "intent": "browser_music_session",
                "target": {"service": "spotify", "vibe": vibe},
            }

    queue_music_match = re.match(
        r"^(?:adicionar|adicione|colocar|coloque|bota|botar|manda|mandar)\s+(.+?)\s+(?:na|a|para a|pra)\s+fila(?:\s+(?:do|no|da|na)\s+(spotify|spotfy|spoti|espotify))?$",
        lower,
    )
    if queue_music_match:
        return {
            "intent": "browser_queue_music",
            "target": {
                "service": "spotify",
                "query": _strip_leading_articles(queue_music_match.group(1).strip()),
            },
        }

    queue_music_prefix_match = re.match(
        r"^(?:adicionar|adicione|colocar|coloque|bota|botar)\s+(?:na|a|para a|pra)\s+fila\s+(.+)$",
        lower,
    )
    if queue_music_prefix_match:
        return {
            "intent": "browser_queue_music",
            "target": {
                "service": "spotify",
                "query": _strip_leading_articles(queue_music_prefix_match.group(1).strip()),
            },
        }

    if lower in {
        "abrir curtidas",
        "abrir minhas curtidas",
        "abre curtidas",
        "abre minhas curtidas",
        "tocar curtidas",
        "toque curtidas",
        "abrir musicas curtidas",
        "abrir minhas musicas curtidas",
        "abre musicas curtidas",
        "abre minhas musicas curtidas",
        "playlist musicas curtidas",
    }:
        return {
            "intent": "browser_search_music",
            "target": {"service": "spotify", "query": "musicas curtidas"},
        }

    default_music_match = re.match(
        r"^(?:doca|docar|toca|tocar|toque)\s+(?:a\s+musica\s+|musica\s+)?(.+)$",
        lower,
    )
    if default_music_match:
        query = _strip_leading_articles(default_music_match.group(1).strip())
        if query and query not in MEDIA_TARGETS:
            return {
                "intent": "browser_search_music",
                "target": {
                    "service": "spotify",
                    "query": query,
                },
            }

    return None


MUSIC_DETECTORS = [
    detect_music_command,
]
