import base64
import difflib
import json
import os
import re
import shutil
import subprocess
import unicodedata
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

APPDATA = os.environ.get("APPDATA", "")
PROGRAMDATA = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", "")

START_MENU_DIRS = [
    Path(APPDATA) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    Path(PROGRAMDATA) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
]

WINDOWS_APPS_DIR = Path(LOCAL_APPDATA) / "Microsoft" / "WindowsApps"
ALIASES_FILE = Path("memory/aliases.json")

SITE_DOMAIN_OVERRIDES = {
    "mercado livre": "https://www.mercadolivre.com.br",
}

NOISE_WORDS = {
    "app",
    "aplicativo",
    "programa",
    "site",
    "pagina",
    "página",
}

EXTRA_TARGET_ALIASES = {
    "github": {"git hub", "github desktop", "e chegar", "chegar"},
    "android studio": {"studio", "android", "and run 2", "androm studio", "android estudar"},
}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _normalize_text(text: str) -> str:
    text = _strip_accents((text or "").strip().lower())
    text = re.sub(r"[^\w\s.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_target(target: str) -> str:
    words = _normalize_text(target).split()

    while words and words[0] in {"o", "a", "os", "as", "um", "uma", "do", "da", "dos", "das", "no", "na"}:
        words = words[1:]

    words = [word for word in words if word not in NOISE_WORDS]
    return " ".join(words).strip(" .")


def _load_aliases():
    if not ALIASES_FILE.exists():
        return {}

    try:
        data = json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _save_aliases(aliases: dict):
    ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALIASES_FILE.write_text(
        json.dumps(aliases, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _find_alias_entry(cleaned: str):
    aliases = _load_aliases()
    normalized_key = _normalize_text(cleaned).strip(" .")

    for key, value in aliases.items():
        if _normalize_text(str(key)).strip(" .") == normalized_key:
            return str(key), value

    return None, None


def _find_typed_alias_entry(cleaned: str, alias_types: set[str], cutoff: float = 0.68):
    aliases = _load_aliases()
    normalized_key = _normalize_text(cleaned).strip(" .")

    existing_key, value = _find_alias_entry(normalized_key)
    if isinstance(value, dict) and value.get("type") in alias_types:
        return existing_key, value

    best_key = None
    best_value = None
    best_score = 0.0

    for key, value in aliases.items():
        if not isinstance(value, dict) or value.get("type") not in alias_types:
            continue

        key_normalized = _normalize_text(str(key)).strip(" .")
        label = value.get("label") if isinstance(value.get("label"), str) else ""
        label_normalized = _normalize_text(label).strip(" .")
        stored_aliases = [
            _normalize_text(alias).strip(" .")
            for alias in value.get("aliases", [])
            if isinstance(alias, str)
        ]
        score = max(
            difflib.SequenceMatcher(None, normalized_key, key_normalized).ratio(),
            difflib.SequenceMatcher(None, normalized_key, label_normalized).ratio() if label_normalized else 0.0,
            *[
                difflib.SequenceMatcher(None, normalized_key, alias).ratio()
                for alias in stored_aliases
            ],
        )

        if normalized_key and (
            normalized_key in key_normalized
            or normalized_key in label_normalized
            or normalized_key in stored_aliases
        ):
            score = max(score, 0.92)

        if score > best_score:
            best_key = str(key)
            best_value = value
            best_score = score

    if best_key and best_score >= cutoff:
        return best_key, best_value

    return None, None


def _run_powershell(script: str, timeout_seconds: int = 10) -> subprocess.CompletedProcess:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return subprocess.run(
        [
            "powershell",
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


def _ps_array(values):
    escaped = []
    for value in values:
        value = str(value or "").strip()
        if value:
            escaped.append("'" + value.replace("'", "''").lower() + "'")
    return "@(" + ", ".join(escaped) + ")"


def _resolve_shortcut_target(path: str):
    if not path or not str(path).lower().endswith(".lnk"):
        return path

    shortcut_path = str(path).replace("'", "''")
    script = f"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut('{shortcut_path}')
Write-Output $shortcut.TargetPath
"""

    try:
        completed = _run_powershell(script, timeout_seconds=5)
    except Exception:
        return path

    resolved = (completed.stdout or "").strip()
    return resolved or path


def _generated_aliases(cleaned: str, label: str):
    aliases = set()
    for text in {cleaned, label}:
        normalized = _normalize_text(text).strip(" .")
        if not normalized:
            continue

        aliases.add(normalized)

        words = [word for word in normalized.split() if len(word) >= 4]
        if len(words) >= 2:
            aliases.add(" ".join(words))
            aliases.add(words[-1])

        if normalized in EXTRA_TARGET_ALIASES:
            aliases.update(EXTRA_TARGET_ALIASES[normalized])

    return sorted(alias for alias in aliases if alias and alias != cleaned)


def _remember_site(cleaned: str, url: str):
    key = _normalize_text(cleaned)
    if not key or not url:
        return

    aliases = _load_aliases()
    existing_key, existing_value = _find_alias_entry(key)

    if existing_value and not (isinstance(existing_value, dict) and existing_value.get("type") in {"site", "smart_site"}):
        return

    aliases[existing_key or key] = {
        "type": "site",
        "target": url,
    }
    _save_aliases(aliases)


def _remember_app(cleaned: str, path: str, label: str):
    key = _normalize_text(cleaned)
    if not key or not path:
        return

    aliases = _load_aliases()
    existing_key, existing_value = _find_alias_entry(key)

    if existing_value and not (isinstance(existing_value, dict) and existing_value.get("type") == "smart_app"):
        return

    aliases[existing_key or key] = {
        "type": "smart_app",
        "target": path,
        "label": label,
        "aliases": _generated_aliases(cleaned, label),
    }
    _save_aliases(aliases)


def _open_remembered_target(cleaned: str):
    _, value = _find_alias_entry(cleaned)
    if not isinstance(value, dict):
        return None

    alias_type = value.get("type")
    target = value.get("target")

    if not isinstance(target, str) or not target.strip():
        return None

    if alias_type in {"site", "smart_site"}:
        webbrowser.open(target)
        return "Abrindo o site."

    if alias_type == "smart_app":
        path = Path(target)
        if not path.exists():
            return None

        os.startfile(path)
        label = value.get("label") if isinstance(value.get("label"), str) else path.stem
        return f"Abrindo {label}."

    if alias_type == "smart_preference":
        if target == "site":
            site_url = _probable_site_url(cleaned, force=True)
            if site_url:
                webbrowser.open(site_url)
                return "Abrindo o site."
            return f"Ainda nao sei qual site usar para {cleaned}."

        if target == "app":
            opened_app = _open_local_candidate(cleaned)
            if opened_app:
                _remember_app(cleaned, opened_app["path"], opened_app["label"])
                return f"Abrindo {opened_app['label']}."
            return f"Ainda nao encontrei o app {cleaned} neste PC."

    return None


def smart_app_exists(target: str):
    cleaned = _clean_target(target)
    if not cleaned:
        return False

    _, value = _find_typed_alias_entry(cleaned, {"smart_app", "smart_preference"})
    return isinstance(value, dict)


def close_smart_target(target: str):
    cleaned = _clean_target(target)
    if not cleaned:
        return None

    _, value = _find_typed_alias_entry(cleaned, {"smart_app"})
    if not isinstance(value, dict):
        return None

    label = value.get("label") if isinstance(value.get("label"), str) else cleaned
    remembered_target = value.get("target") if isinstance(value.get("target"), str) else ""
    resolved_target = _resolve_shortcut_target(remembered_target)
    process_stem = Path(resolved_target).stem if resolved_target else ""

    label_words = [word for word in _normalize_text(label).split() if len(word) >= 3]
    cleaned_words = [word for word in _normalize_text(cleaned).split() if len(word) >= 3]
    process_names = [process_stem]

    # Android Studio commonly runs as studio64.exe/studio.exe even when opened from a .lnk.
    if "android" in cleaned_words and "studio" in cleaned_words:
        process_names.extend(["studio64", "studio"])

    title_queries = [label, cleaned, " ".join(label_words), " ".join(cleaned_words)]
    word_queries = sorted(set(label_words + cleaned_words), key=len, reverse=True)

    script = f"""
$processNames = {_ps_array(process_names)}
$titleQueries = {_ps_array(title_queries)}
$wordQueries = {_ps_array(word_queries)}
$matches = @()

foreach ($process in Get-Process -ErrorAction SilentlyContinue) {{
    try {{
        $processName = ([string]$process.ProcessName).ToLower()
        $title = ([string]$process.MainWindowTitle).ToLower()
        $hasWindow = $process.MainWindowHandle -ne 0
        $matched = $false

        foreach ($name in $processNames) {{
            if ($name -and $processName -eq $name) {{
                $matched = $true
                break
            }}
        }}

        if (-not $matched -and $hasWindow) {{
            foreach ($query in $titleQueries) {{
                if ($query -and $title.Contains($query)) {{
                    $matched = $true
                    break
                }}
            }}
        }}

        if (-not $matched -and $hasWindow -and $wordQueries.Count -gt 0) {{
            $allWordsInTitle = $true
            foreach ($query in $wordQueries) {{
                if (-not $query -or -not $title.Contains($query)) {{
                    $allWordsInTitle = $false
                    break
                }}
            }}
            if ($allWordsInTitle) {{
                $matched = $true
            }}
        }}

        if ($matched) {{
            $matches += $process
        }}
    }} catch {{
    }}
}}

if (-not $matches -or $matches.Count -eq 0) {{
    Write-Output "__NO_PROCESS__"
    return
}}

$requestedClose = $false
foreach ($process in $matches | Sort-Object StartTime -Descending) {{
    try {{
        if ($process.MainWindowHandle -ne 0) {{
            [void]$process.CloseMainWindow()
            $requestedClose = $true
        }}
    }} catch {{
    }}
}}

Start-Sleep -Milliseconds 1800

$stillOpen = @()
foreach ($process in $matches) {{
    try {{
        $fresh = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
        if ($fresh) {{
            $stillOpen += $fresh
        }}
    }} catch {{
    }}
}}

if (-not $stillOpen -or $stillOpen.Count -eq 0) {{
    Write-Output "__OK_GRACEFUL__"
    return
}}

$forced = $false
foreach ($process in $stillOpen) {{
    try {{
        Stop-Process -Id $process.Id -Force -ErrorAction Stop
        $forced = $true
    }} catch {{
    }}
}}

Start-Sleep -Milliseconds 300

$remaining = $false
foreach ($process in $stillOpen) {{
    try {{
        if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {{
            $remaining = $true
            break
        }}
    }} catch {{
    }}
}}

if ($forced -and -not $remaining) {{
    Write-Output "__OK_FORCED__"
}} elseif ($requestedClose) {{
    Write-Output "__REQUESTED_ONLY__"
}} else {{
    Write-Output "__NO_CLOSE__"
}}
"""

    try:
        completed = _run_powershell(script, timeout_seconds=10)
    except Exception:
        return f"Nao consegui fechar {label}."

    output = completed.stdout or ""
    if "__OK_GRACEFUL__" in output or "__OK_FORCED__" in output:
        return f"Fechando {label}."

    if "__REQUESTED_ONLY__" in output:
        return f"Pedi para fechar {label}, mas ele ainda parece aberto."

    if "__NO_PROCESS__" in output:
        return f"O aplicativo '{label}' nao parecia estar aberto."

    return f"Nao consegui fechar {label}."


def smart_window_action(target: str, action: str):
    action = _normalize_text(action)
    if action not in {"focus", "minimize", "maximize", "restore"}:
        return None

    cleaned = _clean_target(target)
    if not cleaned:
        return None

    _, value = _find_typed_alias_entry(cleaned, {"smart_app"})
    if not isinstance(value, dict):
        return None

    label = value.get("label") if isinstance(value.get("label"), str) else cleaned
    remembered_target = value.get("target") if isinstance(value.get("target"), str) else ""
    resolved_target = _resolve_shortcut_target(remembered_target)
    process_stem = Path(resolved_target).stem if resolved_target else ""

    label_words = [word for word in _normalize_text(label).split() if len(word) >= 3]
    cleaned_words = [word for word in _normalize_text(cleaned).split() if len(word) >= 3]
    aliases = [
        alias
        for alias in value.get("aliases", [])
        if isinstance(alias, str) and len(_normalize_text(alias)) >= 4
    ]
    process_names = [process_stem]

    if "android" in cleaned_words and "studio" in cleaned_words:
        process_names.extend(["studio64", "studio"])

    title_queries = [label, cleaned, " ".join(label_words), " ".join(cleaned_words), *aliases]
    word_queries = sorted(set(label_words + cleaned_words), key=len, reverse=True)
    show_codes = {
        "focus": 5,
        "minimize": 6,
        "maximize": 3,
        "restore": 9,
    }
    action_labels = {
        "focus": f"Trocando para {label}.",
        "minimize": f"Minimizando {label}.",
        "maximize": f"Maximizando {label}.",
        "restore": f"Restaurando {label}.",
    }

    script = f"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WinApi {{
    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}}
"@

$processNames = {_ps_array(process_names)}
$titleQueries = {_ps_array(title_queries)}
$wordQueries = {_ps_array(word_queries)}
$matches = @()

foreach ($process in Get-Process -ErrorAction SilentlyContinue) {{
    try {{
        $processName = ([string]$process.ProcessName).ToLower()
        $title = ([string]$process.MainWindowTitle).ToLower()
        $hasWindow = $process.MainWindowHandle -ne 0
        $matched = $false

        foreach ($name in $processNames) {{
            if ($name -and $processName -eq $name) {{
                $matched = $true
                break
            }}
        }}

        if (-not $matched -and $hasWindow) {{
            foreach ($query in $titleQueries) {{
                if ($query -and $title.Contains($query)) {{
                    $matched = $true
                    break
                }}
            }}
        }}

        if (-not $matched -and $hasWindow -and $wordQueries.Count -gt 0) {{
            $allWordsInTitle = $true
            foreach ($query in $wordQueries) {{
                if (-not $query -or -not $title.Contains($query)) {{
                    $allWordsInTitle = $false
                    break
                }}
            }}
            if ($allWordsInTitle) {{
                $matched = $true
            }}
        }}

        if ($matched -and $hasWindow) {{
            $matches += $process
        }}
    }} catch {{
    }}
}}

$process = $matches |
    Sort-Object StartTime -Descending |
    Select-Object -First 1

if (-not $process) {{
    Write-Output "__NO_WINDOW__"
    return
}}

[void][WinApi]::ShowWindowAsync($process.MainWindowHandle, {show_codes[action]})
if ("{action}" -ne "minimize") {{
    [void][WinApi]::SetForegroundWindow($process.MainWindowHandle)
}}
Write-Output "__OK__"
"""

    try:
        completed = _run_powershell(script, timeout_seconds=10)
    except Exception:
        return f"Nao consegui controlar a janela de {label}."

    output = completed.stdout or ""
    if "__OK__" in output:
        return action_labels[action]

    return f"Nao encontrei uma janela aberta de {label}."


def _iter_start_menu_shortcuts():
    for root in START_MENU_DIRS:
        if not root.exists():
            continue

        for suffix in ("*.lnk", "*.url"):
            yield from root.rglob(suffix)


def _score_candidate(query: str, candidate_name: str) -> float:
    query = _normalize_text(query)
    candidate_name = _normalize_text(candidate_name)

    if not query or not candidate_name:
        return 0.0

    if query == candidate_name:
        return 1.0

    if query in candidate_name:
        return 0.92

    if candidate_name in query:
        return 0.86

    return difflib.SequenceMatcher(None, query, candidate_name).ratio()


def _find_start_menu_shortcut(target: str):
    best_path = None
    best_score = 0.0

    for shortcut in _iter_start_menu_shortcuts():
        score = _score_candidate(target, shortcut.stem)
        if score > best_score:
            best_path = shortcut
            best_score = score

    if best_path and best_score >= 0.66:
        return best_path

    return None


def _try_windows_app_alias(target: str):
    compact = re.sub(r"\s+", "", _clean_target(target))
    if not compact:
        return None

    alias = WINDOWS_APPS_DIR / f"{compact}.exe"
    if alias.exists():
        return alias

    return None


def _try_path_executable(target: str):
    cleaned = _clean_target(target)
    compact = re.sub(r"\s+", "", cleaned)

    for candidate in {cleaned, compact, f"{compact}.exe"}:
        if not candidate:
            continue

        found = shutil.which(candidate)
        if found:
            return found

    return None


def _find_local_candidate(target: str):
    executable = _try_path_executable(target)
    if executable:
        return {
            "label": Path(executable).stem,
            "path": str(executable),
        }

    alias = _try_windows_app_alias(target)
    if alias:
        return {
            "label": alias.stem,
            "path": str(alias),
        }

    shortcut = _find_start_menu_shortcut(target)
    if shortcut:
        return {
            "label": shortcut.stem,
            "path": str(shortcut),
        }

    return None


def _open_local_candidate(target: str):
    candidate = _find_local_candidate(target)
    if not candidate:
        return None

    os.startfile(candidate["path"])
    return candidate


def _looks_like_url(target: str) -> bool:
    cleaned = _clean_target(target)
    return "." in cleaned and " " not in cleaned


def _normalize_url(target: str) -> str:
    target = (target or "").strip()
    cleaned = _clean_target(target)
    if target.lower().startswith(("http://", "https://")):
        return target
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    return "https://" + cleaned


def _probable_site_url(target: str, force: bool = False):
    cleaned = _clean_target(target)
    if not cleaned:
        return None

    if _looks_like_url(cleaned):
        return _normalize_url(cleaned)

    override = SITE_DOMAIN_OVERRIDES.get(cleaned)
    if override:
        return override

    words = cleaned.split()
    if len(words) >= 2:
        compact = re.sub(r"[^a-z0-9-]", "", "".join(words))
        if compact:
            return f"https://www.{compact}.com.br"

    if force and len(words) == 1:
        compact = re.sub(r"[^a-z0-9-]", "", cleaned)
        if compact:
            return f"https://www.{compact}.com"

    return None


def smart_open_needs_choice(target: str):
    cleaned = _clean_target(target)
    if not cleaned:
        return False

    _, value = _find_alias_entry(cleaned)
    if isinstance(value, dict):
        return False

    if _looks_like_url(cleaned):
        return False

    return True


def remember_target_kind(target: str, kind: str, open_after: bool = False):
    cleaned = _clean_target(target)
    kind = _normalize_text(kind)

    if not cleaned:
        return "Nao consegui identificar o que lembrar."

    if kind not in {"app", "site"}:
        return "Diga se isso e app ou site."

    aliases = _load_aliases()
    existing_key, existing_value = _find_alias_entry(cleaned)

    if existing_value and isinstance(existing_value, dict) and existing_value.get("type") in {"app", "site", "smart_app", "smart_preference"}:
        key = existing_key or cleaned
    else:
        key = cleaned

    if kind == "site":
        site_url = _probable_site_url(cleaned, force=True)
        if not site_url:
            return f"Nao consegui montar o site para {cleaned}."

        aliases[key] = {
            "type": "site",
            "target": site_url,
        }
        _save_aliases(aliases)

        if open_after:
            webbrowser.open(site_url)
            return "Abrindo o site."
        return f"Lembrei que {cleaned} e site."

    candidate = _find_local_candidate(cleaned)
    if candidate:
        aliases[key] = {
            "type": "smart_app",
            "target": candidate["path"],
            "label": candidate["label"],
            "aliases": _generated_aliases(cleaned, candidate["label"]),
        }
        _save_aliases(aliases)

        if open_after:
            os.startfile(candidate["path"])
            return f"Abrindo {candidate['label']}."
        return f"Lembrei que {cleaned} e app."

    aliases[key] = {
        "type": "smart_preference",
        "target": "app",
    }
    _save_aliases(aliases)
    return f"Lembrei que {cleaned} e app, mas ainda nao encontrei ele instalado."


def forget_smart_memory(target: str):
    cleaned = _clean_target(target)
    if not cleaned:
        return "Nao consegui identificar o que esquecer."

    aliases = _load_aliases()
    existing_key, value = _find_alias_entry(cleaned)

    if not existing_key:
        return f"Nao achei memoria para {cleaned}."

    if isinstance(value, dict) and value.get("type") in {"app", "site", "smart_app", "smart_preference"}:
        aliases.pop(existing_key, None)
        _save_aliases(aliases)
        return f"Esqueci {cleaned}."

    return f"{cleaned} existe na memoria, mas nao e um app ou site aprendido."


def list_smart_memory():
    aliases = _load_aliases()
    items = []

    for key, value in aliases.items():
        if not isinstance(value, dict):
            continue

        alias_type = value.get("type")
        if alias_type == "site":
            items.append(f"{key}: site")
        elif alias_type in {"app", "smart_app"}:
            items.append(f"{key}: app")
        elif alias_type == "smart_preference":
            items.append(f"{key}: {value.get('target')}")

    if not items:
        return "Ainda nao tenho apps ou sites aprendidos."

    return "Memoria: " + ", ".join(items)


def open_smart_target_as_kind(target: str, kind: str):
    return remember_target_kind(target, kind, open_after=True)


def open_smart_target(target: str):
    cleaned = _clean_target(target)
    if not cleaned:
        return "Nao consegui identificar o que abrir."

    remembered = _open_remembered_target(cleaned)
    if remembered:
        return remembered

    opened_app = _open_local_candidate(cleaned)
    if opened_app:
        _remember_app(cleaned, opened_app["path"], opened_app["label"])
        return f"Abrindo {opened_app['label']}."

    site_url = _probable_site_url(target)
    if site_url:
        webbrowser.open(site_url)
        _remember_site(cleaned, site_url)
        return "Abrindo o site."

    query = quote_plus(cleaned)
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Pesquisando {cleaned} no Google."
