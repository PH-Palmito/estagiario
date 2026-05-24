from __future__ import annotations

import base64
import subprocess
from dataclasses import dataclass

INTERRUPTED_WINDOWS_TTS_ERROR = "Fala interrompida."
WINDOWS_TTS_TIMEOUT_ERROR = "Tempo limite atingido ao falar a resposta."


@dataclass(frozen=True)
class WindowsTtsPlan:
    text: str
    selected_culture: str
    preferred_voice_name: str
    tts_rate: int
    tts_volume: int
    command: list[str]


@dataclass(frozen=True)
class WindowsTtsMonitorResult:
    completed: subprocess.CompletedProcess | None
    error: str | None


def clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


def build_windows_tts_script(
    text: str,
    *,
    selected_culture: str,
    preferred_voice_name: str,
    tts_rate: int,
    tts_volume: int,
) -> str:
    safe_text = text.replace("'", "''")
    safe_voice_name = preferred_voice_name.replace('"', '`"')
    return f"""
Add-Type -AssemblyName System.Speech
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$preferredVoiceName = "{safe_voice_name}"

try {{
    $voice.Rate = {tts_rate}
    $voice.Volume = {tts_volume}
    $selected = $null

    if ($preferredVoiceName) {{
        $selected = $voice.GetInstalledVoices() |
            Where-Object {{ $_.VoiceInfo.Name -eq $preferredVoiceName }} |
            Select-Object -First 1
    }}

    if (-not $selected) {{
        $selected = $voice.GetInstalledVoices() |
            Where-Object {{ $_.VoiceInfo.Culture.Name -eq "{selected_culture}" }} |
            Select-Object -First 1
    }}

    if ($selected) {{
        $voice.SelectVoice($selected.VoiceInfo.Name)
    }}

    $voice.Speak('{safe_text}')
    Write-Output "__OK__"
}} catch {{
    Write-Output ("__ERROR__:" + $_.Exception.Message)
}} finally {{
    $voice.Dispose()
}}
"""


def windows_tts_plan(
    text: str,
    culture: str | None,
    preferences: dict,
    powershell_exe: str,
) -> WindowsTtsPlan:
    selected_culture = culture or str(preferences.get("tts_voice_culture", "pt-BR"))
    preferred_voice_name = str(preferences.get("tts_voice_name", "")).strip()
    tts_rate = clamp_int(preferences.get("tts_rate", 0), -10, 10, 0)
    tts_volume = clamp_int(preferences.get("tts_volume", 100), 0, 100, 100)
    script = build_windows_tts_script(
        text,
        selected_culture=selected_culture,
        preferred_voice_name=preferred_voice_name,
        tts_rate=tts_rate,
        tts_volume=tts_volume,
    )
    encoded = encode_powershell_script(script)
    return WindowsTtsPlan(
        text=text,
        selected_culture=selected_culture,
        preferred_voice_name=preferred_voice_name,
        tts_rate=tts_rate,
        tts_volume=tts_volume,
        command=windows_tts_command(powershell_exe, encoded),
    )


def encode_powershell_script(script: str) -> str:
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def windows_tts_command(powershell_exe: str, encoded_script: str) -> list[str]:
    return [
        powershell_exe,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        encoded_script,
    ]


def windows_tts_error(completed: subprocess.CompletedProcess) -> str | None:
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        return stderr or "Sintese de voz indisponivel."

    stdout = (completed.stdout or "").strip()
    if stdout.startswith("__ERROR__:"):
        message = stdout.split("__ERROR__:", 1)[1].strip()
        return message or "Sintese de voz indisponivel."

    return None


def monitor_windows_tts_process(
    process,
    interrupt_pressed,
    monotonic,
    sleep,
    timeout_seconds: float = 20.0,
) -> WindowsTtsMonitorResult:
    started_at = monotonic()
    while process.poll() is None:
        if interrupt_pressed():
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
            return WindowsTtsMonitorResult(completed=None, error=INTERRUPTED_WINDOWS_TTS_ERROR)

        if monotonic() - started_at > timeout_seconds:
            process.kill()
            return WindowsTtsMonitorResult(completed=None, error=WINDOWS_TTS_TIMEOUT_ERROR)

        sleep(0.03)

    stdout, stderr = process.communicate()
    return WindowsTtsMonitorResult(
        completed=subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout=stdout,
            stderr=stderr,
        ),
        error=None,
    )
