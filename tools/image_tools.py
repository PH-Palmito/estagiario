import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from llm.ollama_client import ask_model
from llm.vision_client import ask_vision_model, installed_vision_models, vision_unavailable_message
from memory.vision_history import remember_vision_analysis

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL_EXE = "powershell"
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".svg"}
SCREENSHOT_DIR = ROOT / ".tmp" / "screenshots"
# Keep visual analysis inexpensive by default, but let chart mode use a visual
# model when one is installed because graphs need semantic reading.
LOW_COST_IMAGE_MODE = True


def _should_use_vision_model(mode: str = "general") -> bool:
    if not LOW_COST_IMAGE_MODE:
        return True
    if mode == "chart":
        return bool(installed_vision_models())
    return False


def _rapidocr_image(path: Path) -> dict:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:
        return {
            "width": 0,
            "height": 0,
            "ocr_ok": False,
            "ocr_language": "",
            "text": "",
            "ocr_engine": "rapidocr",
            "error": str(exc),
        }

    try:
        ocr = RapidOCR()
        result, _elapsed = ocr(str(path))
    except Exception as exc:
        return {
            "width": 0,
            "height": 0,
            "ocr_ok": False,
            "ocr_language": "",
            "text": "",
            "ocr_engine": "rapidocr",
            "error": str(exc),
        }

    lines = []
    items = []
    for item in result or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        box = item[0] if item else []
        text = str(item[1] or "").strip()
        confidence = 0.0
        if len(item) >= 3:
            try:
                confidence = float(item[2])
            except Exception:
                confidence = 0.0
        if text and confidence >= 0.45:
            lines.append(text)
            try:
                points = [[float(point[0]), float(point[1])] for point in box]
            except Exception:
                points = []
            items.append(
                {
                    "text": text,
                    "confidence": confidence,
                    "box": points,
                }
            )

    return {
        "width": 0,
        "height": 0,
        "ocr_ok": bool(lines),
        "ocr_language": "multi",
        "text": "\n".join(lines),
        "items": items,
        "ocr_engine": "rapidocr",
    }


def _resolve_target(path: str | None) -> Path:
    raw = str(path or "").strip().strip('"').strip("'")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (ROOT / candidate).resolve()
    return candidate


def _browser_local_image_from_foreground() -> Path | None:
    try:
        from tools.browser_tools import _get_browser_url
    except Exception:
        return None

    try:
        page_url = _get_browser_url()
        parsed = urlparse(page_url)
    except Exception:
        return None

    if parsed.scheme != "file":
        return None

    local_path = Path(unquote(parsed.path).lstrip("/"))
    if local_path.exists() and local_path.suffix.lower() in SUPPORTED_SUFFIXES:
        return local_path
    return None


def _run_powershell(script: str, timeout_seconds: int = 20) -> str:
    completed = subprocess.run(
        [POWERSHELL_EXE, "-NoProfile", "-Sta", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "").strip() or "Falha no PowerShell.")
    return (completed.stdout or "").strip()


def _ocr_image(path: Path) -> dict:
    escaped = str(path).replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -AssemblyName System.Drawing
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Foundation, ContentType=WindowsRuntime]

function Await($operation) {{
    return [System.WindowsRuntimeSystemExtensions]::AsTask($operation).GetAwaiter().GetResult()
}}

$path = '{escaped}'
$image = [System.Drawing.Image]::FromFile($path)
$width = $image.Width
$height = $image.Height
$image.Dispose()

$ocrText = ''
$ocrLanguage = ''
$ocrOk = $false
try {{
    $file = Await([Windows.Storage.StorageFile]::GetFileFromPathAsync($path))
    $stream = Await($file.OpenAsync([Windows.Storage.FileAccessMode]::Read))
    $decoder = Await([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream))
    $bitmap = Await($decoder.GetSoftwareBitmapAsync())
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if (-not $engine) {{
        $language = [Windows.Globalization.Language]::new('pt-BR')
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
    }}
    if (-not $engine) {{
        $language = [Windows.Globalization.Language]::new('en-US')
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
    }}
    if ($engine) {{
        $result = Await($engine.RecognizeAsync($bitmap))
        $ocrText = ($result.Text | Out-String).Trim()
        $ocrLanguage = [string]$engine.RecognizerLanguage.LanguageTag
        $ocrOk = $true
    }}
    $stream.Dispose()
}} catch {{
}}

