from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.action_result import normalize_action_result
from core.normalizer import normalize_action
from core.permission_policy import permission_decision
from core.response_polish import polish_assistant_response
from core.shared_commands import maybe_handle_shared_command


@dataclass(frozen=True)
class WhatsAppRequest:
    sender: str
    text: str
    message_id: str = ""


@dataclass(frozen=True)
class WhatsAppResponse:
    ok: bool
    text: str
    status: str = "ok"
    action: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", polish_assistant_response(self.text))


def normalize_phone(value: str) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def parse_allowed_senders(raw: str) -> set[str]:
    return {
        normalized
        for normalized in (normalize_phone(item) for item in re.split(r"[,;]+", str(raw or "")))
        if normalized
    }


def sender_allowed(sender: str, allowed_senders: set[str]) -> bool:
    if not allowed_senders:
        return False
    normalized = normalize_phone(sender)
    return bool(normalized and normalized in allowed_senders)


def parse_inbound_payload(payload: dict[str, Any]) -> WhatsAppRequest:
    sender = str(payload.get("from") or payload.get("sender") or payload.get("phone") or "").strip()
    text = str(payload.get("text") or payload.get("body") or payload.get("message") or "").strip()
    message_id = str(payload.get("id") or payload.get("message_id") or "").strip()
    return WhatsAppRequest(sender=sender, text=text, message_id=message_id)


def _blocked_response(reason: str) -> WhatsAppResponse:
    return WhatsAppResponse(False, reason, status="blocked")


def route_text(text: str) -> dict[str, Any]:
    from core.router import route

    return route(text)


def execute_whatsapp_command(command):
    from core.executor import execute_result

    return execute_result(command)


def handle_whatsapp_text(text: str) -> WhatsAppResponse:
    clean = str(text or "").strip()
    if not clean:
        return WhatsAppResponse(False, "Envie uma mensagem para o Axel.", status="empty")

    shared_response = maybe_handle_shared_command(clean)
    if shared_response:
        return WhatsAppResponse(True, shared_response, action="shared_command")

    raw_action = route_text(clean)
    if raw_action.get("intent") == "respond":
        return WhatsAppResponse(True, str(raw_action.get("response") or "Nao entendi."), action="respond")

    command = normalize_action(raw_action)
    decision = permission_decision(command)
    if decision.requires_confirmation or decision.requires_strong_confirmation or not decision.read_only:
        return _blocked_response(
            "Esse comando existe, mas esta bloqueado pelo WhatsApp por seguranca. Use o PC para confirmar a acao."
        )

    result = normalize_action_result(execute_whatsapp_command(command))
    return WhatsAppResponse(
        result.success,
        result.message if result.message else "Sem resposta.",
        status="ok" if result.success else "failed",
        action=command.action,
    )


def handle_whatsapp_payload(payload: dict[str, Any], *, allowed_senders: set[str]) -> WhatsAppResponse:
    request = parse_inbound_payload(payload)
    if not sender_allowed(request.sender, allowed_senders):
        return _blocked_response("Remetente nao autorizado.")
    return handle_whatsapp_text(request.text)
