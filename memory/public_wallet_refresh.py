import re
import subprocess
import time
from html.parser import HTMLParser
from pathlib import Path

from config import INVESTIDOR10_WALLET_URL
from memory.investment_asset_fundamentals import fetch_many_asset_fundamentals
from memory.investment_snapshot import load_investment_snapshot, save_investment_snapshot
from memory.profile import load_profile


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
PUBLIC_WALLET_DOM_PATH = MEMORY_DIR / "wallet_public_dom_full.html"
EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)
SNAPSHOT_STALE_SECONDS = 20 * 60 * 60


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data or "").strip()
        if text:
            self.items.append(text)


def _find_edge_path() -> str:
    for candidate in EDGE_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return ""


def _wallet_url() -> str:
    profile = load_profile()
    finance = profile.get("financas") if isinstance(profile, dict) else {}
    profile_url = ""
    if isinstance(finance, dict):
        profile_url = str(finance.get("investidor10_wallet_url", "")).strip()
    return profile_url or str(INVESTIDOR10_WALLET_URL or "").strip()


def _is_public_wallet_url(url: str) -> bool:
    return "/wallet/public/" in str(url or "").lower()


def _extract_wallet_id(url: str) -> str:
    match = re.search(r"/wallet/public/(\d+)", str(url or ""))
    return match.group(1) if match else ""


