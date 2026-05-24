from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


def normalize_text_for_match(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def screen_lines_quality(lines) -> int:
    if not lines:
        return 0

    product_words = {
        "celular", "smartphone", "notebook", "iphone", "galaxy", "moto", "motorola",
        "xiaomi", "redmi", "samsung", "realme", "oppo", "lavadora", "lava", "relogio",
        "tv", "monitor", "fogao", "geladeira",
    }
    noise_terms = {
        "sem juros", "vez de r$", "vezes de r$", "frete", "cupom", "celulares",
        "eletrodomesticos", "tipo de", "comprar agora",
    }

    score = 0
    for line in lines:
        normalized = normalize_text_for_match(line)
        if not normalized:
            continue

        has_letters = bool(re.search(r"[a-zA-Z\u00C0-\u017F]", line))
        has_digits = bool(re.search(r"\d", line))
        if has_letters:
            score += 5
        if len(normalized.split()) >= 4:
            score += 2
        if any(word in normalized for word in product_words):
            score += 6
        if re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()):
            score -= 2
        if any(term in normalized for term in noise_terms):
            score -= 4
        if has_digits and not has_letters:
            score -= 8

    return score + len(lines)


def detect_screen_category(lines, page_url: str = "", page_title: str = "") -> str:
    normalized_blob = " ".join(normalize_text_for_match(line) for line in lines if line)
    parsed = urlparse(page_url or "")
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    title_blob = normalize_text_for_match(page_title)

    if "github.com" in host:
        return "repositorio github"

    if ("youtube.com" in host or "youtu.be" in host) and ("/watch" in path or "youtube" in title_blob):
        return "video youtube"

    if (
        "investidor10.com.br" in host
        or any(
            token in title_blob
            for token in ("investidor10", "patrimonio", "valor investido", "rentabilidade", "proventos", "dividendos")
        )
    ):
        return "financas"

    if any(
        token in host
        for token in ("poder360", "g1.globo", "cnnbrasil", "uol.com.br", "folha.uol", "estadao", "bbc.com")
    ) or any(token in title_blob for token in ("noticia", "jornal", "reportagem", "politica", "internacional")):
        return "noticia"

    category_patterns = [
        ("repositorio github", ("repository navigation", "pull requests", "issues", "actions", "discussions", "github")),
        ("video youtube", ("up next", "youtube", "inscrito", "inscrever se", "comentarios")),
        ("financas", ("investidor10", "patrimonio", "valor investido", "rentabilidade", "proventos", "dividendos", "saldo", "preco medio")),
        ("noticia", ("noticia", "jornal", "reportagem", "publicado", "atualizado", "leia mais")),
        ("smartphones", ("smartphone", "celular", "iphone", "galaxy", "redmi", "motorola", "oppo", "realme")),
        ("notebooks", ("notebook", "ideapad", "vivobook", "aspire", "inspiron", "thinkpad", "macbook")),
        ("lavadoras", ("lavadora", "lava loucas", "lava-loucas", "lava e seca", "samsung ww", "electrolux")),
        ("televisores", ("smart tv", "televis", "polegadas", "suporte articulado", "monitor")),
        ("relogios", ("relogio", "relogios", "watch", "smartwatch", "amazfit", "mi band")),
    ]

    for category, patterns in category_patterns:
        if any(pattern in normalized_blob for pattern in patterns):
            return category

    return ""


def content_showcase(lines, limit: int = 3) -> list[str]:
    showcase = []
    for line in lines:
        compact = re.sub(r"\s+", " ", line).strip()
        if len(compact) > 110:
            compact = compact[:107].rstrip() + "..."
        if compact and compact not in showcase:
            showcase.append(compact)
        if len(showcase) >= limit:
            break
    return showcase


def extract_finance_focus_lines(lines, limit: int = 5) -> list[str]:
    prioritized = []
    finance_tokens = (
        "patrimonio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
        "dividendos",
        "saldo",
        "carteira",
        "preco medio",
        "lucro",
        "prejuizo",
        "aporte",
        "acao",
        "acoes",
        "fii",
        "ticker",
        "cotacao",
    )

    for index, line in enumerate(lines):
        compact = re.sub(r"\s+", " ", line).strip()
        normalized = normalize_text_for_match(compact)
        if not compact or len(compact) < 3:
            continue
        if normalized.isdigit():
            continue
        if re.match(r"^https?://", compact, flags=re.IGNORECASE):
            continue

        score = 0
        if any(token in normalized for token in finance_tokens):
            score += 6
        if re.search(r"r\$\s*[\d\.\,]+", compact, flags=re.IGNORECASE):
            score += 5
        if "%" in compact:
            score += 3
        if len(normalized.split()) >= 2:
            score += 1
        if compact in {"0", "0,0", "0.0"}:
            score -= 6

        prioritized.append((score, index, compact))

    prioritized.sort(key=lambda item: (-item[0], item[1]))
    chosen = []
    for score, _index, compact in prioritized:
        if score < 2 and chosen:
            continue
        if compact not in chosen:
            chosen.append(compact)
        if len(chosen) >= limit:
            break

    return chosen


def extract_finance_metrics(lines, limit: int = 7) -> list[str]:
    labels = (
        "patrimonio",
        "patrimonio total",
        "valor investido",
        "valor atual",
        "saldo",
        "rentabilidade",
        "lucro",
        "prejuizo",
        "proventos",
        "dividendos",
        "aporte",
        "preco medio",
        "cotacao",
        "carteira",
        "total",
    )
    value_re = re.compile(r"(?:r\$\s*)?[-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})|[-+]?\d+(?:,\d+)?\s*%", re.IGNORECASE)
    candidates = []
    seen = set()

    compact_lines = [re.sub(r"\s+", " ", line or "").strip() for line in lines if str(line or "").strip()]
    for index, line in enumerate(compact_lines):
        normalized = normalize_text_for_match(line)
        if not normalized:
            continue
        if "http" in normalized or "cookie" in normalized or "direitos reservados" in normalized:
            continue

        has_label = any(label in normalized for label in labels)
        values = value_re.findall(line)
        score = 0
        metric = ""

        if has_label and values:
            score = 10
            metric = line
        elif has_label and index + 1 < len(compact_lines):
            next_line = compact_lines[index + 1]
            next_values = value_re.findall(next_line)
            if next_values:
                score = 9
                metric = f"{line}: {next_line}"
        elif values and index > 0:
            prev_line = compact_lines[index - 1]
            prev_norm = normalize_text_for_match(prev_line)
            if any(label in prev_norm for label in labels):
                score = 8
                metric = f"{prev_line}: {line}"

        if not metric:
            continue

        normalized_metric = normalize_text_for_match(metric)
        if normalized_metric in seen:
            continue

        if len(metric) > 160:
            metric = metric[:157].rstrip() + "..."
        candidates.append((score, index, metric))
        seen.add(normalized_metric)

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [metric for _score, _index, metric in candidates[:limit]]


def merge_screen_lines(primary_lines, secondary_lines, limit: int = 12) -> list[str]:
    merged = []
    seen = set()

    for group in (primary_lines or [], secondary_lines or []):
        for source in group:
            compact = re.sub(r"\s+", " ", source or "").strip()
            normalized = normalize_text_for_match(compact)
            if not compact or not normalized or normalized in seen:
                continue
            merged.append(compact)
            seen.add(normalized)
            if len(merged) >= limit:
                return merged

    return merged


def trim_detail_text(text: str, max_length: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 3].rstrip() + "..."
