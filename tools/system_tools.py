import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

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
        "whatsapp:",
        os.path.join(LOCAL_APPDATA, "Microsoft", "WindowsApps", "WhatsApp.exe"),
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
    "whatsapp": ["WhatsApp.exe"],
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


def _resolve_app_command(candidates):
    for candidate in candidates:
        if not candidate:
            continue

        if isinstance(candidate, str) and candidate.endswith(":"):
            return candidate

        found = shutil.which(candidate)
        if found:
            return found

        if os.path.exists(candidate):
            return candidate

    return None


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
        if isinstance(command, str) and command.endswith(":"):
            os.startfile(command)
            return f"Abrindo {app_name}."

        subprocess.Popen([command])
        return f"Abrindo {app_name}."
    except Exception as e:
        return f"Erro ao executar {app_name}: {e}"


def close_app(app_name: str):
    if not app_name:
        return "Nao consegui identificar qual aplicativo fechar."

    app_name = app_name.lower().strip()
    process_names = APP_PROCESSES.get(app_name)

    if not process_names:
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
