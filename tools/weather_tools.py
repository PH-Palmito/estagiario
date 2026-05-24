from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

import requests

from memory.profile import get_value

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_TIMEZONE = "America/Sao_Paulo"


WEATHER_CODE_LABELS = {
    0: "ceu limpo",
    1: "predominio de sol",
    2: "parcialmente nublado",
    3: "nublado",
    45: "nevoa",
    48: "nevoa com geada",
    51: "garoa fraca",
    53: "garoa moderada",
    55: "garoa intensa",
    56: "garoa congelante fraca",
    57: "garoa congelante intensa",
    61: "chuva fraca",
    63: "chuva moderada",
    65: "chuva forte",
    66: "chuva congelante fraca",
    67: "chuva congelante forte",
    71: "neve fraca",
    73: "neve moderada",
    75: "neve forte",
    77: "graos de neve",
    80: "pancadas de chuva fracas",
    81: "pancadas de chuva moderadas",
    82: "pancadas de chuva fortes",
    85: "pancadas de neve fracas",
    86: "pancadas de neve fortes",
    95: "trovoadas",
    96: "trovoadas com granizo fraco",
    99: "trovoadas com granizo forte",
}


@dataclass
class WeatherSnapshot:
    location_label: str
    temperature_c: float | None
    apparent_temperature_c: float | None
    weather_label: str
    wind_kmh: float | None
    humidity_percent: float | None
    max_c: float | None
    min_c: float | None
    rain_chance_percent: float | None
    is_day: bool | None


def _http_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def _default_location() -> str:
    return (
        str(get_value("cidade") or "").strip()
        or str(get_value("perfil.cidade") or "").strip()
        or "Salvador"
    )


def _normalize_location(location: str | None) -> str:
    value = (location or "").strip(" .,")
    return value or _default_location()


def _extract_location_label(result: dict) -> str:
    name = str(result.get("name") or "").strip()
    admin1 = str(result.get("admin1") or "").strip()
    country = str(result.get("country") or "").strip()
    parts = [part for part in (name, admin1, country) if part]
    return ", ".join(parts) if parts else name or _default_location()


def _resolve_weather_label(code: int | None) -> str:
    if code is None:
        return "condicao nao identificada"
    return WEATHER_CODE_LABELS.get(code, "condicao nao identificada")


def _geocode_location(location: str) -> dict | None:
    session = _http_session()
    response = session.get(
        GEOCODING_URL,
        params={
            "name": location,
            "count": 1,
            "language": "pt",
            "format": "json",
        },
        timeout=12,
    )
    response.raise_for_status()
    results = (response.json() or {}).get("results") or []
    return results[0] if results else None


def _fetch_weather_for_coordinates(latitude: float, longitude: float) -> dict:
    session = _http_session()
    response = session.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(
                (
                    "temperature_2m",
                    "apparent_temperature",
                    "relative_humidity_2m",
                    "weather_code",
                    "wind_speed_10m",
                    "is_day",
                )
            ),
            "daily": ",".join(
                (
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                )
            ),
            "timezone": DEFAULT_TIMEZONE,
            "forecast_days": 1,
        },
        timeout=12,
    )
    response.raise_for_status()
    return response.json() or {}


def get_weather_snapshot(location: str | None = None) -> WeatherSnapshot:
    normalized_location = _normalize_location(location)
    place = _geocode_location(normalized_location)
    if not place:
        raise ValueError(f"Nao consegui localizar {normalized_location}.")

    latitude = float(place["latitude"])
    longitude = float(place["longitude"])
    forecast = _fetch_weather_for_coordinates(latitude, longitude)
    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}

    max_values = daily.get("temperature_2m_max") or [None]
    min_values = daily.get("temperature_2m_min") or [None]
    rain_values = daily.get("precipitation_probability_max") or [None]

    return WeatherSnapshot(
        location_label=_extract_location_label(place),
        temperature_c=current.get("temperature_2m"),
        apparent_temperature_c=current.get("apparent_temperature"),
        weather_label=_resolve_weather_label(current.get("weather_code")),
        wind_kmh=current.get("wind_speed_10m"),
        humidity_percent=current.get("relative_humidity_2m"),
        max_c=max_values[0],
        min_c=min_values[0],
        rain_chance_percent=rain_values[0],
        is_day=current.get("is_day"),
    )


def weather_summary(location: str | None = None) -> str:
    place = _normalize_location(location)
    try:
        snapshot = get_weather_snapshot(place)
    except Exception:
        return f"Nao consegui consultar o clima de {place} agora."

    current_temp = f"{round(snapshot.temperature_c)} graus" if snapshot.temperature_c is not None else None
    feels_like = f"{round(snapshot.apparent_temperature_c)} graus" if snapshot.apparent_temperature_c is not None else None
    max_temp = f"{round(snapshot.max_c)} graus" if snapshot.max_c is not None else None
    min_temp = f"{round(snapshot.min_c)} graus" if snapshot.min_c is not None else None
    humidity = (
        f"Umidade em {round(snapshot.humidity_percent)} por cento."
        if snapshot.humidity_percent is not None
        else None
    )
    rain = (
        f"Chance maxima de chuva hoje em torno de {round(snapshot.rain_chance_percent)} por cento."
        if snapshot.rain_chance_percent is not None
        else None
    )
    wind = (
        f"Ventos por volta de {round(snapshot.wind_kmh)} quilometros por hora."
        if snapshot.wind_kmh is not None
        else None
    )

    parts = [
        f"Agora em {snapshot.location_label}, o clima esta com {snapshot.weather_label}.",
        f"A temperatura esta em {current_temp}." if current_temp else None,
        f"Sensacao termica de {feels_like}." if feels_like else None,
        (
            f"A maxima de hoje deve ficar em {max_temp} e a minima em {min_temp}."
            if max_temp and min_temp
            else None
        ),
        rain,
        humidity,
        wind,
    ]
    return " ".join(part for part in parts if part)


def google_maps_place_url(location: str | None = None) -> str:
    place = _normalize_location(location)
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(place)}"


def google_maps_route_url(origin: str, destination: str) -> str:
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}&destination={quote_plus(destination)}"
    )
