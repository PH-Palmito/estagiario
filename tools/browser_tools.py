import base64
import ctypes
import json
import os
import random
import re
import subprocess
import time
import webbrowser
from urllib.parse import quote, quote_plus, unquote, urlparse

from llm.ollama_client import ask_model
from tools.system_tools import focus_app


user32 = ctypes.windll.user32
try:
    # Keeps UI Automation coordinates aligned with mouse coordinates on scaled/multi-monitor setups.
    user32.SetProcessDPIAware()
except Exception:
    pass

POWERSHELL_EXE = "powershell"
BROWSER_ACTIVATE_NAMES = ["chrome", "msedge", "firefox", "opera", "brave"]

VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_A = 0x41
VK_C = 0x43
VK_ESCAPE = 0x1B
VK_L = 0x4C
VK_V = 0x56
VK_W = 0x57
VK_F = 0x46
VK_R = 0x52
VK_F5 = 0x74
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_0 = 0x30
VK_BACK = 0x08
VK_RETURN = 0x0D
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_SPACE = 0x20
VK_DOWN = 0x28
VK_UP = 0x26
VK_LEFT = 0x25
VK_RIGHT = 0x27

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
SPOTIFY_TRACK_SEARCH_PREFIX = "track:"
SPOTIFY_TRACK_RESULT_CLICKS = (
    (0.52, 0.45),
    (0.49, 0.50),
    (0.56, 0.52),
)
LAST_BROWSER_ELEMENTS = []
LAST_BROWSER_CONTEXT = ""
LAST_BROWSER_CONTEXT_CHANGED_AT = 0.0
LAST_SELECTED_TEXT = ""


class _WinRect(ctypes.Structure):
    _fields_ = [
        ("Left", ctypes.c_long),
        ("Top", ctypes.c_long),
        ("Right", ctypes.c_long),
        ("Bottom", ctypes.c_long),
    ]


def _clear_browser_snapshot(context: str = ""):
    global LAST_BROWSER_ELEMENTS, LAST_BROWSER_CONTEXT, LAST_BROWSER_CONTEXT_CHANGED_AT

    LAST_BROWSER_ELEMENTS = []
    LAST_BROWSER_CONTEXT = context
    LAST_BROWSER_CONTEXT_CHANGED_AT = time.monotonic()


def _set_browser_elements(elements, context: str = ""):
    global LAST_BROWSER_ELEMENTS, LAST_BROWSER_CONTEXT

    LAST_BROWSER_ELEMENTS = list(elements)
    LAST_BROWSER_CONTEXT = context


def _remember_text_items(lines, context: str = ""):
    elements = [
        {
            "text": line,
            "x": None,
            "y": None,
            "type": "Text",
        }
        for line in lines
    ]
    _set_browser_elements(elements, context=context)


def _get_foreground_window_title() -> str:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""

    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""

    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value.strip()


def _get_foreground_window_rect():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    rect = _WinRect()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None

    left = int(rect.Left)
    top = int(rect.Top)
    right = int(rect.Right)
    bottom = int(rect.Bottom)
    if right <= left or bottom <= top:
        return None

    return left, top, right, bottom


def _get_foreground_window_capture_hash() -> str:
    rect = _get_foreground_window_rect()
    if not rect:
        return ""

    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width < 80 or height < 80:
        return ""

    temp_dir = os.path.join(os.getcwd(), ".tmp")
    try:
        os.makedirs(temp_dir, exist_ok=True)
    except Exception:
        temp_dir = os.environ.get("TEMP", temp_dir)

    image_path = os.path.join(temp_dir, f"screen-context-{time.monotonic_ns()}.png")
    ps_image_path = image_path.replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Drawing
$path = '{ps_image_path}'
$bmp = New-Object System.Drawing.Bitmap({width}, {height})
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
try {{
    $graphics.CopyFromScreen({left}, {top}, 0, 0, $bmp.Size)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $hash = (Get-FileHash -Algorithm SHA1 -Path $path).Hash
    Write-Output $hash
}} finally {{
    $graphics.Dispose()
    $bmp.Dispose()
    Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
}}
"""
    try:
        completed = _run_powershell(script, timeout_seconds=5)
    except Exception:
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception:
            pass
        return ""

    try:
        if os.path.exists(image_path):
            os.remove(image_path)
    except Exception:
        pass

    if completed.returncode != 0:
        return ""

    return (completed.stdout or "").strip().lower()


def _browser_context_signature() -> str:
    title = _get_foreground_window_title()
    if not title:
        return ""

    title = re.sub(r"\s+", " ", title).strip()
    title_signature = _normalize_text_for_match(title)
    page_url = _get_browser_url()
    if page_url:
        parsed = urlparse(page_url)
        url_signature = _normalize_text_for_match(f"{parsed.netloc}{parsed.path}")
        if url_signature:
            title_signature = f"{title_signature}|{url_signature}"
    capture_hash = _get_foreground_window_capture_hash()
    if capture_hash:
        return f"{title_signature}|{capture_hash[:16]}"
    return title_signature


def _refresh_browser_context() -> str:
    global LAST_BROWSER_CONTEXT, LAST_BROWSER_CONTEXT_CHANGED_AT

    context = _browser_context_signature()
    if context and LAST_BROWSER_CONTEXT and context != LAST_BROWSER_CONTEXT:
        _clear_browser_snapshot(context=context)
    elif context and not LAST_BROWSER_CONTEXT:
        LAST_BROWSER_CONTEXT = context
        LAST_BROWSER_CONTEXT_CHANGED_AT = time.monotonic()

    return context


def _browser_context_recently_changed(window_seconds: float = 1.2) -> bool:
    if LAST_BROWSER_CONTEXT_CHANGED_AT <= 0:
        return False
    return (time.monotonic() - LAST_BROWSER_CONTEXT_CHANGED_AT) <= window_seconds



def _run_powershell(script: str, timeout_seconds: int = 10) -> subprocess.CompletedProcess:
    utf8_preamble = """
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
"""
    encoded = base64.b64encode((utf8_preamble + script).encode("utf-16le")).decode("ascii")
    return subprocess.run(
        [
            POWERSHELL_EXE,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )


def _get_clipboard_text() -> str:
    try:
        completed = _run_powershell("Get-Clipboard -Raw -ErrorAction SilentlyContinue", timeout_seconds=3)
    except Exception:
        return ""

    return completed.stdout or ""


def _set_clipboard_text(text: str):
    try:
        subprocess.run(
            [
                POWERSHELL_EXE,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "Set-Clipboard",
            ],
            input=text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
        )
    except Exception:
        pass


def _activate_browser_window() -> bool:
    names = ", ".join(f"'{name}'" for name in BROWSER_ACTIVATE_NAMES)
    script = f"""
$shell = New-Object -ComObject WScript.Shell
$names = @({names})

foreach ($name in $names) {{
    try {{
        if ($shell.AppActivate($name)) {{
            Start-Sleep -Milliseconds 150
            Write-Output "OK"
            return
        }}
    }} catch {{
    }}
}}

Write-Output "NO"
"""

    try:
        completed = _run_powershell(script)
    except Exception:
        return False

    return completed.returncode == 0 and "OK" in (completed.stdout or "")


def _tap(vk_code: int):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _tap_times(vk_code: int, times: int, delay: float = 0.08):
    for _ in range(max(1, times)):
        _tap(vk_code)
        time.sleep(delay)


def _click(x: int, y: int, clicks: int = 1):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)

    for _ in range(max(1, clicks)):
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.03)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.12)


def _get_app_window_rect(app_name: str):
    script = f"""
$process = Get-Process -Name "{app_name}" -ErrorAction SilentlyContinue |
    Where-Object {{ $_.MainWindowHandle -ne 0 }} |
    Sort-Object StartTime -Descending |
    Select-Object -First 1

if (-not $process) {{
    Write-Output "__NO_WINDOW__"
    return
}}

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WinRectApi {{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {{
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }}

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}}
"@

