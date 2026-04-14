import base64
import ctypes
import os
import re
import subprocess
import time
import webbrowser
from urllib.parse import quote, quote_plus

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
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_L = 0x4C
VK_W = 0x57
VK_F = 0x46
VK_RETURN = 0x0D
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_SPACE = 0x20

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SPOTIFY_TRACK_SEARCH_PREFIX = "track:"
SPOTIFY_TRACK_RESULT_CLICKS = (
    (0.52, 0.45),
    (0.49, 0.50),
    (0.56, 0.52),
)


def _run_powershell(script: str, timeout_seconds: int = 10) -> subprocess.CompletedProcess:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
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


def browser_scroll_up():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_PRIOR)
    return "Rolando para cima."


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
