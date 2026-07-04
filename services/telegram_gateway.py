from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from actions import ensure_default_actions, get_action
from core.action_result import normalize_action_result
from core.axel_brain import build_axel_brain_decision
from core.axel_brain_contract import (
    REMOTE_LIGHT_CONFIRM_ACTIONS,
    build_axel_brain_contract,
    remote_permission_summary,
)
from core.command_schema import Command
from core.intent_complexity import classify_intent_complexity
from core.normalizer import normalize_action
from core.response_polish import polish_assistant_response
from core.router import route_trace
from core.router_utils import normalize_text
from core.shared_commands import maybe_handle_shared_command


TELEGRAM_LOG_PATH = Path("memory/telegram_bot.log")
REMOTE_CONFIRMATION_TTL_SECONDS = 60
REMOTE_CONFIRMABLE_CATEGORIES = {"media"}
REMOTE_CONFIRMABLE_ACTIONS = REMOTE_LIGHT_CONFIRM_ACTIONS
_CHAT_CONTEXT: dict[str, dict[str, Any]] = {}
_RETRY_PHRASES = {
    "retry",
    "tentar de novo",
    "pode tentar novamente",
    "tenta novamente",
    "tentar novamente",
    "tente novamente",
    "tenta de novo",
    "tente de novo",
    "de novo",
    "mais uma vez",
    "repete",
    "repetir",
    "repetir ultimo",
    "repetir ultima acao",
}
_CONFIRMATION_HELP_PHRASES = {
    "como eu confirmo",
    "como confirmo",
    "como confirmar",
    "confirmo como",
    "onde confirmo",
    "basta",
    "basta o que",
}
_CONFIRM_PHRASES = {
    "confirmar",
    "confirmo",
    "sim",
    "pode",
    "pode sim",
    "executar",
}
_CANCEL_PHRASES = {
    "cancelar",
    "cancela",
    "nao",
    "não",
    "deixa quieto",
    "esquece",
}


@dataclass(frozen=True)
class TelegramRequest:
    chat_id: str
    text: str
    message_id: str = ""
    username: str = ""
    callback_data: str = ""
    callback_query_id: str = ""
    media_kind: str = ""
    media_file_id: str = ""
    media_duration: int = 0
    media_mime_type: str = ""


@dataclass(frozen=True)
class TelegramResponse:
    ok: bool
    text: str
    status: str = "ok"
    action: str = ""
    chat_id: str = ""
    contract: dict | None = None
    reply_markup: dict | None = None
    callback_query_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", polish_assistant_response(self.text))


def parse_allowed_chat_ids(raw: str) -> set[str]:
    return {item.strip() for item in str(raw or "").replace(";", ",").split(",") if item.strip()}


def chat_allowed(chat_id: str, allowed_chat_ids: set[str]) -> bool:
    normalized = str(chat_id or "").strip()
    return bool(normalized and normalized in allowed_chat_ids)


def log_telegram_event(event: str, **data: Any) -> None:
    try:
        TELEGRAM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        safe_data = {key: value for key, value in data.items() if "token" not in key.lower()}
        with TELEGRAM_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"{event}: {safe_data}\n")
    except Exception:
        pass


def _chat_key(chat_id: str) -> str:
    return str(chat_id or "").strip()


def parse_inbound_update(update: dict[str, Any]) -> TelegramRequest:
    callback = update.get("callback_query") if isinstance(update.get("callback_query"), dict) else {}
    if callback:
        message = callback.get("message") if isinstance(callback.get("message"), dict) else {}
        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        sender = callback.get("from") if isinstance(callback.get("from"), dict) else {}
        return TelegramRequest(
            chat_id=str(chat.get("id") or "").strip(),
            text=str(callback.get("data") or "").strip(),
            message_id=str(message.get("message_id") or "").strip(),
            username=str(sender.get("username") or sender.get("first_name") or "").strip(),
            callback_data=str(callback.get("data") or "").strip(),
            callback_query_id=str(callback.get("id") or "").strip(),
        )

    message = update.get("message") if isinstance(update.get("message"), dict) else {}
    if not message:
        message = update.get("edited_message") if isinstance(update.get("edited_message"), dict) else {}
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    text = str(message.get("text") or message.get("caption") or "").strip()
    media_kind = ""
    media = {}
    for candidate in ("voice", "audio"):
        item = message.get(candidate)
        if isinstance(item, dict) and item.get("file_id"):
            media_kind = candidate
            media = item
            break
    return TelegramRequest(
        chat_id=str(chat.get("id") or "").strip(),
        text=text,
        message_id=str(message.get("message_id") or "").strip(),
        username=str(sender.get("username") or sender.get("first_name") or "").strip(),
        media_kind=media_kind,
        media_file_id=str(media.get("file_id") or "").strip(),
        media_duration=int(media.get("duration") or 0),
        media_mime_type=str(media.get("mime_type") or "").strip(),
    )


