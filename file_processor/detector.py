from __future__ import annotations

import mimetypes
from pathlib import Path

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".json",
    ".csv",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".sql",
}


def detect_file(path: str) -> dict:
    file_path = Path(path).expanduser()
    suffix = file_path.suffix.lower()
    mime_type, _encoding = mimetypes.guess_type(str(file_path))
    kind = "unknown"
    if suffix in {".csv", ".tsv"}:
        kind = "table"
    elif suffix in {".json", ".xml", ".yaml", ".yml", ".toml", ".ini"}:
        kind = "structured_text"
    elif suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".sql"}:
        kind = "code"
    elif suffix in TEXT_EXTENSIONS or (mime_type or "").startswith("text/"):
        kind = "text"
    elif suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
        kind = "image"
    elif suffix in {".pdf"}:
        kind = "pdf"
    elif suffix in {".xlsx", ".xls"}:
        kind = "spreadsheet"
    elif suffix in {".docx", ".doc"}:
        kind = "document"

    return {
        "path": str(file_path),
        "name": file_path.name,
        "exists": file_path.exists(),
        "extension": suffix,
        "mime_type": mime_type or "",
        "kind": kind,
        "size_bytes": file_path.stat().st_size if file_path.exists() and file_path.is_file() else 0,
    }
