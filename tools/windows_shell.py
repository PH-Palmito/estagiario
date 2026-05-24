from __future__ import annotations

import base64
import subprocess

POWERSHELL_EXE = "powershell"


def run_powershell(
    script: str,
    timeout_seconds: int = 10,
    *,
    powershell_exe: str = POWERSHELL_EXE,
    subprocess_run=subprocess.run,
) -> subprocess.CompletedProcess:
    utf8_preamble = """
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
"""
    encoded = base64.b64encode((utf8_preamble + script).encode("utf-16le")).decode("ascii")
    return subprocess_run(
        [
            powershell_exe,
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


def get_clipboard_text(*, run_powershell_func=run_powershell) -> str:
    try:
        completed = run_powershell_func("Get-Clipboard -Raw -ErrorAction SilentlyContinue", timeout_seconds=3)
    except Exception:
        return ""

    return completed.stdout or ""


def set_clipboard_text(
    text: str,
    *,
    powershell_exe: str = POWERSHELL_EXE,
    subprocess_run=subprocess.run,
) -> None:
    try:
        subprocess_run(
            [
                powershell_exe,
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


def activate_window_names(names, *, run_powershell_func=run_powershell) -> bool:
    names = [str(name or "").strip() for name in list(names or []) if str(name or "").strip()]
    if not names:
        return False

    joined = ", ".join(f"'{name}'" for name in names)
    script = f"""
$shell = New-Object -ComObject WScript.Shell
$names = @({joined})

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
        completed = run_powershell_func(script)
    except Exception:
        return False

    return completed.returncode == 0 and "OK" in (completed.stdout or "")
