from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from time import time

from config import (
    BRAPI_ENABLED,
    BRAPI_TOKEN,
    GEMINI_API_KEY,
    GEMINI_PRIMARY_TEXT_ENABLED,
    NEWSAPI_ENABLED,
    NEWSAPI_KEY,
    NVIDIA_API_KEY,
    NVIDIA_TEXT_FALLBACK_ENABLED,
    OBSIDIAN_SYNC_ENABLED,
    OBSIDIAN_VAULT_PATH,
    OLLAMA_BASE_URL,
    SPOTIFY_API_ENABLED,
    SPOTIFY_CLIENT_ID,
    SUPABASE_REST_URL,
    SUPABASE_SYNC_ENABLED,
)

PROJECT_JSON_FILES = [
    "memory/routines.json",
    "memory/ui_state.json",
    "memory/operational_context.json",
    "memory/operational_memory.json",
    "memory/auto_advances.json",
    "memory/bottlenecks.json",
    "memory/self_evolution.json",
]

KEY_MODULES = [
    "main.py",
    "core/router.py",
    "core/normalizer.py",
    "core/validator.py",
    "memory/operational_context.py",
    "memory/auto_advances.py",
    "tools/briefing_tools.py",
    "ui/qt_axel_hud.py",
]


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_project_jsons(root: Path | None = None) -> tuple[list[str], list[str]]:
    project_dir = root or project_root()
    ok = []
    errors = []
    for relative in PROJECT_JSON_FILES:
        path = project_dir / relative
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            ok.append(relative)
        except Exception as exc:
            errors.append(f"{relative}: {exc}")
    return ok, errors


def compile_project_modules(root: Path | None = None) -> tuple[list[str], str]:
    project_dir = root or project_root()
    existing = [item for item in KEY_MODULES if (project_dir / item).exists()]
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", *existing],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=45,
        )
    except Exception as exc:
        return [], str(exc)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return [], detail[:500] or f"py_compile retornou codigo {result.returncode}"
    return existing, ""


def project_change_summary(root: Path | None = None, limit: int = 4) -> str:
    project_dir = root or project_root()
    if not (project_dir / ".git").exists():
        return "sem repositorio git local detectado"
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={project_dir.as_posix()}", "status", "--short"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        return "status git indisponivel"
    if result.returncode != 0:
        return "status git indisponivel"
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return "sem arquivos alterados no git"
    shown = "; ".join(lines[:limit])
    if len(lines) > limit:
        shown += f"; +{len(lines) - limit} outros"
    return shown


def run_estagiario_preflight(root: Path | None = None) -> dict:
    compiled, compile_error = compile_project_modules(root)
    json_ok, json_errors = validate_project_jsons(root)
    return {
        "compiled_modules": compiled,
        "compile_error": compile_error,
        "json_ok_count": len(json_ok),
        "json_errors": json_errors,
        "change_summary": project_change_summary(root),
    }


