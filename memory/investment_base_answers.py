from typing import Callable

from memory.investment_formatting import format_brl, format_percent, parse_currency_value, parse_percent_value


def answer_price_criterion(
    snapshot: dict,
    question_ticker: str,
    asset_position: dict,
    *,
    effective_price_ceiling: Callable[[dict, str, dict], tuple[float | None, str]],
) -> str:
    if asset_position:
        current_price = parse_currency_value(asset_position.get("current_price"))
        ceiling, source = effective_price_ceiling(snapshot, question_ticker, asset_position)
        if current_price is not None and ceiling is not None:
            criterion_name = "seu preço-teto" if source == "manual" else "o preço-teto automático"
            if current_price > ceiling:
                distance_percent = ((current_price / ceiling) - 1.0) * 100.0 if ceiling > 0 else 0.0
                return (
                    f"Para o seu critério atual, {question_ticker} parece caro. "
                    f"Ele está em {format_brl(current_price)}, cerca de {format_percent(distance_percent)} acima de {criterion_name}, "
                    f"que hoje fica em {format_brl(ceiling)}."
                )
            return (
                f"Para o seu critério atual, {question_ticker} não parece caro. "
                f"Ele está em {format_brl(current_price)}, abaixo de {criterion_name}, "
                f"que hoje fica em {format_brl(ceiling)}."
            )
    return f"Eu ainda não tenho base suficiente para dizer se {question_ticker} está caro para o seu critério."


def answer_manual_assets_above_ceiling(
    snapshot: dict,
    *,
    portfolio_items_above_ceiling: Callable[[dict], list[dict]],
) -> str:
    items = portfolio_items_above_ceiling(snapshot)
    if not items:
        return "Nenhum ativo com preço-teto definido está acima do seu critério no snapshot atual."
    parts = []
    for item in items[:6]:
        premium = format_percent(item.get("premium_percent"))
        parts.append(
            f"{item['ticker']} em {format_brl(item['current_price'])}, acima do teto manual de {format_brl(item['ceiling'])} por cerca de {premium}"
        )
    return "Ativos acima do seu preço-teto no snapshot atual: " + "; ".join(parts) + "."


def answer_negative_assets(
    snapshot: dict,
    *,
    asset_positions: Callable[[dict], dict[str, dict]],
) -> str:
    negatives = []
    for ticker, position in asset_positions(snapshot).items():
        rentability = parse_percent_value(position.get("rentability"))
        if rentability is not None and rentability < 0:
            negatives.append((ticker, position.get("rentability", "")))
    if not negatives:
        return "No snapshot atual, eu não encontrei ativos com rentabilidade negativa."
    return "Ativos com rentabilidade negativa agora: " + "; ".join(f"{ticker} em {value}" for ticker, value in negatives) + "."


def answer_attention_assets(
    snapshot: dict,
    *,
    portfolio_attention_items: Callable[[dict], list[dict]],
    position_action_stance: Callable[[dict, str, dict], str],
    asset_positions: Callable[[dict], dict[str, dict]],
) -> str:
    items = portfolio_attention_items(snapshot)
    if not items:
        return "No snapshot atual, eu não vi nenhuma posição gritando por atenção imediata."
    parts = []
    positions = asset_positions(snapshot)
    for item in items[:6]:
        reason_text = ", ".join(item["reasons"][:2])
        opinion_text = ""
        if item.get("opinions"):
            opinion_text = str(item["opinions"][0]).strip().rstrip(".")
        stance_text = position_action_stance(snapshot, item["ticker"], positions.get(item["ticker"], {})).strip().rstrip(".")
        extra = f" Cotação: {item['current_price']}." if item.get("current_price") else ""
        if opinion_text:
            parts.append(f"{item['ticker']}: {reason_text}. Minha leitura: {opinion_text}. Direção prática: {stance_text}.{extra}".strip())
        else:
            parts.append(f"{item['ticker']}: {reason_text}. Direção prática: {stance_text}.{extra}".strip())
    return "As posições que mais pedem atenção agora são: " + " ".join(parts)


QUESTION_METRIC_MAP = {
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


def answer_metric_question(
    normalized: str,
    question_ticker: str,
    asset_position: dict,
    metric_map: dict,
) -> str | None:
    for canonical, hints in QUESTION_METRIC_MAP.items():
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
    return None


def answer_manual_price_ceiling(
    snapshot: dict,
    question_ticker: str,
    asset_position: dict,
    strategy: dict,
    *,
    extract_current_price: Callable[[dict], float | None],
) -> str:
    current_price = parse_currency_value(asset_position.get("current_price")) if asset_position else extract_current_price(snapshot)
    ceiling = strategy.get("price_ceiling")
    if ceiling is not None:
        if current_price is not None:
            relation = "abaixo" if current_price <= float(ceiling) else "acima"
            return (
                f"Seu preço-teto salvo para {question_ticker} é {format_brl(float(ceiling))}. "
                f"Pela cotação visível, ele está {relation} desse nível."
            )
        return (
            f"Seu preço-teto salvo para {question_ticker} é {format_brl(float(ceiling))}. "
            "Ainda não consegui comparar isso com a cotação atual visível."
        )
    return f"Ainda não tenho preço-teto salvo para {question_ticker}."


def answer_auto_ceiling_settings(settings: dict) -> str:
    reference = "preço médio" if settings.get("reference") == "preco_medio" else "cotação atual"
    return (
        f"Sua base automática está em yield alvo de {str(settings['target_yield_percent']).replace('.', ',')}%. "
        f"Enquanto faltarem dividendos anuais confiáveis por ativo, o fallback local usa "
        f"{str(settings['margin_percent']).replace('.', ',')}% sobre {reference}."
    )


def answer_watchlist_status(question_ticker: str, strategy: dict) -> str:
    return (
        f"{question_ticker} já está na sua watchlist."
        if strategy.get("in_watchlist")
        else f"{question_ticker} não está na sua watchlist."
    )


def answer_thesis_status(question_ticker: str, strategy: dict) -> str:
    thesis = str(strategy.get("thesis", "")).strip()
    if thesis:
        return f"Sua tese salva para {question_ticker} é: {thesis}"
    return f"Ainda não tenho tese salva para {question_ticker}."


def answer_missing_ticker_in_portfolio(question_ticker: str, updated_at: float, *, format_timestamp_natural: Callable[[float], str]) -> str:
    return (
        f"Na sua carteira atualizada, eu não encontrei {question_ticker}. "
        f"Ela foi atualizada {format_timestamp_natural(updated_at)}."
    )


def answer_empty_snapshot() -> str:
    return "Ainda não tenho dados locais da sua carteira. Peça para abrir ou atualizar o Investidor10 primeiro."


def answer_snapshot_updated_at(updated_at: float, *, format_timestamp_natural: Callable[[float], str]) -> str:
    return f"Sua carteira está atualizada {format_timestamp_natural(updated_at)}."
