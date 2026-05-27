from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import AXEL_PERFORMANCE_MODE

PERFORMANCE_MODE_BALANCED = "balanced"
PERFORMANCE_MODE_ECONOMY = "economy"
PERFORMANCE_MODE_PERFORMANCE = "performance"
VALID_PERFORMANCE_MODES = {
    PERFORMANCE_MODE_BALANCED,
    PERFORMANCE_MODE_ECONOMY,
    PERFORMANCE_MODE_PERFORMANCE,
}
SILENT_RUNTIME_MODES = {"silent", "silencioso", "focus", "foco", "modo_foco"}
DEFAULT_RUNTIME_IDLE_SLEEP_SECONDS = 0.08
ECONOMY_RUNTIME_IDLE_SLEEP_SECONDS = 0.18
SILENT_RUNTIME_IDLE_SLEEP_SECONDS = 0.25


@dataclass(frozen=True)
class PerformanceModeSettings:
    mode: str
    qt_poll_ms: int
    web_frame_delay_ms: int
    web_panel_frame_delay_ms: int
    web_transition_frame_delay_ms: int
    animation_scale: float
    reduce_motion: bool
    prefer_background: bool
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "qt_poll_ms": self.qt_poll_ms,
            "web_frame_delay_ms": self.web_frame_delay_ms,
            "web_panel_frame_delay_ms": self.web_panel_frame_delay_ms,
            "web_transition_frame_delay_ms": self.web_transition_frame_delay_ms,
            "animation_scale": self.animation_scale,
            "reduce_motion": self.reduce_motion,
            "prefer_background": self.prefer_background,
            "description": self.description,
        }


def normalize_performance_mode(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    normalized = normalized.replace(" ", "_")
    if normalized.startswith("modo_"):
        normalized = normalized[len("modo_") :]
    aliases = {
        "eco": PERFORMANCE_MODE_ECONOMY,
        "economia": PERFORMANCE_MODE_ECONOMY,
        "low_power": PERFORMANCE_MODE_ECONOMY,
        "leve": PERFORMANCE_MODE_ECONOMY,
        "normal": PERFORMANCE_MODE_BALANCED,
        "equilibrado": PERFORMANCE_MODE_BALANCED,
        "balanced": PERFORMANCE_MODE_BALANCED,
        "alto": PERFORMANCE_MODE_PERFORMANCE,
        "rapido": PERFORMANCE_MODE_PERFORMANCE,
        "performance": PERFORMANCE_MODE_PERFORMANCE,
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in VALID_PERFORMANCE_MODES:
        return normalized
    return PERFORMANCE_MODE_BALANCED


def configured_performance_mode() -> str:
    return normalize_performance_mode(AXEL_PERFORMANCE_MODE)


def performance_mode_from_state(state: dict | None = None) -> str:
    if isinstance(state, dict):
        state_mode = state.get("performance_mode")
        if state_mode:
            return normalize_performance_mode(str(state_mode))
    return configured_performance_mode()


def performance_settings(mode: str | None = None) -> PerformanceModeSettings:
    selected = normalize_performance_mode(mode or configured_performance_mode())
    if selected == PERFORMANCE_MODE_ECONOMY:
        return PerformanceModeSettings(
            mode=selected,
            qt_poll_ms=3500,
            web_frame_delay_ms=90,
            web_panel_frame_delay_ms=120,
            web_transition_frame_delay_ms=120,
            animation_scale=0.38,
            reduce_motion=True,
            prefer_background=True,
            description="modo economia: menos polling, menos animacao e preferencia por background",
        )
    if selected == PERFORMANCE_MODE_PERFORMANCE:
        return PerformanceModeSettings(
            mode=selected,
            qt_poll_ms=1000,
            web_frame_delay_ms=24,
            web_panel_frame_delay_ms=40,
            web_transition_frame_delay_ms=64,
            animation_scale=1.2,
            reduce_motion=False,
            prefer_background=True,
            description="modo performance: interface mais responsiva e animacao mais fluida",
        )
    return PerformanceModeSettings(
        mode=PERFORMANCE_MODE_BALANCED,
        qt_poll_ms=1500,
        web_frame_delay_ms=33,
        web_panel_frame_delay_ms=50,
        web_transition_frame_delay_ms=80,
        animation_scale=1.0,
        reduce_motion=False,
        prefer_background=True,
        description="modo equilibrado: custo moderado com HUD fluido",
    )


def performance_settings_from_state(state: dict | None = None) -> PerformanceModeSettings:
    return performance_settings(performance_mode_from_state(state))


def runtime_idle_sleep_seconds_from_state(state: dict | None = None) -> float:
    if isinstance(state, dict):
        mode = str(state.get("mode") or state.get("ui_mode") or "").strip().lower()
        active_panel = str(state.get("active_panel") or "").strip().lower()
        if mode in SILENT_RUNTIME_MODES or active_panel in SILENT_RUNTIME_MODES:
            return SILENT_RUNTIME_IDLE_SLEEP_SECONDS

    settings = performance_settings_from_state(state)
    if settings.mode == PERFORMANCE_MODE_ECONOMY:
        return ECONOMY_RUNTIME_IDLE_SLEEP_SECONDS
    return DEFAULT_RUNTIME_IDLE_SLEEP_SECONDS
