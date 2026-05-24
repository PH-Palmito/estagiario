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
    if not any(marker in text for marker in ("Ã", "Â", "â")):
        return text
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text


_NUMBER_WORDS = {
    0: "zero",
    1: "um",
    2: "dois",
    3: "trÃªs",
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
    3: "marÃ§o",
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
    "A": "Ã¡",
    "B": "bÃª",
    "C": "cÃª",
    "D": "dÃª",
    "E": "Ãª",
    "F": "Ã©fe",
    "G": "gÃª",
    "H": "agÃ¡",
    "I": "i",
    "J": "jÃ³ta",
    "K": "cÃ¡",
    "L": "Ã©le",
    "M": "Ãªme",
    "N": "Ãªne",
    "O": "Ã³",
    "P": "pÃª",
    "Q": "quÃª",
    "R": "Ã©rre",
    "S": "Ã©sse",
    "T": "tÃª",
    "U": "u",
    "V": "vÃª",
    "W": "dÃ¡blio",
    "X": "xis",
    "Y": "Ã­psilon",
    "Z": "zÃª",
}

_TTS_ABBREVIATION_RULES = {
    "mAh": {"mode": "expand", "value": "miliampere hora"},
    "MAh": {"mode": "expand", "value": "miliampere hora"},
    "mah": {"mode": "expand", "value": "miliampere hora"},
    "Wh": {"mode": "expand", "value": "watt hora"},
    "kWh": {"mode": "expand", "value": "quilo watt hora"},
    "km": {"mode": "expand", "value": "quilÃ´metro"},
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
    "GitHub": "guÃ­ti rÃ£b",
    "github": "guÃ­ti rÃ£b",
    "YouTube": "iÃºtubi",
    "youtube": "iÃºtubi",
    "Steam": "stim",
    "steam": "stim",
    "Chrome": "crÃ´um",
    "chrome": "crÃ´um",
    "Python": "paithon",
    "python": "paithon",
    "Google": "gÃºgou",
    "google": "gÃºgou",
    "Colab": "cÃ³lab",
    "colab": "cÃ³lab",
    "Android": "ÃªndrÃ³id",
    "android": "ÃªndrÃ³id",
    "Android Studio": "ÃªndrÃ³id stÃºdio",
    "android studio": "ÃªndrÃ³id stÃºdio",
    "PowerShell": "pÃ¡uer shel",
    "powershell": "pÃ¡uer shel",
    "OpenAI": "Ã´upen Ãªi Ã¡i",
    "openai": "Ã´upen Ãªi Ã¡i",
    "Wi-Fi": "uÃ¡i fai",
    "wi-fi": "uÃ¡i fai",
    "Wi Fi": "uÃ¡i fai",
    "wi fi": "uÃ¡i fai",
    "WiFi": "uÃ¡i fai",
    "wifi": "uÃ¡i fai",
    "Bluetooth": "blutÃºfi",
    "bluetooth": "blutÃºfi",
    "Mercado Livre": "mercÃ¡do lÃ­vre",
    "mercado livre": "mercÃ¡do lÃ­vre",
    "Magalu": "magalÃº",
    "magalu": "magalÃº",
    "Spotify": "ispÃ³tifai",
    "spotify": "ispÃ³tifai",
    "VS Code": "vÃª Ã©sse cÃ´de",
    "VSCode": "vÃª Ã©sse cÃ´de",
    "vscode": "vÃª Ã©sse cÃ´de",
    "Whisper": "uÃ­sper",
    "whisper": "uÃ­sper",
    "Piper": "paiper",
    "piper": "paiper",
    "Ollama": "olÃ¢ma",
    "ollama": "olÃ¢ma",
    "Mobile": "mÃ´bail",
    "mobile": "mÃ´bail",
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
    return f"{_number_to_pt(value)} {unit} CÃ©lsius"


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
    text = re.sub(r"\s*[â€“â€”-]\s*", ", ", text)
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
        r"\b(\d{1,3})\s*(?:Â°\s*C|graus?\s+Celsius|graus?\s+celsius)\b",
        _expand_temperature_expression,
        text,
    )
    text = re.sub(r"\b(\d{1,3})\s+graus\b", _expand_degrees_expression, text)
    text = re.sub(r"\b(\d{1,5})\s*mAh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} miliampere hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*Wh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} watt hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*kWh\b", lambda m: f"{_number_to_pt(int(m.group(1)))} quilo watt hora", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,5})\s*(MB|GB|TB)\b", _expand_storage_expression, text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,4})\s*km\b", lambda m: f"{_number_to_pt(int(m.group(1)))} quilÃ´metros", text, flags=re.IGNORECASE)
    return text


