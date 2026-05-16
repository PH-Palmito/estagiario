from __future__ import annotations

import csv
import json
import re
import zlib
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


def extract_text(path: str, max_chars: int = 4000) -> dict:
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8", errors="replace")
    truncated = len(content) > max_chars
    return {
        "text": content[:max_chars],
        "truncated": truncated,
        "chars": len(content),
    }


def extract_json(path: str, max_chars: int = 4000) -> dict:
    file_path = Path(path)
    data = json.loads(file_path.read_text(encoding="utf-8"))
    preview = json.dumps(data, ensure_ascii=False, indent=2)
    return {
        "text": preview[:max_chars],
        "truncated": len(preview) > max_chars,
        "top_level_type": type(data).__name__,
        "keys": list(data.keys())[:20] if isinstance(data, dict) else [],
    }


def extract_table(path: str, max_rows: int = 20) -> dict:
    file_path = Path(path)
    delimiter = "\t" if file_path.suffix.lower() == ".tsv" else ","
    rows = []
    with file_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row in reader:
            rows.append(row)
            if len(rows) >= max_rows:
                break
    header = rows[0] if rows else []
    return {
        "rows": rows,
        "header": header,
        "preview_rows": max(0, len(rows) - 1),
        "truncated": len(rows) >= max_rows,
    }


def _xml_text(xml: str) -> ElementTree.Element:
    return ElementTree.fromstring(xml.encode("utf-8"))


def _element_texts(root: ElementTree.Element, tag_suffix: str = "t") -> list[str]:
    texts: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == tag_suffix and element.text:
            texts.append(element.text)
    return texts


def extract_docx(path: str, max_chars: int = 4000) -> dict:
    file_path = Path(path)
    paragraphs: list[str] = []
    with ZipFile(file_path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
        root = _xml_text(document_xml)
        for paragraph in root.iter():
            if paragraph.tag.rsplit("}", 1)[-1] != "p":
                continue
            parts = _element_texts(paragraph)
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)

    text = "\n".join(paragraphs)
    return {
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
        "paragraphs": len(paragraphs),
    }


def _xlsx_shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = _xml_text(archive.read("xl/sharedStrings.xml").decode("utf-8", errors="replace"))
    except Exception:
        return []
    strings: list[str] = []
    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1] != "si":
            continue
        strings.append("".join(_element_texts(item)))
    return strings


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(_element_texts(cell)).strip()

    value = ""
    for child in cell:
        if child.tag.rsplit("}", 1)[-1] == "v" and child.text is not None:
            value = child.text
            break

    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except Exception:
            return value
    return value


def extract_xlsx(path: str, max_rows: int = 20, max_sheets: int = 5) -> dict:
    file_path = Path(path)
    sheets: list[dict] = []
    with ZipFile(file_path) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        worksheet_names = sorted(
            name
            for name in archive.namelist()
            if re.match(r"xl/worksheets/sheet\d+\.xml$", name)
        )
        for sheet_name in worksheet_names[:max_sheets]:
            root = _xml_text(archive.read(sheet_name).decode("utf-8", errors="replace"))
            rows: list[list[str]] = []
            for row in root.iter():
                if row.tag.rsplit("}", 1)[-1] != "row":
                    continue
                values = [
                    _xlsx_cell_value(cell, shared_strings)
                    for cell in row
                    if cell.tag.rsplit("}", 1)[-1] == "c"
                ]
                rows.append(values)
                if len(rows) >= max_rows:
                    break
            sheets.append(
                {
                    "name": sheet_name.rsplit("/", 1)[-1].replace(".xml", ""),
                    "rows": rows,
                    "header": rows[0] if rows else [],
                    "truncated": len(rows) >= max_rows,
                }
            )

    preview_lines = []
    for sheet in sheets:
        preview_lines.append(f"[{sheet['name']}]")
        preview_lines.extend(" | ".join(row) for row in sheet["rows"][:max_rows])
    text = "\n".join(preview_lines)
    return {
        "text": text[:4000],
        "sheets": sheets,
        "sheet_count": len(sheets),
        "truncated": len(text) > 4000 or any(sheet["truncated"] for sheet in sheets),
    }


def _decode_pdf_literal(value: bytes) -> str:
    value = value.replace(rb"\\(", b"\x00").replace(rb"\\)", b"\x01").replace(rb"\\\\", b"\\")
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        text = value.decode("latin-1", errors="replace")
    return text.replace("\x00", "(").replace("\x01", ")")


def _extract_pdf_text_basic(data: bytes) -> str:
    chunks: list[bytes] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, flags=re.S):
        raw = match.group(1).strip(b"\r\n")
        header = data[max(0, match.start() - 250):match.start()]
        if b"FlateDecode" in header:
            try:
                raw = zlib.decompress(raw)
            except Exception:
                continue
        chunks.append(raw)

    if not chunks:
        chunks = [data]

    texts: list[str] = []
    for chunk in chunks:
        texts.extend(_decode_pdf_literal(item) for item in re.findall(rb"\((?:\\.|[^\\)])*\)", chunk))
        for hex_text in re.findall(rb"<([0-9A-Fa-f\s]{4,})>", chunk):
            clean = re.sub(rb"\s+", b"", hex_text)
            try:
                texts.append(bytes.fromhex(clean.decode("ascii")).decode("utf-16-be", errors="ignore"))
            except Exception:
                pass
    return re.sub(r"\s+", " ", " ".join(texts)).strip()


def extract_pdf(path: str, max_chars: int = 4000) -> dict:
    file_path = Path(path)
    text = ""
    engine = "basic"
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(file_path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        engine = "pypdf"
    except Exception:
        text = _extract_pdf_text_basic(file_path.read_bytes())

    return {
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
        "chars": len(text),
        "engine": engine,
        "note": "" if text else "Nao consegui extrair texto pesquisavel deste PDF.",
    }
