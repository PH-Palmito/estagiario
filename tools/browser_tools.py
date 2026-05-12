import base64
import ctypes
import json
import os
import random
import re
import subprocess
import time
import unicodedata
import webbrowser
from urllib.parse import quote, quote_plus, unquote, urlparse

from config import INVESTIDOR10_PRIVATE_WALLET_URL, INVESTIDOR10_WALLET_URL
from llm.ollama_client import ask_model
from memory.investment_snapshot import save_investment_snapshot
from memory.public_wallet_refresh import (
    format_public_wallet_refresh_result,
    parse_wallet_text_blob,
    refresh_wallet_snapshot_auto,
)
from memory.vision_history import remember_vision_analysis
from tools.spotify_api import (
    spotify_add_to_queue,
    spotify_current_playback,
    spotify_next_track,
    spotify_remove_saved_track,
    spotify_save_track,
    spotify_search_track,
    spotify_search_tracks,
    spotify_start_playback,
)
from tools.system_tools import focus_app


user32 = ctypes.windll.user32
try:
    # Keeps UI Automation coordinates aligned with mouse coordinates on scaled/multi-monitor setups.
    user32.SetProcessDPIAware()
except Exception:
    pass

POWERSHELL_EXE = "powershell"
BROWSER_ACTIVATE_NAMES = ["chrome", "msedge", "firefox", "opera", "brave"]

VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_A = 0x41
VK_C = 0x43
VK_ESCAPE = 0x1B
VK_L = 0x4C
VK_V = 0x56
VK_W = 0x57
VK_F = 0x46
VK_R = 0x52
VK_F5 = 0x74
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_0 = 0x30
VK_BACK = 0x08
VK_RETURN = 0x0D
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_SPACE = 0x20
VK_DOWN = 0x28
VK_UP = 0x26
VK_LEFT = 0x25
VK_RIGHT = 0x27

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
SPOTIFY_TRACK_SEARCH_PREFIX = "track:"
SPOTIFY_TRACK_RESULT_CLICKS = (
    (0.52, 0.45),
    (0.49, 0.50),
    (0.56, 0.52),
)
SPOTIFY_LIKED_SONGS_QUERIES = {
    "curtidas",
    "minhas curtidas",
    "as curtidas",
    "musicas curtidas",
    "minhas musicas curtidas",
    "as musicas curtidas",
    "musicas que eu curti",
    "playlist musicas curtidas",
    "liked songs",
    "liked song",
}
SPOTIFY_SURPRISE_QUERIES = (
    "Everybody Wants To Rule The World Tears For Fears",
    "September Earth Wind Fire",
    "Lovely Day Bill Withers",
    "Sultans Of Swing Dire Straits",
    "The Less I Know The Better Tame Impala",
    "Get Lucky Daft Punk",
    "Feeling Good Nina Simone",
    "Take Five Dave Brubeck",
    "Oceano Djavan",
    "Ainda Bem Marisa Monte",
    "Tempo Perdido Legiao Urbana",
    "Lanterna Dos Afogados Os Paralamas Do Sucesso",
    "Back In Black AC/DC",
    "Sweet Child O Mine Guns N Roses",
    "No Surprises Radiohead",
    "Good Days SZA",
    "Lose Yourself Eminem",
    "Clair De Lune Debussy",
    "A Horse With No Name America",
    "Billie Jean Michael Jackson",
)
SPOTIFY_SESSION_QUEUE_TARGET = 5
SPOTIFY_MUSIC_SESSION_POOLS = {
    "alegre": (
        "September Earth Wind Fire",
        "Lovely Day Bill Withers",
        "Walking On Sunshine Katrina And The Waves",
        "Happy Pharrell Williams",
        "Don't Stop Me Now Queen",
        "Get Lucky Daft Punk",
        "Good As Hell Lizzo",
        "Aquarela Do Brasil Gal Costa",
    ),
    "calmo": (
        "Oceano Djavan",
        "Ainda Bem Marisa Monte",
        "Clair De Lune Debussy",
        "No Surprises Radiohead",
        "Banana Pancakes Jack Johnson",
        "Sparks Coldplay",
        "Heartbeats Jose Gonzalez",
        "Come Away With Me Norah Jones",
    ),
    "rock": (
        "Back In Black AC/DC",
        "Sultans Of Swing Dire Straits",
        "Sweet Child O Mine Guns N Roses",
        "Everlong Foo Fighters",
        "Tempo Perdido Legiao Urbana",
        "Smells Like Teen Spirit Nirvana",
        "Another Brick In The Wall Pink Floyd",
        "Black Dog Led Zeppelin",
    ),
    "classico": (
        "Clair De Lune Debussy",
        "Nocturne Op 9 No 2 Chopin",
        "The Four Seasons Spring Vivaldi",
        "Moonlight Sonata Beethoven",
        "Gymnopedie No 1 Erik Satie",
        "Canon In D Pachelbel",
        "Swan Lake Tchaikovsky",
        "Air On The G String Bach",
    ),
    "mpb": (
        "Oceano Djavan",
        "Ainda Bem Marisa Monte",
        "Lanterna Dos Afogados Os Paralamas Do Sucesso",
        "Tempo Perdido Legiao Urbana",
        "So Hoje Jota Quest",
        "Resposta Skank",
        "Velha Infancia Tribalistas",
        "Pais E Filhos Legiao Urbana",
    ),
    "jazz": (
        "Take Five Dave Brubeck",
        "Feeling Good Nina Simone",
        "So What Miles Davis",
        "My Favorite Things John Coltrane",
        "What A Wonderful World Louis Armstrong",
        "Blue In Green Miles Davis",
        "Cantaloupe Island Herbie Hancock",
        "Misty Erroll Garner",
    ),
    "gospel": (
        "Filho Meu Thalles Roberto",
        "Eu Sou De Jesus Luma Elpidio",
        "Ninguem Explica Deus Preto No Branco",
        "Aquieta Minh'alma Ministerio Zoe",
        "Lugar Secreto Gabriela Rocha",
        "Todavia Me Alegrarei Samuel Messias",
        "Deus Provera Gabriela Gomes",
        "Raridade Anderson Freire",
    ),
    "pop": (
        "Billie Jean Michael Jackson",
        "Blinding Lights The Weeknd",
        "As It Was Harry Styles",
        "Levitating Dua Lipa",
        "Good Days SZA",
        "Treasure Bruno Mars",
        "Anti Hero Taylor Swift",
        "Bad Guy Billie Eilish",
    ),
    "eletronica": (
        "Get Lucky Daft Punk",
        "Strobe Deadmau5",
        "One More Time Daft Punk",
        "Levels Avicii",
        "Midnight City M83",
        "Titanium David Guetta Sia",
        "Innerbloom Rufus Du Sol",
        "Opus Eric Prydz",
    ),
    "rap": (
        "Lose Yourself Eminem",
        "Alright Kendrick Lamar",
        "Juicy The Notorious B.I.G.",
        "N.Y. State Of Mind Nas",
        "Jesus Walks Kanye West",
        "A Milli Lil Wayne",
        "HUMBLE. Kendrick Lamar",
        "99 Problems Jay Z",
    ),
    "samba": (
        "Deixa A Vida Me Levar Zeca Pagodinho",
        "Trem Das Onze Demônios Da Garoa",
        "O Mundo E Um Moinho Cartola",
        "Preciso Me Encontrar Cartola",
        "Mas Que Nada Jorge Ben Jor",
        "Aquarela Brasileira Martinho Da Vila",
        "Vou Festejar Beth Carvalho",
        "Não Deixe O Samba Morrer Alcione",
    ),
    "sertanejo": (
        "Evidencias Chitaozinho E Xororo",
        "Infiel Marilia Mendonca",
        "Cuida Bem Dela Henrique E Juliano",
        "Propaganda Jorge E Mateus",
        "Flor E O Beija Flor Henrique E Juliano",
        "Atrasadinha Felipe Araujo Ferrugem",
        "Sosseguei Jorge E Mateus",
        "De Quem E A Culpa Marilia Mendonca",
    ),
    "foco": (
        "Weightless Marconi Union",
        "Intro The xx",
        "Dayvan Cowboy Boards Of Canada",
        "Experience Ludovico Einaudi",
        "Avril 14th Aphex Twin",
        "Time Hans Zimmer",
        "Near Light Olafur Arnalds",
        "A Walk Tycho",
    ),
    "treino": (
        "Lose Yourself Eminem",
        "Till I Collapse Eminem",
        "Eye Of The Tiger Survivor",
        "Stronger Kanye West",
        "Thunderstruck AC/DC",
        "Can't Hold Us Macklemore",
        "Remember The Name Fort Minor",
        "Power Kanye West",
    ),
    "triste": (
        "No Surprises Radiohead",
        "Someone Like You Adele",
        "The Night We Met Lord Huron",
        "Fix You Coldplay",
        "Everybody Hurts R.E.M.",
        "Tears In Heaven Eric Clapton",
        "Creep Radiohead",
        "Hurt Johnny Cash",
    ),
}
SPOTIFY_MUSIC_SESSION_LABELS = {
    "alegre": "alegre",
    "calmo": "calma",
    "rock": "rock",
    "classico": "clássica",
    "mpb": "MPB",
    "jazz": "jazz",
    "gospel": "gospel",
    "pop": "pop",
    "eletronica": "eletrônica",
    "rap": "rap",
    "samba": "samba e pagode",
    "sertanejo": "sertaneja",
    "foco": "de foco",
    "treino": "de treino",
    "triste": "melancólica",
}


def _spotify_play_track_via_app(query: str, track_name: str = "", track_artists: str = "") -> bool:
    search_query = track_name or query
    if track_artists:
        search_query = f"{search_query} {track_artists}"
    try:
        os.startfile(f"spotify:search:{quote(SPOTIFY_TRACK_SEARCH_PREFIX + search_query)}")
        time.sleep(1.4)
        focus_app("spotify")
        time.sleep(0.4)
        if _click_spotify_track_by_name(track_name or query):
            return True
        return _click_spotify_first_visible_track()
    except Exception:
        return False


def _play_spotify_track_result(query: str, best_track: dict, *, surprise: bool = False) -> str:
    track_uri = str(best_track.get("uri") or "").strip()
    track_id = str(best_track.get("id") or "").strip()
    track_name = str(best_track.get("name") or query).strip()
    track_artists = str(best_track.get("artists") or "").strip()

    if track_uri and spotify_start_playback(track_uri):
        if surprise:
            if track_artists:
                return f"Surpresa escolhida: tocando {track_name}, de {track_artists}, no Spotify."
            return f"Surpresa escolhida: tocando {track_name} no Spotify."
        if track_artists:
            return f"Tocando {track_name}, de {track_artists}, no Spotify."
        return f"Tocando {track_name} no Spotify."

    if _spotify_play_track_via_app(query, track_name, track_artists):
        if surprise:
            if track_artists:
                return f"Surpresa escolhida: tentando tocar {track_name}, de {track_artists}, no Spotify."
            return f"Surpresa escolhida: tentando tocar {track_name} no Spotify."
        if track_artists:
            return f"Tentando tocar {track_name}, de {track_artists}, no Spotify."
        return f"Tentando tocar {track_name} no Spotify."

    try:
        if track_id:
            os.startfile(f"spotify:track:{track_id}")
        elif track_uri:
            os.startfile(track_uri)
        else:
            raise RuntimeError("track_not_found")
        time.sleep(1.4)
        focus_app("spotify")
        verb = "Surpresa escolhida: abrindo" if surprise else "Abrindo"
        if track_artists:
            return f"{verb} {track_name}, de {track_artists}, no Spotify."
        return f"{verb} {track_name} no Spotify."
    except Exception:
        track_url = str(best_track.get("url") or "").strip()
        if track_url:
            webbrowser.open(track_url)
        verb = "Surpresa escolhida: abrindo" if surprise else "Abrindo"
        if track_artists:
            return f"{verb} {track_name}, de {track_artists}, no Spotify."
        return f"{verb} {track_name} no Spotify."


def _spotify_track_label(track: dict, fallback: str = "a faixa escolhida") -> str:
    name = str(track.get("name") or fallback).strip()
    artists = str(track.get("artists") or "").strip()
    if artists:
        return f"{name}, de {artists}"
    return name


def _search_spotify_session_tracks(queries, limit: int = SPOTIFY_SESSION_QUEUE_TARGET) -> list[dict]:
    tracks = []
    seen = set()
    query_list = list(queries or [])
    if not query_list:
        return tracks

    for query in random.sample(query_list, k=len(query_list)):
        try:
            track = spotify_search_track(query)
        except Exception:
            track = None
        if not track:
            continue

        key = str(track.get("uri") or track.get("id") or track.get("name") or query).casefold()
        if key in seen:
            continue
        seen.add(key)
        tracks.append(track)
        if len(tracks) >= limit:
            break

    return tracks


def _start_spotify_session(queries, label: str, *, surprise: bool = False) -> str:
    tracks = _search_spotify_session_tracks(queries)
    if not tracks:
        return f"Tentei montar uma sessão {label} no Spotify, mas não encontrei faixas agora."

    first_track = tracks[0]
    first_uri = str(first_track.get("uri") or "").strip()
    started = bool(first_uri and spotify_start_playback(first_uri))
    if not started:
        started = _spotify_play_track_via_app(
            str(first_track.get("name") or ""),
            str(first_track.get("name") or ""),
            str(first_track.get("artists") or ""),
        )

    if not started:
        return _play_spotify_track_result(str(first_track.get("name") or label), first_track, surprise=surprise)

    queued = []
    for track in tracks[1:]:
        track_uri = str(track.get("uri") or "").strip()
        if track_uri and spotify_add_to_queue(track_uri):
            queued.append(track)

    prefix = "Surpresa escolhida" if surprise else f"Sessão {label} iniciada"
    response = f"{prefix}: tocando {_spotify_track_label(first_track)}."
    if queued:
        response += f" Também deixei mais {len(queued)} faixas na fila."
    elif len(tracks) > 1:
        response += " Encontrei outras faixas, mas não consegui adicionar à fila agora."
    return response
LAST_BROWSER_ELEMENTS = []
LAST_BROWSER_CONTEXT = ""
LAST_BROWSER_CONTEXT_CHANGED_AT = 0.0
LAST_SELECTED_TEXT = ""
DEFAULT_INVESTIDOR10_WALLET_URL = (
    INVESTIDOR10_WALLET_URL
    or INVESTIDOR10_PRIVATE_WALLET_URL
    or "https://investidor10.com.br/wallet/my-wallet"
)
EDGE_BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
CHROME_BROWSER_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


class _WinRect(ctypes.Structure):
    _fields_ = [
        ("Left", ctypes.c_long),
        ("Top", ctypes.c_long),
        ("Right", ctypes.c_long),
        ("Bottom", ctypes.c_long),
    ]


def _clear_browser_snapshot(context: str = ""):
    global LAST_BROWSER_ELEMENTS, LAST_BROWSER_CONTEXT, LAST_BROWSER_CONTEXT_CHANGED_AT

    LAST_BROWSER_ELEMENTS = []
    LAST_BROWSER_CONTEXT = context
    LAST_BROWSER_CONTEXT_CHANGED_AT = time.monotonic()


