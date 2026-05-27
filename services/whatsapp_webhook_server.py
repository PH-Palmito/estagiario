from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from config import WHATSAPP_ALLOWED_SENDERS, WHATSAPP_WEBHOOK_TOKEN
from services.whatsapp_gateway import handle_whatsapp_payload, parse_allowed_senders


class WhatsAppWebhookHandler(BaseHTTPRequestHandler):
    server_version = "AxelWhatsAppWebhook/1.0"

    def _write_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        token = (query.get("token") or [""])[0]
        if WHATSAPP_WEBHOOK_TOKEN and token != WHATSAPP_WEBHOOK_TOKEN:
            self._write_json(403, {"ok": False, "error": "invalid token"})
            return
        self._write_json(200, {"ok": True, "service": "axel-whatsapp-webhook"})

    def do_POST(self) -> None:
        if WHATSAPP_WEBHOOK_TOKEN and self.headers.get("X-Axel-Webhook-Token", "") != WHATSAPP_WEBHOOK_TOKEN:
            self._write_json(403, {"ok": False, "error": "invalid token"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("payload must be object")
        except Exception as exc:
            self._write_json(400, {"ok": False, "error": str(exc)})
            return

        response = handle_whatsapp_payload(
            payload,
            allowed_senders=parse_allowed_senders(WHATSAPP_ALLOWED_SENDERS),
        )
        self._write_json(
            200 if response.ok else 403 if response.status == "blocked" else 400,
            {
                "ok": response.ok,
                "status": response.status,
                "reply": response.text,
                "action": response.action,
            },
        )


def run_whatsapp_webhook_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = HTTPServer((host, port), WhatsAppWebhookHandler)
    print(f"Axel WhatsApp webhook ouvindo em http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_whatsapp_webhook_server()
