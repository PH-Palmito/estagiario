import ctypes
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from core.startup_diagnostics import startup_log_path
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
STARTUP_ENTRY_NAME = "Axel Assistant.cmd"

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


def _focused_text_target_available() -> bool:
    script = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$focused = [System.Windows.Automation.AutomationElement]::FocusedElement
if (-not $focused) {
    Write-Output "__NO__"
    return
}

$controlType = ""
try {
    $controlType = $focused.Current.ControlType.ProgrammaticName
} catch {
}

$name = ""
try {
    $name = $focused.Current.Name
} catch {
}

$isKeyboardFocusable = $false
try {
    $isKeyboardFocusable = $focused.Current.IsKeyboardFocusable
} catch {
}

if (
    $controlType -match 'Edit|Document'
    -or $name -match 'edit|editor|message|mensagem|texto|text'
) {
    Write-Output "__YES__"
    return
}

if ($isKeyboardFocusable -and $controlType -match 'Pane') {
    Write-Output "__MAYBE__"
    return
}

Write-Output "__NO__"
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
        )
        output = (result.stdout or "").strip()
        return "__YES__" in output or "__MAYBE__" in output
    except Exception:
        return True


def _ensure_text_target() -> bool:
    if _focused_text_target_available():
        return True

    open_app("bloco de notas")
    time.sleep(0.45)
    return _focused_text_target_available()


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
    content = "" if text is None else str(text)
    if not content:
        return "Qual texto devo inserir?"
    if not content.strip() and content not in {"\n", "\r\n", "\n\n", "\r\n\r\n", "\t"}:
        return "Qual texto devo inserir?"

    if not _ensure_text_target():
        return "Nao encontrei um campo de texto ativo."

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


def _startup_folder() -> Path | None:
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _startup_entry_path() -> Path | None:
    folder = _startup_folder()
    if folder is None:
        return None
    return folder / STARTUP_ENTRY_NAME


def _quote_cmd_arg(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _startup_command_args() -> list[str]:
    repo_dir = Path(__file__).resolve().parents[1]
    main_py = repo_dir / "main.py"
    return [
        str(sys.executable),
        str(main_py),
        "--voice",
        "--hotword",
        "--ui",
        "--startup",
    ]


def _startup_log_path() -> Path:
    return startup_log_path(Path(__file__).resolve().parents[1])


def _startup_output_log_path() -> Path:
    return _startup_log_path().with_name("axel-startup-output.log")


def _read_startup_tail(path: Path, limit: int = 12) -> list[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, int(limit)) :]
    except Exception:
        return []


def _startup_recent_errors() -> list[str]:
    markers = ("Falha fatal", "Traceback", "PermissionError", "Error:", "Exception")
    lines = _read_startup_tail(_startup_log_path()) + _read_startup_tail(_startup_output_log_path())
    return [line for line in lines if any(marker in line for marker in markers)][-3:]


def _startup_entry_content() -> str:
    repo_dir = Path(__file__).resolve().parents[1]
    log_path = _startup_log_path()
    output_log_path = _startup_output_log_path()
    command = " ".join(_quote_cmd_arg(arg) for arg in _startup_command_args())
    runner = f"{command} >> {_quote_cmd_arg(str(output_log_path))} 2>&1"
    return (
        "@echo off\n"
        f"cd /d {_quote_cmd_arg(str(repo_dir))}\n"
        f"if not exist {_quote_cmd_arg(str(log_path.parent))} mkdir {_quote_cmd_arg(str(log_path.parent))}\n"
        f"echo [%date% %time%] Iniciando Axel pelo Windows Startup >> {_quote_cmd_arg(str(log_path))}\n"
        f"echo [%date% %time%] Saida do processo Axel >> {_quote_cmd_arg(str(output_log_path))}\n"
        f"start \"Axel\" /min cmd /d /c {_quote_cmd_arg(runner)}\n"
    )