def _set_browser_elements(elements, context: str = ""):
    global LAST_BROWSER_ELEMENTS, LAST_BROWSER_CONTEXT

    LAST_BROWSER_ELEMENTS = list(elements)
    LAST_BROWSER_CONTEXT = context


def _remember_text_items(lines, context: str = ""):
    elements = [
        {
            "text": line,
            "x": None,
            "y": None,
            "type": "Text",
        }
        for line in lines
    ]
    _set_browser_elements(elements, context=context)


def _remember_browser_analysis(summary: str, lines=None, page_url: str = "", page_title: str = "", source: str = "pagina"):
    summary = re.sub(r"\s+", " ", str(summary or "")).strip()
    if not summary:
        return

    compact_lines = []
    for line in list(lines or [])[:30]:
        clean = re.sub(r"\s+", " ", str(line or "")).strip()
        if clean:
            compact_lines.append(clean)

    remember_vision_analysis(
        source,
        summary,
        details={
            "kind": "browser",
            "page_url": page_url or "",
            "page_title": page_title or "",
            "lines": compact_lines,
        },
    )


def _get_foreground_window_title() -> str:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""

    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""

    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value.strip()


def _get_foreground_window_rect():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    rect = _WinRect()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None

    left = int(rect.Left)
    top = int(rect.Top)
    right = int(rect.Right)
    bottom = int(rect.Bottom)
    if right <= left or bottom <= top:
        return None

    return left, top, right, bottom


def _get_foreground_window_capture_hash() -> str:
    rect = _get_foreground_window_rect()
    if not rect:
        return ""

    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width < 80 or height < 80:
        return ""

    temp_dir = os.path.join(os.getcwd(), ".tmp")
    try:
        os.makedirs(temp_dir, exist_ok=True)
    except Exception:
        temp_dir = os.environ.get("TEMP", temp_dir)

    image_path = os.path.join(temp_dir, f"screen-context-{time.monotonic_ns()}.png")
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
        completed = _run_powershell(script, timeout_seconds=5)
    except Exception:
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception:
            pass
        return ""

    try:
        if os.path.exists(image_path):
            os.remove(image_path)
    except Exception:
        pass

    if completed.returncode != 0:
        return ""

    return (completed.stdout or "").strip().lower()


def _browser_context_signature() -> str:
    title = _get_foreground_window_title()
    if not title:
        return ""

    title = re.sub(r"\s+", " ", title).strip()
    title_signature = _normalize_text_for_match(title)
    page_url = _get_browser_url()
    if page_url:
        parsed = urlparse(page_url)
        url_signature = _normalize_text_for_match(f"{parsed.netloc}{parsed.path}")
        if url_signature:
            title_signature = f"{title_signature}|{url_signature}"
    capture_hash = _get_foreground_window_capture_hash()
    if capture_hash:
        return f"{title_signature}|{capture_hash[:16]}"
    return title_signature


def _refresh_browser_context() -> str:
    global LAST_BROWSER_CONTEXT, LAST_BROWSER_CONTEXT_CHANGED_AT

    context = _browser_context_signature()
    if context and LAST_BROWSER_CONTEXT and context != LAST_BROWSER_CONTEXT:
        _clear_browser_snapshot(context=context)
    elif context and not LAST_BROWSER_CONTEXT:
        LAST_BROWSER_CONTEXT = context
        LAST_BROWSER_CONTEXT_CHANGED_AT = time.monotonic()

    return context


def _browser_context_recently_changed(window_seconds: float = 1.2) -> bool:
    if LAST_BROWSER_CONTEXT_CHANGED_AT <= 0:
        return False
    return (time.monotonic() - LAST_BROWSER_CONTEXT_CHANGED_AT) <= window_seconds



def _run_powershell(script: str, timeout_seconds: int = 10) -> subprocess.CompletedProcess:
    utf8_preamble = """
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
"""
    encoded = base64.b64encode((utf8_preamble + script).encode("utf-16le")).decode("ascii")
    """
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
        # "todos os direitos reservados",
        # "leia mais no texto original",
        "lei nº",
        # "lei n",
        # "redistribuicao",
        "redistribuição",
    )


    """
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


def _get_clipboard_text() -> str:
    try:
        completed = _run_powershell("Get-Clipboard -Raw -ErrorAction SilentlyContinue", timeout_seconds=3)
    except Exception:
        return ""

    return completed.stdout or ""


def _set_clipboard_text(text: str):
    try:
        subprocess.run(
            [
                POWERSHELL_EXE,
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


def _activate_window_names(names) -> bool:
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
        completed = _run_powershell(script)
    except Exception:
        return False

    return completed.returncode == 0 and "OK" in (completed.stdout or "")


def _first_existing_browser(candidates) -> str:
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return ""


def _preferred_wallet_browser() -> tuple[str, str]:
    edge_path = _first_existing_browser(EDGE_BROWSER_CANDIDATES)
    if edge_path:
        return edge_path, "msedge"

    chrome_path = _first_existing_browser(CHROME_BROWSER_CANDIDATES)
    if chrome_path:
        return chrome_path, "chrome"

    return "", ""


def _open_url_in_wallet_browser(url: str) -> str:
    browser_path, app_name = _preferred_wallet_browser()
    if browser_path:
        try:
            subprocess.Popen([browser_path, "--new-tab", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return app_name
        except Exception:
            pass

    try:
        webbrowser.open(url, new=2)
        return ""
    except Exception:
        return ""


def _activate_browser_window() -> bool:
    return _activate_window_names(BROWSER_ACTIVATE_NAMES)


def _tap(vk_code: int):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _tap_times(vk_code: int, times: int, delay: float = 0.08):
    for _ in range(max(1, times)):
        _tap(vk_code)
        time.sleep(delay)


def _click(x: int, y: int, clicks: int = 1):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)

    for _ in range(max(1, clicks)):
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.03)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.12)


def _get_app_window_rect(app_name: str):
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
        completed = _run_powershell(script)
    except Exception:
        return None

    output = completed.stdout or ""
    match = re.search(r"__RECT__:(-?\d+),(-?\d+),(-?\d+),(-?\d+)", output)
    if not match:
        return None

    left, top, right, bottom = [int(value) for value in match.groups()]
    if right <= left or bottom <= top:
        return None

    return left, top, right, bottom


def _get_browser_window_rect():
    for name in BROWSER_ACTIVATE_NAMES:
        rect = _get_app_window_rect(name)
        if rect:
            return rect

    return None


def _click_first_browser_link():
    names = ", ".join(f"'{name}'" for name in BROWSER_ACTIVATE_NAMES)
    script = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @({names})
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
    Write-Output "__NO_BROWSER__"
    return
}}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {{
    Write-Output "__NO_ROOT__"
    return
}}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {{
    $element = $elements.Item($i)
    try {{
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 3) {{
            continue
        }}

        if ($rect.IsEmpty -or $rect.Width -lt 40 -or $rect.Height -lt 10) {{
            continue
        }}

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 135 -or $relativeLeft -lt 80) {{
            continue
        }}

        if ($controlType -notmatch "Hyperlink|Button|ListItem|DataItem") {{
            continue
        }}

        if ($name -match "^(voltar|avancar|recarregar|favoritos|perfil|mais|menu|google apps|entrar)$") {{
            continue
        }}

        $score = 1000 - $relativeTop
        if ($controlType -match "Hyperlink") {{
            $score += 200
        }}

        $candidates += [pscustomobject]@{{
            Top = $rect.Top
            Left = $rect.Left
            Score = $score
            X = [int]($rect.Left + [Math]::Min(160, [Math]::Max(20, $rect.Width / 2)))
            Y = [int]($rect.Top + ($rect.Height / 2))
        }}
    }} catch {{
    }}
}}

$candidate = $candidates |
    Sort-Object -Property @{{ Expression = "Score"; Descending = $true }}, @{{ Expression = "Top"; Descending = $false }}, @{{ Expression = "Left"; Descending = $false }} |
    Select-Object -First 1

if (-not $candidate) {{
    Write-Output "__NO_LINK__"
    return
}}

Write-Output ("__POINT__:{0},{1}" -f $candidate.X, $candidate.Y)
"""

    try:
        completed = _run_powershell(script, timeout_seconds=8)
    except Exception:
        return False

    output = completed.stdout or ""
    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)", output)
    if not point_match:
        return False

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    _click(x, y)
    return True


def _normalize_text_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_gallery_suffix(text: str) -> str:
    cleaned = re.sub(
        r"\s+(?:imagen|imagem|image)\s*-\s*\d+\s*/\s*\d+\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", cleaned).strip(" -")


def _short_click_query(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    normalized = re.sub(r"\bR\$\s*[\d\.\,]+.*$", "", normalized, flags=re.IGNORECASE).strip()
    words = normalized.split()

    if len(words) > 8:
        normalized = " ".join(words[:8])

    return normalized


def _click_query_variants(text: str) -> list[str]:
    base = _short_click_query(text)
    if not base:
        return []

    words = [word for word in base.split() if word]
    variants = []

    def add_variant(candidate: str):
        candidate = re.sub(r"\s+", " ", candidate).strip(" ,.-")
        if len(candidate) >= 3 and candidate not in variants:
            variants.append(candidate)

    add_variant(base)

    for size in (6, 5, 4, 3):
        if len(words) >= size:
            add_variant(" ".join(words[:size]))

    if "-" in base:
        add_variant(base.split("-", 1)[0])

    return variants


def _click_browser_item_from_text(text: str) -> bool:
    for query in _click_query_variants(text):
        if _click_browser_element_by_text(query):
            return True

    return False


def _extract_brl_price(text: str):
    matches = re.findall(r"R\$\s*([\d\.]+,\d{2})", text or "", flags=re.IGNORECASE)
    if not matches:
        return None

    values = []
    for match in matches:
        try:
            values.append(float(match.replace(".", "").replace(",", ".")))
        except ValueError:
            continue

    if not values:
        return None

    return min(values)


def _run_browser_javascript(script_body: str) -> bool:
    if not _activate_browser_window():
        return False

    old_clipboard = _get_clipboard_text()

    try:
        _shortcut(VK_CONTROL, VK_L)
        time.sleep(0.05)
        _type_text("javascript:")
        _set_clipboard_text(script_body)
        _shortcut(VK_CONTROL, VK_V)
        time.sleep(0.05)
        _tap(VK_RETURN)
        time.sleep(0.25)
        return True
    except Exception:
        return False
    finally:
        _set_clipboard_text(old_clipboard)


def _run_browser_javascript_and_read_clipboard(script_body: str, marker: str, timeout: float = 0.8) -> str:
    if not _activate_browser_window():
        return ""

    old_clipboard = _get_clipboard_text()

    try:
        _set_clipboard_text("")
        _shortcut(VK_CONTROL, VK_L)
        time.sleep(0.05)
        _type_text("javascript:")
        _set_clipboard_text(script_body)
        _shortcut(VK_CONTROL, VK_V)
        time.sleep(0.05)
        _tap(VK_RETURN)
        time.sleep(timeout)
        copied = _get_clipboard_text()

        if copied.startswith(marker):
            return copied[len(marker):].strip()

        return ""
    except Exception:
        return ""
    finally:
        _set_clipboard_text(old_clipboard)


def _click_page_item_by_text(text: str) -> bool:
    # Disabled: address-bar JavaScript bookmarklets can be interpreted as a search by Chrome.
    # Keep product clicks conservative until we have a safer browser-control channel.
    return False

    query = _short_click_query(text)
    if not query:
        return False

    query_json = json.dumps(query, ensure_ascii=False)
    script = f"""void ((()=>{{
const q={query_json};
const norm=s=>(s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[^\\p{{L}}\\p{{N}}\\s]/gu," ").replace(/\\s+/g," ").trim();
const words=norm(q).split(" ").filter(w=>w.length>2).slice(0,8);
const visible=el=>{{
  const r=el.getBoundingClientRect();
  const st=getComputedStyle(el);
  return r.width>30&&r.height>12&&r.bottom>70&&r.top<innerHeight&&st.visibility!=="hidden"&&st.display!=="none";
}};
const scoreElement=el=>{{
  if(!visible(el)) return null;
  const text=norm(el.innerText||el.textContent||el.getAttribute("aria-label")||el.title||"");
  if(!text) return null;
  let matches=0;
  for(const w of words) if(text.includes(w)) matches++;
  if(matches<Math.min(3, words.length)) return null;
  const r=el.getBoundingClientRect();
  let score=matches*1000-r.top;
  if(el.tagName==="A") score+=500;
  if(el.querySelector&&el.querySelector("a")) score+=250;
  if(text.includes("r$")) score+=150;
  return {{el, score, top:r.top}};
}};
const nodes=[...document.querySelectorAll("a,button,[role='link'],[role='button'],article,li,section,div")];
const best=nodes.map(scoreElement).filter(Boolean).sort((a,b)=>b.score-a.score||a.top-b.top)[0];
if(!best) return false;
const target=best.el.closest("a")||best.el.querySelector("a")||best.el;
target.scrollIntoView({{block:"center", inline:"center"}});
setTimeout(()=>target.click(),120);
return true;
}})())"""

    return _run_browser_javascript(script)


def _click_browser_element_by_text(query: str, app_names=None):
    query_words = [
        word
        for word in _normalize_text_for_match(query).split()
        if len(word) >= 2
    ][:5]
    if not query_words:
        return False

    ps_words = ", ".join(f"'{word}'" for word in query_words)
    target_names = app_names or BROWSER_ACTIVATE_NAMES
    names = ", ".join(f"'{name}'" for name in target_names)
    script = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @({names})
$queryWords = @({ps_words})
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
    Write-Output "__NO_BROWSER__"
    return
}}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {{
    Write-Output "__NO_ROOT__"
    return
}}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {{
    $element = $elements.Item($i)
    try {{
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 2) {{
            continue
        }}

        if ($rect.IsEmpty -or $rect.Width -lt 12 -or $rect.Height -lt 8) {{
            continue
        }}

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 85 -or $relativeLeft -lt 5) {{
            continue
        }}

        $normalizedName = $name.ToLower() -replace "[^\\p{{L}}\\p{{Nd}}\\s]", " "
        $normalizedName = $normalizedName -replace "\\s+", " "

        $matches = 0
        foreach ($word in $queryWords) {{
            if ($normalizedName.Contains($word)) {{
                $matches += 1
            }}
        }}

        if ($matches -le 0) {{
            continue
        }}

        $score = $matches * 100
        if ($controlType -match "Button|Hyperlink|ListItem|DataItem") {{
            $score += 80
        }}
        if ($matches -eq $queryWords.Count) {{
            $score += 120
        }}

        # Prefer visible content area and elements closer to the top.
        $score += [Math]::Max(0, 500 - [int]$relativeTop)

        $candidates += [pscustomobject]@{{
            Score = $score
            Top = $rect.Top
            Left = $rect.Left
            X = [int]($rect.Left + [Math]::Min([Math]::Max($rect.Width / 2, 12), 180))
            Y = [int]($rect.Top + ($rect.Height / 2))
        }}
    }} catch {{
    }}
}}

$candidate = $candidates |
    Sort-Object -Property @{{ Expression = "Score"; Descending = $true }}, @{{ Expression = "Top"; Descending = $false }}, @{{ Expression = "Left"; Descending = $false }} |
    Select-Object -First 1

if (-not $candidate) {{
    Write-Output "__NO_MATCH__"
    return
}}

Write-Output ("__POINT__:{0},{1}" -f $candidate.X, $candidate.Y)
"""

    try:
        completed = _run_powershell(script, timeout_seconds=8)
    except Exception:
        return False

    output = completed.stdout or ""
    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)", output)
    if not point_match:
        return False

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    _click(x, y)
    return True


