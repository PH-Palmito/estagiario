import sys
import time
from pathlib import Path

from core.app_bootstrap import HELP_TEXT, parse_app_flags
from core.app_runtime import AppRuntime
from core.command_feedback import (
    command_preview,
)
from core.command_service import process_raw_action
from core.confirmation import confirmation_prompt
from core.direct_response_flow import DirectResponseState, handle_direct_response_flow
from core.executor import execute
from core.humor_commands import maybe_handle_humor_command as maybe_handle_humor_command_core
from core.improvement_brain import ImprovementBrain
from core.input_device_commands import maybe_handle_input_device_command as maybe_handle_input_device_command_core
from core.interactive_modes import InteractiveModesState, handle_interactive_modes
from core.macro_recording import MacroRecordingState, handle_macro_recording
from core.operational_command_chain import maybe_handle_operational_command
from core.planner import looks_like_multi_step_request, plan_actions, split_local_steps
from core.post_route_flow import PostRouteState, handle_post_route_action
from core.pronunciation_commands import maybe_handle_pronunciation_command as maybe_handle_pronunciation_command_core
from core.reminder_announcer import ReminderAnnouncer
from core.response_pipeline import ResponsePipeline
from core.router import route
from core.router_utils import normalize_text
from core.routine_execution import (
    execute_routine_steps as execute_routine_steps_core,
)
from core.routine_execution import (
    handle_multi_step_request as handle_multi_step_request_core,
)
from core.startup_briefing import schedule_startup_briefing_worker, send_startup_briefing_once
from core.startup_cli import (
    handle_audio_diagnostic_cli as handle_audio_diagnostic_cli_core,
)
from core.startup_cli import (
    handle_voice_tools_cli,
)
from core.startup_cli import (
    handle_windows_startup_cli as handle_windows_startup_cli_core,
)
from core.startup_diagnostics import run_with_startup_diagnostics
from core.startup_voice import (
    common_tts_cache_phrases as common_tts_cache_phrases_core,
)
from core.startup_voice import (
    startup_greeting_message as startup_greeting_message_core,
)
from core.startup_voice import (
    warm_common_tts_cache_async as warm_common_tts_cache_async_core,
)
from core.training_commands import maybe_handle_training_command as maybe_handle_training_command_core
from core.ui_runtime import UIRuntimeService
from core.ui_runtime_labels import (
    assistant_style_label,
    ui_mode_label,
    voice_profile_label,
)
from core.voice_command_suggestions import (
    command_correction_text,
    is_unclear_response,
    maybe_suggest_probable_command,
)
from core.voice_command_suggestions import (
    maybe_normalize_voice_command as maybe_normalize_voice_command_core,
)
from core.voice_learning import (
    VoiceLearningState,
)
from core.voice_learning import (
    maybe_learn_correction_for_last_voice as maybe_learn_correction_for_last_voice_core,
)
from core.voice_learning import (
    maybe_remember_pending_voice_correction as maybe_remember_pending_voice_correction_core,
)
from core.voice_loop import VoiceReadState, input_source_label, run_voice_input_cycle
from core.voice_modes import (
    is_transcription_artifact,
    is_unreliable_conversation_text,
)
from core.voice_profile_commands import maybe_handle_voice_profile_command as maybe_handle_voice_profile_command_core
from core.work_mode_commands import maybe_handle_work_mode_command as maybe_handle_work_mode_command_core
from llm.chat import chat_response, clear_chat_history
from memory.assistant_phrases import (
    ACTION_PROGRESS_VARIANTS,
    STARTUP_GREETING_VARIANTS,
    STYLE_VARIANTS,
    contextual_startup_phrase,
    next_phrase,
)
from memory.execution_log import append_execution_log
from memory.long_memory import maybe_remember_from_user_text
from memory.macros import add_macro
from memory.operational_context import (
    save_operational_context,
)
from memory.piper_voice_manager import (
    apply_piper_voice,
    download_piper_voice,
    list_piper_voices,
)
from memory.reminders import consume_due_reminders
from memory.session import clear
from memory.training import (
    consume_due_training_reminder,
    training_snapshot,
)
from memory.ui_commands import dequeue_ui_command_item
from memory.ui_state import append_ui_history, reset_ui_state
from memory.voice_corrections import apply_voice_correction, remember_voice_correction
from memory.voice_preferences import load_voice_preferences
from memory.voice_profiles import apply_voice_profile, list_voice_profiles
from tools.briefing_tools import daily_briefing
from tools.investment_tools import start_background_investment_refresh_loop
from tools.smart_open_tools import smart_open_needs_choice
from tools.system_tools import (
    disable_windows_startup,
    enable_windows_startup,
    type_text,
    windows_startup_status,
)
from voice.windows_voice import (
    HOTKEY_NAME,
    HOTWORD_LISTENING_ENABLED,
    TOGGLE_LISTENING_HOTKEY_NAME,
    consume_hotkey_press,
    consume_toggle_listening_hotkey_press,
    get_active_input_device_info,
    listen_conversation_once,
    listen_for_hotword,
    listen_once,
    play_activation_sound,
    prime_piper_cache,
    run_audio_diagnostic,
    speak,
)