def _blocked_response(reason: str, *, chat_id: str = "", contract: dict | None = None) -> TelegramResponse:
    return TelegramResponse(False, reason, status="blocked", chat_id=chat_id, contract=contract)


def _is_remote_confirm_text(text: str) -> bool:
    return normalize_text(text) in _CONFIRM_PHRASES


def _is_remote_cancel_text(text: str) -> bool:
    return normalize_text(text) in _CANCEL_PHRASES


def _remote_pending(chat_id: str) -> dict[str, Any] | None:
    context = _CHAT_CONTEXT.get(_chat_key(chat_id), {})
    pending = context.get("pending_remote_action")
    if not isinstance(pending, dict):
        return None
    if float(pending.get("expires_at") or 0) < time.time():
        context.pop("pending_remote_action", None)
        return None
    return pending


def _clear_remote_pending(chat_id: str) -> None:
    context = _CHAT_CONTEXT.get(_chat_key(chat_id), {})
    context.pop("pending_remote_action", None)


def _handle_remote_mode_command(text: str, chat_id: str) -> TelegramResponse | None:
    normalized = normalize_text(text)
    if normalized in {"status remoto", "modo remoto", "status do modo remoto", "remoto status"}:
        summary = remote_permission_summary()
        confirmable_count = len(summary["confirmable_actions"])
        return TelegramResponse(
            True,
            (
                "Modo remoto ampliado desativado. "
                "Permitido: leitura segura. "
                f"Com confirmacao no chat: {confirmable_count} acoes leves de midia/volume. "
                "Bloqueado: escrita, apps, arquivos, automacoes e risco medio/alto; use o PC."
            ),
            status="remote_mode_disabled",
            chat_id=chat_id,
        )

    if normalized in {"bloquear remoto", "desativar remoto", "desligar remoto", "cancelar remoto", "travar remoto"}:
        context = _CHAT_CONTEXT.setdefault(_chat_key(chat_id), {})
        context.pop("pending_remote_action", None)
        log_telegram_event("remote_mode_disabled", chat_id=chat_id)
        return TelegramResponse(True, "Modo remoto ampliado desativado e acoes pendentes canceladas.", status="remote_mode_disabled", chat_id=chat_id)

    if (
        "remoto" in normalized
        and any(term in normalized for term in {"ativar", "liberar", "ligar", "habilitar"})
    ):
        log_telegram_event("remote_mode_activation_refused", chat_id=chat_id)
        return TelegramResponse(
            False,
            "Modo remoto ampliado esta desativado por seguranca. Continuo aceitando leitura e midia leve com confirmacao.",
            status="remote_mode_disabled",
            chat_id=chat_id,
        )

    return None


def _command_label(command: Command) -> str:
    action = str(command.action or "").strip()
    params = command.params or {}
    target = str(params.get("target") or params.get("query") or params.get("vibe") or "").strip()
    if target:
        return f"{action} ({target})"
    return action


def _can_confirm_remotely(command: Command, chat_id: str = "", remote_policy: dict | None = None) -> tuple[bool, str]:
    policy = remote_policy if isinstance(remote_policy, dict) else {}
    if policy and not bool(policy.get("can_confirm_remotely")):
        return False, str(policy.get("reason") or "AxelBrain 2.0 bloqueou confirmacao remota")

    ensure_default_actions()
    spec = get_action(command.action)
    if command.action not in REMOTE_CONFIRMABLE_ACTIONS:
        return False, "acao fora da lista remota segura"
    category = str(getattr(spec, "category", "") or "")
    if spec and category not in REMOTE_CONFIRMABLE_CATEGORIES and not command.action.startswith(("browser_", "spotify_")):
        return False, "categoria remota nao permitida"
    return True, "acao leve permitida no Telegram"


