from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

HELP_TEXT = (
    "Uso: python main.py [--voice] [--hotword] [--ui]\n"
    "\n"
    "Opcoes principais:\n"
    "  --voice      ativa modo voz\n"
    "  --hotword    usa escuta por hotword/F8 junto do modo voz\n"
    "  --ui         abre a interface Qt do Axel\n"
    "  --setup      revisa configuracao inicial e encerra\n"
    "  --doctor     roda diagnostico geral e encerra\n"
    "  --update     mostra plano seguro de atualizacao e encerra\n"
    "  --backup-memory  cria snapshot dos arquivos criticos de memoria e encerra\n"
    "  --audio-test [segundos]  roda diagnostico de audio\n"
)


@dataclass(frozen=True)
class AppFlags:
    argv: tuple[str, ...]
    help_requested: bool
    voice_mode: bool
    hotword_mode: bool
    ui_mode: bool
    startup_mode: bool
    defer_startup_briefing: bool
    setup_requested: bool
    doctor_requested: bool
    update_requested: bool
    memory_backup_requested: bool
    audio_diagnostic_requested: bool
    audio_diagnostic_seconds: float | None


def _float_after(argv: Sequence[str], flags: tuple[str, ...]) -> float | None:
    for flag in flags:
        if flag not in argv:
            continue
        index = list(argv).index(flag)
        if index + 1 >= len(argv):
            return None
        try:
            return float(argv[index + 1])
        except ValueError:
            return None
    return None


def parse_app_flags(argv: Sequence[str]) -> AppFlags:
    args = tuple(argv)
    audio_flags = ("--audio-test", "--audio-diagnostic")
    setup_requested = "--setup" in args or "setup" in args or tuple(args[1:3]) == ("axel", "setup")
    doctor_requested = "--doctor" in args or "doctor" in args or tuple(args[1:3]) == ("axel", "doctor")
    update_requested = "--update" in args or "update" in args or tuple(args[1:3]) == ("axel", "update")
    memory_backup_requested = (
        "--backup-memory" in args
        or "--memory-backup" in args
        or tuple(args[1:3]) == ("backup", "memory")
        or tuple(args[1:4]) == ("axel", "backup", "memory")
    )
    return AppFlags(
        argv=args,
        help_requested="--help" in args or "-h" in args,
        voice_mode="--voice" in args,
        hotword_mode="--hotword" in args,
        ui_mode="--ui" in args,
        startup_mode="--startup" in args,
        defer_startup_briefing="--startup" in args and "--no-defer-startup-briefing" not in args,
        setup_requested=setup_requested,
        doctor_requested=doctor_requested,
        update_requested=update_requested,
        memory_backup_requested=memory_backup_requested,
        audio_diagnostic_requested=any(flag in args for flag in audio_flags),
        audio_diagnostic_seconds=_float_after(args, audio_flags),
    )
