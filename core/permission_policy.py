from __future__ import annotations

from dataclasses import dataclass

from core.command_schema import Command
from core.sandbox_policy import command_sandbox_decision

STRONG_CONFIRMATION_ACTIONS = {
    "close_app",
    "smart_close_app",
    "run_script",
    "system_shutdown",
    "type_text",
    "windows_startup_enable",
    "windows_startup_disable",
    "browser_close_tab",
    "browser_click_center",
    "browser_click_text",
    "browser_click_listed_item",
    "vision_download_light_model",
    "file_create",
    "file_write",
    "file_append",
    "file_replace",
    "file_delete",
    "file_copy",
    "file_move",
    "file_rename",
    "folder_create",
    "run_macro",
    "memory.backup.restore_file",
    "investment.refresh_public_wallet",
    "investment_refresh_public_wallet",
    "investment.add_watchlist",
    "investment.remove_watchlist",
    "investment.set_price_ceiling",
    "investment.set_auto_ceiling_margin",
    "investment.set_thesis",
    "investment_add_watchlist",
    "investment_remove_watchlist",
    "investment_set_price_ceiling",
    "investment_set_auto_ceiling_margin",
    "investment_set_thesis",
}

STRONG_CONFIRMATION_TOOL_NAMES = set(STRONG_CONFIRMATION_ACTIONS)
STRONG_CONFIRMATION_CATEGORIES = {"files", "system", "browser", "automation", "investments"}
CRITICAL_ACTIONS = {
    "run_script",
    "system_shutdown",
    "type_text",
    "windows_startup_enable",
    "windows_startup_disable",
    "vision_download_light_model",
    "file_write",
    "file_replace",
    "file_delete",
    "file_move",
    "file_rename",
    "run_macro",
    "memory.backup.restore_file",
}


class RiskLevel:
    READ = "read"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class PermissionDecision:
    action: str
    tool_name: str = ""
    read_only: bool = True
    requires_confirmation: bool = False
    requires_strong_confirmation: bool = False
    category: str = ""
    risk_level: str = RiskLevel.LOW
    sandbox_scope: str = "read_only"
    dry_run_recommended: bool = False


@dataclass(frozen=True)
class ExecutionPermission:
    allowed: bool
    decision: PermissionDecision
    reason: str = ""


def registered_spec(name: str):
    try:
        from actions import ensure_default_actions, get_action
    except Exception:
        return None

    ensure_default_actions()
    return get_action(name)


def tool_name_for_command(command: Command) -> str:
    if getattr(command, "action", "") != "action_tool_execute":
        return ""
    params = getattr(command, "params", {}) or {}
    return str(params.get("name") or "").strip()


def spec_for_command(command: Command):
    tool_name = tool_name_for_command(command)
    return registered_spec(tool_name or getattr(command, "action", ""))


def command_requires_confirmation(command: Command) -> bool:
    if bool(getattr(command, "requires_confirmation", False)):
        return True

    spec = spec_for_command(command)
    return bool(getattr(spec, "requires_confirmation", False)) if spec else False


def command_requires_strong_confirmation(command: Command) -> bool:
    action = str(getattr(command, "action", "") or "")
    if action in STRONG_CONFIRMATION_ACTIONS:
        return True

    tool_name = tool_name_for_command(command)
    effective_name = tool_name or action
    if effective_name in STRONG_CONFIRMATION_TOOL_NAMES:
        return True

    spec = registered_spec(effective_name)
    if not spec:
        return False

    return bool(spec.requires_confirmation and spec.category in STRONG_CONFIRMATION_CATEGORIES)


def command_risk_level(command: Command) -> str:
    action = str(getattr(command, "action", "") or "")
    tool_name = tool_name_for_command(command)
    effective_name = tool_name or action
    spec = spec_for_command(command)

    if effective_name in CRITICAL_ACTIONS:
        return RiskLevel.CRITICAL
    if command_requires_strong_confirmation(command):
        return RiskLevel.HIGH
    if command_requires_confirmation(command):
        return RiskLevel.MEDIUM
    if bool(getattr(spec, "read_only", False)):
        return RiskLevel.READ
    return RiskLevel.LOW


def permission_decision(command: Command) -> PermissionDecision:
    action = str(getattr(command, "action", "") or "")
    tool_name = tool_name_for_command(command)
    spec = spec_for_command(command)
    sandbox = command_sandbox_decision(command)
    requires_confirmation = command_requires_confirmation(command)
    requires_strong_confirmation = command_requires_strong_confirmation(command)
    return PermissionDecision(
        action=action,
        tool_name=tool_name,
        read_only=bool(getattr(spec, "read_only", True)) if spec else True,
        requires_confirmation=requires_confirmation,
        requires_strong_confirmation=requires_strong_confirmation,
        category=str(getattr(spec, "category", "") or "") if spec else "",
        risk_level=command_risk_level(command),
        sandbox_scope=sandbox.scope,
        dry_run_recommended=sandbox.dry_run_recommended,
    )


def action_requires_confirmation(name: str) -> bool:
    spec = registered_spec(name)
    return bool(getattr(spec, "requires_confirmation", False)) if spec else False


def execution_permission(command: Command, *, confirmed: bool = False) -> ExecutionPermission:
    decision = permission_decision(command)
    if decision.requires_confirmation and not confirmed:
        if decision.requires_strong_confirmation:
            reason = "requires_strong_confirmation"
        else:
            reason = "requires_confirmation"
        return ExecutionPermission(False, decision, reason)
    return ExecutionPermission(True, decision)
