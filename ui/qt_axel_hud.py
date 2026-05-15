from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from memory.ui_commands import enqueue_ui_command
from memory.ui_state import load_ui_state, update_ui_state

try:
    from tools.spotify_api import spotify_current_playback
except Exception:
    spotify_current_playback = None

try:
    from tools.weather_tools import get_weather_snapshot
except Exception:
    get_weather_snapshot = None

try:
    from memory.investment_snapshot import load_investment_snapshot
except Exception:
    load_investment_snapshot = None

try:
    from config import NEWSAPI_ENABLED, NEWSAPI_KEY
    from memory.news_api import analyze_asset_news
except Exception:
    NEWSAPI_ENABLED = False
    NEWSAPI_KEY = ""
    analyze_asset_news = None

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "ui" / "axel_web_hud.html"


class AxelBridge(QObject):
    def __init__(self, window: "AxelWebHud"):
        super().__init__()
        self.window = window

    @Slot(str)
    def sendCommand(self, text: str):
        enqueue_ui_command(text, source="qt_hud")
        update_ui_state({"last_command": str(text or "").strip()})
        self.window.push_state()

    @Slot()
    def requestRefresh(self):
        self.window.push_state()

    @Slot(str)
    def setActivePanel(self, name: str):
        panel = str(name or "").strip().lower()
        patch = {"active_panel": panel}
        if panel != "mapas":
            patch["map_panel_open"] = False
        update_ui_state(patch)

    @Slot()
    def clearOpenPanels(self):
        update_ui_state({"open_panels": []})
        self.window.push_state()

    @Slot()
    def refreshData(self):
        self.window.clear_cache()
        self.window.push_state()


