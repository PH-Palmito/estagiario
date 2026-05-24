from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass


def normalize_ui_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_point_output(output: str):
    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)", output or "")
    if not point_match:
        return None
    return int(point_match.group(1)), int(point_match.group(2))


def parse_browser_items_output(output: str, limit: int = 10):
    if "__NO_BROWSER__" in (output or "") or "__NO_ROOT__" in (output or ""):
        return None

    items = []
    for line in (output or "").splitlines():
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


@dataclass
class BrowserUiAutomation:
    browser_names: list[str]
    run_powershell: Callable[..., object]
    click: Callable[[int, int], None]

    def click_first_browser_link(self) -> bool:
        script = _FIRST_BROWSER_LINK_SCRIPT.replace("__PROCESS_NAMES__", _ps_string_array(self.browser_names))
        try:
            completed = self.run_powershell(script, timeout_seconds=8)
        except Exception:
            return False

        point = parse_point_output(completed.stdout or "")
        if not point:
            return False

        self.click(point[0], point[1])
        return True

    def click_browser_element_by_text(self, query: str, app_names=None) -> bool:
        query_words = [word for word in normalize_ui_text(query).split() if len(word) >= 2][:5]
        if not query_words:
            return False

        script = (
            _CLICK_BROWSER_ELEMENT_SCRIPT
            .replace("__PROCESS_NAMES__", _ps_string_array(app_names or self.browser_names))
            .replace("__QUERY_WORDS__", _ps_string_array(query_words))
        )
        try:
            completed = self.run_powershell(script, timeout_seconds=8)
        except Exception:
            return False

        point = parse_point_output(completed.stdout or "")
        if not point:
            return False

        self.click(point[0], point[1])
        return True

    def read_browser_elements(self, limit: int = 10):
        script = _READ_BROWSER_ELEMENTS_SCRIPT.replace("__PROCESS_NAMES__", _ps_string_array(self.browser_names))
        try:
            completed = self.run_powershell(script, timeout_seconds=8)
        except Exception:
            return None

        return parse_browser_items_output(completed.stdout or "", limit=limit)


def _ps_string_array(values) -> str:
    return ", ".join(f"'{str(value).replace(chr(39), chr(39) + chr(39))}'" for value in values or [])


_FIRST_BROWSER_LINK_SCRIPT = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @(__PROCESS_NAMES__)
$process = $null

foreach ($name in $processNames) {
    $process = Get-Process -Name $name -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime -Descending |
        Select-Object -First 1

    if ($process) {
        break
    }
}

if (-not $process) {
    Write-Output "__NO_BROWSER__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 3) {
            continue
        }

        if ($rect.IsEmpty -or $rect.Width -lt 40 -or $rect.Height -lt 10) {
            continue
        }

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 135 -or $relativeLeft -lt 80) {
            continue
        }

        if ($controlType -notmatch "Hyperlink|Button|ListItem|DataItem") {
            continue
        }

        if ($name -match "^(voltar|avancar|recarregar|favoritos|perfil|mais|menu|google apps|entrar)$") {
            continue
        }

        $score = 1000 - $relativeTop
        if ($controlType -match "Hyperlink") {
            $score += 200
        }

        $candidates += [pscustomobject]@{
            Top = $rect.Top
            Left = $rect.Left
            Score = $score
            X = [int]($rect.Left + [Math]::Min(160, [Math]::Max(20, $rect.Width / 2)))
            Y = [int]($rect.Top + ($rect.Height / 2))
        }
    } catch {
    }
}

$candidate = $candidates |
    Sort-Object -Property @{ Expression = "Score"; Descending = $true }, @{ Expression = "Top"; Descending = $false }, @{ Expression = "Left"; Descending = $false } |
    Select-Object -First 1

if (-not $candidate) {
    Write-Output "__NO_LINK__"
    return
}