def _read_recent_jsonl(path: Path, limit: int = 30) -> list[dict]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, limit):]
    except Exception:
        return []
    events = []
    for line in lines:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def recent_execution_summary(root: Path | None = None, limit: int = 30) -> dict:
    project_dir = root or project_root()
    events = _read_recent_jsonl(project_dir / "memory" / "execution_log.jsonl", limit=limit)
    commands = []
    errors = []
    recent_routes = []
    no_match_routes = []
    slow_actions = []
    high_risk_actions = []
    for event in events:
        event_type = str(event.get("event") or "").strip()
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        message = str(data.get("message") or data.get("text") or data.get("command") or "").strip()
        if event_type in {"user_input", "ui_command"} and message:
            commands.append(message)
        if event_type == "route_result":
            route_item = {
                "source": data.get("source", ""),
                "input": data.get("input", ""),
                "intent": data.get("intent", ""),
                "group": data.get("group", ""),
                "detector": data.get("detector", ""),
                "checked_detectors": data.get("checked_detectors", 0),
            }
            recent_routes.append(route_item)
            if data.get("intent") == "respond" and not data.get("group"):
                no_match_routes.append(route_item)
        if event_type == "command_execute_end":
            action_item = {
                "action": data.get("action", ""),
                "risk_level": data.get("risk_level", ""),
                "duration_ms": data.get("duration_ms", 0),
                "success": bool(data.get("success", True)),
                "error": data.get("error", ""),
            }
            try:
                duration_ms = float(action_item["duration_ms"] or 0)
            except Exception:
                duration_ms = 0
            if duration_ms >= 1000:
                slow_actions.append(action_item)
            if action_item["risk_level"] in {"high", "critical"}:
                high_risk_actions.append(action_item)
            if not action_item["success"]:
                errors.append(action_item["error"] or str(action_item["action"] or event_type))
        if "error" in event_type.lower() or message.lower().startswith(("erro", "falha")):
            errors.append(message or event_type)
    return {
        "events_count": len(events),
        "recent_commands": commands[-5:],
        "recent_errors": errors[-5:],
        "recent_routes": recent_routes[-5:],
        "no_match_routes": no_match_routes[-5:],
        "slow_actions": slow_actions[-5:],
        "high_risk_actions": high_risk_actions[-5:],
    }


def latency_summary(root: Path | None = None, limit: int = 200) -> dict:
    from core.performance_policy import action_performance_advice

    project_dir = root or project_root()
    events = _read_recent_jsonl(project_dir / "memory" / "execution_log.jsonl", limit=limit)
    action_stats: dict[str, dict] = {}
    total_duration = 0.0
    measured_count = 0
    slow_count = 0

    for event in events:
        if str(event.get("event") or "") != "command_execute_end":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        action = str(data.get("action") or "unknown").strip() or "unknown"
        try:
            duration_ms = float(data.get("duration_ms") or 0)
        except Exception:
            continue

        measured_count += 1
        total_duration += duration_ms
        if duration_ms >= 1000:
            slow_count += 1

        item = action_stats.setdefault(
            action,
            {
                "action": action,
                "count": 0,
                "total_ms": 0.0,
                "max_ms": 0.0,
                "last_ms": 0.0,
            },
        )
        item["count"] += 1
        item["total_ms"] += duration_ms
        item["max_ms"] = max(float(item["max_ms"]), duration_ms)
        item["last_ms"] = duration_ms

    by_action = []
    for item in action_stats.values():
        count = int(item["count"] or 0)
        average_ms = float(item["total_ms"]) / count if count else 0.0
        by_action.append(
            {
                "action": item["action"],
                "count": count,
                "avg_ms": round(average_ms, 2),
                "max_ms": round(float(item["max_ms"]), 2),
                "last_ms": round(float(item["last_ms"]), 2),
            }
        )

    by_action.sort(key=lambda item: (float(item["max_ms"]), float(item["avg_ms"])), reverse=True)
    recommendations = []
    for item in by_action:
        advice = action_performance_advice(
            str(item.get("action") or ""),
            avg_ms=float(item.get("avg_ms") or 0),
            max_ms=float(item.get("max_ms") or 0),
            count=int(item.get("count") or 0),
        )
        if advice.mode != "foreground_ok":
            recommendations.append(
                {
                    "action": advice.action,
                    "mode": advice.mode,
                    "reason": advice.reason,
                    "should_background": advice.should_background,
                    "should_cache": advice.should_cache,
                }
            )
    return {
        "measured_count": measured_count,
        "avg_ms": round(total_duration / measured_count, 2) if measured_count else 0,
        "slow_count": slow_count,
        "slow_threshold_ms": 1000,
        "top_slowest_actions": by_action[:5],
        "recommendations": recommendations[:5],
    }


