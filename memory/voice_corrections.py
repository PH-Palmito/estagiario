import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path


VOICE_CORRECTIONS_PATH = Path("memory") / "voice_corrections.json"

STARTER_VOICE_CORRECTIONS = [
    {"heard": "chegar", "means": "fechar"},
    {"heard": "que tem na tela", "means": "o que tem na tela"},
    {"heard": "e que tem na tela", "means": "o que tem na tela"},
    {"heard": "o que esta ai na tela", "means": "o que tem na tela"},
    {"heard": "o que ta ai na tela", "means": "o que tem na tela"},
    {"heard": "o que esta na tela", "means": "o que tem na tela"},
    {"heard": "o que ta na tela", "means": "o que tem na tela"},
    {"heard": "o kit tem na tela", "means": "o que tem na tela"},
    {"heard": "uki teena tela", "means": "o que tem na tela"},
    {"heard": "resume a tela", "means": "resuma a tela"},
    {"heard": "resumir tela", "means": "resuma a tela"},
    {"heard": "bezumia telap", "means": "resuma a tela"},
    {"heard": "lig ser licionado", "means": "ler selecionado"},
    {"heard": "os links selecionados", "means": "ler selecionado"},
    {"heard": "leica que foi seleccionario", "means": "ler selecionado"},
    {"heard": "humor javes", "means": "humor jarvis"},
    {"heard": "humor jarves", "means": "humor jarvis"},
    {"heard": "modo mordomo", "means": "humor jarvis"},
]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text.strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^\w\s:/.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_voice_corrections():
    if not VOICE_CORRECTIONS_PATH.exists():
        return []

    try:
        data = json.loads(VOICE_CORRECTIONS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(data, list):
        return []

    corrections = []
    for item in data:
        if not isinstance(item, dict):
            continue

        heard = str(item.get("heard", "")).strip()
        means = str(item.get("means", "")).strip()
        if not heard or not means:
            continue

        corrections.append(
            {
                "heard": heard,
                "heard_normalized": normalize_text(heard),
                "means": means,
                "uses": int(item.get("uses", 0) or 0),
            }
        )

    return corrections


def load_starter_voice_corrections():
    return [
        {
            "heard": item["heard"],
            "heard_normalized": normalize_text(item["heard"]),
            "means": item["means"],
            "uses": 0,
            "starter": True,
        }
        for item in STARTER_VOICE_CORRECTIONS
        if item.get("heard") and item.get("means")
    ]


def save_voice_corrections(corrections):
    VOICE_CORRECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "heard": item["heard"],
            "means": item["means"],
            "uses": int(item.get("uses", 0) or 0),
        }
        for item in corrections
        if item.get("heard") and item.get("means")
    ]
    VOICE_CORRECTIONS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def remember_voice_correction(heard: str, means: str):
    heard = heard.strip()
    means = means.strip()

    if not heard or not means:
        return False

    heard_normalized = normalize_text(heard)
    corrections = load_voice_corrections()

    for item in corrections:
        if item["heard_normalized"] == heard_normalized:
            item["heard"] = heard
            item["means"] = means
            save_voice_corrections(corrections)
            return True

    corrections.append({"heard": heard, "heard_normalized": heard_normalized, "means": means, "uses": 0})
    save_voice_corrections(corrections)
    return True


def forget_voice_correction(heard: str):
    heard_normalized = normalize_text(heard)
    corrections = load_voice_corrections()
    kept = [item for item in corrections if item["heard_normalized"] != heard_normalized]

    if len(kept) == len(corrections):
        return False

    save_voice_corrections(kept)
    return True


def list_voice_corrections():
    return load_voice_corrections()


def apply_voice_correction(text: str):
    normalized = normalize_text(text)
    if not normalized:
        return None

    stored_corrections = load_voice_corrections()
    all_corrections = stored_corrections + load_starter_voice_corrections()
    best_item = None
    best_score = 0.0

    for item in all_corrections:
        heard = item["heard_normalized"]
        if not heard:
            continue

        score = SequenceMatcher(None, normalized, heard).ratio()
        if normalized in heard or heard in normalized:
            score = max(score, 0.93)

        if score > best_score:
            best_score = score
            best_item = item

    if not best_item:
        return None

    threshold = 0.82 if len(normalized.split()) <= 4 else 0.76
    if best_score < threshold:
        return None

    if not best_item.get("starter"):
        best_item["uses"] = int(best_item.get("uses", 0) or 0) + 1
        for item in stored_corrections:
            if item["heard_normalized"] == best_item["heard_normalized"]:
                item["uses"] = best_item["uses"]
                break
        save_voice_corrections(stored_corrections)

    return best_item["means"]
