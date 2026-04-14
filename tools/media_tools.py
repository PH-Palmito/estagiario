import base64
import ctypes
import subprocess
import time

from tools.system_tools import focus_app, open_app


user32 = ctypes.windll.user32

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_SHIFT = 0x10
VK_K = 0x4B
VK_N = 0x4E
VK_P = 0x50

MEDIA_TARGET_APP = {
    "spotify": "spotify",
    "youtube": "chrome",
    "google": "chrome",
    "chrome": "chrome",
    "navegador": "chrome",
}

MEDIA_TARGET_HINTS = {
    "spotify": ["spotify"],
    "youtube": ["chrome", "msedge", "firefox", "brave"],
    "google": ["chrome", "msedge", "firefox", "brave"],
    "chrome": ["chrome"],
    "navegador": ["chrome", "msedge", "firefox", "brave"],
}


def _run_powershell(script: str, timeout_seconds: int = 8) -> subprocess.CompletedProcess:
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


def _targeted_media_session(target: str, action: str) -> bool:
    hints = MEDIA_TARGET_HINTS.get((target or "").lower().strip())
    if not hints:
        return False

    ps_hints = ", ".join(f"'{hint}'" for hint in hints)
    script = f"""
$ErrorActionPreference = "Stop"
try {{
    $null = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType = WindowsRuntime]
    $manager = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync().GetAwaiter().GetResult()
    $targetHints = @({ps_hints})
    $action = "{action}"

    foreach ($session in $manager.GetSessions()) {{
        $source = ([string]$session.SourceAppUserModelId).ToLower()

        foreach ($hint in $targetHints) {{
            if ($source.Contains($hint)) {{
                if ($action -eq "play") {{
                    [void]$session.TryPlayAsync().GetAwaiter().GetResult()
                }} elseif ($action -eq "pause") {{
                    [void]$session.TryPauseAsync().GetAwaiter().GetResult()
                }} elseif ($action -eq "next") {{
                    [void]$session.TrySkipNextAsync().GetAwaiter().GetResult()
                }} elseif ($action -eq "previous") {{
                    [void]$session.TrySkipPreviousAsync().GetAwaiter().GetResult()
                }} else {{
                    [void]$session.TryTogglePlayPauseAsync().GetAwaiter().GetResult()
                }}

                Write-Output "__OK__"
                return
            }}
        }}
    }}

    Write-Output "__NO_SESSION__"
}} catch {{
    Write-Output ("__ERROR__:" + $_.Exception.Message)
}}
"""

    try:
        completed = _run_powershell(script)
    except Exception:
        return False

    return completed.returncode == 0 and "__OK__" in (completed.stdout or "")


def _tap(vk_code: int, times: int = 1):
    for _ in range(max(1, times)):
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        time.sleep(0.02)
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)


def _shortcut(*vk_codes: int):
    for code in vk_codes:
        user32.keybd_event(code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        time.sleep(0.02)

    time.sleep(0.04)

    for code in reversed(vk_codes):
        user32.keybd_event(code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)


def media_play_pause():
    _tap(VK_MEDIA_PLAY_PAUSE)
    return "Pausando ou continuando midia."


def media_next():
    _tap(VK_MEDIA_NEXT_TRACK)
    return "Proxima midia."


def media_previous():
    _tap(VK_MEDIA_PREV_TRACK)
    return "Midia anterior."


def _focus_media_target(target: str):
    app = MEDIA_TARGET_APP.get((target or "").lower().strip())
    if not app:
        return f"Alvo de midia '{target}' nao reconhecido."

    result = focus_app(app)
    if result.startswith("Nao encontrei"):
        if app == "spotify":
            open_app("spotify")
            time.sleep(1.0)
            result = focus_app(app)

    if result.startswith("Nao encontrei"):
        return result

    time.sleep(0.15)
    return None


def _is_browser_media_target(target: str) -> bool:
    return (target or "").lower().strip() in {"youtube", "google", "chrome", "navegador"}


def _browser_media_action(target: str, action: str):
    error = _focus_media_target(target)
    if error:
        return error

    if action in {"toggle", "play", "pause"}:
        _tap(VK_K)
        return f"Alternando {target}."

    if action == "next":
        _shortcut(VK_SHIFT, VK_N)
        return f"Proxima midia em {target}."

    if action == "previous":
        _shortcut(VK_SHIFT, VK_P)
        return f"Midia anterior em {target}."

    return f"Comando de midia desconhecido para {target}."


def media_play_pause_target(target: str):
    if _targeted_media_session(target, "toggle"):
        return f"Pausando ou continuando {target}."

    if _is_browser_media_target(target):
        return _browser_media_action(target, "toggle")

    error = _focus_media_target(target)
    if error:
        return error

    _tap(VK_MEDIA_PLAY_PAUSE)
    return f"Pausando ou continuando {target}."


def media_play_target(target: str):
    if _targeted_media_session(target, "play"):
        return f"Tocando {target}."

    if _is_browser_media_target(target):
        return _browser_media_action(target, "play")

    error = _focus_media_target(target)
    if error:
        return error

    _tap(VK_MEDIA_PLAY_PAUSE)
    return f"Tocando {target}."


def media_pause_target(target: str):
    if _targeted_media_session(target, "pause"):
        return f"Pausando {target}."

    if _is_browser_media_target(target):
        return _browser_media_action(target, "pause")

    error = _focus_media_target(target)
    if error:
        return error

    _tap(VK_MEDIA_PLAY_PAUSE)
    return f"Pausando {target}."


def media_next_target(target: str):
    if _targeted_media_session(target, "next"):
        return f"Proxima midia em {target}."

    if _is_browser_media_target(target):
        return _browser_media_action(target, "next")

    error = _focus_media_target(target)
    if error:
        return error

    _tap(VK_MEDIA_NEXT_TRACK)
    return f"Proxima midia em {target}."


def media_previous_target(target: str):
    if _targeted_media_session(target, "previous"):
        return f"Midia anterior em {target}."

    if _is_browser_media_target(target):
        return _browser_media_action(target, "previous")

    error = _focus_media_target(target)
    if error:
        return error

    _tap(VK_MEDIA_PREV_TRACK)
    return f"Midia anterior em {target}."


def volume_up():
    _tap(VK_VOLUME_UP, times=3)
    return "Aumentando volume."


def volume_down():
    _tap(VK_VOLUME_DOWN, times=3)
    return "Abaixando volume."


def volume_mute():
    _tap(VK_VOLUME_MUTE)
    return "Alternando mudo."
