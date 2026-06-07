from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from time import time

from core.cache_policy import BRIEFING_CACHE_POLICY, is_cache_fresh
from memory.agenda import agenda_brief_summary
from memory.auto_advances import load_auto_advances
from memory.investment_formatting import format_percent, parse_currency_value, parse_percent_value
from memory.investment_snapshot import (
    format_investment_financial_report,
    format_upcoming_dividend_brief,
    load_investment_snapshot,
)
from memory.reminders import list_reminders
from tools.weather_tools import get_weather_snapshot

TODO_PATH = Path("memory/todo.md")
BRIEFING_CACHE_PATH = BRIEFING_CACHE_POLICY.path
INVESTMENT_HISTORY_PATH = Path("memory/investment_snapshot_history.json")
DEFAULT_BRIEFING_CACHE_TTL_SECONDS = BRIEFING_CACHE_POLICY.ttl_seconds
BRIEFING_CONTENT_VERSION = 3

B3_HOLIDAYS_2026 = {
    "2026-01-01",
    "2026-02-16",
    "2026-02-17",
    "2026-04-03",
    "2026-04-21",
    "2026-05-01",
    "2026-06-04",
    "2026-09-07",
    "2026-10-12",
    "2026-11-02",
    "2026-11-20",
    "2026-12-24",
    "2026-12-25",
    "2026-12-31",
}
B3_MARKET_OPEN_HOUR = 10
B3_MARKET_CLOSE_HOUR = 17


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
        "ultimo": "último",
        "estavel": "estável",
        "historico": "histórico",
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


def focus_brief_summary() -> str:
    summary = todo_brief_summary(limit=1).strip()
    if not summary or summary == "Sem tarefas em aberto de destaque.":
        return "Foco do dia: escolha uma prioridade curta e finalize antes de abrir novas frentes."
    return "Foco do dia: " + summary[0].lower() + summary[1:]


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


def _today() -> date:
    return datetime.now().date()


def _current_hour() -> int:
    return datetime.now().hour


def _is_b3_market_day(day: date | None = None) -> bool:
    current = day or _today()
    if current.weekday() >= 5:
        return False
    if current.isoformat() in B3_HOLIDAYS_2026:
        return False
    return True


def _market_session_label(hour: int | None = None) -> str:
    current_hour = _current_hour() if hour is None else int(hour)
    if current_hour < B3_MARKET_OPEN_HOUR:
        return "pre_open"
    if current_hour < B3_MARKET_CLOSE_HOUR:
        return "open"
    return "closed"