def _read_browser_elements(limit: int = 10):
    names = ", ".join(f"'{name}'" for name in BROWSER_ACTIVATE_NAMES)
    script = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$processNames = @({names})
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
    Write-Output "__NO_BROWSER__"
    return
}}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {{
    Write-Output "__NO_ROOT__"
    return
}}

$rootRect = $root.Current.BoundingRectangle
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$rows = @()

for ($i = 0; $i -lt $elements.Count; $i++) {{
    $element = $elements.Item($i)
    try {{
        $name = ([string]$element.Current.Name).Trim()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $name.Length -lt 3) {{
            continue
        }}

        if ($rect.IsEmpty -or $rect.Width -lt 20 -or $rect.Height -lt 8) {{
            continue
        }}

        $relativeTop = $rect.Top - $rootRect.Top
        $relativeLeft = $rect.Left - $rootRect.Left

        if ($relativeTop -lt 90 -or $relativeLeft -lt 5) {{
            continue
        }}

        if ($controlType -notmatch "Button|Hyperlink|ListItem|DataItem|Text|Edit|ComboBox") {{
            continue
        }}

        if ($name -match "^(voltar|avancar|recarregar|favoritos|perfil|mais|menu|google apps)$") {{
            continue
        }}

        $safeName = ($name -replace "\\s+", " ").Trim()
        if ($safeName.Length -gt 90) {{
            $safeName = $safeName.Substring(0, 90)
        }}

        $score = 1000 - [int]$relativeTop
        if ($controlType -match "Button|Hyperlink") {{
            $score += 150
        }}

        $rows += [pscustomobject]@{{
            Score = $score
            Top = [int]$rect.Top
            Left = [int]$rect.Left
            Text = ("__ITEM__|{0}|{1}|{2}|{3}" -f $safeName.Replace("|", " "), [int]($rect.Left + ($rect.Width / 2)), [int]($rect.Top + ($rect.Height / 2)), $controlType)
        }}
    }} catch {{
    }}
}}

$seen = @{{}}
$rows |
    Sort-Object -Property @{{ Expression = "Top"; Descending = $false }}, @{{ Expression = "Left"; Descending = $false }} |
    ForEach-Object {{
        $name = ($_.Text -split "\\|")[1]
        $key = $name.ToLower()
        if (-not $seen.ContainsKey($key)) {{
            $seen[$key] = $true
            Write-Output $_.Text
        }}
    }}