def _store_remote_pending(chat_id: str, command: Command, effective_text: str) -> None:
    context = _CHAT_CONTEXT.setdefault(_chat_key(chat_id), {})
    context["pending_remote_action"] = {
        "command": command,
        "text": effective_text,
        "expires_at": time.time() + REMOTE_CONFIRMATION_TTL_SECONDS,
    }


def _remote_confirmation_prompt(command: Command) -> str:
    return (
        f"Confirmar acao remota: {_command_label(command)}? "
        "Use os botoes abaixo ou responda confirmar/cancelar. Expira em 60 segundos."
    )


def _remote_confirmation_buttons() -> dict:
    return {
        "inline_keyboard": [[
            {"text": "Confirmar", "callback_data": "axel_confirm"},
            {"text": "Cancelar", "callback_data": "axel_cancel"},
        ]]
    }


def _handle_remote_confirmation_reply(text: str, chat_id: str, *, callback_query_id: str = "") -> TelegramResponse | None:
    is_confirm = _is_remote_confirm_text(text) or text == "axel_confirm"
    is_cancel = _is_remote_cancel_text(text) or text == "axel_cancel"
    if not (is_confirm or is_cancel):
        return None

    pending = _remote_pending(chat_id)
    if not pending:
        return TelegramResponse(
            False,
            "Nao ha acao remota pendente para confirmar.",
            status="confirmation_missing",
            chat_id=chat_id,
            callback_query_id=callback_query_id,
        )

    command = pending.get("command")
    if not isinstance(command, Command):
        _clear_remote_pending(chat_id)
        return TelegramResponse(False, "A acao pendente estava invalida.", status="confirmation_invalid", chat_id=chat_id)

    if is_cancel:
        _clear_remote_pending(chat_id)
        log_telegram_event("remote_cancelled", chat_id=chat_id, action=command.action)
        return TelegramResponse(
            True,
            "Acao remota cancelada.",
            status="cancelled",
            action=command.action,
            chat_id=chat_id,
            callback_query_id=callback_query_id,
        )

    allowed, reason = _can_confirm_remotely(command, chat_id)
    if not allowed:
        _clear_remote_pending(chat_id)
        log_telegram_event("remote_confirmation_denied", chat_id=chat_id, action=command.action, reason=reason)
        return TelegramResponse(
            False,
            "Essa acao nao pode ser confirmada pelo Telegram. Use o PC.",
            status="blocked",
            action=command.action,
            chat_id=chat_id,
            callback_query_id=callback_query_id,
        )

    result = normalize_action_result(execute_telegram_command(command))
    _clear_remote_pending(chat_id)
    log_telegram_event("remote_confirmed", chat_id=chat_id, action=command.action, success=result.success)
    return TelegramResponse(
        result.success,
        result.message if result.message else "Acao remota executada.",
        status="ok" if result.success else "failed",
        action=command.action,
        chat_id=chat_id,
        callback_query_id=callback_query_id,
    )


def _resolve_retry_text(text: str, chat_id: str) -> tuple[str, bool]:
    normalized = normalize_text(text).lstrip("/").strip()
    if normalized not in _RETRY_PHRASES:
        return text, False
    previous = _CHAT_CONTEXT.get(_chat_key(chat_id), {}).get("last_text")
    if not previous:
        return text, False
    return str(previous), True


def _remember_chat_context(chat_id: str, text: str, raw_action: dict) -> None:
    normalized = normalize_text(text)
    if not chat_id or normalized in _RETRY_PHRASES:
        return
    if raw_action.get("intent") == "respond":
        return
    context = _CHAT_CONTEXT.setdefault(_chat_key(chat_id), {})
    context.update({
        "last_text": text,
        "last_intent": raw_action.get("intent"),
        "last_target": raw_action.get("target"),
    })


