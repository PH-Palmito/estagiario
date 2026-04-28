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
INVESTIDOR10_WALLET_URL = env_str(
    "AXEL_INVESTIDOR10_WALLET_URL",
    default="",
    aliases=("INVESTIDOR10_WALLET_URL",),
)