Write-Output ("__POINT__:{0},{1}" -f $candidate.X, $candidate.Y)
"""


_CLICK_BROWSER_ELEMENT_SCRIPT = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @(__PROCESS_NAMES__)
$queryWords = @(__QUERY_WORDS__)
$process = $null

foreach ($name in $processNames) {
    $process = Get-Process -Name $name -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime -Descending |
        Select-Object -First 1

    if ($process) {
        break
    }
}

if (-not $process) {
    Write-Output "__NO_BROWSER__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 2) {
            continue
        }

        if ($rect.IsEmpty -or $rect.Width -lt 12 -or $rect.Height -lt 8) {
            continue
        }

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 85 -or $relativeLeft -lt 5) {
            continue
        }

        $normalizedName = $name.ToLower() -replace "[^\\p{L}\\p{Nd}\\s]", " "
        $normalizedName = $normalizedName -replace "\\s+", " "

        $matches = 0
        foreach ($word in $queryWords) {
            if ($normalizedName.Contains($word)) {
                $matches += 1
            }
        }

        if ($matches -le 0) {
            continue
        }

        $score = $matches * 100
        if ($controlType -match "Button|Hyperlink|ListItem|DataItem") {
            $score += 80
        }
        if ($matches -eq $queryWords.Count) {
            $score += 120
        }

        $score += [Math]::Max(0, 500 - [int]$relativeTop)

        $candidates += [pscustomobject]@{
            Score = $score
            Top = $rect.Top
            Left = $rect.Left
            X = [int]($rect.Left + [Math]::Min([Math]::Max($rect.Width / 2, 12), 180))
            Y = [int]($rect.Top + ($rect.Height / 2))
        }
    } catch {
    }
}

$candidate = $candidates |
    Sort-Object -Property @{ Expression = "Score"; Descending = $true }, @{ Expression = "Top"; Descending = $false }, @{ Expression = "Left"; Descending = $false } |
    Select-Object -First 1

if (-not $candidate) {
    Write-Output "__NO_MATCH__"
    return
}

Write-Output ("__POINT__:{0},{1}" -f $candidate.X, $candidate.Y)
"""


_READ_BROWSER_ELEMENTS_SCRIPT = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @(__PROCESS_NAMES__)
$process = $null

foreach ($name in $processNames) {
    $process = Get-Process -Name $name -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime -Descending |
        Select-Object -First 1

    if ($process) {
        break
    }
}

if (-not $process) {
    Write-Output "__NO_BROWSER__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$rows = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 3) {
            continue
        }

        if ($rect.IsEmpty -or $rect.Width -lt 20 -or $rect.Height -lt 8) {
            continue
        }

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 90 -or $relativeLeft -lt 5) {
            continue
        }

        if ($controlType -notmatch "Button|Hyperlink|ListItem|DataItem|Text|Edit|ComboBox") {
            continue
        }

        if ($name -match "^(voltar|avancar|recarregar|favoritos|perfil|mais|menu|google apps)$") {
            continue
        }

        $safeName = ($name -replace "\\s+", " ").Trim()
        if ($safeName.Length -gt 90) {
            $safeName = $safeName.Substring(0, 90)
        }

        $score = 1000 - [int]$relativeTop
        if ($controlType -match "Button|Hyperlink") {
            $score += 150
        }

        $rows += [pscustomobject]@{
            Score = $score
            Top = [int]$rect.Top
            Left = [int]$rect.Left
            Text = ("__ITEM__|{0}|{1}|{2}|{3}" -f $safeName.Replace("|", " "), [int]($rect.Left + ($rect.Width / 2)), [int]($rect.Top + ($rect.Height / 2)), $controlType)
        }
    } catch {
    }
}

$seen = @{}
$rows |
    Sort-Object -Property @{ Expression = "Top"; Descending = $false }, @{ Expression = "Left"; Descending = $false } |
    ForEach-Object {
        $name = ($_.Text -split "\\|")[1]
        $key = $name.ToLower()
        if (-not $seen.ContainsKey($key)) {
            $seen[$key] = $true
            Write-Output $_.Text
        }
    }
"""
