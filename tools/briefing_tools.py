from __future__ import annotations

from datetime import datetime
from pathlib import Path

from memory.agenda import agenda_brief_summary
from memory.investment_snapshot import load_investment_snapshot
from memory.news_api import summarize_asset_news
from tools.weather_tools import get_weather_snapshot


TODO_PATH = Path("memory/todo.md")


def _polish_pt_br(text: str) -> str:
    polished = str(text or "")
    for hidden in ("\u2060", "\u200c", "\u200b", "\ufeff"):
        polished = polished.replace(hidden, "")
    replacements = {
        "predominio": "predomínio",
        "proximos": "próximos",
        "esta livre": "está livre",
        "esta vazia": "está vazia",
        "esta com": "está com",
        " estao ": " estão ",
        "Patrimonio": "Patrimônio",
        "patrimonio": "patrimônio",
        "relatorio": "relatório",
        "visao": "visão",
        "precisao": "precisão",
        "maxima": "máxima",
        "quilometros": "quilômetros",
        "Noticia": "Notícia",
        "ceu": "céu",
        "graficos": "gráficos",
    }
    for source, target in replacements.items():
        polished = polished.replace(source, target)
    return polished


def _time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia, chefe."
    if hour < 18:
        return "Boa tarde, chefe."
    return "Boa noite, chefe."


def _load_open_todo_items(limit: int = 2) -> list[str]:
    if not TODO_PATH.exists():
        return []

    items: list[str] = []
    for raw_line in TODO_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("- [ ] "):
            value = line[6:].strip().rstrip(".;")
            if value:
                items.append(value)
        if len(items) >= limit:
            break
    return items


def todo_brief_summary(limit: int = 2) -> str:
    items = _load_open_todo_items(limit=limit)
    if not items:
        return "Sem tarefas em aberto de destaque."
    return "Tarefas em aberto: " + " ; ".join(items) + "."


def _climate_brief() -> str:
    try:
        snapshot = get_weather_snapshot(None)
    except Exception:
        return "Clima indisponível no momento."

    city = str(snapshot.location_label or "sua cidade").split(",")[0].strip()
    parts = []
    if snapshot.weather_label and snapshot.temperature_c is not None:
        parts.append(
            f"Agora em {city}, predomínio de sol e {round(snapshot.temperature_c)} graus."
            if snapshot.weather_label == "predominio de sol"
            else f"Agora em {city}, {snapshot.weather_label} e {round(snapshot.temperature_c)} graus."
        )
    elif snapshot.temperature_c is not None:
        parts.append(f"Agora em {city}, {round(snapshot.temperature_c)} graus.")

    if snapshot.rain_chance_percent is not None and snapshot.rain_chance_percent >= 70:
        parts.append(f"Chance alta de chuva hoje, perto de {round(snapshot.rain_chance_percent)} por cento.")

    return " ".join(parts) if parts else "Clima indisponível no momento."


def _investment_brief() -> str:
    snapshot = load_investment_snapshot()
    metrics = snapshot.get("metric_map") or {}
    patrimonio = str(metrics.get("patrimonio") or "").strip()
    investido = str(metrics.get("valor investido") or "").strip()
    rentabilidade = str(metrics.get("rentabilidade") or "").strip()
    proventos = str(metrics.get("proventos") or "").strip()

    parts = ["Carteira atualizada."]
    if patrimonio:
        parts.append(f"Patrimônio em {patrimonio}.")
    if investido:
        parts.append(f"Valor investido em {investido}.")
    if rentabilidade:
        parts.append(f"Rentabilidade em {rentabilidade}.")
    if proventos:
        parts.append(f"Proventos em {proventos}.")
    return " ".join(parts)


def _portfolio_news_brief() -> str:
    snapshot = load_investment_snapshot()
    positions = snapshot.get("asset_positions") or {}
    fundamentals = snapshot.get("asset_fundamentals") or {}
    ranked = []
    for ticker, position in positions.items():
        raw_weight = str((position or {}).get("portfolio_percentage") or "").replace("%", "").replace(",", ".").strip()
        try:
            weight = float(raw_weight)
        except Exception:
            weight = 0.0
        ranked.append((ticker, weight))

    ranked.sort(key=lambda item: item[1], reverse=True)

    for ticker, _weight in ranked[:3]:
        fund = fundamentals.get(ticker) or {}
        company_name = str(fund.get("company_name") or "").strip()
        summary = summarize_asset_news(
            ticker,
            company_name=company_name,
            market_data=fund,
        )
        if not summary:
            continue

        normalized = summary.lower()
        if "nada com confiança suficiente" in normalized or "sensacionalista" in normalized:
            continue

        summary = summary.replace(f"Encontrei sinais relevantes sobre {ticker}. ", "")
        summary = summary.replace(f"Encontrei sinais relevantes sobre {ticker}.", "")
        return f"Notícia relevante: {summary}"

    return "Sem notícia relevante de destaque na carteira agora."


def _short_agenda_brief() -> str:
    summary = agenda_brief_summary()
    return _polish_pt_br(summary.replace("amanha", "amanhã"))


def daily_briefing() -> str:
    sections = [
        _time_greeting(),
        _climate_brief(),
        _short_agenda_brief(),
        todo_brief_summary(),
        _portfolio_news_brief(),
        _investment_brief(),
    ]
    return _polish_pt_br(" ".join(part.strip() for part in sections if str(part or "").strip()))
