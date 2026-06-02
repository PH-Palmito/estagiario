from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


@dataclass
class TelegramPollingState:
    offset: int = 0
    running: bool = False


def telegram_api_url(token: str, method: str) -> str:
    return TELEGRAM_API.format(token=str(token or "").strip(), method=method)


def send_telegram_message(
    token: str,
    chat_id: str,
    text: str,
    *,
    reply_markup: dict | None = None,
    timeout_seconds: int = 20,
) -> None:
    if not token:
        raise RuntimeError("Token do Telegram nao configurado.")
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(
        telegram_api_url(token, "sendMessage"),
        json=payload,
        timeout=timeout_seconds,
    ).raise_for_status()


def answer_callback_query(token: str, callback_query_id: str, text: str = "", *, timeout_seconds: int = 20) -> None:
    if not token or not callback_query_id:
        return
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text[:180]
    requests.post(
        telegram_api_url(token, "answerCallbackQuery"),
        json=payload,
        timeout=timeout_seconds,
    ).raise_for_status()


def poll_telegram_updates(
    *,
    token: str,
    allowed_chat_ids: set[str],
    state: TelegramPollingState | None = None,
    interval_seconds: float = 2.0,
    stop_when: Callable[[], bool] | None = None,
    on_response: Callable[[object], None] | None = None,
) -> None:
    from services.telegram_gateway import handle_telegram_update, log_telegram_event

    if not token:
        raise RuntimeError("Token do Telegram nao configurado.")
    polling_state = state or TelegramPollingState()
    polling_state.running = True
    log_telegram_event("polling_started", allowed_chats=len(allowed_chat_ids), offset=polling_state.offset)
    stop_when = stop_when or (lambda: False)

    while not stop_when():
        try:
            response = requests.get(
                telegram_api_url(token, "getUpdates"),
                params={"timeout": 20, "offset": polling_state.offset + 1},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            updates = payload.get("result") if isinstance(payload, dict) else []
            for update in updates if isinstance(updates, list) else []:
                update_id = int(update.get("update_id") or 0)
                if update_id > polling_state.offset:
                    polling_state.offset = update_id
                result = handle_telegram_update(update, allowed_chat_ids=allowed_chat_ids)
                log_telegram_event(
                    "polling_update",
                    chat_id=result.chat_id,
                    status=result.status,
                    action=result.action,
                    ok=result.ok,
                )
                if result.chat_id and result.text:
                    send_telegram_message(
                        token,
                        result.chat_id,
                        result.text,
                        reply_markup=getattr(result, "reply_markup", None),
                    )
                callback_query_id = getattr(result, "callback_query_id", "")
                if callback_query_id:
                    answer_callback_query(token, callback_query_id, "OK")
                if on_response:
                    on_response(result)
        except Exception as exc:
            log_telegram_event("polling_error", error=type(exc).__name__, message=str(exc)[:300])
            time.sleep(max(1.0, float(interval_seconds)))
            continue
        time.sleep(max(0.2, float(interval_seconds)))

    polling_state.running = False
    log_telegram_event("polling_stopped", offset=polling_state.offset)
