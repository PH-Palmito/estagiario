from __future__ import annotations

import ctypes
import os
import re
import time


class WinRect(ctypes.Structure):
    _fields_ = [
        ("Left", ctypes.c_long),
        ("Top", ctypes.c_long),
        ("Right", ctypes.c_long),
        ("Bottom", ctypes.c_long),
    ]


def foreground_window_title(user32) -> str:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""

    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""

    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value.strip()


def foreground_window_rect(user32):
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    rect = WinRect()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None

    return _valid_rect_tuple(int(rect.Left), int(rect.Top), int(rect.Right), int(rect.Bottom))


def foreground_window_capture_hash(
    *,
    get_rect_func,
    run_powershell_func,
    getcwd=os.getcwd,
    makedirs=os.makedirs,
    environ=os.environ,
    path_exists=os.path.exists,
    remove=os.remove,
    monotonic_ns=time.monotonic_ns,
) -> str:
    rect = get_rect_func()
    if not rect:
        return ""

    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width < 80 or height < 80:
        return ""

    temp_dir = os.path.join(getcwd(), ".tmp")
    try:
        makedirs(temp_dir, exist_ok=True)
    except Exception:
        temp_dir = environ.get("TEMP", temp_dir)

    image_path = os.path.join(temp_dir, f"screen-context-{monotonic_ns()}.png")
    ps_image_path = image_path.replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Drawing
$path = '{ps_image_path}'
$bmp = New-Object System.Drawing.Bitmap({width}, {height})
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
try {{
    $graphics.CopyFromScreen({left}, {top}, 0, 0, $bmp.Size)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $hash = (Get-FileHash -Algorithm SHA1 -Path $path).Hash
    Write-Output $hash
}} finally {{
    $graphics.Dispose()
    $bmp.Dispose()
    Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
}}
"""
    try:
        completed = run_powershell_func(script, timeout_seconds=5)
    except Exception:
        _remove_if_exists(image_path, path_exists=path_exists, remove=remove)
        return ""

    _remove_if_exists(image_path, path_exists=path_exists, remove=remove)

    if completed.returncode != 0:
        return ""

    return (completed.stdout or "").strip().lower()


def app_window_rect(app_name: str, *, run_powershell_func):
    script = f"""
$process = Get-Process -Name "{app_name}" -ErrorAction SilentlyContinue |
    Where-Object {{ $_.MainWindowHandle -ne 0 }} |
    Sort-Object StartTime -Descending |
    Select-Object -First 1

if (-not $process) {{
    Write-Output "__NO_WINDOW__"
    return
}}

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WinRectApi {{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {{
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }}

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}}
"@

$rect = New-Object WinRectApi+RECT
if ([WinRectApi]::GetWindowRect($process.MainWindowHandle, [ref]$rect)) {{
    Write-Output ("__RECT__:{0},{1},{2},{3}" -f $rect.Left, $rect.Top, $rect.Right, $rect.Bottom)
}} else {{
    Write-Output "__NO_RECT__"
}}
"""

    try:
        completed = run_powershell_func(script)
    except Exception:
        return None

    output = completed.stdout or ""
    match = re.search(r"__RECT__:(-?\d+),(-?\d+),(-?\d+),(-?\d+)", output)
    if not match:
        return None

    left, top, right, bottom = [int(value) for value in match.groups()]
    return _valid_rect_tuple(left, top, right, bottom)


def first_window_rect(names, *, get_app_window_rect_func):
    for name in names:
        rect = get_app_window_rect_func(name)
        if rect:
            return rect
    return None


def _valid_rect_tuple(left: int, top: int, right: int, bottom: int):
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _remove_if_exists(path: str, *, path_exists, remove) -> None:
    try:
        if path_exists(path):
            remove(path)
    except Exception:
        pass
