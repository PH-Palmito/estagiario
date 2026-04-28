import difflib
import re
import unicodedata

from memory.aliases import load_app_aliases, load_site_aliases, load_smart_app_aliases
from memory.macros import delete_macro, get_macro, list_macros
from memory.profile import get_value, set_value
from memory.routines import get_routine, list_routines
from memory.voice_corrections import (
    forget_voice_correction,
    list_voice_corrections,
    remember_voice_correction,
)
from llm.chat import chat_response
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
    "whats app": "whatsapp",
    "watsap": "whatsapp",
    "uatsap": "whatsapp",
    "estaga": "whatsapp",
    "estag": "whatsapp",
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

MEDIA_TARGETS = {
    "spotify": "spotify",
    "youtube": "youtube",
    "you tube": "youtube",
    "you": "youtube",
    "chrome": "chrome",
    "navegador": "chrome",
}

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

TEXT_INPUT_PREFIXES = (
    "digitar ",
    "digite ",
    "digita ",
    "escrever ",
    "escreva ",
    "escreve ",
    "ditar ",
    "dita ",
    "colar ",
    "cole ",
    "cola ",
    "inserir texto ",
    "insira texto ",
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

CHATTER_PATTERNS = {
    "boa": "Estou ouvindo.",
    "opa": "Estou aqui.",
    "e ai": "Fala comigo.",
    "oi": "Ola.",
    "ola": "Ola.",
    "olá": "Ola.",
    "posso falar": "Pode falar.",
    "ta ouvindo": "Estou ouvindo sim.",
    "esta ouvindo": "Estou ouvindo sim.",
    "tudo bem": "Tudo certo por aqui. Pronto para trabalhar.",
    "como voce esta": "Estou bem. Com vontade de ser util.",
    "como voce ta": "Estou bem. Pode mandar.",
    "obrigado": "Disponha. Estamos juntos.",
    "obrigada": "Disponha. Estamos juntos.",
    "valeu": "Valeu. Seguimos.",
    "bom trabalho": "Obrigado. Estou pegando o jeito.",
    "muito bom": "Boa. Isso significa que estamos evoluindo.",
    "vamos trabalhar": "Vamos sim. Me diga o que quer fazer.",
    "vamos avancar": "Vamos avancar. Qual frente voce quer puxar agora?",
    "quem e voce": "Sou seu estagiario local. Eu abro apps, controlo janelas, navego e estou aprendendo a conversar melhor.",
    "o que voce e": "Sou seu estagiario local. Ainda meio junior, mas dedicado.",
    "qual seu nome": "Meu nome e Estagiario. Simples, funcional, com leve cheiro de cafe frio.",
    "qual e seu nome": "Meu nome e Estagiario. Simples, funcional, com leve cheiro de cafe frio.",
    "o que voce sabe fazer": "Posso abrir apps e sites, controlar janelas, navegar no navegador, controlar midia, lembrar atalhos e responder comandos por voz.",
    "o que voce consegue fazer": "Posso abrir apps e sites, controlar janelas, navegar no navegador, controlar midia, lembrar atalhos e responder comandos por voz.",
    "me conta uma coisa interessante": "Uma coisa interessante: quase toda automacao boa nasce de uma frase irritante repetida muitas vezes. A gente esta transformando irritacao em botao invisivel.",
    "fala uma coisa interessante": "Uma coisa interessante: quase toda automacao boa nasce de uma frase irritante repetida muitas vezes. A gente esta transformando irritacao em botao invisivel.",
}

REPEAT_PATTERNS = {
    "de novo",
    "denovo",
    "mais uma",
    "outra vez",
    "repete",
    "repita",
}

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
    while words and words[0] in {"o", "a", "os", "as", "um", "uma", "do", "da", "dos", "das", "no", "na", "nos", "nas"}:
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
    if text in CHATTER_PATTERNS:
        return {"intent": "respond", "target": None, "response": CHATTER_PATTERNS[text]}

    if "bom dia" in text:
        return {"intent": "respond", "target": None, "response": "Bom dia. Vamos fazer esse computador trabalhar."}

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


def detect_memory_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {"listar memoria", "liste a memoria", "listar atalhos", "liste os atalhos", "o que voce lembra"}:
        return {"intent": "list_smart_memory", "target": None}

    remember_match = re.match(
        r"^(?:lembre|lembra|memorize|salve)\s+que\s+(.+?)\s+e\s+(app|aplicativo|programa|site)$",
        lower,
    )
    if remember_match:
        kind = remember_match.group(2)
        if kind in {"aplicativo", "programa"}:
            kind = "app"
        return {
            "intent": "remember_target_kind",
            "target": {
                "name": remember_match.group(1).strip(),
                "kind": kind,
            },
        }

    forget_match = re.match(
        r"^(?:esqueca|esquece|remova|apague)\s+(?:a\s+memoria\s+de\s+|o\s+atalho\s+|a\s+lembranca\s+de\s+)?(.+)$",
        lower,
    )
    if forget_match:
        return {"intent": "forget_smart_memory", "target": forget_match.group(1).strip()}

    return None


def detect_voice_correction_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {"listar correcoes de voz", "listar correcoes", "ver correcoes de voz", "ver correcoes"}:
        corrections = list_voice_corrections()
        if not corrections:
            return {"intent": "respond", "target": None, "response": "Nenhuma correcao de voz salva."}

        rows = [
            f"{idx}. quando ouvir '{item['heard']}', entender '{item['means']}'"
            for idx, item in enumerate(corrections, start=1)
        ]
        return {"intent": "respond", "target": None, "response": "Correcoes de voz: " + "; ".join(rows)}

    forget_match = re.match(
        r"^(?:esquecer|esquece|apagar|apague|remover|remova)\s+correc(?:ao|oes)\s+(?:de\s+voz\s+)?(.+)$",
        lower,
    )
    if forget_match:
        heard = forget_match.group(1).strip().strip('"').strip("'")
        if forget_voice_correction(heard):
            return {"intent": "respond", "target": None, "response": f"Esqueci a correcao de voz para '{heard}'."}
        return {"intent": "respond", "target": None, "response": f"Nao encontrei correcao de voz para '{heard}'."}

    teach_patterns = [
        r"^(?:aprenda|aprende|lembrar|lembre)\s+que\s+['\"]?(.+?)['\"]?\s+(?:significa|quer dizer|e para entender como|eh para entender como)\s+['\"]?(.+?)['\"]?$",
        r"^quando\s+(?:eu\s+)?(?:disser|falar)\s+['\"]?(.+?)['\"]?\s+(?:entenda|entender|interprete|interpretar)\s+(?:como\s+)?['\"]?(.+?)['\"]?$",
    ]
    for pattern in teach_patterns:
        match = re.match(pattern, lower)
        if not match:
            continue

        heard = match.group(1).strip()
        means = match.group(2).strip()
        if remember_voice_correction(heard, means):
            return {
                "intent": "respond",
                "target": None,
                "response": f"Aprendi: quando ouvir '{heard}', vou entender como '{means}'.",
            }

    return None


def _match_site_target(text: str):
    sites = _site_options()
    target = _strip_leading_articles(normalize_text(text))
    site = _best_fuzzy_match(target, sites, cutoff=0.65)
    if site:
        return site

    return target


def detect_navigation_command(user_input: str):
    lower = normalize_text(user_input).strip(" .")

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

    if lower in {
        "traduzir isso",
        "traduza isso",
        "traduz isso",
        "traduzir esse texto",
        "traduza esse texto",
        "traduz esse texto",
        "traduzir o que li",
        "traduza o que li",
        "traduz o que li",
    }:
        return {"intent": "browser_translate_last_selection", "target": None}

    if re.match(
        r"^(?:e\s+)?(?:o\s+)?que\s+(?:tem|ta|esta)(?:\s+ai)?\s+na\s+tela$",
        lower,
    ):
        return {"intent": "browser_describe_screen", "target": None}

    if lower in {
        "resuma a tela",
        "resumir tela",
        "resumir a tela",
        "resuma o conteudo",
        "resuma o conteúdo",
        "resuma o conteudo da tela",
        "resuma o conteúdo da tela",
        "me da um resumo da tela",
        "me de um resumo da tela",
        "qual o resumo da tela",
        "resumo da tela",
        "o que voce ve resumido",
        "o que voce ve na tela resumido",
    }:
        return {"intent": "browser_summarize_screen", "target": None}

    if lower in {
        "atualizar investimentos",
        "atualizar meus investimentos",
        "atualizar carteira",
        "sincronizar investimentos",
        "sincronizar carteira",
        "reler carteira",
        "ler carteira agora",
        "analisar investimentos",
        "analisar meus investimentos",
        "resumir investimentos",
        "resuma investimentos",
        "analisar carteira",
        "ler carteira",
    }:
        return {"intent": "browser_investment_snapshot", "target": None}

    if lower in {
        "modo investimentos",
        "resumo financeiro",
        "resumo da carteira",
        "minha carteira",
        "ver investimentos",
        "acompanhar investimentos",
        "acompanhar carteira",
        "ver carteira",
        "resumir carteira",
    }:
        return {"intent": "investment_memory_summary", "target": None}

    if lower in {
        "valor investido",
        "valor investido da carteira",
        "valor atual",
        "valor atual da carteira",
        "patrimonio",
        "patrimÃ´nio",
        "rentabilidade",
        "rentabilidade da carteira",
        "proventos",
        "proventos da carteira",
        "dividendos",
        "dividendos da carteira",
        "lucro",
        "prejuizo",
        "prejuÃ­zo",
        "saldo da carteira",
        "posicoes",
        "posiÃ§Ãµes",
    }:
        return {"intent": "investment_memory_answer", "target": user_input.strip()}

    if lower in {
        "analisar investimentos",
        "analisar meus investimentos",
        "modo investimentos",
        "resumo financeiro",
        "resumir investimentos",
        "resuma investimentos",
        "resumo da carteira",
        "analisar carteira",
        "ler carteira",
        "minha carteira",
        "ver investimentos",
        "acompanhar investimentos",
        "acompanhar carteira",
        "ver carteira",
        "resumir carteira",
        "valor investido da carteira",
        "valor atual da carteira",
        "rentabilidade da carteira",
        "proventos da carteira",
        "dividendos da carteira",
    }:
        return {"intent": "browser_investment_snapshot", "target": None}

    if lower in {
        "valor investido",
        "valor atual",
        "patrimonio",
        "patrimônio",
        "rentabilidade",
        "proventos",
        "dividendos",
        "lucro",
        "prejuizo",
        "prejuízo",
        "saldo da carteira",
        "posicoes",
        "posições",
    }:
        return {"intent": "browser_investment_snapshot", "target": None}

    if lower in {
        "abrir investidor 10",
        "abrir investidor10",
        "abrir carteira",
        "abrir minha carteira",
        "abrir carteira do investidor 10",
        "abrir carteira do investidor10",
        "abrir meus investimentos",
        "abrir carteira e resumir",
        "abrir minha carteira e resumir",
        "abrir carteira e analisar",
        "abrir minha carteira e analisar",
        "abrir investidor 10 e resumir",
        "abrir investidor10 e resumir",
        "abrir investidor 10 e analisar",
        "abrir investidor10 e analisar",
    }:
        return {"intent": "browser_open_wallet_and_summarize", "target": None}

    if lower in {"resume", "resome", "resumida", "resumir", "resuma"}:
        return {"intent": "browser_summarize_screen", "target": None}

    if re.match(r"^resum\w*\s+(?:a\s+)?tela$", lower):
        return {"intent": "browser_summarize_screen", "target": None}

    if lower in {
        "detalha",
        "detalhar",
        "detalha a tela",
        "detalhar a tela",
        "conteudo principal",
        "conteúdo principal",
        "conteudo principal da tela",
        "conteúdo principal da tela",
        "o que importa na tela",
        "o que e importante na tela",
        "o que é importante na tela",
        "explique a tela",
        "me explique a tela",
        "quero detalhes da tela",
        "me de detalhes da tela",
        "me dê detalhes da tela",
        "o que ha na tela em detalhe",
        "o que há na tela em detalhe",
    }:
        return {"intent": "browser_explain_screen", "target": None}

    if lower in {"explica", "explique", "explica melhor", "me explica melhor"}:
        return {"intent": "browser_explain_screen", "target": None}

    if re.match(r"^(?:detalh\w*|explic\w*)\s+(?:a\s+)?tela$", lower):
        return {"intent": "browser_explain_screen", "target": None}

    if lower in {
        "o que tem na tela",
        "que tem na tela",
        "e que tem na tela",
        "ler tela",
        "leia a tela",
        "ler a pagina",
        "leia a pagina",
        "ler texto da pagina",
        "ver texto da pagina",
        "ver o texto da pagina",
        "veja texto da pagina",
        "veja o texto da pagina",
        "leia o texto da pagina",
        "leia texto da pagina",
        "lembre o texto da pagina",
        "ler o texto da pagina",
        "liga o texto da pagina",
        "ligar o texto da pagina",
        "listar links",
        "liste os links",
        "mostrar opcoes",
        "mostrar opções",
        "quais botoes",
        "quais botao",
        "quais links",
    }:
        return {"intent": "browser_describe_screen", "target": None}

    if lower in {
        "traduzir selecionado",
        "traduz selecionado",
        "traduza selecionado",
        "traduzir selecao",
        "traduzir seleção",
        "traduz a selecao",
        "traduz a seleção",
        "traduza a selecao",
        "traduza a seleção",
        "traduzir texto selecionado",
        "traduza o texto selecionado",
        "traduzir isso",
        "traduza isso",
        "traduz isso",
        "traducao do selecionado",
        "tradução do selecionado",
    }:
        if "isso" in lower or "que li" in lower:
            return {"intent": "browser_translate_last_selection", "target": None}
        return {"intent": "browser_translate_selection", "target": None}

    if any(token in lower for token in {"traduz", "traduza", "traducao", "tradução"}) and any(
        token in lower for token in {"selecion", "seleccion", "licion", "isso", "texto"}
    ):
        if "isso" in lower or "que li" in lower:
            return {"intent": "browser_translate_last_selection", "target": None}
        return {"intent": "browser_translate_selection", "target": None}

    if lower in {
        "ler produtos selecionados",
        "ler produto selecionado",
        "leia produtos selecionados",
        "leia os produtos selecionados",
        "extrair produtos selecionados",
        "listar produtos selecionados",
    }:
        return {"intent": "browser_read_selected_products", "target": None}

    if lower in {
        "ler selecionado",
        "leia selecionado",
        "ler selecao",
        "ler seleção",
        "leia a selecao",
        "leia a seleção",
        "ler texto selecionado",
        "leia o texto selecionado",
        "o que selecionei",
        "usar selecionado",
        "usar selecao",
        "usar seleção",
        "ler itens selecionados",
        "ler produtos selecionados",
    }:
        return {"intent": "browser_read_selection", "target": None}

    if any(token in lower for token in {"selecion", "seleccion", "licion"}) and any(
        token in lower
        for token in {
            "ler",
            "leia",
            "leica",
            "lig",
            "link",
            "links",
            "item",
            "itens",
            "produto",
            "produtos",
            "texto",
            "usar",
        }
    ):
        return {"intent": "browser_read_selection", "target": None}

    if lower in {
        "ler mais",
        "leia mais",
        "mostrar mais",
        "mostre mais",
        "ver mais",
        "veja mais",
        "continua lendo",
        "continuar lendo",
        "o que mais tem",
        "mais produtos",
        "proximos produtos",
        "proximas opcoes",
        "proximos itens",
    }:
        return {"intent": "browser_read_more", "target": None}

    if lower in {
        "qual o mais barato",
        "qual e o mais barato",
        "qual é o mais barato",
        "me diga o mais barato",
        "mostre o mais barato",
        "comparar precos",
        "comparar preços",
        "compare os precos",
        "compare os preços",
        "menor preco",
        "menor preço",
        "menor pre o",
        "comparar pre os",
        "compare os pre os",
    }:
        return {"intent": "browser_cheapest_listed_item", "target": None}

    if lower.startswith(("comparar pre", "compare os pre", "comparar os pre")):
        return {"intent": "browser_cheapest_listed_item", "target": None}

    ordinal_words = {
        "primeiro": 1,
        "primeira": 1,
        "segundo": 2,
        "segunda": 2,
        "terceiro": 3,
        "terceira": 3,
        "quarto": 4,
        "quarta": 4,
        "quinto": 5,
        "quinta": 5,
        "sexto": 6,
        "sexta": 6,
        "setimo": 7,
        "setima": 7,
        "oitavo": 8,
        "oitava": 8,
        "nono": 9,
        "nona": 9,
        "decimo": 10,
        "decima": 10,
    }
    listed_item_match = re.match(
        r"^(?:clicar|clica|clique|abrir|abre|selecionar|selecione|apertar|aperte)\s+(?:no|na|o|a)?\s*(\d+|primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa]|sext[oa]|setim[oa]|oitav[oa]|non[oa]|decim[oa])(?:\s+(?:item|produto|resultado|opcao|opcao da lista|link))?$",
        lower,
    )
    if listed_item_match:
        item = listed_item_match.group(1)
        index = int(item) if item.isdigit() else ordinal_words.get(item)
        if index:
            return {"intent": "browser_click_listed_item", "target": index}

    info_item_match = re.match(
        r"^(?:informacao|informacoes|informaçao|informação|informa o|informa es|detalhe|detalhes|fale|me fale|me diga|diga|ver|veja|mostrar|mostre)\s+(?:do|da|de|o|a|sobre\s+o|sobre\s+a)?\s*(\d+|primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa]|sext[oa]|setim[oa]|oitav[oa]|non[oa]|decim[oa])(?:\s+(?:item|produto|resultado|opcao|opcao da lista))?$",
        lower,
    )
    if info_item_match:
        item = info_item_match.group(1)
        index = int(item) if item.isdigit() else ordinal_words.get(item)
        if index:
            return {"intent": "browser_describe_listed_item", "target": index}

    if any(phrase in lower for phrase in {
        "rolar para baixo",
        "rolar tela para baixo",
        "role tela para baixo",
        "role para baixo",
        "role a tela para baixo",
        "desce a tela",
        "descer a tela",
        "desca a tela",
        "desça a tela",
        "desce na tela",
        "descer na tela",
        "desuna a tela",
        "desum na tela",
        "desuna na tela",
        "desum a tela",
        "desliza para baixo",
        "deslize para baixo",
        "deslizar para baixo",
        "mais para baixo",
        "rolar mais",
        "descer mais",
        "continua descendo",
        "continuar descendo",
        "pagina para baixo",
        "olhe a tela para baixo",
        "olhe para baixo",
        "ola para baixo",
        "ol para baixo",
    }):
        return {"intent": "browser_scroll_down", "target": None}

    if any(phrase in lower for phrase in {
        "descer um pouco",
        "desce um pouco",
        "rolar um pouco",
        "role um pouco",
        "um pouco para baixo",
        "pouco para baixo",
    }):
        return {"intent": "browser_scroll_down_small", "target": None}

    if any(phrase in lower for phrase in {
        "rolar para cima",
        "rolar tela para cima",
        "role tela para cima",
        "role para cima",
        "role a tela para cima",
        "sobe a tela",
        "subir a tela",
        "sobe na tela",
        "subir na tela",
        "desliza para cima",
        "deslize para cima",
        "deslizar para cima",
        "mais para cima",
        "subir mais",
        "continua subindo",
        "continuar subindo",
        "pagina para cima",
        "olhe a tela para cima",
        "olhe para cima",
        "ola para cima",
        "ol para cima",
    }):
        return {"intent": "browser_scroll_up", "target": None}

    if any(phrase in lower for phrase in {
        "subir um pouco",
        "sobe um pouco",
        "um pouco para cima",
        "pouco para cima",
    }):
        return {"intent": "browser_scroll_up_small", "target": None}

    if lower in {"ir para o topo", "vai para o topo", "topo da pagina", "topo", "inicio da pagina", "comeco da pagina", "começo da pagina"}:
        return {"intent": "browser_scroll_top", "target": None}

    if lower in {
        "ir para o fim",
        "vai para o fim",
        "fim da pagina",
        "final da pagina",
        "fim da tela",
        "final da tela",
        "ate o final",
        "ate o fim",
        "rolar ate o final",
        "rolar tela ate o final",
        "olhe a tela ate o final da tela",
        "ir ate o final da tela",
        "vai ate o final da tela",
        "fim",
    }:
        return {"intent": "browser_scroll_bottom", "target": None}

    if lower in {"voltar pagina", "voltar no site", "voltar no navegador", "pagina anterior", "volta pagina", "volta no site"}:
        return {"intent": "browser_back", "target": None}

    if lower in {"avancar pagina", "avancar no site", "avancar no navegador", "pagina seguinte", "vai pra frente", "vai para frente"}:
        return {"intent": "browser_forward", "target": None}

    if lower in {"atualizar pagina", "atualiza pagina", "recarregar pagina", "recarrega pagina", "refresh", "atualizar"}:
        return {"intent": "browser_refresh", "target": None}

    if any(phrase in lower for phrase in {
        "abrir primeiro resultado",
        "abre primeiro resultado",
        "abrir o primeiro resultado",
        "abre o primeiro resultado",
        "primeiro resultado",
        "abrir primeiro link",
        "abre primeiro link",
        "abrir o primeiro link",
        "abre o primeiro link",
        "primeiro link",
    }):
        return {"intent": "browser_open_first_result", "target": None}

    if lower in {"abrir selecionado", "abre selecionado", "abrir item", "abre item", "entrar", "enter"}:
        return {"intent": "browser_open_focused_item", "target": None}

    if lower in {"clicar no centro", "clique no centro", "clica no centro", "clicar na pagina", "clique na pagina"}:
        return {"intent": "browser_click_center", "target": None}

    click_match = re.match(
        r"^(?:clicar|clica|clique|selecionar|selecione|apertar|aperte)\s+(?:(?:em|no|na|o|a)\s+)?(.+)$",
        lower,
    )
    if click_match:
        target = click_match.group(1).strip()
        if target and target not in {"centro", "pagina", "tela"}:
            return {"intent": "browser_click_text", "target": target}

    if lower in {"zoom", "aumentar zoom", "aumenta zoom", "mais zoom", "zoom mais", "ampliar tela", "ampliar a tela", "amplia tela", "amplia a tela", "umpliar a tela", "umpliar a teoria", "ampliar a teoria"}:
        return {"intent": "browser_zoom_in", "target": None}

    if lower in {"diminuir zoom", "diminui zoom", "menos zoom", "zoom menos"}:
        return {"intent": "browser_zoom_out", "target": None}

    if lower in {"resetar zoom", "restaurar zoom", "zoom normal", "voltar zoom"}:
        return {"intent": "browser_zoom_reset", "target": None}

    find_match = re.match(r"^(?:procurar|procure|buscar|busque|encontre)\s+(.+?)\s+(?:na|nesta|nessa)\s+pagina$", lower)
    if find_match:
        return {"intent": "browser_find", "target": find_match.group(1).strip()}

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

    site_search_match = re.match(
        r"^(?:pesquisa|pesquise|pesquisar|esquise|esquisar|procure|procurar|buscar|busque)\s+(.+?)\s+(?:no|na|em|dentro\s+do|dentro\s+da)\s+(.+)$",
        lower,
    )
    if site_search_match:
        return {
            "intent": "browser_search_site",
            "target": {
                "query": site_search_match.group(1).strip(),
                "site": _match_site_target(site_search_match.group(2).strip()),
            },
        }

    return None


def detect_browser_command(user_input: str):
    lower = normalize_text(user_input)

    if any(phrase in lower for phrase in {"fecha aba e site", "fechar aba e site", "fecha o site", "fechar o site"}):
        return {"intent": "browser_close_tab", "target": None}

    if lower in {"fecha", "fechar", "fecha ai", "fecha ae"}:
        return {"intent": "context_close", "target": None}

    if lower in {"aba anterior", "anterior"}:
        return {"intent": "browser_prev_tab", "target": None}

    if lower in {"volta", "voltar"}:
        return {"intent": "browser_back", "target": None}

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
        if _match_app_target(candidate):
            return None
        if _best_fuzzy_match(candidate, _site_options(), cutoff=0.7):
            return None
        if _looks_like_new_tab(candidate):
            return {"intent": "browser_new_tab", "target": None}

    if lower in {"fechar aba", "fecha aba", "feche a aba", "fecha"} or "fechar aba" in lower:
        return {"intent": "browser_close_tab", "target": None}

    if lower.startswith(("pesquisa por ", "pesquisar por ", "pesquise por ", "esquisar por ", "esquise por ")):
        query = re.sub(r"^(pesquisa|pesquisar|pesquise|esquisar|esquise) por ", "", lower).strip()
        query = re.sub(r"\s+no navegador$", "", query).strip()
        if query:
            return {"intent": "browser_search", "target": query}

    if lower.startswith(("pesquisa ", "pesquisar ", "pesquise ", "esquisar ", "esquise ")):
        query = re.sub(r"^(pesquisa|pesquisar|pesquise|esquisar|esquise) ", "", lower).strip()
        query = re.sub(r"\s+no navegador$", "", query).strip()
        if query:
            return {"intent": "google_search", "target": query}

    return None


def detect_media_command(user_input: str):
    lower = normalize_text(user_input)
    media_target_pattern = r"(?:spotify|youtube|you tube|you|chrome|navegador)"
    target_article_pattern = r"(?:(?:o|a|no|na|do|da)\s+)?"

    if re.search(rf"\b(bye|bai)\s+{target_article_pattern}({media_target_pattern})\b", lower):
        target_match = re.search(rf"\b(bye|bai)\s+{target_article_pattern}({media_target_pattern})\b", lower)
        target = MEDIA_TARGETS.get(target_match.group(2), target_match.group(2))
        return {"intent": "media_pause_target", "target": target}

    combo_match = re.search(
        rf"\b(?:pausa|pausar|pause|parar|para|para ai|pare)\s+{target_article_pattern}(?P<first>{media_target_pattern})\b"
        rf".*\b(?:play|toca|tocar|continua|continuar|abre|abrir)\s+{target_article_pattern}(?P<second>{media_target_pattern})\b",
        lower,
    )
    if combo_match:
        first = MEDIA_TARGETS.get(combo_match.group("first"), combo_match.group("first"))
        second = MEDIA_TARGETS.get(combo_match.group("second"), combo_match.group("second"))
        if first and second:
            return {
                "intent": "run_routine",
                "target": [
                    f"pausar {first}",
                    f"play {second}",
                ],
                "name": "troca de midia",
            }

    target_match = re.search(rf"\b(?P<action>pausa|pausar|pause|parar|para|para ai|pare|play|toca|tocar|continua|continuar|despausa)\s+{target_article_pattern}(?P<target>{media_target_pattern})\b", lower)
    if target_match:
        action_word = target_match.group("action")
        target = MEDIA_TARGETS.get(target_match.group("target"), target_match.group("target"))
        if action_word in {"pausa", "pausar", "pause", "parar", "para", "para ai", "pare"}:
            return {"intent": "media_pause_target", "target": target}
        if action_word in {"play", "toca", "tocar", "continua", "continuar", "despausa"}:
            return {"intent": "media_play_target", "target": target}
        return {"intent": "media_play_pause_target", "target": target}

    next_match = re.search(rf"\b(proxima|proximo|passa|passar)\s+(?:musica|video|midia)?\s*(?:no\s+|na\s+|do\s+|da\s+)?({media_target_pattern})\b", lower)
    if next_match:
        target = MEDIA_TARGETS.get(next_match.group(2), next_match.group(2))
        return {"intent": "media_next_target", "target": target}

    previous_match = re.search(rf"\b(anterior|volta|voltar)\s+(?:musica|video|midia)?\s*(?:no\s+|na\s+|do\s+|da\s+)?({media_target_pattern})\b", lower)
    if previous_match:
        target = MEDIA_TARGETS.get(previous_match.group(2), previous_match.group(2))
        return {"intent": "media_previous_target", "target": target}

    if lower in {"pausa", "pausar", "pause", "play", "continua", "continuar", "despausa"}:
        return {"intent": "media_play_pause", "target": None}

    if any(phrase in lower for phrase in {"pausa musica", "pausar musica", "pausa video", "pausar video", "continua musica", "continuar musica", "continua video", "continuar video"}):
        return {"intent": "media_play_pause", "target": None}

    if any(phrase in lower for phrase in {"proxima musica", "proximo video", "proxima midia", "passa musica", "passar musica", "passa para proxima", "passar para proxima"}):
        return {"intent": "media_next", "target": None}

    if any(phrase in lower for phrase in {"musica anterior", "video anterior", "midia anterior", "volta musica", "voltar musica", "musica de antes"}):
        return {"intent": "media_previous", "target": None}

    if any(phrase in lower for phrase in {"aumenta volume", "aumentar volume", "volume para cima", "sobe volume", "subir volume", "mais volume"}):
        return {"intent": "volume_up", "target": None}

    if any(phrase in lower for phrase in {"abaixa volume", "abaixar volume", "diminui volume", "diminuir volume", "volume para baixo", "menos volume"}):
        return {"intent": "volume_down", "target": None}

    if any(phrase in lower for phrase in {"muta", "mutar", "mudo", "silencia", "silenciar", "tira o som", "ativar mudo"}):
        return {"intent": "volume_mute", "target": None}

    return None


def detect_code_inspection_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {
        "inspecionar selecionado",
        "inspecionar selecao",
        "inspecionar seleção",
        "inspecionar codigo selecionado",
        "inspecionar c digo selecionado",
        "inspecionar c3digo selecionado",
        "inspecionar c3 b3digo selecionado",
        "inspecionar cã³digo selecionado",
        "inspecionar cã³digo selecionado",
        "inspecionar o codigo selecionado",
        "analisar selecionado",
        "analisar selecao",
        "analisar seleção",
        "analisar codigo selecionado",
        "analisar c digo selecionado",
        "analisar o codigo selecionado",
        "revisar codigo selecionado",
        "procurar erro no selecionado",
        "procurar erros no selecionado",
        "procurar erros no codigo selecionado",
    }:
        return {"intent": "code_inspect_selection", "target": None}

    if "selecionado" in lower and ("inspecionar" in lower or "analisar" in lower) and (
        "codigo" in lower or "c digo" in lower or "digo" in lower
    ):
        return {"intent": "code_inspect_selection", "target": None}

    if lower in {
        "inspecionar codigo",
        "inspecionar o codigo",
        "inspecionar codigo do projeto",
        "analisar codigo",
        "analisar o codigo",
        "revisar codigo",
        "revisar o codigo",
        "procurar erros no codigo",
        "procurar erros no projeto",
        "achar erros no codigo",
        "detectar erros no codigo",
    }:
        return {"intent": "code_inspect_workspace", "target": None}

    for prefix in (
        "inspecionar arquivo ",
        "inspecione o arquivo ",
        "analisar arquivo ",
        "analise o arquivo ",
        "procurar erros no arquivo ",
        "achar erros no arquivo ",
        "revisar arquivo ",
    ):
        if lower.startswith(prefix):
            target = user_input[len(prefix):].strip()
            if target:
                return {"intent": "code_inspect_target", "target": target}

    return None


def detect_image_analysis_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {
        "analisar imagem no navegador",
        "analisar a imagem no navegador",
        "interpretar imagem no navegador",
        "interpretar a imagem no navegador",
        "identificar elementos no navegador",
        "descrever cena no navegador",
        "o que tem na imagem do navegador",
        "o que ha na imagem do navegador",
        "ler imagem no navegador",
        "ver imagem no navegador",
    }:
        return {"intent": "image_analyze_browser", "target": None}

    if lower in {
        "analisar imagem copiada",
        "interpretar imagem copiada",
        "descrever imagem copiada",
        "analisar imagem do clipboard",
        "interpretar imagem do clipboard",
        "analisar imagem da area de transferencia",
        "interpretar imagem da area de transferencia",
        "analisar print copiado",
        "ler imagem copiada",
    }:
        return {"intent": "image_analyze_clipboard", "target": None}

    if lower in {
        "analisar imagem",
        "analisa imagem",
        "analise imagem",
        "analisar grafico",
        "analisa grafico",
        "analise grafico",
        "interpretar grafico",
        "interpreta grafico",
        "interprete grafico",
        "interpretar grafico da tela",
        "interpretar gráfico",
        "interpretar gráfico da tela",
        "ler grafico",
        "ler gráfico",
    }:
        return {"intent": "image_analyze_screen", "target": None}

    if lower in {
        "analisar imagem da tela",
        "analisar a imagem da tela",
        "analisa imagem da tela",
        "analise a imagem da tela",
        "interpretar imagem",
        "interpreta imagem",
        "interprete imagem",
        "interpretar imagem da tela",
        "interpretar a imagem da tela",
        "identificar elementos",
        "identifica elementos",
        "identifique elementos",
        "identificar elementos da tela",
        "descrever cena",
        "descreve cena",
        "descreva cena",
        "descrever a cena",
        "descrever imagem",
        "descreve imagem",
        "descreva imagem",
        "descrever a imagem",
        "descrever imagem da tela",
        "descreve imagem da tela",
        "descreva imagem da tela",
        "o que aparece na tela",
        "o que aparece nessa imagem",
        "o que aparece na imagem",
        "o que tem nessa imagem",
        "o que tem na imagem",
        "o que ha nessa imagem",
        "o que ha na imagem",
        "analisar print da tela",
        "analisar screenshot da tela",
        "ler imagem da tela",
        "leia imagem da tela",
        "ocr da tela",
        "ver imagem da tela",
    }:
        return {"intent": "image_analyze_screen", "target": None}

    for prefix in (
        "analisar imagem ",
        "analisa imagem ",
        "interpretar imagem ",
        "interprete imagem ",
        "descrever imagem ",
        "descreva imagem ",
        "identificar elementos em ",
        "identificar elementos da imagem ",
        "o que tem na imagem ",
        "o que aparece na imagem ",
        "o que ha na imagem ",
        "analisar grafico ",
        "analisar gráfico ",
        "interpretar grafico ",
        "interpretar gráfico ",
        "ler imagem ",
        "leia a imagem ",
        "extrair texto da imagem ",
        "extrai texto da imagem ",
        "ocr da imagem ",
        "analisar print ",
        "analisa print ",
        "analisar screenshot ",
    ):
        if lower.startswith(prefix):
            target = user_input[len(prefix):].strip()
            if target:
                return {"intent": "image_analyze", "target": target}

    return None


def detect_visual_question_command(user_input: str):
    lower = normalize_text(user_input)
    if not lower:
        return None

    explicit_prefixes = (
        "perguntar sobre imagem ",
        "pergunta sobre imagem ",
        "perguntar sobre a imagem ",
        "pergunta sobre a imagem ",
        "perguntar sobre pagina ",
        "pergunta sobre pagina ",
        "perguntar sobre a pagina ",
        "pergunta sobre a pagina ",
        "perguntar sobre página ",
        "pergunta sobre página ",
        "perguntar sobre a página ",
        "pergunta sobre a página ",
        "perguntar sobre site ",
        "pergunta sobre site ",
        "perguntar sobre o site ",
        "pergunta sobre o site ",
        "perguntar sobre tela ",
        "pergunta sobre tela ",
        "perguntar sobre a tela ",
        "pergunta sobre a tela ",
        "perguntar sobre grafico ",
        "pergunta sobre grafico ",
        "perguntar sobre o grafico ",
        "pergunta sobre o grafico ",
        "sobre a imagem ",
        "sobre a pagina ",
        "sobre a página ",
        "sobre o site ",
        "sobre a tela ",
        "sobre o grafico ",
        "sobre essa imagem ",
        "sobre essa pagina ",
        "sobre essa página ",
        "sobre essa tela ",
        "sobre esse grafico ",
    )
    for prefix in explicit_prefixes:
        if lower.startswith(prefix):
            question = user_input[len(prefix):].strip()
            if question:
                return {"intent": "vision_answer_question", "target": question}

    visual_terms = {"imagem", "grafico", "gráfico", "visual", "foto", "print", "tela", "pagina", "página", "site"}
    chart_question_terms = {
        "ganhou",
        "venceu",
        "vencedor",
        "maior",
        "menor",
        "menos",
        "valor",
        "valores",
        "resultado",
        "quanto",
        "porcentagem",
        "percentual",
        "queda",
        "caiu",
        "variacao",
        "variação",
        "anos",
        "materia",
        "matéria",
        "categoria",
        "categorias",
        "titulo",
        "título",
        "assunto",
        "preco",
        "preço",
        "link",
        "repo",
        "repositorio",
        "repositório",
    }
    question_starters = (
        "qual ",
        "quais ",
        "quem ",
        "que ",
        "quanto ",
        "quantos ",
        "quantas ",
        "o que ",
        "sobre o que ",
        "por que ",
        "porque ",
        "como ",
        "listar ",
        "lista ",
        "valor ",
        "valor de ",
        "quanto deu ",
        "quanto custa ",
        "quanto custa",
        "custa quanto ",
        "custa quanto",
        "resultado de ",
        "mostra ",
        "mostre ",
    )

    compact_lower = lower.replace(" ", "")
    has_visual_term = any(term in lower for term in visual_terms) or "graf" in compact_lower
    has_chart_question = any(term in lower for term in chart_question_terms)
    contextless_chart_terms = {
        "ganhou",
        "venceu",
        "vencedor",
        "maior",
        "menor",
        "porcentagem",
        "percentual",
        "queda",
        "caiu",
        "variacao",
        "variação",
        "anos",
        "materia",
        "matéria",
        "categoria",
        "titulo",
        "título",
        "matematica",
        "matemática",
        "portugues",
        "português",
        "ciencias",
        "ciências",
        "educacao fisica",
        "educação física",
        "historia",
        "história",
        "geografia",
        "ingles",
        "inglês",
    }
    contextless_visual_terms = {
        "animal",
        "bicho",
        "objeto",
        "objetos",
        "pessoa",
        "pessoas",
        "cor",
        "cores",
        "texto",
        "escrito",
        "aparece",
        "mostra",
        "assunto",
        "resumo",
        "preco",
        "preço",
        "custa",
        "custo",
        "valor",
        "repositorio",
        "repositório",
        "noticia",
        "notícia",
        "pagina",
        "página",
        "site",
        "isso",
        "essa",
        "esse",
        "dessa",
        "desse",
    }
    has_contextless_chart_question = any(term in lower for term in contextless_chart_terms)
    has_contextless_visual_question = any(term in lower for term in contextless_visual_terms)
    starts_like_question = lower.startswith(question_starters)

    if has_visual_term and (has_chart_question or starts_like_question):
        return {"intent": "vision_answer_question", "target": user_input.strip()}

    if has_contextless_chart_question and starts_like_question:
        return {"intent": "vision_answer_question", "target": user_input.strip()}

    if has_contextless_visual_question and starts_like_question:
        return {"intent": "vision_answer_question", "target": user_input.strip()}

    return None


def detect_investment_question_command(user_input: str):
    lower = normalize_text(user_input)
    if not lower:
        return None

    investment_terms = {
        "patrimonio",
        "patrimônio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
        "dividendos",
        "lucro",
        "prejuizo",
        "prejuízo",
        "aporte",
        "cotacao",
        "cotação",
        "preco medio",
        "preço medio",
        "preço médio",
        "carteira",
        "investimentos",
        "rendeu",
        "retorno",
    }
    question_starters = (
        "qual ",
        "quanto ",
        "quais ",
        "como ",
        "me diga ",
        "me fala ",
        "me fale ",
        "mostrar ",
        "mostre ",
    )

    if any(term in lower for term in investment_terms) and (
        lower.startswith(question_starters) or "?" in user_input
    ):
        return {"intent": "investment_memory_answer", "target": user_input.strip()}

    return None


def detect_vision_model_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {
        "status da visao",
        "status visao",
        "status visão",
        "status da visão",
        "status da visão",
        "modelo visual",
        "modelo de visao",
        "modelo de visão",
        "status do modelo visual",
        "qual modelo visual",
        "visao local",
        "visão local",
    }:
        return {"intent": "vision_status", "target": None}

    if lower in {
        "como ativar visao",
        "como ativar visão",
        "como instalar visao",
        "como instalar visão",
        "instalar modelo visual",
        "baixar modelo visual",
        "preparar visao",
        "preparar visão",
    }:
        return {"intent": "vision_install_hint", "target": None}

    if lower in {
        "baixar moondream",
        "instalar moondream",
        "baixar modelo moondream",
        "baixar modelo visual leve",
        "instalar modelo visual leve",
    }:
        return {"intent": "vision_download_light_model", "target": None}

    if lower in {
        "modelo visual ativo",
        "qual modelo de visao",
        "qual modelo de visão",
    }:
        return {"intent": "vision_active_model", "target": None}

    if lower in {
        "ultima analise visual",
        "última análise visual",
        "ultima imagem analisada",
        "última imagem analisada",
        "repetir analise visual",
        "repetir análise visual",
        "o que voce viu na imagem",
        "o que você viu na imagem",
    }:
        return {"intent": "vision_last_analysis", "target": None}

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

    if lower.startswith(("pesquisa ", "pesquise ", "pesquisar ")):
        query = re.sub(r"^(pesquisa|pesquise|pesquisar)\s+", "", user_input, flags=re.IGNORECASE).strip()
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

    focus_target = _extract_after_prefix(lower, FOCUS_PREFIXES)
    if focus_target:
        focus_target = _normalize_target_phrase(focus_target)
        app = _match_app_target(focus_target)
        if not app:
            app = _match_smart_app_target(focus_target)
        if app:
            return {"intent": "focus_app", "target": app}
        return {"intent": "respond", "target": None, "response": "Nao identifiquei qual janela focar."}

    maximize_target = _extract_after_prefix(lower, MAXIMIZE_PREFIXES)
    if maximize_target:
        maximize_target = _normalize_target_phrase(maximize_target)
        app = _match_app_target(maximize_target)
        if not app:
            app = _match_smart_app_target(maximize_target)
        if app:
            return {"intent": "maximize_app", "target": app}
        return {"intent": "respond", "target": None, "response": "Nao identifiquei qual janela maximizar."}

    minimize_target = _extract_after_prefix(lower, MINIMIZE_PREFIXES)
    if minimize_target:
        minimize_target = _normalize_target_phrase(minimize_target)
        app = _match_app_target(minimize_target)
        if not app:
            app = _match_smart_app_target(minimize_target)
        if app:
            return {"intent": "minimize_app", "target": app}
        return {"intent": "respond", "target": None, "response": "Nao identifiquei qual janela minimizar."}

    restore_target = _extract_after_prefix(lower, RESTORE_PREFIXES)
    if restore_target:
        restore_target = _normalize_target_phrase(restore_target)
        app = _match_app_target(restore_target)
        if not app:
            app = _match_smart_app_target(restore_target)
        if app:
            return {"intent": "restore_app", "target": app}
        return {"intent": "respond", "target": None, "response": "Nao identifiquei qual janela restaurar."}

    focus_target = _extract_after_fuzzy_prefix(lower, FOCUS_PREFIXES)
    if focus_target:
        focus_target = _normalize_target_phrase(focus_target)
        app = _match_app_target(focus_target)
        if not app:
            app = _match_smart_app_target(focus_target)
        if app:
            return {"intent": "focus_app", "target": app}
        return {"intent": "respond", "target": None, "response": "Nao identifiquei qual janela focar."}

    maximize_target = _extract_after_fuzzy_prefix(lower, MAXIMIZE_PREFIXES)
    if maximize_target:
        maximize_target = _normalize_target_phrase(maximize_target)
        app = _match_app_target(maximize_target)
        if not app:
            app = _match_smart_app_target(maximize_target)
        if app:
            return {"intent": "maximize_app", "target": app}
        return {"intent": "respond", "target": None, "response": "Nao identifiquei qual janela maximizar."}

    minimize_target = _extract_after_fuzzy_prefix(lower, MINIMIZE_PREFIXES)
    if minimize_target:
        minimize_target = _normalize_target_phrase(minimize_target)
        app = _match_app_target(minimize_target)
        if not app:
            app = _match_smart_app_target(minimize_target)
        if app:
            return {"intent": "minimize_app", "target": app}
        return {"intent": "respond", "target": None, "response": "Nao identifiquei qual janela minimizar."}

    restore_target = _extract_after_fuzzy_prefix(lower, RESTORE_PREFIXES)
    if restore_target:
        restore_target = _normalize_target_phrase(restore_target)
        app = _match_app_target(restore_target)
        if not app:
            app = _match_smart_app_target(restore_target)
        if app:
            return {"intent": "restore_app", "target": app}
        return {"intent": "respond", "target": None, "response": "Nao identifiquei qual janela restaurar."}

    return None


def detect_close_app(user_input: str):
    lower = normalize_text(user_input)
    close_target = _extract_after_prefix(lower, CLOSE_PREFIXES)
    apps = _app_options()
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
    apps = _app_options()
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


def detect_run_routine(user_input: str):
    lower = normalize_text(user_input)

    if lower in {"listar rotinas", "liste as rotinas", "quais rotinas", "ver rotinas"}:
        names = list_routines()
        if names:
            return {"intent": "respond", "target": None, "response": "Rotinas: " + ", ".join(names)}
        return {"intent": "respond", "target": None, "response": "Nenhuma rotina salva."}

    routine = get_routine(lower)
    if routine:
        return {"intent": "run_routine", "target": routine, "name": lower}

    for prefix in {"modo ", "rotina ", "executar rotina ", "executa rotina ", "rode rotina "}:
        if lower.startswith(prefix):
            name = lower[len(prefix):].strip()
            candidates = [name, f"modo {name}"]
            for candidate in candidates:
                routine = get_routine(candidate)
                if routine:
                    return {"intent": "run_routine", "target": routine, "name": candidate}

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


def detect_ollama_chat(user_input: str):
    text = normalize_text(user_input)
    if not text or len(text) <= 4:
        return None

    response = chat_response(user_input)
    if response:
        return {"intent": "respond", "target": None, "response": response}

    return None


def detect_type_text(user_input: str):
    lower = normalize_text(user_input)
    compact_lower = re.sub(r"[:\-]+", " ", lower)
    compact_lower = re.sub(r"\s+", " ", compact_lower).strip()
    for prefix in TEXT_INPUT_PREFIXES:
        if compact_lower.startswith(prefix):
            content = user_input[len(prefix):].strip(" \t,:;-")
            if not content:
                return {
                    "intent": "respond",
                    "target": None,
                    "response": "Qual texto devo inserir?",
                }
            return {"intent": "type_text", "target": None, "content": content}

    return None


def route(user_input: str):
    detectors = [
        detect_create_macro_start,
        detect_run_routine,
        detect_run_macro,
        detect_list_macros,
        detect_delete_macro,
        detect_type_text,
        detect_user_name,
        detect_greeting,
        detect_math,
        detect_bluetooth_command,
        detect_memory_command,
        detect_voice_correction_command,
        detect_navigation_command,
        detect_media_command,
        detect_browser_command,
        detect_code_inspection_command,
        detect_image_analysis_command,
        detect_visual_question_command,
        detect_investment_question_command,
        detect_vision_model_command,
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
        detect_window_command,
        detect_open_app,
        detect_open_url,
        detect_run_script,
        detect_profile_question,
        detect_short_unclear_text,
        detect_light_conversation,
    ]

    for detector in detectors:
        result = detector(user_input)
        if result:
            return result

    return {"intent": "respond", "target": None, "response": "Nao entendi."}