def _run_headless_wallet_dump(url: str) -> str:
    edge_path = _find_edge_path()
    if not edge_path:
        raise RuntimeError("Nao encontrei o Microsoft Edge para atualizar a carteira publica.")

    completed = subprocess.run(
        [
            edge_path,
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=12000",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError("Nao consegui renderizar a carteira publica em modo headless.")

    html = completed.stdout or ""
    if not html.strip():
        raise RuntimeError("A carteira publica nao retornou HTML util.")

    PUBLIC_WALLET_DOM_PATH.write_text(html, encoding="utf-8")
    return html


def _extract_visible_items(html: str) -> list[str]:
    parser = _VisibleTextParser()
    parser.feed(html or "")
    items = []
    for raw in parser.items:
        text = str(raw or "").strip()
        if not text or text == "\ufeff":
            continue
        items.append(text)
    if "DISCUSSÃO" in items:
        items = items[: items.index("DISCUSSÃO")]
    return items


def _value_after(items: list[str], label: str, offset: int = 1) -> str:
    try:
        index = items.index(label)
    except ValueError:
        return ""
    target = index + offset
    if 0 <= target < len(items):
        return items[target]
    return ""


def _last_value_after(items: list[str], label: str, offset: int = 1) -> str:
    target_index = -1
    for index, token in enumerate(items):
        if token == label:
            target_index = index
    if target_index < 0:
        return ""
    target = target_index + offset
    if 0 <= target < len(items):
        return items[target]
    return ""


def _parse_overview(items: list[str]) -> dict:
    try:
        summary_end = items.index("Evolução do Patrimônio")
        chunk = items[:summary_end]
    except ValueError:
        chunk = items

    overview = {
        "wallet_name": _value_after(chunk, "Investidor10 | Resumo", 1),
        "page_title": "Investidor10 | Resumo",
        "patrimonio": _last_value_after(chunk, "Patrimônio total"),
        "patrimonio_variacao": _last_value_after(chunk, "Patrimônio total", 2),
        "valor_investido": _last_value_after(chunk, "Valor investido"),
        "lucro_total": _last_value_after(chunk, "Lucro total"),
        "ganho_capital": _last_value_after(chunk, "Ganho de Capital"),
        "dividendos_recebidos": _last_value_after(chunk, "Dividendos Recebidos"),
        "proventos_12m": _last_value_after(chunk, "Proventos Recebidos (12M)"),
        "proventos_total": _last_value_after(chunk, "Total"),
        "variacao": _last_value_after(chunk, "Variação"),
        "saldo_variacao": _last_value_after(chunk, "Variação", 2),
        "rentabilidade": _last_value_after(chunk, "Rentabilidade"),
    }
    return overview


def _parse_category_breakdown(items: list[str]) -> dict[str, str]:
    categories = {}
    try:
        start = items.index("Ativos na Carteira") + 1
        end = items.index("Ativos")
    except ValueError:
        return categories

    chunk = items[start:end]
    i = 0
    while i + 1 < len(chunk):
        label = chunk[i]
        value = chunk[i + 1]
        if label in {"Todos os tipos", "Tipo"}:
            i += 1
            continue
        if re.fullmatch(r"-?\d+(?:[.,]\d+)?%", value):
            categories[label] = value
            i += 2
            continue
        i += 1
    return categories


def _parse_primary_positions(items: list[str]) -> dict[str, dict]:
    positions = {}
    try:
        start = items.index("Ativo")
    except ValueError:
        return positions

    row = []
    for token in items[start + 11 :]:
        if token == "Valor total":
            break
        row.append(token)

    row_size = 11
    for offset in range(0, len(row), row_size):
        chunk = row[offset : offset + row_size]
        if len(chunk) < row_size:
            break
        ticker = chunk[0].strip().upper()
        if not re.fullmatch(r"[A-Z]{4}\d{1,2}", ticker):
            continue
        positions[ticker] = {
            "ticker": ticker,
            "quantity": chunk[1],
            "average_price": chunk[2],
            "current_price": chunk[3],
            "variation": chunk[4],
            "rentability": chunk[5],
            "balance": chunk[6],
            "rating": chunk[7],
            "portfolio_percentage": chunk[8],
            "ideal_percentage": chunk[9],
            "buy_more": chunk[10],
            "category": "Ações",
        }
    return positions


def _parse_category_summaries(items: list[str]) -> dict[str, dict]:
    summaries = {}
    category_names = ("Ações", "FIIs", "Criptomoedas", "Tesouro Direto")
    active_block_seen = False

    i = 0
    while i < len(items):
        token = items[i]
        if token == "Ativos":
            active_block_seen = True
            i += 1
            continue

        if active_block_seen and token in category_names and i + 10 < len(items):
            maybe_count = items[i + 1]
            if not maybe_count.startswith("("):
                i += 1
                continue
            if items[i + 2 : i + 10] and items[i + 2] == "Valor total":
                summaries[token] = {
                    "assets_count": maybe_count,
                    "value_total": items[i + 3],
                    "variation": items[i + 5] if items[i + 4] == "Variação" else "",
                    "rentability": items[i + 7] if items[i + 6] == "Rentabilidade" else "",
                    "portfolio_percentage": items[i + 9] if items[i + 8] == "% na carteira" else "",
                    "ideal_percentage": items[i + 11] if i + 11 < len(items) and items[i + 10] == "/" else "",
                }
                i += 12
                continue
        i += 1

    return summaries


def _build_summary_text(overview: dict, categories: dict[str, str]) -> str:
    parts = []
    patrimony = overview.get("patrimonio")
    if patrimony:
        parts.append(f"Carteira pública atualizada com patrimônio total de {patrimony}.")
    invested = overview.get("valor_investido")
    if invested:
        parts.append(f"Valor investido: {invested}.")
    rentability = overview.get("rentabilidade")
    if rentability:
        parts.append(f"Rentabilidade visível: {rentability}.")
    provents = overview.get("proventos_12m")
    if provents:
        parts.append(f"Proventos recebidos em 12 meses: {provents}.")
    if categories:
        top = ", ".join(f"{name} {value}" for name, value in list(categories.items())[:4])
        parts.append(f"Distribuição por classe: {top}.")
    return " ".join(parts).strip()


def _build_lines(overview: dict, categories: dict[str, str], positions: dict[str, dict]) -> list[str]:
    lines = []
    mapping = (
        ("Patrimônio total", overview.get("patrimonio")),
        ("Valor investido", overview.get("valor_investido")),
        ("Lucro total", overview.get("lucro_total")),
        ("Ganho de Capital", overview.get("ganho_capital")),
        ("Dividendos Recebidos", overview.get("dividendos_recebidos")),
        ("Proventos 12M", overview.get("proventos_12m")),
        ("Rentabilidade", overview.get("rentabilidade")),
        ("Variação", overview.get("variacao")),
    )
    for label, value in mapping:
        if value:
            lines.append(f"{label}: {value}")

    for name, value in categories.items():
        lines.append(f"{name}: {value} da carteira")

    for ticker, position in list(positions.items())[:8]:
        lines.append(
            f"{ticker}: preço médio {position['average_price']}, preço atual {position['current_price']}, "
            f"variação {position['variation']}, rentabilidade {position['rentability']}, saldo {position['balance']}"
        )
    return lines


def _build_metrics(overview: dict) -> list[str]:
    metrics = []
    mapping = (
        ("Patrimônio total", overview.get("patrimonio")),
        ("Valor investido", overview.get("valor_investido")),
        ("Lucro total", overview.get("lucro_total")),
        ("Ganho de Capital", overview.get("ganho_capital")),
        ("Dividendos Recebidos", overview.get("dividendos_recebidos")),
        ("Proventos Recebidos (12M)", overview.get("proventos_12m")),
        ("Rentabilidade", overview.get("rentabilidade")),
        ("Variação", overview.get("variacao")),
    )
    for label, value in mapping:
        if value:
            metrics.append(f"{label} {value}")
    return metrics


def _parse_wallet_html(html: str, wallet_url: str) -> dict:
    items = _extract_visible_items(html)
    if "Patrimônio total" not in items or "Ativos na Carteira" not in items:
        raise RuntimeError("A carteira pública não trouxe dados suficientes para extrair o resumo.")

    overview = _parse_overview(items)
    categories = _parse_category_breakdown(items)
    positions = _parse_primary_positions(items)
    asset_fundamentals = fetch_many_asset_fundamentals(list(positions.keys()))
    category_summaries = _parse_category_summaries(items)
    summary = _build_summary_text(overview, categories)
    lines = _build_lines(overview, categories, positions)
    metrics = _build_metrics(overview)

    saved = save_investment_snapshot(
        summary=summary,
        metrics=metrics,
        lines=lines,
        page_url=wallet_url,
        page_title=overview.get("page_title", ""),
        extra={
            "source": "investidor10_public_wallet",
            "wallet_name": overview.get("wallet_name", ""),
            "wallet_id": _extract_wallet_id(wallet_url),
            "metric_map": {
                "patrimonio": overview.get("patrimonio", ""),
                "valor investido": overview.get("valor_investido", ""),
                "lucro": overview.get("lucro_total", ""),
                "proventos": overview.get("proventos_total", "") or overview.get("proventos_12m", ""),
                "rentabilidade": overview.get("rentabilidade", ""),
                "variacao": overview.get("variacao", ""),
            },
            "asset_positions": positions,
            "asset_fundamentals": asset_fundamentals,
            "category_breakdown": categories,
            "category_summaries": category_summaries,
            "public_wallet_refreshed_at": time.time(),
        },
    )
    return saved


def refresh_public_wallet_snapshot(force: bool = True) -> dict:
    wallet_url = _wallet_url()
    if not wallet_url:
        raise RuntimeError("AXEL_INVESTIDOR10_WALLET_URL não está configurada.")
    if not _is_public_wallet_url(wallet_url):
        raise RuntimeError("A atualização sem abrir a carteira precisa de uma URL pública do Investidor10.")

    current = load_investment_snapshot()
    if not force and current.get("source") == "investidor10_public_wallet":
        updated_at = float(current.get("updated_at") or 0)
        if updated_at and (time.time() - updated_at) < SNAPSHOT_STALE_SECONDS:
            return current

    html = _run_headless_wallet_dump(wallet_url)
    return _parse_wallet_html(html, wallet_url)


def refresh_public_wallet_snapshot_if_stale() -> dict:
    try:
        return refresh_public_wallet_snapshot(force=False)
    except Exception:
        return load_investment_snapshot()


def format_public_wallet_refresh_result(force: bool = True) -> str:
    snapshot = refresh_public_wallet_snapshot(force=force)
    summary = str(snapshot.get("summary", "")).strip()
    if summary:
        return summary
    return "Atualizei a memória local da sua carteira pública."
