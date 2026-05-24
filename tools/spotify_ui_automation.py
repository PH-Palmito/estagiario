from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class SpotifyUiAutomation:
    run_powershell: Callable[..., object]
    click: Callable[..., None]
    set_cursor_pos: Callable[[int, int], object]
    sleep: Callable[[float], None]
    focus_app: Callable[[str], object]

    def click_track_by_name(self, query: str) -> bool:
        words = [word for word in re.sub(r"[^\w\s]", " ", query.lower()).split() if len(word) >= 3]
        ps_words = ", ".join(f"'{word}'" for word in words[:4])
        if not ps_words:
            return False

        script = _SPOTIFY_TRACK_BY_NAME_SCRIPT.replace("__QUERY_WORDS__", ps_words)
        try:
            completed = self.run_powershell(script)
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
        self.set_cursor_pos(x, y)
        self.sleep(0.25)
        self.click(x, y, clicks=clicks)
        return True

    def click_first_visible_track(self) -> bool:
        try:
            completed = self.run_powershell(_SPOTIFY_FIRST_VISIBLE_TRACK_SCRIPT)
        except Exception:
            return False

        output = completed.stdout or ""
        point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)", output)
        if not point_match:
            return False

        x = int(point_match.group(1))
        y = int(point_match.group(2))
        self.set_cursor_pos(x, y)
        self.sleep(0.25)
        self.click(x, y, clicks=2)
        return True

    def diagnostic(self) -> str:
        self.focus_app("spotify")
        self.sleep(0.3)

        try:
            completed = self.run_powershell(_SPOTIFY_DIAGNOSTIC_SCRIPT, timeout_seconds=12)
        except Exception as exc:
            return f"Erro no diagnostico do Spotify: {exc}"

        output = (completed.stdout or "").strip()
        if "__NO_SPOTIFY__" in output:
            return "Nao encontrei uma janela aberta do Spotify."
        if "__NO_ROOT__" in output:
            return "Nao consegui ler a janela do Spotify."
        if not output:
            return "O diagnostico nao encontrou textos visiveis no Spotify."

        return "Diagnostico Spotify:\n" + output


_SPOTIFY_TRACK_BY_NAME_SCRIPT = """
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
            $x = [int]($rect.Left + 90)
            $clicks = 2
        } else {
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


_SPOTIFY_FIRST_VISIBLE_TRACK_SCRIPT = r"""
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


_SPOTIFY_DIAGNOSTIC_SCRIPT = """
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
