from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from core.router_utils import normalize_text
from core.voice_command_classifier import normalize_voice_command

RouteCommand = Callable[[str], Mapping[str, object]]
ApplyVoiceCorrection = Callable[[str], str]

CONTEXTUAL_FOLLOWUP_PREFIXES = (
    "o que voce acha",
    "o que vc acha",
    "o que acha",
    "o que voce pensa",
    "o que pensa",
    "voce acha",
    "vc acha",
    "acha que",
    "existem",
    "existe",
    "tem",
    "qual sua opiniao",
    "qual a sua opiniao",
    "qual sua leitura",
    "me explica",
    "me explique",
    "explica",
    "explique",
    "detalha isso",
    "detalhar isso",
    "interpreta isso",
    "interprete isso",
)

PROTECTED_VOICE_COMMANDS = {
    "o que tem na tela",
    "resuma a tela",
    "detalha a tela",
    "o que voce acha disso",
    "o que vc acha disso",
    "o que acha disso",
    "o que voce pensa disso",
    "qual sua opiniao sobre isso",
    "qual a sua opiniao sobre isso",
    "voce acha que existem melhores",
    "voce acha que existe melhor",
    "vc acha que existem melhores",
    "acha que existem melhores",
    "tem melhores",
    "tem melhor",
    "me explica melhor esse cenario",
    "me explique melhor esse cenario",
    "explica melhor esse cenario",
    "detalha isso",
    "detalhar isso",
    "interpreta isso",
    "interprete isso",
    "proximos avancos",
    "pedido ao codex",
    "conversa com codex",
    "canal com codex",
    "sugestao do codex",
    "fila do codex",
    "inbox do codex",
    "codex aplicou",
    "codex implementou",
    "codex falhou",
    "plano de auto evolucao",
    "quantos passos faltam",
    "status da auto evolucao",
    "progresso da auto evolucao",
    "listar passos faltantes",
    "mostrar passos faltantes",
    "passos restantes",
    "proximo passo da auto evolucao",
    "mostrar gargalos",
    "atualizar gargalos",
    "propostas de patch",
    "mostrar propostas de patch",
    "acoes candidatas",
    "mostrar acoes candidatas",
    "aprovar proximo avanco",
    "aprovar proximo avanço",
    "aprovar e preparar proximo avanco",
    "aprovar e preparar proximo avanço",
    "pacote de execucao",
    "mostrar pacote de execucao",
    "handoff",
    "mostrar handoff",
    "status da aplicacao",
    "aplicacao do handoff",
    "handoff aplicado",
    "handoff falhou",
    "handoff validado",
    "aplicacao validada",
    "como validar handoff",
    "validar handoff",
    "checklist do handoff",
    "plano de nova tentativa",
    "replanejar handoff",
    "contexto operacional",
    "apps recentes",
    "aplicativos recentes",
    "sites recentes",
    "topicos recentes",
    "analisar imagem da tela",
    "analisar imagem no navegador",
    "interpretar imagem da tela",
    "descrever imagem da tela",
    "identificar elementos",
    "analisa grafico",
    "analisar grafico",
    "interpreta grafico",
    "interpretar grafico",
    "ler grafico",
    "inspecionar codigo selecionado",
    "analisar codigo selecionado",
    "inspecionar selecionado",
    "diretrizes",
    "diretrizes do axel",
    "modo investimentos",
    "analisar investimentos",
    "resumo financeiro",
    "resumo da carteira",
    "analisar carteira",
    "preparar nova tentativa",
    "preparar nova tentativa para codex",
    "preparar pedido de implementacao",
    "gerar pedido de implementacao",
    "pedido de implementacao ao codex",
    "mensagem para codex implementar",
    "mostrar pedido de implementacao",
    "enviar pedido de implementacao",
    "enviar pedido de implementacao ao codex",
    "colocar pedido na fila do codex",
    "mandar pedido para o codex",
    "enviar nova tentativa ao codex",
    "mandar nova tentativa para o codex",
    "proposta atual",
    "aprovar proposta atual",
    "rejeitar proposta atual",
    "status da verificacao",
    "verificar melhoria",
    "melhoria funcionou",
    "melhoria falhou",
    "replanejar melhoria",
}

UNCLEAR_RESPONSES = {
    "Nao entendi.",
    "Pode repetir?",
    "Nao identifiquei o comando.",
}

UNCLEAR_RESPONSE_FRAGMENTS = (
    "nao entendi",
    "nao consegui entender",
    "esse comando nao ficou claro",
    "pode repetir",
    "qual alvo",
    "qual site",
    "qual pesquisa",
)


def is_unclear_response(raw_action: object) -> bool:
    if not isinstance(raw_action, dict) or raw_action.get("intent") != "respond":
        return False

    response = normalize_text(str(raw_action.get("response", "")))
    return any(fragment in response for fragment in UNCLEAR_RESPONSE_FRAGMENTS)


