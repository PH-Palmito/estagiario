from __future__ import annotations

import difflib
import re

from core.router_utils import normalize_text
from memory.aliases import load_app_aliases, load_site_aliases, load_smart_app_aliases

KNOWN_APPS = {
    "bloco de notas": "bloco de notas",
    "bloco notas": "bloco de notas",
    "notas": "bloco de notas",
    "notepad": "bloco de notas",
    "calculadora": "calculadora",
    "calc": "calculadora",
    "spotify": "spotify",
    "whatsapp": "whatsapp",
    "zap": "whatsapp",
    "whats": "whatsapp",
    "whats app": "whatsapp",
    "watsap": "whatsapp",
    "uatsap": "whatsapp",
    "chrome": "chrome",
    "google chrome": "chrome",
    "vs code": "code",
    "vscode": "code",
    "codigo": "code",
    "visual studio code": "code",
    "explorador de arquivos": "explorer",
    "explorer": "explorer",
    "prompt de comando": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "power shell": "powershell",
    "power": "powershell",
    "pwsh": "powershell",
    "edge": "edge",
    "microsoft edge": "edge",
}

KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chat.openai.com",
    "investidor 10": "https://investidor10.com.br",
    "investidor10": "https://investidor10.com.br",
    "mercado livre": "https://www.mercadolivre.com.br",
    "mercadolivre": "https://www.mercadolivre.com.br",
    "mercado de": "https://www.mercadolivre.com.br",
    "magalu": "https://www.magazineluiza.com.br",
    "magazine luiza": "https://www.magazineluiza.com.br",
    "magazinha luisa": "https://www.magazineluiza.com.br",
    "magazinha luiza": "https://www.magazineluiza.com.br",
}

TARGET_CORRECTIONS = {
    "git hub": "github",
    "gui hub": "github",
    "guithub": "github",
    "github desktop": "github",
    "and run 2": "android studio",
    "androm studio": "android studio",
    "android estudar": "android studio",
    "android estudio": "android studio",
}

OPEN_PREFIXES = (
    "abra ",
    "abre ",
    "abrir ",
    "abri ",
    "abriu ",
    "abrei ",
    "abre ai ",
    "abre ae ",
    "inicie ",
    "iniciar ",
    "abre o ",
    "abre a ",
    "abre os ",
    "abre as ",
)

CLOSE_PREFIXES = (
    "feche ",
    "fechar ",
    "fecha ",
    "encerre ",
    "encerrar ",
    "termine ",
    "terminar ",
)

FOCUS_PREFIXES = (
    "troca pro ",
    "troca para ",
    "troque pro ",
    "troque para ",
    "vai pro ",
    "vai para ",
    "volta pro ",
    "volta para ",
    "foca no ",
    "foca na ",
    "foca ",
    "foca o ",
    "foca a ",
    "foca em ",
    "focar no ",
    "focar na ",
    "focar ",
    "focar o ",
    "focar a ",
    "focar em ",
)

MINIMIZE_PREFIXES = (
    "minimiza ",
    "minimizar ",
    "minimize ",
    "minimiza o ",
    "minimiza a ",
    "minimizar o ",
    "minimizar a ",
    "minimize o ",
    "minimize a ",
)

MAXIMIZE_PREFIXES = (
    "maximiza ",
    "maximizar ",
    "maximize ",
    "maximiza o ",
    "maximiza a ",
    "maximizar o ",
    "maximizar a ",
    "maximize o ",
    "maximize a ",
)

RESTORE_PREFIXES = (
    "restaura ",
    "restaurar ",
    "restaure ",
    "restaura o ",
    "restaura a ",
    "restaurar o ",
    "restaurar a ",
    "restaure o ",
    "restaure a ",
)

CONTEXT_FOCUS_PATTERNS = {
    "foca",
    "focar",
    "troca",
    "troque",
    "vai",
    "volta pra janela",
    "volta para janela",
}

CONTEXT_MINIMIZE_PATTERNS = {
    "imiza",
    "imizar",
    "minimiza",
    "minimizar",
    "minimize",
    "minibiza",
    "minibizar",
}

CONTEXT_MAXIMIZE_PATTERNS = {
    "machina",
    "maquina",
    "maxima",
    "maxina",
    "maximiza",
    "maximizar",
    "maximize",
}

CONTEXT_RESTORE_PATTERNS = {
    "restaura",
    "restaurar",
    "restaure",
}


def _app_options():
    options = dict(KNOWN_APPS)
    options.update({normalize_text(k): v for k, v in load_app_aliases().items()})
    return options


def _site_options():
    options = dict(KNOWN_SITES)
    options.update({normalize_text(k): v for k, v in load_site_aliases().items()})
    return options