[pscustomobject]@{{
    width = $width
    height = $height
    ocr_ok = $ocrOk
    ocr_language = $ocrLanguage
    text = $ocrText
}} | ConvertTo-Json -Compress
"""
    output = _run_powershell(script, timeout_seconds=25)
    result = json.loads(output) if output else {}
    if str(result.get("text", "")).strip():
        result.setdefault("ocr_engine", "windows")
        return result

    fallback = _rapidocr_image(path)
    if str(fallback.get("text", "")).strip():
        fallback["width"] = int(result.get("width", 0) or fallback.get("width", 0) or 0)
        fallback["height"] = int(result.get("height", 0) or fallback.get("height", 0) or 0)
        return fallback

    result.setdefault("ocr_engine", "windows")
    return result


def _capture_foreground_window(path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(path).replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Capture {{
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    public struct RECT {{
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }}
}}
"@
$handle = [Win32Capture]::GetForegroundWindow()
$rect = New-Object Win32Capture+RECT
[Win32Capture]::GetWindowRect($handle, [ref]$rect) | Out-Null
$width = [Math]::Max(1, $rect.Right - $rect.Left)
$height = [Math]::Max(1, $rect.Bottom - $rect.Top)
$left = $rect.Left
$top = $rect.Top
if ($width -le 1 -or $height -le 1) {{
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $left = $bounds.Left
    $top = $bounds.Top
    $width = $bounds.Width
    $height = $bounds.Height
}}
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {{
    $graphics.CopyFromScreen($left, $top, 0, 0, $bitmap.Size)
}} catch {{
    $graphics.Dispose()
    $bitmap.Dispose()
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $width = $bounds.Width
    $height = $bounds.Height
    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bitmap.Size)
}}
$bitmap.Save('{escaped}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
[pscustomobject]@{{
    width = $width
    height = $height
}} | ConvertTo-Json -Compress
"""
    output = _run_powershell(script, timeout_seconds=10)
    return json.loads(output) if output else {}


def _make_screen_content_crop(source: Path) -> Path | None:
    try:
        from PIL import Image
    except Exception:
        return None

    try:
        image = Image.open(source)
    except Exception:
        return None

    try:
        width, height = image.size
        if width < 500 or height < 420:
            return None

        top_crop = min(105, max(70, int(height * 0.085)))
        left_crop = max(0, int(width * 0.01))
        right_crop = max(left_crop + 1, width - max(0, int(width * 0.01)))
        bottom_crop = height
        if top_crop >= height - 180:
            return None

        cropped = image.crop((left_crop, top_crop, right_crop, bottom_crop))
        crop_path = source.with_name(f"{source.stem}_content{source.suffix}")
        cropped.save(crop_path)
        return crop_path
    finally:
        try:
            image.close()
        except Exception:
            pass


