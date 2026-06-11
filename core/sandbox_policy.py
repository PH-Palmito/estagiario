from __future__ import annotations

from dataclasses import dataclass

from core.command_schema import Command


FILE_WRITE_ACTIONS = {
    "file_create",
    "file_write",
    "file_append",
    "file_replace",
    "file_delete",
    "file_copy",
    "file_move",
    "file_rename",
    "folder_create",
}

PROCESS_ACTIONS = {
    "open_app",
    "close_app",
    "smart_close_app",
    "run_script",
    "system_shutdown",
    "windows_startup_enable",
    "windows_startup_disable",
}

BROWSER_MUTATION_ACTIONS = {
    "browser_close_tab",
    "browser_click_center",
    "browser_click_text",
    "browser_click_listed_item",
}

DRY_RUN_RECOMMENDED_ACTIONS = {
    "file_delete",
    "file_replace",
    "file_move",
    "file_rename",
    "run_script",
    "run_macro",
    "memory.backup.restore_file",
}


@dataclass(frozen=True)
class SandboxDecision:
    scope: str
    requires_confirmation: bool
    dry_run_recommended: bool
    reason: str


def effective_action_name(command: Command) -> str:
    action = str(getattr(command, "action", "") or "").strip()
    if action != "action_tool_execute":
        return action
    params = getattr(command, "params", {}) or {}
    return str(params.get("name") or "").strip() or action


def command_sandbox_decision(command: Command) -> SandboxDecision:
    name = effective_action_name(command)

    if name in FILE_WRITE_ACTIONS:
        return SandboxDecision(
            scope="filesystem",
            requires_confirmation=True,
            dry_run_recommended=name in DRY_RUN_RECOMMENDED_ACTIONS,
            reason="acao altera arquivos ou pastas",
        )
    if name in PROCESS_ACTIONS:
        return SandboxDecision(
            scope="process",
            requires_confirmation=name not in {"open_app"},
            dry_run_recommended=name in DRY_RUN_RECOMMENDED_ACTIONS,
            reason="acao controla processo ou startup",
        )
    if name in BROWSER_MUTATION_ACTIONS:
        return SandboxDecision(
            scope="browser",
            requires_confirmation=True,
            dry_run_recommended=False,
            reason="acao altera estado do navegador",
        )
    if name in DRY_RUN_RECOMMENDED_ACTIONS:
        return SandboxDecision(
            scope="automation",
            requires_confirmation=True,
            dry_run_recommended=True,
            reason="acao automatizada sensivel",
        )
    return SandboxDecision(
        scope="read_only",
        requires_confirmation=False,
        dry_run_recommended=False,
        reason="acao sem efeito externo sensivel conhecido",
    )