def _confirmation_help_response(chat_id: str) -> TelegramResponse | None:
    context = _CHAT_CONTEXT.get(_chat_key(chat_id), {})
    pending = _remote_pending(chat_id)
    if pending:
        command = pending.get("command")
        if isinstance(command, Command):
            return TelegramResponse(
                True,
                _remote_confirmation_prompt(command),
                status="confirmation_help",
                action=command.action,
                chat_id=chat_id,
                reply_markup=_remote_confirmation_buttons(),
            )
    blocked_action = context.get("blocked_action")
    if not blocked_action:
        return TelegramResponse(
            True,
            "No Telegram ainda nao ha confirmacao remota. Para executar a acao, use o Axel no PC e confirme por la.",
            status="confirmation_help",
            chat_id=chat_id,
        )
    return TelegramResponse(
        True,
        (
            f"Esse comando ficou bloqueado por seguranca: {blocked_action}. "
            "Para executar agora, repita o pedido no Axel pelo PC ou pela voz e confirme no painel. "
            "Confirmacao direta pelo Telegram ainda nao esta liberada."
        ),
        status="confirmation_help",
        action=str(blocked_action),
        chat_id=chat_id,
    )


def _undo_remote_pending_text(chat_id: str) -> str:
    pending = _remote_pending(chat_id)
    if pending:
        _clear_remote_pending(chat_id)
        return "Acao remota pendente cancelada. Nao desfaco automaticamente acoes ja executadas pelo Telegram."
    return "Nao ha acao remota pendente para desfazer. Undo real de acoes ja executadas ainda nao esta liberado."


def _is_confirmation_help(text: str) -> bool:
    normalized = normalize_text(text)
    return normalized in _CONFIRMATION_HELP_PHRASES or (
        "confirm" in normalized and any(term in normalized for term in {"como", "onde", "basta"})
    )


def execute_telegram_command(command):
    from core.executor import execute_result

    return execute_result(command)


def build_remote_decision(text: str) -> tuple[dict, object, object, dict]:
    trace = route_trace(text)
    raw_action = trace.match.result if trace.match else {"intent": "respond", "target": None, "response": "Nao entendi."}
    intent_level = trace.match.intent_level if trace.match else "conversa"
    complexity = classify_intent_complexity(text, intent_level=intent_level, raw_action=raw_action)
    decision = build_axel_brain_decision(
        text,
        raw_action,
        intent_level=intent_level,
        complexity_kind=complexity.kind,
    )
    route_payload = {
        "source": "telegram",
        "input": text,
        "intent": raw_action.get("intent"),
        "target": raw_action.get("target"),
        "group": trace.match.group_name if trace.match else "",
        "detector": trace.match.detector_name if trace.match else "",
        "intent_level": intent_level,
        "complexity": complexity.kind,
        "complexity_reason": complexity.reason,
        "checked_detectors": trace.checked_detectors,
        "checked_groups": list(trace.checked_groups),
    }
    contract = build_axel_brain_contract(
        source="telegram",
        user_input=text,
        raw_action=raw_action,
        plan=decision.plan,
        brief=decision.brief,
        route_trace=route_payload,
    )
    return raw_action, decision.plan, decision.brief, contract


