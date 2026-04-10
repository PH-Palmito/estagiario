from pathlib import Path
from config import SANDBOX_DIR


def _safe_path(relative_path: str) -> Path:
    base = Path(SANDBOX_DIR).resolve()
    target = (base / relative_path).resolve()

    if base not in target.parents and target != base:
        raise ValueError("Caminho fora da sandbox.")
    return target


def create_folder(path: str):
    folder = _safe_path(path)
    folder.mkdir(parents=True, exist_ok=True)
    return f"Pasta criada: {folder.name}"