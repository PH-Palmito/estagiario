import json
import time
import subprocess
from pathlib import Path

from llm.vision_client import ask_vision_model, vision_unavailable_message


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL_EXE = "powershell"
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
SCREENSHOT_DIR = ROOT / ".tmp" / "screenshots"


def _resolve_target(path: str | None) -> Path:
    raw = str(path or "").strip().strip('"').strip("'")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (ROOT / candidate).resolve()
    return candidate


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
    return json.loads(output) if output else {}


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
    compact = " ".join(str(response or "").split()).strip()
    compact = compact.replace("A imagem mostra", "Vejo")
    compact = compact.replace("A imagem parece mostrar", "Parece")
    if len(compact) > max_length:
        compact = compact[: max_length - 3].rstrip() + "..."
    return compact


def _semantic_image_analysis(path: Path, ocr_result: dict | None = None, prefix: str = "Análise visual") -> str:
    text = str((ocr_result or {}).get("text", "")).strip()
    extra = ""
    if text:
        compact_text = " ".join(text.split())
        if len(compact_text) > 500:
            compact_text = compact_text[:497].rstrip() + "..."
        extra = "\n\nTexto detectado por OCR para contexto:\n" + compact_text

    prompt = (
        "Analise esta imagem para o usuário Pedro. Ele quer saber o que há nela e o que isso significa, "
        "não dados técnicos do arquivo. Considere qualquer elemento visual relevante: objetos, animais, pessoas, gráficos, "
        "símbolos, interfaces, documentos, cenário, cores e relações espaciais. Se for gráfico, interprete tendência e conclusão. "
        "Se houver pessoa, descreva características visuais e contexto sem identificar quem é. Diga o que importa na imagem."
        + extra
    )
    visual = ask_vision_model(path, prompt=prompt)
    visual = _clean_visual_response(visual)
    if visual:
        return f"{prefix}: {visual}"
    return ""


def analyze_image_target(path: str | None = None) -> str:
    target = _resolve_target(path)
    if not str(path or "").strip():
        return "Me diga o caminho da imagem. Exemplo: analisar imagem C:\\pasta\\print.png"
    if not target.exists():
        return "Não encontrei essa imagem."
    if not target.is_file():
        return "Esse caminho não é um arquivo de imagem."
    if target.suffix.lower() not in SUPPORTED_SUFFIXES:
        return f"Formato ainda não suportado para análise: {target.suffix}"

    try:
        result = _ocr_image(target)
    except Exception as exc:
        size_kb = max(1, round(target.stat().st_size / 1024))
        return f"Consegui localizar a imagem ({size_kb} KB), mas a análise falhou: {exc}"

    try:
        semantic = _semantic_image_analysis(target, ocr_result=result)
        if semantic:
            return semantic
    except Exception as exc:
        fallback = _format_image_analysis(result)
        return vision_unavailable_message(exc) + " " + fallback

    return _format_image_analysis(result)


def analyze_screen_image() -> str:
    screenshot_path = SCREENSHOT_DIR / f"axel_screen_{time.time_ns()}.png"
    try:
        _capture_foreground_window(screenshot_path)
        result = _ocr_image(screenshot_path)
        try:
            semantic = _semantic_image_analysis(screenshot_path, ocr_result=result, prefix="Análise visual da tela")
            if semantic:
                return semantic
        except Exception as exc:
            return vision_unavailable_message(exc) + " " + _format_image_analysis(
                result,
                prefix="OCR da tela",
            )

        return _format_image_analysis(result, prefix="OCR da tela")
    except Exception as exc:
        return f"Não consegui analisar a imagem da tela: {exc}"
    finally:
        try:
            screenshot_path.unlink(missing_ok=True)
        except Exception:
            pass


def analyze_browser_image() -> str:
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
