import re
import time
from collections.abc import Callable, Iterable

NewsCandidates = Callable[[dict, int], Iterable[tuple[str, str, dict]]]
EnsureFundamentals = Callable[[dict, str], dict]
GetStrategy = Callable[[str], dict]
SummarizeAssetNews = Callable[..., str | None]
NormalizeText = Callable[[str], str]
NewsFingerprint = Callable[[str], str]
LoadSeenState = Callable[[], dict]
SaveSeenState = Callable[[dict], None]


RELEVANT_NEWS_TERMS = {
    "resultado",
    "lucro",
    "prejuizo",
    "dividendo",
    "provento",
    "jcp",
    "fato relevante",
    "guidance",
    "aquisicao",
    "fusao",
    "oferta",
    "captacao",
    "venda",
    "compra",
    "risco",
    "divida",
    "selic",
    "juros",
}


def clean_news_lead(text: str, ticker: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    patterns = [
        rf"^encontrei sinais relevantes sobre {re.escape(ticker)}\.\s*",
        rf"^eu encontrei material sobre {re.escape(ticker)},\s*",
        rf"^o que apareceu sobre {re.escape(ticker)}\s*",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.I)
    return cleaned.strip()


def compact_report_news(news_text: str, max_chars: int = 230) -> str:
    text = re.sub(r"\s+", " ", str(news_text or "")).strip()
    if not text:
        return ""
    text = re.sub(r"\bIsso importa porque\b", "Relevância:", text, flags=re.I)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    compact = " ".join(sentence for sentence in sentences[:2] if sentence).strip()
    if not compact:
        compact = text
    if len(compact) <= max_chars:
        return compact
    trimmed = compact[:max_chars].rsplit(" ", 1)[0].strip()
    return trimmed.rstrip(".,;:") + "."


def is_relevant_portfolio_news(text: str, normalize: NormalizeText) -> bool:
    normalized = normalize(text)
    if not normalized:
        return False
    if "nada com confianca suficiente" in normalized:
        return False
    if "sensacionalista" in normalized:
        return False
    return any(term in normalized for term in RELEVANT_NEWS_TERMS)


def portfolio_news_digest(
    snapshot: dict,
    *,
    investment_news_candidates: NewsCandidates,
    ensure_asset_fundamentals: EnsureFundamentals,
    get_asset_strategy: GetStrategy,
    summarize_asset_news: SummarizeAssetNews,
    normalize: NormalizeText,
    news_fingerprint: NewsFingerprint,
    load_seen_state: LoadSeenState,
    save_seen_state: SaveSeenState,
    limit_assets: int = 4,
    limit_summaries: int = 2,
    only_new: bool = False,
    mark_seen: bool = False,
) -> list[str]:
    summaries: list[str] = []
    seen_state = load_seen_state() if only_new or mark_seen else {}
    seen_hashes = set(str(item) for item in (seen_state.get("seen") or []))
    new_hashes: list[str] = []

    for ticker, scope, _position in investment_news_candidates(snapshot, limit_assets):
        fundamentals = ensure_asset_fundamentals(snapshot, ticker)
        company_name = str(fundamentals.get("company_name") or "").strip()
        thesis = str(get_asset_strategy(ticker).get("thesis") or "").strip()
        try:
            summary = summarize_asset_news(
                ticker,
                company_name=company_name,
                thesis=thesis,
                market_data=fundamentals,
            )
        except Exception:
            summary = None
        cleaned = clean_news_lead(summary or "", ticker)
        if not is_relevant_portfolio_news(cleaned, normalize):
            continue
        fingerprint = news_fingerprint(f"{ticker}: {cleaned}")
        if only_new and fingerprint and fingerprint in seen_hashes:
            continue
        prefix = ticker if scope == "carteira" else f"{ticker} (watchlist)"
        summaries.append(f"{prefix}: {compact_report_news(cleaned, max_chars=150)}")
        if fingerprint:
            new_hashes.append(fingerprint)
        if len(summaries) >= limit_summaries:
            break

    if mark_seen and new_hashes:
        combined = list(dict.fromkeys([*seen_hashes, *new_hashes]))
        seen_state["seen"] = combined[-80:]
        seen_state["updated_at"] = time.time()
        save_seen_state(seen_state)
    return summaries
