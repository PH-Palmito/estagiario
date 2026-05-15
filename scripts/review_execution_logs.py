from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "memory" / "execution_log.jsonl"
REPORT_PATH = ROOT / "memory" / "execution_log_review.json"


def _load_events(limit: int = 400) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
    events = []
    for line in lines[-limit:]:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def _dt(ts: float) -> str:
    try:
        return datetime.fromtimestamp(float(ts)).isoformat(timespec="seconds")
    except Exception:
        return ""


def build_report(limit: int = 400) -> dict:
    events = _load_events(limit=limit)
    event_counts = Counter(str(item.get("event", "unknown")) for item in events)
    intent_counts = Counter()
    action_counts = Counter()
    failures = []
    slow_commands = []
    reminders = []

    for item in events:
        event = str(item.get("event", "")).strip()
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        if event == "route_result":
            intent_counts[str(data.get("intent", "unknown"))] += 1
        if event in {"command_execute_start", "command_execute_end", "action_processed"}:
            action_counts[str(data.get("action", "unknown"))] += 1
        text_blob = json.dumps(data, ensure_ascii=False).lower()
        if "erro" in text_blob or "falha" in text_blob or "nao consegui" in text_blob or "não consegui" in text_blob:
            failures.append({"at": _dt(item.get("ts", 0)), "event": event, "data": data})
        if event == "command_execute_end":
            duration = float(data.get("duration_ms", 0) or 0)
            if duration >= 5000:
                slow_commands.append(
                    {
                        "at": _dt(item.get("ts", 0)),
                        "action": str(data.get("action", "")),
                        "duration_ms": round(duration, 2),
                        "result": str(data.get("result", ""))[:240],
                    }
                )
        if "reminder" in str(data.get("action", "")) or "lembrete" in text_blob:
            reminders.append({"at": _dt(item.get("ts", 0)), "event": event, "data": data})

    observations = []
    if slow_commands:
        observations.append("Comandos de carteira/musica/briefing aparecem acima de 5s e merecem cache ou resposta progressiva.")
    if reminders:
        observations.append("Ha evidencias reais de lembrete por voz com transcricao imperfeita; vale preservar o texto original e uma versao corrigida.")
    if intent_counts.get("daily_briefing", 0) >= 2:
        observations.append("Briefing diario e um fluxo recorrente, entao deve usar memoria consolidada e fontes com cuidado.")
    if not failures:
        observations.append("Nenhuma falha explicita recente foi detectada nos eventos revisados.")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "log_path": str(LOG_PATH),
        "events_reviewed": len(events),
        "first_event_at": _dt(events[0].get("ts", 0)) if events else "",
        "last_event_at": _dt(events[-1].get("ts", 0)) if events else "",
        "event_counts": dict(event_counts.most_common()),
        "top_intents": dict(intent_counts.most_common(10)),
        "top_actions": dict(action_counts.most_common(10)),
        "slow_commands": slow_commands[:10],
        "failure_signals": failures[:10],
        "reminder_signals": reminders[-8:],
        "observations": observations,
    }


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    report = build_report(limit=limit)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
