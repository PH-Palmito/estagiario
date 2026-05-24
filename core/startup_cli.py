from __future__ import annotations

from collections.abc import Callable, Sequence

from core.cli_args import cli_text_after, cli_value_after


def handle_windows_startup_cli(
    argv: Sequence[str],
    *,
    print_fn: Callable[[object], None],
    enable_windows_startup: Callable[[], str],
    disable_windows_startup: Callable[[], str],
    windows_startup_status: Callable[[], str],
) -> bool:
    if "--install-startup" in argv or "--enable-startup" in argv:
        print_fn(enable_windows_startup())
        return True
    if "--uninstall-startup" in argv or "--disable-startup" in argv:
        print_fn(disable_windows_startup())
        return True
    if "--startup-status" in argv:
        print_fn(windows_startup_status())
        return True
    return False


def handle_voice_tools_cli(
    argv: Sequence[str],
    *,
    voice_preferences: dict,
    common_tts_cache_phrases: Callable[[], list[str]],
    prime_piper_cache: Callable[[list[str]], object],
    list_piper_voices: Callable[[], list[dict]],
    download_piper_voice: Callable[[str], tuple[bool, str]],
    apply_piper_voice: Callable[[str], tuple[bool, str]],
    list_voice_profiles: Callable[[], list[str]],
    apply_voice_profile: Callable[[str], tuple[bool, str]],
    refresh_voice_preferences: Callable[[], None],
    output_response: Callable[..., None],
    print_fn: Callable[[object], None],
    set_windows_voice_wait_for_playback: Callable[[], None] | None = None,
) -> bool:
    if "--warm-tts-cache" in argv:
        result = prime_piper_cache(common_tts_cache_phrases())
        print_fn(result.text or result.error)
        if result.error:
            print_fn(result.error)
        return True

    if "--list-piper-voices" in argv:
        print_fn("Vozes Piper disponiveis:")
        for voice in list_piper_voices():
            status = "instalada" if voice["installed"] else "nao instalada"
            print_fn(f"- {voice['key']} ({status}) - {voice['label']}")
        return True

    voice_to_download = cli_value_after(argv, "--download-piper-voice")
    if voice_to_download:
        ok, message = download_piper_voice(voice_to_download)
        print_fn(message)
        if not ok:
            return True

    voice_to_apply = cli_value_after(argv, "--use-piper-voice")
    if voice_to_apply:
        ok, message = apply_piper_voice(voice_to_apply)
        print_fn(message)
        if not ok:
            return True
        refresh_voice_preferences()

    if "--list-voice-profiles" in argv:
        print_fn("Perfis de voz disponiveis:")
        for profile in list_voice_profiles():
            print_fn(f"- {profile}")
        return True

    profile_name = cli_value_after(argv, "--voice-profile")
    if profile_name:
        ok, message = apply_voice_profile(profile_name)
        print_fn(message)
        if not ok:
            return True
        refresh_voice_preferences()

    if "--voice-test" in argv:
        test_text = (
            cli_text_after(argv, "--voice-test")
            or str(voice_preferences.get("startup_voice_greeting", "")).strip()
            or "Sistemas online. A sua disposicao."
        )
        voice_preferences["tts_wait_for_playback"] = True
        if set_windows_voice_wait_for_playback:
            set_windows_voice_wait_for_playback()
        output_response(test_text, voice_mode=True)
        return True

    return bool(profile_name or voice_to_download or voice_to_apply)


def handle_audio_diagnostic_cli(
    *,
    requested: bool,
    seconds: float | None,
    run_audio_diagnostic: Callable[[float | None], str],
    print_fn: Callable[[object], None],
) -> bool:
    if not requested:
        return False

    print_fn("Gravando diagnostico de audio. Fale uma frase curta...")
    print_fn(run_audio_diagnostic(seconds))
    return True