def _smart_app_options():
    options = {}
    for alias, value in load_smart_app_aliases().items():
        canonical = value.get("_key") if isinstance(value, dict) else None
        options[normalize_text(alias)] = canonical or normalize_text(alias)
    return options


def _extract_after_prefix(text: str, prefixes):
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return None


def _extract_after_fuzzy_prefix(text: str, prefixes, cutoff: float = 0.74):
    extracted = _extract_after_prefix(text, prefixes)
    if extracted is not None:
        return extracted

    words = text.split()
    if not words:
        return None

    for prefix in prefixes:
        prefix_words = prefix.strip().split()
        if len(words) < len(prefix_words):
            continue

        candidate = " ".join(words[:len(prefix_words)])
        if difflib.SequenceMatcher(None, candidate, prefix.strip()).ratio() >= cutoff:
            return " ".join(words[len(prefix_words):]).strip()

    return None


def _strip_leading_articles(text: str) -> str:
    words = text.split()
    while words and words[0] in {"o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos", "das", "no", "na", "nos", "nas"}:
        words = words[1:]
    return " ".join(words)


def _normalize_target_phrase(text: str) -> str:
    target = _strip_leading_articles(normalize_text(text)).strip(" .")
    return TARGET_CORRECTIONS.get(target, target)


def _best_fuzzy_match(text: str, options: dict, cutoff: float = 0.72):
    if not text:
        return None

    normalized_options = {normalize_text(key): value for key, value in options.items()}

    if text in normalized_options:
        return normalized_options[text]

    matches = difflib.get_close_matches(text, normalized_options.keys(), n=1, cutoff=cutoff)
    if matches:
        return normalized_options[matches[0]]

    words = text.split()
    for size in range(len(words), 0, -1):
        for start in range(0, len(words) - size + 1):
            chunk = " ".join(words[start:start + size])
            if chunk in normalized_options:
                return normalized_options[chunk]

            matches = difflib.get_close_matches(chunk, normalized_options.keys(), n=1, cutoff=cutoff)
            if matches:
                return normalized_options[matches[0]]

    return None


def _match_app_target(text: str):
    apps = _app_options()
    target = _normalize_target_phrase(text)
    app = _best_fuzzy_match(target, apps, cutoff=0.68)
    if app:
        return app

    for alias, canonical in apps.items():
        alias_normalized = normalize_text(alias)
        if alias_normalized in target:
            return canonical

    return None


def _match_smart_app_target(text: str):
    target = _normalize_target_phrase(text)
    return _best_fuzzy_match(target, _smart_app_options(), cutoff=0.66)


def _looks_like_window_request(text: str) -> bool:
    normalized = normalize_text(text)
    window_prefix_groups = (
        FOCUS_PREFIXES,
        MINIMIZE_PREFIXES,
        MAXIMIZE_PREFIXES,
        RESTORE_PREFIXES,
    )

    for prefixes in window_prefix_groups:
        if _extract_after_fuzzy_prefix(normalized, prefixes):
            return True

    first_word = normalized.split(" ", 1)[0] if normalized else ""
    if difflib.get_close_matches(
        first_word,
        ["foca", "focar", "troca", "troque", "vai", "volta", "minimiza", "minimizar", "maximize", "maximiza", "maximizar", "restaura", "restaurar"],
        n=1,
        cutoff=0.76,
    ):
        return True

    return False


def detect_open_chatgpt(user_input: str):
    lower = normalize_text(user_input)
    if "chatgpt" in lower and any(x in lower for x in ["abra", "abrir", "abre", "abrei"]):
        return {"intent": "open_chatgpt", "target": None}
    return None


def detect_open_url(user_input: str):
    lower = normalize_text(user_input)
    sites = _site_options()

    direct_url = re.search(r"\b(?:https?://|www\.)\S+", user_input.strip(), flags=re.I)
    if direct_url and any(lower.startswith(prefix.strip()) for prefix in OPEN_PREFIXES):
        url = direct_url.group(0).strip(" .,")
        if url.startswith("www."):
            url = "https://" + url
        return {"intent": "open_url", "target": url}

    if lower.startswith("abra o site "):
        url = user_input[len("abra o site "):].strip()
        if url and not url.startswith("http"):
            url = "https://" + url
        return {"intent": "open_url", "target": url}

    if lower.startswith(("pesquisa ", "pesquise ", "pesquisar ")):
        query = re.sub(r"^(pesquisa|pesquise|pesquisar)\s+", "", user_input, flags=re.IGNORECASE).strip()
        if query:
            return {"intent": "google_search", "target": query}

    open_target = _extract_after_prefix(lower, OPEN_PREFIXES)
    if open_target:
        open_target = _strip_leading_articles(open_target)
        if open_target.startswith(("http://", "https://", "www.")):
            url = open_target if not open_target.startswith("www.") else "https://" + open_target
            return {"intent": "open_url", "target": url}
        if _best_fuzzy_match(open_target, _app_options(), cutoff=0.68):
            return None
        site = _best_fuzzy_match(open_target, sites, cutoff=0.7)
        if site:
            return {"intent": "open_url", "target": site}

    if len(lower.split()) <= 3:
        site = _best_fuzzy_match(lower, sites, cutoff=0.75)
        if site:
            return {"intent": "open_url", "target": site}

    return None