def format_latency_report(snapshot: dict | None = None) -> str:
    data = snapshot or latency_summary()
    measured_count = int(data.get("measured_count") or 0)
    if not measured_count:
        return "Latencia do Axel: ainda nao ha comandos medidos no log operacional."

    parts = [
        "Latencia do Axel: "
        f"{measured_count} comandos medidos; media {data.get('avg_ms', 0)} ms; "
        f"{int(data.get('slow_count') or 0)} acima de {data.get('slow_threshold_ms', 1000)} ms."
    ]

    slowest = data.get("top_slowest_actions") or []
    if slowest:
        items = []
        for item in slowest[:3]:
            action = str(item.get("action") or "acao").strip() or "acao"
            items.append(
                f"{action} max {item.get('max_ms', 0)} ms, media {item.get('avg_ms', 0)} ms"
            )
        parts.append("Gargalos recentes: " + "; ".join(items) + ".")

    recommendations = data.get("recommendations") or []
    if recommendations:
        advice = recommendations[0]
        parts.append(
            "Proxima otimizacao: "
            f"{advice.get('action', '')} -> {advice.get('mode', '')}; {advice.get('reason', '')}."
        )
    else:
        parts.append("Sem recomendacao automatica de performance no momento.")

    return " ".join(parts)


def _telemetry_domain(data: dict) -> str:
    for key in ("category", "group", "toolset", "provider"):
        value = str(data.get(key) or "").strip()
        if value:
            return value
    action = str(data.get("action") or "").strip()
    if "." in action:
        return action.split(".", 1)[0]
    if "_" in action:
        return action.split("_", 1)[0]
    return action or "geral"


def observability_summary(root: Path | None = None, limit: int = 300) -> dict:
    project_dir = root or project_root()
    events = _read_recent_jsonl(project_dir / "memory" / "execution_log.jsonl", limit=limit)
    recent_actions = []
    recent_model_calls = []
    domains: dict[str, dict] = {}
    action_count = 0
    action_error_count = 0
    action_duration_total = 0.0
    model_count = 0
    model_error_count = 0
    fallback_count = 0
    total_tokens = 0
    total_cost = 0.0

    for event in events:
        event_type = str(event.get("event") or "").strip()
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event_type == "command_execute_end":
            action_count += 1
            domain = _telemetry_domain(data)
            domain_item = domains.setdefault(domain, {"domain": domain, "actions": 0, "errors": 0, "avg_ms": 0.0, "total_ms": 0.0})
            domain_item["actions"] += 1
            success = bool(data.get("success", True))
            if not success:
                action_error_count += 1
                domain_item["errors"] += 1
            try:
                duration_ms = float(data.get("duration_ms") or 0.0)
            except Exception:
                duration_ms = 0.0
            action_duration_total += duration_ms
            domain_item["total_ms"] += duration_ms
            recent_actions.append(
                {
                    "action": data.get("action", ""),
                    "action_class": data.get("action_class", ""),
                    "risk_level": data.get("risk_level", ""),
                    "decision": data.get("decision", ""),
                    "target": data.get("target", ""),
                    "duration_ms": round(duration_ms, 2),
                    "success": success,
                    "error": data.get("error", ""),
                }
            )
        elif event_type == "model_call_end":
            model_count += 1
            success = bool(data.get("success", True))
            if not success:
                model_error_count += 1
            if bool(data.get("fallback_used")):
                fallback_count += 1
            try:
                tokens = int(float(data.get("total_tokens_estimate") or 0))
            except Exception:
                tokens = 0
            try:
                cost = float(data.get("estimated_cost_usd") or 0.0)
            except Exception:
                cost = 0.0
            total_tokens += max(0, tokens)
            total_cost += max(0.0, cost)
            recent_model_calls.append(
                {
                    "provider": data.get("provider", ""),
                    "model": data.get("model", ""),
                    "requested_provider": data.get("requested_provider", ""),
                    "model_policy": data.get("model_policy", ""),
                    "fallback_used": bool(data.get("fallback_used")),
                    "success": success,
                    "duration_ms": data.get("duration_ms", 0),
                    "total_tokens_estimate": tokens,
                    "estimated_cost_usd": round(cost, 6),
                    "cost_basis": data.get("cost_basis", ""),
                    "error": data.get("error", ""),
                }
            )

    by_domain = []
    for item in domains.values():
        actions = int(item.get("actions") or 0)
        total_ms = float(item.pop("total_ms", 0.0) or 0.0)
        item["avg_ms"] = round(total_ms / actions, 2) if actions else 0.0
        item["error_rate"] = round(float(item.get("errors") or 0) / actions, 3) if actions else 0.0
        by_domain.append(item)
    by_domain.sort(key=lambda item: (int(item.get("errors") or 0), int(item.get("actions") or 0)), reverse=True)

    return {
        "actions": {
            "count": action_count,
            "error_count": action_error_count,
            "error_rate": round(action_error_count / action_count, 3) if action_count else 0.0,
            "avg_ms": round(action_duration_total / action_count, 2) if action_count else 0.0,
            "recent": recent_actions[-8:],
        },
        "models": {
            "count": model_count,
            "error_count": model_error_count,
            "fallback_count": fallback_count,
            "tokens_estimate": total_tokens,
            "estimated_cost_usd": round(total_cost, 6),
            "recent": recent_model_calls[-6:],
        },
        "domains": by_domain[:8],
    }


