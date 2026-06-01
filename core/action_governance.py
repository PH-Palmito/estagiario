from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from core.command_schema import Command
from core.permission_policy import PermissionDecision, permission_decision

READ_ACTION_CLASS = "read"
RESPONSE_ACTION_CLASS = "response"
LOCAL_ACTION_CLASS = "local_action"
WRITE_ACTION_CLASS = "write"
SENSITIVE_WRITE_ACTION_CLASS = "sensitive_write"

IRREVERSIBLE_ACTIONS = {
    "file_delete",
    "file_move",
    "file_replace",
    "file_write",
    "file_rename",
    "run_macro",
    "run_script",
    "type_text",
    "windows_startup_disable",
    "windows_startup_enable",
}

WRITE_CATEGORIES = {"automation", "browser", "files", "investments", "system"}
TARGET_PARAM_KEYS = (
    "target",
    "path",
    "dst",
    "destination",
    "url",
    "name",
    "location",
    "query",
    "app",
)


@dataclass(frozen=True)
class ActionGovernance:
    action_class: str
    payload_hash: str
    reversible: bool
    target: str
    decision: str
    audit_required: bool


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))


def command_payload_hash(command: Command, decision: PermissionDecision | None = None) -> str:
    decision = decision or permission_decision(command)
    payload = {
        "action": getattr(command, "action", ""),
        "tool_name": decision.tool_name,
        "params": getattr(command, "params", {}) or {},
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]


def command_target(command: Command) -> str:
    params = getattr(command, "params", {}) or {}
    if not isinstance(params, dict):
        return ""
    for key in TARGET_PARAM_KEYS:
        value = params.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def command_action_class(command: Command, decision: PermissionDecision | None = None) -> str:
    decision = decision or permission_decision(command)
    action = str(getattr(command, "action", "") or "")
    if action == "respond":
        return RESPONSE_ACTION_CLASS
    if decision.read_only:
        return READ_ACTION_CLASS
    if decision.risk_level in {"high", "critical"} or decision.requires_strong_confirmation:
        return SENSITIVE_WRITE_ACTION_CLASS
    if decision.category in WRITE_CATEGORIES or decision.requires_confirmation:
        return WRITE_ACTION_CLASS
    return LOCAL_ACTION_CLASS


def command_reversible(command: Command, decision: PermissionDecision | None = None) -> bool:
    decision = decision or permission_decision(command)
    action = str(getattr(command, "action", "") or "")
    effective_name = decision.tool_name or action
    if effective_name in IRREVERSIBLE_ACTIONS:
        return False
    if decision.risk_level == "critical" or decision.requires_strong_confirmation:
        return False
    return True


def command_governance_decision(decision: PermissionDecision) -> str:
    if decision.requires_strong_confirmation:
        return "confirm_strong"
    if decision.requires_confirmation or decision.risk_level in {"high", "critical"}:
        return "confirm"
    if decision.read_only:
        return "allow_read"
    return "allow"


def command_audit_required(decision: PermissionDecision) -> bool:
    return bool(
        decision.requires_confirmation
        or decision.requires_strong_confirmation
        or decision.risk_level in {"high", "critical"}
    )


def command_governance(command: Command) -> ActionGovernance:
    decision = permission_decision(command)
    return ActionGovernance(
        action_class=command_action_class(command, decision),
        payload_hash=command_payload_hash(command, decision),
        reversible=command_reversible(command, decision),
        target=command_target(command),
        decision=command_governance_decision(decision),
        audit_required=command_audit_required(decision),
    )


def command_governance_payload(command: Command) -> dict:
    governance = command_governance(command)
    return {
        "action_class": governance.action_class,
        "payload_hash": governance.payload_hash,
        "reversible": governance.reversible,
        "target": governance.target,
        "decision": governance.decision,
        "audit_required": governance.audit_required,
    }