$rect = New-Object WinRectApi+RECT
if ([WinRectApi]::GetWindowRect($process.MainWindowHandle, [ref]$rect)) {{
    Write-Output ("__RECT__:{0},{1},{2},{3}" -f $rect.Left, $rect.Top, $rect.Right, $rect.Bottom)
}} else {{
    Write-Output "__NO_RECT__"
}}
"""

    try:
        completed = _run_powershell(script)
    except Exception:
        return None

    output = completed.stdout or ""
    match = re.search(r"__RECT__:(-?\d+),(-?\d+),(-?\d+),(-?\d+)", output)
    if not match:
        return None

    left, top, right, bottom = [int(value) for value in match.groups()]
    if right <= left or bottom <= top:
        return None

    return left, top, right, bottom


def _get_browser_window_rect():
    for name in BROWSER_ACTIVATE_NAMES:
        rect = _get_app_window_rect(name)
        if rect:
            return rect

    return None


def _click_first_browser_link():
    names = ", ".join(f"'{name}'" for name in BROWSER_ACTIVATE_NAMES)
    script = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @({names})
$process = $null

foreach ($name in $processNames) {{
    $process = Get-Process -Name $name -ErrorAction SilentlyContinue |
        Where-Object {{ $_.MainWindowHandle -ne 0 }} |
        Sort-Object StartTime -Descending |
        Select-Object -First 1

    if ($process) {{
        break
    }}
}}

if (-not $process) {{
    Write-Output "__NO_BROWSER__"
    return
}}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {{
    Write-Output "__NO_ROOT__"
    return
}}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {{
    $element = $elements.Item($i)
    try {{
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 3) {{
            continue
        }}

        if ($rect.IsEmpty -or $rect.Width -lt 40 -or $rect.Height -lt 10) {{
            continue
        }}

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 135 -or $relativeLeft -lt 80) {{
            continue
        }}

        if ($controlType -notmatch "Hyperlink|Button|ListItem|DataItem") {{
            continue
        }}

        if ($name -match "^(voltar|avancar|recarregar|favoritos|perfil|mais|menu|google apps|entrar)$") {{
            continue
        }}

        $score = 1000 - $relativeTop
        if ($controlType -match "Hyperlink") {{
            $score += 200
        }}

        $candidates += [pscustomobject]@{{
            Top = $rect.Top
            Left = $rect.Left
            Score = $score
            X = [int]($rect.Left + [Math]::Min(160, [Math]::Max(20, $rect.Width / 2)))
            Y = [int]($rect.Top + ($rect.Height / 2))
        }}
    }} catch {{
    }}
}}

$candidate = $candidates |
    Sort-Object -Property @{{ Expression = "Score"; Descending = $true }}, @{{ Expression = "Top"; Descending = $false }}, @{{ Expression = "Left"; Descending = $false }} |
    Select-Object -First 1

if (-not $candidate) {{
    Write-Output "__NO_LINK__"
    return
}}

Write-Output ("__POINT__:{0},{1}" -f $candidate.X, $candidate.Y)
"""

    try:
        completed = _run_powershell(script, timeout_seconds=8)
    except Exception:
        return False

    output = completed.stdout or ""
    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)", output)
    if not point_match:
        return False

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    _click(x, y)
    return True


def _normalize_text_for_match(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_gallery_suffix(text: str) -> str:
    cleaned = re.sub(
        r"\s+(?:imagen|imagem|image)\s*-\s*\d+\s*/\s*\d+\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", cleaned).strip(" -")


def _short_click_query(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    normalized = re.sub(r"\bR\$\s*[\d\.\,]+.*$", "", normalized, flags=re.IGNORECASE).strip()
    words = normalized.split()

    if len(words) > 8:
        normalized = " ".join(words[:8])

    return normalized


def _click_query_variants(text: str) -> list[str]:
    base = _short_click_query(text)
    if not base:
        return []

    words = [word for word in base.split() if word]
    variants = []

    def add_variant(candidate: str):
        candidate = re.sub(r"\s+", " ", candidate).strip(" ,.-")
        if len(candidate) >= 3 and candidate not in variants:
            variants.append(candidate)

    add_variant(base)

    for size in (6, 5, 4, 3):
        if len(words) >= size:
            add_variant(" ".join(words[:size]))

    if "-" in base:
        add_variant(base.split("-", 1)[0])

    return variants


def _click_browser_item_from_text(text: str) -> bool:
    for query in _click_query_variants(text):
        if _click_browser_element_by_text(query):
            return True

    return False


def _extract_brl_price(text: str):
    matches = re.findall(r"R\$\s*([\d\.]+,\d{2})", text or "", flags=re.IGNORECASE)
    if not matches:
        return None

    values = []
    for match in matches:
        try:
            values.append(float(match.replace(".", "").replace(",", ".")))
        except ValueError:
            continue

    if not values:
        return None

    return min(values)


def _run_browser_javascript(script_body: str) -> bool:
    if not _activate_browser_window():
        return False

    old_clipboard = _get_clipboard_text()

    try:
        _shortcut(VK_CONTROL, VK_L)
        time.sleep(0.05)
        _type_text("javascript:")
        _set_clipboard_text(script_body)
        _shortcut(VK_CONTROL, VK_V)
        time.sleep(0.05)
        _tap(VK_RETURN)
        time.sleep(0.25)
        return True
    except Exception:
        return False
    finally:
        _set_clipboard_text(old_clipboard)


def _run_browser_javascript_and_read_clipboard(script_body: str, marker: str, timeout: float = 0.8) -> str:
    if not _activate_browser_window():
        return ""

    old_clipboard = _get_clipboard_text()

    try:
        _set_clipboard_text("")
        _shortcut(VK_CONTROL, VK_L)
        time.sleep(0.05)
        _type_text("javascript:")
        _set_clipboard_text(script_body)
        _shortcut(VK_CONTROL, VK_V)
        time.sleep(0.05)
        _tap(VK_RETURN)
        time.sleep(timeout)
        copied = _get_clipboard_text()

        if copied.startswith(marker):
            return copied[len(marker):].strip()

        return ""
    except Exception:
        return ""
    finally:
        _set_clipboard_text(old_clipboard)


def _click_page_item_by_text(text: str) -> bool:
    # Disabled: address-bar JavaScript bookmarklets can be interpreted as a search by Chrome.
    # Keep product clicks conservative until we have a safer browser-control channel.
    return False

    query = _short_click_query(text)
    if not query:
        return False

    query_json = json.dumps(query, ensure_ascii=False)
    script = f"""void ((()=>{{
const q={query_json};
const norm=s=>(s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[^\\p{{L}}\\p{{N}}\\s]/gu," ").replace(/\\s+/g," ").trim();
const words=norm(q).split(" ").filter(w=>w.length>2).slice(0,8);
const visible=el=>{{
  const r=el.getBoundingClientRect();
  const st=getComputedStyle(el);
  return r.width>30&&r.height>12&&r.bottom>70&&r.top<innerHeight&&st.visibility!=="hidden"&&st.display!=="none";
}};
const scoreElement=el=>{{
  if(!visible(el)) return null;
  const text=norm(el.innerText||el.textContent||el.getAttribute("aria-label")||el.title||"");
  if(!text) return null;
  let matches=0;
  for(const w of words) if(text.includes(w)) matches++;
  if(matches<Math.min(3, words.length)) return null;
  const r=el.getBoundingClientRect();
  let score=matches*1000-r.top;
  if(el.tagName==="A") score+=500;
  if(el.querySelector&&el.querySelector("a")) score+=250;
  if(text.includes("r$")) score+=150;
  return {{el, score, top:r.top}};
}};
const nodes=[...document.querySelectorAll("a,button,[role='link'],[role='button'],article,li,section,div")];
const best=nodes.map(scoreElement).filter(Boolean).sort((a,b)=>b.score-a.score||a.top-b.top)[0];
if(!best) return false;
const target=best.el.closest("a")||best.el.querySelector("a")||best.el;
target.scrollIntoView({{block:"center", inline:"center"}});
setTimeout(()=>target.click(),120);
return true;
}})())"""

    return _run_browser_javascript(script)


def _click_browser_element_by_text(query: str):
    query_words = [
        word
        for word in _normalize_text_for_match(query).split()
        if len(word) >= 2
    ][:5]
    if not query_words:
        return False

    ps_words = ", ".join(f"'{word}'" for word in query_words)
    names = ", ".join(f"'{name}'" for name in BROWSER_ACTIVATE_NAMES)
    script = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @({names})
$queryWords = @({ps_words})
$process = $null

foreach ($name in $processNames) {{
    $process = Get-Process -Name $name -ErrorAction SilentlyContinue |
        Where-Object {{ $_.MainWindowHandle -ne 0 }} |
        Sort-Object StartTime -Descending |
        Select-Object -First 1

    if ($process) {{
        break
    }}
}}

if (-not $process) {{
    Write-Output "__NO_BROWSER__"
    return
}}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {{
    Write-Output "__NO_ROOT__"
    return
}}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {{
    $element = $elements.Item($i)
    try {{
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 2) {{
            continue
        }}

        if ($rect.IsEmpty -or $rect.Width -lt 12 -or $rect.Height -lt 8) {{
            continue
        }}

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 85 -or $relativeLeft -lt 5) {{
            continue
        }}

        $normalizedName = $name.ToLower() -replace "[^\\p{{L}}\\p{{Nd}}\\s]", " "
        $normalizedName = $normalizedName -replace "\\s+", " "

        $matches = 0
        foreach ($word in $queryWords) {{
            if ($normalizedName.Contains($word)) {{
                $matches += 1
            }}
        }}

        if ($matches -le 0) {{
            continue
        }}

        $score = $matches * 100
        if ($controlType -match "Button|Hyperlink|ListItem|DataItem") {{
            $score += 80
        }}
        if ($matches -eq $queryWords.Count) {{
            $score += 120
        }}

        # Prefer visible content area and elements closer to the top.
        $score += [Math]::Max(0, 500 - [int]$relativeTop)

        $candidates += [pscustomobject]@{{
            Score = $score
            Top = $rect.Top
            Left = $rect.Left
            X = [int]($rect.Left + [Math]::Min([Math]::Max($rect.Width / 2, 12), 180))
            Y = [int]($rect.Top + ($rect.Height / 2))
        }}
    }} catch {{
    }}
}}

