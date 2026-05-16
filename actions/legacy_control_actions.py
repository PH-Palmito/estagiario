from __future__ import annotations

from actions.registry import ActionSpec, register_action
from tools.bluetooth_tools import bluetooth_off, bluetooth_on, bluetooth_settings
from tools.media_tools import (
    media_next,
    media_next_target,
    media_pause_target,
    media_play_pause,
    media_play_pause_target,
    media_play_target,
    media_previous,
    media_previous_target,
    volume_down,
    volume_mute,
    volume_up,
)
from tools.system_tools import focus_app, maximize_app, minimize_app, open_app, open_url, restore_app


def _register(
    name: str,
    description: str,
    handler,
    parameters: dict | None = None,
    category: str = "control",
    read_only: bool = False,
    requires_confirmation: bool = False,
) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category=category,
            read_only=read_only,
            requires_confirmation=requires_confirmation,
            parameters=parameters or {},
        )
    )


def register_legacy_control_actions() -> None:
    target_param = {"target": {"type": "string", "description": "Alvo do comando.", "required": True}}

    _register("open_app", "Abre aplicativo permitido.", lambda args: open_app(args.get("target", "")), target_param, category="system")
    _register("focus_app", "Foca janela de aplicativo permitido.", lambda args: focus_app(args.get("target", "")), target_param, category="system")
    _register("minimize_app", "Minimiza janela de aplicativo permitido.", lambda args: minimize_app(args.get("target", "")), target_param, category="system")
    _register("maximize_app", "Maximiza janela de aplicativo permitido.", lambda args: maximize_app(args.get("target", "")), target_param, category="system")
    _register("restore_app", "Restaura janela de aplicativo permitido.", lambda args: restore_app(args.get("target", "")), target_param, category="system")
    _register("open_url", "Abre URL no navegador padrao.", lambda args: open_url(args.get("target", "")), target_param, category="browser")
    _register("media_play_pause", "Alterna play/pause da midia.", lambda _args: media_play_pause(), category="media")
    _register("media_next", "Avanca para a proxima midia.", lambda _args: media_next(), category="media")
    _register("media_previous", "Volta para a midia anterior.", lambda _args: media_previous(), category="media")
    _register("media_play_pause_target", "Alterna play/pause em alvo de midia.", lambda args: media_play_pause_target(args.get("target", "")), target_param, category="media")
    _register("media_play_target", "Toca midia em alvo especifico.", lambda args: media_play_target(args.get("target", "")), target_param, category="media")
    _register("media_pause_target", "Pausa midia em alvo especifico.", lambda args: media_pause_target(args.get("target", "")), target_param, category="media")
    _register("media_next_target", "Avanca midia em alvo especifico.", lambda args: media_next_target(args.get("target", "")), target_param, category="media")
    _register("media_previous_target", "Volta midia em alvo especifico.", lambda args: media_previous_target(args.get("target", "")), target_param, category="media")
    _register("volume_up", "Aumenta volume do sistema.", lambda _args: volume_up(), category="media")
    _register("volume_down", "Abaixa volume do sistema.", lambda _args: volume_down(), category="media")
    _register("volume_mute", "Alterna mudo do sistema.", lambda _args: volume_mute(), category="media")
    _register("bluetooth_on", "Liga Bluetooth.", lambda _args: bluetooth_on(), category="system")
    _register("bluetooth_off", "Desliga Bluetooth.", lambda _args: bluetooth_off(), category="system")
    _register("bluetooth_settings", "Abre configuracoes de Bluetooth.", lambda _args: bluetooth_settings(), category="system")
