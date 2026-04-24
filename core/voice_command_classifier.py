import difflib

from memory.aliases import load_app_aliases, load_site_aliases, load_smart_app_aliases
from core.router import normalize_text


APP_TARGETS = [
    "chrome",
    "google chrome",
    "vscode",
    "code",
    "spotify",
    "whatsapp",
    "zap",
    "whats app",
    "watsap",
    "uatsap",
    "estaga",
    "estag",
    "bloco de notas",
    "notas",
    "powershell",
    "edge",
    "explorador de arquivos",
]

SITE_TARGETS = [
    "youtube",
    "google",
    "gmail",
    "chatgpt",
]

BASE_COMMANDS = {
    "nova aba": "nova aba",
    "abrir nova aba": "nova aba",
    "abre nova aba": "nova aba",
    "fechar aba": "fechar aba",
    "fecha aba": "fechar aba",
    "proxima aba": "proxima aba",
    "aba anterior": "aba anterior",
    "de novo": "de novo",
    "maximiza": "maximiza",
    "maximizar": "maximiza",
    "minimiza": "minimiza",
    "minimizar": "minimiza",
    "restaura": "restaura",
    "restaurar": "restaura",
    "foca": "foca",
    "focar": "foca",
    "fecha": "fecha",
    "fechar": "fecha",
    "pausa": "pausa",
    "pausar": "pausa",
    "continua": "pausa",
    "continuar": "pausa",
    "pausa musica": "pausa musica",
    "pausa video": "pausa video",
    "proxima musica": "proxima musica",
    "proximo video": "proximo video",
    "musica anterior": "musica anterior",
    "video anterior": "video anterior",
    "aumenta volume": "aumenta volume",
    "abaixa volume": "abaixa volume",
    "diminui volume": "abaixa volume",
    "mudo": "mudo",
    "mutar": "mudo",
    "rolar para baixo": "rolar para baixo",
    "role para baixo": "rolar para baixo",
    "olhe para baixo": "rolar para baixo",
    "ola para baixo": "rolar para baixo",
    "desce a tela": "rolar para baixo",
    "descer a tela": "rolar para baixo",
    "desuna a tela": "rolar para baixo",
    "desum na tela": "rolar para baixo",
    "desuna na tela": "rolar para baixo",
    "rolar tela para baixo": "rolar para baixo",
    "rolar mais": "rolar para baixo",
    "descer mais": "rolar para baixo",
    "descer um pouco": "descer um pouco",
    "desce um pouco": "descer um pouco",
    "rolar para cima": "rolar para cima",
    "role para cima": "rolar para cima",
    "olhe para cima": "rolar para cima",
    "ola para cima": "rolar para cima",
    "sobe a tela": "rolar para cima",
    "subir a tela": "rolar para cima",
    "rolar tela para cima": "rolar para cima",
    "subir mais": "rolar para cima",
    "subir um pouco": "subir um pouco",
    "sobe um pouco": "subir um pouco",
    "fim da pagina": "fim da pagina",
    "final da pagina": "fim da pagina",
    "fim da tela": "fim da pagina",
    "final da tela": "fim da pagina",
    "ate o final": "fim da pagina",
    "rolar ate o final": "fim da pagina",
    "rolar tela ate o final": "fim da pagina",
    "topo da pagina": "topo da pagina",
    "inicio da pagina": "topo da pagina",
    "zoom": "zoom",
    "aumentar zoom": "aumentar zoom",
    "aumenta zoom": "aumentar zoom",
    "ampliar tela": "aumentar zoom",
    "umpliar a tela": "aumentar zoom",
    "umpliar a teoria": "aumentar zoom",
    "diminuir zoom": "diminuir zoom",
    "diminui zoom": "diminuir zoom",
    "menos zoom": "diminuir zoom",
    "ativar bluetooth": "ativar bluetooth",
    "ligar bluetooth": "ativar bluetooth",
    "desativar bluetooth": "desativar bluetooth",
    "desligar bluetooth": "desativar bluetooth",
    "abrir bluetooth": "abrir bluetooth",
    "configuracoes bluetooth": "abrir bluetooth",
    "status bluetooth": "status bluetooth",
    "diagnosticar spotify": "diagnosticar spotify",
    "diagnostica spotify": "diagnosticar spotify",
    "diagnostica e spotify": "diagnosticar spotify",
    "diagnosticar e spotify": "diagnosticar spotify",
    "diagnosticare spotify": "diagnosticar spotify",
    "jagnoche car spotify": "diagnosticar spotify",
    "debug spotify": "diagnosticar spotify",
    "pesquisa": "pesquisar",
    "pesquisa notebook": "pesquisar notebook",
    "procura": "pesquisar",
    "procurar": "pesquisar",
    "buscar": "pesquisar",
    "busca": "pesquisar",
    "resuma a tela": "resuma a tela",
    "resume a tela": "resuma a tela",
    "resumir tela": "resuma a tela",
    "resuma o conteudo": "resuma a tela",
    "resuma o conteudo da tela": "resuma a tela",
    "resumo do conteudo da tela": "resuma a tela",
    "resumo da tela": "resuma a tela",
    "detalha a tela": "detalha a tela",
    "detalhar a tela": "detalha a tela",
    "detalha": "detalha a tela",
    "conteudo principal": "detalha a tela",
    "conteudo principal da tela": "detalha a tela",
    "o que importa na tela": "detalha a tela",
    "o que tem na tela": "o que tem na tela",
    "que tem na tela": "o que tem na tela",
    "e que tem na tela": "o que tem na tela",
    "o que esta na tela": "o que tem na tela",
    "o que ta na tela": "o que tem na tela",
    "o que esta ai na tela": "o que tem na tela",
    "o que ta ai na tela": "o que tem na tela",
    "o que aparece na tela": "o que aparece na tela",
    "o que aparece na imagem": "o que aparece na imagem",
    "o que aparece nessa imagem": "o que aparece nessa imagem",
    "o que tem na imagem": "o que tem na imagem",
    "o que tem nessa imagem": "o que tem nessa imagem",
    "analisar imagem": "analisar imagem da tela",
    "analisa imagem": "analisar imagem da tela",
    "analise imagem": "analisar imagem da tela",
    "interpretar imagem": "interpretar imagem da tela",
    "interpreta imagem": "interpretar imagem da tela",
    "interprete imagem": "interpretar imagem da tela",
    "descrever imagem": "descrever imagem da tela",
    "descreve imagem": "descrever imagem da tela",
    "descreva imagem": "descrever imagem da tela",
    "identificar elementos": "identificar elementos",
    "identifica elementos": "identificar elementos",
    "identifique elementos": "identificar elementos",
    "descrever cena": "descrever cena",
    "descreve cena": "descrever cena",
    "descreva cena": "descrever cena",
    "analisar grafico": "analisar imagem da tela",
    "analisa grafico": "analisar imagem da tela",
    "analise grafico": "analisar imagem da tela",
    "interpretar grafico": "analisar imagem da tela",
    "interpreta grafico": "analisar imagem da tela",
    "interprete grafico": "analisar imagem da tela",
    "ler grafico": "analisar imagem da tela",
    "leia grafico": "analisar imagem da tela",
    "status visao": "status da visao",
    "status da visao": "status da visao",
    "modelo visual": "modelo visual",
    "modelo de visao": "status da visao",
    "ultima analise visual": "ultima analise visual",
    "analise visual anterior": "ultima analise visual",
    "o que esta ai": "o que tem na tela",
    "o kit tem na tela": "o que tem na tela",
}