def memory_artifact_summary(root: Path | None = None) -> dict:
    project_dir = root or project_root()
    memory_dir = project_dir / "memory"
    patterns = {
        "json": "*.json",
        "jsonl": "*.jsonl",
        "tmp": "*.tmp",
        "html": "*.html",
        "txt": "*.txt",
    }
    counts = {}
    for name, pattern in patterns.items():
        try:
            counts[name] = len(list(memory_dir.glob(pattern)))
        except Exception:
            counts[name] = 0
    return counts


def memory_backup_health(root: Path | None = None) -> dict:
    try:
        from memory.memory_backup import memory_backup_summary

        return memory_backup_summary(root)
    except Exception as exc:
        return {"count": 0, "latest": {}, "critical_files": 0, "error": str(exc)}


def text_health(root: Path | None = None) -> dict:
    try:
        from core.text_health import text_encoding_health

        return text_encoding_health(root or project_root(), limit=8)
    except Exception as exc:
        return {"mojibake_count": 0, "findings": [], "status": "indisponivel", "error": str(exc)}


def _read_tail_text(path: Path, limit: int = 20) -> list[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, limit):]
    except Exception:
        return []


def _startup_errors_after_latest_bootstrap(lines: list[str]) -> list[str]:
    latest_start_index = -1
    for index, line in enumerate(lines):
        if "Bootstrap do Axel iniciado" in line:
            latest_start_index = index
    relevant = lines[latest_start_index + 1 :] if latest_start_index >= 0 else lines
    error_markers = ("Falha fatal", "PermissionError", "Traceback", "Error:", "FileNotFoundError")
    return [line for line in relevant if any(marker in line for marker in error_markers)]


def startup_health(root: Path | None = None) -> dict:
    project_dir = root or project_root()
    log_path = project_dir / ".tmp" / "axel-startup.log"
    output_log_path = project_dir / ".tmp" / "axel-startup-output.log"
    diagnostic_tail = _read_tail_text(log_path)
    output_tail = _read_tail_text(output_log_path)
    error_markers = ("Falha fatal", "PermissionError", "Traceback", "Error:")
    diagnostic_errors = _startup_errors_after_latest_bootstrap(diagnostic_tail)
    output_errors = [line for line in output_tail if any(marker in line for marker in error_markers)]
    recent_errors = diagnostic_errors + output_errors
    startup_entry = {}
    try:
        from tools.system_tools import windows_startup_diagnostics

        startup_entry = windows_startup_diagnostics()
    except Exception as exc:
        startup_entry = {"error": str(exc)}

    return {
        "diagnostic_log": str(log_path),
        "output_log": str(output_log_path),
        "diagnostic_log_exists": log_path.exists(),
        "output_log_exists": output_log_path.exists(),
        "recent_errors": recent_errors[-3:],
        "startup_entry": startup_entry,
    }