$candidate = $candidates |
    Sort-Object -Property @{{ Expression = "Score"; Descending = $true }}, @{{ Expression = "Top"; Descending = $false }}, @{{ Expression = "Left"; Descending = $false }} |
    Select-Object -First 1

if (-not $candidate) {{
    Write-Output "__NO_MATCH__"
    return
}}

Write-Output ("__POINT__:{0},{1}" -f $candidate.X, $candidate.Y)
"""

    try:
        completed = _run_powershell(script, timeout_seconds=8)
    except Exception:
        return False

    output = completed.stdout or ""
    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)", output)
    if not point_match:
        return False

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    _click(x, y)
    return True


def _read_browser_elements(limit: int = 10):
    names = ", ".join(f"'{name}'" for name in BROWSER_ACTIVATE_NAMES)
    script = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @({names})
$process = $null

foreach ($name in $processNames) {{
    $process = Get-Process -Name $name -ErrorAction SilentlyContinue |
        Where-Object {{ $_.MainWindowHandle -ne 0 }} |
        Sort-Object StartTime -Descending |
        Select-Object -First 1

    if ($process) {{
        break
    }}
}}

if (-not $process) {{
    Write-Output "__NO_BROWSER__"
    return
}}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {{
    Write-Output "__NO_ROOT__"
    return
}}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$rows = @()

for ($i = 0; $i -lt $elements.Count; $i++) {{
    $element = $elements.Item($i)
    try {{
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 3) {{
            continue
        }}

        if ($rect.IsEmpty -or $rect.Width -lt 20 -or $rect.Height -lt 8) {{
            continue
        }}

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 90 -or $relativeLeft -lt 5) {{
            continue
        }}

        if ($controlType -notmatch "Button|Hyperlink|ListItem|DataItem|Text|Edit|ComboBox") {{
            continue
        }}

        if ($name -match "^(voltar|avancar|recarregar|favoritos|perfil|mais|menu|google apps)$") {{
            continue
        }}

        $safeName = ($name -replace "\\s+", " ").Trim()
        if ($safeName.Length -gt 90) {{
            $safeName = $safeName.Substring(0, 90)
        }}

        $score = 1000 - [int]$relativeTop
        if ($controlType -match "Button|Hyperlink") {{
            $score += 150
        }}

        $rows += [pscustomobject]@{{
            Score = $score
            Top = [int]$rect.Top
            Left = [int]$rect.Left
            Text = ("__ITEM__|{0}|{1}|{2}|{3}" -f $safeName.Replace("|", " "), [int]($rect.Left + ($rect.Width / 2)), [int]($rect.Top + ($rect.Height / 2)), $controlType)
        }}
    }} catch {{
    }}
}}

$seen = @{{}}
$rows |
    Sort-Object -Property @{{ Expression = "Top"; Descending = $false }}, @{{ Expression = "Left"; Descending = $false }} |
    ForEach-Object {{
        $name = ($_.Text -split "\\|")[1]
        $key = $name.ToLower()
        if (-not $seen.ContainsKey($key)) {{
            $seen[$key] = $true
            Write-Output $_.Text
        }}
    }}
"""

    try:
        completed = _run_powershell(script, timeout_seconds=8)
    except Exception:
        return None

    output = completed.stdout or ""
    if "__NO_BROWSER__" in output or "__NO_ROOT__" in output:
        return None

    items = []
    for line in output.splitlines():
        if not line.startswith("__ITEM__|"):
            continue

        parts = line.split("|", 4)
        if len(parts) < 5:
            continue

        try:
            items.append(
                {
                    "text": parts[1].strip(),
                    "x": int(parts[2]),
                    "y": int(parts[3]),
                    "type": parts[4].strip(),
                }
            )
        except ValueError:
            continue

        if len(items) >= limit:
            break

    return items


def _useful_page_text_lines(text: str, limit: int = 10):
    ignore_patterns = (
        "javascript",
        "cookie",
        "politica de privacidade",
        "política de privacidade",
        "termos de uso",
        "menu",
        "entrar",
        "minha conta",
        "sacola",
        "carrinho",
        "buscar",
        "pesquisar",
    )
    lines = []
    seen = set()

    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()

        if len(line) < 4 or len(line) > 120:
            continue

        normalized = _normalize_text_for_match(line)
        if not normalized or normalized in seen:
            continue

        if normalized.isdigit():
            continue

        if re.match(r"^(?:r\$\s*)?[\d\.\,]+$", line.lower()):
            continue

        if re.match(r"^\d+x\s+de\s+r\$", line.lower()):
            continue

        if any(pattern in normalized for pattern in ignore_patterns):
            continue

        score = 0
        if re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()):
            score += 80
        if any(word in normalized for word in {"celular", "notebook", "smartphone", "iphone", "samsung", "motorola", "xiaomi", "comprar", "frete", "oferta"}):
            score += 50
        score += max(0, 60 - len(lines))
        lines.append((score, line))
        seen.add(normalized)

    lines.sort(key=lambda item: item[0], reverse=True)
    return [line for _score, line in lines[:limit]]


def _screen_lines_quality(lines) -> int:
    if not lines:
        return 0

    product_words = {
        "celular", "smartphone", "notebook", "iphone", "galaxy", "moto", "motorola",
        "xiaomi", "redmi", "samsung", "realme", "oppo", "lavadora", "lava", "relogio",
        "relógio", "tv", "monitor", "fogao", "fogão", "geladeira",
    }
    noise_terms = {
        "sem juros", "vez de r$", "vezes de r$", "frete", "cupom", "celulares",
        "eletrodomesticos", "eletrodomésticos", "tipo de", "comprar agora",
    }

    score = 0
    for line in lines:
        normalized = _normalize_text_for_match(line)
        if not normalized:
            continue

        has_letters = bool(re.search(r"[a-zA-Z\u00C0-\u017F]", line))
        has_digits = bool(re.search(r"\d", line))
        if has_letters:
            score += 5
        if len(normalized.split()) >= 4:
            score += 2
        if any(word in normalized for word in product_words):
            score += 6
        if re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()):
            score -= 2
        if any(term in normalized for term in noise_terms):
            score -= 4
        if has_digits and not has_letters:
            score -= 8

    return score + len(lines)


def _screen_list_intro() -> str:
    return random.choice(
        [
            "Consegui ler texto da pagina",
            "Isto foi o que achei na pagina",
            "Encontrei estes pontos na tela",
            "O que estou vendo na pagina e",
        ]
    )


def _screen_summary_intro() -> str:
    return random.choice(
        [
            "Resumo da tela",
            "Panorama da tela",
            "Visao rapida da tela",
        ]
    )


def _get_browser_url() -> str:
    if not _activate_browser_window():
        return ""

    old_clipboard = _get_clipboard_text()
    sentinel = f"__ESTAGIARIO_BROWSER_URL__{time.monotonic_ns()}__"
    copied = ""

    try:
        _set_clipboard_text(sentinel)
        time.sleep(0.03)
        _shortcut(VK_CONTROL, VK_L)
        time.sleep(0.08)
        _shortcut(VK_CONTROL, VK_C)
        for _ in range(12):
            time.sleep(0.08)
            sample = _get_clipboard_text().strip()
            if sample and sample != sentinel and sample != old_clipboard:
                copied = sample
                break
    finally:
        _tap(VK_ESCAPE)
        _set_clipboard_text(old_clipboard)

    if not copied:
        return ""

    if copied.startswith(("http://", "https://")):
        return copied

    return ""


