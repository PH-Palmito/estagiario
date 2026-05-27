from __future__ import annotations

from actions.registry import ActionSpec, register_action
from core.background_tasks import background_task_summary
from core.background_tasks import consume_background_notifications
from core.background_tasks import latest_background_task_result
from core.background_tasks import submit_background_task


def background_status(_args: dict | None = None) -> str:
    summary = background_task_summary()
    latest = summary.get("latest") or {}
    parts = [
        "Tarefas em segundo plano:",
        f"{summary.get('running', 0)} rodando",
        f"{summary.get('succeeded', 0)} concluidas",
        f"{summary.get('failed', 0)} falhas",
    ]
    if latest:
        parts.append(f"ultima {latest.get('name', 'indefinida')} ({latest.get('status', 'indefinido')})")
    return "; ".join(parts) + "."


def background_latest_result(_args: dict | None = None) -> str:
    latest = latest_background_task_result()
    if not latest:
        return "Ainda nao ha tarefa em segundo plano concluida."
    name = latest.get("name", "indefinida")
    task_id = latest.get("task_id", "")
    status = latest.get("status", "indefinido")
    duration = latest.get("duration_ms")
    if status == "failed":
        detail = str(latest.get("error") or latest.get("message") or "falha sem detalhe").strip()
        return f"Ultima tarefa em segundo plano: {name} ({task_id}) falhou. Erro: {detail[:500]}"

    message = str(latest.get("message") or "Concluida sem mensagem.").strip()
    duration_text = f" em {duration} ms" if duration is not None else ""
    return f"Ultima tarefa em segundo plano: {name} ({task_id}) concluida{duration_text}. Resultado: {message[:700]}"


def background_notifications(_args: dict | None = None) -> str:
    notifications = consume_background_notifications()
    if not notifications:
        return "Nao ha notificacoes pendentes de tarefas em segundo plano."
    lines = []
    for item in notifications[-5:]:
        name = item.get("name", "tarefa")
        status = item.get("status", "indefinido")
        if status == "failed":
            detail = str(item.get("error") or item.get("message") or "sem detalhe").strip()
            lines.append(f"{name} falhou: {detail[:180]}")
        else:
            lines.append(f"{name} terminou: {str(item.get('message') or 'concluida')[:180]}")
    message = "Notificacoes de background: " + " | ".join(lines) + "."
    try:
        from memory.ui_state import append_ui_notification

        append_ui_notification("background", message, level="info")
    except Exception:
        pass
    return message


def run_action_in_background(action_name: str, arguments: dict | None = None, *, allow_sensitive: bool = False) -> str:
    safe_action = str(action_name or "").strip()
    if not safe_action:
        return "Qual action devo executar em segundo plano?"
    if safe_action.startswith("background") or safe_action.startswith("background."):
        return "Nao executo uma action de background dentro dela mesma."

    from actions.registry import get_action

    spec = get_action(safe_action)
    if not spec:
        return f"Action desconhecida: {safe_action}."
    if not allow_sensitive and (not spec.read_only or spec.requires_confirmation):
        return f"A action {safe_action} precisa de confirmacao e nao pode ser disparada pelo background generico."

    task_id = submit_background_task(
        safe_action,
        lambda: _execute_action_for_background(safe_action, arguments or {}),
    )
    return f"Deixei {safe_action} rodando em segundo plano. Tarefa: {task_id}."


def _execute_action_for_background(action_name: str, arguments: dict) -> str:
    from actions.registry import execute_action_result

    result = execute_action_result(action_name, arguments)
    if result.success:
        return result.message
    raise RuntimeError(result.error or result.message)


def background_daily_briefing(_args: dict | None = None) -> str:
    return run_action_in_background("daily_briefing", {})


def background_vision_screen(_args: dict | None = None) -> str:
    return run_action_in_background("image_analyze_screen", {})


def background_vision_screen_graph(_args: dict | None = None) -> str:
    return run_action_in_background("image_analyze_screen_graph", {})


def background_investment_report(_args: dict | None = None) -> str:
    return run_action_in_background("investment_financial_report", {})


def background_investment_refresh(_args: dict | None = None) -> str:
    return run_action_in_background("investment_refresh_public_wallet", {}, allow_sensitive=True)


def register_background_actions() -> None:
    register_action(
        ActionSpec(
            name="background_status",
            description="Mostra o status das tarefas em segundo plano.",
            handler=background_status,
            category="system",
            read_only=True,
        )
    )
    register_action(
        ActionSpec(
            name="background_latest_result",
            description="Mostra o resultado da ultima tarefa em segundo plano concluida.",
            handler=background_latest_result,
            category="system",
            read_only=True,
        )
    )
    register_action(
        ActionSpec(
            name="background_notifications",
            description="Mostra e limpa notificacoes pendentes de tarefas em segundo plano.",
            handler=background_notifications,
            category="system",
            read_only=True,
        )
    )
    register_action(
        ActionSpec(
            name="background_daily_briefing",
            description="Executa o briefing diario em segundo plano.",
            handler=background_daily_briefing,
            category="briefing",
            read_only=True,
        )
    )
    register_action(
        ActionSpec(
            name="background_vision_screen",
            description="Analisa a tela em segundo plano.",
            handler=background_vision_screen,
            category="vision",
            read_only=True,
        )
    )
    register_action(
        ActionSpec(
            name="background_vision_screen_graph",
            description="Analisa grafico da tela em segundo plano.",
            handler=background_vision_screen_graph,
            category="vision",
            read_only=True,
        )
    )
    register_action(
        ActionSpec(
            name="background_investment_report",
            description="Gera relatorio financeiro em segundo plano.",
            handler=background_investment_report,
            category="investments",
            read_only=True,
        )
    )
    register_action(
        ActionSpec(
            name="background_investment_refresh",
            description="Atualiza carteira publica em segundo plano.",
            handler=background_investment_refresh,
            category="investments",
            read_only=False,
            requires_confirmation=True,
        )
    )
    register_action(
        ActionSpec(
            name="background.run_action",
            description="Executa uma action registrada em segundo plano.",
            handler=lambda args: run_action_in_background(args.get("name", ""), args.get("arguments") or {}),
            parameters={
                "name": {"type": "string", "description": "Nome da action registrada.", "required": True},
                "arguments": {"type": "object", "description": "Argumentos da action."},
            },
            category="system",
            read_only=True,
        )
    )