UI_HISTORY_MAX_ITEMS = 40
app_runtime = AppRuntime(ui_history_max_items=UI_HISTORY_MAX_ITEMS)
pending_command = None
pending_command_learning_text = ""
pending_smart_open_choice = None
pending_smart_open_invalid_attempts = 0
conversation_mode = False
conversation_ready_announced = False
dictation_mode = False
dictation_ready_announced = False
direct_response_ready_announced = False
last_voice_text = ""
repeat_listen_until = 0.0
silent_ui_command_active = False
STARTUP_BRIEFING_STATE_PATH = Path("memory") / "startup_briefing_state.json"

creating_macro = False
macro_name = None
macro_steps = []
VOICE_PREFERENCES = load_voice_preferences()


def log_execution_event(event_type: str, **payload):
    try:
        append_execution_log(event_type, payload)
    except Exception:
        pass


def process_action(raw_action: dict):
    return process_raw_action(raw_action, app_runtime.runtime_state, log_execution_event)




def show_action_progress(command, voice_mode: bool = False):
    get_response_pipeline().show_action_progress(
        command,
        voice_mode=voice_mode,
        silent_ui_command_active=silent_ui_command_active,
    )


def execute_command(command, voice_mode: bool = False):
    return get_response_pipeline().execute_command(
        command,
        voice_mode=voice_mode,
        silent_ui_command_active=silent_ui_command_active,
    )












def style_response(message: str) -> str:
    return get_response_pipeline().style_response(message)



def output_response(
    message: str,
    voice_mode: bool,
    *,
    interrupt_current_tts: bool = False,
    wait_for_tts: bool | None = None,
):
    global repeat_listen_until
    global direct_response_ready_announced

    result = get_response_pipeline().output_response(
        message,
        voice_mode,
        direct_response_ready_announced=direct_response_ready_announced,
        silent_ui_command_active=silent_ui_command_active,
        interrupt_current_tts=interrupt_current_tts,
        wait_for_tts=wait_for_tts,
    )
    if result.repeat_listen_until is not None:
        repeat_listen_until = result.repeat_listen_until
    direct_response_ready_announced = result.direct_response_ready_announced


def get_response_pipeline() -> ResponsePipeline:
    if app_runtime.response_pipeline is None:
        app_runtime.response_pipeline = ResponsePipeline(
            preferences=VOICE_PREFERENCES,
            style_variants=STYLE_VARIANTS,
            progress_variants=ACTION_PROGRESS_VARIANTS,
            next_phrase=next_phrase,
            terminal_print=terminal_print,
            append_ui_history=append_ui_history,
            refresh_ui_runtime_state=refresh_ui_runtime_state,
            refresh_improvement_brain=refresh_improvement_brain,
            current_ui_mode_label=current_ui_mode_label,
            speak=speak,
            execute=execute,
            runtime_state=app_runtime.runtime_state,
            log_event=log_execution_event,
            history_max_items=UI_HISTORY_MAX_ITEMS,
        )
    return app_runtime.response_pipeline


