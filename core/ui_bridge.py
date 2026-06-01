from __future__ import annotations

import subprocess
from datetime import datetime
from collections.abc import Callable
from pathlib import Path

from core.project_health import build_project_health_snapshot, format_project_health_panel
from memory.ui_state import load_ui_state, update_ui_state


class UIBridge:
    def __init__(
        self,
        root_dir: Path,
        python_executable: str,
        runtime_patch: Callable[[], dict],
        normalize_text: Callable[[str], str],
        route: Callable[[str], dict],
        process_action: Callable[[dict], object],
        training_snapshot: Callable[[], dict],
    ):
        self.root_dir = root_dir
        self.python_executable = python_executable
        self.runtime_patch = runtime_patch
        self.normalize_text = normalize_text
        self.route = route
        self.process_action = process_action
        self.training_snapshot = training_snapshot
        self.hud_started = False
        self.hud_log_handle = None

    def _hud_log_path(self) -> Path:
        return self.root_dir / "memory" / "ui_hud.log"

    def _open_hud_log(self):
        try:
            self._hud_log_path().parent.mkdir(parents=True, exist_ok=True)
            if self.hud_log_handle:
                try:
                    self.hud_log_handle.close()
                except Exception:
                    pass
            self.hud_log_handle = self._hud_log_path().open("a", encoding="utf-8", buffering=1)
            self.hud_log_handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] launching HUD\n")
            return self.hud_log_handle
        except Exception:
            return subprocess.DEVNULL

    def refresh_runtime_state(self, extra: dict | None = None) -> None:
        try:
            patch = dict(self.runtime_patch())
            if extra:
                patch.update(extra)
            update_ui_state(patch)
        except Exception:
            pass

    def launch_hud(self) -> None:
        state = load_ui_state()
        if self.hud_started and state.get("visible", False):
            self.refresh_runtime_state({"visible": True})
            return

        pythonw = Path(self.python_executable).with_name("pythonw.exe")
        python_exec = str(pythonw if pythonw.exists() else Path(self.python_executable))

        try:
            hud_log = self._open_hud_log()
            subprocess.Popen(
                [python_exec, "-m", "ui.qt_axel_hud"],
                cwd=str(self.root_dir),
                stdin=subprocess.DEVNULL,
                stdout=hud_log,
                stderr=subprocess.STDOUT,
            )
            self.hud_started = True
        except Exception:
            return

        self.refresh_runtime_state({"visible": True})

    def show_hud(self) -> str:
        update_ui_state({"visible": True})
        self.launch_hud()
        return "Interface ativada. Deixei o painel no ar."

    def hide_hud(self) -> str:
        self.hud_started = False
        update_ui_state({"visible": False})
        self.refresh_runtime_state({"visible": False})
        return "Interface oculta."

    def show_map(self, map_request: dict | None = None) -> str:
        payload = map_request if isinstance(map_request, dict) else {}
        label = str(payload.get("label") or payload.get("location") or payload.get("destination") or "mapa").strip()
        update_ui_state(
            {
                "visible": True,
                "map_panel_open": True,
                "map_request": payload,
                "last_command": f"mostrar mapa {label}".strip(),
            }
        )
        self.launch_hud()
        return f"Mapa aberto na interface: {label}."

    def show_training(self) -> str:
        snapshot = self.training_snapshot()
        workout = snapshot.get("workout") or {}
        update_ui_state(
            {
                "visible": True,
                "open_panels": ["treino"],
                "last_command": "abrir treino",
                "training_snapshot": snapshot,
            }
        )
        self.launch_hud()
        return f"Painel de treino aberto: {workout.get('label', 'hoje')}, {workout.get('title', 'treino')}."

    def show_health(self) -> str:
        snapshot = build_project_health_snapshot(self.root_dir)
        update_ui_state(
            {
                "visible": True,
                "open_panels": ["saude"],
                "last_command": "saude do axel",
                "health_snapshot": snapshot,
            }
        )
        self.launch_hud()
        return format_project_health_panel(snapshot)

    def maybe_handle_command(self, user_input: str) -> str | None:
        normalized = self.normalize_text(user_input)

        show_commands = {
            "abrir interface",
            "abrir painel",
            "mostrar interface",
            "mostrar painel",
            "exibir interface",
            "exibir painel",
            "ativar interface",
            "ativar painel",
            "mostrar hud",
        }
        hide_commands = {
            "fechar interface",
            "fechar painel",
            "ocultar interface",
            "ocultar painel",
            "esconder interface",
            "esconder painel",
            "desativar interface",
            "desativar painel",
            "fechar hud",
        }

        if normalized in show_commands:
            return self.show_hud()

        if normalized in hide_commands:
            return self.hide_hud()

        if normalized in {"interface atual", "status da interface", "painel atual"}:
            state = "ativa" if load_ui_state().get("visible", False) else "oculta"
            return f"Interface {state}."

        if normalized in {
            "saude do axel",
            "status do axel",
            "painel de saude",
            "abrir painel de saude",
            "mostrar painel de saude",
            "diagnostico do axel",
            "painel saude",
        }:
            return self.show_health()

        if normalized in {
            "abrir painel de skills",
            "mostrar painel de skills",
            "painel de skills",
            "skills sugeridas no painel",
            "abrir skills",
        }:
            update_ui_state(
                {
                    "visible": True,
                    "open_panels": ["skills"],
                    "last_command": "abrir painel de skills",
                }
            )
            self.launch_hud()
            return "Painel de skills aberto."

        raw_action = self.route(user_input)
        if raw_action.get("intent") == "ui_show_map":
            processed = self.process_action(raw_action)
            if not isinstance(processed, str):
                return self.show_map(processed.params.get("target"))

        return None
