from pathlib import Path

from memory.json_store import read_json_file, update_json_file, write_json_atomic

TTS_PRONUNCIATIONS_PATH = Path("memory") / "tts_pronunciations.json"


def load_tts_pronunciations() -> dict[str, str]:
    data = read_json_file(TTS_PRONUNCIATIONS_PATH, {}, validator=lambda value: isinstance(value, dict))

    return {
        str(key): str(value)
        for key, value in data.items()
        if str(key).strip() and str(value).strip()
    }


def save_tts_pronunciations(pronunciations: dict[str, str]) -> None:
    clean = {
        str(key): str(value)
        for key, value in pronunciations.items()
        if str(key).strip() and str(value).strip()
    }
    write_json_atomic(TTS_PRONUNCIATIONS_PATH, clean, indent=2)


def set_tts_pronunciation(term: str, pronunciation: str) -> None:
    def apply(pronunciations: dict) -> dict:
        pronunciations = {
            str(key): str(value)
            for key, value in pronunciations.items()
            if str(key).strip() and str(value).strip()
        }
        pronunciations[term] = pronunciation
        return pronunciations

    update_json_file(
        TTS_PRONUNCIATIONS_PATH,
        {},
        apply,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )


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
    def remove(pronunciations: dict) -> dict:
        pronunciations = dict(pronunciations or {})
        pronunciations.pop(term, None)
        return pronunciations

    update_json_file(
        TTS_PRONUNCIATIONS_PATH,
        {},
        remove,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    return True
