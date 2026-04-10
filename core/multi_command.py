def split_commands(text: str):
    separators = [" e depois ", " e ", ","]

    for sep in separators:
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            return parts

    return [text]