import json
import re
import subprocess
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from config import (
    EDGE_PROFILE_DIRECTORY,
    EDGE_USER_DATA_DIR,
    INVESTIDOR10_PRIVATE_WALLET_URL,
    INVESTIDOR10_WALLET_URL,
    WALLET_PLAYWRIGHT_CHANNEL,
    WALLET_PLAYWRIGHT_ENABLED,
    WALLET_PLAYWRIGHT_USER_DATA_DIR,
)
from memory.investment_asset_fundamentals import fetch_many_asset_fundamentals
from memory.investment_snapshot import load_investment_snapshot, save_investment_snapshot
from memory.profile import load_profile


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
PUBLIC_WALLET_DOM_PATH = MEMORY_DIR / "wallet_public_dom_full.html"
PRIVATE_WALLET_DOM_PATH = MEMORY_DIR / "wallet_private_dom_full.html"
EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)
SNAPSHOT_STALE_SECONDS = 20 * 60 * 60
PUBLIC_WALLET_API_TIMEOUT = 20


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


def _private_wallet_url() -> str:
    profile = load_profile()
    finance = profile.get("financas") if isinstance(profile, dict) else {}
    profile_url = ""
    if isinstance(finance, dict):
        profile_url = str(finance.get("investidor10_private_wallet_url", "")).strip()
    return profile_url or str(INVESTIDOR10_PRIVATE_WALLET_URL or "").strip()


def _is_public_wallet_url(url: str) -> bool:
    return "/wallet/public/" in str(url or "").lower()


def _is_private_wallet_url(url: str) -> bool:
    lowered = str(url or "").lower()
    return "/wallet/" in lowered and "/wallet/public/" not in lowered


def _extract_wallet_id(url: str) -> str:
    match = re.search(r"/wallet/public/(\d+)", str(url or ""))
    return match.group(1) if match else ""


def _edge_user_data_dir() -> str:
    raw = str(EDGE_USER_DATA_DIR or "").strip()
    if raw and Path(raw).exists():
        return raw
    return ""


def _wallet_playwright_profiles() -> list[dict]:
    profiles = []
    dedicated = str(WALLET_PLAYWRIGHT_USER_DATA_DIR or "").strip()
    if dedicated:
        path = Path(dedicated).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        profiles.append(
            {
                "user_data_dir": str(path),
                "profile_directory": "",
                "label": "perfil dedicado do Axel",
            }
        )

    edge_dir = _edge_user_data_dir()
    if edge_dir:
        profiles.append(
            {
                "user_data_dir": edge_dir,
                "profile_directory": str(EDGE_PROFILE_DIRECTORY or "").strip(),
                "label": "perfil principal do Edge",
            }
        )
    return profiles