def maybe_announce_due_reminders(voice_mode: bool):
    get_reminder_announcer().maybe_announce_due_reminders(voice_mode)


def get_reminder_announcer() -> ReminderAnnouncer:
    if app_runtime.reminder_announcer is None:
        app_runtime.reminder_announcer = ReminderAnnouncer(
            consume_due_training_reminder=consume_due_training_reminder,
            consume_due_reminders=consume_due_reminders,
            output_response=output_response,
        )
    return app_runtime.reminder_announcer


def maybe_send_startup_briefing(voice_mode: bool):
    return send_startup_briefing_once(
        voice_mode=voice_mode,
        args=sys.argv,
        voice_preferences=VOICE_PREFERENCES,
        state_path=STARTUP_BRIEFING_STATE_PATH,
        greeting_variants=STARTUP_GREETING_VARIANTS,
        next_phrase=next_phrase,
        daily_briefing=daily_briefing,
        output_response=output_response,
    )


def schedule_startup_briefing_async(voice_mode: bool):
    return schedule_startup_briefing_worker(
        args=sys.argv,
        voice_mode=voice_mode,
        send_startup_briefing=maybe_send_startup_briefing,
    )


def startup_greeting_message() -> str:
    return startup_greeting_message_core(
        argv=sys.argv,
        voice_preferences=VOICE_PREFERENCES,
        greeting_variants=STARTUP_GREETING_VARIANTS,
        contextual_startup_phrase=contextual_startup_phrase,
        next_phrase=next_phrase,
    )


def common_tts_cache_phrases() -> list[str]:
    return common_tts_cache_phrases_core(
        voice_preferences=VOICE_PREFERENCES,
        style_response=style_response,
    )


def warm_common_tts_cache_async():
    return warm_common_tts_cache_async_core(
        voice_preferences=VOICE_PREFERENCES,
        common_tts_cache_phrases=common_tts_cache_phrases,
        prime_piper_cache=prime_piper_cache,
    )


def refresh_voice_preferences():
    VOICE_PREFERENCES.clear()
    VOICE_PREFERENCES.update(load_voice_preferences())

    try:
        import voice.windows_voice as windows_voice

        windows_voice.VOICE_PREFERENCES.clear()
        windows_voice.VOICE_PREFERENCES.update(VOICE_PREFERENCES)
    except Exception:
        pass

    try:
        import llm.chat as chat

        chat.refresh_preferences()
    except Exception:
        pass


def current_assistant_style_label() -> str:
    return assistant_style_label(VOICE_PREFERENCES)


def current_voice_profile_label() -> str:
    return voice_profile_label(VOICE_PREFERENCES)


def current_ui_mode_label() -> str:
    return ui_mode_label(
        dictation_mode=dictation_mode,
        conversation_mode=conversation_mode,
        waiting_for_direct_response=is_waiting_for_direct_response(),
    )




def _ui_runtime_patch() -> dict:
    active_device = get_active_input_device_info() or {}
    return {
        "assistant_name": "Axel",
        "status": app_runtime.terminal_io.voice_status or "INATIVO",
        "mode": current_ui_mode_label(),
        "microphone": active_device.get("name", ""),
        "assistant_style": current_assistant_style_label(),
        "voice_profile": current_voice_profile_label(),
        "hotword_enabled": bool(app_runtime.terminal_io.hotword_ui_enabled),
        "conversation_mode": bool(conversation_mode),
        "dictation_mode": bool(dictation_mode),
        "last_command": command_preview(app_runtime.runtime_state.last_command),
    }


def get_ui_runtime() -> UIRuntimeService:
    if app_runtime.ui_runtime is None:
        app_runtime.ui_runtime = UIRuntimeService(
            root_dir=Path(__file__).resolve().parent,
            python_executable=sys.executable,
            runtime_patch=_ui_runtime_patch,
            normalize_text=normalize_text,
            route=route,
            process_action=process_action,
            training_snapshot=training_snapshot,
            dequeue_ui_command_item=dequeue_ui_command_item,
            append_ui_history=append_ui_history,
            history_max_items=UI_HISTORY_MAX_ITEMS,
        )
    return app_runtime.ui_runtime


