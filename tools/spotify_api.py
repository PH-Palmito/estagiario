from __future__ import annotations

import base64
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import requests

from config import (
    SPOTIFY_ACCESS_TOKEN,
    SPOTIFY_API_ENABLED,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_DEVICE_ID,
    SPOTIFY_REFRESH_TOKEN,
)

SPOTIFY_ACCOUNTS_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
_TOKEN_CACHE: dict[str, Any] = {"value": "", "expires_at": 0.0}
_USER_TOKEN_CACHE: dict[str, Any] = {"value": "", "expires_at": 0.0}
_DEVICE_CACHE: dict[str, Any] = {"value": "", "expires_at": 0.0}
_TRACK_CACHE_PATH = Path("memory") / "spotify_track_cache.json"
_TRACK_CACHE: dict[str, Any] | None = None


def _session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def _normalize_cache_key(text: str) -> str:
    normalized = "".join(
        ch for ch in unicodedata.normalize("NFD", str(text or "").casefold().strip())
        if unicodedata.category(ch) != "Mn"
    )
    normalized = re.sub(r"[^\w\s/-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _load_track_cache() -> dict[str, Any]:
    global _TRACK_CACHE
    if _TRACK_CACHE is not None:
        return _TRACK_CACHE

    try:
        data = json.loads(_TRACK_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}

    _TRACK_CACHE = data if isinstance(data, dict) else {}
    return _TRACK_CACHE


def _save_track_cache() -> None:
    if _TRACK_CACHE is None:
        return

    try:
        _TRACK_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TRACK_CACHE_PATH.write_text(
            json.dumps(_TRACK_CACHE, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError:
        pass


def _valid_cached_track(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    uri = str(value.get("uri") or "").strip()
    name = str(value.get("name") or "").strip()
    if not uri or not name:
        return None
    return {
        "id": str(value.get("id") or "").strip(),
        "uri": uri,
        "name": name,
        "artists": str(value.get("artists") or "").strip(),
        "url": str(value.get("url") or "").strip(),
    }


def _remember_track(query: str, track: dict) -> None:
    key = _normalize_cache_key(query)
    if not key:
        return
    cache = _load_track_cache()
    cache[key] = {
        "id": str(track.get("id") or "").strip(),
        "uri": str(track.get("uri") or "").strip(),
        "name": str(track.get("name") or "").strip(),
        "artists": str(track.get("artists") or "").strip(),
        "url": str(track.get("url") or "").strip(),
        "updated_at": time.time(),
    }
    _save_track_cache()


def _client_credentials_token() -> str:
    if not SPOTIFY_API_ENABLED or not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return ""

    now = time.time()
    cached_value = str(_TOKEN_CACHE.get("value") or "")
    cached_expiration = float(_TOKEN_CACHE.get("expires_at") or 0.0)
    if cached_value and now < cached_expiration:
        return cached_value

    basic = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode("ascii")
    response = _session().post(
        SPOTIFY_ACCOUNTS_URL,
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {basic}"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json() or {}
    token = str(payload.get("access_token") or "").strip()
    expires_in = int(payload.get("expires_in") or 3600)
    if token:
        _TOKEN_CACHE["value"] = token
        _TOKEN_CACHE["expires_at"] = now + max(60, expires_in - 60)
    return token


def _search_token() -> str:
    user_token = _user_access_token()
    if user_token:
        return user_token
    return _client_credentials_token()


def _user_access_token() -> str:
    refreshed = _refresh_user_access_token()
    if refreshed:
        return refreshed
    return SPOTIFY_ACCESS_TOKEN


def _refresh_user_access_token() -> str:
    if not SPOTIFY_API_ENABLED or not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET or not SPOTIFY_REFRESH_TOKEN:
        return ""

    now = time.time()
    cached_value = str(_USER_TOKEN_CACHE.get("value") or "")
    cached_expiration = float(_USER_TOKEN_CACHE.get("expires_at") or 0.0)
    if cached_value and now < cached_expiration:
        return cached_value

    basic = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode("ascii")
    response = _session().post(
        SPOTIFY_ACCOUNTS_URL,
        data={"grant_type": "refresh_token", "refresh_token": SPOTIFY_REFRESH_TOKEN},
        headers={"Authorization": f"Basic {basic}"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json() or {}
    token = str(payload.get("access_token") or "").strip()
    expires_in = int(payload.get("expires_in") or 3600)
    if token:
        _USER_TOKEN_CACHE["value"] = token
        _USER_TOKEN_CACHE["expires_at"] = now + max(60, expires_in - 60)
    return token


def _authorized_get(path: str, *, token: str, params: dict | None = None) -> dict:
    response = _session().get(
        f"{SPOTIFY_API_BASE_URL}{path}",
        params=params or {},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json() or {}


def _authorized_put(path: str, *, token: str, params: dict | None = None, json_body: dict | None = None):
    response = _session().put(
        f"{SPOTIFY_API_BASE_URL}{path}",
        params=params or {},
        json=json_body or {},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()


def _authorized_delete(path: str, *, token: str, params: dict | None = None, json_body: dict | None = None):
    response = _session().delete(
        f"{SPOTIFY_API_BASE_URL}{path}",
        params=params or {},
        json=json_body or {},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()


def _track_from_item(item: dict) -> dict:
    artists = ", ".join(
        str(artist.get("name") or "").strip()
        for artist in (item.get("artists") or [])
        if str(artist.get("name") or "").strip()
    )
    external_urls = item.get("external_urls") or {}
    return {
        "id": str(item.get("id") or "").strip(),
        "uri": str(item.get("uri") or "").strip(),
        "name": str(item.get("name") or "").strip(),
        "artists": artists,
        "url": str(external_urls.get("spotify") or "").strip(),
    }


def _available_devices(token: str) -> list[dict]:
    try:
        payload = _authorized_get("/me/player/devices", token=token)
    except Exception:
        return []
    devices = payload.get("devices") if isinstance(payload, dict) else []
    return [device for device in devices if isinstance(device, dict)]


def _best_device_id(token: str) -> str:
    now = time.time()
    cached_value = str(_DEVICE_CACHE.get("value") or "")
    cached_expiration = float(_DEVICE_CACHE.get("expires_at") or 0.0)
    if cached_value and now < cached_expiration:
        return cached_value

    devices = _available_devices(token)
    if not devices:
        return str(SPOTIFY_DEVICE_ID or "").strip()

    configured = str(SPOTIFY_DEVICE_ID or "").strip()
    active = next((device for device in devices if device.get("is_active") and device.get("id")), None)
    configured_device = next((device for device in devices if str(device.get("id") or "") == configured), None)
    chosen = active or configured_device or next((device for device in devices if device.get("id")), None)
    device_id = str((chosen or {}).get("id") or "").strip()
    if device_id:
        _DEVICE_CACHE["value"] = device_id
        _DEVICE_CACHE["expires_at"] = now + 60
    return device_id


def spotify_search_track(query: str) -> dict | None:
    text = str(query or "").strip()
    if not text:
        return None

    cache_key = _normalize_cache_key(text)
    cached_track = _valid_cached_track(_load_track_cache().get(cache_key))
    if cached_track:
        return cached_track

    token = _search_token()
    if not token:
        return None

    payload = _authorized_get(
        "/search",
        token=token,
        params={
            "q": text,
            "type": "track",
            "limit": 5,
            "market": "BR",
        },
    )
    items = ((payload.get("tracks") or {}).get("items") or [])
    if not items:
        return None

    normalized_query = text.casefold()

    def score_track(item: dict) -> tuple[int, int]:
        name = str(item.get("name") or "").casefold()
        artists = " ".join(str(artist.get("name") or "") for artist in (item.get("artists") or [])).casefold()
        score = 0
        if name == normalized_query:
            score += 100
        elif normalized_query in name:
            score += 60
        if normalized_query in artists:
            score += 20
        popularity = int(item.get("popularity") or 0)
        return score, popularity

    best = max(items, key=score_track)
    result = _track_from_item(best)
    _remember_track(text, result)
    return result


def spotify_search_tracks(query: str, limit: int = 5) -> list[dict]:
    text = str(query or "").strip()
    if not text:
        return []

    token = _search_token()
    if not token:
        return []

    payload = _authorized_get(
        "/search",
        token=token,
        params={
            "q": text,
            "type": "track",
            "limit": max(1, min(int(limit or 5), 10)),
            "market": "BR",
        },
    )
    items = ((payload.get("tracks") or {}).get("items") or [])
    tracks = [_track_from_item(item) for item in items if isinstance(item, dict)]
    return [track for track in tracks if track.get("uri") and track.get("name")]


def spotify_start_playback(track_uri: str) -> bool:
    token = _user_access_token()
    if not SPOTIFY_API_ENABLED or not token or not track_uri:
        return False

    device_id = _best_device_id(token)
    params = {"device_id": device_id} if device_id else None
    try:
        _authorized_put(
            "/me/player/play",
            token=token,
            params=params,
            json_body={"uris": [track_uri]},
        )
        return True
    except Exception:
        return False


def spotify_add_to_queue(track_uri: str) -> bool:
    token = _user_access_token()
    if not SPOTIFY_API_ENABLED or not token or not track_uri:
        return False

    params = {"uri": track_uri}
    device_id = _best_device_id(token)
    if device_id:
        params["device_id"] = device_id
    try:
        response = _session().post(
            f"{SPOTIFY_API_BASE_URL}/me/player/queue",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def spotify_next_track() -> bool:
    token = _user_access_token()
    if not SPOTIFY_API_ENABLED or not token:
        return False

    params = {}
    device_id = _best_device_id(token)
    if device_id:
        params["device_id"] = device_id
    try:
        response = _session().post(
            f"{SPOTIFY_API_BASE_URL}/me/player/next",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def spotify_save_track(track_id: str) -> bool:
    token = _user_access_token()
    if not SPOTIFY_API_ENABLED or not token or not track_id:
        return False

    try:
        _authorized_put("/me/tracks", token=token, params={"ids": track_id})
        return True
    except Exception:
        return False


def spotify_remove_saved_track(track_id: str) -> bool:
    token = _user_access_token()
    if not SPOTIFY_API_ENABLED or not token or not track_id:
        return False

    try:
        _authorized_delete("/me/tracks", token=token, params={"ids": track_id})
        return True
    except Exception:
        return False


def spotify_current_playback() -> dict | None:
    token = _user_access_token()
    if not SPOTIFY_API_ENABLED or not token:
        return None

    try:
        response = _session().get(
            f"{SPOTIFY_API_BASE_URL}/me/player/currently-playing",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if response.status_code == 204:
            return None
        response.raise_for_status()
        payload = response.json() or {}
    except Exception:
        return None

    item = payload.get("item") or {}
    if not isinstance(item, dict):
        return None

    album = item.get("album") or {}
    images = album.get("images") if isinstance(album, dict) else []
    image_url = ""
    if isinstance(images, list) and images:
        image_url = str((images[0] or {}).get("url") or "").strip()

    artists = ", ".join(
        str(artist.get("name") or "").strip()
        for artist in (item.get("artists") or [])
        if str(artist.get("name") or "").strip()
    )
    return {
        "id": str(item.get("id") or "").strip(),
        "uri": str(item.get("uri") or "").strip(),
        "name": str(item.get("name") or "").strip(),
        "artists": artists,
        "album": str(album.get("name") or "").strip() if isinstance(album, dict) else "",
        "image_url": image_url,
        "is_playing": bool(payload.get("is_playing")),
        "progress_ms": int(payload.get("progress_ms") or 0),
        "duration_ms": int(item.get("duration_ms") or 0),
    }
