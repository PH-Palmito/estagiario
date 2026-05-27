import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SANDBOX_DIR = BASE_DIR / "sandbox"
SANDBOX_DIR.mkdir(exist_ok=True)
DOTENV_PATH = BASE_DIR / ".env"
_DOTENV_LOADED = False


def load_dotenv(dotenv_path: Path | None = None):
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    path = dotenv_path or DOTENV_PATH
    if not path.exists():
        _DOTENV_LOADED = True
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)

    _DOTENV_LOADED = True


def env_str(name: str, default: str = "", aliases: tuple[str, ...] = ()) -> str:
    load_dotenv()
    for key in (name, *aliases):
        value = str(os.environ.get(key, "")).strip()
        if value:
            return value
    return default


def join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


OLLAMA_BASE_URL = env_str(
    "AXEL_OLLAMA_BASE_URL",
    default="http://localhost:11434",
    aliases=("OLLAMA_BASE_URL",),
)
OLLAMA_TEXT_MODEL = env_str(
    "AXEL_OLLAMA_TEXT_MODEL",
    default="qwen2.5:0.5b",
    aliases=("OLLAMA_TEXT_MODEL",),
)
OLLAMA_VISION_MODEL = env_str(
    "AXEL_OLLAMA_VISION_MODEL",
    default="",
    aliases=("OLLAMA_VISION_MODEL",),
)
GEMINI_API_KEY = env_str(
    "AXEL_GEMINI_API_KEY",
    default="",
    aliases=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
)
GEMINI_MODEL = env_str(
    "AXEL_GEMINI_MODEL",
    default="gemini-2.5-flash",
    aliases=("GEMINI_MODEL",),
)
GEMINI_COMPLEX_CHAT_ENABLED = env_str(
    "AXEL_GEMINI_COMPLEX_CHAT_ENABLED",
    default="1",
    aliases=("GEMINI_COMPLEX_CHAT_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
GEMINI_PRIMARY_TEXT_ENABLED = env_str(
    "AXEL_GEMINI_PRIMARY_TEXT_ENABLED",
    default="1",
    aliases=("GEMINI_PRIMARY_TEXT_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
GEMINI_TTS_MODEL = env_str(
    "AXEL_GEMINI_TTS_MODEL",
    default="gemini-3.1-flash-tts-preview",
    aliases=("GEMINI_TTS_MODEL",),
)
SUPABASE_REST_URL = env_str(
    "AXEL_SUPABASE_REST_URL",
    default="",
    aliases=("SUPABASE_REST_URL", "NEXT_PUBLIC_SUPABASE_URL"),
).rstrip("/")
SUPABASE_PUBLISHABLE_KEY = env_str(
    "AXEL_SUPABASE_PUBLISHABLE_KEY",
    default="",
    aliases=("SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"),
)
SUPABASE_ANON_KEY = env_str(
    "AXEL_SUPABASE_ANON_KEY",
    default="",
    aliases=("SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY"),
)
SUPABASE_MEMORY_TABLE = env_str(
    "AXEL_SUPABASE_MEMORY_TABLE",
    default="axel_memory_states",
    aliases=("SUPABASE_MEMORY_TABLE",),
)
SUPABASE_SYNC_ENABLED = env_str(
    "AXEL_SUPABASE_SYNC_ENABLED",
    default="1",
    aliases=("SUPABASE_SYNC_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
OBSIDIAN_VAULT_PATH = env_str(
    "AXEL_OBSIDIAN_VAULT_PATH",
    default="",
    aliases=("OBSIDIAN_VAULT_PATH",),
).strip()
OBSIDIAN_SYNC_ENABLED = env_str(
    "AXEL_OBSIDIAN_SYNC_ENABLED",
    default="1",
    aliases=("OBSIDIAN_SYNC_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
INVESTIDOR10_WALLET_URL = env_str(
    "AXEL_INVESTIDOR10_WALLET_URL",
    default="",
    aliases=("INVESTIDOR10_WALLET_URL",),
)
INVESTIDOR10_PRIVATE_WALLET_URL = env_str(
    "AXEL_INVESTIDOR10_PRIVATE_WALLET_URL",
    default="https://investidor10.com.br/wallet/my-wallet",
    aliases=("INVESTIDOR10_PRIVATE_WALLET_URL",),
)
EDGE_USER_DATA_DIR = env_str(
    "AXEL_EDGE_USER_DATA_DIR",
    default=str(Path(os.environ.get("LOCALAPPDATA", "")).joinpath("Microsoft", "Edge", "User Data")),
    aliases=("EDGE_USER_DATA_DIR",),
)
EDGE_PROFILE_DIRECTORY = env_str(
    "AXEL_EDGE_PROFILE_DIRECTORY",
    default="Default",
    aliases=("EDGE_PROFILE_DIRECTORY",),
)
WALLET_PLAYWRIGHT_ENABLED = env_str(
    "AXEL_WALLET_PLAYWRIGHT_ENABLED",
    default="1",
    aliases=("WALLET_PLAYWRIGHT_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
WALLET_PLAYWRIGHT_CHANNEL = env_str(
    "AXEL_WALLET_PLAYWRIGHT_CHANNEL",
    default="msedge",
    aliases=("WALLET_PLAYWRIGHT_CHANNEL",),
)
WALLET_PLAYWRIGHT_USER_DATA_DIR = env_str(
    "AXEL_WALLET_PLAYWRIGHT_USER_DATA_DIR",
    default="",
    aliases=("WALLET_PLAYWRIGHT_USER_DATA_DIR",),
)
BRAPI_TOKEN = env_str(
    "AXEL_BRAPI_TOKEN",
    default="",
    aliases=("BRAPI_TOKEN",),
)
BRAPI_ENABLED = env_str(
    "AXEL_BRAPI_ENABLED",
    default="1",
    aliases=("BRAPI_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
OPENWEATHER_API_KEY = env_str(
    "AXEL_OPENWEATHER_API_KEY",
    default="",
    aliases=("OPENWEATHER_API_KEY", "OPENWEATHERMAP_API_KEY"),
)
OPENWEATHER_ENABLED = env_str(
    "AXEL_OPENWEATHER_ENABLED",
    default="1",
    aliases=("OPENWEATHER_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
NEWSAPI_KEY = env_str(
    "AXEL_NEWSAPI_KEY",
    default="",
    aliases=("NEWSAPI_KEY",),
)
NEWSAPI_ENABLED = env_str(
    "AXEL_NEWSAPI_ENABLED",
    default="1",
    aliases=("NEWSAPI_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
INVESTMENT_BACKGROUND_REFRESH_ENABLED = env_str(
    "AXEL_INVESTMENT_BACKGROUND_REFRESH_ENABLED",
    default="0",
    aliases=("INVESTMENT_BACKGROUND_REFRESH_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
WHATSAPP_BRIDGE_ENABLED = env_str(
    "AXEL_WHATSAPP_BRIDGE_ENABLED",
    default="0",
    aliases=("WHATSAPP_BRIDGE_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
WHATSAPP_ALLOWED_SENDERS = env_str(
    "AXEL_WHATSAPP_ALLOWED_SENDERS",
    default="",
    aliases=("WHATSAPP_ALLOWED_SENDERS",),
)
WHATSAPP_WEBHOOK_TOKEN = env_str(
    "AXEL_WHATSAPP_WEBHOOK_TOKEN",
    default="",
    aliases=("WHATSAPP_WEBHOOK_TOKEN",),
)
WHATSAPP_BRIDGE_HOST = env_str(
    "AXEL_WHATSAPP_BRIDGE_HOST",
    default="127.0.0.1",
    aliases=("WHATSAPP_BRIDGE_HOST",),
)
WHATSAPP_BRIDGE_PORT = env_str(
    "AXEL_WHATSAPP_BRIDGE_PORT",
    default="8765",
    aliases=("WHATSAPP_BRIDGE_PORT",),
)
AXEL_PERFORMANCE_MODE = env_str(
    "AXEL_PERFORMANCE_MODE",
    default="balanced",
    aliases=("PERFORMANCE_MODE",),
).strip().lower()
SPOTIFY_API_ENABLED = env_str(
    "AXEL_SPOTIFY_API_ENABLED",
    default="1",
    aliases=("SPOTIFY_API_ENABLED",),
).strip().lower() not in {"0", "false", "no", "off"}
SPOTIFY_CLIENT_ID = env_str(
    "AXEL_SPOTIFY_CLIENT_ID",
    default="",
    aliases=("SPOTIFY_CLIENT_ID",),
)
SPOTIFY_CLIENT_SECRET = env_str(
    "AXEL_SPOTIFY_CLIENT_SECRET",
    default="",
    aliases=("SPOTIFY_CLIENT_SECRET",),
)
SPOTIFY_REDIRECT_URI = env_str(
    "AXEL_SPOTIFY_REDIRECT_URI",
    default="http://127.0.0.1:8888/callback",
    aliases=("SPOTIFY_REDIRECT_URI",),
)
SPOTIFY_ACCESS_TOKEN = env_str(
    "AXEL_SPOTIFY_ACCESS_TOKEN",
    default="",
    aliases=("SPOTIFY_ACCESS_TOKEN",),
)
SPOTIFY_REFRESH_TOKEN = env_str(
    "AXEL_SPOTIFY_REFRESH_TOKEN",
    default="",
    aliases=("SPOTIFY_REFRESH_TOKEN",),
)
SPOTIFY_DEVICE_ID = env_str(
    "AXEL_SPOTIFY_DEVICE_ID",
    default="",
    aliases=("SPOTIFY_DEVICE_ID",),
)