def refresh_ui_runtime_state(extra: dict | None = None):
    get_ui_runtime().refresh_runtime_state(extra)


def launch_ui_hud():
    get_ui_runtime().launch_hud()


def show_ui_hud() -> str:
    return get_ui_runtime().show_hud()


def hide_ui_hud() -> str:
    return get_ui_runtime().hide_hud()


def show_map_in_ui(map_request: dict | None = None) -> str:
    return get_ui_runtime().show_map(map_request)


def show_training_in_ui() -> str:
    return get_ui_runtime().show_training()


def maybe_handle_ui_command(user_input: str) -> str | None:
    return get_ui_runtime().maybe_handle_command(user_input)








































def refresh_improvement_brain(force: bool = False):
    get_improvement_brain().refresh(force=force)


def maybe_announce_codex_suggestion(voice_mode: bool):
    get_improvement_brain().maybe_announce_codex_suggestion(voice_mode)


def get_improvement_brain() -> ImprovementBrain:
    if app_runtime.improvement_brain is None:
        app_runtime.improvement_brain = ImprovementBrain(output_response=output_response)
    return app_runtime.improvement_brain


def poll_ui_text_command() -> str:
    global silent_ui_command_active

    queued = get_ui_runtime().poll_text_command(refresh_runtime_state=refresh_ui_runtime_state)
    silent_ui_command_active = get_ui_runtime().silent_command_active
    return queued





















def handle_windows_startup_cli() -> bool:
    return handle_windows_startup_cli_core(
        sys.argv,
        print_fn=print,
        enable_windows_startup=enable_windows_startup,
        disable_windows_startup=disable_windows_startup,
        windows_startup_status=windows_startup_status,
    )


def handle_voice_profile_cli() -> bool:
    return handle_voice_tools_cli(
        sys.argv,
        voice_preferences=VOICE_PREFERENCES,
        common_tts_cache_phrases=common_tts_cache_phrases,
        prime_piper_cache=prime_piper_cache,
        list_piper_voices=list_piper_voices,
        download_piper_voice=download_piper_voice,
        apply_piper_voice=apply_piper_voice,
        list_voice_profiles=list_voice_profiles,
        apply_voice_profile=apply_voice_profile,
        refresh_voice_preferences=refresh_voice_preferences,
        output_response=output_response,
        print_fn=print,
        set_windows_voice_wait_for_playback=set_windows_voice_wait_for_playback,
    )


def set_windows_voice_wait_for_playback() -> None:
    try:
        import voice.windows_voice as windows_voice

        windows_voice.VOICE_PREFERENCES["tts_wait_for_playback"] = True
    except Exception:
        pass


def handle_audio_diagnostic_cli(flags) -> bool:
    return handle_audio_diagnostic_cli_core(
        requested=flags.audio_diagnostic_requested,
        seconds=flags.audio_diagnostic_seconds,
        run_audio_diagnostic=run_audio_diagnostic,
        print_fn=print,
    )










def set_voice_status(status: str):
    app_runtime.terminal_io.set_voice_status(status, refresh_ui_runtime_state=refresh_ui_runtime_state)


def clear_status_line():
    app_runtime.terminal_io.clear_status_line()


def terminal_print(message: str):
    app_runtime.terminal_io.terminal_print(message)


def terminal_print_user_command(source: str, text: str):
    app_runtime.terminal_io.terminal_print_user_command(source, text)


def terminal_input(prompt: str) -> str:
    return app_runtime.terminal_io.terminal_input(prompt)


def render_status_line():
    app_runtime.terminal_io.render_status_line()