class AxelWebHud(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Axel")
        self.resize(1380, 820)
        self._closing_from_state = False
        self._js_busy = False
        self._queued_payload = ""
        self._cache = {
            "media": {"at": 0.0, "data": {}},
            "weather": {"at": 0.0, "data": {}},
            "investment": {"at": 0.0, "data": {}},
            "news": {"at": 0.0, "data": []},
        }

        self.view = QWebEngineView(self)
        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        self.channel = QWebChannel(self.view.page())
        self.bridge = AxelBridge(self)
        self.channel.registerObject("axelBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        self.setCentralWidget(self.view)
        self.view.loadFinished.connect(self._on_load_finished)
        self.view.setUrl(QUrl.fromLocalFile(str(HTML_PATH)))

        self.timer = QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self.push_state)

    def clear_cache(self):
        for entry in self._cache.values():
            entry["at"] = 0.0

    def _on_load_finished(self, ok: bool):
        if ok:
            update_ui_state({"visible": True})
            self.push_state()
            self.timer.start()

    def closeEvent(self, event):
        if not self._closing_from_state:
            update_ui_state({"visible": False})
        super().closeEvent(event)

    def _media_payload(self) -> dict:
        if time.time() - self._cache["media"]["at"] < 10:
            return self._cache["media"]["data"]
        data = {}
        if spotify_current_playback:
            try:
                data = spotify_current_playback() or {}
            except Exception:
                data = {}
        self._cache["media"] = {"at": time.time(), "data": data}
        return data

    def _weather_payload(self) -> dict:
        if time.time() - self._cache["weather"]["at"] < 600:
            return self._cache["weather"]["data"]
        data = {}
        if get_weather_snapshot:
            try:
                snapshot = get_weather_snapshot()
                data = dict(getattr(snapshot, "__dict__", {}) or {})
            except Exception:
                data = {}
        self._cache["weather"] = {"at": time.time(), "data": data}
        return data

    def _investment_payload(self) -> dict:
        if time.time() - self._cache["investment"]["at"] < 60:
            return self._cache["investment"]["data"]
        data = {}
        if load_investment_snapshot:
            try:
                data = load_investment_snapshot() or {}
            except Exception:
                data = {}
        self._cache["investment"] = {"at": time.time(), "data": data}
        return data

    def _news_payload(self, investment: dict) -> list:
        if time.time() - self._cache["news"]["at"] < 900:
            return self._cache["news"]["data"]
        lines = []
        if NEWSAPI_ENABLED and NEWSAPI_KEY and analyze_asset_news:
            positions = investment.get("asset_positions") if isinstance(investment, dict) else []
            if isinstance(positions, list):
                for asset in positions[:4]:
                    if not isinstance(asset, dict):
                        continue
                    ticker = str(asset.get("ticker") or asset.get("symbol") or "").strip().upper()
                    company_name = str(asset.get("name") or asset.get("company_name") or "").strip()
                    if not ticker:
                        continue
                    try:
                        for item in analyze_asset_news(ticker, company_name=company_name)[:1]:
                            if isinstance(item, dict):
                                lines.append({
                                    "ticker": ticker,
                                    "title": str(item.get("title") or "").strip(),
                                    "source": str(item.get("source") or "").strip(),
                                    "url": str(item.get("url") or "").strip(),
                                })
                    except Exception:
                        continue
        self._cache["news"] = {"at": time.time(), "data": lines[:8]}
        return lines[:8]

    def _map_payload(self, ui_state: dict) -> dict:
        request = ui_state.get("map_request") if isinstance(ui_state.get("map_request"), dict) else {}
        label = str(request.get("label") or request.get("location") or request.get("destination") or "Mapa").strip()
        kind = str(request.get("kind") or "place").strip()
        return {
            "label": label,
            "kind": kind,
            "url": str(request.get("url") or "").strip(),
            "origin": str(request.get("origin") or "").strip(),
            "destination": str(request.get("destination") or "").strip(),
            "request": request,
            "open": bool(ui_state.get("map_panel_open")),
        }

    def _cached(self, key: str):
        return self._cache.get(key, {}).get("data", {} if key != "news" else [])

    def _active_panels(self, ui_state: dict) -> set[str]:
        aliases = {
            "text": "texto",
            "invest": "carteira",
            "noticia": "noticias",
            "notícias": "noticias",
            "mapa": "mapas",
        }
        panels = set()
        active = str(ui_state.get("active_panel") or "").strip().lower()
        if active:
            panels.add(aliases.get(active, active))
        for name in ui_state.get("open_panels") or []:
            panel = str(name or "").strip().lower()
            if panel:
                panels.add(aliases.get(panel, panel))
        if ui_state.get("map_panel_open"):
            panels.add("mapas")
        return panels

    def _payload(self) -> dict:
        ui_state = load_ui_state()
        active_panels = self._active_panels(ui_state)
        try:
            from memory.training import training_snapshot

            training = training_snapshot()
        except Exception as exc:
            training = {
                "target_days": 170,
                "completed_this_year": 0,
                "remaining": 170,
                "streak": 0,
                "fatigue": {},
                "workout": {"label": "Hoje", "title": "Treino", "focus": str(exc), "exercises": []},
            }

        media = self._media_payload() if "midia" in active_panels else self._cached("media")
        weather = self._weather_payload() if "tempo" in active_panels else self._cached("weather")
        investment_needed = bool({"carteira", "noticias"} & active_panels)
        investment = self._investment_payload() if investment_needed else self._cached("investment")
        news = self._news_payload(investment) if "noticias" in active_panels else self._cached("news")
        return {
            "ui": ui_state,
            "training": training,
            "media": media,
            "weather": weather,
            "investment": investment,
            "news": news,
            "map": self._map_payload(ui_state),
        }

    def push_state(self):
        payload_data = self._payload()
        if not payload_data.get("ui", {}).get("visible", True):
            self._closing_from_state = True
            self.close()
            return
        payload = json.dumps(payload_data, ensure_ascii=False)
        self._send_payload(payload)

    def _send_payload(self, payload: str):
        if self._js_busy:
            self._queued_payload = payload
            return
        self._js_busy = True
        self.view.page().runJavaScript(
            f"window.setAxelState && window.setAxelState({payload});",
            self._on_js_state_applied,
        )

    def _on_js_state_applied(self, _result=None):
        self._js_busy = False
        if not self._queued_payload:
            return
        payload = self._queued_payload
        self._queued_payload = ""
        self._send_payload(payload)


def main() -> int:
    app = QApplication(sys.argv)
    window = AxelWebHud()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
