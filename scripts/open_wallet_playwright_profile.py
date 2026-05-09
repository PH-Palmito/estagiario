import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import INVESTIDOR10_PRIVATE_WALLET_URL, WALLET_PLAYWRIGHT_USER_DATA_DIR


EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)


def _edge_path() -> Path:
    for candidate in EDGE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise RuntimeError("Nao encontrei o Microsoft Edge instalado.")


def _profile_dir() -> Path:
    configured = str(WALLET_PLAYWRIGHT_USER_DATA_DIR or "").strip()
    if configured:
        return Path(configured).expanduser()
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
    return base / "Axel" / "WalletBrowserProfile"


def main() -> int:
    profile_dir = _profile_dir()
    profile_dir.mkdir(parents=True, exist_ok=True)
    url = str(INVESTIDOR10_PRIVATE_WALLET_URL or "https://investidor10.com.br/wallet/my-wallet").strip()
    subprocess.Popen(
        [
            str(_edge_path()),
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--new-window",
            url,
        ]
    )
    print(f"Perfil aberto: {profile_dir}")
    print("Se ainda nao estiver no .env, use:")
    print(f"AXEL_WALLET_PLAYWRIGHT_USER_DATA_DIR={profile_dir}")
    print("Faca login no Investidor10 nessa janela uma vez; depois pode fechar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
