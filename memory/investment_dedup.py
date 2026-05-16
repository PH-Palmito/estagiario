import hashlib
import re
import time
from pathlib import Path
from typing import Callable


Normalize = Callable[[str], str]
LoadJson = Callable[[Path], dict]
SaveJson = Callable[[Path, dict], None]


def load_seen_state(path: Path, *, load_json: LoadJson) -> dict:
    data = load_json(path)
    return data if isinstance(data, dict) else {}


def save_seen_state(path: Path, state: dict, *, save_json: SaveJson) -> None:
    if not isinstance(state, dict):
        return
    try:
        save_json(path, state)
    except Exception:
        pass


def text_fingerprint(text: str, *, normalize: Normalize) -> str:
    normalized = normalize(text)
    normalized = re.sub(r"[^\w\s]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def signal_fingerprint(kind: str, text: str, *, normalize: Normalize) -> str:
    return text_fingerprint(f"{kind}: {text}", normalize=normalize)


def filter_new_signal_texts(
    kind: str,
    texts: list[str],
    *,
    signal_state_path: Path,
    load_json: LoadJson,
    save_json: SaveJson,
    normalize: Normalize,
    only_new: bool = False,
    mark_seen: bool = False,
) -> list[str]:
    if not only_new and not mark_seen:
        return texts

    state = load_seen_state(signal_state_path, load_json=load_json)
    seen_by_kind = state.get(kind)
    if not isinstance(seen_by_kind, list):
        seen_by_kind = []
    seen_hashes = set(str(item) for item in seen_by_kind)
    fresh: list[str] = []
    new_hashes: list[str] = []

    for text in texts:
        fingerprint = signal_fingerprint(kind, text, normalize=normalize)
        if only_new and fingerprint and fingerprint in seen_hashes:
            continue
        fresh.append(text)
        if fingerprint:
            new_hashes.append(fingerprint)

    if mark_seen and new_hashes:
        combined = list(dict.fromkeys([*seen_hashes, *new_hashes]))
        state[kind] = combined[-80:]
        state["updated_at"] = time.time()
        save_seen_state(signal_state_path, state, save_json=save_json)

    return fresh