"""

    try:
        completed = _run_powershell(script, timeout_seconds=8)
    except Exception:
        return None

    output = completed.stdout or ""
    if "__NO_BROWSER__" in output or "__NO_ROOT__" in output:
        return None

    items = []
    for line in output.splitlines():
        if not line.startswith("__ITEM__|"):
            continue

        parts = line.split("|", 4)
        if len(parts) < 5:
            continue

        try:
            items.append(
                {
                    "text": parts[1].strip(),
                    "x": int(parts[2]),
                    "y": int(parts[3]),
                    "type": parts[4].strip(),
                }
            )
        except ValueError:
            continue

        if len(items) >= limit:
            break

    return items


def _useful_page_text_lines(text: str, limit: int = 10, page_url: str = "", page_title: str = ""):
    ignore_patterns = (
        "javascript",
        "cookie",
        "politica de privacidade",
        "política de privacidade",
        "termos de uso",
        "menu",
        "entrar",
        "minha conta",
        "sacola",
        "carrinho",
        "buscar",
        "pesquisar",
    )
    finance_category = _detect_screen_category([], page_url=page_url, page_title=page_title) == "financas"
    finance_tokens = {
        "investidor10",
        "carteira",
        "wallet",
        "patrimonio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
        "dividendos",
        "saldo",
        "preco medio",
        "lucro",
        "prejuizo",
        "aporte",
        "ticker",
        "fii",
        "cotacao",
    }
    lines = []
    seen = set()

    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()

        if len(line) < 4 or len(line) > 120:
            continue

        normalized = _normalize_text_for_match(line)
        if not normalized or normalized in seen:
            continue

        if re.match(r"^https?://", line, flags=re.IGNORECASE):
            continue
        if "http://" in line.lower() or "https://" in line.lower():
            continue

        if normalized.isdigit():
            continue

        if re.match(r"^(?:r\$\s*)?[\d\.\,]+$", line.lower()):
            continue

        if re.match(r"^\d+x\s+de\s+r\$", line.lower()):
            continue

        if any(pattern in normalized for pattern in ignore_patterns):
            continue
        if "direitos reservados" in normalized or "copyright" in normalized or "leia mais no texto original" in normalized:
            continue

        score = 0
        if re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()):
            score += 80
        if any(word in normalized for word in {"celular", "notebook", "smartphone", "iphone", "samsung", "motorola", "xiaomi", "comprar", "frete", "oferta"}):
            score += 50
        if finance_category and any(token in normalized for token in finance_tokens):
            score += 90
        if finance_category and "%" in line:
            score += 40
        score += max(0, 60 - len(lines))
        lines.append((score, line))
        seen.add(normalized)

    lines.sort(key=lambda item: item[0], reverse=True)
    return [line for _score, line in lines[:limit]]


def _screen_lines_quality(lines) -> int:
    if not lines:
        return 0

    product_words = {
        "celular", "smartphone", "notebook", "iphone", "galaxy", "moto", "motorola",
        "xiaomi", "redmi", "samsung", "realme", "oppo", "lavadora", "lava", "relogio",
        "relógio", "tv", "monitor", "fogao", "fogão", "geladeira",
    }
    noise_terms = {
        "sem juros", "vez de r$", "vezes de r$", "frete", "cupom", "celulares",
        "eletrodomesticos", "eletrodomésticos", "tipo de", "comprar agora",
    }

    score = 0
    for line in lines:
        normalized = _normalize_text_for_match(line)
        if not normalized:
            continue

        has_letters = bool(re.search(r"[a-zA-Z\u00C0-\u017F]", line))
        has_digits = bool(re.search(r"\d", line))
        if has_letters:
            score += 5
        if len(normalized.split()) >= 4:
            score += 2
        if any(word in normalized for word in product_words):
            score += 6
        if re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()):
            score -= 2
        if any(term in normalized for term in noise_terms):
            score -= 4
        if has_digits and not has_letters:
            score -= 8

    return score + len(lines)


def _screen_list_intro() -> str:
    return random.choice(
        [
            "Consegui ler texto da pagina",
            "Isto foi o que achei na pagina",
            "Encontrei estes pontos na tela",
            "O que estou vendo na pagina e",
        ]
    )


def _screen_summary_intro() -> str:
    return random.choice(
        [
            "Resumo da tela",
            "Panorama da tela",
            "Visao rapida da tela",
        ]
    )


def _get_browser_url() -> str:
    if not _activate_browser_window():
        return ""

    old_clipboard = _get_clipboard_text()
    sentinel = f"__ESTAGIARIO_BROWSER_URL__{time.monotonic_ns()}__"
    copied = ""

    try:
        _set_clipboard_text(sentinel)
        time.sleep(0.03)
        _shortcut(VK_CONTROL, VK_L)
        time.sleep(0.08)
        _shortcut(VK_CONTROL, VK_C)
        for _ in range(12):
            time.sleep(0.08)
            sample = _get_clipboard_text().strip()
            if sample and sample != sentinel and sample != old_clipboard:
                copied = sample
                break
    finally:
        _tap(VK_ESCAPE)
        _set_clipboard_text(old_clipboard)

    if not copied:
        return ""

    if copied.startswith(("http://", "https://")):
        return copied

    return ""


def _clean_browser_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", title or "").strip(" -|")
    cleaned = re.sub(r"\s*-\s*(google chrome|chrome|microsoft edge|edge|mozilla firefox|firefox|opera|brave)$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _parse_github_repo_from_url(page_url: str) -> str:
    parsed = urlparse(page_url or "")
    if "github.com" not in parsed.netloc.lower():
        return ""

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return ""


def _parse_github_profile_from_url(page_url: str) -> str:
    parsed = urlparse(page_url or "")
    if "github.com" not in parsed.netloc.lower():
        return ""

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) == 1:
        return parts[0]
    return ""


def _github_page_kind(page_url: str) -> str:
    if _parse_github_repo_from_url(page_url):
        return "repo"
    if _parse_github_profile_from_url(page_url):
        return "profile"
    return "generic"


def _parse_title_content(clean_title: str, page_url: str) -> str:
    if not clean_title:
        return ""

    parsed = urlparse(page_url or "")
    host = parsed.netloc.lower()

    if "youtube.com" in host or "youtu.be" in host:
        return re.sub(r"\s*-\s*youtube$", "", clean_title, flags=re.IGNORECASE).strip()

    if "github.com" in host:
        match = re.match(r"GitHub\s*-\s*([^:]+):\s*(.+)$", clean_title, flags=re.IGNORECASE)
        if match:
            return match.group(2).strip()

    return clean_title


def _strip_repo_prefix_from_title(title_content: str, repo_name: str) -> str:
    compact = re.sub(r"\s+", " ", title_content or "").strip()
    if not compact or not repo_name:
        return compact

    pattern = rf"^{re.escape(repo_name)}\s*[:\-–|]\s*"
    stripped = re.sub(pattern, "", compact, flags=re.IGNORECASE).strip()
    return stripped or compact


def _relevance_terms_from_context(page_url: str = "", page_title: str = "") -> set[str]:
    stopwords = {
        "para", "com", "sem", "por", "uma", "uns", "umas", "the", "and", "from",
        "that", "this", "como", "mais", "menos", "sobre", "resumo", "detalhe",
        "home", "inicio", "início", "page", "pagina", "página", "site", "oficial",
        "google", "chrome", "edge", "firefox", "youtube", "github", "investidor10",
    }
    tokens = set()

    clean_title = _clean_browser_title(page_title)
    title_content = _parse_title_content(clean_title, page_url)
    normalized_title = _normalize_text_for_match(title_content)
    for token in normalized_title.split():
        if len(token) >= 4 and token not in stopwords and not token.isdigit():
            tokens.add(token)

    parsed = urlparse(page_url or "")
    host = parsed.netloc.lower()
    for piece in re.split(r"[\.\-_/]+", host):
        piece = piece.strip()
        if len(piece) >= 4 and piece not in {"www", "com", "br"} and piece not in stopwords:
            tokens.add(piece)

    return tokens


def _extract_generic_focus_lines(lines, page_url: str = "", page_title: str = "", limit: int = 5) -> list[str]:
    prioritized = []
    relevance_terms = _relevance_terms_from_context(page_url=page_url, page_title=page_title)
    generic_noise = (
        "cookie",
        "politica de privacidade",
        "política de privacidade",
        "termos de uso",
        "menu",
        "entrar",
        "login",
        "minha conta",
        "carrinho",
        "sacola",
        "buscar",
        "pesquisar",
        "departamentos",
        "atendimento",
        "pular navegacao",
        "pular navegação",
        "ir para o conte",
        "repository navigation",
        "visao geral",
        "visão geral",
    )

    for index, line in enumerate(lines):
        compact = re.sub(r"\s+", " ", line).strip()
        normalized = _normalize_text_for_match(compact)
        if not compact or len(compact) < 4:
            continue
        if normalized.isdigit():
            continue
        if re.match(r"^https?://", compact, flags=re.IGNORECASE):
            continue
        if any(token in normalized for token in generic_noise):
            continue
        if "http://" in compact.lower() or "https://" in compact.lower():
            continue
        if (
            "direitos reservados" in normalized
            or "copyright" in normalized
            or "leia mais no texto original" in normalized
            or ("lei" in normalized and "9 610 98" in normalized)
        ):
            continue

        score = 0
        words = normalized.split()
        if len(words) >= 3:
            score += 2
        if len(words) >= 6:
            score += 2
        if len(compact) >= 28:
            score += 1
        if re.search(r"[.!:%]", compact):
            score += 1
        if any(term in normalized for term in relevance_terms):
            score += 6
        if re.search(r"[a-zA-Z\u00C0-\u017F]{4,}.*[a-zA-Z\u00C0-\u017F]{4,}", compact):
            score += 1
        if "copyright" in normalized or "direitos reservados" in normalized:
            score -= 8
        if re.fullmatch(r"[\W\d_]+", compact):
            score -= 6
        if compact in {"0", "0,0", "0.0"}:
            score -= 6
        if len(words) <= 2 and not any(term in normalized for term in relevance_terms):
            score -= 4

        prioritized.append((score, index, compact))

    prioritized.sort(key=lambda item: (-item[0], item[1]))
    chosen = []
    for score, _index, compact in prioritized:
        if score < 1 and chosen:
            continue
        if compact not in chosen:
            chosen.append(compact)
        if len(chosen) >= limit:
            break

    if chosen:
        return chosen

    relaxed = []
    for line in lines:
        compact = re.sub(r"\s+", " ", line).strip()
        normalized = _normalize_text_for_match(compact)
        if not compact or len(compact) < 8:
            continue
        if re.match(r"^https?://", compact, flags=re.IGNORECASE):
            continue
        if "http://" in compact.lower() or "https://" in compact.lower():
            continue
        if (
            "direitos reservados" in normalized
            or "copyright" in normalized
            or "leia mais no texto original" in normalized
        ):
            continue
        if compact not in relaxed:
            relaxed.append(compact)
        if len(relaxed) >= limit:
            break

    if relaxed:
        return relaxed

    return chosen


def _is_generic_github_line(normalized: str) -> bool:
    if not normalized:
        return True

    exact_noise = {
        "repository navigation",
        "code",
        "issues",
        "pull requests",
        "actions",
        "discussions",
        "agents",
        "security",
        "insights",
        "projects",
        "wiki",
        "releases",
        "packages",
        "overview",
        "repositories",
        "stars",
        "followers",
        "following",
        "navegacao do usuario",
        "visao geral",
        "repositorios",
        "repositorios",
        "popular repositories",
        "pinned",
        "contributions",
        "contribuicoes",
    }
    if normalized in exact_noise:
        return True

    contains_noise = (
        "skip to content",
        "ir para o conte",
        "sign in",
        "sign up",
        "repository navigation",
        "navegacao do usuario",
        "jump to",
        "search code",
        "search issues",
        "github stars",
    )
    return any(token in normalized for token in contains_noise)


def _extract_github_focus_lines(lines, page_url: str = "", limit: int = 5) -> list[str]:
    repo_name = _parse_github_repo_from_url(page_url)
    profile_name = _parse_github_profile_from_url(page_url)
    prioritized = []

    for index, line in enumerate(lines):
        compact = re.sub(r"\s+", " ", line).strip()
        normalized = _normalize_text_for_match(compact)
        if not compact or len(compact) < 4:
            continue
        if _is_generic_github_line(normalized):
            continue
        if "http://" in compact.lower() or "https://" in compact.lower():
            continue
        if normalized.startswith("git clone"):
            continue

        score = 0
        if len(compact) >= 24:
            score += 2
        if len(compact) >= 50:
            score += 2
        if any(token in normalized for token in (
            "readme", "sobre", "about", "descricao", "description", "getting started",
            "instal", "installation", "setup", "como usar", "usage", "feature",
            "features", "topic", "python", "ai", "vision", "automation", "agent",
            "screen", "project", "projeto", "requirements", "requisitos", "example",
            "exemplo", "quick start", "overview", "demo"
        )):
            score += 6
        if repo_name and any(piece in normalized for piece in _normalize_text_for_match(repo_name).split("/")):
            score += 2
        if profile_name and _normalize_text_for_match(profile_name) in normalized:
            score += 1
        if re.search(r"[a-zA-Z\u00C0-\u017F]{4,}.*[a-zA-Z\u00C0-\u017F]{4,}", compact):
            score += 1
        if re.search(r"[.!:]", compact):
            score += 1
        if re.search(r"^(readme|about|descricao|description|installation|setup|usage|features|overview)\b", normalized):
            score += 3
        if any(token in normalized for token in ("followers", "following", "stars", "repositories", "overview", "contributions")):
            score -= 3
        if len(compact) <= 18:
            score -= 2
        if re.fullmatch(r"[\W\d_]+", compact):
            score -= 4

        prioritized.append((score, index, compact))

    prioritized.sort(key=lambda item: (-item[0], item[1]))
    chosen = []
    for score, _index, compact in prioritized:
        if score < 1 and chosen:
            continue
        if compact not in chosen:
            chosen.append(compact)
        if len(chosen) >= limit:
            break

    return chosen


def _detect_screen_category(lines, page_url: str = "", page_title: str = "") -> str:
    normalized_blob = " ".join(_normalize_text_for_match(line) for line in lines if line)
    parsed = urlparse(page_url or "")
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    title_blob = _normalize_text_for_match(page_title)

    if "github.com" in host:
        return "repositorio github"

    if ("youtube.com" in host or "youtu.be" in host) and ("/watch" in path or "youtube" in title_blob):
        return "video youtube"

    if (
        "investidor10.com.br" in host
        or any(
            token in title_blob
            for token in ("investidor10", "patrimonio", "valor investido", "rentabilidade", "proventos", "dividendos")
        )
    ):
        return "financas"

    if any(
        token in host
        for token in ("poder360", "g1.globo", "cnnbrasil", "uol.com.br", "folha.uol", "estadao", "bbc.com")
    ) or any(token in title_blob for token in ("noticia", "jornal", "reportagem", "politica", "internacional")):
        return "noticia"

    category_patterns = [
        ("repositorio github", ("repository navigation", "pull requests", "issues", "actions", "discussions", "github")),
        ("video youtube", ("up next", "youtube", "inscrito", "inscrever-se", "comentarios", "comentários")),
        ("financas", ("investidor10", "patrimonio", "valor investido", "rentabilidade", "proventos", "dividendos", "saldo", "preco medio")),
        ("noticia", ("noticia", "jornal", "reportagem", "publicado", "atualizado", "leia mais")),
        ("smartphones", ("smartphone", "celular", "iphone", "galaxy", "redmi", "motorola", "oppo", "realme")),
        ("notebooks", ("notebook", "ideapad", "vivobook", "aspire", "inspiron", "thinkpad", "macbook")),
        ("lavadoras", ("lavadora", "lava loucas", "lava-loucas", "lava e seca", "samsung ww", "electrolux")),
        ("televisores", ("smart tv", "televis", "polegadas", "suporte articulado", "monitor")),
        ("relogios", ("relogio", "relogios", "watch", "smartwatch", "amazfit", "mi band")),
    ]

    for category, patterns in category_patterns:
        if any(pattern in normalized_blob for pattern in patterns):
            return category

    return ""


def _content_showcase(lines, limit: int = 3) -> list[str]:
    showcase = []
    for line in lines:
        compact = re.sub(r"\s+", " ", line).strip()
        if len(compact) > 110:
            compact = compact[:107].rstrip() + "..."
        if compact and compact not in showcase:
            showcase.append(compact)
        if len(showcase) >= limit:
            break
    return showcase


def _extract_finance_focus_lines(lines, limit: int = 5) -> list[str]:
    prioritized = []
    finance_tokens = (
        "patrimonio",
        "patrimônio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
        "dividendos",
        "saldo",
        "carteira",
        "preco medio",
        "preço médio",
        "lucro",
        "prejuizo",
        "prejuízo",
        "aporte",
        "acao",
        "ações",
        "fii",
        "ticker",
        "cotacao",
        "cotação",
    )

    for index, line in enumerate(lines):
        compact = re.sub(r"\s+", " ", line).strip()
        normalized = _normalize_text_for_match(compact)
        if not compact or len(compact) < 3:
            continue
        if normalized.isdigit():
            continue
        if re.match(r"^https?://", compact, flags=re.IGNORECASE):
            continue

        score = 0
        if any(token in normalized for token in finance_tokens):
            score += 6
        if re.search(r"r\$\s*[\d\.\,]+", compact, flags=re.IGNORECASE):
            score += 5
        if "%" in compact:
            score += 3
        if len(normalized.split()) >= 2:
            score += 1
        if compact in {"0", "0,0", "0.0"}:
            score -= 6

        prioritized.append((score, index, compact))

    prioritized.sort(key=lambda item: (-item[0], item[1]))
    chosen = []
    for score, _index, compact in prioritized:
        if score < 2 and chosen:
            continue
        if compact not in chosen:
            chosen.append(compact)
        if len(chosen) >= limit:
            break

    return chosen


def _extract_finance_metrics(lines, limit: int = 7) -> list[str]:
    labels = (
        "patrimonio",
        "patrimonio total",
        "valor investido",
        "valor atual",
        "saldo",
        "rentabilidade",
        "lucro",
        "prejuizo",
        "proventos",
        "dividendos",
        "aporte",
        "preco medio",
        "cotacao",
        "carteira",
        "total",
    )
    value_re = re.compile(r"(?:r\$\s*)?[-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})|[-+]?\d+(?:,\d+)?\s*%", re.IGNORECASE)
    candidates = []
    seen = set()

    compact_lines = [re.sub(r"\s+", " ", line or "").strip() for line in lines if str(line or "").strip()]
    for index, line in enumerate(compact_lines):
        normalized = _normalize_text_for_match(line)
        if not normalized:
            continue
        if "http" in normalized or "cookie" in normalized or "direitos reservados" in normalized:
            continue

        has_label = any(label in normalized for label in labels)
        values = value_re.findall(line)
        score = 0
        metric = ""

        if has_label and values:
            score = 10
            metric = line
        elif has_label and index + 1 < len(compact_lines):
            next_line = compact_lines[index + 1]
            next_values = value_re.findall(next_line)
            if next_values:
                score = 9
                metric = f"{line}: {next_line}"
        elif values and index > 0:
            prev_line = compact_lines[index - 1]
            prev_norm = _normalize_text_for_match(prev_line)
            if any(label in prev_norm for label in labels):
                score = 8
                metric = f"{prev_line}: {line}"

        if not metric:
            continue

        normalized_metric = _normalize_text_for_match(metric)
        if normalized_metric in seen:
            continue

        if len(metric) > 160:
            metric = metric[:157].rstrip() + "..."
        candidates.append((score, index, metric))
        seen.add(normalized_metric)

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [metric for _score, _index, metric in candidates[:limit]]


def _merge_screen_lines(primary_lines, secondary_lines, limit: int = 12) -> list[str]:
    merged = []
    seen = set()

    for group in (primary_lines or [], secondary_lines or []):
        for source in group:
            compact = re.sub(r"\s+", " ", source or "").strip()
            normalized = _normalize_text_for_match(compact)
            if not compact or not normalized or normalized in seen:
                continue
            merged.append(compact)
            seen.add(normalized)
            if len(merged) >= limit:
                return merged

    return merged


def _items_are_navigation_heavy(lines, page_url: str = "", page_title: str = "") -> bool:
    if not lines:
        return True

    category = _detect_screen_category(lines, page_url=page_url, page_title=page_title)
    if category in {"repositorio github", "video youtube", "financas"}:
        return True

    generic_hits = 0
    useful_hits = 0
    for line in lines:
        normalized = _normalize_text_for_match(line)
        if not normalized:
            continue
        if _is_generic_github_line(normalized):
            generic_hits += 1
        if len(normalized.split()) >= 4:
            useful_hits += 1
        if any(token in normalized for token in {"readme", "sobre", "descricao", "description", "instal", "usage", "projeto", "project"}):
            useful_hits += 2

    return generic_hits >= max(2, useful_hits)


def _read_screen_content_lines(
    item_limit: int,
    page_limit: int,
    page_url: str,
    page_title: str,
):
    items = _read_browser_elements(limit=item_limit) or []
    item_lines = [item["text"] for item in items]
    item_quality = _screen_lines_quality(item_lines)
    category = _detect_screen_category([], page_url=page_url, page_title=page_title)
    prefer_page_text = (
        not items
        or _items_are_navigation_heavy(item_lines, page_url=page_url, page_title=page_title)
        or item_quality < 24
        or category in {"financas", "noticia"}
    )

    page_lines = []
    best_page_score = 0
    if prefer_page_text:
        if _browser_context_recently_changed():
            time.sleep(0.35)

        first_pass = _read_page_text_via_clipboard(limit=page_limit, page_url=page_url, page_title=page_title)
        page_lines = first_pass
        best_page_score = _screen_lines_quality(first_pass)

        need_second_pass = _browser_context_recently_changed(2.0) or not first_pass or best_page_score < 24
        if need_second_pass:
            time.sleep(0.25)
            second_pass = _read_page_text_via_clipboard(limit=page_limit, page_url=page_url, page_title=page_title)
            second_score = _screen_lines_quality(second_pass)
            if second_score > best_page_score:
                page_lines = second_pass
                best_page_score = second_score

    combined_lines = _merge_screen_lines(page_lines, item_lines, limit=max(item_limit, page_limit))
    combined_quality = _screen_lines_quality(combined_lines)

    return {
        "items": items,
        "item_lines": item_lines,
        "item_quality": item_quality,
        "page_lines": page_lines,
        "page_quality": best_page_score,
        "combined_lines": combined_lines,
        "combined_quality": combined_quality,
        "prefer_page_text": prefer_page_text,
    }


def _trim_detail_text(text: str, max_length: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 3].rstrip() + "..."


def _summarize_screen_lines(lines, page_url: str = "", page_title: str = "") -> str:
    if not lines:
        return "Nao consegui extrair um resumo confiavel da tela."

    normalized_lines = [_normalize_text_for_match(line) for line in lines if line]
    category = _detect_screen_category(lines, page_url=page_url, page_title=page_title)
    clean_title = _clean_browser_title(page_title)
    title_content = _parse_title_content(clean_title, page_url)

    if category == "repositorio github":
        repo_name = _parse_github_repo_from_url(page_url)
        profile_name = _parse_github_profile_from_url(page_url)
        title_content = _strip_repo_prefix_from_title(title_content, repo_name)
        showcase = _content_showcase(_extract_github_focus_lines(lines, page_url=page_url, limit=4), limit=3)
        if repo_name and title_content and title_content.lower() != repo_name.lower():
            return f"É o repositorio {repo_name} no GitHub. Pelo titulo, o foco parece ser: {title_content}. No conteudo visivel, vejo: " + "; ".join(showcase) + "."
        if repo_name and showcase:
            return f"É o repositorio {repo_name} no GitHub. No conteudo visivel, vejo: " + "; ".join(showcase) + "."
        if repo_name:
            return f"É o repositorio {repo_name} no GitHub. Estou vendo a navegacao principal com Code, Issues, Pull requests, Discussions e Actions."
        if profile_name and title_content:
            return f"É o perfil {profile_name} no GitHub. Pelo titulo, o foco parece ser: {title_content}."
        if profile_name and showcase:
            return f"É o perfil {profile_name} no GitHub. No que ficou visivel, vejo: " + "; ".join(showcase) + "."
        return "Parece um repositorio no GitHub. Estou vendo a navegacao principal e parte do conteudo do projeto."

    if category == "video youtube":
        title = title_content or clean_title or "um video no YouTube"
        showcase = _content_showcase([line for line in lines if _normalize_text_for_match(line) not in {"up next", "youtube"}], limit=2)
        if showcase:
            return f"Parece a pagina de um video no YouTube: {title}. Na tela, vejo: " + "; ".join(showcase) + "."
        return f"Parece a pagina de um video no YouTube: {title}."

    if category == "noticia":
        showcase = _content_showcase(_extract_generic_focus_lines(lines, page_url=page_url, page_title=page_title, limit=6), limit=4)
        if title_content and showcase:
            return f"Parece uma noticia. O titulo sugere: {title_content}. Pontos principais visiveis: " + "; ".join(showcase) + "."
        if title_content:
            return f"Parece uma noticia. O titulo sugere: {title_content}."
        if showcase:
            return "Parece uma noticia. Pontos principais visiveis: " + "; ".join(showcase) + "."
        return "Parece uma noticia, mas ainda nao capturei o trecho principal com confianca."

    if category == "financas":
        showcase = _content_showcase(_extract_finance_focus_lines(lines, limit=5), limit=4)
        if title_content and showcase:
            return f"Parece uma pagina financeira. Pelo titulo, o foco parece ser: {title_content}. Pontos uteis visiveis: " + "; ".join(showcase) + "."
        if showcase:
            return "Parece uma pagina financeira. Pontos uteis visiveis: " + "; ".join(showcase) + "."
        if title_content:
            return f"Parece uma pagina financeira. Pelo titulo, o foco parece ser: {title_content}."
        return "Parece uma pagina financeira, mas ainda nao consegui capturar os valores e rotulos mais importantes."

    pure_price_lines = 0
    for line in lines:
        line_lower = line.lower()
        if re.search(r"r\$\s*\d|\d+,\d{2}", line_lower) and not re.search(r"[a-zA-Z\u00C0-\u017F]{4,}", line):
            pure_price_lines += 1
        if "sem juros" in line_lower or "vez" in line_lower:
            pure_price_lines += 1

    if pure_price_lines >= max(3, len(lines) // 2):
        return "Vejo principalmente precos e parcelas. A tela parece comercial, mas ainda nao peguei bem os nomes principais dos itens."

    showcase = _content_showcase(_extract_generic_focus_lines(lines, page_url=page_url, page_title=page_title, limit=5), limit=3)

    if category == "financas":
        visible = _content_showcase(_extract_finance_focus_lines(lines, limit=6), limit=5)
        if title_content and visible:
            return f"Na tela esta uma pagina financeira. Pelo titulo, ela parece ser sobre {title_content}. Do que ficou visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        if visible:
            return "Na tela esta uma pagina financeira. Do que ficou visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        if title_content:
            return f"Na tela esta uma pagina financeira. Pelo titulo, ela parece ser sobre {title_content}, mas ainda nao capturei os valores e rotulos principais."
        return "Na tela esta uma pagina financeira, mas ainda nao capturei os valores e rotulos principais."

    if category in {"smartphones", "notebooks", "lavadoras", "televisores", "relogios"}:
        return f"Parece uma lista de {category}. Destaques: " + "; ".join(showcase) + "."

    if any("repository navigation" in line or "pull requests" in line for line in normalized_lines):
        return "Parece uma pagina de repositorio com navegacao e abas principais, mais do que conteudo detalhado do projeto."

    if title_content and title_content not in showcase and showcase:
        return f"Pelo titulo da pagina, o foco parece ser: {title_content}. Na tela, vejo: " + "; ".join(showcase) + "."

    if title_content and not showcase:
        return f"Pelo titulo da pagina, o foco parece ser: {title_content}."

    if not showcase:
        return "Ainda nao consegui separar os pontos mais relevantes dessa pagina."

    return f"Vejo {len(lines)} itens principais na tela. Destaques: " + "; ".join(showcase) + "."


def _explain_screen_lines(lines, page_url: str = "", page_title: str = "") -> str:
    if not lines:
        return "Ainda nao consegui extrair detalhes confiaveis da tela."

    category = _detect_screen_category(lines, page_url=page_url, page_title=page_title)
    clean_title = _clean_browser_title(page_title)
    title_content = _trim_detail_text(_parse_title_content(clean_title, page_url), max_length=260)
    showcase = _content_showcase(_extract_generic_focus_lines(lines, page_url=page_url, page_title=page_title, limit=6), limit=5)

    if category == "repositorio github":
        repo_name = _parse_github_repo_from_url(page_url)
        profile_name = _parse_github_profile_from_url(page_url)
        title_content = _strip_repo_prefix_from_title(title_content, repo_name)
        visible = _content_showcase(_extract_github_focus_lines(lines, page_url=page_url, limit=6), limit=5)

        if repo_name:
            if title_content and visible:
                return f"Na tela está o repositório {repo_name}. Pelo título, ele parece ser sobre {title_content}. Do que ficou visível, os pontos mais úteis são: " + "; ".join(visible) + "."
            if title_content:
                return f"Na tela está o repositório {repo_name}. Pelo título, ele parece ser sobre {title_content}."
            if visible:
                return f"Na tela está o repositório {repo_name}. Do que ficou visível, os pontos mais úteis são: " + "; ".join(visible) + "."
            return f"Na tela está o repositório {repo_name}. Ainda estou vendo mais a moldura do GitHub do que README ou conteúdo do projeto."

        if profile_name:
            if title_content and visible:
                return f"Na tela está o perfil {profile_name} no GitHub. Pelo título, ele parece ser sobre {title_content}. No trecho visível, encontrei: " + "; ".join(visible) + "."
            if visible:
                return f"Na tela está o perfil {profile_name} no GitHub. No trecho visível, encontrei: " + "; ".join(visible) + "."
            return f"Na tela está o perfil {profile_name} no GitHub. Estou vendo visão geral, repositórios e navegação principal do perfil."

        if title_content and visible:
            return f"Na tela está uma página do GitHub. Pelo título, ela parece ser sobre {title_content}. No trecho visível, encontrei: " + "; ".join(visible) + "."
        if visible:
            return f"Na tela está uma página do GitHub. No trecho visível, encontrei: " + "; ".join(visible) + "."
        return "Na tela está uma página do GitHub, mas ainda com pouco conteúdo útil exposto."

    if category == "video youtube":
        title = title_content or clean_title or "um vídeo no YouTube"
        filtered = [line for line in showcase if _normalize_text_for_match(line) not in {"up next", "youtube"}]
        if filtered:
            return f"Na tela está a página de vídeo {title}. No que ficou visível, encontrei: " + "; ".join(filtered[:3]) + "."
        return f"Na tela está a página de vídeo {title}."

    if category == "noticia":
        visible = _content_showcase(_extract_generic_focus_lines(lines, page_url=page_url, page_title=page_title, limit=8), limit=5)
        if title_content and visible:
            return f"Na tela parece haver uma noticia sobre {title_content}. Do trecho visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        if title_content:
            return f"Na tela parece haver uma noticia sobre {title_content}."
        if visible:
            return "Na tela parece haver uma noticia. Do trecho visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        return "Na tela parece haver uma noticia, mas ainda nao separei o corpo principal do restante da pagina."

    if category in {"smartphones", "notebooks", "lavadoras", "televisores", "relogios"}:
        if title_content and title_content not in showcase:
            return f"Parece uma lista de {category}. Pelo título da página, o foco parece ser {title_content}. Entre os itens visíveis, vejo: " + "; ".join(showcase[:4]) + "."
        return f"Parece uma lista de {category}. Entre os itens visíveis, vejo: " + "; ".join(showcase[:4]) + "."

    if category == "financas":
        visible = _content_showcase(_extract_finance_focus_lines(lines, limit=6), limit=5)
        if title_content and visible:
            return f"Na tela esta uma pagina financeira. Pelo titulo, ela parece ser sobre {title_content}. Do que ficou visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        if visible:
            return "Na tela esta uma pagina financeira. Do que ficou visivel, os pontos mais uteis sao: " + "; ".join(visible) + "."
        if title_content:
            return f"Na tela esta uma pagina financeira. Pelo titulo, ela parece ser sobre {title_content}, mas ainda nao capturei os valores e rotulos principais."
        return "Na tela esta uma pagina financeira, mas ainda nao capturei os valores e rotulos principais."

    if title_content and showcase:
        return f"Pelo título da página, o foco parece ser {title_content}. No conteúdo visível, encontrei: " + "; ".join(showcase[:4]) + "."

    if title_content:
        summary = _summarize_screen_lines(lines, page_url=page_url, page_title=page_title)
        if summary and "nao consegui" not in _normalize_text_for_match(summary):
            return summary
        return f"Pelo titulo da pagina, o foco parece ser {title_content}, mas ainda nao separei detalhes confiaveis na area visivel."

    if not showcase:
        return "Ainda nao consegui separar detalhes confiaveis da area visivel da tela."

    return f"No conteúdo visível, encontrei: " + "; ".join(showcase[:4]) + "."


def _should_auto_summarize(lines, quality_score: int, page_url: str = "", page_title: str = "") -> bool:
    if not lines:
        return False

    if _detect_screen_category(lines, page_url=page_url, page_title=page_title) in {"repositorio github", "video youtube", "financas", "noticia"}:
        return True

    summary_hint = _summarize_screen_lines(lines, page_url=page_url, page_title=page_title).lower()
    if "precos e parcelas" in summary_hint:
        return True

    if quality_score < 22:
        return True

    long_lines = sum(1 for line in lines if len(line) >= 70)
    if len(lines) >= 6 and long_lines >= 4:
        return True

    if len("; ".join(lines)) >= 520:
        return True

    return False


def _investment_screen_summary(lines, page_url: str = "", page_title: str = "") -> str:
    category = _detect_screen_category(lines, page_url=page_url, page_title=page_title)
    title_content = _parse_title_content(_clean_browser_title(page_title), page_url)
    metrics = _extract_finance_metrics(lines, limit=7)
    focus_lines = _extract_finance_focus_lines(lines, limit=7)

    if category != "financas" and not metrics:
        return "Não parece ser uma tela financeira. Abra sua carteira, ativo ou página de investimentos e peça de novo."

    if metrics:
        intro = "Resumo financeiro da tela"
        if title_content:
            intro += f" ({_trim_detail_text(title_content, max_length=90)})"
        return (
            intro
            + ": "
            + "; ".join(metrics)
            + ". Dados lidos da tela atual; não é recomendação de compra ou venda."
        )

    if focus_lines:
        return (
            "Modo investimentos: encontrei uma página financeira, mas os valores principais não ficaram bem pareados com rótulos. "
            "Pontos visíveis: "
            + "; ".join(_content_showcase(focus_lines, limit=5))
            + "."
        )

    return "Modo investimentos: a página parece financeira, mas ainda não capturei patrimônio, rentabilidade, proventos ou posições com clareza."


def _rank_page_text_lines(text: str, limit: int = 10, page_url: str = "", page_title: str = ""):
    ignore_patterns = (
        "javascript",
        "cookie",
        "politica de privacidade",
        "politica de cookies",
        "termos de uso",
        "menu",
        "entrar",
        "minha conta",
        "sacola",
        "carrinho",
        "buscar",
        "pesquisar",
        "departamentos",
        "atendimento",
        "central de",
        "compre pelo",
        "formas de pagamento",
        "pular navegacao",
        "pular navegação",
        "imagem do avatar",
        "avatar",
        "login",
        "memoria ram",
        "cupom",
        "sem juros",
        "cashback",
        "desconto",
        "direitos reservados",
        "copyright",
        "leia mais no texto original",
    )
    category_noise = {
        "celulares",
        "celular",
        "a celular",
        "celulares e smartphones",
        "samsung",
        "motorola",
        "xiaomi",
        "apple",
        "iphone",
    }
    product_words = {
        "celular",
        "smartphone",
        "notebook",
        "iphone",
        "galaxy",
        "moto",
        "realme",
        "xiaomi",
        "redmi",
        "samsung",
        "motorola",
        "lenovo",
        "acer",
        "dell",
        "positivo",
        "tablet",
    }
    spec_words = {
        "gb",
        "ram",
        "mah",
        "tela",
        "hz",
        "nfc",
        "ip54",
        "resistencia",
        "camera",
        "processador",
    }
    finance_tokens = {
        "investidor10",
        "carteira",
        "wallet",
        "patrimonio",
        "patrimônio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
        "dividendos",
        "saldo",
        "preco medio",
        "preço medio",
        "preço médio",
        "lucro",
        "prejuizo",
        "prejuízo",
        "aporte",
        "ticker",
        "fii",
        "acao",
        "ações",
        "cotacao",
        "cotação",
    }
    page_category = _detect_screen_category([], page_url=page_url, page_title=page_title)
    finance_category = page_category == "financas"
    priority_category = page_category in {"repositorio github", "video youtube", "financas", "noticia"}
    relevance_terms = _relevance_terms_from_context(page_url=page_url, page_title=page_title)
    candidates = []
    seen = set()

    for index, raw_line in enumerate((text or "").splitlines()):
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = _strip_gallery_suffix(line)

        if len(line) < 4 or len(line) > 180:
            continue

        normalized = _normalize_text_for_match(line)
        if not normalized or normalized in seen:
            continue

        if normalized.isdigit():
            continue

        if re.match(r"^https?://", line, flags=re.IGNORECASE):
            continue

        words = normalized.split()
        has_price = bool(re.search(r"r\$\s*\d|\d+,\d{2}", line.lower()))
        price_only = bool(re.match(r"^r\$\s*[\d\.\,]+$", line.lower()))
        looks_like_slug = line.count("-") >= 2 and " " not in line.strip()
        has_product_word = any(word in product_words for word in words)
        has_spec_word = any(word in spec_words for word in words)
        has_finance_word = any(token in normalized for token in finance_tokens)
        has_percent = "%" in line
        has_currency = bool(re.search(r"r\$\s*[\d\.\,]+", line, flags=re.IGNORECASE))
        has_relevance_word = any(term in normalized for term in relevance_terms)

        if looks_like_slug:
            continue

        if price_only and not finance_category:
            continue

        if normalized in category_noise:
            continue

        if len(words) <= 2 and not has_price and not finance_category:
            continue

        if len(words) <= 3 and has_spec_word and not has_product_word and not has_price and not finance_category:
            continue

        if any(pattern in normalized for pattern in ignore_patterns):
            continue

        if "lei" in normalized and "9 610 98" in normalized:
            continue

        if re.match(r"^\d+x\s+de\s+r\$", line.lower()) and not finance_category:
            continue

        if finance_category:
            score = 0
            if has_finance_word:
                score += 8
            if has_currency:
                score += 5
            if has_percent:
                score += 4
            if len(words) >= 2:
                score += 1
            if normalized in {"0", "0,0", "0.0"}:
                score -= 8
            if score < 2:
                continue
        else:
            score = 0
            if has_product_word:
                score += 6
            if has_spec_word:
                score += 2
            if has_relevance_word:
                score += 7
            if len(words) >= 3:
                score += 2
            if len(words) >= 6:
                score += 1
            if has_price:
                score += 1
            if len(words) <= 2 and not has_relevance_word and not has_product_word:
                score -= 5
            if page_category == "repositorio github":
                if any(token in normalized for token in ("readme", "about", "sobre", "descricao", "description", "instalacao", "installation", "usage", "features", "projeto", "project")):
                    score += 9
                if any(token in normalized for token in ("git clone", "repository navigation", "pull requests", "issues", "actions")):
                    score -= 8
            if page_category == "video youtube":
                if any(token in normalized for token in ("inscrever", "up next", "compartilhar", "comentarios")):
                    score -= 5
                if len(words) >= 4:
                    score += 3
            if page_category == "noticia":
                if len(words) >= 8:
                    score += 6
                if any(token in normalized for token in ("publicado", "atualizado", "segundo", "afirma", "disse", "jornal", "governo", "negociacao")):
                    score += 4
                if any(token in normalized for token in ("todos os direitos", "lei", "publicacao redistribuicao")):
                    score -= 10
            if score < 3:
                continue

        if len(line) > 145:
            line = line[:142].rstrip() + "..."

        candidates.append((score, index, line))
        seen.add(normalized)

        if len(candidates) >= max(limit * 6, 60):
            break

    if finance_category:
        ranked = [line for _score, _index, line in sorted(candidates, key=lambda item: (-item[0], item[1]))]
        return _extract_finance_focus_lines(ranked, limit=limit)

    if priority_category:
        return [
            line
            for _score, _index, line in sorted(candidates, key=lambda item: (-item[0], item[1]))[:limit]
        ]

    return [line for _score, _index, line in sorted(candidates, key=lambda item: item[1])[:limit]]


def _selected_text_items(text: str, limit: int = 10):
    product_words = {
        "celular",
        "smartphone",
        "notebook",
        "iphone",
        "galaxy",
        "moto",
        "realme",
        "xiaomi",
        "redmi",
        "samsung",
        "motorola",
        "lenovo",
        "acer",
        "dell",
        "positivo",
        "tablet",
    }
    noise_patterns = (
        "memoria ram",
        "cupom",
        "sem juros",
        "frete",
        "favorito",
        "avaliacao",
        "avaliações",
        "avaliacoes",
        "patrocinado",
    )
    raw_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in (text or "").splitlines()
    ]
    raw_lines = [line for line in raw_lines if line]
    items = []
    seen = set()

    for index, line in enumerate(raw_lines):
        line = _strip_gallery_suffix(line)
        normalized = _normalize_text_for_match(line)
        words = normalized.split()

        if not normalized or normalized in seen:
            continue

        if any(pattern in normalized for pattern in noise_patterns):
            continue

        if line.count("-") >= 2 and " " not in line:
            continue

        if not any(word in product_words for word in words):
            continue

        item = line
        if "r$" not in normalized:
            for extra in raw_lines[index + 1:index + 5]:
                if re.search(r"r\$\s*[\d\.\,]+", extra.lower()) and not re.match(r"^\d+x\s+de\s+r\$", extra.lower()):
                    item = f"{item} - {extra}"
                    break

        if len(item) > 180:
            item = item[:177].rstrip() + "..."

        items.append(item)
        seen.add(normalized)

        if len(items) >= limit:
            break

    if items:
        return items

    return _rank_page_text_lines(text, limit=limit)


def _read_product_cards_via_javascript(limit: int = 10):
    marker = "__ESTAGIARIO_PRODUCTS__\n"
    script = f"""void ((()=>{{
const marker={json.dumps(marker)};
const limit={int(limit)};
const viewportOffsetX=Math.max(0, Math.round((window.outerWidth - window.innerWidth)/2));
const viewportOffsetY=Math.max(0, Math.round(window.outerHeight - window.innerHeight));
const norm=s=>(s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[^\\p{{L}}\\p{{N}}\\s]/gu," ").replace(/\\s+/g," ").trim();
const clean=s=>(s||"").replace(/\\s+/g," ").trim();
const visible=el=>{{
  const r=el.getBoundingClientRect();
  const st=getComputedStyle(el);
  return r.width>35&&r.height>20&&r.bottom>90&&r.top<innerHeight&&st.visibility!=="hidden"&&st.display!=="none";
}};
const productRe=/\\b(celular|smartphone|notebook|iphone|galaxy|xiaomi|redmi|samsung|motorola|realme|lenovo|acer|dell|tablet)\\b/i;
const noiseRe=/\\b(memoria ram|cupom|frete|departamento|categoria|sacola|carrinho|entrar|login|favorito|ordenar|filtrar|avaliacao|avaliações|sem juros|cashback)\\b/i;
const slugText=href=>{{
  try {{
    const url=new URL(href, location.href);
    const part=decodeURIComponent(url.pathname.split("/").filter(Boolean)[0]||"");
    return clean(part.replace(/-/g," "));
  }} catch(e) {{
    return "";
  }}
}};
const bestCardText=a=>{{
  const chunks=[];
  chunks.push(a.innerText, a.getAttribute("aria-label"), a.title);
  const img=a.querySelector("img");
  if(img) chunks.push(img.alt);

  let node=a;
  for(let depth=0; node&&depth<5; depth++, node=node.parentElement) {{
    if(!visible(node)) continue;
    const text=clean(node.innerText||node.textContent||"");
    if(text.length>=8&&text.length<=700) chunks.push(text);
  }}

  let best="";
  for(const raw of chunks) {{
    const text=clean(raw);
    const n=norm(text);
    if(!text||noiseRe.test(n)) continue;
    if(productRe.test(n)||/r\\$\\s*\\d/i.test(text)) {{
      if(text.length>best.length) best=text;
    }}
  }}

  if(best) return best;
  return slugText(a.href);
}};
const anchors=[...document.querySelectorAll("a[href]")];
const rows=[];
const seen=new Set();
for(const a of anchors) {{
  if(!visible(a)) continue;
  const href=a.href||"";
  const raw=bestCardText(a);
  let text=clean(raw);
  if(!text) continue;
  if(text.length>170) text=text.slice(0,167).trim()+"...";
  const n=norm(text);
  const hrefNorm=norm(slugText(href));
  const looksProduct=productRe.test(n)||productRe.test(hrefNorm)||/\\/p\\//.test(href);
  if(!looksProduct||noiseRe.test(n)) continue;
  if(n.length<8||seen.has(href)||seen.has(n)) continue;
  seen.add(href);
  seen.add(n);
  const r=a.getBoundingClientRect();
  rows.push({{
    top:r.top,
    left:r.left,
    x:Math.round(window.screenX + viewportOffsetX + r.left + Math.min(Math.max(r.width/2, 20), 220)),
    y:Math.round(window.screenY + viewportOffsetY + r.top + Math.min(Math.max(r.height/2, 16), 90)),
    text,
    type:"Hyperlink"
  }});
}}
rows.sort((a,b)=>a.top-b.top||a.left-b.left);
const output=marker+JSON.stringify(rows.slice(0,limit));
const fallback=()=>{{
  const ta=document.createElement("textarea");
  ta.value=output;
  ta.style.position="fixed";
  ta.style.left="-9999px";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {{ document.execCommand("copy"); }} catch(e) {{}}
  ta.remove();
}};
if(navigator.clipboard&&navigator.clipboard.writeText) {{
  navigator.clipboard.writeText(output).catch(fallback);
}} else {{
  fallback();
}}
}})())"""

    copied = _run_browser_javascript_and_read_clipboard(script, marker)
    try:
        rows = json.loads(copied)
    except json.JSONDecodeError:
        return []

    items = []
    seen = set()

    for row in rows:
        if not isinstance(row, dict):
            continue

        line = re.sub(r"\s+", " ", str(row.get("text", ""))).strip()
        normalized = _normalize_text_for_match(line)

        if len(line) < 8 or not normalized or normalized in seen:
            continue

        try:
            items.append(
                {
                    "text": line,
                    "x": int(row.get("x")),
                    "y": int(row.get("y")),
                    "type": str(row.get("type", "Hyperlink")).strip() or "Hyperlink",
                    "source": "dom_product",
                }
            )
        except (TypeError, ValueError):
            continue

        seen.add(normalized)

        if len(items) >= limit:
            break

    return items


def _read_page_text_via_clipboard(limit: int = 10, page_url: str = "", page_title: str = ""):
    old_clipboard = _get_clipboard_text()
    copied = ""
    sentinel = f"__ESTAGIARIO_READ_PAGE__{time.monotonic_ns()}__"
    last_sample = ""
    stable_reads = 0

    try:
        _set_clipboard_text(sentinel)
        time.sleep(0.03)
        _shortcut(VK_CONTROL, VK_A)
        time.sleep(0.12)
        _shortcut(VK_CONTROL, VK_C)
        for _ in range(18):
            time.sleep(0.12)
            sample = _get_clipboard_text()
            stripped = sample.strip()
            if not stripped or stripped == sentinel or sample == old_clipboard:
                stable_reads = 0
                continue

            copied = sample
            if sample == last_sample:
                stable_reads += 1
            else:
                last_sample = sample
                stable_reads = 1

            if stable_reads >= 2 and len(stripped) >= 20:
                break
    finally:
        _tap(VK_ESCAPE)
        _set_clipboard_text(old_clipboard)

    ranked_lines = _rank_page_text_lines(copied, limit=limit, page_url=page_url, page_title=page_title)
    if ranked_lines:
        return ranked_lines

    return _useful_page_text_lines(copied, limit=limit, page_url=page_url, page_title=page_title)


def _click_relative_to_app(app_name: str, relative_x: float, relative_y: float, clicks: int = 1):
    rect = _get_app_window_rect(app_name)
    if not rect:
        return False

    left, top, right, bottom = rect
    x = left + ((right - left) * relative_x)
    y = top + ((bottom - top) * relative_y)
    _click(x, y, clicks=clicks)
    return True


def _click_spotify_track_result():
    clicked = False

    for relative_x, relative_y in SPOTIFY_TRACK_RESULT_CLICKS:
        if _click_relative_to_app("Spotify", relative_x, relative_y, clicks=2):
            clicked = True
            time.sleep(0.35)

    return clicked


def _click_spotify_music_filter():
    script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$process = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    Write-Output "__NO_SPOTIFY__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$trueCondition = [System.Windows.Automation.Condition]::TrueCondition
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $trueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim().ToLower()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if ($name -notlike "m*sicas") {
            continue
        }

        if ($rect.IsEmpty -or $rect.Width -lt 20 -or $rect.Height -lt 10) {
            continue
        }

        $relativeLeft = $rect.Left - $rootRect.Left
        $relativeTop = $rect.Top - $rootRect.Top

        # Prefer the search filter row, not library/sidebar labels.
        if ($relativeTop -gt 70 -and $relativeTop -lt 170 -and $relativeLeft -gt 250) {
            $candidates += [pscustomobject]@{
                Element = $element
                Top = $rect.Top
                Left = $rect.Left
            }
        }
    } catch {
    }
}

$candidateItem = $candidates | Sort-Object Top, Left | Select-Object -First 1
if (-not $candidateItem) {
    Write-Output "__NO_FILTER__"
    return
}

try {
    $candidate = $candidateItem.Element
    $pattern = $null
    if ($candidate.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
        $pattern.Invoke()
        Write-Output "__OK__"
        return
    }
} catch {
}

try {
    $rect = $candidateItem.Element.Current.BoundingRectangle
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MouseClicker {
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")]
    public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
}
"@
    $x = [int]($rect.Left + ($rect.Width / 2))
    $y = [int]($rect.Top + ($rect.Height / 2))
    [void][MouseClicker]::SetCursorPos($x, $y)
    Start-Sleep -Milliseconds 80
    [MouseClicker]::mouse_event(2, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 40
    [MouseClicker]::mouse_event(4, 0, 0, 0, 0)
    Write-Output "__OK__"
    return
} catch {
}

Write-Output "__NO_CLICK__"
"""

    try:
        completed = _run_powershell(script, timeout_seconds=8)
    except Exception:
        return False

    return completed.returncode == 0 and "__OK__" in (completed.stdout or "")


