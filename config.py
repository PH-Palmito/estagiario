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