def background_runtime_health() -> dict:
    try:
        from core.background_tasks import background_task_summary

        return background_task_summary()
    except Exception as exc:
        return {"total": 0, "running": 0, "failed": 0, "succeeded": 0, "latest": {}, "error": str(exc)}


def action_catalog_summary() -> dict:
    try:
        from actions import ensure_default_actions, list_actions

        ensure_default_actions()
        actions = list_actions()
    except Exception as exc:
        return {"count": 0, "categories": {}, "error": str(exc)}

    categories: dict[str, int] = {}
    for action in actions:
        category = str(getattr(action, "category", "") or "general")
        categories[category] = categories.get(category, 0) + 1
    return {"count": len(actions), "categories": categories, "error": ""}


def service_mode_summary() -> dict:
    from core.specialist_agents import list_agents
    from core.toolsets import list_toolsets

    try:
        from tools.investment_tools import investment_background_refresh_status

        investment_background = investment_background_refresh_status()
    except Exception as exc:
        investment_background = {"enabled": False, "started": False, "error": str(exc)}

    return {
        "always_on": {
            "investment_background_refresh": investment_background,
            "reminders_loop": {"enabled": True, "mode": "checked in main loop"},
        },
        "on_demand": {
            "news": {"enabled": bool(NEWSAPI_ENABLED), "configured": bool(NEWSAPI_KEY)},
            "training": {"enabled": True, "mode": "commands and due reminders"},
            "vision": {"enabled": True, "mode": "screen/file/clipboard commands"},
            "browser": {"enabled": True, "mode": "browser commands"},
        },
        "integrations": {
            "ollama": {"configured": bool(OLLAMA_BASE_URL)},
            "gemini_primary_text": {"enabled": bool(GEMINI_PRIMARY_TEXT_ENABLED), "configured": bool(GEMINI_API_KEY)},
            "nvidia_text_fallback": {"enabled": bool(NVIDIA_TEXT_FALLBACK_ENABLED), "configured": bool(NVIDIA_API_KEY)},
            "brapi": {"enabled": bool(BRAPI_ENABLED), "configured": bool(BRAPI_TOKEN)},
            "spotify": {"enabled": bool(SPOTIFY_API_ENABLED), "configured": bool(SPOTIFY_CLIENT_ID)},
            "supabase": {"enabled": bool(SUPABASE_SYNC_ENABLED), "configured": bool(SUPABASE_REST_URL)},
            "obsidian": {"enabled": bool(OBSIDIAN_SYNC_ENABLED), "configured": bool(OBSIDIAN_VAULT_PATH)},
        },
        "toolsets": list_toolsets(),
        "agents": list_agents(),
    }


def build_project_health_snapshot(root: Path | None = None) -> dict:
    preflight = run_estagiario_preflight(root)
    execution = recent_execution_summary(root)
    latency = latency_summary(root)
    artifacts = memory_artifact_summary(root)
    backups = memory_backup_health(root)
    text = text_health(root)
    startup = startup_health(root)
    background = background_runtime_health()
    actions = action_catalog_summary()
    services = service_mode_summary()
    observability = observability_summary(root)
    healthy = (
        not preflight.get("compile_error")
        and not preflight.get("json_errors")
        and not actions.get("error")
        and not startup.get("recent_errors")
        and not (startup.get("startup_entry") or {}).get("outdated")
    )
    return {
        "generated_at": time(),
        "status": "saudavel" if healthy else "precisa de atencao",
        "preflight": preflight,
        "execution": execution,
        "latency": latency,
        "artifacts": artifacts,
        "backups": backups,
        "text": text,
        "startup": startup,
        "background": background,
        "actions": actions,
        "services": services,
        "observability": observability,
    }


def _enabled_label(value: bool) -> str:
    return "ligado" if value else "desligado"


