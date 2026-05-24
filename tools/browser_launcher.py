from __future__ import annotations

import os
import subprocess
import webbrowser

EDGE_BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
CHROME_BROWSER_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


def first_existing_browser(candidates, *, path_exists=os.path.exists) -> str:
    for candidate in candidates:
        if candidate and path_exists(candidate):
            return candidate
    return ""


def preferred_wallet_browser(
    *,
    edge_candidates=EDGE_BROWSER_CANDIDATES,
    chrome_candidates=CHROME_BROWSER_CANDIDATES,
    path_exists=os.path.exists,
) -> tuple[str, str]:
    edge_path = first_existing_browser(edge_candidates, path_exists=path_exists)
    if edge_path:
        return edge_path, "msedge"

    chrome_path = first_existing_browser(chrome_candidates, path_exists=path_exists)
    if chrome_path:
        return chrome_path, "chrome"

    return "", ""


def open_url_in_wallet_browser(
    url: str,
    *,
    preferred_browser_func=preferred_wallet_browser,
    popen=subprocess.Popen,
    open_url=webbrowser.open,
) -> str | None:
    browser_path, app_name = preferred_browser_func()
    if browser_path:
        try:
            popen([browser_path, "--new-tab", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return app_name
        except Exception:
            pass

    try:
        open_url(url, new=2)
        return ""
    except Exception:
        return ""
