import sys
from pathlib import Path
import time
from copy import deepcopy

from core.app_bootstrap import HELP_TEXT, parse_app_flags
from core.app_runtime import AppRuntime, AssistantRunConfig, AssistantRuntimeRunner
from core.command_feedback import (
    command_preview,
)
from core.command_service import process_raw_action
from core.confirmation import confirmation_prompt
from core.direct_response_flow import handle_direct_response_flow
from core.executor import execute
from core.humor_commands import maybe_handle_humor_command as maybe_handle_humor_command_core
from core.improvement_brain import ImprovementBrain
from core.input_device_commands import maybe_handle_input_device_command as maybe_handle_input_device_command_core
from core.interactive_modes import handle_interactive_modes
from core.deferred_runtime import run_deferred
from core.axel_brain import build_axel_brain_decision
from core.axel_brain_commands import maybe_handle_axel_brain_runtime_command
from core.axel_brain_contract import build_axel_brain_contract
from core.intent_complexity import classify_intent_complexity
from core.latency_metrics import log_latency_stage
from core.macro_recording import handle_macro_recording
from core.main_loop import MainLoopHandlers, run_main_loop as run_main_loop_core
from core.operational_command_chain import maybe_handle_operational_command
from core.performance_mode import runtime_idle_sleep_seconds_from_state
from core.planner import looks_like_multi_step_request, plan_actions, split_local_steps
from core.post_route_flow import handle_post_route_action
from core.pronunciation_commands import maybe_handle_pronunciation_command as maybe_handle_pronunciation_command_core
from core.project_health import format_project_health_panel
from core.reminder_announcer import ReminderAnnouncer
from core.response_pipeline import ResponsePipeline
from core.router import route, route_trace
from core.router_utils import normalize_text
from core.routine_execution import (
    execute_routine_steps as execute_routine_steps_core,
)
from core.routine_execution import (
    handle_multi_step_request as handle_multi_step_request_core,
)
from core.setup_check import format_setup_report
from core.update_check import format_update_report
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
from core.startup_flow import StartupFlowHandlers, run_startup_flow
from core.study_commands import maybe_handle_study_command as maybe_handle_study_command_core
from core.shared_commands import maybe_handle_shared_command
from core.training_commands import maybe_handle_training_command as maybe_handle_training_command_core
from core.turn_flow import TurnFlowHandlers, handle_user_turn as handle_user_turn_core
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
from core.voice_loop import input_source_label, run_voice_input_cycle
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
from memory.long_memory import curate_recent_ui_history, maybe_remember_from_user_text
from memory.macros import add_macro
from memory.memory_backup import create_memory_backup
from memory.operational_context import (
    save_operational_context,
)
from memory.piper_voice_manager import (
    apply_piper_voice,
    download_piper_voice,
    list_piper_voices,
)
from memory.agenda import consume_due_agenda_items
from memory.reminders import consume_due_reminders
from memory.session import add_turn, clear
from memory.training import (
    consume_due_training_reminder,
    training_snapshot,
)
from memory.ui_commands import dequeue_ui_command_item
from memory.ui_state import append_ui_history, append_ui_notification, load_ui_state, reset_ui_state
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
assistant_state = app_runtime.assistant_state
STARTUP_BRIEFING_STATE_PATH = Path("memory") / "startup_briefing_state.json"
LONG_MEMORY_AUTOCURATE_TURNS = 12
LONG_MEMORY_AUTOCURATE_INTERVAL_SECONDS = 30 * 60

VOICE_PREFERENCES = load_voice_preferences()


def log_execution_event(event_type: str, **payload):
    try:
        append_execution_log(event_type, payload)
    except Exception:
        pass


def run_noncritical_task(name: str, task, *, defer: bool = False):
    if defer:
        return run_deferred(name, task, log_event=log_execution_event)
    task()
    return None


def process_action(raw_action: dict):
    return process_raw_action(raw_action, app_runtime.runtime_state, log_execution_event)