def _click_spotify_track_by_name(query: str):
    words = [word for word in re.sub(r"[^\w\s]", " ", query.lower()).split() if len(word) >= 3]
    ps_words = ", ".join(f"'{word}'" for word in words[:4])
    if not ps_words:
        return False

    script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$queryWords = @(__QUERY_WORDS__)
$process = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    Write-Output "__NO_SPOTIFY__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$trueCondition = [System.Windows.Automation.Condition]::TrueCondition
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $trueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).ToLower()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name) {
            continue
        }

        if ($rect.IsEmpty -or $rect.Height -lt 8) {
            continue
        }

        if ($controlType -match "Button") {
            if ($rect.Width -lt 8) {
                continue
            }
        } elseif ($rect.Width -lt 20) {
            continue
        }

        $relativeLeft = $rect.Left - $rootRect.Left
        $relativeTop = $rect.Top - $rootRect.Top
        $isResultArea = $relativeLeft -gt 250 -and $relativeTop -gt 120
        $isPlayButton = $controlType -match "Button" -and ($name.StartsWith("tocar ") -or $name.StartsWith("play "))

        $matches = 0
        foreach ($word in $queryWords) {
            if ($name.Contains($word)) {
                $matches += 1
            }
        }

        if (($matches -gt 0 -or ($isPlayButton -and $isResultArea)) -and $controlType -match "Button|Text|DataItem|ListItem|Custom") {
            $score = $matches * 100

            if ($isPlayButton) {
                $score += 500
            }

            if ($controlType -match "DataItem|ListItem") {
                $score += 20
            }

            # Prefer the result/list area over sidebar/library/global controls.
            if ($isResultArea) {
                $score += 100
            }

            $candidates += [pscustomobject]@{
                Element = $element
                Score = $score
                Top = $rect.Top
                Left = $rect.Left
                ControlType = $controlType
            }
        }
    } catch {
    }
}