SCREEN_TARGET_HINTS = {
    "tela",
    "pagina",
    "site",
    "janela",
    "github",
    "repositorio",
    "perfil",
    "video",
    "youtube",
    "conteudo",
}

SCREEN_SUMMARY_HINTS = {
    "resuma",
    "resume",
    "resumi",
    "resumir",
    "resumo",
    "resumida",
    "resumido",
}

SCREEN_DETAIL_HINTS = {
    "detalha",
    "detalhar",
    "detalhe",
    "explica",
    "explicar",
    "explique",
    "importa",
    "importante",
    "principal",
    "conteudo",
}

SCREEN_DESCRIBE_HINTS = {
    "oq",
    "oque",
    "que",
    "mostra",
    "mostrar",
    "aparece",
    "tem",
    "ve",
    "ver",
    "vendo",
}


def _build_command_candidates() -> dict[str, str]:
    candidates = dict(BASE_COMMANDS)
    app_targets = list(APP_TARGETS)
    site_targets = list(SITE_TARGETS)

    for alias, target in load_app_aliases().items():
        app_targets.append(alias)
        app_targets.append(target)

    for alias in load_smart_app_aliases().keys():
        app_targets.append(alias)

    for alias in load_site_aliases().keys():
        site_targets.append(alias)

    app_targets = sorted(set(normalize_text(target) for target in app_targets if target))
    site_targets = sorted(set(normalize_text(target) for target in site_targets if target))

    for target in app_targets + site_targets:
        candidates[f"abre {target}"] = f"abre {target}"
        candidates[f"abre o {target}"] = f"abre {target}"
        candidates[f"abrir {target}"] = f"abre {target}"
        candidates[f"abrir o {target}"] = f"abre {target}"

    for target in app_targets:
        candidates[f"fecha {target}"] = f"fecha {target}"
        candidates[f"fecha o {target}"] = f"fecha {target}"
        candidates[f"fechar {target}"] = f"fecha {target}"
        candidates[f"fechar o {target}"] = f"fecha {target}"
        candidates[f"foca {target}"] = f"foca {target}"
        candidates[f"foca no {target}"] = f"foca {target}"
        candidates[f"maximiza {target}"] = f"maximiza {target}"
        candidates[f"maximizar {target}"] = f"maximiza {target}"
        candidates[f"minimiza {target}"] = f"minimiza {target}"
        candidates[f"minimizar {target}"] = f"minimiza {target}"
        candidates[f"restaura {target}"] = f"restaura {target}"
        candidates[f"restaurar {target}"] = f"restaura {target}"

    return candidates


