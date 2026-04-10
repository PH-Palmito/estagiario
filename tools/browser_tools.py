import base64
import ctypes
import subprocess
import time
import webbrowser
from urllib.parse import quote_plus


user32 = ctypes.windll.user32

POWERSHELL_EXE = "powershell"
BROWSER_ACTIVATE_NAMES = ["chrome", "msedge", "firefox", "opera", "brave"]

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_L = 0x4C
VK_W = 0x57

KEYEVENTF_KEYUP = 0x0002


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
    _tap(0x0D)
    return f"Pesquisando por {query} na aba atual."