def _run_playwright_wallet_text_legacy(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(f"Playwright nao esta disponivel: {exc}")

    user_data_dir = _edge_user_data_dir()
    if not user_data_dir:
        raise RuntimeError("Perfil do Edge nao configurado para leitura com Playwright.")

    with sync_playwright() as playwright:
        context = None
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="msedge",
                headless=False,
                viewport={"width": 1600, "height": 3000},
                args=["--disable-gpu"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(2500)

            texts = [page.locator("body").inner_text(timeout=10000)]

            # The summary page often keeps FIIs aggregated; try obvious wallet tabs/filters once.
            for label in ("FIIs", "Proventos", "Análise", "Patrimônio"):
                try:
                    locator = page.get_by_text(label, exact=True)
                    if locator.count() == 1 and locator.is_visible(timeout=1500):
                        locator.click(timeout=3000)
                        page.wait_for_timeout(1800)
                        texts.append(page.locator("body").inner_text(timeout=10000))
                except Exception:
                    continue

            return "\n".join(text for text in texts if text)
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass


def _run_playwright_wallet_text(url: str) -> str:
    if not WALLET_PLAYWRIGHT_ENABLED:
        raise RuntimeError("Leitura Playwright da carteira desativada.")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(f"Playwright nao esta disponivel: {exc}")

    profiles = _wallet_playwright_profiles()
    if not profiles:
        raise RuntimeError("Nenhum perfil de navegador configurado para leitura com Playwright.")

    last_error = None
    with sync_playwright() as playwright:
        channel = str(WALLET_PLAYWRIGHT_CHANNEL or "msedge").strip() or "msedge"
        for profile in profiles:
            context = None
            try:
                args = ["--disable-gpu"]
                profile_directory = str(profile.get("profile_directory") or "").strip()
                if profile_directory:
                    args.append(f"--profile-directory={profile_directory}")

                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(profile.get("user_data_dir") or ""),
                    channel=channel,
                    headless=False,
                    viewport={"width": 1600, "height": 3000},
                    args=args,
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(2500)

                texts = [page.locator("body").inner_text(timeout=10000)]

                # The summary page often keeps FIIs aggregated; try useful wallet tabs once.
                for label in ("Patrimônio", "FIIs", "Proventos", "Análise"):
                    try:
                        locator = page.get_by_text(label, exact=True).first
                        if locator.count() and locator.is_visible(timeout=1500):
                            locator.click(timeout=3000)
                            page.wait_for_timeout(1800)
                            texts.append(page.locator("body").inner_text(timeout=10000))
                    except Exception:
                        continue

                combined = "\n".join(text for text in texts if text)
                if combined.strip():
                    return combined
            except Exception as exc:
                last_error = exc
            finally:
                if context is not None:
                    try:
                        context.close()
                    except Exception:
                        pass

    raise RuntimeError(f"Playwright nao conseguiu ler a carteira: {last_error}")


def _run_playwright_wallet_dump(url: str) -> str:
    text = _run_playwright_wallet_text(url)
    if not text.strip():
        raise RuntimeError("Playwright nao conseguiu extrair texto util da carteira.")
    PRIVATE_WALLET_DOM_PATH.with_suffix(".playwright.txt").write_text(text, encoding="utf-8")
    return text


def _fetch_public_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Axel/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(request, timeout=PUBLIC_WALLET_API_TIMEOUT) as response:
        payload = response.read().decode("utf-8", errors="replace")
    data = json.loads(payload)
    return data if isinstance(data, dict) else {}


def _fetch_public_wallet_bootstrap(wallet_id: str, wallet_hash: str = "") -> dict:
    if not wallet_id:
        return {}
    url = f"https://investidor10.com.br/wallet/api/proxy/wallet-app/get-user-bootstrap?wallet_id={wallet_id}"
    if wallet_hash:
        url += f"&hash={wallet_hash}"
    try:
        return _fetch_public_json(url)
    except Exception:
        return {}


def _fetch_public_wallet_summary_info(wallet_id: str) -> dict:
    if not wallet_id:
        return {}
    url = f"https://investidor10.com.br/wallet/api/proxy/wallet-app/summary/info/{wallet_id}"
    try:
        return _fetch_public_json(url)
    except Exception:
        return {}


def _run_headless_wallet_dump(url: str, *, use_logged_profile: bool = False) -> str:
    edge_path = _find_edge_path()
    if not edge_path:
        raise RuntimeError("Nao encontrei o Microsoft Edge para atualizar a carteira publica.")

    command = [
        edge_path,
        "--headless=new",
        "--disable-gpu",
        "--window-size=1600,3000",
        "--virtual-time-budget=12000",
    ]
    if use_logged_profile:
        user_data_dir = _edge_user_data_dir()
        if user_data_dir:
            command.append(f"--user-data-dir={user_data_dir}")
        profile_directory = str(EDGE_PROFILE_DIRECTORY or "").strip()
        if profile_directory:
            command.append(f"--profile-directory={profile_directory}")
    command.extend(["--dump-dom", url])

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    if completed.returncode != 0:
        raise RuntimeError("Nao consegui renderizar a carteira publica em modo headless.")

    html = completed.stdout or ""
    if not html.strip():
        raise RuntimeError("A carteira publica nao retornou HTML util.")

    target_path = PRIVATE_WALLET_DOM_PATH if use_logged_profile else PUBLIC_WALLET_DOM_PATH
    target_path.write_text(html, encoding="utf-8")
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


def _extract_items_from_text_blob(text: str) -> list[str]:
    items = []
    for raw in re.split(r"[\r\n]+", str(text or "")):
        cleaned = re.sub(r"\s+", " ", raw or "").strip()
        if cleaned:
            items.append(cleaned)
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
            categories[label] = _normalize_percent_label(value)
            i += 2
            continue
        i += 1
    return categories


def _normalize_category_name(value: str) -> str:
    raw = str(value or "").strip()
    lowered = raw.lower()
    if "fii" in lowered:
        return "FIIs"
    if "cript" in lowered:
        return "Criptomoedas"
    if "tesouro" in lowered:
        return "Tesouro Direto"
    if lowered in {"ações", "acoes", "ação", "acao"}:
        return "Ações"
    return raw


def _parse_visible_positions(items: list[str]) -> dict[str, dict]:
    positions = {}
    row_size = 11
    known_categories = {"Ações", "FIIs", "Criptomoedas", "Tesouro Direto"}
    current_category = ""
    index = 0

    while index < len(items):
        token = str(items[index] or "").strip()
        normalized_category = _normalize_category_name(token)
        if normalized_category in known_categories:
            current_category = normalized_category
            index += 1
            continue
        if token != "Ativo":
            index += 1
            continue

        cursor = index + row_size
        while cursor + row_size - 1 < len(items):
            if str(items[cursor] or "").strip() == "Valor total":
                break
            chunk = items[cursor : cursor + row_size]
            ticker = str(chunk[0] or "").strip().upper()
            if not re.fullmatch(r"[A-Z]{4}\d{1,2}", ticker):
                cursor += 1
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
                "category": current_category or "Ações",
            }
            cursor += row_size
        index = cursor + 1
    return positions


def _split_private_compound_metric(token: str) -> tuple[str, str]:
    parts = [part for part in re.split(r"\s+", str(token or "").strip()) if part]
    if len(parts) >= 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return parts[0], ""
    return "", ""


def _looks_like_private_position_row(chunk: list[str]) -> bool:
    if len(chunk) < 12:
        return False
    if not re.fullmatch(r"[A-Z]{4}\d{1,2}", str(chunk[0] or "").strip().upper()):
        return False
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", str(chunk[1] or "").strip()):
        return False
    if not str(chunk[2] or "").strip().startswith("R$"):
        return False
    if not str(chunk[3] or "").strip().startswith("R$"):
        return False
    if not re.fullmatch(r"-?\d+(?:[.,]\d+)?%", str(chunk[4] or "").strip()):
        return False
    if not re.fullmatch(r"-?\d+(?:[.,]\d+)?%", str(chunk[5] or "").strip()):
        return False
    if not str(chunk[6] or "").strip().startswith("R$"):
        return False
    return True


def _parse_private_visible_positions(items: list[str]) -> dict[str, dict]:
    positions = {}
    known_categories = {"Ações", "FIIs", "Criptomoedas", "Tesouro Direto"}
    stop_markers = {"Nacional", "Internacional", "Startups e Alternativos", "Conteúdo", "Ferramentas", "Cursos"}
    current_category = ""
    cursor = 0

    while cursor < len(items):
        token = str(items[cursor] or "").strip()

        if token in known_categories:
            current_category = token
            cursor += 1
            continue

        if token == "Opções":
            cursor += 1
            while cursor + 11 < len(items):
                row_start = str(items[cursor] or "").strip().upper()
                if row_start in known_categories or row_start in stop_markers:
                    break
                if not re.fullmatch(r"[A-Z]{4}\d{1,2}", row_start):
                    cursor += 1
                    continue

                chunk = items[cursor : cursor + 12]
                if not _looks_like_private_position_row(chunk):
                    cursor += 1
                    continue
                rating, dividend_yield = _split_private_compound_metric(chunk[7])
                positions[row_start] = {
                    "ticker": row_start,
                    "quantity": chunk[1],
                    "average_price": chunk[2],
                    "current_price": chunk[3],
                    "variation": chunk[4],
                    "rentability": chunk[5],
                    "balance": chunk[6],
                    "rating": rating,
                    "dividend_yield": dividend_yield,
                    "score": chunk[8],
                    "portfolio_percentage": chunk[9],
                    "ideal_percentage": chunk[10],
                    "buy_more": chunk[11],
                    "category": current_category or "Ações",
                }
                cursor += 12
            continue

        cursor += 1

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


def _parse_private_category_summaries(items: list[str]) -> dict[str, dict]:
    summaries = {}
    category_names = ("Ações", "FIIs", "Criptomoedas", "Tesouro Direto")
    i = 0

    while i + 12 < len(items):
        token = str(items[i] or "").strip()
        if token not in category_names:
            i += 1
            continue
        if str(items[i + 1] or "").strip() != "Ativos":
            i += 1
            continue

        summaries[token] = {
            "assets_count": f"({str(items[i + 2] or '').strip()} ativos)",
            "assets_count_number": int(re.sub(r"[^\d]", "", str(items[i + 2] or "")) or 0),
            "value_total": items[i + 4],
            "variation": _normalize_percent_label(items[i + 6]),
            "rentability": _normalize_percent_label(items[i + 8]),
            "portfolio_percentage": _normalize_percent_label(items[i + 10]),
            "ideal_percentage": _normalize_percent_label(items[i + 12] if i + 12 < len(items) else ""),
            "class": token,
        }
        i += 13

    return summaries


def _parse_private_allocation_positions(items: list[str]) -> dict[str, dict]:
    positions: dict[str, dict] = {}
    category_names = {"Ações", "FIIs", "Criptomoedas", "Tesouro Direto"}
    stop_markers = {
        "Nacional",
        "Internacional",
        "Startups e Alternativos",
        "Conteúdo",
        "Ferramentas",
        "Cursos",
    }
    skip_tokens = {
        "Consolidado",
        "Por tipo",
        "Por segmento",
        "Exibir posição ideal",
        "Ativos",
        "Exposição ao exterior",
    }
    current_category = ""
    cursor = 0

    while cursor + 2 < len(items):
        token = str(items[cursor] or "").strip()
        if token in category_names:
            current_category = token
            cursor += 1
            continue
        if token in stop_markers:
            current_category = ""
            cursor += 1
            continue
        if not current_category or token in skip_tokens:
            cursor += 1
            continue

        ticker = token.upper()
        value = str(items[cursor + 1] or "").strip()
        percent = _normalize_percent_label(str(items[cursor + 2] or "").strip())
        if (
            re.fullmatch(r"[A-Z]{3,5}\d{0,2}", ticker)
            and value.startswith("R$")
            and re.fullmatch(r"-?\d+(?:[.,]\d+)?%", percent)
        ):
            positions[ticker] = {
                "ticker": ticker,
                "quantity": "",
                "average_price": "",
                "current_price": "",
                "variation": "",
                "rentability": "",
                "balance": value,
                "rating": "",
                "dividend_yield": "",
                "score": "",
                "portfolio_percentage": percent,
                "ideal_percentage": "",
                "buy_more": "",
                "category": current_category,
                "source_detail": "private_allocation",
            }
            cursor += 3
            continue

        cursor += 1

    return positions


def _format_brl_from_decimal(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        number = float(raw)
    except Exception:
        return raw
    formatted = f"{number:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent_from_number(value) -> str:
    raw = str(value or "").strip()
    if raw == "":
        return ""
    try:
        number = float(raw)
    except Exception:
        return raw
    formatted = f"{number:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".") + "%"


def _normalize_percent_label(value: str) -> str:
    raw = str(value or "").strip()
    if re.fullmatch(r"-?\d+\.\d+%", raw):
        return raw.replace(".", ",")
    return raw


def _parse_category_summaries_from_api(summary_info: dict) -> tuple[dict[str, str], dict[str, dict]]:
    category_breakdown: dict[str, str] = {}
    category_summaries: dict[str, dict] = {}

    for row in list(summary_info.get("tickers") or []) + list(summary_info.get("others_tickers") or []):
        category_name = _normalize_category_name(row.get("class"))
        if not category_name:
            continue
        portfolio_percentage = _format_percent_from_number(row.get("percent"))
        category_breakdown[category_name] = portfolio_percentage
        category_summaries[category_name] = {
            "assets_count": f"({int(row.get('count') or 0)} ativos)" if str(row.get("count", "")).strip() else "",
            "assets_count_number": int(row.get("count") or 0),
            "value_total": _format_brl_from_decimal(row.get("equity")),
            "variation": _format_percent_from_number(row.get("rentability")),
            "rentability": _format_percent_from_number(row.get("weighted_return")),
            "portfolio_percentage": portfolio_percentage,
            "ideal_percentage": _format_percent_from_number(row.get("balancing")),
            "class": category_name,
            "type": str(row.get("type") or "").strip(),
        }

    return category_breakdown, category_summaries


def _extract_dividend_events_map(asset_fundamentals: dict[str, dict]) -> dict[str, list[dict]]:
    events_map: dict[str, list[dict]] = {}
    for ticker, fundamentals in (asset_fundamentals or {}).items():
        events = fundamentals.get("next_dividend_events")
        if isinstance(events, list) and events:
            events_map[str(ticker).upper()] = events
    return events_map


def _build_unresolved_category_counts(positions: dict[str, dict], category_summaries: dict[str, dict]) -> dict[str, dict]:
    captured_by_category: dict[str, int] = {}
    for position in positions.values():
        category = _normalize_category_name(position.get("category"))
        if not category:
            continue
        captured_by_category[category] = captured_by_category.get(category, 0) + 1

    unresolved: dict[str, dict] = {}
    for category, summary in (category_summaries or {}).items():
        reported = int(summary.get("assets_count_number") or 0)
        captured = int(captured_by_category.get(category) or 0)
        if reported > captured:
            unresolved[category] = {"reported": reported, "captured": captured}
    return unresolved


def _build_summary_text(overview: dict, categories: dict[str, str], wallet_url: str = "") -> str:
    parts = []
    if _is_private_wallet_url(wallet_url):
        opening = "Carteira atualizada"
    else:
        opening = "Carteira pública atualizada"
    patrimony = overview.get("patrimonio")
    if patrimony:
        parts.append(f"{opening} com patrimônio total de {patrimony}.")
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


def _parse_wallet_items(items: list[str], wallet_url: str) -> dict:
    if "Patrimônio total" not in items or "Ativos na Carteira" not in items:
        raise RuntimeError("A carteira pública não trouxe dados suficientes para extrair o resumo.")

    wallet_id = _extract_wallet_id(wallet_url)
    overview = _parse_overview(items)
    visible_categories = _parse_category_breakdown(items)
    positions = _parse_visible_positions(items)
    visible_category_summaries = _parse_category_summaries(items)
    if _is_private_wallet_url(wallet_url):
        private_positions = _parse_private_visible_positions(items)
        if private_positions:
            positions = private_positions
        allocation_positions = _parse_private_allocation_positions(items)
        for ticker, allocation_position in allocation_positions.items():
            if ticker in positions:
                positions[ticker].setdefault("allocation_balance", allocation_position.get("balance", ""))
                positions[ticker].setdefault(
                    "allocation_percentage",
                    allocation_position.get("portfolio_percentage", ""),
                )
                continue
            positions[ticker] = allocation_position
        private_category_summaries = _parse_private_category_summaries(items)
        if private_category_summaries:
            visible_category_summaries.update(private_category_summaries)
    public_bootstrap = _fetch_public_wallet_bootstrap(wallet_id) if wallet_id else {}
    public_summary_info = _fetch_public_wallet_summary_info(wallet_id) if wallet_id else {}
    api_categories, api_category_summaries = _parse_category_summaries_from_api(public_summary_info) if public_summary_info else ({}, {})
    categories = dict(visible_categories)
    categories.update(api_categories)
    asset_fundamentals = fetch_many_asset_fundamentals(list(positions.keys()))
    asset_dividend_events = _extract_dividend_events_map(asset_fundamentals)
    category_summaries = dict(visible_category_summaries)
    category_summaries.update(api_category_summaries)
    unresolved_category_counts = _build_unresolved_category_counts(positions, category_summaries)
    summary = _build_summary_text(overview, categories, wallet_url=wallet_url)
    lines = _build_lines(overview, categories, positions)
    metrics = _build_metrics(overview)

    saved = save_investment_snapshot(
        summary=summary,
        metrics=metrics,
        lines=lines,
        page_url=wallet_url,
        page_title=overview.get("page_title", ""),
        extra={
            "source": "investidor10_public_wallet" if _is_public_wallet_url(wallet_url) else "investidor10_private_wallet",
            "wallet_name": overview.get("wallet_name", ""),
            "wallet_id": wallet_id,
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
            "asset_dividend_events": asset_dividend_events,
            "category_breakdown": categories,
            "category_summaries": category_summaries,
            "public_wallet_bootstrap": public_bootstrap,
            "public_wallet_summary_info": public_summary_info,
            "unresolved_category_counts": unresolved_category_counts,
            "public_wallet_refreshed_at": time.time(),
        },
    )
    return saved


def _parse_wallet_html(html: str, wallet_url: str) -> dict:
    items = _extract_visible_items(html)
    return _parse_wallet_items(items, wallet_url)


def parse_wallet_text_blob(text: str, wallet_url: str) -> dict:
    items = _extract_items_from_text_blob(text)
    return _parse_wallet_items(items, wallet_url)


def is_public_wallet_snapshot_stale(snapshot: dict | None = None, max_age_seconds: float = SNAPSHOT_STALE_SECONDS) -> bool:
    current = snapshot if isinstance(snapshot, dict) else load_investment_snapshot()
    if str(current.get("source", "")).strip() != "investidor10_public_wallet":
        return True
    updated_at = float(current.get("updated_at") or 0)
    if not updated_at:
        return True
    return (time.time() - updated_at) >= float(max_age_seconds)


def is_wallet_snapshot_stale(snapshot: dict | None = None, max_age_seconds: float = SNAPSHOT_STALE_SECONDS) -> bool:
    current = snapshot if isinstance(snapshot, dict) else load_investment_snapshot()
    source = str(current.get("source", "")).strip()
    if _private_wallet_url() and source != "investidor10_private_wallet":
        return True
    if source not in {"investidor10_public_wallet", "investidor10_private_wallet"}:
        return True
    updated_at = float(current.get("updated_at") or 0)
    if not updated_at:
        return True
    return (time.time() - updated_at) >= float(max_age_seconds)


def refresh_public_wallet_snapshot(force: bool = True, max_age_seconds: float = SNAPSHOT_STALE_SECONDS) -> dict:
    wallet_url = _wallet_url()
    if not wallet_url:
        raise RuntimeError("AXEL_INVESTIDOR10_WALLET_URL não está configurada.")
    if not _is_public_wallet_url(wallet_url):
        raise RuntimeError("A atualização sem abrir a carteira precisa de uma URL pública do Investidor10.")

    current = load_investment_snapshot()
    if not force and not is_public_wallet_snapshot_stale(current, max_age_seconds=max_age_seconds):
        return current

    html = _run_headless_wallet_dump(wallet_url)
    return _parse_wallet_html(html, wallet_url)


def refresh_private_wallet_snapshot(force: bool = True, max_age_seconds: float = SNAPSHOT_STALE_SECONDS) -> dict:
    wallet_url = _private_wallet_url()
    if not wallet_url:
        raise RuntimeError("AXEL_INVESTIDOR10_PRIVATE_WALLET_URL nao esta configurada.")
    if not _is_private_wallet_url(wallet_url):
        raise RuntimeError("A URL privada do Investidor10 parece invalida.")

    current = load_investment_snapshot()
    if not force and not is_wallet_snapshot_stale(current, max_age_seconds=max_age_seconds):
        return current

    try:
        text = _run_playwright_wallet_dump(wallet_url)
        return parse_wallet_text_blob(text, wallet_url)
    except Exception:
        html = _run_headless_wallet_dump(wallet_url, use_logged_profile=True)
        return _parse_wallet_html(html, wallet_url)


def refresh_wallet_snapshot_auto(force: bool = True, max_age_seconds: float = SNAPSHOT_STALE_SECONDS) -> dict:
    private_url = _private_wallet_url()
    if private_url:
        return refresh_private_wallet_snapshot(force=force, max_age_seconds=max_age_seconds)
    wallet_url = _wallet_url()
    if _is_public_wallet_url(wallet_url):
        return refresh_public_wallet_snapshot(force=force, max_age_seconds=max_age_seconds)
    return refresh_public_wallet_snapshot(force=force, max_age_seconds=max_age_seconds)


def refresh_public_wallet_snapshot_if_stale(max_age_seconds: float = SNAPSHOT_STALE_SECONDS) -> dict:
    try:
        return refresh_public_wallet_snapshot(force=False, max_age_seconds=max_age_seconds)
    except Exception:
        return load_investment_snapshot()


def refresh_wallet_snapshot_if_stale(max_age_seconds: float = SNAPSHOT_STALE_SECONDS) -> dict:
    try:
        return refresh_wallet_snapshot_auto(force=False, max_age_seconds=max_age_seconds)
    except Exception:
        return load_investment_snapshot()


def format_public_wallet_refresh_result(force: bool = True) -> str:
    snapshot = refresh_wallet_snapshot_auto(force=force)
    summary = str(snapshot.get("summary", "")).strip()
    if summary:
        return summary
    return "Atualizei a memória local da sua carteira pública."
