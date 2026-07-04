from __future__ import annotations

import re

from core.router_apps import APP_DETECTORS, command_target_segment
from core.router_daily import detect_reminder_command
from core.router_music import _extract_music_session_vibe, detect_music_command
from core.router_search_utils import cleanup_marketplace_query, cleanup_site_query, strip_search_conversation_tail
from core.router_utils import normalize_text


TRAILING_ACTION_VERBS = (
    "abra",
    "abre",
    "abrir",
    "inicie",
    "iniciar",
    "toca",
    "toque",
    "tocar",
    "coloca",
    "coloque",
    "botar",
    "bota",
    "foca",
    "foque",
    "focar",
    "troca",
    "troque",
    "vai",
    "volta",
    "pesquisa",
    "pesquise",
    "pesquisar",
    "procure",
    "buscar",
    "busque",
    "lembre",
    "lembra",
    "lembrar",
    "avise",
    "avisa",
    "avisar",
)

LEADING_PRIMARY_ACTION_PATTERN = re.compile(
    r"^(?:"
    r"adicionar|adicione|agenda|agendar|"
    r"me\s+lembre|me\s+lembra|lembre|lembra|avise|avisa|"
    r"abra|abre|abrir|inicie|iniciar|"
    r"toca|toque|tocar|coloca|coloque|botar|bota|"
    r"foca|foque|focar|troca|troque|vai|volta|"
    r"pesquisa|pesquise|pesquisar|procure|buscar|busque"
    r")\b"
)


def _trailing_action_segment(user_input: str) -> str:
    phrase = normalize_text(user_input).strip(" .,:;-")
    if LEADING_PRIMARY_ACTION_PATTERN.search(phrase):
        return ""
    verb_pattern = "|".join(re.escape(verb) for verb in TRAILING_ACTION_VERBS)
    match = re.search(
        rf"\b(?:e\s+depois|e|ai|aí|depois)\s+(?=(?:me\s+)?(?:{verb_pattern})\b)",
        phrase,
    )
    if not match or match.start() <= 0:
        return ""
    return phrase[match.end() :].strip(" .,:;-")


def _detect_trailing_action(user_input: str):
    segment = _trailing_action_segment(user_input)
    if not segment:
        return None

    fast_result = _detect_fast_path_core(segment)
    if fast_result and fast_result.get("intent") != "respond":
        return fast_result

    for detector in (detect_music_command, detect_reminder_command, *APP_DETECTORS):
        result = detector(segment)
        if result and result.get("intent") != "respond":
            return result
    return None


def _detect_fast_path_core(user_input: str):
    lower = command_target_segment(strip_search_conversation_tail(user_input))
    if not lower:
        return None

    if lower in {"abrir spotify", "abre spotify", "abrir o spotify", "abre o spotify"}:
        return {"intent": "open_app", "target": "spotify"}

    if lower in {
        "gostei dessa",
        "gostei dessa musica",
        "gostei da musica",
        "curte essa",
        "curtir essa",
        "salva essa",
        "salve essa",
        "adiciona essa nas curtidas",
        "adicione essa nas curtidas",
    }:
        return {"intent": "spotify_like_current_track", "target": None}

    if lower in {
        "nao gostei",
        "nao gostei dessa",
        "nao gostei dessa musica",
        "pula essa",
        "pular essa",
    }:
        return {"intent": "spotify_dislike_current_track", "target": None}

    if lower in {
        "mais desse estilo",
        "mais nessa linha",
        "mais disso",
        "toca algo parecido",
        "toque algo parecido",
        "coloca algo parecido",
        "mais parecidas",
    }:
        return {"intent": "spotify_more_like_current_track", "target": None}

    less_vibe_match = re.match(r"^(?:menos|nao quero)\s+(.+)$", lower)
    if less_vibe_match:
        vibe = _extract_music_session_vibe(less_vibe_match.group(1))
        if vibe:
            return {"intent": "spotify_less_music_vibe", "target": {"vibe": vibe}}

    if lower in {"que no mercado livre", "no mercado livre"}:
        return {"intent": "respond", "target": None, "response": "Qual produto voce quer pesquisar no Mercado Livre?"}

    if "mercado livre" in lower or "mercadolivre" in lower or "mercado de" in lower:
        market_query = re.sub(r"\b(?:mercado\s+livre|mercadolivre|mercado\s+de)\b", " ", lower)
        market_query = re.sub(
            r"\b(?:comandos?|comando|de|para|pra|pode|poderia|consegue|conseguiria|"
            r"pesquisa|pesquise|pesquisar|esquisa|esquise|esquisar|quisa|quise|quisar|"
            r"procure|procurar|buscar|busque|no|na|em|dentro|do|da)\b",
            " ",
            market_query,
        )
        market_query = re.sub(r"\s+", " ", market_query).strip(" .")
        market_query = cleanup_marketplace_query(market_query)
        if market_query and market_query not in {"que", "o que", "isso"}:
            return {
                "intent": "browser_search_site",
                "target": {
                    "query": market_query,
                    "site": "https://www.mercadolivre.com.br",
                },
            }

    market_match = re.match(
        r"^(?:comandos?\s+(?:de|para|pra)\s+)?(?:pode\s+|poderia\s+|consegue\s+|conseguiria\s+|da\s+para\s+|daria\s+para\s+)?(?:pesquisa|pesquise|pesquisar|esquisa|esquise|esquisar|quisa|quise|quisar|procure|procurar|buscar|busque)\s+(.+?)\s+(?:no|na|em|dentro\s+do|dentro\s+da)\s+(mercado\s+livre|mercadolivre|mercado\s+de)$",
        lower,
    )
    if market_match:
        return {
            "intent": "browser_search_site",
            "target": {
                "query": cleanup_marketplace_query(market_match.group(1)),
                "site": "https://www.mercadolivre.com.br",
            },
        }

    if (
        ("youtube" in lower or "you tube" in lower)
        and lower not in {"youtube", "you tube", "abrir youtube", "abre youtube", "abrir o youtube", "abre o youtube"}
    ):
        youtube_query = re.sub(r"\b(?:youtube|you\s+tube)\b", " ", lower)
        youtube_query = cleanup_site_query(youtube_query)
        if youtube_query and youtube_query not in {"que", "o que", "isso"}:
            return {
                "intent": "browser_search_site",
                "target": {
                    "query": youtube_query,
                    "site": "https://www.youtube.com",
                },
            }

    youtube_match = re.match(
        r"^(?:comandos?\s+(?:de|para|pra)\s+)?(?:pode\s+|poderia\s+|consegue\s+|conseguiria\s+|da\s+para\s+|daria\s+para\s+)?(?:pesquisa|pesquise|pesquisar|esquisa|esquise|esquisar|quisa|quise|quisar|procure|procurar|buscar|busque)\s+(.+?)\s+(?:no|na|em|dentro\s+do|dentro\s+da)\s+(youtube|you\s+tube)$",
        lower,
    )
    if youtube_match:
        return {
            "intent": "browser_search_site",
            "target": {
                "query": cleanup_site_query(youtube_match.group(1)),
                "site": "https://www.youtube.com",
            },
        }

    return detect_music_command(user_input)


def detect_fast_path_command(user_input: str):
    trailing_action = _detect_trailing_action(user_input)
    if trailing_action:
        return trailing_action

    return _detect_fast_path_core(user_input)


FAST_PATH_DETECTORS = (
    detect_fast_path_command,
)
