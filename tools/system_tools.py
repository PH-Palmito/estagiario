import os
import shutil
import subprocess
import sys
import webbrowser
import ctypes
import time
from pathlib import Path
from urllib.parse import urlparse
from tools.clipboard_tools import get_clipboard, set_clipboard

user32 = ctypes.windll.user32
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56

SAFE_DIR = Path.cwd() / "scripts"

PROGRAM_FILES = os.environ.get("ProgramFiles", r"C:\Program Files")
PROGRAM_FILES_X86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", "")
APPDATA = os.environ.get("APPDATA", "")

ALLOWED_APPS = {
    "bloco de notas": ["notepad.exe"],
    "calculadora": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "edge": [
        "msedge.exe",
        os.path.join(PROGRAM_FILES, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(PROGRAM_FILES_X86, "Microsoft", "Edge", "Application", "msedge.exe"),
    ],
    "chrome": [
        "chrome.exe",
        os.path.join(LOCAL_APPDATA, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(PROGRAM_FILES, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(PROGRAM_FILES_X86, "Google", "Chrome", "Application", "chrome.exe"),
    ],
    "code": [
        "code",
        "Code.exe",
        os.path.join(LOCAL_APPDATA, "Programs", "Microsoft VS Code", "Code.exe"),
        os.path.join(PROGRAM_FILES, "Microsoft VS Code", "Code.exe"),
        os.path.join(PROGRAM_FILES_X86, "Microsoft VS Code", "Code.exe"),
    ],
    "spotify": [
        "spotify.exe",
        os.path.join(APPDATA, "Spotify", "Spotify.exe"),
        os.path.join(LOCAL_APPDATA, "Microsoft", "WindowsApps", "Spotify.exe"),
    ],
    "whatsapp": [
        "WhatsApp.exe",
        os.path.join(LOCAL_APPDATA, "Microsoft", "WindowsApps", "WhatsApp.exe"),
        r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
        "whatsapp:",
    ],
}

APP_PROCESSES = {
    "bloco de notas": ["notepad.exe"],
    "notas": ["notepad.exe"],
    "calculadora": ["CalculatorApp.exe", "calc.exe"],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe", "WindowsTerminal.exe"],
    "powershell": ["powershell.exe", "pwsh.exe", "WindowsTerminal.exe"],
    "edge": ["msedge.exe"],
    "chrome": ["chrome.exe"],
    "code": ["Code.exe"],
    "vscode": ["Code.exe"],
    "spotify": ["Spotify.exe"],
    "whatsapp": ["WhatsApp.exe", "WhatsApp.Root.exe"],
}

FRIENDLY_URLS = {
    "www.youtube.com": "YouTube",
    "youtube.com": "YouTube",
    "www.google.com": "Google",
    "google.com": "Google",
    "mail.google.com": "Gmail",
    "web.whatsapp.com": "WhatsApp",
    "chat.openai.com": "ChatGPT",
}

WINDOW_ACTIONS = {
    "focus": 5,
    "minimize": 6,
    "maximize": 3,
    "restore": 9,
}


def _tap(vk_code: int):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _shortcut(*vk_codes: int):
    for code in vk_codes:
        user32.keybd_event(code, 0, 0, 0)
        time.sleep(0.01)

    time.sleep(0.03)

    for code in reversed(vk_codes):
        user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)


def _resolve_app_command(candidates):
    for candidate in candidates:
        if not candidate:
            continue

        if isinstance(candidate, str) and (candidate.endswith(":") or candidate.startswith("shell:")):
            return candidate

        found = shutil.which(candidate)
        if found:
            return found

        if os.path.exists(candidate):
            return candidate

    return None


def _run_window_action(app_name: str, action: str):
    process_names = APP_PROCESSES.get(app_name)

    if not process_names:
        try:
            from tools.smart_open_tools import smart_window_action

            smart_result = smart_window_action(app_name, action)
            if smart_result:
                return smart_result
        except Exception:
            pass

        return f"Aplicativo '{app_name}' nao permitido para janela."

    ps_process_names = ", ".join(f"'{Path(name).stem}'" for name in process_names)
    show_code = WINDOW_ACTIONS[action]
    action_labels = {
        "focus": f"Trocando para {app_name}.",
        "minimize": f"Minimizando {app_name}.",
        "maximize": f"Maximizando {app_name}.",
        "restore": f"Restaurando {app_name}.",
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

$processNames = @({ps_process_names})
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
    Write-Output "__NO_WINDOW__"
    return
}}

[void][WinApi]::ShowWindowAsync($process.MainWindowHandle, {show_code})
[void][WinApi]::SetForegroundWindow($process.MainWindowHandle)
Write-Output "__OK__"
"""

    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output = (result.stdout or "").strip()
    if "__OK__" in output:
        return action_labels[action]

    return f"Nao encontrei uma janela aberta de {app_name}."


def open_app(app_name: str):
    if not app_name:
        return "Nao consegui identificar qual aplicativo abrir."

    app_name = app_name.lower().strip()
    candidates = ALLOWED_APPS.get(app_name)

    if not candidates:
        return f"Aplicativo '{app_name}' nao permitido."

    command = _resolve_app_command(candidates)
    if not command:
        return f"Aplicativo '{app_name}' nao encontrado neste PC."

    try:
        if isinstance(command, str) and (command.endswith(":") or command.startswith("shell:")):
            os.startfile(command)
            return f"Abrindo {app_name}."

        subprocess.Popen([command])
        return f"Abrindo {app_name}."
    except Exception as e:
        return f"Erro ao executar {app_name}: {e}"


def focus_app(app_name: str):
    if not app_name:
        return "Nao consegui identificar qual aplicativo focar."

    return _run_window_action(app_name.lower().strip(), "focus")


def minimize_app(app_name: str):
    if not app_name:
        return "Nao consegui identificar qual aplicativo minimizar."

    return _run_window_action(app_name.lower().strip(), "minimize")


def maximize_app(app_name: str):
    if not app_name:
        return "Nao consegui identificar qual aplicativo maximizar."

    return _run_window_action(app_name.lower().strip(), "maximize")


def restore_app(app_name: str):
    if not app_name:
        return "Nao consegui identificar qual aplicativo restaurar."

    return _run_window_action(app_name.lower().strip(), "restore")


def type_text(text: str):
    content = (text or "").strip()
    if not content:
        return "Qual texto devo inserir?"

    previous_clipboard = get_clipboard()
    try:
        set_clipboard(content)
        time.sleep(0.04)
        _shortcut(VK_CONTROL, VK_V)
        time.sleep(0.05)
    except Exception as e:
        return f"Erro ao inserir texto: {e}"
    finally:
        try:
            if previous_clipboard is not None:
                set_clipboard(previous_clipboard)
        except Exception:
            pass

    return "Texto inserido no campo ativo."


def _close_processes_with_powershell(process_names: list[str]) -> bool:
    ps_process_names = ", ".join(f"'{Path(name).stem}'" for name in process_names)
    script = f"""
$processNames = @({ps_process_names})
$closed = $false

foreach ($name in $processNames) {{
    $processes = Get-Process -Name $name -ErrorAction SilentlyContinue
    foreach ($process in $processes) {{
        try {{
            Stop-Process -Id $process.Id -Force -ErrorAction Stop
            $closed = $true
        }} catch {{
        }}
    }}
}}

if ($closed) {{
    Write-Output "__OK__"
}} else {{
    Write-Output "__NO_PROCESS__"
}}
"""

    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return result.returncode == 0 and "__OK__" in (result.stdout or "")


def close_app(app_name: str):
    if not app_name:
        return "Nao consegui identificar qual aplicativo fechar."

    app_name = app_name.lower().strip()
    process_names = APP_PROCESSES.get(app_name)

    if not process_names:
        try:
            from tools.smart_open_tools import close_smart_target

            smart_result = close_smart_target(app_name)
            if smart_result:
                return smart_result
        except Exception:
            pass

        return f"Aplicativo '{app_name}' nao permitido para fechamento."

    for process_name in process_names:
        result = subprocess.run(
            ["taskkill", "/IM", process_name, "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return f"Fechando {app_name}."

    if _close_processes_with_powershell(process_names):
        return f"Fechando {app_name}."

    return f"O aplicativo '{app_name}' nao parecia estar aberto."


def run_script(script_name: str):
    if not script_name:
        return "Nome do script nao informado."

    script_name = script_name.strip()
    script_path = (SAFE_DIR / script_name).resolve()
    safe_root = SAFE_DIR.resolve()

    if not script_path.exists():
        return "Script nao encontrado."

    if safe_root not in script_path.parents:
        return "Acesso negado."

    if script_path.suffix.lower() != ".py":
        return "So e permitido executar scripts Python (.py)."

    try:
        subprocess.Popen(
            [sys.executable, str(script_path)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return f"Executando {script_name}."
    except Exception as e:
        return f"Erro ao executar script: {e}"


def open_url(url: str):
    try:
        webbrowser.open(url)
        host = urlparse(url).netloc.lower()
        friendly_name = FRIENDLY_URLS.get(host)

        if friendly_name:
            return f"Abrindo {friendly_name}."

        return "Abrindo o site."
    except Exception as e:
        return f"Erro ao abrir URL: {e}"
