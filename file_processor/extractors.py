from __future__ import annotations

import csv
import json
import os
import re
import shutil
import shlex
import subprocess
import tempfile
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


def extract_pptx(path: str, max_chars: int = 4000) -> dict:
    file_path = Path(path)
    slides: list[dict] = []
    with ZipFile(file_path) as archive:
        slide_names = sorted(
            name
            for name in archive.namelist()
            if re.match(r"ppt/slides/slide\d+\.xml$", name)
        )
        for index, slide_name in enumerate(slide_names, start=1):
            root = _xml_text(archive.read(slide_name).decode("utf-8", errors="replace"))
            text = re.sub(r"\s+", " ", " ".join(_element_texts(root))).strip()
            slides.append({"index": index, "text": text})

    lines = [f"Slide {slide['index']}: {slide['text']}" for slide in slides if slide["text"]]
    text = "\n".join(lines)
    return {
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
        "slides": slides,
        "slide_count": len(slides),
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


def _compact_pdf_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\x00", "")).strip()


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


def _pdf_stream_chunks(data: bytes) -> list[bytes]:
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
    return chunks


def _decode_utf16_hex(hex_value: bytes) -> str:
    clean = re.sub(rb"\s+", b"", hex_value)
    try:
        raw = bytes.fromhex(clean.decode("ascii"))
    except Exception:
        return ""
    if len(raw) >= 2 and len(raw) % 2 == 0:
        text = raw.decode("utf-16-be", errors="ignore")
        if text:
            return text
    return raw.decode("latin-1", errors="ignore")


def _parse_pdf_cmaps(chunks: list[bytes]) -> dict[int, str]:
    cmap: dict[int, str] = {}
    for chunk in chunks:
        if b"beginbfchar" not in chunk and b"beginbfrange" not in chunk:
            continue
        text = chunk.decode("latin-1", errors="ignore")

        for section in re.findall(r"beginbfchar(.*?)endbfchar", text, flags=re.S):
            for source, target in re.findall(r"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>", section):
                try:
                    cmap[int(source, 16)] = _decode_utf16_hex(target.encode("ascii"))
                except Exception:
                    continue

        for section in re.findall(r"beginbfrange(.*?)endbfrange", text, flags=re.S):
            for start, end, target in re.findall(r"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>", section):
                try:
                    start_int = int(start, 16)
                    end_int = int(end, 16)
                    target_int = int(target, 16)
                except Exception:
                    continue
                for offset, code in enumerate(range(start_int, end_int + 1)):
                    try:
                        cmap[code] = chr(target_int + offset)
                    except Exception:
                        continue
    return {key: value for key, value in cmap.items() if value}


def _decode_pdf_literal_with_cmap(value: bytes, cmap: dict[int, str]) -> str:
    if not cmap:
        return _decode_pdf_literal(value)

    output: list[str] = []
    index = 0
    while index < len(value):
        byte = value[index]
        if byte == 0x5C and index + 1 < len(value):
            index += 1
            byte = value[index]
        output.append(cmap.get(byte, chr(byte)))
        index += 1
    return "".join(output)


def _extract_pdf_text_with_cmap(data: bytes) -> str:
    chunks = _pdf_stream_chunks(data)
    cmap = _parse_pdf_cmaps(chunks)
    if not cmap:
        return ""

    texts: list[str] = []
    for chunk in chunks:
        if b"beginbfchar" in chunk or b"beginbfrange" in chunk:
            continue
        texts.extend(_decode_pdf_literal_with_cmap(item, cmap) for item in re.findall(rb"\((?:\\.|[^\\)])*\)", chunk))
        for hex_text in re.findall(rb"<([0-9A-Fa-f\s]{4,})>", chunk):
            clean = re.sub(rb"\s+", b"", hex_text)
            try:
                raw = bytes.fromhex(clean.decode("ascii"))
            except Exception:
                continue
            texts.append("".join(cmap.get(byte, chr(byte)) for byte in raw))
    return re.sub(r"\s+", " ", " ".join(texts)).strip()


def _pdf_text_quality(text: str) -> float:
    text = str(text or "").replace("\x00", "")
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return 0.0
    letters = sum(1 for char in compact if char.isalpha())
    common = len(re.findall(r"\b(?:de|da|do|que|para|com|uma|teste|quest[aã]o|software)\b", text or "", flags=re.I))
    noise = sum(1 for char in compact if char in "♥�◄►♦♣♠")
    spaced_caps = len(re.findall(r"(?:\b[A-Z0-9]\s+){4,}", text or ""))
    tokens = re.findall(r"\b\w+\b", text or "")
    single_token_ratio = sum(1 for token in tokens if len(token) == 1) / max(1, len(tokens))
    substitution_penalty = _pdf_glyph_substitution_score(text) * 16
    penalty = (noise * 6) + (spaced_caps * 12) + int(single_token_ratio * 40) + substitution_penalty
    return (letters + (common * 14)) / max(1, len(compact) + penalty)


def _pdf_glyph_substitution_score(text: str) -> int:
    text = str(text or "").replace("\x00", "")
    normalized = re.sub(r"\s+", " ", text or "").lower()
    if not normalized:
        return 0

    suspicious_patterns = [
        r"\bqum\b",
        r"\blm\b",
        r"\bmu\b",
        r"\bxor\b",
        r"\bciqxi\b",
        r"\btmstm?s?\b",
        r"\bcisos\b",
        r"\bvitorms?\b",
        r"\bmquqvit",
        r"\blmcqs",
        r"\bcouxtmx",
        r"\bquivtos?\b",
        r"\btrivsn",
        r"\bqvv[aã]t",
    ]
    score = sum(len(re.findall(pattern, normalized, flags=re.I)) for pattern in suspicious_patterns)

    spaced_words = [
        r"\bt\s+m\s+s\s+t\s+m\s+s\b",
        r"\bq\s+u\s+i\s+t\s+q\s+l\s+i\s+l\s+m\b",
        r"\bs\s+o\s+n\s+t\s+w\s+i\s+r\s+m\b",
    ]
    score += sum(4 for pattern in spaced_words if re.search(pattern, normalized, flags=re.I))
    return score


def _pdf_text_is_garbled(text: str) -> bool:
    text = str(text or "").replace("\x00", "")
    if not text.strip():
        return False

    compact = re.sub(r"\s+", "", text or "")
    tokens = re.findall(r"\b\w+\b", text or "")
    single_token_ratio = sum(1 for token in tokens if len(token) == 1) / max(1, len(tokens))
    noise = sum(1 for char in compact if char in "♥�◄►♦♣♠")
    spaced_caps = len(re.findall(r"(?:\b[A-Z0-9]\s+){4,}", text or ""))
    common = len(re.findall(r"\b(?:de|da|do|que|para|com|uma|teste|quest[aã]o|software)\b", text or "", flags=re.I))
    substitution_score = _pdf_glyph_substitution_score(text)

    if noise >= 3:
        return True
    if spaced_caps >= 2 and single_token_ratio >= 0.28:
        return True
    if len(compact) > 120 and single_token_ratio >= 0.45 and common <= 1:
        return True
    if len(compact) > 180 and substitution_score >= 6 and common <= 4:
        return True
    if len(compact) > 600 and substitution_score >= 12:
        return True
    return False


def _render_pdf_pages_with_qt(path: Path, *, max_pages: int = 3, scale: float = 2.0) -> list[Path]:
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
        os.environ.setdefault("QT_SCALE_FACTOR", "1")

        from PySide6.QtCore import QSize, Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtPdf import QPdfDocument
    except Exception:
        return []

    try:
        QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_Use96Dpi, True)
    except Exception:
        pass

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    document = QPdfDocument()
    try:
        load_result = document.load(str(path))
        error_enum = getattr(QPdfDocument, "Error", None)
        no_error = None
        if error_enum is not None:
            no_error = getattr(error_enum, "None_", None)
            if no_error is None:
                no_error = getattr(error_enum, "NoError", None)
        if no_error is not None and load_result != no_error:
            return []

        page_count = max(0, int(document.pageCount()))
        ready = getattr(QPdfDocument.Status, "Ready", None)
        current_status = document.status() if callable(getattr(document, "status", None)) else None
        if page_count <= 0 and ready is not None and current_status is not None and current_status != ready:
            return []
        image_paths: list[Path] = []
        temp_dir = Path(tempfile.mkdtemp(prefix="axel_pdf_ocr_"))

        for page_index in range(min(max_pages, page_count)):
            page_size = document.pagePointSize(page_index)
            width = max(1, int(page_size.width() * scale))
            height = max(1, int(page_size.height() * scale))
            image = document.render(page_index, QSize(width, height))
            if image.isNull():
                continue
            image_path = temp_dir / f"page_{page_index + 1}.png"
            if image.save(str(image_path)):
                image_paths.append(image_path)
        return image_paths
    except Exception:
        return []
    finally:
        try:
            document.close()
        except Exception:
            pass