def _compact_background_task(task: dict) -> str:
    name = str(task.get("name") or "tarefa").strip() or "tarefa"
    status = str(task.get("status") or "indefinido").strip() or "indefinido"
    duration = task.get("duration_ms")
    try:
        duration_text = f" {round(float(duration))}ms" if duration is not None else ""
    except Exception:
        duration_text = ""

    if status == "failed":
        detail = str(task.get("error") or task.get("message") or "").strip()
        detail_text = f" erro={detail[:80]}" if detail else ""
        return f"{name}:{status}{duration_text}{detail_text}"

    message = str(task.get("message") or "").strip()
    message_text = f" msg={message[:80]}" if message else ""
    return f"{name}:{status}{duration_text}{message_text}"


def format_service_modes(snapshot: dict | None = None) -> str:
    data = snapshot or build_project_health_snapshot()
    services = data.get("services") or {}
    always_on = services.get("always_on") or {}
    on_demand = services.get("on_demand") or {}
    integrations = services.get("integrations") or {}
    toolsets = services.get("toolsets") or []
    agents = services.get("agents") or []

    investment = always_on.get("investment_background_refresh") or {}
    parts = [
        "carteira em background "
        + _enabled_label(bool(investment.get("enabled")))
        + (" e rodando" if investment.get("started") else ""),
        "lembretes checados no loop principal",
    ]

    news = on_demand.get("news") or {}
    training = on_demand.get("training") or {}
    parts.append("noticias sob demanda " + _enabled_label(bool(news.get("enabled"))))
    parts.append("treinos sob demanda" if training.get("enabled") else "treinos desligados")

    configured = []
    for name, item in integrations.items():
        if item.get("enabled") and item.get("configured"):
            configured.append(name)
    if configured:
        parts.append("integracoes prontas: " + ", ".join(configured[:4]))
    if toolsets:
        parts.append("toolsets ativos: " + ", ".join(str(item.get("name", "")) for item in toolsets[:6]))
    if agents:
        parts.append("agentes especialistas: " + ", ".join(str(item.get("name", "")) for item in agents[:7]))
    return "Modos ativos: " + "; ".join(parts) + "."