$candidateItem = $candidates |
    Sort-Object -Property @{ Expression = "Score"; Descending = $true }, @{ Expression = "Top"; Descending = $false }, @{ Expression = "Left"; Descending = $true } |
    Select-Object -First 1

if (-not $candidateItem) {
    Write-Output "__NO_TRACK_TEXT__"
    return
}

try {
    $candidate = $candidateItem.Element
    $rect = $candidate.Current.BoundingRectangle
    if (-not $rect.IsEmpty) {
        if ($candidateItem.ControlType -match "Button") {
            # The button is often hidden behind the track number. Use it as an anchor
            # and double-click inside the row title area instead.
            $x = [int]($rect.Left + 90)
            $clicks = 2
        } else {
            # Spotify hides the play button behind the track number until hover.
            # A double click on the song row/card is more reliable.
            $x = [int]($rect.Left + [Math]::Min(180, [Math]::Max(40, $rect.Width / 3)))
            $clicks = 2
        }
        $y = [int]($rect.Top + ($rect.Height / 2))
        Write-Output ("__POINT__:{0},{1},{2}" -f $x, $y, $clicks)
        return
    }
} catch {
}

Write-Output "__NO_CLICK__"
"""
    script = script.replace("__QUERY_WORDS__", ps_words)

    try:
        completed = _run_powershell(script)
    except Exception:
        return False

    output = completed.stdout or ""
    if "__OK__" in output:
        return True

    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)(?:,(\d+))?", output)
    if not point_match:
        return False

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    clicks = int(point_match.group(3) or 1)
    user32.SetCursorPos(x, y)
    time.sleep(0.25)
    _click(x, y, clicks=clicks)
    return True


def _click_spotify_first_visible_track():
    script = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$process = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    Write-Output "__NO_SPOTIFY__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$rootRect = $root.Current.BoundingRectangle
$trueCondition = [System.Windows.Automation.Condition]::TrueCondition
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $trueCondition)
$candidates = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim().ToLower()
        $controlType = $element.Current.ControlType.ProgrammaticName
        $rect = $element.Current.BoundingRectangle

        if (-not $name -or $rect.IsEmpty -or $rect.Height -lt 8 -or $rect.Width -lt 8) {
            continue
        }

        $relativeLeft = $rect.Left - $rootRect.Left
        $relativeTop = $rect.Top - $rootRect.Top
        $isResultArea = $relativeLeft -gt 250 -and $relativeTop -gt 120

        if (-not $isResultArea) {
            continue
        }

        $score = 0
        if ($controlType -match "DataItem|ListItem|Custom" -and $name -match "^\d+\s+tocar\s+") {
            $score = 600
        } elseif ($controlType -match "Button" -and ($name.StartsWith("tocar ") -or $name.StartsWith("play "))) {
            $score = 500
        } elseif ($controlType -match "DataItem|ListItem|Custom" -and $name.Contains(" tocar ") -and $name.Contains(" adicionar ")) {
            $score = 450
        }

        if ($score -le 0) {
            continue
        }

        $candidates += [pscustomobject]@{
            Element = $element
            Score = $score
            Top = $rect.Top
            Left = $rect.Left
            ControlType = $controlType
        }
    } catch {
    }
}

$candidateItem = $candidates |
    Sort-Object -Property @{ Expression = "Score"; Descending = $true }, @{ Expression = "Top"; Descending = $false }, @{ Expression = "Left"; Descending = $false } |
    Select-Object -First 1

if (-not $candidateItem) {
    Write-Output "__NO_FIRST_TRACK__"
    return
}

try {
    $rect = $candidateItem.Element.Current.BoundingRectangle
    if (-not $rect.IsEmpty) {
        if ($candidateItem.ControlType -match "Button") {
            $x = [int]($rect.Left + 90)
        } else {
            $x = [int]($rect.Left + [Math]::Min(180, [Math]::Max(80, $rect.Width / 3)))
        }
        $y = [int]($rect.Top + ($rect.Height / 2))
        Write-Output ("__POINT__:{0},{1}" -f $x, $y)
        return
    }
} catch {
}

Write-Output "__NO_CLICK__"
"""

    try:
        completed = _run_powershell(script)
    except Exception:
        return False

    output = completed.stdout or ""
    point_match = re.search(r"__POINT__:(-?\d+),(-?\d+)", output)
    if not point_match:
        return False

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    user32.SetCursorPos(x, y)
    time.sleep(0.25)
    _click(x, y, clicks=2)
    return True