def _clean_browser_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", title or "").strip(" -|")
    cleaned = re.sub(r"\s*-\s*(google chrome|chrome|microsoft edge|edge|mozilla firefox|firefox|opera|brave)$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _parse_github_repo_from_url(page_url: str) -> str:
    parsed = urlparse(page_url or "")
    if "github.com" not in parsed.netloc.lower():
        return ""

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return ""


def _parse_title_content(clean_title: str, page_url: str) -> str:
    if not clean_title:
        return ""

    parsed = urlparse(page_url or "")
    host = parsed.netloc.lower()

    if "youtube.com" in host or "youtu.be" in host:
        return re.sub(r"\s*-\s*youtube$", "", clean_title, flags=re.IGNORECASE).strip()

    if "github.com" in host:
        match = re.match(r"GitHub\s*-\s*([^:]+):\s*(.+)$", clean_title, flags=re.IGNORECASE)
        if match:
            return match.group(2).strip()

    return clean_title


def _detect_screen_category(lines, page_url: str = "", page_title: str = "") -> str:
    normalized_blob = " ".join(_normalize_text_for_match(line) for line in lines if line)
    parsed = urlparse(page_url or "")
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    title_blob = _normalize_text_for_match(page_title)

    if "github.com" in host:
        return "repositorio github"

    if ("youtube.com" in host or "youtu.be" in host) and ("/watch" in path or "youtube" in title_blob):
        return "video youtube"

    category_patterns = [
        ("repositorio github", ("repository navigation", "pull requests", "issues", "actions", "discussions", "github")),
        ("video youtube", ("up next", "youtube", "inscrito", "inscrever-se", "comentarios", "comentários")),
        ("smartphones", ("smartphone", "celular", "iphone", "galaxy", "redmi", "motorola", "oppo", "realme")),
        ("notebooks", ("notebook", "ideapad", "vivobook", "aspire", "inspiron", "thinkpad", "macbook")),
        ("lavadoras", ("lavadora", "lava loucas", "lava-loucas", "lava e seca", "samsung ww", "electrolux")),
        ("televisores", ("smart tv", "televis", "polegadas", "suporte articulado", "monitor")),
        ("relogios", ("relogio", "relogios", "watch", "smartwatch", "amazfit", "mi band")),
    ]

    for category, patterns in category_patterns:
        if any(pattern in normalized_blob for pattern in patterns):
            return category

    return ""


def _content_showcase(lines, limit: int = 3) -> list[str]:
    showcase = []
    for line in lines:
        compact = re.sub(r"\s+", " ", line).strip()
        if len(compact) > 110:
            compact = compact[:107].rstrip() + "..."
        if compact and compact not in showcase:
            showcase.append(compact)
        if len(showcase) >= limit:
            break
    return showcase


def _summarize_screen_lines(lines, page_url: str = "", page_title: str = "") -> str:
    if not lines:
        return "Nao consegui extrair um resumo confiavel da tela."

    normalized_lines = [_normalize_text_for_match(line) for line in lines if line]
    category = _detect_screen_category(lines, page_url=page_url, page_title=page_title)
    clean_title = _clean_browser_title(page_title)
    title_content = _parse_title_content(clean_title, page_url)

    if category == "repositorio github":
        repo_name = _parse_github_repo_from_url(page_url)
        content_lines = []
        for line in lines:
            compact = re.sub(r"\s+", " ", line).strip()
            normalized_compact = _normalize_text_for_match(compact)
            if normalized_compact.startswith("ir para o conte"):
                continue
            if normalized_compact in {
                "repository navigation",
                "code",
                "issues",
                "pull requests",
                "actions",
                "discussions",
                "agents",
                "security",
                "insights",
                "projects",
                "wiki",
                "releases",
                "packages",
            }:
                continue
            if len(compact) < 4:
                continue
            content_lines.append(compact)

        content_lines = list(dict.fromkeys(content_lines))
        showcase = _content_showcase(content_lines, limit=2)
        if repo_name and title_content and title_content.lower() != repo_name.lower():
            return f"É o repositorio {repo_name} no GitHub. Pelo titulo, o foco parece ser: {title_content}. No conteudo visivel, vejo: " + "; ".join(showcase) + "."
        if repo_name and showcase:
            return f"É o repositorio {repo_name} no GitHub. No conteudo visivel, vejo: " + "; ".join(showcase) + "."
        if repo_name:
            return f"É o repositorio {repo_name} no GitHub. Estou vendo a navegacao principal com Code, Issues, Pull requests, Discussions e Actions."
        return "Parece um repositorio no GitHub. Estou vendo a navegacao principal e parte do conteudo do projeto."

    if category == "video youtube":
        title = title_content or clean_title or "um video no YouTube"
        showcase = _content_showcase([line for line in lines if _normalize_text_for_match(line) not in {"up next", "youtube"}], limit=2)
        if showcase:
            return f"Parece a pagina de um video no YouTube: {title}. Na tela, vejo: " + "; ".join(showcase) + "."
        return f"Parece a pagina de um video no YouTube: {title}."

    pure_price_lines = 0
    for line in lines:
        line_lower = line.lower()
        if re.search(r"r\$\s*\d|\d+,\d{2}", line_lower) and not re.search(r"[a-zA-Z\u00C0-\u017F]{4,}", line):
            pure_price_lines += 1
        if "sem juros" in line_lower or "vez" in line_lower:
            pure_price_lines += 1

    if pure_price_lines >= max(3, len(lines) // 2):
        return "Vejo principalmente precos e parcelas. A tela parece comercial, mas ainda nao peguei bem os nomes principais dos itens."

    showcase = _content_showcase(lines, limit=3)

    if category in {"smartphones", "notebooks", "lavadoras", "televisores", "relogios"}:
        return f"Parece uma lista de {category}. Destaques: " + "; ".join(showcase) + "."

    if any("repository navigation" in line or "pull requests" in line for line in normalized_lines):
        return "Parece uma pagina de repositorio com navegacao e abas principais, mais do que conteudo detalhado do projeto."

    if title_content and title_content not in showcase:
        return f"Pelo titulo da pagina, o foco parece ser: {title_content}. Na tela, vejo: " + "; ".join(showcase) + "."

    return f"Vejo {len(lines)} itens principais na tela. Destaques: " + "; ".join(showcase) + "."


def _should_auto_summarize(lines, quality_score: int, page_url: str = "", page_title: str = "") -> bool:
    if not lines:
        return False

    if _detect_screen_category(lines, page_url=page_url, page_title=page_title) in {"repositorio github", "video youtube"}:
        return True

    summary_hint = _summarize_screen_lines(lines, page_url=page_url, page_title=page_title).lower()
    if "precos e parcelas" in summary_hint:
        return True

    if quality_score < 22:
        return True

    long_lines = sum(1 for line in lines if len(line) >= 70)
    if len(lines) >= 6 and long_lines >= 4:
        return True

    if len("; ".join(lines)) >= 520:
        return True

    return False


def _rank_page_text_lines(text: str, limit: int = 10):
    ignore_patterns = (
        "javascript",
        "cookie",
        "politica de privacidade",
        "termos de uso",
        "menu",
        "entrar",
        "minha conta",
        "sacola",
        "carrinho",
        "buscar",
        "pesquisar",
        "departamentos",
        "atendimento",
        "central de",
        "compre pelo",
        "formas de pagamento",
        "pular navegacao",
        "pular navegação",
        "imagem do avatar",
        "avatar",
        "login",
        "memoria ram",
        "cupom",
        "sem juros",
        "cashback",
        "desconto",
    )
    category_noise = {
        "celulares",
        "celular",
        "a celular",
        "celulares e smartphones",
        "samsung",
        "motorola",
        "xiaomi",
        "apple",
        "iphone",
    }
    product_words = {
        "celular",
        "smartphone",
        "notebook",
        "iphone",
        "galaxy",
        "moto",
        "realme",
        "xiaomi",
        "redmi",
        "samsung",
        "motorola",
        "lenovo",
        "acer",
        "dell",
        "positivo",
        "tablet",
    }
    spec_words = {
        "gb",
        "ram",
        "mah",
        "tela",
        "hz",
        "nfc",
        "ip54",
        "resistencia",
        "camera",
        "processador",
    }
    lines = []
    seen = set()

    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = _strip_gallery_suffix(line)

        if len(line) < 4 or len(line) > 180:
            continue

        normalized = _normalize_text_for_match(line)
        if not normalized or normalized in seen:
            continue

        if normalized.isdigit():
            continue

        words = normalized.split()
        has_price = bool(re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()))
        price_only = bool(re.match(r"^r\$\s*[\d\.\,]+$", line.lower()))
        looks_like_slug = line.count("-") >= 2 and " " not in line.strip()
        has_product_word = any(word in product_words for word in words)
        has_spec_word = any(word in spec_words for word in words)

        if looks_like_slug:
            continue

        if price_only:
            continue

        if normalized in category_noise:
            continue

        if len(words) <= 2 and not has_price:
            continue

        if len(words) <= 3 and has_spec_word and not has_product_word and not has_price:
            continue

        if any(pattern in normalized for pattern in ignore_patterns):
            continue

        if re.match(r"^\d+x\s+de\s+r\$", line.lower()):
            continue

        if not has_product_word:
            continue

        if len(line) > 145:
            line = line[:142].rstrip() + "..."

        lines.append(line)
        seen.add(normalized)

        if len(lines) >= limit:
            break

    return lines


def _selected_text_items(text: str, limit: int = 10):
    product_words = {
        "celular",
        "smartphone",
        "notebook",
        "iphone",
        "galaxy",
        "moto",
        "realme",
        "xiaomi",
        "redmi",
        "samsung",
        "motorola",
        "lenovo",
        "acer",
        "dell",
        "positivo",
        "tablet",
    }
    noise_patterns = (
        "memoria ram",
        "cupom",
        "sem juros",
        "frete",
        "favorito",
        "avaliacao",
        "avaliações",
        "avaliacoes",
        "patrocinado",
    )
    raw_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in (text or "").splitlines()
    ]
    raw_lines = [line for line in raw_lines if line]
    items = []
    seen = set()

    for index, line in enumerate(raw_lines):
        line = _strip_gallery_suffix(line)
        normalized = _normalize_text_for_match(line)
        words = normalized.split()

        if not normalized or normalized in seen:
            continue

        if any(pattern in normalized for pattern in noise_patterns):
            continue

        if line.count("-") >= 2 and " " not in line:
            continue

        if not any(word in product_words for word in words):
            continue

        item = line
        if "r$" not in normalized:
            for extra in raw_lines[index + 1:index + 5]:
                if re.search(r"r\$\s*[\d\.\,]+", extra.lower()) and not re.match(r"^\d+x\s+de\s+r\$", extra.lower()):
                    item = f"{item} - {extra}"
                    break

        if len(item) > 180:
            item = item[:177].rstrip() + "..."

        items.append(item)
        seen.add(normalized)

        if len(items) >= limit:
            break

    if items:
        return items

    return _rank_page_text_lines(text, limit=limit)