def route_user_input(user_input: str, *, source: str = "turn") -> dict:
    started_at = time.perf_counter()
    trace = route_trace(user_input)
    raw_action = (
        trace.match.result
        if trace.match
        else {"intent": "respond", "target": None, "response": "Nao entendi."}
    )
    intent_level = trace.match.intent_level if trace.match else "conversa"
    complexity = classify_intent_complexity(user_input, intent_level=intent_level, raw_action=raw_action)
    brain_decision = build_axel_brain_decision(
        user_input,
        raw_action,
        intent_level=intent_level,
        complexity_kind=complexity.kind,
    )
    decision_plan = brain_decision.plan
    app_runtime.runtime_state.axel_brain_plan = decision_plan.to_dict()
    app_runtime.runtime_state.axel_brain_brief = brain_decision.brief.to_dict()
    route_payload = {
        "source": source,
        "input": user_input,
        "intent": raw_action.get("intent"),
        "target": raw_action.get("target"),
        "group": trace.match.group_name if trace.match else "",
        "detector": trace.match.detector_name if trace.match else "",
        "intent_level": intent_level,
        "complexity": complexity.kind,
        "complexity_reason": complexity.reason,
        "checked_detectors": trace.checked_detectors,
        "checked_groups": list(trace.checked_groups),
    }
    app_runtime.runtime_state.last_route_trace = route_payload
    brain_contract = build_axel_brain_contract(
        source=source,
        user_input=user_input,
        raw_action=raw_action,
        plan=decision_plan,
        brief=brain_decision.brief,
        route_trace=route_payload,
    )
    app_runtime.runtime_state.axel_brain_contract = brain_contract
    app_runtime.runtime_state.record_axel_brain_decision(
        decision_plan.to_dict(),
        brain_contract,
        route_payload,
    )
    log_execution_event(
        "route_result",
        source=source,
        input=user_input,
        intent=raw_action.get("intent"),
        target=raw_action.get("target"),
        group=trace.match.group_name if trace.match else "",
        detector=trace.match.detector_name if trace.match else "",
        intent_level=intent_level,
        complexity=complexity.kind,
        complexity_reason=complexity.reason,
        should_plan=complexity.should_plan,
        should_use_llm=complexity.should_use_llm,
        checked_detectors=trace.checked_detectors,
        checked_groups=list(trace.checked_groups),
        decision_plan=decision_plan.to_dict(),
        specialist_brief=brain_decision.brief.to_dict(),
        axel_brain_contract=brain_contract,
    )
    if source in {"turn", "ui_bridge"}:
        run_noncritical_task(
            "routine_learning",
            lambda: observe_routine_command_for_learning(user_input, raw_action, source=source, decision_plan=decision_plan),
            defer=source == "turn",
        )
    log_latency_stage(
        log_execution_event,
        "routing",
        started_at,
        source=source,
        intent=raw_action.get("intent"),
        group=trace.match.group_name if trace.match else "",
        detector=trace.match.detector_name if trace.match else "",
        intent_level=intent_level,
        complexity=complexity.kind,
    )
    return raw_action


def observe_routine_command_for_learning(user_input: str, raw_action: dict, *, source: str, decision_plan=None) -> None:
    from memory.routine_learning import observe_routine_command
    from memory.skill_learning import observe_skill_opportunity

    suggestion = observe_routine_command(user_input, raw_action, source=source)
    if suggestion:
        log_execution_event(
            "routine_suggestion_created",
            title=suggestion.get("title"),
            pair_id=suggestion.get("pair_id"),
        )
        append_ui_notification("routine_learning", str(suggestion.get("title") or ""), level="info")

    if decision_plan is None:
        return

    skill_suggestion = observe_skill_opportunity(
        user_input,
        raw_action,
        source=source,
        toolset=str(getattr(decision_plan, "toolset", "") or ""),
        agent=str(getattr(decision_plan, "agent", "") or ""),
    )
    if skill_suggestion:
        log_execution_event(
            "skill_suggestion_created",
            title=skill_suggestion.get("title"),
            pattern_id=skill_suggestion.get("pattern_id"),
            agent=skill_suggestion.get("agent"),
            toolset=skill_suggestion.get("toolset"),
        )
        append_ui_notification("skill_learning", str(skill_suggestion.get("title") or ""), level="info")




def show_action_progress(command, voice_mode: bool = False):
    get_response_pipeline().show_action_progress(
        command,
        voice_mode=voice_mode,
        silent_ui_command_active=assistant_state.silent_ui_command_active,
    )