def detect_window_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in CONTEXT_FOCUS_PATTERNS:
        return {"intent": "focus_app", "target": None}

    if lower in CONTEXT_MINIMIZE_PATTERNS:
        return {"intent": "minimize_app", "target": None}

    if lower in CONTEXT_MAXIMIZE_PATTERNS or "sim bizarro" in lower:
        return {"intent": "maximize_app", "target": None}

    if lower in CONTEXT_RESTORE_PATTERNS:
        return {"intent": "restore_app", "target": None}

    for prefixes, intent, missing_response in (
        (FOCUS_PREFIXES, "focus_app", "Nao identifiquei qual janela focar."),
        (MAXIMIZE_PREFIXES, "maximize_app", "Nao identifiquei qual janela maximizar."),
        (MINIMIZE_PREFIXES, "minimize_app", "Nao identifiquei qual janela minimizar."),
        (RESTORE_PREFIXES, "restore_app", "Nao identifiquei qual janela restaurar."),
    ):
        target = _extract_after_prefix(lower, prefixes)
        if target:
            target = _normalize_target_phrase(target)
            app = _match_app_target(target) or _match_smart_app_target(target)
            if app:
                return {"intent": intent, "target": app}
            return {"intent": "respond", "target": None, "response": missing_response}

    for prefixes, intent, missing_response in (
        (FOCUS_PREFIXES, "focus_app", "Nao identifiquei qual janela focar."),
        (MAXIMIZE_PREFIXES, "maximize_app", "Nao identifiquei qual janela maximizar."),
        (MINIMIZE_PREFIXES, "minimize_app", "Nao identifiquei qual janela minimizar."),
        (RESTORE_PREFIXES, "restore_app", "Nao identifiquei qual janela restaurar."),
    ):
        target = _extract_after_fuzzy_prefix(lower, prefixes)
        if target:
            target = _normalize_target_phrase(target)
            app = _match_app_target(target) or _match_smart_app_target(target)
            if app:
                return {"intent": intent, "target": app}
            return {"intent": "respond", "target": None, "response": missing_response}

    return None


def detect_close_app(user_input: str):
    lower = normalize_text(user_input)
    close_target = _extract_after_prefix(lower, CLOSE_PREFIXES)
    sites = _site_options()

    if not close_target:
        return None

    close_target = _normalize_target_phrase(close_target)

    if _best_fuzzy_match(close_target, sites, cutoff=0.72):
        return {"intent": "browser_close_tab", "target": None}

    app = _match_app_target(close_target)
    if app:
        return {"intent": "close_app", "target": app}

    smart_app = _match_smart_app_target(close_target)
    if smart_app:
        return {"intent": "smart_close_app", "target": smart_app}

    return {"intent": "respond", "target": None, "response": "Nao identifiquei qual app fechar."}


def detect_open_app(user_input: str):
    lower = normalize_text(user_input)
    open_target = _extract_after_prefix(lower, OPEN_PREFIXES)
    sites = _site_options()

    if _looks_like_window_request(lower):
        return None

    if open_target:
        open_target = _normalize_target_phrase(open_target)

        if _best_fuzzy_match(open_target, sites, cutoff=0.7):
            return None

        app = _match_app_target(open_target)
        if app:
            return {"intent": "open_app", "target": app}

        smart_app = _match_smart_app_target(open_target)
        if smart_app:
            return {"intent": "smart_open", "target": smart_app}

        return {"intent": "smart_open", "target": open_target}

    if len(lower.split()) <= 3:
        app = _match_app_target(lower)
        if app:
            return {"intent": "open_app", "target": app}
        smart_app = _match_smart_app_target(lower)
        if smart_app:
            return {"intent": "smart_open", "target": smart_app}

    return None


APP_DETECTORS = [
    detect_open_chatgpt,
    detect_close_app,
    detect_window_command,
    detect_open_url,
    detect_open_app,
]
