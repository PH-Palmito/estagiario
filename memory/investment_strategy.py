import re
from typing import Any

from memory.profile import load_profile, save_profile


def _normalize_ticker(value: str) -> str:
    match = re.search(r"\b([A-Za-z]{3,5}\d{0,2})(?:[-/](?:BRL|USD|USDT))?\b", str(value or ""))
    return match.group(1).upper() if match else ""


def _parse_brl_value(raw: str) -> float | None:
    text = str(raw or "").strip().lower()
    if not text:
        return None
    text = text.replace("r$", "").replace(" ", "")
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_percent_value(raw: str) -> float | None:
    text = str(raw or "").strip().lower().replace("%", "").replace(" ", "")
    if not text:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _format_brl(value: float | None) -> str:
    if value is None:
        return ""
    formatted = f"{value:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value: float | None) -> str:
    if value is None:
        return ""
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".") + "%"


def _ensure_strategy(profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    finances = profile.get("financas")
    if not isinstance(finances, dict):
        finances = {}
        profile["financas"] = finances

    strategy = finances.get("estrategia")
    if not isinstance(strategy, dict):
        strategy = {}
        finances["estrategia"] = strategy

    watchlist = strategy.get("watchlist")
    if not isinstance(watchlist, list):
        watchlist = []
        strategy["watchlist"] = watchlist

    price_targets = strategy.get("precos_teto")
    if not isinstance(price_targets, dict):
        price_targets = {}
        strategy["precos_teto"] = price_targets

    theses = strategy.get("teses")
    if not isinstance(theses, dict):
        theses = {}
        strategy["teses"] = theses

    auto_rules = strategy.get("preco_teto_automatico")
    if not isinstance(auto_rules, dict):
        auto_rules = {}
        strategy["preco_teto_automatico"] = auto_rules

    if str(auto_rules.get("metodo", "")).strip() not in {"yield_alvo", "margem_referencia"}:
        auto_rules["metodo"] = "yield_alvo"
    if not isinstance(auto_rules.get("habilitado"), bool):
        auto_rules["habilitado"] = True
    if not isinstance(auto_rules.get("margem_seguranca_percentual"), (int, float)):
        auto_rules["margem_seguranca_percentual"] = 8.0
    if not isinstance(auto_rules.get("dividend_yield_alvo_percentual"), (int, float)):
        auto_rules["dividend_yield_alvo_percentual"] = 8.0
    if str(auto_rules.get("referencia", "")).strip() not in {"preco_medio", "cotacao_atual"}:
        auto_rules["referencia"] = "preco_medio"

    return profile, strategy, finances


def load_investment_strategy() -> dict[str, Any]:
    profile = load_profile() or {}
    _profile, strategy, _finances = _ensure_strategy(profile)
    return strategy


def get_asset_strategy(ticker: str) -> dict[str, Any]:
    normalized_ticker = _normalize_ticker(ticker)
    strategy = load_investment_strategy()
    watchlist = [str(item).upper() for item in strategy.get("watchlist", []) if _normalize_ticker(str(item))]
    price_targets = strategy.get("precos_teto", {}) if isinstance(strategy.get("precos_teto"), dict) else {}
    theses = strategy.get("teses", {}) if isinstance(strategy.get("teses"), dict) else {}
    auto_rules = strategy.get("preco_teto_automatico", {}) if isinstance(strategy.get("preco_teto_automatico"), dict) else {}

    return {
        "ticker": normalized_ticker,
        "in_watchlist": normalized_ticker in watchlist if normalized_ticker else False,
        "price_ceiling": price_targets.get(normalized_ticker),
        "thesis": str(theses.get(normalized_ticker, "")).strip(),
        "auto_ceiling_method": str(auto_rules.get("metodo", "yield_alvo")).strip(),
        "auto_ceiling_enabled": bool(auto_rules.get("habilitado", True)),
        "auto_ceiling_margin_percent": float(auto_rules.get("margem_seguranca_percentual", 8.0)),
        "auto_ceiling_target_yield_percent": float(auto_rules.get("dividend_yield_alvo_percentual", 8.0)),
        "auto_ceiling_reference": str(auto_rules.get("referencia", "preco_medio")).strip(),
    }


def get_auto_ceiling_settings() -> dict[str, Any]:
    strategy = load_investment_strategy()
    auto_rules = strategy.get("preco_teto_automatico", {}) if isinstance(strategy.get("preco_teto_automatico"), dict) else {}
    return {
        "enabled": bool(auto_rules.get("habilitado", True)),
        "method": str(auto_rules.get("metodo", "yield_alvo")).strip() or "yield_alvo",
        "margin_percent": float(auto_rules.get("margem_seguranca_percentual", 8.0)),
        "target_yield_percent": float(auto_rules.get("dividend_yield_alvo_percentual", 8.0)),
        "reference": str(auto_rules.get("referencia", "preco_medio")).strip() or "preco_medio",
    }


def calculate_auto_price_ceiling(reference_price: float | None, margin_percent: float | None) -> float | None:
    if reference_price is None or margin_percent is None:
        return None
    if reference_price <= 0:
        return None
    return reference_price * (1.0 - (float(margin_percent) / 100.0))


def set_price_ceiling(ticker: str, raw_value: str) -> str:
    normalized_ticker = _normalize_ticker(ticker)
    value = _parse_brl_value(raw_value)
    if not normalized_ticker or value is None:
        return "Não consegui entender o ticker ou o preço-teto."

    profile = load_profile() or {}
    profile, strategy, _finances = _ensure_strategy(profile)
    strategy["precos_teto"][normalized_ticker] = value
    save_profile(profile)
    return f"Preço-teto salvo para {normalized_ticker}: {_format_brl(value)}."


def set_auto_ceiling_margin(raw_value: str) -> str:
    value = _parse_percent_value(raw_value)
    if value is None:
        return "Não consegui entender a margem de segurança."

    profile = load_profile() or {}
    profile, strategy, _finances = _ensure_strategy(profile)
    strategy["preco_teto_automatico"]["margem_seguranca_percentual"] = float(value)
    save_profile(profile)
    return f"Margem de segurança automática atualizada para {_format_percent(float(value))}."


def format_auto_ceiling_settings() -> str:
    settings = get_auto_ceiling_settings()
    status = "ativado" if settings["enabled"] else "desativado"
    referencia = "preço médio" if settings["reference"] == "preco_medio" else "cotação atual"
    metodo = "yield alvo" if settings["method"] == "yield_alvo" else "margem sobre referência"
    return (
        f"O preço-teto automático está {status}. Base atual: {metodo} com alvo de "
        f"{_format_percent(settings['target_yield_percent'])}. Enquanto o snapshot não trouxer dividendos anuais por ativo de forma confiável, "
        f"o fallback local usa {_format_percent(settings['margin_percent'])} sobre {referencia}."
    )


def add_to_watchlist(ticker: str) -> str:
    normalized_ticker = _normalize_ticker(ticker)
    if not normalized_ticker:
        return "Não consegui identificar o ticker para a watchlist."

    profile = load_profile() or {}
    profile, strategy, _finances = _ensure_strategy(profile)
    watchlist = [str(item).upper() for item in strategy.get("watchlist", []) if _normalize_ticker(str(item))]
    if normalized_ticker not in watchlist:
        watchlist.append(normalized_ticker)
    strategy["watchlist"] = sorted(set(watchlist))
    save_profile(profile)
    return f"{normalized_ticker} adicionado à watchlist."


def remove_from_watchlist(ticker: str) -> str:
    normalized_ticker = _normalize_ticker(ticker)
    if not normalized_ticker:
        return "Não consegui identificar o ticker para remover da watchlist."

    profile = load_profile() or {}
    profile, strategy, _finances = _ensure_strategy(profile)
    watchlist = [str(item).upper() for item in strategy.get("watchlist", []) if _normalize_ticker(str(item))]
    if normalized_ticker not in watchlist:
        return f"{normalized_ticker} não estava na watchlist."
    strategy["watchlist"] = [item for item in watchlist if item != normalized_ticker]
    save_profile(profile)
    return f"{normalized_ticker} removido da watchlist."


def set_asset_thesis(ticker: str, thesis: str) -> str:
    normalized_ticker = _normalize_ticker(ticker)
    clean_thesis = " ".join(str(thesis or "").split()).strip()
    if not normalized_ticker or not clean_thesis:
        return "Não consegui salvar a tese desse ativo."

    profile = load_profile() or {}
    profile, strategy, _finances = _ensure_strategy(profile)
    strategy["teses"][normalized_ticker] = clean_thesis
    save_profile(profile)
    return f"Tese salva para {normalized_ticker}."


def format_watchlist() -> str:
    strategy = load_investment_strategy()
    watchlist = [str(item).upper() for item in strategy.get("watchlist", []) if _normalize_ticker(str(item))]
    if not watchlist:
        return "Sua watchlist ainda está vazia."
    return "Watchlist atual: " + ", ".join(sorted(set(watchlist))) + "."
