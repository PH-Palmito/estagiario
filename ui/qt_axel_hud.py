from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow

from core.performance_mode import performance_settings_from_state
from memory.ui_commands import enqueue_ui_command
from memory.ui_state import load_ui_state, update_ui_state
from memory.voice_preferences import load_voice_preferences

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
    from core.project_health import build_project_health_snapshot
except Exception:
    build_project_health_snapshot = None

try:
    from config import NEWSAPI_ENABLED, NEWSAPI_KEY
    from memory.news_api import analyze_asset_news
except Exception:
    NEWSAPI_ENABLED = False
    NEWSAPI_KEY = ""
    analyze_asset_news = None

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "ui" / "axel_web_hud.html"
TRAINING_HTML_PATH = ROOT / "ui" / "training_panel.html"


class AxelBridge(QObject):
    def __init__(self, window: AxelWebHud):
        super().__init__()
        self.window = window

    @Slot(str, result=str)
    def sendCommand(self, text: str):
        try:
            item = enqueue_ui_command(text, source="qt_hud")
            feedback = {
                "id": str(item.get("id") or ""),
                "command": str(item.get("text") or ""),
                "status": "queued",
                "message": "Comando adicionado a fila.",
                "at": time.time(),
            }
            update_ui_state({"last_command": str(text or "").strip(), "command_feedback": feedback})
            self.window.push_state()
            return json.dumps(feedback, ensure_ascii=False)
        except Exception as exc:
            self.window.log_exception("sendCommand")
            return json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)

    @Slot()
    def requestRefresh(self):
        try:
            self.window.push_state(force=True)
        except Exception:
            self.window.log_exception("requestRefresh")

    @Slot(str)
    def setActivePanel(self, name: str):
        try:
            panel = str(name or "").strip().lower()
            patch = {"active_panel": panel}
            if panel != "mapas":
                patch["map_panel_open"] = False
            update_ui_state(patch)
            self.window.push_state()
        except Exception:
            self.window.log_exception("setActivePanel")

    @Slot()
    def clearOpenPanels(self):
        try:
            update_ui_state({"open_panels": []})
            self.window.push_state()
        except Exception:
            self.window.log_exception("clearOpenPanels")

    @Slot(result=str)
    def refreshData(self):
        try:
            self.window.clear_cache()
            feedback = {
                "id": f"refresh-{int(time.time() * 1000)}",
                "command": "atualizar painel",
                "status": "success",
                "message": "Dados atualizados.",
                "at": time.time(),
            }
            update_ui_state({"command_feedback": feedback})
            self.window.push_state(force=True)
            return json.dumps(feedback, ensure_ascii=False)
        except Exception as exc:
            self.window.log_exception("refreshData")
            return json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)

    @Slot(result=str)
    def selectStudyFiles(self) -> str:
        try:
            paths, _selected_filter = QFileDialog.getOpenFileNames(
                self.window,
                "Adicionar arquivos ao Axel",
                str(Path.home()),
                "Arquivos de estudo (*.pdf *.pptx *.docx *.txt *.md *.csv *.json *.xlsx);;Todos os arquivos (*.*)",
            )
            return json.dumps([str(path) for path in paths], ensure_ascii=False)
        except Exception:
            self.window.log_exception("selectStudyFiles")
            return "[]"