def _read_product_cards_via_javascript(limit: int = 10):
    marker = "__ESTAGIARIO_PRODUCTS__\n"
    script = f"""void ((()=>{{
const marker={json.dumps(marker)};
const limit={int(limit)};
const viewportOffsetX=Math.max(0, Math.round((window.outerWidth - window.innerWidth)/2));
const viewportOffsetY=Math.max(0, Math.round(window.outerHeight - window.innerHeight));
const norm=s=>(s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[^\\p{{L}}\\p{{N}}\\s]/gu," ").replace(/\\s+/g," ").trim();
const clean=s=>(s||"").replace(/\\s+/g," ").trim();
const visible=el=>{{
  const r=el.getBoundingClientRect();
  const st=getComputedStyle(el);
  return r.width>35&&r.height>20&&r.bottom>90&&r.top<innerHeight&&st.visibility!=="hidden"&&st.display!=="none";
}};
const productRe=/\\b(celular|smartphone|notebook|iphone|galaxy|xiaomi|redmi|samsung|motorola|realme|lenovo|acer|dell|tablet)\\b/i;
const noiseRe=/\\b(memoria ram|cupom|frete|departamento|categoria|sacola|carrinho|entrar|login|favorito|ordenar|filtrar|avaliacao|avaliações|sem juros|cashback)\\b/i;
const slugText=href=>{{
  try {{
    const url=new URL(href, location.href);
    const part=decodeURIComponent(url.pathname.split("/").filter(Boolean)[0]||"");
    return clean(part.replace(/-/g," "));
  }} catch(e) {{
    return "";
  }}
}};
const bestCardText=a=>{{
  const chunks=[];
  chunks.push(a.innerText, a.getAttribute("aria-label"), a.title);
  const img=a.querySelector("img");
  if(img) chunks.push(img.alt);

  let node=a;
  for(let depth=0; node&&depth<5; depth++, node=node.parentElement) {{
    if(!visible(node)) continue;
    const text=clean(node.innerText||node.textContent||"");
    if(text.length>=8&&text.length<=700) chunks.push(text);
  }}

  let best="";
  for(const raw of chunks) {{
    const text=clean(raw);
    const n=norm(text);
    if(!text||noiseRe.test(n)) continue;
    if(productRe.test(n)||/r\\$\\s*\\d/i.test(text)) {{
      if(text.length>best.length) best=text;
    }}
  }}

  if(best) return best;
  return slugText(a.href);
}};
const anchors=[...document.querySelectorAll("a[href]")];
const rows=[];
const seen=new Set();
for(const a of anchors) {{
  if(!visible(a)) continue;
  const href=a.href||"";
  const raw=bestCardText(a);
  let text=clean(raw);
  if(!text) continue;
  if(text.length>170) text=text.slice(0,167).trim()+"...";
  const n=norm(text);
  const hrefNorm=norm(slugText(href));
  const looksProduct=productRe.test(n)||productRe.test(hrefNorm)||/\\/p\\//.test(href);
  if(!looksProduct||noiseRe.test(n)) continue;
  if(n.length<8||seen.has(href)||seen.has(n)) continue;
  seen.add(href);
  seen.add(n);
  const r=a.getBoundingClientRect();
  rows.push({{
    top:r.top,
    left:r.left,
    x:Math.round(window.screenX + viewportOffsetX + r.left + Math.min(Math.max(r.width/2, 20), 220)),
    y:Math.round(window.screenY + viewportOffsetY + r.top + Math.min(Math.max(r.height/2, 16), 90)),
    text,
    type:"Hyperlink"
  }});
}}
rows.sort((a,b)=>a.top-b.top||a.left-b.left);
const output=marker+JSON.stringify(rows.slice(0,limit));
const fallback=()=>{{
  const ta=document.createElement("textarea");
  ta.value=output;
  ta.style.position="fixed";
  ta.style.left="-9999px";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {{ document.execCommand("copy"); }} catch(e) {{}}
  ta.remove();
}};
if(navigator.clipboard&&navigator.clipboard.writeText) {{
  navigator.clipboard.writeText(output).catch(fallback);
}} else {{
  fallback();
}}
}})())"""

    copied = _run_browser_javascript_and_read_clipboard(script, marker)
    try:
        rows = json.loads(copied)
    except json.JSONDecodeError:
        return []

    items = []
    seen = set()

    for row in rows:
        if not isinstance(row, dict):
            continue

        line = re.sub(r"\s+", " ", str(row.get("text", ""))).strip()
        normalized = _normalize_text_for_match(line)

        if len(line) < 8 or not normalized or normalized in seen:
            continue

        try:
            items.append(
                {
                    "text": line,
                    "x": int(row.get("x")),
                    "y": int(row.get("y")),
                    "type": str(row.get("type", "Hyperlink")).strip() or "Hyperlink",
                    "source": "dom_product",
                }
            )
        except (TypeError, ValueError):
            continue

        seen.add(normalized)

        if len(items) >= limit:
            break

    return items


def _read_page_text_via_clipboard(limit: int = 10):
    old_clipboard = _get_clipboard_text()
    copied = ""
    sentinel = f"__ESTAGIARIO_READ_PAGE__{time.monotonic_ns()}__"
    last_sample = ""
    stable_reads = 0

    try:
        _set_clipboard_text(sentinel)
        time.sleep(0.03)
        _shortcut(VK_CONTROL, VK_A)
        time.sleep(0.12)
        _shortcut(VK_CONTROL, VK_C)
        for _ in range(18):
            time.sleep(0.12)
            sample = _get_clipboard_text()
            stripped = sample.strip()
            if not stripped or stripped == sentinel or sample == old_clipboard:
                stable_reads = 0
                continue

            copied = sample
            if sample == last_sample:
                stable_reads += 1
            else:
                last_sample = sample
                stable_reads = 1

            if stable_reads >= 2 and len(stripped) >= 20:
                break
    finally:
        _tap(VK_ESCAPE)
        _set_clipboard_text(old_clipboard)

    ranked_lines = _rank_page_text_lines(copied, limit=limit)
    if ranked_lines:
        return ranked_lines

    return _useful_page_text_lines(copied, limit=limit)


def _click_relative_to_app(app_name: str, relative_x: float, relative_y: float, clicks: int = 1):
    rect = _get_app_window_rect(app_name)
    if not rect:
        return False

    left, top, right, bottom = rect
    x = left + ((right - left) * relative_x)
    y = top + ((bottom - top) * relative_y)
    _click(x, y, clicks=clicks)
    return True


def _click_spotify_track_result():
    clicked = False

    for relative_x, relative_y in SPOTIFY_TRACK_RESULT_CLICKS:
        if _click_relative_to_app("Spotify", relative_x, relative_y, clicks=2):
            clicked = True
            time.sleep(0.35)

    return clicked