def maybe_normalize_voice_command(
    user_input: str,
    voice_mode: bool,
    apply_correction: ApplyVoiceCorrection,
    route_command: RouteCommand,
) -> str:
    if not voice_mode:
        return user_input

    learned = apply_correction(user_input)
    if learned:
        return learned

    normalized_input = normalize_text(user_input)
    if normalized_input.startswith(CONTEXTUAL_FOLLOWUP_PREFIXES):
        return user_input

    normalized_candidate = normalize_voice_command(user_input)
    if (
        normalized_candidate in PROTECTED_VOICE_COMMANDS
        or normalized_candidate.startswith("pesquisar")
        or normalized_candidate.startswith(("codex aplicou", "codex implementou", "codex falhou"))
    ):
        return normalized_candidate

    raw_action = route_command(user_input)
    if raw_action.get("intent") != "respond":
        return user_input

    if raw_action.get("response") not in UNCLEAR_RESPONSES:
        return user_input

    return normalized_candidate or user_input


def clean_probable_query(text: str) -> str:
    cleaned = normalize_text(text).strip(" .,:;-")
    replacements = {
        "nutbook": "notebook",
        "notbook": "notebook",
        "notebooke": "notebook",
    }
    return replacements.get(cleaned, cleaned)


def maybe_suggest_probable_command(user_input: str):
    text = normalize_text(user_input).strip(" .")
    if not text:
        return None

    if "mercado livre" in text or "mercadolivre" in text or "mercado de" in text:
        query = re.sub(r"\b(?:mercado\s+livre|mercadolivre|mercado\s+de)\b", " ", text)
        query = re.sub(
            r"\b(?:comandos?|comando|de|para|pra|pode|poderia|consegue|conseguiria|"
            r"pesquisa|pesquise|pesquisar|esquisa|esquise|esquisar|quisa|quise|quisar|"
            r"procure|procurar|buscar|busque|no|na|em|dentro|do|da)\b",
            " ",
            query,
        )
        query = re.sub(r"\s+", " ", query).strip(" .")
        query = clean_probable_query(query)
        if query:
            return {
                "question": f"Você quis pesquisar {query} no Mercado Livre?",
                "action": {
                    "intent": "browser_search_site",
                    "target": {
                        "query": query,
                        "site": "https://www.mercadolivre.com.br",
                    },
                },
            }

    if "youtube" in text or "you tube" in text:
        query = re.sub(r"\b(?:youtube|you\s+tube)\b", " ", text)
        query = re.sub(
            r"\b(?:comandos?|comando|de|para|pra|pode|poderia|consegue|conseguiria|"
            r"pesquisa|pesquise|pesquisar|esquisa|esquise|esquisar|quisa|quise|quisar|"
            r"procure|procurar|buscar|busque|procura|no|na|em|dentro|do|da)\b",
            " ",
            query,
        )
        query = re.sub(r"\s+", " ", query).strip(" .")
        if query and query not in {"que", "o que", "isso"}:
            return {
                "question": f"Você quis pesquisar {query} no YouTube?",
                "action": {
                    "intent": "browser_search_site",
                    "target": {
                        "query": query,
                        "site": "https://www.youtube.com",
                    },
                },
            }

    if "spotify" in text and "filho" in text and any(token in text for token in {"meu", "mil"}):
        return {
            "question": "Você quis tocar Filho Meu no Spotify?",
            "action": {
                "intent": "browser_search_music",
                "target": {"service": "spotify", "query": "filho meu"},
            },
        }

    music_vibes = {
        "alegre": "alegre",
        "agre": "alegre",
        "calmo": "calmo",
        "calma": "calmo",
        "rock": "rock",
        "roque": "rock",
        "classico": "classico",
        "classica": "classico",
        "jazz": "jazz",
        "gospel": "gospel",
        "triste": "triste",
        "foco": "foco",
        "treino": "treino",
    }
    for token, vibe in music_vibes.items():
        if token in text and any(
            word in text for word in {"musica", "musicas", "tocar", "toque", "toca", "spotify", "algo"}
        ):
            label = "clássica" if vibe == "classico" else vibe
            return {
                "question": f"Você quis iniciar uma sessão {label}?",
                "action": {
                    "intent": "browser_music_session",
                    "target": {"service": "spotify", "vibe": vibe},
                },
            }

    return None


def command_correction_text(command) -> str:
    action = getattr(command, "action", "")
    params = getattr(command, "params", {}) or {}

    if action == "browser_search_site":
        query = str(params.get("query", "")).strip()
        site = str(params.get("site", "")).strip().lower()
        if not query:
            return ""
        if "mercadolivre.com.br" in site:
            return f"pesquisar {query} no Mercado Livre"
        if "magazineluiza.com.br" in site:
            return f"pesquisar {query} no Magazine Luiza"
        if "youtube.com" in site:
            return f"pesquisar {query} no YouTube"
        return f"pesquisar {query}"

    if action == "browser_search_music":
        query = str(params.get("query", "")).strip()
        service = str(params.get("service", "Spotify")).strip() or "Spotify"
        return f"tocar {query} no {service}" if query else ""

    if action == "browser_music_session":
        vibe = str(params.get("vibe", "")).strip()
        if not vibe:
            return ""
        label = "clássica" if vibe == "classico" else vibe
        return f"tocar música {label}"

    if action == "browser_surprise_music":
        return "me surpreenda"

    if action == "open_app":
        target = str(params.get("target", "")).strip()
        return f"abrir {target}" if target else ""

    return ""