def read_user_input(
    voice_mode: bool,
    announce_ready: bool = True,
    fallback_to_text: bool = True,
    ready_message: str = "Pode falar...",
    ignored_text_filter=None,
    listener=None,
) -> str:
    return app_runtime.terminal_io.read_user_input(
        voice_mode,
        append_ui_history=append_ui_history,
        refresh_ui_runtime_state=refresh_ui_runtime_state,
        listen_once=listen_once,
        announce_ready=announce_ready,
        fallback_to_text=fallback_to_text,
        ready_message=ready_message,
        ignored_text_filter=ignored_text_filter,
        listener=listener,
    )












def maybe_remember_pending_voice_correction(command) -> None:
    global pending_command_learning_text

    result = maybe_remember_pending_voice_correction_core(
        command,
        VoiceLearningState(
            pending_command_learning_text=pending_command_learning_text,
            last_voice_text=last_voice_text,
        ),
        command_correction_text=command_correction_text,
        normalize_text=normalize_text,
        remember_voice_correction=remember_voice_correction,
    )
    pending_command_learning_text = result.state.pending_command_learning_text
    if result.learned:
        log_execution_event(
            "voice_correction_auto_learned",
            heard=result.heard,
            means=result.means,
        )


def wait_for_hotword(
    voice_mode: bool,
    hotword_mode: bool,
    voice_paused: bool,
) -> tuple[bool, bool, str]:
    return app_runtime.terminal_io.wait_for_hotword(
        voice_mode=voice_mode,
        hotword_mode=hotword_mode,
        voice_paused=voice_paused,
        maybe_announce_due_reminders=maybe_announce_due_reminders,
        hotword_listening_enabled=HOTWORD_LISTENING_ENABLED,
        hotkey_name=HOTKEY_NAME,
        poll_ui_text_command=poll_ui_text_command,
        consume_toggle_listening_hotkey_press=consume_toggle_listening_hotkey_press,
        consume_hotkey_press=consume_hotkey_press,
        play_activation_sound=play_activation_sound,
        listen_for_hotword=listen_for_hotword,
        output_response=output_response,
        refresh_ui_runtime_state=refresh_ui_runtime_state,
    )


def is_waiting_for_direct_response() -> bool:
    return (
        pending_command is not None
        or pending_smart_open_choice is not None
        or repeat_listen_until > time.time()
    )
















def maybe_learn_correction_for_last_voice(user_input: str) -> str | None:
    global last_voice_text

    result = maybe_learn_correction_for_last_voice_core(
        user_input,
        VoiceLearningState(
            pending_command_learning_text=pending_command_learning_text,
            last_voice_text=last_voice_text,
        ),
        normalize_text=normalize_text,
        remember_voice_correction=remember_voice_correction,
    )
    last_voice_text = result.state.last_voice_text
    return result.response


def handle_multi_step_request(user_input: str):
    return handle_multi_step_request_core(
        user_input,
        split_local_steps=split_local_steps,
        plan_actions=plan_actions,
        route_step=route,
        process_action=process_action,
        execute_command=execute_command,
    )


def execute_routine_steps(steps):
    return execute_routine_steps_core(
        steps,
        route_step=route,
        process_action=process_action,
        execute_command=execute_command,
    )


