from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SANDBOX_DIR = BASE_DIR / "sandbox"
SANDBOX_DIR.mkdir(exist_ok=True)
