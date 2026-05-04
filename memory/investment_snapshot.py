import json
import os
import re
import time
import unicodedata
from pathlib import Path

from config import GEMINI_API_KEY
from llm.gemini_client import ask_gemini_grounded_model
from memory.investment_strategy import calculate_auto_price_ceiling, get_asset_strategy, get_auto_ceiling_settings


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
INVESTMENT_SNAPSHOT_PATH = MEMORY_DIR / "investment_snapshot.json"

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


def _save_json(path: Path, payload: dict):
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or "").strip().lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = re.sub(r"[^\w\s%$.,:-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _format_timestamp(timestamp: float) -> str:
    if not timestamp:
        return "data desconhecida"
    return time.strftime("%d/%m/%Y às %H:%M", time.localtime(timestamp))


def _number_to_ptbr(value: int) -> str:
    units = {
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
    }
    if value in units:
        return units[value]
    if 20 < value < 60:
        base = (value // 10) * 10
        remainder = value % 10
        return f"{units[base]} e {units[remainder]}"
    return str(value)


def _format_timestamp_natural(timestamp: float) -> str:
    if not timestamp:
        return "em data não identificada"
    months = (
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    )
    struct = time.localtime(timestamp)
    day = _number_to_ptbr(struct.tm_mday)
    month = months[max(0, min(11, struct.tm_mon - 1))]
    hour = _number_to_ptbr(struct.tm_hour)
    minute = struct.tm_min
    if minute == 0:
        return f"em {day} de {month}, às {hour} horas"
    return f"em {day} de {month}, às {hour} horas e {_number_to_ptbr(minute)} minutos"


def _format_brl(value: float | None) -> str:
    if value is None:
        return ""
    formatted = f"{float(value):,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value: float | None, digits: int = 1) -> str:
    if value is None:
        return ""
    formatted = f"{float(value):,.{digits}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".") + "%"


def _snapshot_blob(snapshot: dict) -> str:
    return " ".join(
        [
            str(snapshot.get("page_title", "")),
            str(snapshot.get("summary", "")),
            *[str(item) for item in (snapshot.get("metrics") or [])],
            *[str(item) for item in (snapshot.get("lines") or [])],
        ]
    )


def _extract_metric_map(metrics: list[str] | None, lines: list[str] | None) -> dict[str, str]:
    metric_map: dict[str, str] = {}
    candidates = list(metrics or []) + list(lines or [])

    for raw_line in candidates:
        line = re.sub(r"\s+", " ", str(raw_line or "")).strip()
        if not line:
            continue
        normalized = _normalize(line)
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


def _extract_ticker(snapshot: dict) -> str:
    match = re.search(r"\b([A-Z]{4}\d{1,2})\b", _snapshot_blob(snapshot))
    return match.group(1).upper() if match else ""


def _extract_question_ticker(question: str) -> str:
    match = re.search(r"\b([A-Za-z]{4}\d{1,2})\b", str(question or ""))
    return match.group(1).upper() if match else ""


def _mentions_price_ceiling(normalized: str) -> bool:
    compact = normalized.replace(" ", "")
    return "teto" in normalized and ("preco" in compact or "pre o" in normalized or "preco teto" in normalized)


def _contains_investment_phrase(normalized: str, *patterns: str) -> bool:
    text = str(normalized or "")
    compact = text.replace(" ", "")
    for pattern in patterns:
        raw = str(pattern or "").strip().lower()
        if not raw:
            continue
        raw_compact = raw.replace(" ", "")
        if raw in text or raw_compact in compact:
            return True
    return False


def _extract_snapshot_direction(snapshot: dict) -> str:
    normalized = _normalize(_snapshot_blob(snapshot))
    raw_blob = _snapshot_blob(snapshot)

    if "0,00%" in raw_blob or "0 00 %" in normalized:
        return "sem movimento relevante no recorte visível"
    if any(term in normalized for term in {"arrow upward", "alta", "subindo", "valorizacao"}):
        return "em alta no recorte visível"
    if any(term in normalized for term in {"arrow downward", "queda", "caindo", "desvalorizacao"}):
        return "em queda no recorte visível"
    return ""


def _parse_currency_value(text: str) -> float | None:
    cleaned = str(text or "").strip().lower().replace("r$", "").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_percent_value(text: str) -> float | None:
    cleaned = str(text or "").strip().replace("%", "").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_current_price(snapshot: dict) -> float | None:
    metric_map = snapshot.get("metric_map") or {}
    direct = _parse_currency_value(metric_map.get("cotacao"))
    if direct is not None:
        return direct

    blob_lines = [str(item) for item in (snapshot.get("metrics") or [])] + [str(item) for item in (snapshot.get("lines") or [])]
    for line in blob_lines:
        if "cot" not in _normalize(line):
            continue
        match = re.search(r"r\$\s*([-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2}))", line, flags=re.I)
        if match:
            return _parse_currency_value(match.group(1))
    return None


def _asset_positions(snapshot: dict) -> dict[str, dict]:
    positions = snapshot.get("asset_positions")
    return positions if isinstance(positions, dict) else {}


def _asset_fundamentals(snapshot: dict) -> dict[str, dict]:
    fundamentals = snapshot.get("asset_fundamentals")
    return fundamentals if isinstance(fundamentals, dict) else {}


def _resolve_reference_price(position: dict, strategy: dict) -> float | None:
    reference_name = str(strategy.get("auto_ceiling_reference", "preco_medio")).strip()
    if reference_name == "cotacao_atual":
        return _parse_currency_value(position.get("current_price"))
    return _parse_currency_value(position.get("average_price")) or _parse_currency_value(position.get("current_price"))


def _effective_price_ceiling(snapshot: dict, ticker: str, position: dict) -> tuple[float | None, str]:
    strategy = get_asset_strategy(ticker)
    manual_ceiling = strategy.get("price_ceiling")
    if manual_ceiling is not None:
        return float(manual_ceiling), "manual"

    if not strategy.get("auto_ceiling_enabled"):
        return None, "none"

    if str(strategy.get("auto_ceiling_method", "")).strip() == "yield_alvo":
        fundamentals = _asset_fundamentals(snapshot).get(ticker, {})
        annual_dividend = fundamentals.get("annual_dividend_estimate_per_share")
        target_yield = strategy.get("auto_ceiling_target_yield_percent")
        if annual_dividend and target_yield:
            try:
                ceiling = float(annual_dividend) / (float(target_yield) / 100.0)
                if ceiling > 0:
                    return ceiling, "automatic_yield"
            except Exception:
                pass

    reference_price = _resolve_reference_price(position, strategy)
    auto_ceiling = calculate_auto_price_ceiling(reference_price, strategy.get("auto_ceiling_margin_percent"))
    if auto_ceiling is None:
        return None, "none"
    return float(auto_ceiling), "automatic"


def _portfolio_items_above_ceiling(snapshot: dict) -> list[dict]:
    results: list[dict] = []
    for ticker, position in _asset_positions(snapshot).items():
        current_price = _parse_currency_value(position.get("current_price"))
        ceiling, source = _effective_price_ceiling(snapshot, ticker, position)
        if source == "none" or current_price is None or ceiling is None or current_price <= ceiling:
            continue
        premium_percent = ((current_price / ceiling) - 1.0) * 100.0 if ceiling > 0 else None
        results.append(
            {
                "ticker": ticker,
                "current_price": current_price,
                "ceiling": ceiling,
                "source": source,
                "premium_percent": premium_percent,
            }
        )
    return sorted(results, key=lambda item: item.get("premium_percent") or 0.0, reverse=True)


def _portfolio_attention_items(snapshot: dict) -> list[dict]:
    items: list[dict] = []
    for ticker, position in _asset_positions(snapshot).items():
        reasons: list[str] = []
        current_price = _parse_currency_value(position.get("current_price"))
        average_price = _parse_currency_value(position.get("average_price"))
        variation = _parse_percent_value(position.get("variation"))
        rentability = _parse_percent_value(position.get("rentability"))
        portfolio_percentage = _parse_percent_value(position.get("portfolio_percentage"))
        ideal_percentage = _parse_percent_value(position.get("ideal_percentage"))
        rating_text = str(position.get("rating", "")).strip()
        buy_more = str(position.get("buy_more", "")).strip().lower()

        ceiling, source = _effective_price_ceiling(snapshot, ticker, position)
        if source == "manual" and current_price is not None and ceiling is not None and current_price > ceiling:
            reasons.append("acima de seu preço-teto")
        if rentability is not None and rentability <= -10:
            reasons.append(f"rentabilidade fraca em {position.get('rentability')}")
        if variation is not None and variation <= -10:
            reasons.append(f"queda recente de {position.get('variation')}")
        if portfolio_percentage is not None and ideal_percentage is not None and portfolio_percentage > (ideal_percentage + 0.75):
            reasons.append("peso acima do ideal")
        if rating_text.isdigit() and int(rating_text) <= 5:
            reasons.append(f"nota interna em {rating_text}")
        if average_price is not None and current_price is not None and current_price < average_price and buy_more == "não":
            reasons.append("abaixo do preço médio sem sinal de compra adicional")

        if reasons:
            items.append(
                {
                    "ticker": ticker,
                    "reasons": reasons,
                    "current_price": position.get("current_price"),
                    "rentability": position.get("rentability"),
                }
            )
    return items


def _format_position_reading(snapshot: dict, ticker: str, position: dict) -> str:
    strategy = get_asset_strategy(ticker)
    fundamentals = _asset_fundamentals(snapshot).get(ticker, {})
    parts = [
        f"Sobre {ticker}, a cotação atual visível está em {position.get('current_price', 'valor não identificado')}.",
    ]

    if position.get("average_price"):
        parts.append(f"Seu preço médio está em {position['average_price']}.")
    if position.get("variation"):
        parts.append(f"A variação no recorte está em {position['variation']}.")
    if position.get("rentability"):
        parts.append(f"A rentabilidade mostrada está em {position['rentability']}.")
    if position.get("balance"):
        parts.append(f"O saldo atual visível é {position['balance']}.")
    if position.get("portfolio_percentage"):
        parts.append(f"Hoje ele representa {position['portfolio_percentage']} da carteira.")
    if fundamentals.get("dividend_yield_current"):
        parts.append(f"O dividend yield atual salvo está em {fundamentals['dividend_yield_current']}.")

    ceiling = strategy.get("price_ceiling")
    if ceiling is not None:
        current_price = _parse_currency_value(position.get("current_price"))
        parts.append(f"Seu preço-teto salvo para {ticker} é {_format_brl(float(ceiling))}.")
        if current_price is not None:
            relation = "abaixo" if current_price <= float(ceiling) else "acima"
            parts.append(f"Pela cotação visível, ele está {relation} desse nível.")
    else:
        auto_ceiling, source = _effective_price_ceiling(snapshot, ticker, position)
        if auto_ceiling is not None:
            if source == "automatic_yield":
                target_yield = float(strategy.get("auto_ceiling_target_yield_percent", 8.0))
                parts.append(
                    f"Pela base automática por yield alvo de {target_yield:.0f}%, "
                    f"o preço-teto estimado ficaria em {_format_brl(auto_ceiling)}."
                )
            elif source == "automatic":
                margin = float(strategy.get("auto_ceiling_margin_percent", 8.0))
                parts.append(
                    f"Como referência automática, com margem de segurança de {margin:.0f}%, "
                    f"o preço-teto estimado ficaria em {_format_brl(auto_ceiling)}."
                )

    thesis = str(strategy.get("thesis", "")).strip()
    if thesis:
        parts.append(f"Sua tese curta salva para esse ativo é: {thesis}")

    if strategy.get("in_watchlist"):
        parts.append(f"{ticker} já está na sua watchlist.")

    parts.append("Minha leitura prática é cruzar esse preço com sua tese, o risco do setor e seu critério de entrada antes de chamar de oportunidade.")
    return " ".join(parts)


def _looks_like_broader_investment_question(normalized: str) -> bool:
    broader_terms = {
        "vale a pena",
        "bom ativo",
        "ativo bom",
        "acha de",
        "isso e bom",
        "isso e ruim",
        "esta bom",
        "esta ruim",
        "subindo",
        "caindo",
        "tendencia",
        "cenario",
        "leitura",
        "avaliacao",
        "analise",
        "analisar",
        "opiniao",
        "risco",
        "riscos",
        "tese",
        "comprar",
        "vender",
        "compra",
        "venda",
        "barato",
        "caro",
        "preco teto",
        "preço teto",
        "abaixo do meu preco teto",
        "abaixo do meu preço teto",
        "acima do meu preco teto",
        "acima do meu preço teto",
        "qual sua leitura",
        "o que voce acha",
        "o que você acha",
        "me fala mais",
        "me fale mais",
        "explica melhor",
        "me explica melhor",
        "momento de compra",
        "momento de venda",
    }
    return any(term in normalized for term in broader_terms)


def _build_local_investment_reading(question: str, snapshot: dict) -> str:
    metric_map = snapshot.get("metric_map") or {}
    ticker = _extract_question_ticker(question) or _extract_ticker(snapshot)
    direction = _extract_snapshot_direction(snapshot)
    summary = str(snapshot.get("summary", "")).strip()
    normalized_question = _normalize(question)
    strategy = get_asset_strategy(ticker) if ticker else {}
    price_ceiling = strategy.get("price_ceiling")
    thesis = str(strategy.get("thesis", "")).strip()
    in_watchlist = bool(strategy.get("in_watchlist"))
    current_price = _extract_current_price(snapshot)
    position = _asset_positions(snapshot).get(ticker, {}) if ticker else {}
    fundamentals = _asset_fundamentals(snapshot).get(ticker, {}) if ticker else {}

    asset_name = ticker or str(snapshot.get("page_title", "")).strip() or "esse ativo"
    parts = [f"Sobre {asset_name}, eu tenho um contexto recente de cotação, rentabilidade e proventos na sua carteira."]

    if direction:
        parts.append(f"No recorte visível, ele está {direction}.")

    if metric_map.get("rentabilidade"):
        parts.append(f"A rentabilidade destacada está em {metric_map['rentabilidade']}.")
    elif metric_map.get("variacao"):
        parts.append(f"A variação visível está em {metric_map['variacao']}.")

    if fundamentals.get("dividend_yield_current"):
        parts.append(f"O dividend yield atual salvo está em {fundamentals['dividend_yield_current']}.")

    if metric_map.get("proventos"):
        parts.append(f"Também há destaque para proventos, com referência visível a {metric_map['proventos']}.")

    if price_ceiling is not None:
        parts.append(f"Seu preço-teto salvo para {asset_name} é {_format_brl(price_ceiling)}.")
        if current_price is not None:
            if current_price <= float(price_ceiling):
                parts.append("Pelo preço visível, ele está no ponto ou abaixo do seu preço-teto.")
            else:
                parts.append("Pelo preço visível, ele ainda está acima do seu preço-teto.")
    elif ticker and (current_price is not None or position):
        auto_ceiling, auto_source = _effective_price_ceiling(snapshot, ticker, position or {"current_price": _format_brl(current_price)})
        if auto_ceiling is not None:
            if auto_source == "automatic_yield":
                parts.append(
                    f"Pela base automática por yield alvo de {float(strategy.get('auto_ceiling_target_yield_percent', 8.0)):.0f}%, "
                    f"o preço-teto estimado ficaria em {_format_brl(auto_ceiling)}."
                )
            else:
                parts.append(
                    f"Como referência automática provisória, com margem de segurança de "
                    f"{float(strategy.get('auto_ceiling_margin_percent', 8.0)):.0f}%, "
                    f"o preço-teto estimado ficaria em {_format_brl(auto_ceiling)}."
                )
    elif _mentions_price_ceiling(normalized_question):
        parts.append("Eu ainda não tenho seu preço-teto salvo para comparar isso de forma confiável.")

    if in_watchlist:
        parts.append(f"{asset_name} já está na sua watchlist.")

    if thesis:
        parts.append(f"Sua tese salva para esse ativo hoje é: {thesis}")
    if any(term in normalized_question for term in {"barato", "caro"}):
        parts.append("Com esse recorte sozinho, eu ainda não chamaria de barato ou caro com convicção; precisaria cruzar preço, fundamento e seu critério.")
    else:
        parts.append("Minha leitura prática é que isso pede olhar conjunto para momento, tese e risco, não só para um número isolado.")

    if summary and len(summary) < 220:
        parts.append(f"O contexto salvo sugere isto: {summary}")

    return " ".join(parts)


def _ask_grounded_investment_reading(question: str, snapshot: dict) -> str | None:
    if not GEMINI_API_KEY:
        return None

    metric_map = snapshot.get("metric_map") or {}
    ticker = _extract_question_ticker(question) or _extract_ticker(snapshot) or str(snapshot.get("page_title", "")).strip() or "ativo não identificado"
    summary = str(snapshot.get("summary", "")).strip() or "sem resumo salvo"
    lines = [str(item).strip() for item in (snapshot.get("lines") or []) if str(item).strip()][:12]
    metrics = "; ".join(f"{key}: {value}" for key, value in metric_map.items() if value) or "nenhuma métrica estruturada"
    strategy = get_asset_strategy(ticker)
    fundamentals = _asset_fundamentals(snapshot).get(ticker, {})
    strategy_context = []
    if strategy.get("price_ceiling") is not None:
        strategy_context.append(f"preço-teto: {_format_brl(strategy['price_ceiling'])}")
    if strategy.get("in_watchlist"):
        strategy_context.append("está na watchlist")
    if strategy.get("thesis"):
        strategy_context.append(f"tese: {strategy['thesis']}")
    if fundamentals.get("dividend_yield_current"):
        strategy_context.append(f"DY atual salvo: {fundamentals['dividend_yield_current']}")
    if fundamentals.get("dividend_yield_5y_average"):
        strategy_context.append(f"DY médio 5 anos salvo: {fundamentals['dividend_yield_5y_average']}")

    prompt = (
        "Você é o Axel respondendo uma pergunta sobre investimentos usando um snapshot local e, se necessário, busca web atual.\n"
        "Responda em português do Brasil, de forma útil, clara e cautelosa.\n"
        "Não cite links nem fontes a menos que o usuário peça.\n"
        "Não dê recomendação categórica de compra ou venda como certeza.\n"
        "Prefira uma leitura prática: momento do ativo, principais riscos, o que observar e se o cenário parece mais favorável ou mais exigente.\n"
        "Se faltar dado para concluir com força, diga isso de forma natural.\n"
        "Pode responder em 4 a 6 frases.\n\n"
        f"Ativo ou contexto principal: {ticker}\n"
        f"Resumo local salvo: {summary}\n"
        f"Métricas locais salvas: {metrics}\n"
        f"Contexto estratégico do Pedro: {'; '.join(strategy_context) if strategy_context else 'nenhuma regra pessoal salva para esse ativo'}\n"
        "Trechos locais úteis:\n"
        + ("\n".join(f"- {line}" for line in lines) if lines else "- nenhum trecho extra salvo")
        + f"\n\nPergunta do Pedro:\n{question}\n\nResposta:"
    )
    try:
        result = ask_gemini_grounded_model(
            prompt,
            timeout_seconds=25,
            max_output_tokens=320,
            temperature=0.2,
        )
        text = str((result or {}).get("text", "")).strip()
        if text:
            return text
    except Exception:
        return None
    return None


def save_investment_snapshot(
    summary: str,
    metrics: list[str] | None = None,
    lines: list[str] | None = None,
    page_url: str = "",
    page_title: str = "",
    extra: dict | None = None,
):
    payload = {
        "updated_at": time.time(),
        "summary": re.sub(r"\s+", " ", str(summary or "")).strip(),
        "metrics": [re.sub(r"\s+", " ", str(item or "")).strip() for item in list(metrics or []) if str(item or "").strip()],
        "lines": [re.sub(r"\s+", " ", str(item or "")).strip() for item in list(lines or [])[:30] if str(item or "").strip()],
        "page_url": str(page_url or "").strip(),
        "page_title": str(page_title or "").strip(),
    }
    if isinstance(extra, dict):
        payload.update(extra)
    if not isinstance(payload.get("metric_map"), dict):
        payload["metric_map"] = _extract_metric_map(payload.get("metrics"), payload.get("lines"))
    _save_json(INVESTMENT_SNAPSHOT_PATH, payload)
    return payload


def load_investment_snapshot() -> dict:
    data = _load_json(INVESTMENT_SNAPSHOT_PATH)
    return data if isinstance(data, dict) else {}


def format_investment_snapshot_summary() -> str:
    snapshot = load_investment_snapshot()
    updated_at = float(snapshot.get("updated_at") or 0)
    summary = str(snapshot.get("summary", "")).strip()
    metric_map = snapshot.get("metric_map") or {}

    if not updated_at and not summary:
        return "Ainda não tenho uma carteira salva localmente. Abra o Investidor10 uma vez e peça para atualizar os investimentos."

    key_order = ("patrimonio", "valor investido", "valor atual", "rentabilidade", "proventos")
    highlights = [f"{label}: {metric_map[label]}" for label in key_order if metric_map.get(label)]
    if highlights:
        return "Carteira atualizada. " + "; ".join(highlights) + "."

    if summary:
        return "Carteira atualizada. " + summary + "."

    return "Tenho uma carteira atualizada, mas ainda com poucos dados úteis extraídos."


def answer_investment_snapshot_question(question: str) -> str:
    snapshot = load_investment_snapshot()
    updated_at = float(snapshot.get("updated_at") or 0)
    summary = str(snapshot.get("summary", "")).strip()
    metric_map = snapshot.get("metric_map") or {}
    normalized = _normalize(question)
    question_ticker = _extract_question_ticker(question)
    strategy = get_asset_strategy(question_ticker) if question_ticker else {}
    asset_positions = _asset_positions(snapshot)
    asset_position = asset_positions.get(question_ticker, {}) if question_ticker else {}

    if question_ticker and _mentions_price_ceiling(normalized):
        current_price = _parse_currency_value(asset_position.get("current_price")) if asset_position else _extract_current_price(snapshot)
        effective_ceiling, source = _effective_price_ceiling(snapshot, question_ticker, asset_position or {})
        ceiling = strategy.get("price_ceiling")
        if ceiling is not None:
            if current_price is not None:
                relation = "abaixo" if current_price <= float(ceiling) else "acima"
                return (
                    f"Seu preço-teto salvo para {question_ticker} é {_format_brl(float(ceiling))}. "
                    f"Pela cotação visível, ele está {relation} desse nível."
                )
            return (
                f"Seu preço-teto salvo para {question_ticker} é {_format_brl(float(ceiling))}. "
                "Ainda não consegui comparar isso com a cotação atual visível."
            )
        return f"Ainda não tenho preço-teto salvo para {question_ticker}."

    if "margem de segurança" in normalized or "margem de seguranca" in normalized:
        settings = get_auto_ceiling_settings()
        return (
            f"Sua base automática está em yield alvo de {str(settings['target_yield_percent']).replace('.', ',')}%. "
            f"Enquanto faltarem dividendos anuais confiáveis por ativo, o fallback local usa "
            f"{str(settings['margin_percent']).replace('.', ',')}% sobre {('preço médio' if settings['reference'] == 'preco_medio' else 'cotação atual')}."
        )

    if question_ticker and "watchlist" in normalized:
        return (
            f"{question_ticker} já está na sua watchlist."
            if strategy.get("in_watchlist")
            else f"{question_ticker} não está na sua watchlist."
        )

    if question_ticker and "tese" in normalized:
        thesis = str(strategy.get("thesis", "")).strip()
        if thesis:
            return f"Sua tese salva para {question_ticker} é: {thesis}"
        return f"Ainda não tenho tese salva para {question_ticker}."

    if question_ticker and asset_positions and not asset_position:
        return (
            f"Na sua carteira atualizada, eu não encontrei {question_ticker}. "
            f"Ela foi atualizada {_format_timestamp_natural(updated_at)}."
        )

    if not updated_at and not summary:
        return "Ainda não tenho dados locais da sua carteira. Peça para abrir ou atualizar o Investidor10 primeiro."

    if any(token in normalized for token in ("quando", "atualizado", "atualizacao", "salvo", "snapshot")):
        return f"Sua carteira está atualizada {_format_timestamp_natural(updated_at)}."

    if question_ticker and any(term in normalized for term in {"caro", "barato", "criterio", "critério"}):
        if asset_position:
            current_price = _parse_currency_value(asset_position.get("current_price"))
            ceiling, source = _effective_price_ceiling(snapshot, question_ticker, asset_position)
            if current_price is not None and ceiling is not None:
                criterion_name = "seu preço-teto" if source == "manual" else "o preço-teto automático"
                if current_price > ceiling:
                    distance_percent = ((current_price / ceiling) - 1.0) * 100.0 if ceiling > 0 else 0.0
                    return (
                        f"Para o seu critério atual, {question_ticker} parece caro. "
                        f"Ele está em {_format_brl(current_price)}, cerca de {_format_percent(distance_percent)} acima de {criterion_name}, "
                        f"que hoje fica em {_format_brl(ceiling)}."
                    )
                return (
                    f"Para o seu critério atual, {question_ticker} não parece caro. "
                    f"Ele está em {_format_brl(current_price)}, abaixo de {criterion_name}, "
                    f"que hoje fica em {_format_brl(ceiling)}."
                )
        return f"Eu ainda não tenho base suficiente para dizer se {question_ticker} está caro para o seu critério."

    if "quais ativos" in normalized and ("acima do meu preco teto" in normalized or "acima do meu preço teto" in normalized):
        items = _portfolio_items_above_ceiling(snapshot)
        if not items:
            return "Nenhum ativo com preço-teto definido está acima do seu critério no snapshot atual."
        parts = []
        for item in items[:6]:
            premium = _format_percent(item.get("premium_percent"))
            parts.append(
                f"{item['ticker']} em {_format_brl(item['current_price'])}, acima do teto manual de {_format_brl(item['ceiling'])} por cerca de {premium}"
            )
        return "Ativos acima do seu preço-teto no snapshot atual: " + "; ".join(parts) + "."

    if "quais ativos" in normalized and "negativos" in normalized:
        negatives = []
        for ticker, position in _asset_positions(snapshot).items():
            rentability = _parse_percent_value(position.get("rentability"))
            if rentability is not None and rentability < 0:
                negatives.append((ticker, position.get("rentability", "")))
        if not negatives:
            return "No snapshot atual, eu não encontrei ativos com rentabilidade negativa."
        return "Ativos com rentabilidade negativa agora: " + "; ".join(f"{ticker} em {value}" for ticker, value in negatives) + "."

    if "merecem atencao" in normalized or "merecem atenção" in normalized:
        items = _portfolio_attention_items(snapshot)
        if not items:
            return "No snapshot atual, eu não vi nenhuma posição gritando por atenção imediata."
        parts = []
        for item in items[:6]:
            reason_text = ", ".join(item["reasons"][:2])
            extra = f" Cotação: {item['current_price']}." if item.get("current_price") else ""
            parts.append(f"{item['ticker']}: {reason_text}.{extra}".strip())
        return "As posições que mais pedem atenção agora são: " + " ".join(parts)

    question_map = {
        "patrimonio": ("patrimonio", "patrimônio"),
        "valor investido": ("valor investido", "quanto investi", "tenho investido"),
        "valor atual": ("valor atual", "quanto vale", "valor da carteira"),
        "rentabilidade": ("rentabilidade", "rendeu", "retorno"),
        "proventos": ("proventos", "dividendos"),
        "saldo": ("saldo",),
        "lucro": ("lucro",),
        "prejuizo": ("prejuizo", "prejuízo"),
        "aporte": ("aporte", "aportes"),
        "preco medio": ("preco medio", "preço médio", "preço medio"),
        "cotacao": ("cotacao", "cotação"),
        "variacao": ("variacao", "variação", "subiu", "caiu"),
    }

    for canonical, hints in question_map.items():
        if any(hint in normalized for hint in hints):
            if asset_position:
                asset_value_map = {
                    "valor atual": asset_position.get("balance"),
                    "rentabilidade": asset_position.get("rentability"),
                    "preco medio": asset_position.get("average_price"),
                    "cotacao": asset_position.get("current_price"),
                    "variacao": asset_position.get("variation"),
                    "saldo": asset_position.get("balance"),
                }
                asset_value = asset_value_map.get(canonical)
                if asset_value:
                    return f"{question_ticker} está com {canonical} em {asset_value}. Carteira atualizada."
            value = metric_map.get(canonical)
            if value:
                return f"{canonical.capitalize()} em {value}. Carteira atualizada."
            if canonical == "patrimonio" and metric_map.get("valor atual"):
                return f"Não encontrei patrimônio explícito no recorte salvo, mas o valor atual está em {metric_map['valor atual']}. Carteira atualizada."
            break

    if _looks_like_broader_investment_question(normalized):
        if asset_position:
            grounded = _ask_grounded_investment_reading(question, snapshot)
            if grounded:
                return grounded
            return _format_position_reading(snapshot, question_ticker, asset_position)
        grounded = _ask_grounded_investment_reading(question, snapshot)
        if grounded:
            return grounded
        return _build_local_investment_reading(question, snapshot)

    if summary:
        return "Carteira atualizada. " + summary

    return "Tenho uma carteira atualizada, mas não encontrei essa informação de forma confiável nela."


_answer_investment_snapshot_question_base = answer_investment_snapshot_question


def answer_investment_snapshot_question(question: str) -> str:
    snapshot = load_investment_snapshot()
    normalized = _normalize(question)
    question_ticker = _extract_question_ticker(question)
    asset_positions = _asset_positions(snapshot)
    asset_position = asset_positions.get(question_ticker, {}) if question_ticker else {}
    strategy = get_asset_strategy(question_ticker) if question_ticker else {}
    fundamentals = _asset_fundamentals(snapshot).get(question_ticker, {}) if question_ticker else {}

    if question_ticker and _contains_investment_phrase(normalized, "dy", "dividend yield", "yield"):
        current_dy = fundamentals.get("dividend_yield_current")
        average_dy = fundamentals.get("dividend_yield_5y_average")
        if current_dy and average_dy:
            return f"O DY atual de {question_ticker} está em {current_dy}, com média de 5 anos em {average_dy}."
        if current_dy:
            return f"O DY atual de {question_ticker} está em {current_dy}."
        return f"Ainda não tenho DY salvo para {question_ticker}."

    if question_ticker and _contains_investment_phrase(normalized, "cotacao", "cotação", "cotaçao"):
        current_price = asset_position.get("current_price") or fundamentals.get("quote")
        if current_price:
            variation = asset_position.get("variation")
            variation_value = _parse_percent_value(variation) if variation else None
            if variation_value is not None:
                if variation_value > 0:
                    return f"A cotação visível de {question_ticker} está em {current_price}. No dia, ele está subindo, com variação de {variation}."
                if variation_value < 0:
                    return f"A cotação visível de {question_ticker} está em {current_price}. No dia, ele está caindo, com variação de {variation}."
                return f"A cotação visível de {question_ticker} está em {current_price}. No dia, ele está estável, com variação de {variation}."
            if variation:
                return f"A cotação visível de {question_ticker} está em {current_price}, com variação visível de {variation}."
            return f"A cotação visível de {question_ticker} está em {current_price}."
        return f"Ainda não tenho cotação salva para {question_ticker}."

    if question_ticker and _contains_investment_phrase(normalized, "preco medio", "preço medio", "preço médio", "preco médio"):
        average_price = asset_position.get("average_price")
        if average_price:
            return f"O preço médio de {question_ticker} está em {average_price}."
        return f"Ainda não tenho preço médio salvo para {question_ticker}."

    if question_ticker and _contains_investment_phrase(normalized, "subindo", "caindo", "variacao", "variação", "alta", "queda"):
        variation = asset_position.get("variation")
        if variation:
            variation_value = _parse_percent_value(variation)
            if variation_value is not None:
                if variation_value > 0:
                    return f"No recorte atual, {question_ticker} está subindo, com variação de {variation}."
                if variation_value < 0:
                    return f"No recorte atual, {question_ticker} está caindo, com variação de {variation}."
                return f"No recorte atual, {question_ticker} está estável, com variação de {variation}."
            return f"A variação visível de {question_ticker} está em {variation}."
        return f"Ainda não tenho variação salva para {question_ticker}."

    if question_ticker and _contains_investment_phrase(normalized, "dividendos agendados", "proventos agendados", "dividendos previstos", "dividendos programados", "proximo dividendo", "próximo dividendo", "data ex", "data com"):
        return f"Ainda não tenho agenda de dividendos integrada para {question_ticker}. Hoje eu consigo ler proventos e DY salvos, mas não a próxima data com confiança."

    if question_ticker and _contains_investment_phrase(normalized, "fato relevante", "noticia", "notícias", "noticias", "relevante", "novidade"):
        return f"Ainda não tenho notícias ou fatos relevantes integrados em tempo real para {question_ticker}. Isso já entrou na lista de avanços do modo investimentos."

    if question_ticker and _mentions_price_ceiling(normalized):
        current_price = _parse_currency_value(asset_position.get("current_price")) if asset_position else _extract_current_price(snapshot)
        manual_ceiling = strategy.get("price_ceiling")
        effective_ceiling, source = _effective_price_ceiling(snapshot, question_ticker, asset_position or {})

        if manual_ceiling is None and effective_ceiling is not None:
            relation = ""
            if current_price is not None:
                relation = "abaixo" if current_price <= effective_ceiling else "acima"
            if source == "automatic_yield":
                prefix = (
                    f"Ainda não tenho preço-teto manual salvo para {question_ticker}. "
                    f"Pela sua base automática de yield alvo, o teto estimado fica em {_format_brl(effective_ceiling)}."
                )
            else:
                prefix = (
                    f"Ainda não tenho preço-teto manual salvo para {question_ticker}. "
                    f"Pela sua base automática atual, o teto estimado fica em {_format_brl(effective_ceiling)}."
                )
            if relation:
                return prefix + f" Na cotação visível, ele está {relation} desse nível."
            return prefix

    if "quais ativos" in normalized and ("acima do meu preco teto" in normalized or "acima do meu preço teto" in normalized):
        items = _portfolio_items_above_ceiling(snapshot)
        if not items:
            return "Nenhum ativo com preço-teto manual ou automático está acima do seu critério no snapshot atual."
        parts = []
        for item in items[:6]:
            source_label = "teto manual"
            if item.get("source") == "automatic_yield":
                source_label = "teto automático por yield"
            elif item.get("source") == "automatic":
                source_label = "teto automático"
            premium = _format_percent(item.get("premium_percent"))
            parts.append(
                f"{item['ticker']} em {_format_brl(item['current_price'])}, acima do {source_label} de {_format_brl(item['ceiling'])} por cerca de {premium}"
            )
        return "Ativos acima do seu preço-teto no snapshot atual: " + "; ".join(parts) + "."

    return _answer_investment_snapshot_question_base(question)