def main():
    global last_voice_text
    global pending_command
    global pending_command_learning_text
    global pending_smart_open_choice
    global pending_smart_open_invalid_attempts
    global creating_macro, macro_name, macro_steps
    global conversation_mode
    global conversation_ready_announced
    global dictation_mode
    global dictation_ready_announced
    global direct_response_ready_announced
    global repeat_listen_until

    flags = parse_app_flags(sys.argv)

    if flags.help_requested:
        print(HELP_TEXT)
        return
    voice_mode = flags.voice_mode
    hotword_mode = flags.hotword_mode
    ui_mode = flags.ui_mode
    voice_paused = False
    app_runtime.terminal_io.hotword_ui_enabled = voice_mode and hotword_mode

    if handle_windows_startup_cli():
        return

    if handle_voice_profile_cli():
        return

    if handle_audio_diagnostic_cli(flags):
        return
    clear()
    reset_ui_state()
    refresh_ui_runtime_state({"visible": False})
    refresh_improvement_brain(force=True)
    start_background_investment_refresh_loop()

    if ui_mode:
        show_ui_hud()

    if voice_mode:
        if hotword_mode:
            mode_text = (
                "Diga 'estagiario' ou fale tudo junto, como 'estagiario abre o chrome'."
                if HOTWORD_LISTENING_ENABLED
                else f"Aperte {HOTKEY_NAME} para falar."
            )
            output_response(
                f"Modo voz ativado. {mode_text} Aperte {TOGGLE_LISTENING_HOTKEY_NAME} para pausar/retomar.",
                voice_mode=False,
            )
            set_voice_status("ATIVA" if HOTWORD_LISTENING_ENABLED else f"BOTAO {HOTKEY_NAME}")
        else:
            output_response(
                "Modo voz ativado. Fale um comando ou digite se o microfone falhar.",
                voice_mode=False,
            )

        if bool(VOICE_PREFERENCES.get("startup_voice_greeting_enabled", True)):
            startup_message = startup_greeting_message().strip()
            if startup_message:
                output_response(startup_message, voice_mode=True)

        warm_common_tts_cache_async()
        if flags.defer_startup_briefing:
            schedule_startup_briefing_async(voice_mode=True)
        else:
            maybe_send_startup_briefing(voice_mode=True)

    refresh_ui_runtime_state()

    while True:
        maybe_announce_due_reminders(voice_mode)

        try:
            voice_cycle = run_voice_input_cycle(
                state=VoiceReadState(
                    voice_mode=voice_mode,
                    hotword_mode=hotword_mode,
                    voice_paused=voice_paused,
                    direct_response_ready_announced=direct_response_ready_announced,
                    conversation_ready_announced=conversation_ready_announced,
                    dictation_ready_announced=dictation_ready_announced,
                    conversation_mode=conversation_mode,
                    dictation_mode=dictation_mode,
                    pending_command=pending_command,
                    pending_smart_open_choice=pending_smart_open_choice,
                ),
                poll_ui_text_command=poll_ui_text_command,
                waiting_for_direct_response=is_waiting_for_direct_response,
                read_user_input=read_user_input,
                wait_for_hotword=wait_for_hotword,
                set_voice_status=set_voice_status,
                terminal_print_user_command=terminal_print_user_command,
                conversation_listener=listen_conversation_once,
                unreliable_conversation_filter=is_unreliable_conversation_text,
                transcription_artifact_filter=is_transcription_artifact,
            )
            user_input = voice_cycle.user_input
            queued_user_input = voice_cycle.queued_user_input
            voice_paused = voice_cycle.voice_paused
            direct_response_ready_announced = voice_cycle.direct_response_ready_announced
            conversation_ready_announced = voice_cycle.conversation_ready_announced
            dictation_ready_announced = voice_cycle.dictation_ready_announced
            if voice_cycle.repeat_listen_until is not None:
                repeat_listen_until = voice_cycle.repeat_listen_until
            if voice_cycle.hotword_ui_enabled is not None:
                app_runtime.terminal_io.hotword_ui_enabled = voice_cycle.hotword_ui_enabled
            if voice_cycle.should_break:
                clear_status_line()
                if voice_cycle.break_message:
                    output_response(voice_cycle.break_message, voice_cycle.break_voice_mode)
                break
        except KeyboardInterrupt:
            app_runtime.terminal_io.hotword_ui_enabled = False
            clear_status_line()
            output_response("Encerrando.", voice_mode=False)
            break

        if not user_input:
            continue

        if is_transcription_artifact(user_input):
            continue

        terminal_print_user_command(
            input_source_label(queued_user_input=queued_user_input, voice_mode=voice_mode),
            user_input,
        )

        log_execution_event(
            "user_input",
            text=user_input,
            voice_mode=voice_mode,
            mode=current_ui_mode_label(),
        )
        try:
            if maybe_remember_from_user_text(user_input, source="conversation"):
                save_operational_context()
        except Exception:
            pass

        correction_response = maybe_learn_correction_for_last_voice(user_input)
        if correction_response:
            output_response(correction_response, voice_mode)
            continue

        pronunciation_response = maybe_handle_pronunciation_command_core(user_input)
        if pronunciation_response:
            output_response(pronunciation_response, voice_mode)
            continue

        humor_response = maybe_handle_humor_command_core(user_input, VOICE_PREFERENCES, refresh_voice_preferences)
        if humor_response:
            output_response(humor_response, voice_mode)
            continue

        input_device_response = maybe_handle_input_device_command_core(user_input, refresh_voice_preferences)
        if input_device_response:
            output_response(input_device_response, voice_mode)
            continue

        voice_profile_response = maybe_handle_voice_profile_command_core(user_input, VOICE_PREFERENCES, refresh_voice_preferences)
        if voice_profile_response:
            output_response(voice_profile_response, voice_mode)
            continue

        work_mode_response = maybe_handle_work_mode_command_core(user_input, show_ui_hud)
        if work_mode_response:
            refresh_improvement_brain(force=True)
            output_response(work_mode_response, voice_mode)
            continue

        ui_response = maybe_handle_ui_command(user_input)
        if ui_response:
            output_response(ui_response, voice_mode)
            continue

        training_response = maybe_handle_training_command_core(user_input, show_training_in_ui)
        if training_response:
            output_response(training_response, voice_mode)
            continue

        operational_result = maybe_handle_operational_command(user_input)
        if operational_result:
            if operational_result.refresh_improvement_brain:
                refresh_improvement_brain(force=True)
            output_response(operational_result.response, voice_mode)
            if operational_result.announce_codex_suggestion:
                maybe_announce_codex_suggestion(voice_mode)
            continue

        interactive_result = handle_interactive_modes(
            user_input,
            InteractiveModesState(
                dictation_mode=dictation_mode,
                dictation_ready_announced=dictation_ready_announced,
                conversation_mode=conversation_mode,
                conversation_ready_announced=conversation_ready_announced,
            ),
            voice_mode=voice_mode,
            hotword_mode=hotword_mode,
            hotkey_name=HOTKEY_NAME,
            waiting_for_direct_response=is_waiting_for_direct_response,
            set_voice_status=set_voice_status,
            type_text=type_text,
            chat_response=chat_response,
        )
        dictation_mode = interactive_result.state.dictation_mode
        dictation_ready_announced = interactive_result.state.dictation_ready_announced
        conversation_mode = interactive_result.state.conversation_mode
        conversation_ready_announced = interactive_result.state.conversation_ready_announced
        if interactive_result.handled:
            if interactive_result.message:
                response_voice_mode = voice_mode if interactive_result.voice_mode is None else interactive_result.voice_mode
                output_response(interactive_result.message, response_voice_mode)
            continue

        direct_response_result = handle_direct_response_flow(
            user_input,
            DirectResponseState(
                pending_command=pending_command,
                pending_command_learning_text=pending_command_learning_text,
                pending_smart_open_choice=pending_smart_open_choice,
                pending_smart_open_invalid_attempts=pending_smart_open_invalid_attempts,
                direct_response_ready_announced=direct_response_ready_announced,
            ),
            execute_command=lambda command: execute_command(command, voice_mode=voice_mode),
            process_action=process_action,
            remember_correction=maybe_remember_pending_voice_correction,
            retry_invalid_smart_open=True,
        )
        pending_command = direct_response_result.state.pending_command
        pending_command_learning_text = direct_response_result.state.pending_command_learning_text
        pending_smart_open_choice = direct_response_result.state.pending_smart_open_choice
        pending_smart_open_invalid_attempts = direct_response_result.state.pending_smart_open_invalid_attempts
        direct_response_ready_announced = direct_response_result.state.direct_response_ready_announced
        if direct_response_result.handled:
            output_response(direct_response_result.message, voice_mode)
            continue

        original_user_input = user_input
        user_input = maybe_normalize_voice_command_core(user_input, voice_mode, apply_voice_correction, route)
        if original_user_input != user_input:
            log_execution_event(
                "voice_input_normalized",
                original=original_user_input,
                normalized=user_input,
            )
        if voice_mode and original_user_input == user_input:
            last_voice_text = original_user_input
        refresh_ui_runtime_state({"last_command": user_input})

        macro_result = handle_macro_recording(
            user_input,
            MacroRecordingState(
                creating_macro=creating_macro,
                macro_name=macro_name,
                macro_steps=macro_steps,
            ),
            route=route,
            process_action=process_action,
            add_macro=add_macro,
        )
        creating_macro = macro_result.state.creating_macro
        macro_name = macro_result.state.macro_name
        macro_steps = macro_result.state.macro_steps
        if macro_result.handled:
            output_response(macro_result.message, voice_mode)
            continue

        direct_response_result = handle_direct_response_flow(
            user_input,
            DirectResponseState(
                pending_command=pending_command,
                pending_command_learning_text=pending_command_learning_text,
                pending_smart_open_choice=pending_smart_open_choice,
                pending_smart_open_invalid_attempts=pending_smart_open_invalid_attempts,
                direct_response_ready_announced=direct_response_ready_announced,
            ),
            execute_command=lambda command: execute_command(command, voice_mode=voice_mode),
            process_action=process_action,
            remember_correction=maybe_remember_pending_voice_correction,
            retry_invalid_smart_open=False,
        )
        pending_command = direct_response_result.state.pending_command
        pending_command_learning_text = direct_response_result.state.pending_command_learning_text
        pending_smart_open_choice = direct_response_result.state.pending_smart_open_choice
        pending_smart_open_invalid_attempts = direct_response_result.state.pending_smart_open_invalid_attempts
        direct_response_ready_announced = direct_response_result.state.direct_response_ready_announced
        if direct_response_result.handled:
            output_response(direct_response_result.message, voice_mode)
            continue

        if looks_like_multi_step_request(user_input):
            result = handle_multi_step_request(user_input)
            if result:
                output_response(result, voice_mode)
                continue

        raw_action = route(user_input)
        log_execution_event(
            "route_result",
            input=user_input,
            intent=raw_action.get("intent"),
            target=raw_action.get("target"),
        )

        post_route_result = handle_post_route_action(
            raw_action,
            user_input=user_input,
            original_user_input=original_user_input,
            voice_mode=voice_mode,
            state=PostRouteState(
                pending_command=pending_command,
                pending_command_learning_text=pending_command_learning_text,
                pending_smart_open_choice=pending_smart_open_choice,
                pending_smart_open_invalid_attempts=pending_smart_open_invalid_attempts,
                direct_response_ready_announced=direct_response_ready_announced,
                conversation_mode=conversation_mode,
                conversation_ready_announced=conversation_ready_announced,
            ),
            last_command=app_runtime.runtime_state.last_command,
            process_action=process_action,
            execute_command=lambda command: execute_command(command, voice_mode=voice_mode),
            execute_routine_steps=execute_routine_steps,
            clear_chat_history=clear_chat_history,
            confirmation_prompt=confirmation_prompt,
            smart_open_needs_choice=smart_open_needs_choice,
            show_map_in_ui=show_map_in_ui,
            update_runtime_state=app_runtime.runtime_state.update,
            is_unclear_response=is_unclear_response,
            maybe_suggest_probable_command=maybe_suggest_probable_command,
        )
        pending_command = post_route_result.state.pending_command
        pending_command_learning_text = post_route_result.state.pending_command_learning_text
        pending_smart_open_choice = post_route_result.state.pending_smart_open_choice
        pending_smart_open_invalid_attempts = post_route_result.state.pending_smart_open_invalid_attempts
        direct_response_ready_announced = post_route_result.state.direct_response_ready_announced
        conversation_mode = post_route_result.state.conversation_mode
        conversation_ready_announced = post_route_result.state.conversation_ready_announced
        if post_route_result.handled:
            output_response(post_route_result.message, voice_mode)
            continue


if __name__ == "__main__":
    run_with_startup_diagnostics(sys.argv, main)