UNSAFE_SHORT_INPUTS = {"oi", "ola", "opa", "boa", "um beijo", "beijo"}


def _similarity(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, left, right).ratio()


def _threshold_for(text: str, canonical: str) -> float:
    word_count = len(text.split())

    if canonical == "nova aba" and text.startswith(("ab", "abr")):
        return 0.66

    if canonical in {"minimiza", "maximiza"} and word_count <= 2:
        return 0.70

    return 0.82 if word_count <= 2 else 0.76


def _token_similarity(token: str, candidates: set[str]) -> float:
    if not token:
        return 0.0
    return max((difflib.SequenceMatcher(None, token, candidate).ratio() for candidate in candidates), default=0.0)


def _contains_like(tokens: list[str], candidates: set[str], threshold: float) -> bool:
    return any(_token_similarity(token, candidates) >= threshold for token in tokens)


def _screen_target_score(tokens: list[str]) -> float:
    return max((_token_similarity(token, SCREEN_TARGET_HINTS) for token in tokens), default=0.0)


def _normalize_search_intent(text: str) -> str | None:
    prefixes = ("pesquisa ", "procura ", "procurar ", "buscar ", "busca ")
    for prefix in prefixes:
        if text.startswith(prefix):
            remainder = text[len(prefix):].strip()
            return f"pesquisar {remainder}".strip()

    if text in {"pesquisa", "procura", "procurar", "buscar", "busca"}:
        return "pesquisar"

    return None


def _normalize_screen_intent(text: str) -> str | None:
    tokens = [token for token in text.split() if token]
    if not tokens:
        return None

    target_score = _screen_target_score(tokens)

    if _contains_like(tokens, SCREEN_SUMMARY_HINTS, 0.70):
        if target_score >= 0.56 or len(tokens) <= 3:
            return "resuma a tela"

    if _contains_like(tokens, SCREEN_DETAIL_HINTS, 0.72):
        if target_score >= 0.56 or len(tokens) <= 2:
            return "detalha a tela"

    describe_target = target_score >= 0.56
    describe_prompt = _contains_like(tokens, SCREEN_DESCRIBE_HINTS, 0.74)
    if describe_target and describe_prompt:
        return "o que tem na tela"

    return None


def normalize_voice_command(user_input: str) -> str:
    text = normalize_text(user_input)

    if not text or text in UNSAFE_SHORT_INPUTS:
        return user_input

    visual_intents = {
        "o que aparece na tela": "o que aparece na tela",
        "o que aparece na imagem": "o que aparece na imagem",
        "o que aparece nessa imagem": "o que aparece nessa imagem",
        "o que tem na imagem": "o que tem na imagem",
        "o que tem nessa imagem": "o que tem nessa imagem",
        "analisar imagem": "analisar imagem da tela",
        "analisa imagem": "analisar imagem da tela",
        "analise imagem": "analisar imagem da tela",
        "interpretar imagem": "interpretar imagem da tela",
        "interpreta imagem": "interpretar imagem da tela",
        "interprete imagem": "interpretar imagem da tela",
        "descrever imagem": "descrever imagem da tela",
        "descreve imagem": "descrever imagem da tela",
        "descreva imagem": "descrever imagem da tela",
        "identificar elementos": "identificar elementos",
        "identifica elementos": "identificar elementos",
        "identifique elementos": "identificar elementos",
        "descrever cena": "descrever cena",
        "descreve cena": "descrever cena",
        "descreva cena": "descrever cena",
        "analisar grafico": "analisar imagem da tela",
        "analisa grafico": "analisar imagem da tela",
        "analise grafico": "analisar imagem da tela",
        "interpretar grafico": "analisar imagem da tela",
        "interpreta grafico": "analisar imagem da tela",
        "interprete grafico": "analisar imagem da tela",
        "ler grafico": "analisar imagem da tela",
        "leia grafico": "analisar imagem da tela",
    }
    if text in visual_intents:
        return visual_intents[text]

    search_intent = _normalize_search_intent(text)
    if search_intent:
        return search_intent

    screen_intent = _normalize_screen_intent(text)
    if screen_intent:
        return screen_intent

    command_candidates = _build_command_candidates()

    if text in command_candidates:
        return command_candidates[text]

    best_key = None
    best_score = 0.0

    for candidate in command_candidates:
        score = _similarity(text, candidate)
        if score > best_score:
            best_score = score
            best_key = candidate

    if not best_key:
        return user_input

    canonical = command_candidates[best_key]
    threshold = _threshold_for(text, canonical)

    if best_score >= threshold:
        return canonical

    return user_input
