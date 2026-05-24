import base64
import os
import subprocess

POWERSHELL_EXE = "powershell"

RADIO_STATES = {
    "on": "On",
    "off": "Off",
}

WINRT_AWAIT_HELPER = """
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$script:AsTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq "AsTask" -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 } |
    Select-Object -First 1)

function Invoke-WinRtAsync($operation, $resultType) {
    $task = $script:AsTaskGeneric.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait() | Out-Null
    return $task.Result
}
"""


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


def _open_bluetooth_settings():
    os.startfile("ms-settings:bluetooth")
    return "Abri as configuracoes de Bluetooth."


def _set_bluetooth_radio(state: str) -> bool:
    radio_state = RADIO_STATES[state]
    script = f"""
$ErrorActionPreference = "Stop"
try {{
{WINRT_AWAIT_HELPER}
    $null = [Windows.Devices.Radios.Radio, Windows.Devices.Radios, ContentType = WindowsRuntime]
    $null = [Windows.Devices.Radios.RadioAccessStatus, Windows.Devices.Radios, ContentType = WindowsRuntime]
    $radios = Invoke-WinRtAsync ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
    $bluetooth = $radios | Where-Object {{ $_.Kind.ToString() -eq "Bluetooth" }} | Select-Object -First 1

    if (-not $bluetooth) {{
        Write-Output "__NO_RADIO__"
        return
    }}

    $desiredState = [Windows.Devices.Radios.RadioState]::{radio_state}
    $result = Invoke-WinRtAsync ($bluetooth.SetStateAsync($desiredState)) ([Windows.Devices.Radios.RadioAccessStatus])

    if ($result.ToString() -eq "Allowed") {{
        Write-Output "__OK__"
    }} else {{
        Write-Output ("__DENIED__:" + $result.ToString())
    }}
}} catch {{
    Write-Output ("__ERROR__:" + $_.Exception.Message)
}}
"""

    try:
        completed = _run_powershell(script)
    except Exception:
        return False

    return completed.returncode == 0 and "__OK__" in (completed.stdout or "")


def _set_bluetooth_pnp(state: str) -> bool:
    action = "Enable-PnpDevice" if state == "on" else "Disable-PnpDevice"
    script = f"""
$ErrorActionPreference = "Stop"
try {{
    $devices = Get-PnpDevice -Class Bluetooth -ErrorAction Stop |
        Where-Object {{ $_.InstanceId -match "^(USB|PCI|ACPI)\\\\" }}

    if (-not $devices) {{
        Write-Output "__NO_DEVICE__"
        return
    }}

    foreach ($device in $devices) {{
        {action} -InstanceId $device.InstanceId -Confirm:$false -ErrorAction Stop
    }}

    Write-Output "__OK__"
}} catch {{
    Write-Output ("__ERROR__:" + $_.Exception.Message)
}}
"""

    try:
        completed = _run_powershell(script, timeout_seconds=15)
    except Exception:
        return False

    return completed.returncode == 0 and "__OK__" in (completed.stdout or "")


def _get_bluetooth_pnp_state():
    script = """
$ErrorActionPreference = "Stop"
try {
    $devices = @(Get-PnpDevice -Class Bluetooth -ErrorAction Stop |
        Where-Object { $_.InstanceId -match "^(USB|PCI|ACPI)\\\\" })

    if (-not $devices -or $devices.Count -eq 0) {
        Write-Output "__NO_DEVICE__"
        return
    }

    $enabled = @($devices | Where-Object { $_.Status -eq "OK" })

    if ($enabled.Count -gt 0) {
        Write-Output "__STATE__:On"
    } else {
        Write-Output "__STATE__:Off"
    }
} catch {
    Write-Output ("__ERROR__:" + $_.Exception.Message)
}
"""

    try:
        completed = _run_powershell(script)
    except Exception:
        return None

    output = completed.stdout or ""
    if "__STATE__:On" in output:
        return "on"
    if "__STATE__:Off" in output:
        return "off"

    return None


def bluetooth_on():
    if _set_bluetooth_radio("on") or _set_bluetooth_pnp("on"):
        return "Ligando Bluetooth."

    try:
        _open_bluetooth_settings()
    except Exception as e:
        return f"Nao consegui ligar o Bluetooth automaticamente: {e}"

    return "Nao consegui ligar direto. Abri as configuracoes de Bluetooth."


def bluetooth_off():
    if _set_bluetooth_radio("off") or _set_bluetooth_pnp("off"):
        return "Desligando Bluetooth."

    try:
        _open_bluetooth_settings()
    except Exception as e:
        return f"Nao consegui desligar o Bluetooth automaticamente: {e}"

    return "Nao consegui desligar direto. Abri as configuracoes de Bluetooth."


def bluetooth_settings():
    try:
        return _open_bluetooth_settings()
    except Exception as e:
        return f"Erro ao abrir configuracoes de Bluetooth: {e}"


def bluetooth_status():
    script = """
$ErrorActionPreference = "Stop"
try {
__WINRT_AWAIT_HELPER__
    $null = [Windows.Devices.Radios.Radio, Windows.Devices.Radios, ContentType = WindowsRuntime]
    $radios = Invoke-WinRtAsync ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
    $bluetooth = $radios | Where-Object { $_.Kind.ToString() -eq "Bluetooth" } | Select-Object -First 1

    if (-not $bluetooth) {
        Write-Output "__NO_RADIO__"
        return
    }

    Write-Output ("__STATE__:" + $bluetooth.State.ToString())
} catch {
    Write-Output ("__ERROR__:" + $_.Exception.Message)
}
"""
    script = script.replace("__WINRT_AWAIT_HELPER__", WINRT_AWAIT_HELPER)

    try:
        completed = _run_powershell(script)
    except Exception:
        return "Nao consegui consultar o Bluetooth."

    output = completed.stdout or ""
    if "__STATE__:On" in output:
        return "Bluetooth esta ligado."
    if "__STATE__:Off" in output:
        return "Bluetooth esta desligado."
    if "__NO_RADIO__" in output:
        pnp_state = _get_bluetooth_pnp_state()
        if pnp_state == "on":
            return "Bluetooth parece estar ligado."
        if pnp_state == "off":
            return "Bluetooth parece estar desligado."
        return "Nao encontrei radio Bluetooth neste PC."

    pnp_state = _get_bluetooth_pnp_state()
    if pnp_state == "on":
        return "Bluetooth parece estar ligado."
    if pnp_state == "off":
        return "Bluetooth parece estar desligado."

    return "Nao consegui consultar o Bluetooth."