def _rapidocr_image_text(path: Path) -> str:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return ""

    try:
        ocr = RapidOCR()
        result, _elapsed = ocr(str(path))
    except Exception:
        return ""

    lines: list[str] = []
    for item in result or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        text = re.sub(r"\s+", " ", str(item[1] or "")).strip()
        confidence = 0.0
        if len(item) >= 3:
            try:
                confidence = float(item[2])
            except Exception:
                confidence = 0.0
        if text and confidence >= 0.38:
            lines.append(text)
    return "\n".join(lines)


def _extract_pdf_text_ocr(
    path: Path,
    *,
    max_chars: int = 4000,
    max_pages: int = 3,
    render_pages=_render_pdf_pages_with_qt,
    ocr_image=_rapidocr_image_text,
) -> dict:
    image_paths = render_pages(path, max_pages=max_pages)
    if not image_paths:
        return {"text": "", "pages": 0, "note": "OCR indisponivel: nao consegui renderizar as paginas do PDF."}

    lines: list[str] = []
    try:
        for image_path in image_paths:
            page_text = ocr_image(image_path)
            if page_text:
                lines.append(page_text)
    finally:
        for directory in {image_path.parent for image_path in image_paths}:
            try:
                shutil.rmtree(directory, ignore_errors=True)
            except Exception:
                pass

    text = "\n".join(lines).strip()
    return {
        "text": text[:max_chars],
        "pages": len(image_paths),
        "truncated": len(text) > max_chars,
        "note": "" if text else "OCR nao encontrou texto legivel nas paginas renderizadas.",
    }