def spotify_diagnostic():
    focus_app("spotify")
    time.sleep(0.3)

    script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$process = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    Write-Output "__NO_SPOTIFY__"
    return
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
if (-not $root) {
    Write-Output "__NO_ROOT__"
    return
}

$trueCondition = [System.Windows.Automation.Condition]::TrueCondition
$elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $trueCondition)
$rows = @()

for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    try {
        $name = ([string]$element.Current.Name).Trim()
        if (-not $name -or $name.Length -lt 2) {
            continue
        }

        $rect = $element.Current.BoundingRectangle
        if ($rect.IsEmpty -or $rect.Width -lt 10 -or $rect.Height -lt 5) {
            continue
        }

        $controlType = $element.Current.ControlType.ProgrammaticName
        $left = [int]$rect.Left
        $top = [int]$rect.Top
        $width = [int]$rect.Width
        $height = [int]$rect.Height
        $safeName = $name.Replace("`r", " ").Replace("`n", " ")

        $rows += [pscustomobject]@{
            Top = $top
            Left = $left
            Text = ("{0} | {1} | x={2} y={3} w={4} h={5}" -f $safeName, $controlType, $left, $top, $width, $height)
        }
    } catch {
    }
}

$rows |
    Sort-Object Top, Left |
    Select-Object -First 120 |
    ForEach-Object { Write-Output $_.Text }
"""

    try:
        completed = _run_powershell(script, timeout_seconds=12)
    except Exception as e:
        return f"Erro no diagnostico do Spotify: {e}"

    output = (completed.stdout or "").strip()
    if "__NO_SPOTIFY__" in output:
        return "Nao encontrei uma janela aberta do Spotify."
    if "__NO_ROOT__" in output:
        return "Nao consegui ler a janela do Spotify."
    if not output:
        return "O diagnostico nao encontrou textos visiveis no Spotify."

    return "Diagnostico Spotify:\n" + output


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


def browser_back():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para voltar."

    user32.keybd_event(VK_MENU, 0, 0, 0)
    time.sleep(0.02)
    _tap(VK_LEFT)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    return "Voltando pagina."


def browser_forward():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para avancar."

    user32.keybd_event(VK_MENU, 0, 0, 0)
    time.sleep(0.02)
    _tap(VK_RIGHT)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    return "Avancando pagina."


def browser_refresh():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para atualizar."

    _tap(VK_F5)
    return "Atualizando pagina."


def browser_open_first_result():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para abrir o resultado."

    if _click_first_browser_link():
        return "Abrindo primeiro resultado."

    _tap(VK_TAB)
    time.sleep(0.08)
    _tap(VK_RETURN)
    return "Abrindo primeiro resultado."


def browser_open_focused_item():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para abrir."

    _tap(VK_RETURN)
    return "Abrindo item selecionado."


def browser_click_center():
    rect = _get_browser_window_rect()
    if not rect:
        return "Nao encontrei um navegador aberto para clicar."

    left, top, right, bottom = rect
    _click(left + ((right - left) / 2), top + ((bottom - top) / 2))
    return "Clicando no centro da pagina."


def browser_click_text(query: str):
    if not query:
        return "Clicar em que texto?"

    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para clicar."

    if _click_browser_element_by_text(query):
        return f"Clicando em {query}."

    return f"Nao encontrei {query} visivel na pagina."


def browser_click_listed_item(index: int):
    if index < 1:
        return "Qual item da lista?"

    if _activate_browser_window():
        _refresh_browser_context()

    if index > len(LAST_BROWSER_ELEMENTS):
        browser_describe_screen()

    if index > len(LAST_BROWSER_ELEMENTS):
        return "Li a tela, mas nao encontrei esse item na lista atual."

    item = LAST_BROWSER_ELEMENTS[index - 1]
    if item.get("x") is None or item.get("y") is None:
        if _click_page_item_by_text(item["text"]):
            return f"Tentando abrir o item {index}: {item['text']}."

        query = _short_click_query(item["text"])

        if _click_browser_item_from_text(item["text"]):
            return f"Clicando no item {index}: {item['text']}."

        if query:
            browser_find(query)
            time.sleep(0.12)
            if _click_browser_item_from_text(item["text"]):
                return f"Clicando no item {index}: {item['text']}."
            return (
                f"Encontrei o texto do item {index}, mas nao consegui clicar direto nele. "
                "Deixei ele procurado na pagina."
            )

        return "Tenho esse item em texto, mas nao consegui transformar em clique."

    _click(item["x"], item["y"])
    return f"Clicando no item {index}: {item['text']}."


def browser_describe_listed_item(index: int):
    if index < 1:
        return "Qual item?"

    if _activate_browser_window():
        _refresh_browser_context()

    if index > len(LAST_BROWSER_ELEMENTS):
        return "Ainda nao tenho esse item na lista. Selecione os produtos e diga: ler selecionado."

    item = LAST_BROWSER_ELEMENTS[index - 1]
    return f"Item {index}: {item['text']}."


def _read_selected_text_from_browser(app_name: str | None = None):
    if app_name:
        if not _activate_window_names([app_name]):
            return None
    elif not _activate_browser_window():
        return None

    old_clipboard = _get_clipboard_text()

    try:
        _set_clipboard_text("")
        _shortcut(VK_CONTROL, VK_C)
        time.sleep(0.25)
        selected = _get_clipboard_text()
    finally:
        _set_clipboard_text(old_clipboard)

    return selected


def _read_full_page_text_from_browser(wait_seconds: float = 0.35, app_name: str | None = None):
    if app_name:
        if not _activate_window_names([app_name]):
            return None
    elif not _activate_browser_window():
        return None

    old_clipboard = _get_clipboard_text()

    try:
        _set_clipboard_text("")
        _shortcut(VK_CONTROL, VK_A)
        time.sleep(0.12)
        _shortcut(VK_CONTROL, VK_C)
        time.sleep(wait_seconds)
        selected = _get_clipboard_text()
    finally:
        _tap(VK_ESCAPE)
        _set_clipboard_text(old_clipboard)

    return selected


def _read_full_page_text_from_foreground(wait_seconds: float = 0.35):
    old_clipboard = _get_clipboard_text()

    try:
        _set_clipboard_text("")
        _shortcut(VK_CONTROL, VK_A)
        time.sleep(0.12)
        _shortcut(VK_CONTROL, VK_C)
        time.sleep(wait_seconds)
        selected = _get_clipboard_text()
    finally:
        _tap(VK_ESCAPE)
        _set_clipboard_text(old_clipboard)

    return selected


def _compact_selected_text(text: str, max_length: int = 650):
    compacted = re.sub(r"\s+", " ", text or "").strip()
    if len(compacted) > max_length:
        return compacted[:max_length - 3].rstrip() + "..."
    return compacted


def browser_read_selection():
    global LAST_SELECTED_TEXT

    selected = _read_selected_text_from_browser()
    if selected is None:
        return "Nao encontrei um navegador aberto para ler a selecao."

    text = _compact_selected_text(selected)
    if not text:
        _clear_browser_snapshot()
        LAST_SELECTED_TEXT = ""
        return "Nao encontrei texto selecionado."

    _clear_browser_snapshot()
    LAST_SELECTED_TEXT = text
    response = "Texto selecionado: " + text
    _remember_browser_analysis(response, lines=[text], source="texto selecionado")
    return response


def _translate_with_ollama(text: str, target_language: str = "portugues do Brasil"):
    prompt = f"""
Voce e um tradutor cuidadoso.
Traduza o texto abaixo para {target_language}.
Se o texto ja estiver em portugues, apenas corrija acentos e pequenos erros obvios sem inventar conteudo.
Responda somente com o texto final.
Nao escreva introducoes como "a traducao e".
Nao use aspas.