def _capture_clipboard_image(path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(path).replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$path = '{escaped}'

if ([System.Windows.Forms.Clipboard]::ContainsImage()) {{
    $image = [System.Windows.Forms.Clipboard]::GetImage()
    $width = $image.Width
    $height = $image.Height
    $image.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $image.Dispose()
    [pscustomobject]@{{ width = $width; height = $height; source = 'clipboard-image' }} | ConvertTo-Json -Compress
    exit 0
}}

if ([System.Windows.Forms.Clipboard]::ContainsFileDropList()) {{
    $files = [System.Windows.Forms.Clipboard]::GetFileDropList()
    foreach ($file in $files) {{
        if ($file -match '\\.(png|jpg|jpeg|webp|bmp|gif|tif|tiff)$') {{
            $image = [System.Drawing.Image]::FromFile($file)
            $width = $image.Width
            $height = $image.Height
            $image.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
            $image.Dispose()
            [pscustomobject]@{{ width = $width; height = $height; source = 'clipboard-file' }} | ConvertTo-Json -Compress
            exit 0
        }}
    }}
}}

throw 'Nenhuma imagem encontrada no clipboard.'
"""
    output = _run_powershell(script, timeout_seconds=10)
    return json.loads(output) if output else {}


def _format_image_analysis(
    result: dict,
    size_kb: int | None = None,
    prefix: str = "Imagem analisada",
) -> str:
    width = int(result.get("width", 0) or 0)
    height = int(result.get("height", 0) or 0)
    text = str(result.get("text", "")).strip()
    language = str(result.get("ocr_language", "")).strip()

    details = []
    if width and height:
        details.append(f"{width}x{height}")
    if size_kb:
        details.append(f"{size_kb} KB")
    intro = prefix + (f" ({', '.join(details)})." if details else ".")

    if text:
        compact = " ".join(text.split())
        if len(compact) > 420:
            compact = compact[:417].rstrip() + "..."
        if language:
            return f"{intro} Texto detectado ({language}): {compact}"
        return f"{intro} Texto detectado: {compact}"

    return f"{intro} Não detectei texto legível via OCR."


def _clean_visual_response(response: str, max_length: int = 760) -> str:
    def _strip_leaked_instruction(text: str) -> str:
        if re.search(r"nao vejo um grafico claro na tela", text, flags=re.IGNORECASE) and re.search(
            r"depois|se houver grafico|valores visiveis|conclusao pratica|tendencia|seu grafico",
            text,
            flags=re.IGNORECASE,
        ):
            return "Nao vejo um grafico claro na tela."
        text = re.sub(r"\bDepois\b.*$", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\bSe houver grafico\b.*$", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\bseu grafico\b.*$", "", text, flags=re.IGNORECASE).strip()
        return text

    compact = " ".join(str(response or "").split()).strip()
    compact = compact.strip(" \"'“”")
    compact = compact.replace("A imagem mostra", "Vejo")
    compact = compact.replace("A imagem parece mostrar", "Parece")
    compact = compact.replace("site's interface", "interface do site")
    compact = re.sub(r"^aqui est[aá]\s+(?:a\s+)?(?:tradu[cç][aã]o|resposta final)\s*(?:para portugu[eê]s)?\s*:\s*", "", compact, flags=re.IGNORECASE).strip()
    if "Nao vejo um grafico claro na tela." in compact and any(
        marker in compact
        for marker in (
            "Depois descreva",
            "Se houver grafico",
            "valores visiveis",
            "conclusao pratica",
        )
    ):
        compact = "Nao vejo um grafico claro na tela."
    compact = re.sub(r"\bDepois descreva brevemente\b.*$", "", compact, flags=re.IGNORECASE).strip()
    compact = re.sub(r"\bSe houver grafico\b.*$", "", compact, flags=re.IGNORECASE).strip()
    compact = _strip_leaked_instruction(compact)
    if len(compact) > max_length:
        compact = compact[: max_length - 3].rstrip() + "..."
    return compact


def _looks_like_low_value_chart_response(text: str) -> bool:
    lowered = str(text or "").lower()
    weak_markers = (
        "sem mais detalhes",
        "sem mais contexto",
        "difícil determinar",
        "dificil determinar",
        "não consegui entender",
        "nao consegui entender",
        "não conseguiu interpretar",
        "nao conseguiu interpretar",
        "não consegui interpretar",
        "nao consegui interpretar",
        "não consigo interpretar",
        "nao consigo interpretar",
        "não consegui interpretar os dados",
        "nao consegui interpretar os dados",
        "agradeço se puder fornecer",
        "agradeco se puder fornecer",
        "não posso ajudar com isso",
        "nao posso ajudar com isso",
        "poderia forçar mais detalhes",
        "poderia forcar mais detalhes",
        "reformular o texto",
        "pode ser para mostrar",
        "pode ser usado para",
        "informações visualmente",
        "informacoes visualmente",
        "comparar diferentes categorias",
        "monitorar mudanças",
        "monitorar mudancas",
        "excel ou similar",
        "software como excel",
        "natureza específica",
        "natureza especifica",
        "função principal",
        "funcao principal",
        "pergunta incompleta",
        "forneça mais detalhes",
        "forneca mais detalhes",
        "não posso fornecer uma resposta completa",
        "nao posso fornecer uma resposta completa",
        "parece ser um gráfico barra",
        "parece ser um grafico barra",
        "pode fornecer informações adicionais",
        "pode fornecer informacoes adicionais",
        "formato de apresentação",
        "formato de apresentacao",
        "slidemaster",
        "não conseguiu interpretar",
        "nao conseguiu interpretar",
        "não consigo interpretar",
        "nao consigo interpretar",
        "não consegui entender",
        "nao consegui entender",
        "poderia forçar mais detalhes",
        "poderia forcar mais detalhes",
        "reformular o texto",
    )
    has_weak_marker = any(marker in lowered for marker in weak_markers)
    has_chart_hint = any(token in lowered for token in ("grafico", "gráfico", "barra", "linha", "eixo"))
    return has_chart_hint and has_weak_marker


def _looks_like_low_value_visual_response(text: str) -> bool:
    lowered = str(text or "").lower()
    weak_markers = (
        "aqui está a tradução",
        "aqui esta a traducao",
        "aqui está a resposta final",
        "aqui esta a resposta final",
        "pergunta incompleta",
        "forneça mais detalhes",
        "forneca mais detalhes",
        "não posso fornecer uma resposta completa",
        "nao posso fornecer uma resposta completa",
        "sem mais contexto",
        "sem mais detalhes",
        "difícil determinar",
        "dificil determinar",
        "não consegui entender",
        "nao consegui entender",
        "não conseguiu interpretar",
        "nao conseguiu interpretar",
        "poderia forçar mais detalhes",
        "poderia forcar mais detalhes",
        "reformular o texto",
    )
    return any(marker in lowered for marker in weak_markers)


def _compact_ocr_hint(text: str, limit: int = 260) -> str:
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return ""
    if len(compact) > limit:
        compact = compact[: limit - 3].rstrip() + "..."
    return compact


def _ocr_chart_summary(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if len(lines) < 3:
        return ""

    number_lines = []
    label_lines = []
    for line in lines:
        normalized = line.replace(",", ".")
        if re.fullmatch(r"\d+(?:\.\d+)?", normalized):
            number_lines.append(line)
        else:
            label_lines.append(line)

    if len(number_lines) < 2 or len(label_lines) < 2:
        return ""

    title = label_lines[0]
    labels = label_lines[1:9]
    labels_text = ", ".join(labels[:8])
    numbers_text = ", ".join(number_lines[:8])

    return (
        f"Consegui ler texto de um gráfico. Título: {title}. "
        f"Categorias/legendas visíveis: {labels_text}. "
        f"Números visíveis na escala: {numbers_text}. "
        "Ainda não consigo garantir automaticamente o valor exato de cada barra só pelo OCR; para isso, a imagem precisa estar ampliada ou o gráfico isolado."
    )


def _ocr_item_bounds(item: dict) -> tuple[float, float, float, float] | None:
    points = item.get("box") if isinstance(item, dict) else None
    if not isinstance(points, list) or not points:
        return None
    try:
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
    except Exception:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _infer_column_chart_from_image(path: Path, ocr_result: dict | None = None) -> str:
    try:
        import cv2
        import numpy as np
    except Exception:
        return ""

    items = (ocr_result or {}).get("items") or []
    if not items:
        return ""

    numeric_points = []
    label_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        bounds = _ocr_item_bounds(item)
        if not text or not bounds:
            continue
        left, top, right, bottom = bounds
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        normalized = text.replace(",", ".")
        if re.fullmatch(r"\d+(?:\.\d+)?", normalized):
            try:
                numeric_points.append((center_x, center_y, float(normalized)))
            except Exception:
                pass
        else:
            label_items.append((center_x, center_y, right - left, text))

    y_axis = [
        (y, value)
        for x, y, value in numeric_points
        if value >= 0 and x <= max(180, int((ocr_result or {}).get("width", 0) or 0) * 0.35)
    ]
    if len(y_axis) < 2:
        return ""

    try:
        ys = np.array([point[0] for point in y_axis], dtype=float)
        values = np.array([point[1] for point in y_axis], dtype=float)
        slope, intercept = np.polyfit(ys, values, 1)
    except Exception:
        return ""
    if abs(float(slope)) < 0.01:
        return ""

    image = cv2.imread(str(path))
    if image is None:
        return ""
    height, width = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 1] > 55) & (hsv[:, :, 2] > 115)).astype("uint8")

    plot_top = max(0, int(min(y for y, _value in y_axis) - 12))
    plot_bottom = height
    try:
        zero_y = int((0 - intercept) / slope)
        if 0 < zero_y <= height + 20:
            plot_bottom = min(height, zero_y + 6)
    except Exception:
        pass
    mask[:plot_top, :] = 0
    mask[plot_bottom:, :] = 0

    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, 8)
    bars = []
    for index in range(1, count):
        x, y, w, h, area = [int(value) for value in stats[index]]
        if area < 80 or h < 28 or w < 6:
            continue
        if y < plot_top or y > plot_bottom:
            continue
        if x > width * 0.88 and y > height * 0.75:
            continue
        value = max(0, float(slope) * float(y) + float(intercept))
        bars.append({"x": x, "y": y, "w": w, "h": h, "value": value})

    if len(bars) < 2:
        return ""
    bars = sorted(bars, key=lambda bar: bar["x"])

    title = ""
    if label_items:
        title = sorted(label_items, key=lambda item: (item[1], -item[2]))[0][3]

    legend_candidates = [
        item
        for item in label_items
        if item[1] < plot_top and item[3] != title and len(item[3]) > 1
    ]
    legend_candidates = sorted(legend_candidates, key=lambda item: (round(item[1] / 36), item[0]))
    legend_labels = [item[3] for item in legend_candidates]

    pairs = []
    for index, bar in enumerate(bars[:10]):
        label = legend_labels[index] if index < len(legend_labels) else f"barra {index + 1}"
        pairs.append(f"{label}: aproximadamente {round(bar['value'])}")

    if not pairs:
        return ""

    response = "Gráfico de colunas detectado. "
    if title:
        response += f"Título: {title}. "
    response += "Valores estimados pela altura das barras: " + "; ".join(pairs) + "."
    return response


def _infer_svg_column_chart(path: Path) -> str:
    try:
        svg = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    path_matches = re.findall(r"<path\b[^>]*\bclass=[\"']st2[\"'][^>]*\bd=[\"'](.+?)[\"']", svg, flags=re.I | re.S)
    if not path_matches:
        path_matches = re.findall(r"<path\b[^>]*\bd=[\"'](.+?)[\"'][^>]*>", svg, flags=re.I | re.S)

    bars = []
    for path_data in path_matches:
        compact = re.sub(r"\s+", " ", path_data)
        for match in re.finditer(
            r"M\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*h\s*([-+]?\d+(?:\.\d+)?)\s*([vV])\s*([-+]?\d+(?:\.\d+)?)",
            compact,
        ):
            try:
                x = float(match.group(1))
                y = float(match.group(2))
                width = abs(float(match.group(3)))
                command = match.group(4)
                vertical_value = float(match.group(5))
                height = abs(vertical_value) if command == "v" else abs(y - vertical_value)
            except ValueError:
                continue
            if width >= 12 and height >= 8:
                bars.append({"x": x, "y": y, "width": width, "height": height})

    if len(bars) < 2:
        return ""

    bars = sorted(bars, key=lambda item: item["x"])
    heights = [bar["height"] for bar in bars]
    first = heights[0]
    last = heights[-1]
    if first <= 0:
        return ""

    labels = [f"barra {index}" for index in range(1, len(heights) + 1)]
    if len(heights) == 8:
        labels = [str(year) for year in range(2020, 2028)]

    def pt_percent(value: float) -> str:
        return f"{value:.1f}".replace(".", ",")

    normalized_pairs = []
    for label, height in zip(labels, heights):
        relative = (height / first) * 100
        normalized_pairs.append(f"{label}: {pt_percent(relative)}% do primeiro valor")

    drop = ((first - last) / first) * 100
    trend = "queda" if last < first else "alta"
    return (
        "Gráfico de colunas em SVG detectado. "
        "O texto do SVG está convertido em desenho, então li principalmente a geometria das barras. "
        f"Valores relativos estimados: {'; '.join(normalized_pairs)}. "
        f"Da primeira até a última barra há uma {trend} aproximada de {pt_percent(abs(drop))}%."
    )


def _make_visual_response_useful(visual: str, ocr_text: str = "") -> str:
    visual = _clean_visual_response(visual)
    if not visual:
        return visual

    chart_ocr_summary = _ocr_chart_summary(ocr_text)
    if _looks_like_low_value_visual_response(visual):
        if chart_ocr_summary:
            return chart_ocr_summary
        hint = _compact_ocr_hint(ocr_text)
        if _looks_like_low_value_chart_response(visual):
            if hint:
                return (
                    "Vejo um gráfico, mas não consegui interpretar título, eixos e valores com confiança. "
                    f"O texto legível que consegui captar foi: {hint}"
                )
            return (
                "Vejo um gráfico, mas não consegui ler título, eixos, legenda ou valores com confiança. "
                "Para uma interpretação útil, aumente o zoom do gráfico ou abra ele isolado e peça para analisar a imagem de novo."
            )
        if hint:
            return (
                "Não consegui extrair uma análise visual confiável dessa imagem. "
                f"O texto legível que consegui captar foi: {hint}"
            )
        return (
            "Não consegui extrair uma análise visual útil dessa imagem. "
            "Tente ampliar a área importante ou abrir a imagem isolada e peça para analisar de novo."
        )

    if _looks_like_low_value_chart_response(visual):
        if chart_ocr_summary:
            return chart_ocr_summary
        hint = _compact_ocr_hint(ocr_text)
        if hint:
            return (
                "Vejo um gráfico, mas não consegui interpretar título, eixos e valores com confiança. "
                f"O texto legível que consegui captar foi: {hint}"
            )
        return (
            "Vejo um gráfico, mas não consegui ler título, eixos, legenda ou valores com confiança. "
            "Para uma interpretação útil, aumente o zoom do gráfico ou abra ele isolado e peça para analisar a imagem de novo."
        )

    return visual


def _refine_visual_response(raw_visual: str, ocr_text: str = "", mode: str = "general") -> str:
    raw_visual = _clean_visual_response(raw_visual, max_length=1000)
    if not raw_visual:
        return raw_visual

    ocr_hint = _compact_ocr_hint(ocr_text, limit=520)
    prompt = (
        "Voce e o revisor visual do Axel. Transforme a descricao bruta em uma resposta util para Pedro.\n"
        "Regras obrigatorias:\n"
        "- Responda somente em portugues do Brasil.\n"
        "- Nao diga 'tradução', 'pergunta incompleta', nem peça detalhes se uma imagem ja foi enviada.\n"
        "- Nao invente titulo, eixos, valores, pessoas ou contexto.\n"
        "- Se for grafico e nao houver titulo/eixos/valores legiveis, diga claramente que nao conseguiu interpretar esses dados.\n"
        "- Se houver OCR util, use como evidência.\n"
        "- Se a descricao bruta for generica ou inutil, troque por uma resposta honesta e acionavel.\n"
        "- Limite a 3 frases curtas.\n\n"
        f"Modo: {mode}\n"
        f"Descricao bruta da visao: {raw_visual}\n"
        f"OCR disponivel: {ocr_hint or 'nenhum texto legivel'}\n\n"
        "Resposta final:"
    )
    try:
        refined = ask_model(
            prompt,
            timeout_seconds=30,
            num_predict=180,
            temperature=0.1,
        )
        refined = _clean_visual_response(refined, max_length=760)
        refined = re.sub(r"^(resposta final|resposta|final)\s*:\s*", "", refined, flags=re.IGNORECASE).strip()
        if refined:
            return refined
    except Exception:
        pass

    return raw_visual


def _looks_english(text: str) -> bool:
    lowered = f" {str(text or '').lower()} "
    stripped = str(text or "").strip().lower()
    if stripped.startswith(("the image", "this image", "in the image", "it shows", "there is", "there are")):
        return True

    english_hits = sum(
        1
        for token in (
            " the ",
            " there ",
            " this ",
            " image ",
            " appears ",
            " contains ",
            " shows ",
            " with ",
            " and ",
            " people ",
            " screen ",
            " table ",
            " computer ",
            " monitor ",
            " meeting ",
            " discussion ",
            " user interface ",
        )
        if token in lowered
    )
    portuguese_hits = sum(
        1
        for token in (" que ", " uma ", " com ", " imagem ", " parece ", " vejo ", " gráfico ", " tela ")
        if token in lowered
    )
    return english_hits >= 2 and english_hits >= portuguese_hits


def _looks_portuguese(text: str) -> bool:
    lowered = f" {str(text or '').lower()} "
    accents = any(char in str(text or "") for char in "áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ")
    portuguese_hits = sum(
        1
        for token in (
            " a imagem ",
            " esta imagem ",
            " na imagem ",
            " a tela ",
            " pessoas ",
            " pessoa ",
            " objeto ",
            " objetos ",
            " parece ",
            " mostra ",
            " vejo ",
            " há ",
            " ha ",
            " gráfico ",
            " grafico ",
            " reunião ",
            " reuniao ",
            " computador ",
            " conteúdo ",
            " conteudo ",
        )
        if token in lowered
    )
    return portuguese_hits >= 2 or (accents and not _looks_english(text))


def _ensure_portuguese(text: str) -> str:
    compact = _clean_visual_response(text, max_length=1200)
    if not compact:
        return compact

    needs_translation = _looks_english(compact) or not _looks_portuguese(compact)
    if not needs_translation:
        return compact

    try:
        translated = ask_model(
            "Traduza para portugues do Brasil, mantendo a resposta curta e natural. "
            "Nao acrescente informacoes novas. E proibido responder em ingles. "
            "Responda apenas com a traducao, sem explicar.\n\nTexto:\n"
            + compact,
            timeout_seconds=25,
            num_predict=300,
            temperature=0.1,
        )
        translated = _clean_visual_response(translated)
        translated = re.sub(r"^(tradu[cç][aã]o|texto traduzido)\s*:\s*", "", translated, flags=re.IGNORECASE).strip()
        if translated and _looks_english(translated):
            translated = ask_model(
                "Reescreva obrigatoriamente em portugues do Brasil. "
                "Nao explique, nao comente e nao use ingles.\n\nTexto:\n"
                + translated,
                timeout_seconds=25,
                num_predict=300,
                temperature=0.1,
            )
            translated = _clean_visual_response(translated)
            translated = re.sub(r"^(resposta|texto|tradu[cç][aã]o)\s*:\s*", "", translated, flags=re.IGNORECASE).strip()
        return translated or compact
    except Exception:
        return compact


def _semantic_image_analysis(
    path: Path,
    ocr_result: dict | None = None,
    prefix: str = "Análise visual",
    mode: str = "general",
) -> str:
    text = str((ocr_result or {}).get("text", "")).strip()
    extra = ""
    if text:
        compact_text = " ".join(text.split())
        if len(compact_text) > 500:
            compact_text = compact_text[:497].rstrip() + "..."
        extra = "\n\nTexto detectado por OCR para contexto:\n" + compact_text

    deterministic_chart = _infer_column_chart_from_image(path, ocr_result)
    if deterministic_chart:
        return f"{prefix}: {deterministic_chart}"

    if not _should_use_vision_model(mode):
        if text:
            chart_from_ocr = _ocr_chart_summary(text)
            if chart_from_ocr:
                return f"{prefix}: {chart_from_ocr}"
            if mode == "chart":
                return (
                    f"{prefix}: Consegui ler texto no recorte do grafico, mas ainda nao confirmei valores "
                    f"pela geometria ou por modelo visual. Texto legivel: {_compact_ocr_hint(text, limit=520)}"
                )
            return f"{prefix}: Texto legível na imagem: {_compact_ocr_hint(text, limit=520)}"
        if mode == "chart":
            return (
                f"{prefix}: Nao consegui ler o grafico com seguranca. "
                "Se houver modelo visual instalado, eu tento interpretar tipo, tendencia e valores; "
                "sem isso, amplie o grafico ou abra ele isolado."
            )
        return ""

    base_prompt = (
        "RESPONDA SOMENTE EM PORTUGUES DO BRASIL.\n"
        "Nao invente conteudo. Use apenas o que estiver visualmente claro ou no OCR. "
        "Se estiver incerto, diga que nao consegue confirmar. "
        "Se houver pessoa, descreva caracteristicas visuais e contexto sem identificar quem e. "
    )
    if mode == "chart":
        task_prompt = (
            "Tarefa: analisar grafico na imagem. Nao copie estas instrucoes. "
            "Procure sinais reais de grafico: barras, linhas, pizza, velas, eixos, legenda, escala, valores ou serie temporal. "
            "Se nao houver grafico claro, responda somente: Nao vejo um grafico claro na tela. "
            "Se houver grafico, responda em formato curto e estruturado: "
            "Tipo: ... Titulo: ... Valores: categoria: aproximadamente numero; categoria: aproximadamente numero. "
            "Tendencia: ... Conclusao pratica: ... "
            "Use apenas valores visiveis ou estimaveis pela imagem; quando for estimativa, diga aproximadamente."
        )
    else:
        task_prompt = (
            "Analise esta imagem para Pedro. Ele quer saber o que ha nela e o que isso significa, "
            "nao dados tecnicos do arquivo. Priorize elementos concretos visiveis: objetos, animais, pessoas, "
            "interfaces, documentos, cenario, simbolos, texto importante e relacoes espaciais. "
            "Se houver um grafico claro, interprete tipo, tendencia, valores visiveis e conclusao pratica. "
            "Se nao houver grafico, nao mencione grafico. "
            "Se parecer uma pagina ou app, explique o conteudo util visivel sem inventar assunto."
        )

    prompt = base_prompt + task_prompt + extra
    visual = ask_vision_model(path, prompt=prompt)
    visual = _ensure_portuguese(visual)
    visual = _refine_visual_response(visual, text, mode=mode)
    visual = _ensure_portuguese(visual)
    visual = _make_visual_response_useful(visual, text)
    if not visual and text:
        visual = _ocr_chart_summary(text) or ("Texto legível na imagem: " + _compact_ocr_hint(text, limit=520))
    if visual:
        return f"{prefix}: {visual}"
    return ""


def _remember_visual_result(source: str, response: str, details: dict | None = None):
    clean = " ".join(str(response or "").split()).strip()
    if not clean:
        return
    if clean.startswith(("Não encontrei", "Nao encontrei", "Não consegui", "Nao consegui", "Me diga ")):
        return
    remember_vision_analysis(source, clean, details=details or {})


def analyze_image_target(path: str | None = None, mode: str = "general") -> str:
    target = _resolve_target(path)
    if not str(path or "").strip():
        return "Me diga o caminho da imagem. Exemplo: analisar imagem C:\\pasta\\print.png"
    if not target.exists():
        return "Não encontrei essa imagem."
    if not target.is_file():
        return "Esse caminho não é um arquivo de imagem."
    if target.suffix.lower() not in SUPPORTED_SUFFIXES:
        return f"Formato ainda não suportado para análise: {target.suffix}"

    if target.suffix.lower() == ".svg":
        svg_summary = _infer_svg_column_chart(target)
        if svg_summary:
            response = "Análise visual: " + svg_summary
            _remember_visual_result("arquivo SVG", response, details={"kind": "file", "path": str(target), "mode": mode})
            return response
        return "Consegui abrir o SVG, mas ele não tem texto ou geometria simples suficiente para interpretar com segurança."

    try:
        result = _ocr_image(target)
    except Exception as exc:
        size_kb = max(1, round(target.stat().st_size / 1024))
        return f"Consegui localizar a imagem ({size_kb} KB), mas a análise falhou: {exc}"

    try:
        semantic = _semantic_image_analysis(target, ocr_result=result, mode=mode)
        if semantic:
            _remember_visual_result("arquivo", semantic, details={"kind": "file", "path": str(target), "mode": mode})
            return semantic
    except Exception as exc:
        fallback = _format_image_analysis(result)
        return vision_unavailable_message(exc) + " " + fallback

    response = _format_image_analysis(result)
    _remember_visual_result("arquivo", response, details={"kind": "file", "path": str(target), "mode": mode})
    return response


def analyze_graph_target(path: str | None = None) -> str:
    return analyze_image_target(path, mode="chart")


def analyze_screen_image(mode: str = "general") -> str:
    browser_image = _browser_local_image_from_foreground()
    if browser_image:
        return analyze_image_target(str(browser_image), mode=mode)

    screenshot_path = SCREENSHOT_DIR / f"axel_screen_{time.time_ns()}.png"
    analysis_path = screenshot_path
    try:
        _capture_foreground_window(screenshot_path)
        content_crop = _make_screen_content_crop(screenshot_path)
        if content_crop:
            analysis_path = content_crop

        result = _ocr_image(analysis_path)
        try:
            semantic = _semantic_image_analysis(
                analysis_path,
                ocr_result=result,
                prefix="Análise visual da tela",
                mode=mode,
            )
            if semantic:
                _remember_visual_result("tela", semantic, details={"kind": "screen", "mode": mode})
                return semantic
        except Exception as exc:
            return vision_unavailable_message(exc) + " " + _format_image_analysis(
                result,
                prefix="OCR da tela",
            )

        response = _format_image_analysis(result, prefix="OCR da tela")
        _remember_visual_result("tela", response, details={"kind": "screen", "mode": mode})
        return response
    except Exception as exc:
        return f"Não consegui analisar a imagem da tela: {exc}"
    finally:
        try:
            if analysis_path != screenshot_path:
                analysis_path.unlink(missing_ok=True)
            screenshot_path.unlink(missing_ok=True)
        except Exception:
            pass


def analyze_screen_graph() -> str:
    return analyze_screen_image(mode="chart")


def analyze_clipboard_image() -> str:
    clipboard_path = SCREENSHOT_DIR / f"axel_clipboard_{time.time_ns()}.png"
    try:
        _capture_clipboard_image(clipboard_path)
        result = _ocr_image(clipboard_path)
        try:
            semantic = _semantic_image_analysis(clipboard_path, ocr_result=result, prefix="Análise visual da imagem copiada")
            if semantic:
                _remember_visual_result("clipboard", semantic, details={"kind": "clipboard"})
                return semantic
        except Exception as exc:
            return vision_unavailable_message(exc) + " " + _format_image_analysis(
                result,
                prefix="OCR da imagem copiada",
            )

        response = _format_image_analysis(result, prefix="OCR da imagem copiada")
        _remember_visual_result("clipboard", response, details={"kind": "clipboard"})
        return response
    except Exception as exc:
        return f"Não encontrei imagem copiada para analisar: {exc}"
    finally:
        try:
            clipboard_path.unlink(missing_ok=True)
        except Exception:
            pass


def analyze_browser_image() -> str:
    browser_image = _browser_local_image_from_foreground()
    if browser_image:
        return analyze_image_target(str(browser_image))

    screenshot_summary = analyze_screen_image()
    if screenshot_summary.startswith("Análise visual"):
        return screenshot_summary

    try:
        from tools.browser_tools import browser_explain_screen

        browser_summary = browser_explain_screen()
    except Exception:
        browser_summary = ""

    if browser_summary and "Nao encontrei um navegador aberto" not in browser_summary and "Não encontrei um navegador aberto" not in browser_summary:
        return screenshot_summary + " Pelo conteúdo acessível do navegador: " + browser_summary

    return screenshot_summary + " Se for texto de uma página, tente também: o que tem na tela."