def _extract_pdf_text_with_external_ocr(path: Path, *, max_chars: int = 4000) -> dict:
    try:
        from config import env_str
    except Exception:
        return {"text": "", "provider": "", "note": ""}

    command = env_str(
        "AXEL_PDF_OCR_COMMAND",
        default="",
        aliases=("AXEL_CLAWHUB_PDF_OCR_COMMAND",),
    )
    if not command:
        return {"text": "", "provider": "", "note": ""}

    try:
        args = shlex.split(command, posix=False)
        if any("{path}" in arg for arg in args):
            args = [arg.strip('"').replace("{path}", str(path)) for arg in args]
        else:
            args.append(str(path))
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except Exception as exc:
        return {"text": "", "provider": "external_ocr", "note": f"OCR externo falhou ao iniciar: {exc}"}

    output = _compact_pdf_text(completed.stdout)
    if completed.returncode != 0 and not output:
        error = _compact_pdf_text(completed.stderr)
        return {
            "text": "",
            "provider": "external_ocr",
            "note": f"OCR externo retornou erro: {error[:240] or completed.returncode}",
        }
    return {
        "text": output[:max_chars],
        "provider": "external_ocr",
        "truncated": len(output) > max_chars,
        "note": "" if output else "OCR externo nao retornou texto.",
    }


def extract_pdf(path: str, max_chars: int = 4000) -> dict:
    file_path = Path(path)
    text = ""
    pages: list[dict] = []
    engine = "basic"
    ocr = {"text": "", "pages": 0, "note": ""}
    external_ocr = {"text": "", "provider": "", "note": ""}
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(file_path))
        page_texts = [page.extract_text() or "" for page in reader.pages]
        pages = [
            {"index": index, "text": page_text[:max_chars]}
            for index, page_text in enumerate(page_texts, start=1)
            if page_text.strip()
        ]
        text = "\n".join(page_texts)
        engine = "pypdf"
    except Exception:
        data = file_path.read_bytes()
        mapped_text = _extract_pdf_text_with_cmap(data)
        basic_text = _extract_pdf_text_basic(data)
        if _pdf_text_quality(mapped_text) >= _pdf_text_quality(basic_text):
            text = mapped_text
            engine = "basic_cmap" if mapped_text else "basic"
        else:
            text = basic_text

    quality = _pdf_text_quality(text)
    note = "" if text else "Nao consegui extrair texto pesquisavel deste PDF."
    if text and (quality < 0.18 or _pdf_text_is_garbled(text)):
        note = "O texto extraido parece ilegivel por causa da codificacao interna do PDF; use OCR ou converta o arquivo para texto pesquisavel."
        text = ""

    if not text:
        external_ocr = _extract_pdf_text_with_external_ocr(file_path, max_chars=max_chars)
        external_text = str(external_ocr.get("text") or "")
        if external_text and not _pdf_text_is_garbled(external_text):
            text = external_text
            engine = f"{engine}+external_ocr"
            note = "Texto extraido por OCR externo configurado."
            quality = _pdf_text_quality(text)

    if not text:
        ocr = _extract_pdf_text_ocr(file_path, max_chars=max_chars)
        ocr_text = str(ocr.get("text") or "")
        if ocr_text and not _pdf_text_is_garbled(ocr_text):
            text = ocr_text
            engine = f"{engine}+ocr"
            note = "Texto extraido por OCR porque a extracao textual do PDF falhou ou veio ilegivel."
            quality = _pdf_text_quality(text)
        elif ocr.get("note"):
            note = note + " " + str(ocr.get("note"))
        elif external_ocr.get("note"):
            note = note + " " + str(external_ocr.get("note"))

    return {
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
        "chars": len(text),
        "engine": engine,
        "quality": round(quality, 3),
        "note": note,
        "pages": pages[:20],
        "page_count": len(pages),
        "ocr_pages": int(ocr.get("pages") or 0),
        "external_ocr": str(external_ocr.get("provider") or ""),
    }