def format_project_health_panel(snapshot: dict | None = None) -> str:
    data = snapshot or build_project_health_snapshot()
    preflight = data.get("preflight") or {}
    execution = data.get("execution") or {}
    latency = data.get("latency") or {}
    actions = data.get("actions") or {}
    artifacts = data.get("artifacts") or {}
    backups = data.get("backups") or {}
    text = data.get("text") or {}
    startup = data.get("startup") or {}
    background = data.get("background") or {}

    parts = [f"Saude do Axel: projeto {data.get('status', 'indefinido')}."]
    if preflight.get("compile_error"):
        parts.append(f"Compilacao com falha: {preflight.get('compile_error')}.")
    else:
        parts.append(f"Compilacao ok em {len(preflight.get('compiled_modules') or [])} modulos-chave.")

    json_errors = preflight.get("json_errors") or []
    if json_errors:
        parts.append(f"Memorias JSON com erro: {json_errors[0]}.")
    else:
        parts.append(f"Memorias JSON ok: {preflight.get('json_ok_count', 0)} arquivos.")

    action_error = actions.get("error")
    if action_error:
        parts.append(f"Catalogo de actions com alerta: {action_error}.")
    else:
        parts.append(f"Actions registradas: {actions.get('count', 0)}.")
    parts.append(format_service_modes(data))

    errors = execution.get("recent_errors") or []
    if errors:
        parts.append(f"Erros recentes: {errors[-1]}.")
    else:
        parts.append("Sem erro recente no log operacional.")

    startup_errors = startup.get("recent_errors") or []
    startup_entry = startup.get("startup_entry") or {}
    if startup_errors:
        parts.append(f"Startup com alerta recente: {startup_errors[-1]}.")
    elif startup_entry.get("outdated"):
        parts.append("Startup Windows com alerta: atalho desatualizado; recrie com --install-startup.")
    elif startup:
        log_status = "pronto" if startup.get("diagnostic_log_exists") else "sem log ainda"
        output_status = "pronta" if startup.get("output_log_exists") else "sem saida ainda"
        entry_status = "atalho atualizado" if startup_entry.get("current") else "atalho nao verificado"
        parts.append(f"Startup Windows: {entry_status}; diagnostico {log_status}; saida do processo {output_status}.")

    no_match_routes = execution.get("no_match_routes") or []
    if no_match_routes:
        last_no_match = no_match_routes[-1]
        parts.append(f"Rotas sem match: {len(no_match_routes)} recentes; ultima entrada: {last_no_match.get('input', '')}.")

    slow_actions = execution.get("slow_actions") or []
    if slow_actions:
        slowest = max(slow_actions, key=lambda item: float(item.get("duration_ms") or 0))
        parts.append(f"Acao lenta recente: {slowest.get('action', '')} em {slowest.get('duration_ms', 0)} ms.")

    high_risk_actions = execution.get("high_risk_actions") or []
    if high_risk_actions:
        last_risk = high_risk_actions[-1]
        parts.append(f"Acao de risco recente: {last_risk.get('action', '')} ({last_risk.get('risk_level', '')}).")

    if latency:
        measured_count = int(latency.get("measured_count") or 0)
        slow_count = int(latency.get("slow_count") or 0)
        if measured_count:
            parts.append(
                f"Latencia: {measured_count} comandos medidos; media {latency.get('avg_ms', 0)} ms; "
                f"{slow_count} acima de {latency.get('slow_threshold_ms', 1000)} ms."
            )
            top_slowest = latency.get("top_slowest_actions") or []
            if top_slowest:
                slowest = top_slowest[0]
                parts.append(
                    f"Maior gargalo recente: {slowest.get('action', '')} "
                    f"max {slowest.get('max_ms', 0)} ms, media {slowest.get('avg_ms', 0)} ms."
                )
            recommendations = latency.get("recommendations") or []
            if recommendations:
                advice = recommendations[0]
                parts.append(
                    f"Recomendacao de performance: {advice.get('action', '')} "
                    f"-> {advice.get('mode', '')}; {advice.get('reason', '')}."
                )

    if background:
        background_error = background.get("error")
        if background_error:
            parts.append(f"Background runtime com alerta: {background_error}.")
        else:
            parts.append(
                f"Background runtime: {background.get('running', 0)} rodando, "
                f"{background.get('failed', 0)} falhas, {background.get('succeeded', 0)} concluidas."
            )
            recent_background = background.get("recent") or []
            if recent_background:
                compact = [_compact_background_task(task) for task in recent_background[-3:]]
                parts.append("Background recente: " + "; ".join(compact) + ".")

    parts.append(
        "Artefatos locais em memory: "
        f"{artifacts.get('json', 0)} json, {artifacts.get('tmp', 0)} tmp, "
        f"{artifacts.get('html', 0) + artifacts.get('txt', 0)} html/txt."
    )
    backup_error = backups.get("error")
    if backup_error:
        parts.append(f"Backups de memoria com alerta: {backup_error}.")
    elif backups.get("count"):
        latest = backups.get("latest") or {}
        parts.append(f"Backups de memoria: {backups.get('count')} snapshots; ultimo {latest.get('name', 'indefinido')}.")
    else:
        parts.append(
            f"Backups de memoria: nenhum snapshot para {backups.get('critical_files', 0)} arquivos criticos; "
            "rode --backup-memory antes de refatoracoes."
        )
    text_findings = text.get("findings") or []
    if text.get("error"):
        parts.append(f"Encoding textual com alerta: {text.get('error')}.")
    elif text_findings:
        first = text_findings[0]
        parts.append(
            f"Encoding textual: {text.get('mojibake_count', len(text_findings))} arquivo(s) com sinais de mojibake; "
            f"primeiro {first.get('path', '')}."
        )
    elif text:
        parts.append("Encoding textual: sem mojibake detectado nos arquivos principais.")
    parts.append(f"Git: {preflight.get('change_summary')}.")
    return " ".join(parts)