def _click_spotify_music_filter():
    script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$process = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    Write-Output "__NO_SPOTIFY__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$trueCondition = [System.Windows.Automation.Condition]::TrueCondition
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $trueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim().ToLower()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if ($name -notlike "m*sicas") {
            continue
        }

        if ($rect.IsEmpty -or $rect.Width -lt 20 -or $rect.Height -lt 10) {
            continue
        }

        $relativeLeft = $rect.Left - $rootRect.Left
        $relativeTop = $rect.Top - $rootRect.Top

        # Prefer the search filter row, not library/sidebar labels.
        if ($relativeTop -gt 70 -and $relativeTop -lt 170 -and $relativeLeft -gt 250) {
            $candidates += [pscustomobject]@{
                Element = $element
                Top = $rect.Top
                Left = $rect.Left
            }
        }
    } catch {
    }
}

$candidateItem = $candidates | Sort-Object Top, Left | Select-Object -First 1
if (-not $candidateItem) {
    Write-Output "__NO_FILTER__"
    return
}

try {
    $candidate = $candidateItem.Element
    $pattern = $null
    if ($candidate.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
        $pattern.Invoke()
        Write-Output "__OK__"
        return
    }
} catch {
}

try {
    $rect = $candidateItem.Element.Current.BoundingRectangle
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MouseClicker {
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")]
    public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
}
"@
    $x = [int]($rect.Left + ($rect.Width / 2))
    $y = [int]($rect.Top + ($rect.Height / 2))
    [void][MouseClicker]::SetCursorPos($x, $y)
    Start-Sleep -Milliseconds 80
    [MouseClicker]::mouse_event(2, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 40
    [MouseClicker]::mouse_event(4, 0, 0, 0, 0)
    Write-Output "__OK__"
    return
} catch {
}

Write-Output "__NO_CLICK__"
"""

    try:
        completed = _run_powershell(script, timeout_seconds=8)
    except Exception:
        return False

    return completed.returncode == 0 and "__OK__" in (completed.stdout or "")


def _click_spotify_track_by_name(query: str):
    words = [word for word in re.sub(r"[^\w\s]", " ", query.lower()).split() if len(word) >= 3]
    ps_words = ", ".join(f"'{word}'" for word in words[:4])
    if not ps_words:
        return False

    script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$queryWords = @(__QUERY_WORDS__)
$process = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    Write-Output "__NO_SPOTIFY__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$trueCondition = [System.Windows.Automation.Condition]::TrueCondition
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $trueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).ToLower()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name) {
            continue
        }

        if ($rect.IsEmpty -or $rect.Height -lt 8) {
            continue
        }

        if ($controlType -match "Button") {
            if ($rect.Width -lt 8) {
                continue
            }
        } elseif ($rect.Width -lt 20) {
            continue
        }

        $relativeLeft = $rect.Left - $rootRect.Left
        $relativeTop = $rect.Top - $rootRect.Top
        $isResultArea = $relativeLeft -gt 250 -and $relativeTop -gt 120
        $isPlayButton = $controlType -match "Button" -and ($name.StartsWith("tocar ") -or $name.StartsWith("play "))

        $matches = 0
        foreach ($word in $queryWords) {
            if ($name.Contains($word)) {
                $matches += 1
            }
        }

        if (($matches -gt 0 -or ($isPlayButton -and $isResultArea)) -and $controlType -match "Button|Text|DataItem|ListItem|Custom") {
            $score = $matches * 100

            if ($isPlayButton) {
                $score += 500
            }

            if ($controlType -match "DataItem|ListItem") {
                $score += 20
            }

            # Prefer the result/list area over sidebar/library/global controls.
            if ($isResultArea) {
                $score += 100
            }

            $candidates += [pscustomobject]@{
                Element = $element
                Score = $score
                Top = $rect.Top
                Left = $rect.Left
                ControlType = $controlType
            }
        }
    } catch {
    }
}

$candidateItem = $candidates |
    Sort-Object -Property @{ Expression = "Score"; Descending = $true }, @{ Expression = "Top"; Descending = $false }, @{ Expression = "Left"; Descending = $true } |
    Select-Object -First 1

if (-not $candidateItem) {
    Write-Output "__NO_TRACK_TEXT__"
    return
}

try {
    $candidate = $candidateItem.Element
    $rect = $candidate.Current.BoundingRectangle
    if (-not $rect.IsEmpty) {
        if ($candidateItem.ControlType -match "Button") {
            # The button is often hidden behind the track number. Use it as an anchor
            # and double-click inside the row title area instead.
            $x = [int]($rect.Left + 90)
            $clicks = 2
        } else {
            # Spotify hides the play button behind the track number until hover.
            # A double click on the song row/card is more reliable.
            $x = [int]($rect.Left + [Math]::Min(180, [Math]::Max(40, $rect.Width / 3)))
            $clicks = 2
        }
        $y = [int]($rect.Top + ($rect.Height / 2))
        Write-Output ("__POINT__:{0},{1},{2}" -f $x, $y, $clicks)
        return
    }
} catch {
}

Write-Output "__NO_CLICK__"
"""
    script = script.replace("__QUERY_WORDS__", ps_words)

    try:
        completed = _run_powershell(script)
    except Exception:
        return False

    output = completed.stdout or ""
    if "__OK__" in output:
        return True

    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)(?:,(\d+))?", output)
    if not point_match:
        return False

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    clicks = int(point_match.group(3) or 1)
    user32.SetCursorPos(x, y)
    time.sleep(0.25)
    _click(x, y, clicks=clicks)
    return True


def _click_spotify_first_visible_track():
    script = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$process = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    Write-Output "__NO_SPOTIFY__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$trueCondition = [System.Windows.Automation.Condition]::TrueCondition
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $trueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim().ToLower()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $rect.IsEmpty -or $rect.Height -lt 8 -or $rect.Width -lt 8) {
            continue
        }

        $relativeLeft = $rect.Left - $rootRect.Left
        $relativeTop = $rect.Top - $rootRect.Top
        $isResultArea = $relativeLeft -gt 250 -and $relativeTop -gt 120

        if (-not $isResultArea) {
            continue
        }

        $score = 0
        if ($controlType -match "DataItem|ListItem|Custom" -and $name -match "^\d+\s+tocar\s+") {
            $score = 600
        } elseif ($controlType -match "Button" -and ($name.StartsWith("tocar ") -or $name.StartsWith("play "))) {
            $score = 500
        } elseif ($controlType -match "DataItem|ListItem|Custom" -and $name.Contains(" tocar ") -and $name.Contains(" adicionar ")) {
            $score = 450
        }

        if ($score -le 0) {
            continue
        }

        $candidates += [pscustomobject]@{
            Element = $element
            Score = $score
            Top = $rect.Top
            Left = $rect.Left
            ControlType = $controlType
        }
    } catch {
    }
}

$candidateItem = $candidates |
    Sort-Object -Property @{ Expression = "Score"; Descending = $true }, @{ Expression = "Top"; Descending = $false }, @{ Expression = "Left"; Descending = $false } |
    Select-Object -First 1

if (-not $candidateItem) {
    Write-Output "__NO_FIRST_TRACK__"
    return
}

try {
    $rect = $candidateItem.Element.Current.BoundingRectangle
    if (-not $rect.IsEmpty) {
        if ($candidateItem.ControlType -match "Button") {
            $x = [int]($rect.Left + 90)
        } else {
            $x = [int]($rect.Left + [Math]::Min(180, [Math]::Max(80, $rect.Width / 3)))
        }
        $y = [int]($rect.Top + ($rect.Height / 2))
        Write-Output ("__POINT__:{0},{1}" -f $x, $y)
        return
    }
} catch {
}

Write-Output "__NO_CLICK__"
"""

    try:
        completed = _run_powershell(script)
    except Exception:
        return False

    output = completed.stdout or ""
    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)", output)
    if not point_match:
        return False

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    user32.SetCursorPos(x, y)
    time.sleep(0.25)
    _click(x, y, clicks=2)
    return True


def spotify_diagnostic():
    focus_app("spotify")
    time.sleep(0.3)

    script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$process = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    Write-Output "__NO_SPOTIFY__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$trueCondition = [System.Windows.Automation.Condition]::TrueCondition
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $trueCondition)
$rows = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim()
        if (-not $name -or $name.Length -lt 2) {
            continue
        }

        $rect = $element.Current.BoundingRectangle
        if ($rect.IsEmpty -or $rect.Width -lt 10 -or $rect.Height -lt 5) {
            continue
        }

        $controlType = $element.Current.ControlType.ProgrammaticName
        $left = [int]$rect.Left
        $top = [int]$rect.Top
        $width = [int]$rect.Width
        $height = [int]$rect.Height
        $safeName = $name.Replace("`r", " ").Replace("`n", " ")

        $rows += [pscustomobject]@{
            Top = $top
            Left = $left
            Text = ("{0} | {1} | x={2} y={3} w={4} h={5}" -f $safeName, $controlType, $left, $top, $width, $height)
        }
    } catch {
    }
}

$rows |
    Sort-Object Top, Left |
    Select-Object -First 120 |
    ForEach-Object { Write-Output $_.Text }
"""

    try:
        completed = _run_powershell(script, timeout_seconds=12)
    except Exception as e:
        return f"Erro no diagnostico do Spotify: {e}"

    output = (completed.stdout or "").strip()
    if "__NO_SPOTIFY__" in output:
        return "Nao encontrei uma janela aberta do Spotify."
    if "__NO_ROOT__" in output:
        return "Nao consegui ler a janela do Spotify."
    if not output:
        return "O diagnostico nao encontrou textos visiveis no Spotify."

    return "Diagnostico Spotify:\n" + output


