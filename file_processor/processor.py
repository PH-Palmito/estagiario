from __future__ import annotations

from pathlib import Path

from file_processor.detector import detect_file
from file_processor.extractors import extract_docx, extract_json, extract_pdf, extract_pptx, extract_table, extract_text, extract_xlsx


def process_file(path: str, max_chars: int = 4000) -> dict:
    info = detect_file(path)
    if not info["exists"]:
        return {"ok": False, "error": "Arquivo nao encontrado.", "file": info}

    file_path = Path(info["path"])
    if not file_path.is_file():
        return {"ok": False, "error": "O caminho nao e um arquivo.", "file": info}

    kind = info["kind"]
    try:
        if kind == "table":
            extracted = extract_table(info["path"])
        elif info["extension"] == ".json":
            extracted = extract_json(info["path"], max_chars=max_chars)
        elif kind == "pdf":
            extracted = extract_pdf(info["path"], max_chars=max_chars)
        elif info["extension"] == ".docx":
            extracted = extract_docx(info["path"], max_chars=max_chars)
        elif info["extension"] == ".pptx":
            extracted = extract_pptx(info["path"], max_chars=max_chars)
        elif info["extension"] == ".xlsx":
            extracted = extract_xlsx(info["path"])
        elif kind in {"text", "code", "structured_text"}:
            extracted = extract_text(info["path"], max_chars=max_chars)
        else:
            extracted = {
                "text": "",
                "note": "Tipo detectado, mas extracao direta ainda nao implementada.",
            }
    except Exception as exc:
        return {"ok": False, "error": f"Erro ao processar arquivo: {exc}", "file": info}

    return {"ok": True, "file": info, "extracted": extracted}
