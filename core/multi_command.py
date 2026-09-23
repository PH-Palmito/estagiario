import re


def split_commands(text: str):
    raw_parts = [part.strip() for part in re.split(r"\s*,\s*|\s+e\s+depois\s+|\s+e\s+", text) if part.strip()]
    parts = [re.sub(r"^(?:depois|ai|aí)\s+", "", part, flags=re.IGNORECASE).strip() for part in raw_parts]
    return [part for part in parts if part]
