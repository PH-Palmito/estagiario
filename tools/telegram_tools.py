from __future__ import annotations

import threading

import requests

from config import TELEGRAM_ALLOWED_CHAT_IDS, TELEGRAM_BOT_TOKEN, TELEGRAM_POLL_INTERVAL_SECONDS
from services.telegram_polling import TelegramPollingState, poll_telegram_updates, telegram_api_url

_TELEGRAM_STARTED = False
_TELEGRAM_LOCK = threading.Lock()
_TELEGRAM_STATE = TelegramPollingState()


def _poll_interval() -> float:
    try:
        return max(0.5, float(str(TELEGRAM_POLL_INTERVAL_SECONDS or "2")))
    except Exception:
        return 2.0


def telegram_bridge_status() -> str:
    from services.telegram_gateway import parse_allowed_chat_ids

    status = "ativo" if _TELEGRAM_STARTED else "parado"
    allowed = parse_allowed_chat_ids(TELEGRAM_ALLOWED_CHAT_IDS)
    allowlist = f"{len(allowed)} chat(s) autorizado(s)" if allowed else "sem allowlist configurada"
    token = "token configurado" if TELEGRAM_BOT_TOKEN else "token ausente"
    return f"Telegram Bot: {status}. {token}. {allowlist}. Offset: {_TELEGRAM_STATE.offset}."


def telegram_recent_chats(limit: int = 10) -> str:
    if not TELEGRAM_BOT_TOKEN:
        return "Telegram Bot: configure AXEL_TELEGRAM_BOT_TOKEN no .env para descobrir seu chat_id."

    response = requests.get(
        telegram_api_url(TELEGRAM_BOT_TOKEN, "getUpdates"),
        params={"timeout": 0, "limit": max(1, min(int(limit or 10), 50))},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    chats: dict[str, str] = {}
    for update in payload.get("result", []):
        message = update.get("message") if isinstance(update.get("message"), dict) else {}
        if not message:
            message = update.get("edited_message") if isinstance(update.get("edited_message"), dict) else {}
        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        chat_id = str(chat.get("id") or "").strip()
        if not chat_id:
            continue
        label = str(chat.get("username") or chat.get("first_name") or chat.get("title") or "sem nome").strip()
        chats[chat_id] = label

    if not chats:
        return "Telegram Bot: nenhum chat recente. Envie /start ou uma mensagem para o bot e tente de novo."

    summary = "; ".join(f"{chat_id} ({label})" for chat_id, label in chats.items())
    return f"Chats recentes do Telegram: {summary}. Coloque o seu id em AXEL_TELEGRAM_ALLOWED_CHAT_IDS."


def start_telegram_bridge() -> str:
    from services.telegram_gateway import parse_allowed_chat_ids

    global _TELEGRAM_STARTED
    with _TELEGRAM_LOCK:
        if _TELEGRAM_STARTED:
            return telegram_bridge_status()
        if not TELEGRAM_BOT_TOKEN:
            return "Telegram Bot nao iniciado: configure AXEL_TELEGRAM_BOT_TOKEN no .env."

        allowed = parse_allowed_chat_ids(TELEGRAM_ALLOWED_CHAT_IDS)
        if not allowed:
            return "Telegram Bot nao iniciado: configure AXEL_TELEGRAM_ALLOWED_CHAT_IDS no .env."

        threading.Thread(
            target=lambda: poll_telegram_updates(
                token=TELEGRAM_BOT_TOKEN,
                allowed_chat_ids=allowed,
                state=_TELEGRAM_STATE,
                interval_seconds=_poll_interval(),
            ),
            name="axel-telegram-bot",
            daemon=True,
        ).start()
        _TELEGRAM_STARTED = True
    return telegram_bridge_status()


def simulate_telegram_message(text: str, chat_id: str | None = None) -> str:
    from services.telegram_gateway import handle_telegram_update, parse_allowed_chat_ids

    allowed = parse_allowed_chat_ids(TELEGRAM_ALLOWED_CHAT_IDS)
    selected_chat = str(chat_id or next(iter(allowed), "")).strip()
    response = handle_telegram_update(
        {"message": {"chat": {"id": selected_chat}, "text": text, "message_id": 1}},
        allowed_chat_ids=allowed,
    )
    prefix = "Resposta Telegram" if response.ok else "Telegram bloqueado"
    return f"{prefix}: {response.text}"