Texto:
{text}
""".strip()

    return ask_model(
        prompt,
        timeout_seconds=20,
        num_predict=500,
        temperature=0.1,
    ).strip()


def _clean_translation_output(text: str):
    quote_chars = "\"' \u201c\u201d\u2018\u2019"
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = cleaned.strip(quote_chars)

    prefix_patterns = [
        r"^(?:a\s+)?tradu[c\u00e7][a\u00e3]o\s+(?:do\s+texto\s+)?(?:para\s+portugu[e\u00ea]s(?:\s+do\s+brasil)?\s+)?(?:e|\u00e9|eh)\s*:?\s*",
        r"^em\s+portugu[e\u00ea]s(?:\s+do\s+brasil)?\s*:?\s*",
        r"^texto\s+traduzido\s*:?\s*",
        r"^traduzido\s*:?\s*",
    ]

    for pattern in prefix_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned.strip(quote_chars)


def browser_translate_selection():
    global LAST_SELECTED_TEXT

    selected = _read_selected_text_from_browser()
    if selected is None:
        return "Nao encontrei um navegador aberto para traduzir a selecao."

    text = _compact_selected_text(selected, max_length=1800)
    if not text:
        _clear_browser_snapshot()
        return "Nao encontrei texto selecionado para traduzir."

    LAST_SELECTED_TEXT = text

    try:
        translated = _translate_with_ollama(text)
    except Exception:
        return "Nao consegui traduzir agora. Verifique se o Ollama esta aberto."

    translated = _compact_selected_text(_clean_translation_output(translated), max_length=900)
    if not translated:
        return "Nao consegui gerar a traducao."

    _clear_browser_snapshot()
    return "Traduzi: " + translated


def browser_translate_last_selection():
    if not LAST_SELECTED_TEXT:
        return "Ainda nao tenho um texto guardado. Primeiro diga: ler selecionado."

    try:
        translated = _translate_with_ollama(LAST_SELECTED_TEXT)
    except Exception:
        return "Nao consegui traduzir agora. Verifique se o Ollama esta aberto."

    translated = _compact_selected_text(_clean_translation_output(translated), max_length=900)
    if not translated:
        return "Nao consegui gerar a traducao."

    _clear_browser_snapshot()
    return "Traduzi: " + translated


def browser_read_selected_products():
    global LAST_SELECTED_TEXT

    selected = _read_selected_text_from_browser()
    if selected is None:
        return "Nao encontrei um navegador aberto para ler a selecao."

    LAST_SELECTED_TEXT = _compact_selected_text(selected, max_length=1800)
    items = _selected_text_items(selected, limit=10)
    if not items:
        _clear_browser_snapshot()
        return "Nao consegui ler produtos no texto selecionado."

    _remember_text_items(items)
    rows = [f"{idx}. {line}" for idx, line in enumerate(items, start=1)]
    response = "Li selecionado: " + "; ".join(rows)
    _remember_browser_analysis(response, lines=items, source="texto selecionado")
    return response


def browser_cheapest_listed_item():
    if _activate_browser_window():
        _refresh_browser_context()

    if not LAST_BROWSER_ELEMENTS:
        browser_describe_screen()

    priced_items = []

    for index, item in enumerate(LAST_BROWSER_ELEMENTS, start=1):
        price = _extract_brl_price(item.get("text", ""))
        if price is None or price <= 0:
            continue

        priced_items.append((price, index, item["text"]))

    if not priced_items:
        return "Ainda nao tenho precos claros na lista atual. Tente dizer: o que tem na tela."

    price, index, text = min(priced_items, key=lambda entry: entry[0])
    return f"O mais barato que encontrei e o item {index}: {text}."


def browser_summarize_screen():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para resumir a tela."

    context = _refresh_browser_context()
    page_url = _get_browser_url()
    page_title = _clean_browser_title(_get_foreground_window_title())
    capture = _read_screen_content_lines(item_limit=10, page_limit=18, page_url=page_url, page_title=page_title)
    items = capture["items"]
    lines = capture["combined_lines"]

    if not lines:
        _clear_browser_snapshot(context=context)
        return "Nao consegui resumir a tela atual."

    if items:
        _set_browser_elements(items, context=context)
    else:
        _remember_text_items(lines, context=context)

    response = _screen_summary_intro() + ": " + _summarize_screen_lines(lines, page_url=page_url, page_title=page_title)
    _remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
    return response


def browser_explain_screen():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para detalhar a tela."

    context = _refresh_browser_context()
    page_url = _get_browser_url()
    page_title = _clean_browser_title(_get_foreground_window_title())
    capture = _read_screen_content_lines(item_limit=12, page_limit=22, page_url=page_url, page_title=page_title)
    items = capture["items"]
    lines = capture["combined_lines"]

    if not lines:
        _clear_browser_snapshot(context=context)
        return "Nao consegui detalhar a tela atual."

    if items:
        _set_browser_elements(items, context=context)
    else:
        _remember_text_items(lines, context=context)

    response = "Detalhando a tela: " + _explain_screen_lines(lines, page_url=page_url, page_title=page_title)
    _remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
    return response


def browser_investment_snapshot():
    if not _activate_browser_window():
        return "Não encontrei um navegador aberto para analisar investimentos."

    context = _refresh_browser_context()
    page_url = _get_browser_url()
    page_title = _clean_browser_title(_get_foreground_window_title())
    capture = _read_screen_content_lines(item_limit=14, page_limit=30, page_url=page_url, page_title=page_title)
    items = capture["items"]
    lines = capture["combined_lines"]

    if not lines:
        _clear_browser_snapshot(context=context)
        return "Não consegui ler dados financeiros úteis nessa tela."

    if items:
        _set_browser_elements(items, context=context)
    else:
        _remember_text_items(lines, context=context)

    metrics = _extract_finance_metrics(lines, limit=7)
    response = _investment_screen_summary(lines, page_url=page_url, page_title=page_title)
    save_investment_snapshot(
        summary=response,
        metrics=metrics,
        lines=lines,
        page_url=page_url,
        page_title=page_title,
    )
    _remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title, source="pagina financeira")
    return response


def _visible_wallet_capture_summary_legacy(url: str, close_tab: bool = True):
    app_name = _open_url_in_wallet_browser(url)
    if app_name is None:
        return None

    time.sleep(3.2)

    captured_text = ""
    try:
        captured_text = str(_read_full_page_text_from_foreground(wait_seconds=0.55) or "").strip()
        if not captured_text or "Patrimônio total" not in captured_text:
            captured_text = str(_read_full_page_text_from_browser(wait_seconds=0.55) or "").strip()
        if (not captured_text or "Patrimônio total" not in captured_text) and app_name:
            captured_text = str(_read_full_page_text_from_browser(wait_seconds=0.55, app_name=app_name) or "").strip()
        if not captured_text:
            return None

        extra_sections = []
        for section_label in ("Patrimônio", "Proventos"):
            try:
                if _click_browser_element_by_text(section_label, app_names=[app_name] if app_name else None):
                    time.sleep(2.0)
                    section_text = str(_read_full_page_text_from_foreground(wait_seconds=0.55) or "").strip()
                    if section_text and section_text not in captured_text:
                        extra_sections.append(section_text)
            except Exception:
                continue
        if extra_sections:
            captured_text = "\n".join([captured_text, *extra_sections])

        snapshot = parse_wallet_text_blob(captured_text, url)
        summary = str(snapshot.get("summary", "")).strip()
        if not summary:
            return "Carteira lida pela aba visível e memória atualizada."
        return summary
    except Exception:
        return None
    finally:
        if close_tab:
            try:
                if app_name:
                    if _activate_window_names([app_name]):
                        _shortcut(VK_CONTROL, VK_W)
                else:
                    browser_close_tab()
            except Exception:
                pass


def _visible_wallet_capture_summary(url: str, close_tab: bool = True, max_seconds: float = 12.0):
    app_name = _open_url_in_wallet_browser(url)
    if app_name is None:
        return None

    deadline = time.time() + max(4.0, float(max_seconds or 12.0))
    time.sleep(3.2)

    captured_text = ""
    try:
        captured_text = str(_read_full_page_text_from_foreground(wait_seconds=0.55) or "").strip()
        if not captured_text or "Patrimônio total" not in captured_text:
            captured_text = str(_read_full_page_text_from_browser(wait_seconds=0.55) or "").strip()
        if (not captured_text or "Patrimônio total" not in captured_text) and app_name:
            captured_text = str(_read_full_page_text_from_browser(wait_seconds=0.55, app_name=app_name) or "").strip()
        if not captured_text:
            return None

        extra_sections = []
        for section_label in ("Patrimônio",):
            if time.time() >= deadline:
                break
            try:
                if _click_browser_element_by_text(section_label, app_names=[app_name] if app_name else None):
                    time.sleep(min(1.4, max(0.2, deadline - time.time())))
                    section_text = str(_read_full_page_text_from_foreground(wait_seconds=0.55) or "").strip()
                    if section_text and section_text not in captured_text:
                        extra_sections.append(section_text)
            except Exception:
                continue
        if extra_sections:
            captured_text = "\n".join([captured_text, *extra_sections])

        snapshot = parse_wallet_text_blob(captured_text, url)
        summary = str(snapshot.get("summary", "")).strip()
        if not summary:
            return "Carteira lida pela aba visível e memória atualizada."
        return summary
    except Exception:
        return None
    finally:
        if close_tab:
            try:
                if app_name:
                    if _activate_window_names([app_name]):
                        _shortcut(VK_CONTROL, VK_W)
                else:
                    browser_close_tab()
            except Exception:
                pass


def browser_open_wallet_and_summarize():
    private_wallet_url = str(INVESTIDOR10_PRIVATE_WALLET_URL or "").strip()
    if private_wallet_url and "/wallet/" in private_wallet_url.lower():
        visible_summary = _visible_wallet_capture_summary(private_wallet_url, close_tab=True)
        if visible_summary:
            return "Abri sua carteira do Investidor10. " + visible_summary

    if DEFAULT_INVESTIDOR10_WALLET_URL and "/wallet/" in DEFAULT_INVESTIDOR10_WALLET_URL:
        try:
            snapshot = refresh_wallet_snapshot_auto(force=True)
            summary = str(snapshot.get("summary", "")).strip() or format_public_wallet_refresh_result(force=True)
            return "Abri sua carteira do Investidor10. " + summary
        except Exception:
            visible_summary = _visible_wallet_capture_summary(DEFAULT_INVESTIDOR10_WALLET_URL, close_tab=True)
            if visible_summary:
                return "Abri sua carteira do Investidor10. " + visible_summary

    webbrowser.open(DEFAULT_INVESTIDOR10_WALLET_URL)
    time.sleep(1.5)

    time.sleep(1.0)
    summary = browser_investment_snapshot()
    if INVESTIDOR10_WALLET_URL:
        return "Abri sua carteira do Investidor10. " + summary
    return (
        "Abri a área da carteira do Investidor10. "
        + summary
        + " Para abrir direto no seu link, configure AXEL_INVESTIDOR10_WALLET_URL no arquivo .env."
    )


def browser_describe_screen():
    global LAST_BROWSER_ELEMENTS

    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para ler a tela."

    context = _refresh_browser_context()
    page_url = _get_browser_url()
    page_title = _clean_browser_title(_get_foreground_window_title())
    capture = _read_screen_content_lines(item_limit=10, page_limit=18, page_url=page_url, page_title=page_title)
    items = capture["items"]
    lines = capture["combined_lines"]
    quality = capture["combined_quality"]
    category = _detect_screen_category(lines, page_url=page_url, page_title=page_title)
    prefer_page_text = capture.get("prefer_page_text", False)

    if not lines:
        _clear_browser_snapshot(context=context)
        return "Nao consegui ler itens clicaveis visiveis nessa tela."

    if items:
        _set_browser_elements(items, context=context)
    else:
        _remember_text_items(lines, context=context)

    if category in {"repositorio github", "video youtube", "financas", "noticia"} or prefer_page_text:
        response = _screen_summary_intro() + ": " + _explain_screen_lines(lines, page_url=page_url, page_title=page_title)
        _remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
        return response

    if _should_auto_summarize(lines, quality, page_url=page_url, page_title=page_title):
        response = _screen_summary_intro() + ": " + _summarize_screen_lines(lines, page_url=page_url, page_title=page_title)
        _remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
        return response

    if items:
        rows = [f"{idx}. {item['text']}" for idx, item in enumerate(items, start=1)]
    else:
        rows = [f"{idx}. {line}" for idx, line in enumerate(lines, start=1)]
    response = "Vejo na tela: " + "; ".join(rows)
    _remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
    return response


def browser_read_more():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para ler mais."

    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -550, 0)
    time.sleep(0.25)
    result = browser_describe_screen()

    if result.startswith("Vejo na tela:"):
        return result.replace("Vejo na tela:", "Mais abaixo vejo:", 1)

    if result.startswith("Consegui ler texto da pagina:"):
        return result.replace("Consegui ler texto da pagina:", "Mais abaixo consegui ler:", 1)

    return result


def browser_zoom_in():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para zoom."

    _shortcut(VK_CONTROL, VK_ADD)
    return "Aumentando zoom."


def browser_zoom_out():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para zoom."

    _shortcut(VK_CONTROL, VK_SUBTRACT)
    return "Diminuindo zoom."


def browser_zoom_reset():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para zoom."

    _shortcut(VK_CONTROL, VK_0)
    return "Restaurando zoom."


def browser_search(query: str):
    if not query:
        return "Qual termo voce quer pesquisar?"

    if not _activate_browser_window():
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}", new=2)
        return f"Pesquisando por {query} em uma nova aba."

    _shortcut(VK_CONTROL, VK_L)
    time.sleep(0.05)
    _type_text(query)
    _tap(VK_RETURN)
    return f"Pesquisando por {query} na aba atual."


def browser_find(query: str):
    if not query:
        return "Qual texto voce quer procurar na pagina?"

    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para procurar na pagina."

    _shortcut(VK_CONTROL, VK_F)
    time.sleep(0.05)
    _type_text(query)
    _tap(VK_RETURN)
    return f"Procurando {query} na pagina."


def browser_scroll_down():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_NEXT)
    return "Rolando para baixo."


def browser_scroll_down_small():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -350, 0)
    return "Descendo um pouco."


def browser_scroll_up():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_PRIOR)
    return "Rolando para cima."


def browser_scroll_up_small():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, 350, 0)
    return "Subindo um pouco."


def browser_scroll_top():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_HOME)
    return "Indo para o topo."


def browser_scroll_bottom():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para rolar."

    _tap(VK_END)
    return "Indo para o fim."


def browser_search_site(site: str, query: str):
    if not site or not query:
        return "Qual site e qual pesquisa?"

    site = site.strip()
    query = query.strip()

    if "mercadolivre.com.br" in site:
        webbrowser.open(f"https://lista.mercadolivre.com.br/{quote_plus(query)}", new=2)
        return f"Pesquisando {query} no Mercado Livre em uma nova aba."

    if "magazineluiza.com.br" in site:
        webbrowser.open(f"https://www.magazineluiza.com.br/busca/{quote_plus(query)}/", new=2)
        return f"Pesquisando {query} no Magazine Luiza em uma nova aba."

    if "youtube.com" in site:
        webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}", new=2)
        return f"Pesquisando {query} no YouTube em uma nova aba."

    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query + ' site:' + site)}", new=2)
    return f"Pesquisando {query} em {site} em uma nova aba."


def browser_search_music(service: str, query: str):
    if not query:
        return "Qual musica voce quer procurar?"

    service = (service or "").lower().strip()
    normalized_query = _normalize_text_for_match(query)

    if service == "spotify":
        if normalized_query in SPOTIFY_LIKED_SONGS_QUERIES:
            try:
                os.startfile("spotify:collection:tracks")
                time.sleep(1.0)
                focus_app("spotify")
                return "Abrindo suas músicas curtidas no Spotify."
            except Exception:
                webbrowser.open("https://open.spotify.com/collection/tracks")
                return "Abrindo suas músicas curtidas no Spotify."

        try:
            best_track = spotify_search_track(query)
        except Exception:
            best_track = None

        if best_track:
            return _play_spotify_track_result(query, best_track)

        try:
            spotify_query = f"{SPOTIFY_TRACK_SEARCH_PREFIX}{query}"
            os.startfile(f"spotify:search:{quote(spotify_query)}")
            time.sleep(1.2)
            focus_app("spotify")
            return f"Abrindo a busca por {query} no Spotify."
        except Exception:
            webbrowser.open(f"https://open.spotify.com/search/{quote_plus(query)}")
            return f"Abrindo a busca por {query} no Spotify."

    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"Procurando {query} no YouTube."


def browser_surprise_music(service: str = "spotify"):
    service = (service or "spotify").lower().strip()
    if service != "spotify":
        return "Por enquanto, o modo surpresa musical está preparado para o Spotify."

    return _start_spotify_session(SPOTIFY_SURPRISE_QUERIES, "surpresa", surprise=True)


def browser_music_session(service: str = "spotify", vibe: str = ""):
    service = (service or "spotify").lower().strip()
    if service != "spotify":
        return "Por enquanto, sessões por clima e gênero estão preparadas para o Spotify."

    normalized_vibe = _normalize_text_for_match(vibe)
    queries = SPOTIFY_MUSIC_SESSION_POOLS.get(normalized_vibe)
    if not queries:
        return f"Ainda não tenho uma sessão pronta para {vibe}. Posso tocar uma música específica se você quiser."

    label = SPOTIFY_MUSIC_SESSION_LABELS.get(normalized_vibe, normalized_vibe)
    return _start_spotify_session(queries, label)


def browser_queue_music(service: str, query: str):
    if not query:
        return "Qual música você quer adicionar à fila?"

    service = (service or "").lower().strip()
    if service != "spotify":
        return "Por enquanto, fila automática só está preparada para o Spotify."

    try:
        best_track = spotify_search_track(query)
    except Exception:
        best_track = None

    if not best_track:
        return f"Não encontrei {query} no Spotify para colocar na fila."

    track_uri = str(best_track.get("uri") or "").strip()
    track_name = str(best_track.get("name") or query).strip()
    track_artists = str(best_track.get("artists") or "").strip()
    if track_uri and spotify_add_to_queue(track_uri):
        if track_artists:
            return f"Adicionei {track_name}, de {track_artists}, à fila do Spotify."
        return f"Adicionei {track_name} à fila do Spotify."

    return (
        "Encontrei a música, mas ainda não consigo adicionar à fila sem o OAuth do Spotify com permissão de playback. "
        "Posso abrir ou tocar a faixa por enquanto."
    )


def _current_track_or_message():
    current = spotify_current_playback()
    if not current or not current.get("name"):
        return None, "Não identifiquei uma música tocando agora no Spotify."
    return current, ""


def spotify_like_current_track():
    current, message = _current_track_or_message()
    if not current:
        return message

    track_id = str(current.get("id") or "").strip()
    label = _spotify_track_label(current, "a música atual")
    if track_id and spotify_save_track(track_id):
        return f"Gostei do seu gosto. Salvei {label} nas suas músicas curtidas."

    return f"Encontrei {label}, mas não consegui salvar nas curtidas agora."


def spotify_dislike_current_track():
    current, message = _current_track_or_message()
    if not current:
        return message

    track_id = str(current.get("id") or "").strip()
    label = _spotify_track_label(current, "essa faixa")
    removed = bool(track_id and spotify_remove_saved_track(track_id))
    skipped = spotify_next_track()

    if removed and skipped:
        return f"Entendido. Tirei {label} das curtidas, se estava lá, e pulei para a próxima."
    if skipped:
        return f"Entendido. Pulei {label}. Vamos tentar algo melhor."
    if removed:
        return f"Entendido. Tirei {label} das curtidas, se estava lá."
    return f"Entendi que {label} não agradou, mas não consegui alterar o playback agora."


def spotify_more_like_current_track():
    current, message = _current_track_or_message()
    if not current:
        return message

    artists = str(current.get("artists") or "").strip()
    primary_artist = artists.split(",")[0].strip()
    if not primary_artist:
        return "Eu ouvi a faixa atual, mas não consegui identificar o artista para montar algo parecido."

    try:
        tracks = spotify_search_tracks(f'artist:"{primary_artist}"', limit=6)
    except Exception:
        tracks = []

    current_id = str(current.get("id") or "").strip()
    tracks = [track for track in tracks if str(track.get("id") or "") != current_id]
    if not tracks:
        return f"Tentei puxar mais músicas parecidas com {primary_artist}, mas não encontrei uma fila boa agora."

    first = tracks[0]
    started = bool(first.get("uri") and spotify_start_playback(str(first.get("uri"))))
    if not started:
        started = _spotify_play_track_via_app(str(first.get("name") or primary_artist), str(first.get("name") or ""), str(first.get("artists") or ""))

    queued = []
    for track in tracks[1:SPOTIFY_SESSION_QUEUE_TARGET]:
        if track.get("uri") and spotify_add_to_queue(str(track.get("uri"))):
            queued.append(track)

    if started:
        response = f"Seguindo essa linha: tocando {_spotify_track_label(first)}."
        if queued:
            response += f" Também deixei mais {len(queued)} faixas parecidas na fila."
        return response

    return _play_spotify_track_result(str(first.get("name") or primary_artist), first)


def spotify_less_music_vibe(vibe: str = ""):
    normalized = _normalize_text_for_match(vibe)
    alternatives = {
        "triste": ("alegre", "menos melancólica"),
        "melancolico": ("alegre", "menos melancólica"),
        "melancolica": ("alegre", "menos melancólica"),
        "agitado": ("calmo", "mais calma"),
        "agitada": ("calmo", "mais calma"),
        "pesado": ("calmo", "mais leve"),
        "pesada": ("calmo", "mais leve"),
    }
    target_vibe, label = alternatives.get(normalized, ("calmo", "mais equilibrada"))
    queries = SPOTIFY_MUSIC_SESSION_POOLS.get(target_vibe)
    if not queries:
        return "Consigo ajustar o clima, mas ainda não tenho uma sessão alternativa pronta para isso."
    return _start_spotify_session(queries, label)