def _load_investment_history() -> list[dict]:
    if not INVESTMENT_HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(INVESTMENT_HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    history = [item for item in items if isinstance(item, dict) and str(item.get("date") or "").strip()]
    history.sort(key=lambda item: (str(item.get("date") or ""), float(item.get("updated_at") or 0)))
    return history


def _crypto_balance_value(snapshot: dict) -> float | None:
    positions = snapshot.get("asset_positions")
    if not isinstance(positions, dict):
        return None
    total = 0.0
    found = False
    for position in positions.values():
        if not isinstance(position, dict):
            continue
        category = str(position.get("category") or "").strip().lower()
        if not category.startswith("cript"):
            continue
        value = parse_currency_value(position.get("balance"))
        if value is None:
            continue
        total += value
        found = True
    return total if found else None


def _current_investment_sample(snapshot: dict) -> dict:
    metrics = snapshot.get("metric_map") or {}
    sample = {"date": _today().isoformat(), "updated_at": float(snapshot.get("updated_at") or 0)}
    patrimonio = parse_currency_value(metrics.get("patrimonio"))
    rentabilidade = parse_percent_value(metrics.get("rentabilidade"))
    variacao = parse_percent_value(metrics.get("variacao"))
    if patrimonio is not None:
        sample["patrimonio_value"] = patrimonio
    if rentabilidade is not None:
        sample["rentabilidade_percent"] = rentabilidade
    if variacao is not None:
        sample["variacao_percent"] = variacao
    crypto_balance = _crypto_balance_value(snapshot)
    if crypto_balance is not None:
        sample["crypto_balance_value"] = crypto_balance
    return sample


def _sample_date(sample: dict) -> date | None:
    try:
        return date.fromisoformat(str(sample.get("date") or "")[:10])
    except Exception:
        return None


def _latest_sample_before(history: list[dict], day: date) -> dict | None:
    candidates = [item for item in history if (_sample_date(item) or day) < day]
    return candidates[-1] if candidates else None


def _week_baseline_sample(history: list[dict], day: date) -> dict | None:
    week_start = day - timedelta(days=day.weekday())
    same_week = [item for item in history if week_start <= (_sample_date(item) or day) < day]
    if same_week:
        return same_week[0]
    return _latest_sample_before(history, day)


def _percent_change(current_value: float | None, base_value: float | None) -> float | None:
    if current_value is None or base_value in (None, 0):
        return None
    return ((float(current_value) - float(base_value)) / float(base_value)) * 100.0


def _direction_word(value: float) -> str:
    if value > 0:
        return "subiu"
    if value < 0:
        return "caiu"
    return "ficou estavel"


def _format_change_sentence(prefix: str, change: float, period: str) -> str:
    direction = _direction_word(change)
    if direction == "ficou estavel":
        return f"{prefix} ficou estavel {period}."
    return f"{prefix} {direction} {format_percent(abs(change), digits=1)} {period}."


def _format_market_change_sentence(change: float, *, weekly: bool = False) -> str:
    direction = "em alta" if change > 0 else "em baixa" if change < 0 else "estavel"
    value = format_percent(abs(change), digits=1)
    session = _market_session_label()
    if weekly:
        if direction == "estavel":
            return "Carteira ficou estavel na semana."
        return f"Carteira fechou a semana {direction}, {value}."
    if session == "closed":
        if direction == "estavel":
            return "Mercado fechou estavel para sua carteira."
        return f"Mercado fechou {direction} para sua carteira, {value}."
    if session == "open":
        if direction == "estavel":
            return "Mercado segue estavel para sua carteira."
        return f"Mercado segue {direction} para sua carteira, {value}."
    if direction == "estavel":
        return "Sua carteira vem estavel desde o ultimo fechamento."
    return f"Sua carteira vem {direction} desde o ultimo fechamento, {value}."


def _crypto_closed_market_brief(snapshot: dict) -> str:
    current = _current_investment_sample(snapshot)
    current_value = current.get("crypto_balance_value")
    if current_value is None:
        return "Mercado fechado hoje; tirei bolsa, FIIs e agenda da carteira do briefing."

    previous = _latest_sample_before(_load_investment_history(), _today())
    previous_value = previous.get("crypto_balance_value") if previous else None
    change = _percent_change(current_value, previous_value)
    if change is None:
        return "Mercado fechado hoje; tirei bolsa e FIIs do briefing. Cripto segue no radar, sem comparativo salvo."
    return "Mercado fechado hoje; bolsa e FIIs ficam fora. " + _format_change_sentence("Cripto na carteira", change, "desde o ultimo snapshot")


def _investment_brief() -> str:
    today = _today()
    snapshot = load_investment_snapshot()
    if not _is_b3_market_day(today):
        return _crypto_closed_market_brief(snapshot)

    current = _current_investment_sample(snapshot)
    history = _load_investment_history()
    weekly = today.weekday() == 4 and _market_session_label() == "closed"
    baseline = _week_baseline_sample(history, today) if weekly else _latest_sample_before(history, today)
    period = "esta semana" if weekly else "desde o ultimo fechamento"

    change = _percent_change(current.get("patrimonio_value"), baseline.get("patrimonio_value") if baseline else None)
    if change is not None:
        return _format_market_change_sentence(change, weekly=weekly)

    current_profitability = current.get("rentabilidade_percent")
    baseline_profitability = baseline.get("rentabilidade_percent") if baseline else None
    if current_profitability is not None and baseline_profitability is not None:
        delta = float(current_profitability) - float(baseline_profitability)
        direction = "melhorou" if delta > 0 else "piorou" if delta < 0 else "ficou estavel"
        if direction == "ficou estavel":
            return f"Carteira ficou estavel em rentabilidade {period}."
        return f"Carteira {direction} {format_percent(abs(delta), digits=1)} ponto percentual em rentabilidade {period}."

    return "Carteira monitorada, mas ainda sem historico suficiente para comparar alta ou queda."


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


def _read_briefing_cache(path: Path, ttl_seconds: int) -> str:
    if ttl_seconds <= 0 or not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    if int(data.get("content_version") or 1) != BRIEFING_CONTENT_VERSION:
        return ""
    try:
        created_at = float(data.get("created_at") or 0)
    except Exception:
        return ""
    if not is_cache_fresh(created_at, ttl_seconds, now=time()):
        return ""
    text = str(data.get("text") or "").strip()
    return text


def _write_briefing_cache(path: Path, text: str) -> None:
    content = str(text or "").strip()
    if not content:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"created_at": time(), "content_version": BRIEFING_CONTENT_VERSION, "text": content}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        return


def _build_daily_briefing() -> str:
    market_day = _is_b3_market_day()
    sections = [
        _time_greeting(),
        _climate_brief(),
        _short_agenda_brief(),
        _investment_brief(),
    ]
    if market_day:
        sections.extend([
            _dividend_agenda_brief(),
            _portfolio_radar_brief(),
        ])
    sections.extend([
        focus_brief_summary(),
        _short_reminders_brief(),
    ])
    return _polish_pt_br(" ".join(part.strip() for part in sections if str(part or "").strip()))


def daily_briefing(*, use_cache: bool = True, ttl_seconds: int = DEFAULT_BRIEFING_CACHE_TTL_SECONDS) -> str:
    if use_cache:
        cached = _read_briefing_cache(BRIEFING_CACHE_PATH, ttl_seconds)
        if cached:
            return cached
    briefing = _build_daily_briefing()
    if use_cache:
        _write_briefing_cache(BRIEFING_CACHE_PATH, briefing)
    return briefing


def daily_routine() -> str:
    sections = [
        daily_briefing(),
        "Rotina pronta: comandos, voz, navegador, lembretes e carteira local ficam no caminho curto.",
        "Noticias, visao pesada e treinos entram sob demanda, para nao disputar atencao quando voce nao pediu.",
        "Atalho pratico: diga 'modo programacao' para abrir o painel de trabalho, ou 'saude do Axel' para ver o painel operacional.",
    ]
    return _polish_pt_br(" ".join(part.strip() for part in sections if str(part or "").strip()))