class AxelWebHud(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Axel")
        self.resize(1380, 820)
        self._closing_from_state = False
        self._js_busy = False
        self._queued_payload = ""
        self._queued_payload_force = False
        self._last_payload = ""
        self._last_training_payload = ""
        self._cache = {
            "media": {"at": 0.0, "data": {}},
            "weather": {"at": 0.0, "data": {}},
            "investment": {"at": 0.0, "data": {}},
            "news": {"at": 0.0, "data": []},
            "health": {"at": 0.0, "data": {}},
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

        self.training_view = QWebEngineView(self)
        training_settings = self.training_view.settings()
        training_settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        training_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        training_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.training_channel = QWebChannel(self.training_view.page())
        self.training_channel.registerObject("axelBridge", self.bridge)
        self.training_view.page().setWebChannel(self.training_channel)
        self.training_view.setUrl(QUrl.fromLocalFile(str(TRAINING_HTML_PATH)))
        self.training_view.hide()
        self.training_view.raise_()

        self.timer = QTimer(self)
        self.timer.setInterval(performance_settings_from_state(load_ui_state()).qt_poll_ms)
        self.timer.timeout.connect(self.push_state)

    def clear_cache(self):
        for entry in self._cache.values():
            entry["at"] = 0.0
        self._last_payload = ""
        self._last_training_payload = ""

    def log_exception(self, source: str) -> None:
        print(f"[HUD] {source} failed", file=sys.stderr)
        traceback.print_exc()

    def _apply_performance_mode(self, ui_state: dict):
        settings = performance_settings_from_state(ui_state)
        if self.timer.interval() != settings.qt_poll_ms:
            self.timer.setInterval(settings.qt_poll_ms)

    def _on_load_finished(self, ok: bool):
        if ok:
            update_ui_state({"visible": True})
            self.push_state(force=True)
            self.timer.start()

    def closeEvent(self, event):
        if not self._closing_from_state:
            update_ui_state({"visible": False})
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_training_view()

    def _position_training_view(self):
        if not hasattr(self, "training_view"):
            return
        width = min(1120, max(760, self.width() - 112))
        height = max(560, self.height() - 44)
        x = max(24, (self.width() - width) // 2)
        y = max(12, (self.height() - height) // 2)
        self.training_view.setGeometry(x, y, min(width, self.width() - 48), min(height, self.height() - 24))
        self.training_view.raise_()

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

    def _health_payload(self, ui_state: dict) -> dict:
        existing = ui_state.get("health_snapshot") if isinstance(ui_state.get("health_snapshot"), dict) else {}
        if existing:
            return existing
        if time.time() - self._cache["health"]["at"] < 20:
            return self._cache["health"]["data"]
        data = {}
        if build_project_health_snapshot:
            try:
                data = build_project_health_snapshot(ROOT) or {}
            except Exception as exc:
                data = {"status": "precisa de atencao", "error": str(exc)}
        self._cache["health"] = {"at": time.time(), "data": data}
        return data

    def _payload(self) -> dict:
        ui_state = load_ui_state()
        try:
            preferences = load_voice_preferences()
            ui_state = dict(ui_state)
            ui_state["assistant_personality_enabled"] = bool(preferences.get("assistant_personality_enabled", True))
            ui_state["assistant_proactivity_enabled"] = bool(preferences.get("assistant_proactivity_enabled", True))
        except Exception:
            ui_state = dict(ui_state)
        self._apply_performance_mode(ui_state)
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
        try:
            from memory.study import study_snapshot

            study = study_snapshot() if "estudos" in active_panels else ui_state.get("study_snapshot", {})
        except Exception as exc:
            study = {"error": str(exc), "minutes_today": 0, "daily_minutes": 60, "goals": [], "pending_reviews": []}

        media = self._media_payload() if "midia" in active_panels else self._cached("media")
        weather = self._weather_payload() if "tempo" in active_panels else self._cached("weather")
        investment_needed = bool({"carteira", "noticias"} & active_panels)
        investment = self._investment_payload() if investment_needed else self._cached("investment")
        news = self._news_payload(investment) if "noticias" in active_panels else self._cached("news")
        health = self._health_payload(ui_state) if "saude" in active_panels else self._cached("health")
        return {
            "ui": ui_state,
            "training": training,
            "study": study,
            "media": media,
            "weather": weather,
            "investment": investment,
            "news": news,
            "health": health,
            "map": self._map_payload(ui_state),
        }

    def push_state(self, force: bool = False):
        payload_data = self._payload()
        if not payload_data.get("ui", {}).get("visible", True):
            self._closing_from_state = True
            self.close()
            return
        payload = json.dumps(payload_data, ensure_ascii=False)
        training_open = str(payload_data.get("ui", {}).get("active_panel") or "").strip().lower() == "treino"
        if training_open:
            self._position_training_view()
            if not self.training_view.isVisible():
                self.training_view.show()
                self.training_view.raise_()
            if force or payload != self._last_training_payload:
                self._last_training_payload = payload
                self.training_view.page().runJavaScript(f"window.setTrainingState && window.setTrainingState({payload});")
        else:
            self._last_training_payload = ""
            if self.training_view.isVisible():
                self.training_view.hide()
        self._send_payload(payload, force=force)

    def _send_payload(self, payload: str, force: bool = False):
        if not force and payload == self._last_payload:
            return
        if self._js_busy:
            if force or payload != self._last_payload:
                self._queued_payload = payload
                self._queued_payload_force = force
            return
        self._js_busy = True
        self._last_payload = payload
        self.view.page().runJavaScript(
            f"window.setAxelState && window.setAxelState({payload});",
            self._on_js_state_applied,
        )

    def _on_js_state_applied(self, _result=None):
        self._js_busy = False
        if not self._queued_payload:
            return
        payload = self._queued_payload
        force = self._queued_payload_force
        self._queued_payload = ""
        self._queued_payload_force = False
        self._send_payload(payload, force=force)


def main() -> int:
    app = QApplication(sys.argv)
    window = AxelWebHud()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
