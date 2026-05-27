from __future__ import annotations

import threading

from config import WHATSAPP_ALLOWED_SENDERS, WHATSAPP_BRIDGE_HOST, WHATSAPP_BRIDGE_PORT
from services.whatsapp_gateway import handle_whatsapp_payload, parse_allowed_senders
from services.whatsapp_webhook_server import run_whatsapp_webhook_server

_BRIDGE_STARTED = False
_BRIDGE_LOCK = threading.Lock()
_BRIDGE_INFO = {
    "host": WHATSAPP_BRIDGE_HOST,
    "port": WHATSAPP_BRIDGE_PORT,
}


def _bridge_port() -> int:
    try:
        return int(str(WHATSAPP_BRIDGE_PORT or "8765"))
    except Exception:
        return 8765


def whatsapp_bridge_status() -> str:
    status = "ativo" if _BRIDGE_STARTED else "parado"
    allowed = parse_allowed_senders(WHATSAPP_ALLOWED_SENDERS)
    allowlist = f"{len(allowed)} numero(s) autorizado(s)" if allowed else "sem allowlist configurada"
    return f"Ponte WhatsApp local: {status}. Endpoint: http://{_BRIDGE_INFO['host']}:{_BRIDGE_INFO['port']}. {allowlist}."


def start_whatsapp_bridge() -> str:
    global _BRIDGE_STARTED
    with _BRIDGE_LOCK:
        if _BRIDGE_STARTED:
            return whatsapp_bridge_status()

        host = str(WHATSAPP_BRIDGE_HOST or "127.0.0.1")
        port = _bridge_port()
        _BRIDGE_INFO.update({"host": host, "port": str(port)})
        threading.Thread(
            target=lambda: run_whatsapp_webhook_server(host=host, port=port),
            name="axel-whatsapp-local-bridge",
            daemon=True,
        ).start()
        _BRIDGE_STARTED = True
    return whatsapp_bridge_status()


def simulate_whatsapp_message(text: str, sender: str | None = None) -> str:
    allowed = parse_allowed_senders(WHATSAPP_ALLOWED_SENDERS)
    selected_sender = sender or next(iter(allowed), "")
    response = handle_whatsapp_payload(
        {"from": selected_sender, "text": text},
        allowed_senders=allowed,
    )
    prefix = "Resposta WhatsApp" if response.ok else "WhatsApp bloqueado"
    return f"{prefix}: {response.text}"
