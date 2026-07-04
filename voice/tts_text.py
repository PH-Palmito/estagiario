from __future__ import annotations

import json
import re
from pathlib import Path


def load_tts_pronunciations(preferences: dict, pronunciations_path: str | Path) -> dict[str, str]:
    if not bool(preferences.get("tts_pronunciations_enabled", True)):
        return {}

    try:
        data = json.loads(Path(pronunciations_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return {
        str(source): str(target)
        for source, target in data.items()
        if str(source).strip() and str(target).strip()
    }


def _repair_mojibake(text: str) -> str:
    if not any(marker in text for marker in ("\u00c3", "\u00c2", "\u00e2")):
        return text
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text


_NUMBER_WORDS = {
    0: "zero",
    1: "um",
    2: "dois",
    3: "três",
    4: "quatro",
    5: "cinco",
    6: "seis",
    7: "sete",
    8: "oito",
    9: "nove",
    10: "dez",
    11: "onze",
    12: "doze",
    13: "treze",
    14: "quatorze",
    15: "quinze",
    16: "dezesseis",
    17: "dezessete",
    18: "dezoito",
    19: "dezenove",
    20: "vinte",
    30: "trinta",
    40: "quarenta",
    50: "cinquenta",
    60: "sessenta",
    70: "setenta",
    80: "oitenta",
    90: "noventa",
    100: "cem",
}

_HUNDRED_WORDS = {
    100: "cento",
    200: "duzentos",
    300: "trezentos",
    400: "quatrocentos",
    500: "quinhentos",
    600: "seiscentos",
    700: "setecentos",
    800: "oitocentos",
    900: "novecentos",
}

_MONTH_NAMES_PTBR = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

_SPELLED_LETTER_NAMES = {
    "A": "á",
    "B": "bê",
    "C": "cê",
    "D": "dê",
    "E": "ê",
    "F": "éfe",
    "G": "gê",
    "H": "agá",
    "I": "i",
    "J": "jóta",
    "K": "cá",
    "L": "éle",
    "M": "ême",
    "N": "êne",
    "O": "ó",
    "P": "pê",
    "Q": "quê",
    "R": "érre",
    "S": "ésse",
    "T": "tê",
    "U": "u",
    "V": "vê",
    "W": "dáblio",
    "X": "xis",
    "Y": "ípsilon",
    "Z": "zê",
}

_TTS_ABBREVIATION_RULES = {
    "mAh": {"mode": "expand", "value": "miliampere hora"},
    "MAh": {"mode": "expand", "value": "miliampere hora"},
    "mah": {"mode": "expand", "value": "miliampere hora"},
    "Wh": {"mode": "expand", "value": "watt hora"},
    "kWh": {"mode": "expand", "value": "quilo watt hora"},
    "km": {"mode": "expand", "value": "quilômetro"},
    "kg": {"mode": "expand", "value": "quilo"},
    "MB": {"mode": "expand", "value": "megabyte"},
    "mb": {"mode": "expand", "value": "megabyte"},
    "GB": {"mode": "expand", "value": "gigabyte"},
    "gb": {"mode": "expand", "value": "gigabyte"},
    "TB": {"mode": "expand", "value": "terabyte"},
    "tb": {"mode": "expand", "value": "terabyte"},
    "RAM": {"mode": "spell"},
    "CPU": {"mode": "spell"},
    "GPU": {"mode": "spell"},
    "USB": {"mode": "spell"},
    "NFC": {"mode": "spell"},
    "SSD": {"mode": "spell"},
    "HD": {"mode": "spell"},
    "LED": {"mode": "spell"},
    "LCD": {"mode": "spell"},
    "LLM": {"mode": "spell"},
    "IA": {"mode": "spell"},
    "AI": {"mode": "spell"},
    "API": {"mode": "spell"},
    "OCR": {"mode": "spell"},
    "RPA": {"mode": "spell"},
    "UI": {"mode": "spell"},
    "UX": {"mode": "spell"},
    "PDF": {"mode": "spell"},
    "JSON": {"mode": "spell"},
    "URL": {"mode": "spell"},
    "HTTP": {"mode": "spell"},
    "HTTPS": {"mode": "spell"},
    "HDMI": {"mode": "spell"},
    "RGB": {"mode": "spell"},
    "NASA": {"mode": "word"},
    "laser": {"mode": "word"},
    "Laser": {"mode": "word"},
}

_PRONOUNCE_AS_WORD = {
    "NASA",
    "LASER",
    "RADAR",
    "WiFi",
    "WIFI",
}

_BUILTIN_TTS_PRONUNCIATIONS = {
    "GitHub": "guíti rãb",
    "github": "guíti rãb",
    "YouTube": "iútubi",
    "youtube": "iútubi",
    "Steam": "stim",
    "steam": "stim",
    "Chrome": "crôum",
    "chrome": "crôum",
    "Python": "paithon",
    "python": "paithon",
    "Google": "gúgou",
    "google": "gúgou",
    "Colab": "cólab",
    "colab": "cólab",
    "Android": "êndróid",
    "android": "êndróid",
    "Android Studio": "êndróid stúdio",
    "android studio": "êndróid stúdio",
    "PowerShell": "páuer shel",
    "powershell": "páuer shel",
    "OpenAI": "ôupen êi ái",
    "openai": "ôupen êi ái",
    "Wi-Fi": "uái fai",
    "wi-fi": "uái fai",
    "Wi Fi": "uái fai",
    "wi fi": "uái fai",
    "WiFi": "uái fai",
    "wifi": "uái fai",
    "Bluetooth": "blutúfi",
    "bluetooth": "blutúfi",
    "Mercado Livre": "mercádo lívre",
    "mercado livre": "mercádo lívre",
    "Magalu": "magalú",
    "magalu": "magalú",
    "Spotify": "ispótifai",
    "spotify": "ispótifai",
    "VS Code": "vê ésse côde",
    "VSCode": "vê ésse côde",
    "vscode": "vê ésse côde",
    "Whisper": "uísper",
    "whisper": "uísper",
    "Piper": "paiper",
    "piper": "paiper",
    "Ollama": "olâma",
    "ollama": "olâma",
    "Mobile": "môbail",
    "mobile": "môbail",
    "screenpilot": "screen pilot",
    "ScreenPilot": "screen pilot",
}


def _number_to_pt(value: int, feminine_one: bool = False) -> str:
    if feminine_one and value == 1:
        return "uma"

    if value in _NUMBER_WORDS:
        return _NUMBER_WORDS[value]

    if value < 100:
        ten = (value // 10) * 10
        unit = value % 10
        return f"{_NUMBER_WORDS[ten]} e {_number_to_pt(unit, feminine_one=feminine_one)}"

    if value < 1000:
        hundred = (value // 100) * 100
        rest = value % 100
        if rest == 0:
            return _HUNDRED_WORDS.get(hundred, str(value))
        return f"{_HUNDRED_WORDS.get(hundred, str(hundred))} e {_number_to_pt(rest, feminine_one=feminine_one)}"

    if value < 1_000_000:
        thousands = value // 1000
        rest = value % 1000

        if thousands == 1:
            prefix = "mil"
        else:
            prefix = f"{_number_to_pt(thousands, feminine_one=feminine_one)} mil"

        if rest == 0:
            return prefix

        connector = " e " if rest < 100 else ", "
        return f"{prefix}{connector}{_number_to_pt(rest, feminine_one=feminine_one)}"

    return str(value)


def _expand_time_expression(match: re.Match) -> str:
    hour = int(match.group(1))
    minute = match.group(2) if len(match.groups()) >= 2 else None
    hour_word = _number_to_pt(hour, feminine_one=True)

    if minute is None:
        unit = "hora" if hour == 1 else "horas"
        return f"{hour_word} {unit}"

    minute_value = int(minute)
    minute_word = _number_to_pt(minute_value, feminine_one=True)
    minute_unit = "minuto" if minute_value == 1 else "minutos"
    return f"{hour_word} horas e {minute_word} {minute_unit}"


def _expand_date_expression(match: re.Match) -> str:
    try:
        day = int(match.group(1))
        month = int(match.group(2))
    except (TypeError, ValueError):
        return match.group(0)

    if day < 1 or day > 31 or month not in _MONTH_NAMES_PTBR:
        return match.group(0)

    day_text = "primeiro" if day == 1 else _number_to_pt(day)
    year = match.group(3)
    year_text = ""
    if year:
        year_value = int(year)
        if year_value < 100:
            year_value += 2000 if year_value < 50 else 1900
        year_text = f" de {_number_to_pt(year_value)}"

    return f"{day_text} de {_MONTH_NAMES_PTBR[month]}{year_text}"


def _expand_temperature_expression(match: re.Match) -> str:
    value = int(match.group(1))
    unit = "grau" if value == 1 else "graus"
    return f"{_number_to_pt(value)} {unit} Célsius"


def _expand_degrees_expression(match: re.Match) -> str:
    value = int(match.group(1))
    unit = "grau" if value == 1 else "graus"
    return f"{_number_to_pt(value)} {unit}"


def _expand_storage_expression(match: re.Match) -> str:
    value = int(match.group(1))
    unit = (match.group(2) or "").upper()

    if unit == "MB":
        unit_text = "megabyte" if value == 1 else "megabytes"
    elif unit == "GB":
        unit_text = "gigabyte" if value == 1 else "gigabytes"
    elif unit == "TB":
        unit_text = "terabyte" if value == 1 else "terabytes"
    else:
        return match.group(0)

    return f"{_number_to_pt(value)} {unit_text}"


def _spell_acronym(token: str) -> str:
    parts = []
    for char in token:
        parts.append(_SPELLED_LETTER_NAMES.get(char.upper(), char.lower()))
    return " ".join(parts)


def _looks_pronounceable_acronym(token: str) -> bool:
    upper = token.upper()
    if upper in _PRONOUNCE_AS_WORD:
        return True

    if len(token) < 3 or len(token) > 5:
        return False

    vowels = sum(1 for char in upper if char in "AEIOU")
    consonants = sum(1 for char in upper if "A" <= char <= "Z" and char not in "AEIOU")
    return vowels >= 2 and consonants >= 1


_COMMON_UPPERCASE_WORDS = {
    "A",
    "AS",
    "COM",
    "DA",
    "DAS",
    "DE",
    "DO",
    "DOS",
    "E",
    "EM",
    "EU",
    "ME",
    "NO",
    "NOS",
    "O",
    "OS",
    "OU",
    "PRA",
    "QUE",
    "SEM",
    "UM",
    "UMA",
}


def _apply_abbreviation_rules(text: str) -> str:
    for source, rule in _TTS_ABBREVIATION_RULES.items():
        mode = str(rule.get("mode", "")).strip().lower()
        if mode == "expand":
            replacement = str(rule.get("value", "")).strip()
        elif mode == "spell":
            replacement = _spell_acronym(source)
        elif mode == "word":
            replacement = source.lower()
        else:
            continue

        if replacement:
            text = re.sub(rf"\b{re.escape(source)}\b", replacement, text)

    return text


def _apply_abbreviation_heuristics(text: str) -> str:
    def replacer(match: re.Match) -> str:
        token = match.group(0)
        if token in _TTS_ABBREVIATION_RULES:
            return token

        if any(char.islower() for char in token) and any(char.isupper() for char in token):
            lower = token.lower()
            if lower.endswith("mah"):
                return "miliampere hora"
            if lower.endswith("kwh"):
                return "quilo watt hora"
            if lower.endswith("wh"):
                return "watt hora"
            return token

        if token.isupper() and len(token) <= 4:
            if token in _COMMON_UPPERCASE_WORDS:
                return token.lower()
            if _looks_pronounceable_acronym(token):
                return token.lower()
            return _spell_acronym(token)

        return token

    return re.sub(r"\b[A-Za-z\u00C0-\u00FF]{2,5}\b", replacer, text)


def _replace_quoted_segment(match: re.Match) -> str:
    content = re.sub(r"\s+", " ", match.group(1) or "").strip(" ,")
    if not content:
        return ""
    return f", {content}, "


def _normalize_tts_tech_terms(text: str) -> str:
    replacements = {
        r"\bWi[\-\s]?Fi\b": "WiFi",
        r"\bwi[\-\s]?fi\b": "wifi",
        r"\bVS[\-\s]?Code\b": "VS Code",
        r"\bvs[\-\s]?code\b": "vscode",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return text


def _normalize_tts_quotes_and_brackets(text: str) -> str:
    text = re.sub(r'(?<!\w)"([^"\n]{1,120})"(?!\w)', _replace_quoted_segment, text)
    text = re.sub(r"(?<!\w)'([^'\n]{1,120})'(?!\w)", _replace_quoted_segment, text)
    text = re.sub(r"\(([^()\n]{1,120})\)", lambda match: f", {match.group(1).strip(' ,')}, ", text)
    text = re.sub(r"\[([^\[\]\n]{1,120})\]", lambda match: f", {match.group(1).strip(' ,')}, ", text)
    text = re.sub(r"\{([^\{\}\n]{1,120})\}", lambda match: f", {match.group(1).strip(' ,')}, ", text)
    return text


def _capitalize_tts_sentences(text: str) -> str:
    def replacer(match: re.Match) -> str:
        prefix = match.group(1)
        letter = match.group(2)
        return f"{prefix}{letter.upper()}"

    text = re.sub(r"(^|[.!?]\s+)([a-z\u00E0-\u00FF])", replacer, text)
    return text


def _normalize_tts_punctuation(text: str) -> str:
    ellipsis_token = " __TTS_ELLIPSIS__ "
    sentence_break = "\n"
    replacements = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)

    text = _normalize_tts_quotes_and_brackets(text)
    text = re.sub(r"\s*(?:\.{3,}|\u2026)\s*", ellipsis_token, text)
    text = re.sub(r"\s*[\ufffd\x1c\x1d-]\s*", ", ", text)
    text = re.sub(r"\s*/\s*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,.!?;:])(?=\S)", r"\1 ", text)
    text = re.sub(r"([!?]){2,}", r"\1", text)
    text = re.sub(r"(\.){4,}", "...", text)

    text = re.sub(r"\s*;\s*", f".{sentence_break}", text)
    text = re.sub(r"\s*:\s*", f".{sentence_break}", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*\.\s*", f".{sentence_break}", text)
    text = re.sub(r"\s*\?\s*", f"?{sentence_break}", text)
    text = re.sub(r"\s*!\s*", f"!{sentence_break}", text)
    text = text.replace(ellipsis_token.strip(), f"...{sentence_break}")
    text = re.sub(r"\s*\.\.\.\s*", f"...{sentence_break}", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r",\s*\.", f".{sentence_break}", text)
    text = re.sub(r"\.\s*,", f".{sentence_break}", text)
    text = re.sub(r",\s*([!?])", rf"\1{sentence_break}", text)
    text = re.sub(rf"{sentence_break}{{2,}}", sentence_break, text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(rf"[ \t]*{sentence_break}[ \t]*", sentence_break, text)
    text = text.strip()
    return _capitalize_tts_sentences(text)


def _expand_tts_reading_patterns(text: str) -> str:
    text = re.sub(r"\b([01]?\d|2[0-3])h([0-5]\d)\b", _expand_time_expression, text)
    text = re.sub(r"\b([01]?\d|2[0-3])h\b", _expand_time_expression, text)
    text = re.sub(
        r"\b(\d{1,3})\s*(?:°\s*C|graus?\s+Celsius|graus?\s+celsius)\b",
        _expand_temperature_expression,
        text,
    )
    text = re.sub(r"\b(\d{1,3})\s+graus\b", _expand_degrees_expression, text)
    text = re.sub(r"\b(\d{1,5})\s*mAh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} miliampere hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*Wh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} watt hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*kWh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} quilo watt hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*(MB|GB|TB)\b", _expand_storage_expression, text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,4})\s*km\b", lambda m: f"{_number_to_pt(int(m.group(1)))} quilômetros", text, flags=re.IGNORECASE)
    return text


def _expand_negative_tts_patterns(text: str) -> str:
    text = re.sub(r"(?<!\w)-\s*(R\$\s*\d[\d\.,]*)", r"menos \1", text)

    def percent_replacer(match: re.Match) -> str:
        number = str(match.group(1) or "").strip()
        if "," in number:
            integer, decimal = number.split(",", 1)
            if decimal:
                return f"menos {integer} vírgula {decimal} por cento"
        if "." in number:
            integer, decimal = number.split(".", 1)
            if decimal:
                return f"menos {integer} ponto {decimal} por cento"
        return f"menos {number} por cento"

    text = re.sub(r"(?<!\w)-\s*(\d[\d\.,]*)\s*%", percent_replacer, text)
    return text


def _normalize_numeric_token_for_tts(number: str) -> str:
    token = str(number or "").strip()
    if not token:
        return token
    if "," in token:
        token = token.replace(".", "")
        integer, decimal = token.split(",", 1)
        return f"{integer} vírgula {decimal}"
    if "." in token:
        integer, decimal = token.split(".", 1)
        return f"{integer} ponto {decimal}"
    return token


def _expand_currency_tts_patterns(text: str) -> str:
    def scaled_currency_replacer(match: re.Match) -> str:
        number = _normalize_numeric_token_for_tts(match.group(1))
        scale = str(match.group(2) or "").strip()
        return f"{number} {scale} de reais"

    text = re.sub(
        r"R\$\s*([-+]?\d+(?:[.,]\d+)?)\s*((?:bilh|milh)\w+|mil)\b",
        scaled_currency_replacer,
        text,
        flags=re.IGNORECASE,
    )

    def currency_replacer(match: re.Match) -> str:
        number = _normalize_numeric_token_for_tts(match.group(1))
        return f"{number} reais"

    return re.sub(r"R\$\s*([-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})?)", currency_replacer, text, flags=re.IGNORECASE)


def _expand_percent_tts_patterns(text: str) -> str:
    def percent_replacer(match: re.Match) -> str:
        number = _normalize_numeric_token_for_tts(match.group(1))
        return f"{number} por cento"

    return re.sub(r"(?<![\w-])(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+\.\d+)\s*%", percent_replacer, text)


def _expand_general_decimal_tts_patterns(text: str) -> str:
    def number_replacer(match: re.Match) -> str:
        token = match.group(1)
        return _normalize_numeric_token_for_tts(token)

    return re.sub(r"(?<![\w])(\d{1,3}(?:\.\d{3})*(?:,\d+)|\d+\.\d+)(?![\w%])", number_replacer, text)


def _expand_ticker_for_tts(text: str) -> str:
    letter_map = {
        "A": "á",
        "B": "bê",
        "C": "cê",
        "D": "dê",
        "E": "é",
        "F": "éfe",
        "G": "gê",
        "H": "agá",
        "I": "i",
        "J": "jóta",
        "K": "cá",
        "L": "éle",
        "M": "ême",
        "N": "êne",
        "O": "ó",
        "P": "pê",
        "Q": "quê",
        "R": "erre",
        "S": "ésse",
        "T": "tê",
        "U": "u",
        "V": "vê",
        "W": "dáblio",
        "X": "xis",
        "Y": "ípsilon",
        "Z": "zê",
    }

    def replacer(match: re.Match) -> str:
        letters = match.group(1).upper()
        digits = match.group(2)
        spoken_letters = " ".join(letter_map.get(letter, letter.lower()) for letter in letters)
        spoken_digits = " ".join(_number_to_pt(int(digit)) for digit in digits)
        return f"{spoken_letters} {spoken_digits}".strip()

    return re.sub(r"\b([A-Z]{4})(\d{1,2})\b", replacer, text)


def _restore_common_ptbr_accents(text: str) -> str:
    replacements = {
        "pagina": "página",
        "paginas": "páginas",
        "visao": "visão",
        "acoes": "ações",
        "acao": "ação",
        "rapida": "rápida",
        "rapido": "rápido",
        "repositorio": "repositório",
        "repositorios": "repositórios",
        "conteudo": "conteúdo",
        "conteudos": "conteúdos",
        "inteligencia": "inteligência",
        "computacao": "computação",
        "automacao": "automação",
        "camera": "câmera",
        "cameras": "câmeras",
        "videoaula": "vídeoaula",
        "musica": "música",
        "musicas": "músicas",
        "video": "vídeo",
        "videos": "vídeos",
        "audio": "áudio",
        "audios": "áudios",
        "traducao": "tradução",
        "informacao": "informação",
        "informacoes": "informações",
        "selecao": "seleção",
        "selecoes": "seleções",
        "opcao": "opção",
        "opcoes": "opções",
        "proxima": "próxima",
        "proximo": "próximo",
        "numero": "número",
        "numeros": "números",
        "navegacao": "navegação",
        "sintese": "síntese",
        "configuracao": "configuração",
        "configuracoes": "configurações",
        "precisao": "precisão",
        "ingles": "inglês",
        "classificacao": "classificação",
        "explicacao": "explicação",
        "nao": "não",
        "voce": "você",
        "voces": "vocês",
        "util": "útil",
        "uteis": "úteis",
        "alem": "além",
        "comecar": "começar",
        "comeco": "começo",
        "comeca": "começa",
        "comecou": "começou",
        "disposicao": "disposição",
        "instrucao": "instrução",
        "instrucoes": "instruções",
        "patrimonio": "patrimônio",
        "politica": "política",
        "politicas": "políticas",
        "cambio": "câmbio",
        "criterios": "critérios",
        "preferencia": "preferência",
        "preferencias": "preferências",
        "cotacoes": "cotações",
        "relatorio": "relatório",
        "relatorios": "relatórios",
        "especifico": "específico",
        "especifica": "específica",
    }

    replacements.update(
        {
            "avaliacao": "avaliação",
            "comparacao": "comparação",
            "comparacoes": "comparações",
            "variacao": "variação",
            "variacoes": "variações",
            "cotacao": "cotação",
            "cotacoes": "cotações",
            "geracao": "geração",
            "evolucao": "evolução",
            "operacao": "operação",
            "operacoes": "operações",
            "direcao": "direção",
            "funcao": "função",
            "funcoes": "funções",
            "atencao": "atenção",
            "situacao": "situação",
            "condicao": "condição",
            "condicoes": "condições",
            "criterio": "critério",
            "memoria": "memória",
            "historico": "histórico",
            "analise": "análise",
            "tecnico": "técnico",
            "tecnica": "técnica",
            "tecnicas": "técnicas",
            "pratico": "prático",
            "pratica": "prática",
            "estrategia": "estratégia",
            "estrategias": "estratégias",
            "logica": "lógica",
            "topico": "tópico",
            "topicos": "tópicos",
            "critico": "crítico",
            "critica": "crítica",
            "projecao": "projeção",
            "projecoes": "projeções",
        }
    )

    for source, target in replacements.items():
        text = re.sub(rf"\b{source}\b", target, text, flags=re.IGNORECASE)

    return text


def _apply_pronunciation_map(text: str, mapping: dict[str, str]) -> str:
    ordered_items = sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True)
    for source, target in ordered_items:
        text = re.sub(rf"\b{re.escape(source)}\b", target, text)
    return text


def _massage_ptbr_pronunciation(text: str) -> str:
    phrase_replacements = {
        "Pronto para trabalhar.": "Pronto para começar.",
        "pronto para trabalhar.": "pronto para começar.",
        "Vamos fazer esse computador trabalhar.": "Vamos colocar esse computador em movimento.",
        "vamos fazer esse computador trabalhar.": "vamos colocar esse computador em movimento.",
    }
    for source, target in phrase_replacements.items():
        text = text.replace(source, target)

    return text


def prepare_tts_text(text: str, custom_pronunciations: dict[str, str] | None = None) -> str:
    prepared = _repair_mojibake(_normalize_tts_tech_terms(text))
    prepared = _expand_negative_tts_patterns(prepared)
    prepared = _expand_currency_tts_patterns(prepared)
    prepared = _expand_percent_tts_patterns(prepared)
    prepared = _expand_general_decimal_tts_patterns(prepared)
    prepared = re.sub(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", _expand_date_expression, prepared)
    prepared = _normalize_tts_punctuation(prepared)
    prepared = _expand_tts_reading_patterns(prepared)
    prepared = _restore_common_ptbr_accents(prepared)
    prepared = _massage_ptbr_pronunciation(prepared)
    prepared = _apply_abbreviation_rules(prepared)
    prepared = _apply_abbreviation_heuristics(prepared)
    prepared = _apply_pronunciation_map(prepared, _BUILTIN_TTS_PRONUNCIATIONS)
    prepared = _apply_pronunciation_map(prepared, custom_pronunciations or {})
    prepared = re.sub(r"\bv[ęê] ésse côde\b", "vê ésse côde", prepared, flags=re.IGNORECASE)
    prepared = re.sub(r"\bvê ésse code\b", "vê ésse côde", prepared, flags=re.IGNORECASE)

    return _repair_mojibake(prepared)
