from __future__ import annotations

import re

from tools.browser_screen_analysis import (
    detect_screen_category,
    extract_finance_focus_lines,
    normalize_text_for_match,
)
from tools.browser_screen_narrative import relevance_terms_from_context

PRODUCT_WORDS = {
    "celular",
    "smartphone",
    "notebook",
    "iphone",
    "galaxy",
    "moto",
    "realme",
    "xiaomi",
    "redmi",
    "samsung",
    "motorola",
    "lenovo",
    "acer",
    "dell",
    "positivo",
    "tablet",
}


def strip_gallery_suffix(text: str) -> str:
    cleaned = re.sub(
        r"\s+(?:imagen|imagem|image)\s*-\s*\d+\s*/\s*\d+\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", cleaned).strip(" -")


def useful_page_text_lines(text: str, limit: int = 10, page_url: str = "", page_title: str = ""):
    ignore_patterns = (
        "javascript",
        "cookie",
        "politica de privacidade",
        "termos de uso",
        "menu",
        "entrar",
        "minha conta",
        "sacola",
        "carrinho",
        "buscar",
        "pesquisar",
    )
    finance_category = detect_screen_category([], page_url=page_url, page_title=page_title) == "financas"
    finance_tokens = {
        "investidor10",
        "carteira",
        "wallet",
        "patrimonio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
        "dividendos",
        "saldo",
        "preco medio",
        "lucro",
        "prejuizo",
        "aporte",
        "ticker",
        "fii",
        "cotacao",
    }
    lines = []
    seen = set()

    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()

        if len(line) < 4 or len(line) > 120:
            continue

        normalized = normalize_text_for_match(line)
        if not normalized or normalized in seen:
            continue

        if re.match(r"^https?://", line, flags=re.IGNORECASE):
            continue
        if "http://" in line.lower() or "https://" in line.lower():
            continue

        if normalized.isdigit():
            continue

        if re.match(r"^(?:r\$\s*)?[\d\.\,]+$", line.lower()):
            continue

        if re.match(r"^\d+x\s+de\s+r\$", line.lower()):
            continue

        if any(pattern in normalized for pattern in ignore_patterns):
            continue
        if "direitos reservados" in normalized or "copyright" in normalized or "leia mais no texto original" in normalized:
            continue

        score = 0
        if re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()):
            score += 80
        if any(word in normalized for word in {"celular", "notebook", "smartphone", "iphone", "samsung", "motorola", "xiaomi", "comprar", "frete", "oferta"}):
            score += 50
        if finance_category and any(token in normalized for token in finance_tokens):
            score += 90
        if finance_category and "%" in line:
            score += 40
        score += max(0, 60 - len(lines))
        lines.append((score, line))
        seen.add(normalized)

    lines.sort(key=lambda item: item[0], reverse=True)
    return [line for _score, line in lines[:limit]]


