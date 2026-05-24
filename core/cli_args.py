from __future__ import annotations

from collections.abc import Sequence


def cli_value_after(argv: Sequence[str], flag: str) -> str | None:
    if flag not in argv:
        return None

    index = argv.index(flag)
    if index + 1 >= len(argv):
        return None

    value = argv[index + 1].strip()
    if not value or value.startswith("--"):
        return None

    return value


def cli_text_after(argv: Sequence[str], flag: str) -> str | None:
    if flag not in argv:
        return None

    index = argv.index(flag)
    parts = []
    for part in argv[index + 1:]:
        if part.startswith("--"):
            break
        parts.append(part)

    text = " ".join(parts).strip()
    return text or None
