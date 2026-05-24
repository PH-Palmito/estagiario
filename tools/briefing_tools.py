from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from memory.agenda import agenda_brief_summary
from memory.auto_advances import load_auto_advances
from memory.investment_snapshot import (
    format_investment_financial_report,
    format_upcoming_dividend_brief,
    load_investment_snapshot,
)
from memory.reminders import list_reminders
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


def todo_brief_summary(limit: int = 1) -> str:
    try:
        advances = load_auto_advances()
    except Exception:
        advances = []

    if advances:
        title = str((advances[0] or {}).get("title") or "").strip().rstrip(".;")
        if title:
            return "Próximo avanço sugerido: " + title + "."

    items = _load_open_todo_items(limit=limit)
    if not items:
        return "Sem tarefas em aberto de destaque."
    if len(items) == 1:
        return "Próximo avanço sugerido: " + items[0] + "."
    return "Próximos avanços sugeridos: " + " ; ".join(items) + "."


def _compact_text(text: str, max_chars: int = 300) -> str:
    compact = " ".join(str(text or "").split()).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;") + "."


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
        parts.append("Vale sair preparado para chuva.")
    elif snapshot.max_c is not None and snapshot.max_c >= 32:
        parts.append("Dia quente; vale hidratar e evitar deslocamento no pico do calor.")

    return " ".join(parts) if parts else "Clima indisponível no momento."


def _investment_brief() -> str:
    snapshot = load_investment_snapshot()
    metrics = snapshot.get("metric_map") or {}
    patrimonio = str(metrics.get("patrimonio") or "").strip()
    rentabilidade = str(metrics.get("rentabilidade") or "").strip()

    parts = ["Carteira monitorada:"]
    if patrimonio:
        parts.append(f"patrimônio {patrimonio}.")
    if rentabilidade:
        parts.append(f"Rentabilidade {rentabilidade}.")
    return " ".join(parts)


def _portfolio_radar_brief() -> str:
    try:
        report = format_investment_financial_report()
    except Exception:
        return "Radar da carteira indisponível agora."

    text = _polish_pt_br(report)
    if "Ainda não tenho dados suficientes" in text or "Ainda năo tenho dados suficientes" in text:
        return "Radar da carteira: atualize a carteira para eu cruzar alertas financeiros."

    text = text.replace("Relatório financeiro.", "").strip()
    text = re.sub(
        r"^Resumo:.*?(?=(Alocação atual:|Atenção:|Preço-teto:|Próximo dividendo|Notícia nova|Leitura geral:))",
        "",
        text,
        flags=re.I,
    ).strip()
    text = re.sub(
        r"^Alocação atual:.*?(?=(Atenção:|Preço-teto:|Próximo dividendo|Notícia nova|Leitura geral:))",
        "",
        text,
        flags=re.I,
    ).strip()

    if not text:
        return "Radar da carteira: sem alerta crítico novo salvo agora."

    signals = []
    attention_match = re.search(r"Atenção:\s*(.*?)(?=(Preço-teto:|Próximo dividendo|Notícia nova|Leitura geral:|$))", text, flags=re.I)
    if attention_match:
        tickers = re.findall(r"\b[A-Z]{4}\d{1,2}\b", attention_match.group(1))
        if tickers:
            signals.append("atenção em " + ", ".join(dict.fromkeys(tickers[:2])))

    ceiling_match = re.search(r"Preço-teto:\s*(.*?)(?=(Próximo dividendo|Notícia nova|Leitura geral:|$))", text, flags=re.I)
    if ceiling_match:
        tickers = re.findall(r"\b[A-Z]{4}\d{1,2}\b", ceiling_match.group(1))
        if tickers:
            signals.append("acima do teto: " + ", ".join(dict.fromkeys(tickers[:2])))

    dividend_match = re.search(r"Próximo dividendo no radar:\s*(.*?)(?=(Notícia nova|Leitura geral:|$))", text, flags=re.I)
    if dividend_match:
        signals.append(_compact_text(dividend_match.group(1).strip(), max_chars=80).rstrip("."))

    if signals:
        return "Radar da carteira: " + "; ".join(signals) + "."

    if "sem alerta crítico novo" in text.lower() or "leitura geral:" in text.lower():
        return "Radar da carteira: sem alerta novo agora."

    return "Radar da carteira: " + _compact_text(text, max_chars=220)


def _short_agenda_brief() -> str:
    summary = agenda_brief_summary()
    return _polish_pt_br(summary.replace("amanha", "amanhã"))


def _dividend_agenda_brief() -> str:
    try:
        return _polish_pt_br(format_upcoming_dividend_brief(limit=2))
    except Exception:
        return ""


def _short_reminders_brief() -> str:
    summary = list_reminders(limit=3)
    if "Nao ha lembretes pendentes" in summary:
        return ""
    return _compact_text(_polish_pt_br(summary), max_chars=220)


def daily_briefing() -> str:
    sections = [
        _time_greeting(),
        _climate_brief(),
        _short_agenda_brief(),
        _investment_brief(),
        _dividend_agenda_brief(),
        _portfolio_radar_brief(),
        todo_brief_summary(),
        _short_reminders_brief(),
    ]
    return _polish_pt_br(" ".join(part.strip() for part in sections if str(part or "").strip()))


def daily_routine() -> str:
    sections = [
        daily_briefing(),
        "Rotina pronta: comandos, voz, navegador, lembretes e carteira local ficam no caminho curto.",
        "Noticias, visao pesada e treinos entram sob demanda, para nao disputar atencao quando voce nao pediu.",
        "Atalho pratico: diga 'modo programacao' para abrir o painel de trabalho, ou 'saude do Axel' para ver o painel operacional.",
    ]
    return _polish_pt_br(" ".join(part.strip() for part in sections if str(part or "").strip()))
