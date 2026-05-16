import re
from typing import Callable


VALUE_RE = re.compile(
    r"[-+]?\d+(?:,\d+)?\s*%|(?:r\$\s*)?[-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})",
    re.IGNORECASE,
)

LABEL_HINTS = {
    "patrimonio": ("patrimonio total", "patrimonio", "patrimônio total", "patrimônio"),
    "valor investido": ("valor investido",),
    "valor atual": ("valor atual",),
    "rentabilidade": ("rentabilidade",),
    "proventos": ("proventos", "dividendos"),
    "saldo": ("saldo",),
    "lucro": ("lucro",),
    "prejuizo": ("prejuizo", "prejuízo"),
    "aporte": ("aporte",),
    "preco medio": ("preco medio", "preço médio", "preço medio"),
    "cotacao": ("cotacao", "cotação"),
    "variacao": ("variacao", "variação", "alta", "queda", "valorizacao", "desvalorizacao"),
}


def snapshot_blob(snapshot: dict) -> str:
    return " ".join(
        [
            str(snapshot.get("page_title", "")),
            str(snapshot.get("summary", "")),
            *[str(item) for item in (snapshot.get("metrics") or [])],
            *[str(item) for item in (snapshot.get("lines") or [])],
        ]
    )


def extract_metric_map(metrics: list[str] | None, lines: list[str] | None, *, normalize: Callable[[str], str]) -> dict[str, str]:
    metric_map: dict[str, str] = {}
    candidates = list(metrics or []) + list(lines or [])

    for raw_line in candidates:
        line = re.sub(r"\s+", " ", str(raw_line or "")).strip()
        if not line:
            continue
        normalized = normalize(line)
        values = VALUE_RE.findall(line)
        if not values:
            continue

        for canonical, hints in LABEL_HINTS.items():
            if canonical in metric_map:
                continue
            if any(hint in normalized for hint in hints):
                metric_map[canonical] = values[0].strip()
                break

    return metric_map


def extract_ticker(snapshot: dict) -> str:
    match = re.search(r"\b([A-Z]{4}\d{1,2})\b", snapshot_blob(snapshot))
    return match.group(1).upper() if match else ""


def extract_question_ticker(question: str) -> str:
    text = str(question or "")
    match = re.search(r"\b([A-Za-z]{4,5}\d{1,2})\b", text)
    if match:
        return match.group(1).upper()
    for symbol in ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE"):
        if re.search(rf"\b{symbol}(?:[-/](?:BRL|USD|USDT))?\b", text, flags=re.I):
            return symbol
    return ""


def extract_snapshot_direction(snapshot: dict, *, normalize: Callable[[str], str]) -> str:
    normalized = normalize(snapshot_blob(snapshot))
    raw_blob = snapshot_blob(snapshot)

    if "0,00%" in raw_blob or "0 00 %" in normalized:
        return "sem movimento relevante no recorte visível"
    if any(term in normalized for term in {"arrow upward", "alta", "subindo", "valorizacao"}):
        return "em alta no recorte visível"
    if any(term in normalized for term in {"arrow downward", "queda", "caindo", "desvalorizacao"}):
        return "em queda no recorte visível"
    return ""