def windows_startup_diagnostics() -> dict:
    entry_path = _startup_entry_path()
    expected_content = _startup_entry_content()
    log_path = _startup_log_path()
    output_log_path = _startup_output_log_path()
    if entry_path is None:
        return {
            "available": False,
            "enabled": False,
            "current": False,
            "outdated": False,
            "entry_path": "",
            "expected_command": " ".join(_quote_cmd_arg(arg) for arg in _startup_command_args()),
            "log_path": str(log_path),
            "output_log_path": str(output_log_path),
            "diagnostic_log_exists": log_path.exists(),
            "output_log_exists": output_log_path.exists(),
            "recent_errors": _startup_recent_errors(),
            "reason": "appdata_missing",
        }

    result = {
        "available": True,
        "enabled": entry_path.exists(),
        "current": False,
        "outdated": False,
        "entry_path": str(entry_path),
        "expected_command": " ".join(_quote_cmd_arg(arg) for arg in _startup_command_args()),
        "log_path": str(log_path),
        "output_log_path": str(output_log_path),
        "diagnostic_log_exists": log_path.exists(),
        "output_log_exists": output_log_path.exists(),
        "recent_errors": _startup_recent_errors(),
        "reason": "",
    }
    if not entry_path.exists():
        return result

    try:
        content = entry_path.read_text(encoding="utf-8")
    except Exception as exc:
        result.update({"reason": f"read_failed:{exc}", "outdated": True})
        return result

    result["current"] = content == expected_content
    result["outdated"] = not result["current"]
    if result["outdated"]:
        result["reason"] = "content_mismatch"
    return result


def enable_windows_startup() -> str:
    entry_path = _startup_entry_path()
    if entry_path is None:
        return "Nao encontrei a pasta de inicializacao do Windows neste ambiente."

    try:
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.write_text(_startup_entry_content(), encoding="utf-8")
    except Exception as e:
        return f"Nao consegui ativar a inicializacao com o Windows: {e}"

    return (
        "Inicializacao com o Windows ativada. Vou abrir em modo voz, hotword e painel. "
        f"Log: {_startup_log_path()}"
    )


def disable_windows_startup() -> str:
    entry_path = _startup_entry_path()
    if entry_path is None:
        return "Nao encontrei a pasta de inicializacao do Windows neste ambiente."

    try:
        if entry_path.exists():
            entry_path.unlink()
            return "Inicializacao com o Windows desativada."
    except Exception as e:
        return f"Nao consegui desativar a inicializacao com o Windows: {e}"

    return "A inicializacao com o Windows ja estava desativada."


def windows_startup_status() -> str:
    diagnostics = windows_startup_diagnostics()
    if not diagnostics.get("available"):
        return "Nao encontrei a pasta de inicializacao do Windows neste ambiente."
    if not diagnostics.get("enabled"):
        return "Inicializacao com o Windows esta desativada."

    if diagnostics.get("outdated"):
        return (
            "Alerta: inicializacao com o Windows esta ativada, mas o atalho esta desatualizado. "
            f"Atalho atual: {diagnostics.get('entry_path')}. "
            "Recrie com: python main.py --install-startup. "
            f"Comando esperado inclui: {diagnostics.get('expected_command')}. "
            f"Motivo: {diagnostics.get('reason') or 'conteudo diferente'}."
        )

    log_status = "log encontrado" if diagnostics.get("diagnostic_log_exists") else "log ainda nao encontrado"
    output_status = "saida encontrada" if diagnostics.get("output_log_exists") else "saida ainda nao encontrada"
    errors = diagnostics.get("recent_errors") or []
    if errors:
        return (
            "Inicializacao com o Windows esta ativada, mas ha alerta recente no startup. "
            f"Ultimo erro: {errors[-1]}. Log: {diagnostics.get('log_path')}"
        )
    return (
        "Inicializacao com o Windows esta ativada e o atalho esta atualizado. "
        f"Diagnostico: {log_status}; {output_status}. Log: {diagnostics.get('log_path')}"
    )
