import base64
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI

SCOPES = (
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-library-modify",
    "user-library-read",
)
TOKEN_URL = "https://accounts.spotify.com/api/token"
AUTH_URL = "https://accounts.spotify.com/authorize"
DOTENV_PATH = ROOT / ".env"


class _CallbackHandler(BaseHTTPRequestHandler):
    server_version = "AxelSpotifyOAuth/1.0"

    def log_message(self, _format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        self.server.auth_code = (params.get("code") or [""])[0]
        self.server.auth_state = (params.get("state") or [""])[0]
        self.server.auth_error = (params.get("error") or [""])[0]
        body = "Spotify conectado ao Axel. Pode fechar esta aba."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


def _update_env(values: dict[str, str]):
    lines = []
    if DOTENV_PATH.exists():
        lines = DOTENV_PATH.read_text(encoding="utf-8").splitlines()

    remaining = dict(values)
    updated = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in remaining:
            updated.append(f"{key}={remaining.pop(key)}")
        else:
            updated.append(line)

    if remaining and updated and updated[-1].strip():
        updated.append("")
    for key, value in remaining.items():
        updated.append(f"{key}={value}")

    DOTENV_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> int:
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("Configure AXEL_SPOTIFY_CLIENT_ID e AXEL_SPOTIFY_CLIENT_SECRET no .env primeiro.")
        return 1

    redirect = SPOTIFY_REDIRECT_URI or "http://127.0.0.1:8888/callback"
    parsed_redirect = urlparse(redirect)
    host = parsed_redirect.hostname or "127.0.0.1"
    port = parsed_redirect.port or 8888
    state = secrets.token_urlsafe(16)

    server = HTTPServer((host, port), _CallbackHandler)
    server.auth_code = ""
    server.auth_state = ""
    server.auth_error = ""
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    auth_query = urlencode(
        {
            "client_id": SPOTIFY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect,
            "scope": " ".join(SCOPES),
            "state": state,
        }
    )
    auth_link = f"{AUTH_URL}?{auth_query}"
    print("Abrindo autorização do Spotify...")
    print(auth_link)
    print("Mantenha este terminal aberto ate a pagina voltar para o callback.")
    webbrowser.open(auth_link)

    try:
        deadline = time.time() + 180
        while time.time() < deadline and not server.auth_code and not server.auth_error:
            time.sleep(0.2)
    except KeyboardInterrupt:
        server.shutdown()
        print("Autorizacao cancelada. Rode o script de novo e mantenha o terminal aberto ate concluir.")
        return 1

    server.shutdown()
    if server.auth_error:
        print(f"Spotify retornou erro: {server.auth_error}")
        return 1
    if not server.auth_code:
        print("Tempo esgotado aguardando o callback do Spotify.")
        return 1
    if server.auth_state != state:
        print("Estado OAuth inválido. Abortando por segurança.")
        return 1

    basic = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode("ascii")
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": server.auth_code,
            "redirect_uri": redirect,
        },
        headers={"Authorization": f"Basic {basic}"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json() or {}
    access_token = str(payload.get("access_token") or "").strip()
    refresh_token = str(payload.get("refresh_token") or "").strip()
    if not access_token or not refresh_token:
        print("Spotify não retornou tokens completos.")
        return 1

    _update_env(
        {
            "AXEL_SPOTIFY_ACCESS_TOKEN": access_token,
            "AXEL_SPOTIFY_REFRESH_TOKEN": refresh_token,
            "AXEL_SPOTIFY_REDIRECT_URI": redirect,
        }
    )
    print("Spotify OAuth configurado. Reinicie o Axel para carregar os tokens novos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