def _expand_negative_tts_patterns(text: str) -> str:
    text = re.sub(r"(?<!\w)-\s*(R\$\s*\d[\d\.,]*)", r"menos \1", text)

    def percent_replacer(match: re.Match) -> str:
        number = str(match.group(1) or "").strip()
        if "," in number:
            integer, decimal = number.split(",", 1)
            if decimal:
                return f"menos {integer} vÃ­rgula {decimal} por cento"
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
        return f"{integer} vÃ­rgula {decimal}"
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
        "A": "Ã¡",
        "B": "bÃª",
        "C": "cÃª",
        "D": "dÃª",
        "E": "Ã©",
        "F": "Ã©fe",
        "G": "gÃª",
        "H": "agÃ¡",
        "I": "i",
        "J": "jÃ³ta",
        "K": "cÃ¡",
        "L": "Ã©le",
        "M": "Ãªme",
        "N": "Ãªne",
        "O": "Ã³",
        "P": "pÃª",
        "Q": "quÃª",
        "R": "erre",
        "S": "Ã©sse",
        "T": "tÃª",
        "U": "u",
        "V": "vÃª",
        "W": "dÃ¡blio",
        "X": "xis",
        "Y": "Ã­psilon",
        "Z": "zÃª",
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
        "pagina": "pÃ¡gina",
        "paginas": "pÃ¡ginas",
        "visao": "visÃ£o",
        "acoes": "aÃ§Ãµes",
        "acao": "aÃ§Ã£o",
        "rapida": "rÃ¡pida",
        "rapido": "rÃ¡pido",
        "repositorio": "repositÃ³rio",
        "repositorios": "repositÃ³rios",
        "conteudo": "conteÃºdo",
        "conteudos": "conteÃºdos",
        "inteligencia": "inteligÃªncia",
        "computacao": "computaÃ§Ã£o",
        "automacao": "automaÃ§Ã£o",
        "camera": "cÃ¢mera",
        "cameras": "cÃ¢meras",
        "videoaula": "vÃ­deoaula",
        "musica": "mÃºsica",
        "musicas": "mÃºsicas",
        "video": "vÃ­deo",
        "videos": "vÃ­deos",
        "audio": "Ã¡udio",
        "audios": "Ã¡udios",
        "traducao": "traduÃ§Ã£o",
        "informacao": "informaÃ§Ã£o",
        "informacoes": "informaÃ§Ãµes",
        "selecao": "seleÃ§Ã£o",
        "selecoes": "seleÃ§Ãµes",
        "opcao": "opÃ§Ã£o",
        "opcoes": "opÃ§Ãµes",
        "proxima": "prÃ³xima",
        "proximo": "prÃ³ximo",
        "numero": "nÃºmero",
        "numeros": "nÃºmeros",
        "navegacao": "navegaÃ§Ã£o",
        "sintese": "sÃ­ntese",
        "configuracao": "configuraÃ§Ã£o",
        "configuracoes": "configuraÃ§Ãµes",
        "precisao": "precisÃ£o",
        "ingles": "inglÃªs",
        "classificacao": "classificaÃ§Ã£o",
        "explicacao": "explicaÃ§Ã£o",
        "nao": "nÃ£o",
        "voce": "vocÃª",
        "voces": "vocÃªs",
        "util": "Ãºtil",
        "uteis": "Ãºteis",
        "alem": "alÃ©m",
        "comecar": "comeÃ§ar",
        "comeco": "comeÃ§o",
        "comeca": "comeÃ§a",
        "comecou": "comeÃ§ou",
        "disposicao": "disposiÃ§Ã£o",
        "instrucao": "instruÃ§Ã£o",
        "instrucoes": "instruÃ§Ãµes",
        "patrimonio": "patrimÃ´nio",
        "politica": "polÃ­tica",
        "politicas": "polÃ­ticas",
        "cambio": "cÃ¢mbio",
        "criterios": "critÃ©rios",
        "preferencia": "preferÃªncia",
        "preferencias": "preferÃªncias",
        "cotacoes": "cotaÃ§Ãµes",
        "relatorio": "relatÃ³rio",
        "relatorios": "relatÃ³rios",
        "especifico": "especÃ­fico",
        "especifica": "especÃ­fica",
    }

    replacements.update(
        {
            "avaliacao": "avaliaÃ§Ã£o",
            "comparacao": "comparaÃ§Ã£o",
            "comparacoes": "comparaÃ§Ãµes",
            "variacao": "variaÃ§Ã£o",
            "variacoes": "variaÃ§Ãµes",
            "cotacao": "cotaÃ§Ã£o",
            "cotacoes": "cotaÃ§Ãµes",
            "geracao": "geraÃ§Ã£o",
            "evolucao": "evoluÃ§Ã£o",
            "operacao": "operaÃ§Ã£o",
            "operacoes": "operaÃ§Ãµes",
            "direcao": "direÃ§Ã£o",
            "funcao": "funÃ§Ã£o",
            "funcoes": "funÃ§Ãµes",
            "atencao": "atenÃ§Ã£o",
            "situacao": "situaÃ§Ã£o",
            "condicao": "condiÃ§Ã£o",
            "condicoes": "condiÃ§Ãµes",
            "criterio": "critÃ©rio",
            "memoria": "memÃ³ria",
            "historico": "histÃ³rico",
            "analise": "anÃ¡lise",
            "tecnico": "tÃ©cnico",
            "tecnica": "tÃ©cnica",
            "tecnicas": "tÃ©cnicas",
            "pratico": "prÃ¡tico",
            "pratica": "prÃ¡tica",
            "estrategia": "estratÃ©gia",
            "estrategias": "estratÃ©gias",
            "logica": "lÃ³gica",
            "topico": "tÃ³pico",
            "topicos": "tÃ³picos",
            "critico": "crÃ­tico",
            "critica": "crÃ­tica",
            "projecao": "projeÃ§Ã£o",
            "projecoes": "projeÃ§Ãµes",
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
        "Pronto para trabalhar.": "Pronto para comeÃ§ar.",
        "pronto para trabalhar.": "pronto para comeÃ§ar.",
        "Vamos fazer esse computador trabalhar.": "Vamos colocar esse computador em movimento.",
        "vamos fazer esse computador trabalhar.": "vamos colocar esse computador em movimento.",
    }
    for source, target in phrase_replacements.items():
        text = text.replace(source, target)

    return text


def prepare_tts_text(text: str, custom_pronunciations: dict[str, str] | None = None) -> str:
    prepared = _normalize_tts_tech_terms(text)
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
    prepared = re.sub(r"\bv[Ä™Ãª] Ã©sse cÃ´de\b", "vÃª Ã©sse cÃ´de", prepared, flags=re.IGNORECASE)
    prepared = re.sub(r"\bvÃª Ã©sse code\b", "vÃª Ã©sse cÃ´de", prepared, flags=re.IGNORECASE)

    return _repair_mojibake(prepared)