def _shortcut(*vk_codes: int):
    for code in vk_codes:
        user32.keybd_event(code, 0, 0, 0)
        time.sleep(0.02)

    time.sleep(0.04)

    for code in reversed(vk_codes):
        user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)


def _type_text(text: str):
    user32.VkKeyScanW.restype = ctypes.c_short

    for char in text:
        key = user32.VkKeyScanW(ord(char))
        vk_code = key & 0xFF
        shift_state = (key >> 8) & 0xFF

        if vk_code == 0xFF:
            continue

        modifiers = []
        if shift_state & 1:
            modifiers.append(VK_SHIFT)

        for mod in modifiers:
            user32.keybd_event(mod, 0, 0, 0)
            time.sleep(0.01)

        _tap(vk_code)

        for mod in reversed(modifiers):
            user32.keybd_event(mod, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)


def browser_new_tab():
    if _activate_browser_window():
        _shortcut(VK_CONTROL, 0x54)
        return "Abrindo nova aba."

    webbrowser.open("https://www.google.com", new=2)
    return "Abrindo nova aba."


def browser_close_tab():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para fechar a aba."

    _shortcut(VK_CONTROL, VK_W)
    return "Fechando aba."


def browser_next_tab():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para trocar de aba."

    _shortcut(VK_CONTROL, VK_TAB)
    return "Indo para a proxima aba."


def browser_prev_tab():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para trocar de aba."

    _shortcut(VK_CONTROL, VK_SHIFT, VK_TAB)
    return "Voltando para a aba anterior."


def browser_back():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para voltar."

    user32.keybd_event(VK_MENU, 0, 0, 0)
    time.sleep(0.02)
    _tap(VK_LEFT)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    return "Voltando pagina."


def browser_forward():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para avancar."

    user32.keybd_event(VK_MENU, 0, 0, 0)
    time.sleep(0.02)
    _tap(VK_RIGHT)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    return "Avancando pagina."


def browser_refresh():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para atualizar."

    _tap(VK_F5)
    return "Atualizando pagina."


def browser_open_first_result():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para abrir o resultado."

    if _click_first_browser_link():
        return "Abrindo primeiro resultado."

    _tap(VK_TAB)
    time.sleep(0.08)
    _tap(VK_RETURN)
    return "Abrindo primeiro resultado."


def browser_open_focused_item():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para abrir."

    _tap(VK_RETURN)
    return "Abrindo item selecionado."


def browser_click_center():
    rect = _get_browser_window_rect()
    if not rect:
        return "Nao encontrei um navegador aberto para clicar."

    left, top, right, bottom = rect
    _click(left + ((right - left) / 2), top + ((bottom - top) / 2))
    return "Clicando no centro da pagina."


def browser_click_text(query: str):
    if not query:
        return "Clicar em que texto?"

    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para clicar."

    if _click_browser_element_by_text(query):
        return f"Clicando em {query}."

    return f"Nao encontrei {query} visivel na pagina."


def browser_click_listed_item(index: int):
    if index < 1:
        return "Qual item da lista?"

    if _activate_browser_window():
        _refresh_browser_context()

    if index > len(LAST_BROWSER_ELEMENTS):
        browser_describe_screen()

    if index > len(LAST_BROWSER_ELEMENTS):
        return "Li a tela, mas nao encontrei esse item na lista atual."

    item = LAST_BROWSER_ELEMENTS[index - 1]
    if item.get("x") is None or item.get("y") is None:
        if _click_page_item_by_text(item["text"]):
            return f"Tentando abrir o item {index}: {item['text']}."

        query = _short_click_query(item["text"])

        if _click_browser_item_from_text(item["text"]):
            return f"Clicando no item {index}: {item['text']}."

        if query:
            browser_find(query)
            time.sleep(0.12)
            if _click_browser_item_from_text(item["text"]):
                return f"Clicando no item {index}: {item['text']}."
            return (
                f"Encontrei o texto do item {index}, mas nao consegui clicar direto nele. "
                "Deixei ele procurado na pagina."
            )

        return "Tenho esse item em texto, mas nao consegui transformar em clique."

    _click(item["x"], item["y"])
    return f"Clicando no item {index}: {item['text']}."


def browser_describe_listed_item(index: int):
    if index < 1:
        return "Qual item?"

    if _activate_browser_window():
        _refresh_browser_context()

    if index > len(LAST_BROWSER_ELEMENTS):
        return "Ainda nao tenho esse item na lista. Selecione os produtos e diga: ler selecionado."

    item = LAST_BROWSER_ELEMENTS[index - 1]
    return f"Item {index}: {item['text']}."


def _read_selected_text_from_browser():
    if not _activate_browser_window():
        return None

    old_clipboard = _get_clipboard_text()

    try:
        _set_clipboard_text("")
        _shortcut(VK_CONTROL, VK_C)
        time.sleep(0.25)
        selected = _get_clipboard_text()
    finally:
        _set_clipboard_text(old_clipboard)

    return selected


def _compact_selected_text(text: str, max_length: int = 650):
    compacted = re.sub(r"\s+", " ", text or "").strip()
    if len(compacted) > max_length:
        return compacted[:max_length - 3].rstrip() + "..."
    return compacted


def browser_read_selection():
    global LAST_SELECTED_TEXT

    selected = _read_selected_text_from_browser()
    if selected is None:
        return "Nao encontrei um navegador aberto para ler a selecao."

    text = _compact_selected_text(selected)
    if not text:
        _clear_browser_snapshot()
        LAST_SELECTED_TEXT = ""
        return "Nao encontrei texto selecionado."

    _clear_browser_snapshot()
    LAST_SELECTED_TEXT = text
    return "Texto selecionado: " + text


def _translate_with_ollama(text: str, target_language: str = "portugues do Brasil"):
    prompt = f"""
Voce e um tradutor cuidadoso.
Traduza o texto abaixo para {target_language}.
Se o texto ja estiver em portugues, apenas corrija acentos e pequenos erros obvios sem inventar conteudo.
Responda somente com o texto final.
Nao escreva introducoes como "a traducao e".
Nao use aspas.

Texto:
{text}
""".strip()

    return ask_model(
        prompt,
        timeout_seconds=20,
        num_predict=500,
        temperature=0.1,
    ).strip()


def _clean_translation_output(text: str):
    quote_chars = "\"' \u201c\u201d\u2018\u2019"
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = cleaned.strip(quote_chars)

    prefix_patterns = [
        r"^(?:a\s+)?tradu[c\u00e7][a\u00e3]o\s+(?:do\s+texto\s+)?(?:para\s+portugu[e\u00ea]s(?:\s+do\s+brasil)?\s+)?(?:e|\u00e9|eh)\s*:?\s*",
        r"^em\s+portugu[e\u00ea]s(?:\s+do\s+brasil)?\s*:?\s*",
        r"^texto\s+traduzido\s*:?\s*",
        r"^traduzido\s*:?\s*",
    ]

    for pattern in prefix_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned.strip(quote_chars)


def browser_translate_selection():
    global LAST_SELECTED_TEXT

    selected = _read_selected_text_from_browser()
    if selected is None:
        return "Nao encontrei um navegador aberto para traduzir a selecao."

    text = _compact_selected_text(selected, max_length=1800)
    if not text:
        _clear_browser_snapshot()
        return "Nao encontrei texto selecionado para traduzir."

    LAST_SELECTED_TEXT = text

    try:
        translated = _translate_with_ollama(text)
    except Exception:
        return "Nao consegui traduzir agora. Verifique se o Ollama esta aberto."

    translated = _compact_selected_text(_clean_translation_output(translated), max_length=900)
    if not translated:
        return "Nao consegui gerar a traducao."

    _clear_browser_snapshot()
    return "Traduzi: " + translated


