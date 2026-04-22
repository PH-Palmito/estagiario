import json
from pathlib import Path


TTS_PRONUNCIATIONS_PATH = Path("memory") / "tts_pronunciations.json"


def load_tts_pronunciations() -> dict[str, str]:
    try:
        data = json.loads(TTS_PRONUNCIATIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return {
        str(key): str(value)
        for key, value in data.items()
        if str(key).strip() and str(value).strip()
    }


def save_tts_pronunciations(pronunciations: dict[str, str]) -> None:
    TTS_PRONUNCIATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean = {
        str(key): str(value)
        for key, value in pronunciations.items()
        if str(key).strip() and str(value).strip()
    }
    TTS_PRONUNCIATIONS_PATH.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def set_tts_pronunciation(term: str, pronunciation: str) -> None:
    pronunciations = load_tts_pronunciations()
    pronunciations[term] = pronunciation
    save_tts_pronunciations(pronunciations)


def get_tts_pronunciation(term: str) -> str | None:
    pronunciations = load_tts_pronunciations()
    if term in pronunciations:
        return pronunciations[term]

    lowered = term.lower()
    for saved_term, saved_pronunciation in pronunciations.items():
        if saved_term.lower() == lowered:
            return saved_pronunciation

    return None


def remove_tts_pronunciation(term: str) -> bool:
    pronunciations = load_tts_pronunciations()
    if term not in pronunciations:
        lowered = term.lower()
        matched_key = next((saved for saved in pronunciations if saved.lower() == lowered), None)
        if not matched_key:
            return False
        term = matched_key
    pronunciations.pop(term, None)
    save_tts_pronunciations(pronunciations)
    return True