def execute_command(command, voice_mode: bool = False):
    return get_response_pipeline().execute_command(
        command,
        voice_mode=voice_mode,
        silent_ui_command_active=assistant_state.silent_ui_command_active,
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
    result = get_response_pipeline().output_response(
        message,
        voice_mode,
        direct_response_ready_announced=assistant_state.direct_response_ready_announced,
        silent_ui_command_active=assistant_state.silent_ui_command_active,
        interrupt_current_tts=interrupt_current_tts,
        wait_for_tts=wait_for_tts,
    )
    if result.repeat_listen_until is not None:
        assistant_state.repeat_listen_until = result.repeat_listen_until
    assistant_state.direct_response_ready_announced = result.direct_response_ready_announced


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
    maybe_speak_pending_voice_notification(voice_mode)


def maybe_speak_pending_voice_notification(voice_mode: bool) -> bool:
    from memory.ui_state import load_ui_state, pop_next_voice_notification
    from services.voice_notification_service import speak_next_pending_voice_notification

    return speak_next_pending_voice_notification(
        voice_mode=voice_mode,
        speak=speak,
        load_ui_state=load_ui_state,
        pop_next_voice_notification=pop_next_voice_notification,
    )


def consume_due_schedule_items() -> list[dict]:
    due = []
    try:
        due.extend(consume_due_reminders())
    except Exception:
        pass
    try:
        due.extend(consume_due_agenda_items())
    except Exception:
        pass
    return due


def get_reminder_announcer() -> ReminderAnnouncer:
    if app_runtime.reminder_announcer is None:
        app_runtime.reminder_announcer = ReminderAnnouncer(
            consume_due_training_reminder=consume_due_training_reminder,
            consume_due_reminders=consume_due_schedule_items,
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
        dictation_mode=assistant_state.dictation_mode,
        conversation_mode=assistant_state.conversation_mode,
        waiting_for_direct_response=is_waiting_for_direct_response(),
    )




def _ui_runtime_patch() -> dict:
    from core.performance_mode import performance_settings_from_state
    from memory.ui_state import load_ui_state
    from memory.skill_learning import pending_skill_suggestions

    active_device = get_active_input_device_info() or {}
    perf = performance_settings_from_state(load_ui_state())
    return {
        "assistant_name": "Axel",
        "status": app_runtime.terminal_io.voice_status or "INATIVO",
        "mode": current_ui_mode_label(),
        "microphone": active_device.get("name", ""),
        "assistant_style": current_assistant_style_label(),
        "performance_mode": perf.mode,
        "performance_settings": perf.as_dict(),
        "voice_profile": current_voice_profile_label(),
        "hotword_enabled": bool(app_runtime.terminal_io.hotword_ui_enabled),
        "conversation_mode": bool(assistant_state.conversation_mode),
        "dictation_mode": bool(assistant_state.dictation_mode),
        "last_command": command_preview(app_runtime.runtime_state.last_command),
        "axel_brain_plan": dict(getattr(app_runtime.runtime_state, "axel_brain_plan", {}) or {}),
        "axel_brain_brief": dict(getattr(app_runtime.runtime_state, "axel_brain_brief", {}) or {}),
        "axel_brain_contract": dict(getattr(app_runtime.runtime_state, "axel_brain_contract", {}) or {}),
        "axel_brain_history": list(getattr(app_runtime.runtime_state, "axel_brain_history", []) or []),
        "axel_brain_timeline": list(getattr(app_runtime.runtime_state, "axel_brain_timeline", []) or []),
        "axel_brain_history_summary": app_runtime.runtime_state.axel_brain_history_summary(),
        "last_route_trace": dict(getattr(app_runtime.runtime_state, "last_route_trace", {}) or {}),
        "skill_suggestions": pending_skill_suggestions(limit=5),
    }


def get_ui_runtime() -> UIRuntimeService:
    if app_runtime.ui_runtime is None:
        app_runtime.ui_runtime = UIRuntimeService(
            root_dir=Path(__file__).resolve().parent,
            python_executable=sys.executable,
            runtime_patch=_ui_runtime_patch,
            normalize_text=normalize_text,
            route=lambda text: route_user_input(text, source="ui_bridge"),
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
    queued = get_ui_runtime().poll_text_command(refresh_runtime_state=refresh_ui_runtime_state)
    assistant_state.silent_ui_command_active = get_ui_runtime().silent_command_active
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


def safe_console_text(message: str, encoding: str | None = None) -> str:
    output_encoding = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    return str(message).encode(output_encoding, errors="replace").decode(output_encoding, errors="replace")


def handle_doctor_cli(flags) -> bool:
    if not getattr(flags, "doctor_requested", False):
        return False
    print(safe_console_text(format_project_health_panel()))
    return True


def handle_setup_cli(flags) -> bool:
    if not getattr(flags, "setup_requested", False):
        return False
    print(safe_console_text(format_setup_report()))
    return True


def handle_memory_backup_cli(flags) -> bool:
    if not getattr(flags, "memory_backup_requested", False):
        return False
    result = create_memory_backup()
    print(
        safe_console_text(
            f"Backup de memoria criado: {result.backup_dir.name}. "
            f"Arquivos copiados: {len(result.copied)}; ausentes: {len(result.skipped)}. "
            f"Manifesto: {result.manifest_path}"
        )
    )
    return True


def handle_update_cli(flags) -> bool:
    if not getattr(flags, "update_requested", False):
        return False
    print(safe_console_text(format_update_report()))
    return True










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
    started_at = time.perf_counter()
    try:
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
    finally:
        if voice_mode:
            log_latency_stage(
                log_execution_event,
                "stt",
                started_at,
                announce_ready=announce_ready,
                fallback_to_text=fallback_to_text,
                listener=bool(listener),
            )












def maybe_remember_pending_voice_correction(command) -> None:
    result = maybe_remember_pending_voice_correction_core(
        command,
        VoiceLearningState(
            pending_command_learning_text=assistant_state.pending_command_learning_text,
            last_voice_text=assistant_state.last_voice_text,
        ),
        command_correction_text=command_correction_text,
        normalize_text=normalize_text,
        remember_voice_correction=remember_voice_correction,
    )
    assistant_state.pending_command_learning_text = result.state.pending_command_learning_text
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
        idle_sleep_seconds=lambda: runtime_idle_sleep_seconds_from_state(current_ui_state_patch()),
    )


def current_ui_state_patch() -> dict:
    try:
        return load_ui_state()
    except Exception:
        return {}


def is_waiting_for_direct_response() -> bool:
    return assistant_state.is_waiting_for_direct_response()
















def maybe_learn_correction_for_last_voice(user_input: str) -> str | None:
    result = maybe_learn_correction_for_last_voice_core(
        user_input,
        VoiceLearningState(
            pending_command_learning_text=assistant_state.pending_command_learning_text,
            last_voice_text=assistant_state.last_voice_text,
        ),
        normalize_text=normalize_text,
        remember_voice_correction=remember_voice_correction,
    )
    assistant_state.last_voice_text = result.state.last_voice_text
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


def run_direct_response_flow(user_input: str, *, voice_mode: bool, retry_invalid_smart_open: bool):
    result = handle_direct_response_flow(
        user_input,
        assistant_state.to_direct_response_state(),
        execute_command=lambda command: execute_command(command, voice_mode=voice_mode),
        process_action=process_action,
        remember_correction=maybe_remember_pending_voice_correction,
        retry_invalid_smart_open=retry_invalid_smart_open,
    )
    assistant_state.apply_direct_response_state(result.state)
    return result


def handle_direct_response_command(
    user_input: str,
    *,
    voice_mode: bool,
    retry_invalid_smart_open: bool,
) -> bool:
    result = run_direct_response_flow(
        user_input,
        voice_mode=voice_mode,
        retry_invalid_smart_open=retry_invalid_smart_open,
    )
    if not result.handled:
        return False

    output_response(result.message, voice_mode)
    return True


def handle_startup_cli(flags) -> bool:
    return (
        handle_windows_startup_cli()
        or handle_voice_profile_cli()
        or handle_setup_cli(flags)
        or handle_memory_backup_cli(flags)
        or handle_update_cli(flags)
        or handle_doctor_cli(flags)
        or handle_audio_diagnostic_cli(flags)
    )


def initialize_runtime_services(ui_mode: bool) -> None:
    clear()
    reset_ui_state()
    refresh_ui_runtime_state({"visible": False})
    refresh_improvement_brain(force=True)
    start_background_investment_refresh_loop()

    if ui_mode:
        show_ui_hud()


def announce_voice_startup(*, hotword_mode: bool, defer_startup_briefing: bool) -> None:
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
    if defer_startup_briefing:
        schedule_startup_briefing_async(voice_mode=True)
    else:
        maybe_send_startup_briefing(voice_mode=True)


def run_startup(*, flags, voice_mode: bool, hotword_mode: bool, ui_mode: bool) -> bool:
    return run_startup_flow(
        flags=flags,
        voice_mode=voice_mode,
        hotword_mode=hotword_mode,
        ui_mode=ui_mode,
        defer_startup_briefing=flags.defer_startup_briefing,
        handlers=StartupFlowHandlers(
            handle_startup_cli=handle_startup_cli,
            initialize_runtime_services=initialize_runtime_services,
            announce_voice_startup=announce_voice_startup,
            refresh_ui_runtime_state=refresh_ui_runtime_state,
        ),
    )


def handle_pre_route_command(user_input: str, *, voice_mode: bool) -> bool:
    correction_response = maybe_learn_correction_for_last_voice(user_input)
    if correction_response:
        output_response(correction_response, voice_mode)
        return True

    def stop_local_pending() -> None:
        assistant_state.pending_command = None
        assistant_state.pending_command_learning_text = ""
        assistant_state.pending_smart_open_choice = None
        assistant_state.pending_smart_open_invalid_attempts = 0
        assistant_state.direct_response_ready_announced = False
        assistant_state.conversation_mode = False
        assistant_state.conversation_ready_announced = False

    def retry_last_local_command() -> str:
        last_command = app_runtime.runtime_state.last_command
        if last_command is None:
            return "Nada para tentar novamente agora."
        return execute_command(deepcopy(last_command), voice_mode=voice_mode)

    def undo_last_local_action() -> str:
        has_pending = (
            assistant_state.pending_command is not None
            or assistant_state.pending_smart_open_choice is not None
            or assistant_state.conversation_mode
        )
        if has_pending:
            stop_local_pending()
            return "Pendencia local cancelada. Ainda nao desfaco automaticamente a ultima acao ja executada."
        return "Nao ha pendencia aberta para desfazer. Undo real de acoes ja executadas ainda nao esta liberado."

    shared_response = maybe_handle_shared_command(
        user_input,
        runtime_state=app_runtime.runtime_state,
        allow_state_changes=True,
        clear_chat=clear_chat_history,
        reset_ui=reset_ui_state,
        stop_pending=stop_local_pending,
        retry_last=retry_last_local_command,
        undo_last=undo_last_local_action,
        refresh_preferences=refresh_voice_preferences,
    )
    if shared_response:
        output_response(shared_response, voice_mode)
        return True

    pronunciation_response = maybe_handle_pronunciation_command_core(user_input)
    if pronunciation_response:
        output_response(pronunciation_response, voice_mode)
        return True

    humor_response = maybe_handle_humor_command_core(user_input, VOICE_PREFERENCES, refresh_voice_preferences)
    if humor_response:
        output_response(humor_response, voice_mode)
        return True

    input_device_response = maybe_handle_input_device_command_core(user_input, refresh_voice_preferences)
    if input_device_response:
        output_response(input_device_response, voice_mode)
        return True

    voice_profile_response = maybe_handle_voice_profile_command_core(
        user_input,
        VOICE_PREFERENCES,
        refresh_voice_preferences,
    )
    if voice_profile_response:
        output_response(voice_profile_response, voice_mode)
        return True

    work_mode_response = maybe_handle_work_mode_command_core(user_input, show_ui_hud)
    if work_mode_response:
        refresh_improvement_brain(force=True)
        output_response(work_mode_response, voice_mode)
        return True

    ui_response = maybe_handle_ui_command(user_input)
    if ui_response:
        output_response(ui_response, voice_mode)
        return True

    training_response = maybe_handle_training_command_core(user_input, show_training_in_ui)
    if training_response:
        output_response(training_response, voice_mode)
        return True

    study_response = maybe_handle_study_command_core(user_input, show_ui_hud)
    if study_response:
        output_response(study_response, voice_mode)
        return True

    axel_brain_response = maybe_handle_axel_brain_runtime_command(user_input, app_runtime.runtime_state)
    if axel_brain_response:
        output_response(axel_brain_response, voice_mode)
        return True

    operational_result = maybe_handle_operational_command(user_input)
    if operational_result:
        if operational_result.refresh_improvement_brain:
            refresh_improvement_brain(force=True)
        output_response(operational_result.response, voice_mode)
        if operational_result.announce_codex_suggestion:
            maybe_announce_codex_suggestion(voice_mode)
        return True

    return False


def record_user_turn_start(user_input: str, *, queued_user_input: str, voice_mode: bool) -> None:
    add_turn("user", user_input, source=input_source_label(queued_user_input=queued_user_input, voice_mode=voice_mode))
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
    run_noncritical_task(
        "conversation_memory",
        lambda: remember_user_context_from_turn(user_input),
        defer=voice_mode,
    )


def remember_user_context_from_turn(user_input: str) -> None:
    try:
        if maybe_remember_from_user_text(user_input, source="conversation"):
            save_operational_context()
    except Exception:
        pass
    maybe_autocurate_long_memory_from_history()


def maybe_autocurate_long_memory_from_history() -> None:
    try:
        app_runtime.runtime_state.turns_since_long_memory_curated += 1
        turns = int(app_runtime.runtime_state.turns_since_long_memory_curated or 0)
        last_at = float(app_runtime.runtime_state.last_long_memory_curated_at or 0.0)
        now = time.time()
        due_by_turns = turns >= LONG_MEMORY_AUTOCURATE_TURNS
        due_by_time = last_at > 0 and (now - last_at) >= LONG_MEMORY_AUTOCURATE_INTERVAL_SECONDS
        if not due_by_turns and not due_by_time:
            return

        app_runtime.runtime_state.turns_since_long_memory_curated = 0
        app_runtime.runtime_state.last_long_memory_curated_at = now
        added = curate_recent_ui_history(limit=30)
        log_execution_event("long_memory_autocurated", added=added)
        if added:
            save_operational_context()
    except Exception:
        pass


def handle_interactive_command(user_input: str, *, voice_mode: bool, hotword_mode: bool) -> bool:
    result = handle_interactive_modes(
        user_input,
        assistant_state.to_interactive_modes_state(),
        voice_mode=voice_mode,
        hotword_mode=hotword_mode,
        hotkey_name=HOTKEY_NAME,
        waiting_for_direct_response=is_waiting_for_direct_response,
        set_voice_status=set_voice_status,
        type_text=type_text,
        chat_response=chat_response,
    )
    assistant_state.apply_interactive_modes_state(result.state)
    if not result.handled:
        return False

    if result.message:
        response_voice_mode = voice_mode if result.voice_mode is None else result.voice_mode
        output_response(result.message, response_voice_mode)
    return True


def normalize_user_command(user_input: str, *, voice_mode: bool) -> tuple[str, str]:
    original_user_input = user_input
    normalized_user_input = maybe_normalize_voice_command_core(
        user_input,
        voice_mode,
        apply_voice_correction,
        route,
    )
    if original_user_input != normalized_user_input:
        log_execution_event(
            "voice_input_normalized",
            original=original_user_input,
            normalized=normalized_user_input,
        )
    if voice_mode and original_user_input == normalized_user_input:
        assistant_state.last_voice_text = original_user_input
    refresh_ui_runtime_state({"last_command": normalized_user_input})
    return original_user_input, normalized_user_input


def maybe_open_media_panel_for_action(raw_action: dict) -> None:
    intent = str((raw_action or {}).get("intent") or "")
    if intent not in {
        "browser_search_music",
        "browser_music_session",
        "browser_surprise_music",
        "media_play_pause",
        "media_next",
        "media_previous",
        "media_play_pause_target",
        "media_play_target",
        "media_pause_target",
        "media_next_target",
        "media_previous_target",
    }:
        return
    refresh_ui_runtime_state({"active_panel": "midia", "open_panels": ["midia"]})


def handle_macro_command(user_input: str, *, voice_mode: bool) -> bool:
    result = handle_macro_recording(
        user_input,
        assistant_state.to_macro_recording_state(),
        route=lambda text: route_user_input(text, source="macro_recording"),
        process_action=process_action,
        add_macro=add_macro,
    )
    assistant_state.apply_macro_recording_state(result.state)
    if not result.handled:
        return False

    output_response(result.message, voice_mode)
    return True


def handle_routed_command(user_input: str, *, original_user_input: str, voice_mode: bool) -> bool:
    if looks_like_multi_step_request(user_input):
        result = handle_multi_step_request(user_input)
        if result:
            output_response(result, voice_mode)
            return True

    raw_action = route_user_input(user_input, source="turn")
    maybe_open_media_panel_for_action(raw_action)

    result = handle_post_route_action(
        raw_action,
        user_input=user_input,
        original_user_input=original_user_input,
        voice_mode=voice_mode,
        state=assistant_state.to_post_route_state(),
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
        decision_plan=getattr(app_runtime.runtime_state, "axel_brain_plan", {}) or {},
    )
    assistant_state.apply_post_route_state(result.state)
    if not result.handled:
        return False

    output_response(result.message, voice_mode)
    return True


def handle_user_turn(
    user_input: str,
    *,
    queued_user_input: str,
    voice_mode: bool,
    hotword_mode: bool,
) -> bool:
    return handle_user_turn_core(
        user_input,
        queued_user_input=queued_user_input,
        voice_mode=voice_mode,
        hotword_mode=hotword_mode,
        handlers=TurnFlowHandlers(
            record_user_turn_start=record_user_turn_start,
            handle_pre_route_command=handle_pre_route_command,
            handle_interactive_command=handle_interactive_command,
            handle_direct_response_command=handle_direct_response_command,
            normalize_user_command=normalize_user_command,
            handle_macro_command=handle_macro_command,
            handle_routed_command=handle_routed_command,
        ),
    )


def read_next_turn_input(*, voice_mode: bool, hotword_mode: bool, voice_paused: bool):
    result = run_voice_input_cycle(
        state=assistant_state.to_voice_read_state(
            voice_mode=voice_mode,
            hotword_mode=hotword_mode,
            voice_paused=voice_paused,
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
    assistant_state.apply_voice_cycle_result(result)
    if result.hotword_ui_enabled is not None:
        app_runtime.terminal_io.hotword_ui_enabled = result.hotword_ui_enabled
    return result


def handle_voice_cycle_break(voice_cycle) -> bool:
    if not voice_cycle.should_break:
        return False

    clear_status_line()
    if voice_cycle.break_message:
        output_response(voice_cycle.break_message, voice_cycle.break_voice_mode)
    return True


def handle_main_loop_keyboard_interrupt() -> None:
    app_runtime.terminal_io.hotword_ui_enabled = False
    clear_status_line()
    output_response("Encerrando.", voice_mode=False)


def run_main_loop(*, voice_mode: bool, hotword_mode: bool, voice_paused: bool = False) -> None:
    run_main_loop_core(
        voice_mode=voice_mode,
        hotword_mode=hotword_mode,
        voice_paused=voice_paused,
        handlers=MainLoopHandlers(
            maybe_announce_due_reminders=maybe_announce_due_reminders,
            read_next_turn_input=read_next_turn_input,
            handle_voice_cycle_break=handle_voice_cycle_break,
            handle_keyboard_interrupt=handle_main_loop_keyboard_interrupt,
            is_transcription_artifact=is_transcription_artifact,
            handle_user_turn=handle_user_turn,
        ),
    )


def main():
    flags = parse_app_flags(sys.argv)

    if flags.help_requested:
        print(HELP_TEXT)
        return

    runner = AssistantRuntimeRunner(
        app_runtime=app_runtime,
        run_startup=run_startup,
        run_main_loop=run_main_loop,
    )
    runner.run(
        AssistantRunConfig(
            flags=flags,
            voice_mode=flags.voice_mode,
            hotword_mode=flags.hotword_mode,
            ui_mode=flags.ui_mode,
        )
    )


if __name__ == "__main__":
    run_with_startup_diagnostics(sys.argv, main)