def handle_telegram_text(text: str, *, chat_id: str = "", callback_query_id: str = "") -> TelegramResponse:
    clean = str(text or "").strip()
    if not clean:
        return TelegramResponse(False, "Envie uma mensagem para o Axel.", status="empty", chat_id=chat_id)

    remote_mode_response = _handle_remote_mode_command(clean, chat_id)
    if remote_mode_response:
        return remote_mode_response

    confirmation_reply = _handle_remote_confirmation_reply(clean, chat_id, callback_query_id=callback_query_id)
    if confirmation_reply:
        return confirmation_reply

    if _is_confirmation_help(clean):
        return _confirmation_help_response(chat_id)

    effective_text, retried = _resolve_retry_text(clean, chat_id)

    if not retried:
        shared_response = maybe_handle_shared_command(clean, undo_last=lambda: _undo_remote_pending_text(chat_id))
        if shared_response:
            return TelegramResponse(
                True,
                shared_response,
                status="ok",
                action="shared_command",
                chat_id=chat_id,
            )

    raw_action, _plan, _brief, contract = build_remote_decision(effective_text)
    _remember_chat_context(chat_id, effective_text, raw_action)
    if raw_action.get("intent") == "respond":
        if retried:
            return TelegramResponse(
                False,
                "Nao encontrei uma acao anterior boa para repetir agora.",
                status="retry_empty",
                action="respond",
                chat_id=chat_id,
                contract=contract,
            )
        return TelegramResponse(
            True,
            str(raw_action.get("response") or "Nao entendi."),
            action="respond",
            chat_id=chat_id,
            contract=contract,
        )

    command = normalize_action(raw_action)
    if not contract.get("remote_policy", {}).get("can_execute"):
        context = _CHAT_CONTEXT.setdefault(_chat_key(chat_id), {})
        context["blocked_action"] = command.action
        context["blocked_text"] = effective_text
        remote_allowed, remote_reason = _can_confirm_remotely(
            command,
            chat_id,
            contract.get("remote_policy", {}),
        )
        if remote_allowed:
            _store_remote_pending(chat_id, command, effective_text)
            log_telegram_event(
                "remote_confirmation_requested",
                chat_id=chat_id,
                text=clean,
                effective_text=effective_text,
                action=command.action,
                reason=remote_reason,
            )
            return TelegramResponse(
                False,
                _remote_confirmation_prompt(command),
                status="confirmation_required",
                action=command.action,
                chat_id=chat_id,
                contract=contract,
                reply_markup=_remote_confirmation_buttons(),
            )
        log_telegram_event(
            "blocked_action",
            chat_id=chat_id,
            text=clean,
            effective_text=effective_text,
            action=command.action,
            reason=f"{contract.get('remote_policy', {}).get('reason', '')}; {remote_reason}",
        )
        return _blocked_response(
            "Esse comando existe, mas precisa de confirmacao no PC antes de executar.",
            chat_id=chat_id,
            contract=contract,
        )

    result = normalize_action_result(execute_telegram_command(command))
    log_telegram_event(
        "handled",
        chat_id=chat_id,
        text=clean,
        effective_text=effective_text,
        action=command.action,
        success=result.success,
    )
    return TelegramResponse(
        result.success,
        result.message if result.message else "Sem resposta.",
        status="ok" if result.success else "failed",
        action=command.action,
        chat_id=chat_id,
        contract=contract,
    )


def handle_telegram_audio_request(
    request: TelegramRequest,
    *,
    transcribe_audio: Callable[[TelegramRequest], str] | None = None,
) -> TelegramResponse:
    if not request.media_file_id:
        return TelegramResponse(False, "Audio do Telegram sem arquivo reconhecivel.", status="audio_invalid", chat_id=request.chat_id)
    if transcribe_audio is None:
        log_telegram_event("audio_transcription_unavailable", chat_id=request.chat_id, media_kind=request.media_kind)
        return TelegramResponse(
            False,
            "Recebi o audio, mas a transcricao remota do Telegram ainda nao esta configurada neste ambiente.",
            status="audio_transcription_unavailable",
            action="telegram_audio",
            chat_id=request.chat_id,
        )
    try:
        text = str(transcribe_audio(request) or "").strip()
    except Exception as exc:
        log_telegram_event("audio_transcription_failed", chat_id=request.chat_id, error=type(exc).__name__)
        return TelegramResponse(
            False,
            f"Nao consegui transcrever o audio do Telegram: {exc}",
            status="audio_transcription_failed",
            action="telegram_audio",
            chat_id=request.chat_id,
        )
    if not text:
        return TelegramResponse(
            False,
            "Nao consegui reconhecer fala util nesse audio do Telegram.",
            status="audio_transcription_empty",
            action="telegram_audio",
            chat_id=request.chat_id,
        )
    log_telegram_event("audio_transcribed", chat_id=request.chat_id, media_kind=request.media_kind, chars=len(text))
    return handle_telegram_text(text, chat_id=request.chat_id, callback_query_id=request.callback_query_id)


def handle_telegram_update(
    update: dict[str, Any],
    *,
    allowed_chat_ids: set[str],
    transcribe_audio: Callable[[TelegramRequest], str] | None = None,
) -> TelegramResponse:
    request = parse_inbound_update(update)
    if not chat_allowed(request.chat_id, allowed_chat_ids):
        log_telegram_event("blocked_chat", chat_id=request.chat_id, username=request.username)
        return _blocked_response("Chat nao autorizado.", chat_id=request.chat_id)
    if request.media_file_id and not request.text:
        return handle_telegram_audio_request(request, transcribe_audio=transcribe_audio)
    return handle_telegram_text(request.text, chat_id=request.chat_id, callback_query_id=request.callback_query_id)