def browser_translate_last_selection():
    if not LAST_SELECTED_TEXT:
        return "Ainda nao tenho um texto guardado. Primeiro diga: ler selecionado."

    try:
        translated = _translate_with_ollama(LAST_SELECTED_TEXT)
    except Exception:
        return "Nao consegui traduzir agora. Verifique se o Ollama esta aberto."

    translated = _compact_selected_text(_clean_translation_output(translated), max_length=900)
    if not translated:
        return "Nao consegui gerar a traducao."

    _clear_browser_snapshot()
    return "Traduzi: " + translated


def browser_read_selected_products():
    global LAST_SELECTED_TEXT

    selected = _read_selected_text_from_browser()
    if selected is None:
        return "Nao encontrei um navegador aberto para ler a selecao."

    LAST_SELECTED_TEXT = _compact_selected_text(selected, max_length=1800)
    items = _selected_text_items(selected, limit=10)
    if not items:
        _clear_browser_snapshot()
        return "Nao consegui ler produtos no texto selecionado."

    _remember_text_items(items)
    rows = [f"{idx}. {line}" for idx, line in enumerate(items, start=1)]
    return "Li selecionado: " + "; ".join(rows)


def browser_cheapest_listed_item():
    if _activate_browser_window():
        _refresh_browser_context()

    if not LAST_BROWSER_ELEMENTS:
        browser_describe_screen()

    priced_items = []

    for index, item in enumerate(LAST_BROWSER_ELEMENTS, start=1):
        price = _extract_brl_price(item.get("text", ""))
        if price is None or price <= 0:
            continue

        priced_items.append((price, index, item["text"]))

    if not priced_items:
        return "Ainda nao tenho precos claros na lista atual. Tente dizer: o que tem na tela."

    price, index, text = min(priced_items, key=lambda entry: entry[0])
    return f"O mais barato que encontrei e o item {index}: {text}."


def browser_summarize_screen():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para resumir a tela."

    context = _refresh_browser_context()
    page_url = _get_browser_url()
    page_title = _clean_browser_title(_get_foreground_window_title())
    items = _read_browser_elements(limit=10)
    weak_items = not items or all(_normalize_text_for_match(item["text"]).isdigit() for item in items)

    if weak_items:
        if _browser_context_recently_changed():
            time.sleep(0.35)

        page_lines = _read_page_text_via_clipboard(limit=10)
        best_lines = page_lines
        best_score = _screen_lines_quality(page_lines)

        need_second_pass = _browser_context_recently_changed(2.0) or not page_lines or best_score < 24
        if need_second_pass:
            time.sleep(0.25)
            second_lines = _read_page_text_via_clipboard(limit=10)
            second_score = _screen_lines_quality(second_lines)
            if second_score > best_score:
                best_lines = second_lines
                best_score = second_score

        page_lines = best_lines
        if page_lines:
            _remember_text_items(page_lines, context=context)
            return _screen_summary_intro() + ": " + _summarize_screen_lines(page_lines, page_url=page_url, page_title=page_title)

        _clear_browser_snapshot(context=context)
        return "Nao consegui resumir a tela atual."

    _set_browser_elements(items, context=context)
    lines = [item["text"] for item in items]
    return _screen_summary_intro() + ": " + _summarize_screen_lines(lines, page_url=page_url, page_title=page_title)


def browser_describe_screen():
    global LAST_BROWSER_ELEMENTS

    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para ler a tela."

    context = _refresh_browser_context()
    page_url = _get_browser_url()
    page_title = _clean_browser_title(_get_foreground_window_title())
    items = _read_browser_elements(limit=10)
    weak_items = not items or all(_normalize_text_for_match(item["text"]).isdigit() for item in items)
    if weak_items:
        if _browser_context_recently_changed():
            time.sleep(0.35)

        page_lines = _read_page_text_via_clipboard(limit=10)
        best_lines = page_lines
        best_score = _screen_lines_quality(page_lines)

        need_second_pass = _browser_context_recently_changed(2.0) or not page_lines or best_score < 24
        if need_second_pass:
            time.sleep(0.25)
            second_lines = _read_page_text_via_clipboard(limit=10)
            second_score = _screen_lines_quality(second_lines)
            if second_score > best_score:
                best_lines = second_lines
                best_score = second_score

        page_lines = best_lines
        if page_lines:
            _remember_text_items(page_lines, context=context)
            if _should_auto_summarize(page_lines, best_score, page_url=page_url, page_title=page_title):
                return _screen_summary_intro() + ": " + _summarize_screen_lines(page_lines, page_url=page_url, page_title=page_title)
            rows = [f"{idx}. {line}" for idx, line in enumerate(page_lines, start=1)]
            return _screen_list_intro() + ": " + "; ".join(rows)

        _clear_browser_snapshot(context=context)
        return "Nao consegui ler itens clicaveis visiveis nessa tela."

    _set_browser_elements(items, context=context)
    lines = [item["text"] for item in items]
    if _should_auto_summarize(lines, _screen_lines_quality(lines), page_url=page_url, page_title=page_title):
        return _screen_summary_intro() + ": " + _summarize_screen_lines(lines, page_url=page_url, page_title=page_title)
    rows = [f"{idx}. {item['text']}" for idx, item in enumerate(items, start=1)]
    return "Vejo na tela: " + "; ".join(rows)


def browser_read_more():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para ler mais."

    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -550, 0)
    time.sleep(0.25)
    result = browser_describe_screen()

    if result.startswith("Vejo na tela:"):
        return result.replace("Vejo na tela:", "Mais abaixo vejo:", 1)

    if result.startswith("Consegui ler texto da pagina:"):
        return result.replace("Consegui ler texto da pagina:", "Mais abaixo consegui ler:", 1)

    return result


def browser_zoom_in():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para zoom."

    _shortcut(VK_CONTROL, VK_ADD)
    return "Aumentando zoom."


def browser_zoom_out():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para zoom."

    _shortcut(VK_CONTROL, VK_SUBTRACT)
    return "Diminuindo zoom."


def browser_zoom_reset():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para zoom."

    _shortcut(VK_CONTROL, VK_0)
    return "Restaurando zoom."


def browser_search(query: str):
    if not query:
        return "Qual termo voce quer pesquisar?"

    if not _activate_browser_window():
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}", new=2)
        return f"Pesquisando por {query} em uma nova aba."

    _shortcut(VK_CONTROL, VK_L)
    time.sleep(0.05)
    _type_text(query)
    _tap(VK_RETURN)
    return f"Pesquisando por {query} na aba atual."


def browser_find(query: str):
    if not query:
        return "Qual texto voce quer procurar na pagina?"

    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para procurar na pagina."

    _shortcut(VK_CONTROL, VK_F)
    time.sleep(0.05)
    _type_text(query)
    _tap(VK_RETURN)
    return f"Procurando {query} na pagina."


def browser_scroll_down():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_NEXT)
    return "Rolando para baixo."


def browser_scroll_down_small():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -350, 0)
    return "Descendo um pouco."


def browser_scroll_up():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_PRIOR)
    return "Rolando para cima."


def browser_scroll_up_small():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, 350, 0)
    return "Subindo um pouco."


def browser_scroll_top():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_HOME)
    return "Indo para o topo."


def browser_scroll_bottom():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_END)
    return "Indo para o fim."


def browser_search_site(site: str, query: str):
    if not site or not query:
        return "Qual site e qual pesquisa?"

    site = site.strip()
    query = query.strip()

    if "mercadolivre.com.br" in site:
        webbrowser.open(f"https://lista.mercadolivre.com.br/{quote_plus(query)}")
        return f"Pesquisando {query} no Mercado Livre."

    if "magazineluiza.com.br" in site:
        webbrowser.open(f"https://www.magazineluiza.com.br/busca/{quote_plus(query)}/")
        return f"Pesquisando {query} no Magazine Luiza."

    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query + ' site:' + site)}")
    return f"Pesquisando {query} em {site}."


def browser_search_music(service: str, query: str):
    if not query:
        return "Qual musica voce quer procurar?"

    service = (service or "").lower().strip()

    if service == "spotify":
        try:
            spotify_query = f"{SPOTIFY_TRACK_SEARCH_PREFIX}{query}"
            os.startfile(f"spotify:search:{quote(spotify_query)}")
            time.sleep(2.0)
            focus_app("spotify")
            time.sleep(1.0)

            if _click_spotify_music_filter():
                time.sleep(0.8)

            for _ in range(6):
                if _click_spotify_track_by_name(query):
                    return f"Tentando dar play em {query} no Spotify."
                if _click_spotify_first_visible_track():
                    return f"Tentando dar play em {query} no Spotify."
                time.sleep(0.7)

            return f"Pesquisei {query} no Spotify, mas nao consegui clicar no play."
        except Exception:
            webbrowser.open(f"https://open.spotify.com/search/{quote_plus(query)}")
            return f"Procurando {query} no Spotify."

    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"Procurando {query} no YouTube."