def rank_page_text_lines(text: str, limit: int = 10, page_url: str = "", page_title: str = ""):
    ignore_patterns = (
        "javascript",
        "cookie",
        "politica de privacidade",
        "politica de cookies",
        "termos de uso",
        "menu",
        "entrar",
        "minha conta",
        "sacola",
        "carrinho",
        "buscar",
        "pesquisar",
        "departamentos",
        "atendimento",
        "central de",
        "compre pelo",
        "formas de pagamento",
        "pular navegacao",
        "imagem do avatar",
        "avatar",
        "login",
        "memoria ram",
        "cupom",
        "sem juros",
        "cashback",
        "desconto",
        "direitos reservados",
        "copyright",
        "leia mais no texto original",
    )
    category_noise = {
        "celulares",
        "celular",
        "a celular",
        "celulares e smartphones",
        "samsung",
        "motorola",
        "xiaomi",
        "apple",
        "iphone",
    }
    spec_words = {
        "gb",
        "ram",
        "mah",
        "tela",
        "hz",
        "nfc",
        "ip54",
        "resistencia",
        "camera",
        "processador",
    }
    finance_tokens = {
        "investidor10",
        "carteira",
        "wallet",
        "patrimonio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
        "dividendos",
        "saldo",
        "preco medio",
        "lucro",
        "prejuizo",
        "aporte",
        "ticker",
        "fii",
        "acao",
        "acoes",
        "cotacao",
    }
    page_category = detect_screen_category([], page_url=page_url, page_title=page_title)
    finance_category = page_category == "financas"
    priority_category = page_category in {"repositorio github", "video youtube", "financas", "noticia"}
    relevance_terms = relevance_terms_from_context(page_url=page_url, page_title=page_title)
    candidates = []
    seen = set()

    for index, raw_line in enumerate((text or "").splitlines()):
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = strip_gallery_suffix(line)

        if len(line) < 4 or len(line) > 180:
            continue

        normalized = normalize_text_for_match(line)
        if not normalized or normalized in seen:
            continue

        if normalized.isdigit():
            continue

        if re.match(r"^https?://", line, flags=re.IGNORECASE):
            continue

        words = normalized.split()
        has_price = bool(re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()))
        price_only = bool(re.match(r"^r\$\s*[\d\.\,]+$", line.lower()))
        looks_like_slug = line.count("-") >= 2 and " " not in line.strip()
        has_product_word = any(word in PRODUCT_WORDS for word in words)
        has_spec_word = any(word in spec_words for word in words)
        has_finance_word = any(token in normalized for token in finance_tokens)
        has_percent = "%" in line
        has_currency = bool(re.search(r"r\$\s*[\d\.\,]+", line, flags=re.IGNORECASE))
        has_relevance_word = any(term in normalized for term in relevance_terms)

        if looks_like_slug:
            continue

        if price_only and not finance_category:
            continue

        if normalized in category_noise:
            continue

        if len(words) <= 2 and not has_price and not finance_category:
            continue

        if len(words) <= 3 and has_spec_word and not has_product_word and not has_price and not finance_category:
            continue

        if any(pattern in normalized for pattern in ignore_patterns):
            continue

        if "lei" in normalized and "9 610 98" in normalized:
            continue

        if re.match(r"^\d+x\s+de\s+r\$", line.lower()) and not finance_category:
            continue

        if finance_category:
            score = 0
            if has_finance_word:
                score += 8
            if has_currency:
                score += 5
            if has_percent:
                score += 4
            if len(words) >= 2:
                score += 1
            if normalized in {"0", "0,0", "0.0"}:
                score -= 8
            if score < 2:
                continue
        else:
            score = 0
            if has_product_word:
                score += 6
            if has_spec_word:
                score += 2
            if has_relevance_word:
                score += 7
            if len(words) >= 3:
                score += 2
            if len(words) >= 6:
                score += 1
            if has_price:
                score += 1
            if len(words) <= 2 and not has_relevance_word and not has_product_word:
                score -= 5
            if page_category == "repositorio github":
                if any(token in normalized for token in ("readme", "about", "sobre", "descricao", "description", "instalacao", "installation", "usage", "features", "projeto", "project")):
                    score += 9
                if any(token in normalized for token in ("git clone", "repository navigation", "pull requests", "issues", "actions")):
                    score -= 8
            if page_category == "video youtube":
                if any(token in normalized for token in ("inscrever", "up next", "compartilhar", "comentarios")):
                    score -= 5
                if len(words) >= 4:
                    score += 3
            if page_category == "noticia":
                if len(words) >= 8:
                    score += 6
                if any(token in normalized for token in ("publicado", "atualizado", "segundo", "afirma", "disse", "jornal", "governo", "negociacao")):
                    score += 4
                if any(token in normalized for token in ("todos os direitos", "lei", "publicacao redistribuicao")):
                    score -= 10
            if score < 3:
                continue

        if len(line) > 145:
            line = line[:142].rstrip() + "..."

        candidates.append((score, index, line))
        seen.add(normalized)

        if len(candidates) >= max(limit * 6, 60):
            break

    if finance_category:
        ranked = [line for _score, _index, line in sorted(candidates, key=lambda item: (-item[0], item[1]))]
        return extract_finance_focus_lines(ranked, limit=limit)

    if priority_category:
        return [
            line
            for _score, _index, line in sorted(candidates, key=lambda item: (-item[0], item[1]))[:limit]
        ]

    return [line for _score, _index, line in sorted(candidates, key=lambda item: item[1])[:limit]]


def selected_text_items(text: str, limit: int = 10):
    noise_patterns = (
        "memoria ram",
        "cupom",
        "sem juros",
        "frete",
        "favorito",
        "avaliacao",
        "avaliacoes",
        "patrocinado",
    )
    raw_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in (text or "").splitlines()
    ]
    raw_lines = [line for line in raw_lines if line]
    items = []
    seen = set()

    for index, line in enumerate(raw_lines):
        line = strip_gallery_suffix(line)
        normalized = normalize_text_for_match(line)
        words = normalized.split()

        if not normalized or normalized in seen:
            continue

        if any(pattern in normalized for pattern in noise_patterns):
            continue

        if line.count("-") >= 2 and " " not in line:
            continue

        if not any(word in PRODUCT_WORDS for word in words):
            continue

        item = line
        if "r$" not in normalized:
            for extra in raw_lines[index + 1:index + 5]:
                if re.search(r"r\$\s*[\d\.\,]+", extra.lower()) and not re.match(r"^\d+x\s+de\s+r\$", extra.lower()):
                    item = f"{item} - {extra}"
                    break

        if len(item) > 180:
            item = item[:177].rstrip() + "..."

        items.append(item)
        seen.add(normalized)

        if len(items) >= limit:
            break

    if items:
        return items

    return rank_page_text_lines(text, limit=limit)
