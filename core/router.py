import difflib
import re
import unicodedata

from memory.aliases import load_app_aliases, load_site_aliases
from memory.macros import delete_macro, get_macro, list_macros
from memory.profile import get_value, set_value
from tools.math_tools import calculate_basic_expression, calculate_percentage


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
}

OPEN_PREFIXES = (
    "abra ",
    "abre ",
    "abrir ",
    "abri ",
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

CHATTER_PATTERNS = {
    "boa": "Estou ouvindo.",
    "opa": "Estou aqui.",
    "e ai": "Fala comigo.",
    "oi": "Ola.",
    "ola": "Ola.",
    "posso falar": "Pode falar.",
    "ta ouvindo": "Estou ouvindo sim.",
    "esta ouvindo": "Estou ouvindo sim.",
}

REPEAT_PATTERNS = {
    "de novo",
    "denovo",
    "mais uma",
    "outra vez",
    "repete",
    "repita",
}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_text(text: str) -> str:
    text = strip_accents(text.strip().lower())
    text = re.sub(r"[^\w\s:/.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _app_options():
    options = dict(KNOWN_APPS)
    options.update({normalize_text(k): v for k, v in load_app_aliases().items()})
    return options


def _site_options():
    options = dict(KNOWN_SITES)
    options.update({normalize_text(k): v for k, v in load_site_aliases().items()})
    return options


def _extract_after_prefix(text: str, prefixes):
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return None


def _strip_leading_articles(text: str) -> str:
    words = text.split()
    while words and words[0] in {"o", "a", "os", "as", "um", "uma"}:
        words = words[1:]
    return " ".join(words)


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


def _looks_like_new_tab(text: str) -> bool:
    text = normalize_text(text)

    if not text:
        return False

    direct_phrases = {
        "nova aba",
        "nova ab",
        "nova abra",
        "novo aba",
        "nova",
        "novado",
        "noza",
        "noza abra",
        "abrir nova",
        "abre nova",
    }

    if text in direct_phrases:
        return True

    if difflib.SequenceMatcher(None, text, "nova aba").ratio() >= 0.45:
        return True

    words = text.split()
    if any(word.startswith(("nov", "noz")) for word in words):
        return True

    if "aba" in text or "ab" == text:
        return True

    return False


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
    if text in CHATTER_PATTERNS:
        return {"intent": "respond", "target": None, "response": CHATTER_PATTERNS[text]}
    return None


def detect_math(user_input: str):
    result = calculate_percentage(user_input)
    if result:
        return {"intent": "respond", "target": None, "response": result}

    result = calculate_basic_expression(user_input)
    if result:
        return {"intent": "respond", "target": None, "response": result}

    return None


def detect_browser_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {"fecha", "fechar", "fecha ai", "fecha ae"}:
        return {"intent": "browser_close_tab", "target": None}

    if lower in {"volta", "voltar", "aba anterior", "anterior"}:
        return {"intent": "browser_prev_tab", "target": None}

    if lower in {"proxima", "proxima aba", "aba seguinte", "seguinte"} or "proxima aba" in lower:
        return {"intent": "browser_next_tab", "target": None}

    if lower in {"mais uma", "outra aba"}:
        return {"intent": "browser_new_tab", "target": None}

    if lower in {"proxima aba", "aba seguinte"} or "proxima aba" in lower:
        return {"intent": "browser_next_tab", "target": None}

    if lower in {"aba anterior", "voltar aba"} or "aba anterior" in lower:
        return {"intent": "browser_prev_tab", "target": None}

    if any(phrase in lower for phrase in {"nova aba", "nova ab", "nova abra", "novo aba", "abrir nova", "abre nova"}):
        return {"intent": "browser_new_tab", "target": None}

    open_target = _extract_after_prefix(lower, OPEN_PREFIXES)
    if open_target:
        candidate = _strip_leading_articles(open_target)
        if _looks_like_new_tab(candidate):
            return {"intent": "browser_new_tab", "target": None}

    if lower in {"fechar aba", "fecha aba", "feche a aba", "fecha"} or "fechar aba" in lower:
        return {"intent": "browser_close_tab", "target": None}

    if lower.startswith("pesquisar por ") or lower.startswith("pesquise por "):
        query = re.sub(r"^(pesquisar|pesquise) por ", "", lower).strip()
        query = re.sub(r"\s+no navegador$", "", query).strip()
        if query:
            return {"intent": "browser_search", "target": query}

    if lower.startswith("pesquisar ") or lower.startswith("pesquise "):
        query = re.sub(r"^(pesquisar|pesquise) ", "", lower).strip()
        query = re.sub(r"\s+no navegador$", "", query).strip()
        if query:
            return {"intent": "google_search", "target": query}

    return None


def detect_create_file(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["crie um arquivo ", "criar arquivo "]:
        if lower.startswith(prefix):
            name = user_input[len(prefix):].strip()
            if name:
                return {"intent": "create_file", "target": name}
    return None


def detect_write_file(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["escreva no arquivo ", "escreva "]:
        if lower.startswith(prefix) and ":" in user_input:
            left, content = user_input.split(":", 1)
            content = content.strip()
            if not content:
                return None
            name = left[len("escreva no arquivo "):].strip() if prefix == "escreva no arquivo " else None
            return {"intent": "write_file", "target": name if name else None, "content": content}
    return None


def detect_append_file(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["adicione no arquivo ", "adicione "]:
        if lower.startswith(prefix) and ":" in user_input:
            left, content = user_input.split(":", 1)
            content = content.strip()
            if not content:
                return None
            name = left[len("adicione no arquivo "):].strip() if prefix == "adicione no arquivo " else None
            return {"intent": "append_file", "target": name if name else None, "content": content}
    return None


def detect_read_file(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["leia o arquivo ", "leia arquivo ", "leia "]:
        if lower.startswith(prefix):
            name = user_input[len(prefix):].strip()
            return {"intent": "read_file", "target": name if name else None}
    if lower == "leia":
        return {"intent": "read_file", "target": None}
    return None


def detect_delete_file(user_input: str):
    lower = normalize_text(user_input)
    prefixes = [
        "delete o arquivo ", "delete arquivo ", "delete ",
        "apague o arquivo ", "apague arquivo ", "apague ",
        "remova o arquivo ", "remova arquivo ", "remova ",
    ]
    for prefix in prefixes:
        if lower.startswith(prefix):
            name = user_input[len(prefix):].strip()
            return {"intent": "delete_file", "target": name if name else None}
    if lower in {"delete", "apague", "remova"}:
        return {"intent": "delete_file", "target": None}
    return None


def detect_copy_file(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["copie ", "copiar "]:
        if lower.startswith(prefix):
            rest = user_input[len(prefix):].strip()
            if " para " not in rest.lower():
                return None
            idx = rest.lower().find(" para ")
            src = rest[:idx].strip()
            dst = rest[idx + len(" para "):].strip()
            if src and dst:
                return {"intent": "copy_file", "target": {"src": src, "dst": dst}}
    return None


def detect_move_file(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["mova ", "mover "]:
        if lower.startswith(prefix):
            rest = user_input[len(prefix):].strip()
            if " para " not in rest.lower():
                return None
            idx = rest.lower().find(" para ")
            src = rest[:idx].strip()
            dst = rest[idx + len(" para "):].strip()
            if src and dst:
                return {"intent": "move_file", "target": {"src": src, "dst": dst}}
    return None


def detect_rename_file(user_input: str):
    lower = normalize_text(user_input)
    if lower.startswith("renomeie para "):
        new_name = user_input[len("renomeie para "):].strip()
        return {"intent": "rename_file", "target": {"src": None, "new_name": new_name if new_name else None}}
    if lower.startswith("renomeie "):
        rest = user_input[len("renomeie "):].strip()
        if " para " in rest.lower():
            idx = rest.lower().find(" para ")
            src = rest[:idx].strip()
            new_name = rest[idx + len(" para "):].strip()
            return {"intent": "rename_file", "target": {"src": src if src else None, "new_name": new_name if new_name else None}}
    return None


def detect_list_files(user_input: str):
    lower = normalize_text(user_input)
    triggers = ["listar arquivos", "liste os arquivos", "mostrar arquivos", "mostre os arquivos", "ver arquivos"]
    if any(t in lower for t in triggers):
        return {"intent": "list_files", "target": ""}
    return None


def detect_create_folder(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["crie uma pasta ", "crie pasta ", "criar pasta ", "nova pasta "]:
        if lower.startswith(prefix):
            name = user_input[len(prefix):].strip()
            if name:
                return {"intent": "create_folder", "target": name}
    return None


def detect_open_chatgpt(user_input: str):
    lower = normalize_text(user_input)
    if "chatgpt" in lower and any(x in lower for x in ["abra", "abrir", "abre", "abrei"]):
        return {"intent": "open_chatgpt", "target": None}
    return None


def detect_open_url(user_input: str):
    lower = normalize_text(user_input)
    sites = _site_options()

    if lower.startswith("abra o site "):
        url = user_input[len("abra o site "):].strip()
        if url and not url.startswith("http"):
            url = "https://" + url
        return {"intent": "open_url", "target": url}

    if lower.startswith("pesquise "):
        query = user_input[len("pesquise "):].strip()
        if query:
            return {"intent": "google_search", "target": query}

    open_target = _extract_after_prefix(lower, OPEN_PREFIXES)
    if open_target:
        open_target = _strip_leading_articles(open_target)
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


def detect_run_script(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["rode o script ", "rode script ", "execute o script ", "execute script ", "executar script "]:
        if lower.startswith(prefix):
            script = user_input[len(prefix):].strip()
            if script:
                return {"intent": "run_script", "target": script}
    return None


def detect_close_app(user_input: str):
    lower = normalize_text(user_input)
    close_target = _extract_after_prefix(lower, CLOSE_PREFIXES)
    apps = _app_options()
    sites = _site_options()

    if not close_target:
        return None

    close_target = _strip_leading_articles(close_target)

    if _best_fuzzy_match(close_target, sites, cutoff=0.72):
        return {"intent": "browser_close_tab", "target": None}

    app = _best_fuzzy_match(close_target, apps, cutoff=0.68)
    if app:
        return {"intent": "close_app", "target": app}

    for alias, canonical in apps.items():
        alias_normalized = normalize_text(alias)
        if alias_normalized in close_target:
            return {"intent": "close_app", "target": canonical}

    return {"intent": "respond", "target": None, "response": "Nao identifiquei qual app fechar."}


def detect_open_app(user_input: str):
    lower = normalize_text(user_input)
    open_target = _extract_after_prefix(lower, OPEN_PREFIXES)
    apps = _app_options()
    sites = _site_options()

    if open_target:
        open_target = _strip_leading_articles(open_target)

        if _best_fuzzy_match(open_target, sites, cutoff=0.7):
            return None

        app = _best_fuzzy_match(open_target, apps, cutoff=0.68)
        if app:
            return {"intent": "open_app", "target": app}

        for alias, canonical in apps.items():
            alias_normalized = normalize_text(alias)
            if alias_normalized in lower:
                return {"intent": "open_app", "target": canonical}

        return {"intent": "respond", "target": None, "response": "Nao identifiquei o comando."}

    if len(lower.split()) <= 3:
        app = _best_fuzzy_match(lower, apps, cutoff=0.75)
        if app:
            return {"intent": "open_app", "target": app}

    return None


def detect_create_macro_start(user_input: str):
    lower = normalize_text(user_input)
    if lower.startswith("crie macro "):
        name = user_input[len("crie macro "):].strip()
        if name:
            return {"intent": "start_macro", "target": name}
    return None


def detect_run_macro(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["executar ", "execute ", "rode ", "rodar "]:
        if lower.startswith(prefix):
            name = user_input[len(prefix):].strip()
            macro = get_macro(name)
            if macro:
                return {"intent": "run_macro", "target": macro}
    return None


def detect_list_macros(user_input: str):
    lower = normalize_text(user_input)
    if lower in {"listar macros", "liste as macros", "quais macros", "ver macros"}:
        names = list_macros()
        if names:
            return {"intent": "respond", "target": None, "response": "Macros: " + ", ".join(names)}
        return {"intent": "respond", "target": None, "response": "Nenhuma macro salva."}
    return None


def detect_delete_macro(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["delete macro ", "apague macro ", "remova macro "]:
        if lower.startswith(prefix):
            name = user_input[len(prefix):].strip()
            if not name:
                return None
            ok = delete_macro(name)
            if ok:
                return {"intent": "respond", "target": None, "response": f"Macro '{name}' removida."}
            return {"intent": "respond", "target": None, "response": f"Macro '{name}' nao encontrada."}
    return None


def detect_short_unclear_text(user_input: str):
    text = normalize_text(user_input)

    if text in REPEAT_PATTERNS:
        return {"intent": "repeat_last", "target": None}

    if len(text) <= 4:
        return {"intent": "respond", "target": None, "response": "Pode repetir?"}
    return None


def route(user_input: str):
    detectors = [
        detect_create_macro_start,
        detect_run_macro,
        detect_list_macros,
        detect_delete_macro,
        detect_user_name,
        detect_greeting,
        detect_math,
        detect_browser_command,
        detect_create_file,
        detect_write_file,
        detect_append_file,
        detect_read_file,
        detect_delete_file,
        detect_copy_file,
        detect_move_file,
        detect_rename_file,
        detect_list_files,
        detect_create_folder,
        detect_open_chatgpt,
        detect_close_app,
        detect_open_app,
        detect_open_url,
        detect_run_script,
        detect_profile_question,
        detect_short_unclear_text,
    ]

    for detector in detectors:
        result = detector(user_input)
        if result:
            return result

    return {"intent": "respond", "target": None, "response": "Nao entendi."}
