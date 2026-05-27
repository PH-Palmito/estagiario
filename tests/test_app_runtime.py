import unittest

from types import SimpleNamespace

from core.app_runtime import AppRuntime, AssistantRunConfig, AssistantRuntimeRunner
from core.assistant_state import AssistantState
from core.direct_response_flow import DirectResponseState
from core.interactive_modes import InteractiveModesState
from core.macro_recording import MacroRecordingState
from core.post_route_flow import PostRouteState
from core.runtime_state import RuntimeState
from core.terminal_voice_io import TerminalVoiceIO
from core.voice_loop import VoiceInputCycleResult


class AppRuntimeTests(unittest.TestCase):
    def test_initializes_runtime_state_and_terminal_io(self):
        runtime = AppRuntime(ui_history_max_items=12)

        self.assertIsInstance(runtime.runtime_state, RuntimeState)
        self.assertIsInstance(runtime.assistant_state, AssistantState)
        self.assertIsInstance(runtime.terminal_io, TerminalVoiceIO)
        self.assertEqual(runtime.terminal_io.ui_history_max_items, 12)

    def test_assistant_state_tracks_direct_response_wait(self):
        runtime = AppRuntime()

        self.assertFalse(runtime.assistant_state.is_waiting_for_direct_response(now=100.0))

        runtime.assistant_state.repeat_listen_until = 101.0

        self.assertTrue(runtime.assistant_state.is_waiting_for_direct_response(now=100.0))

    def test_assistant_state_applies_direct_response_state(self):
        state = AssistantState()
        pending = object()

        state.apply_direct_response_state(DirectResponseState(pending, "abre cromi", "chrome", 2, True))
        exported = state.to_direct_response_state()

        self.assertIs(state.pending_command, pending)
        self.assertEqual(state.pending_command_learning_text, "abre cromi")
        self.assertEqual(state.pending_smart_open_choice, "chrome")
        self.assertEqual(state.pending_smart_open_invalid_attempts, 2)
        self.assertTrue(state.direct_response_ready_announced)
        self.assertEqual(exported.pending_smart_open_invalid_attempts, 2)
        self.assertTrue(exported.direct_response_ready_announced)

    def test_assistant_state_applies_mode_macro_and_post_route_states(self):
        state = AssistantState()
        pending = object()

        state.apply_interactive_modes_state(InteractiveModesState(True, True, False, False))
        state.apply_macro_recording_state(MacroRecordingState(True, "rotina", [{"intent": "open_app"}]))
        state.apply_post_route_state(PostRouteState(pending, "", None, 0, False, True, True))

        self.assertTrue(state.dictation_mode)
        self.assertTrue(state.creating_macro)
        self.assertEqual(state.macro_name, "rotina")
        self.assertIs(state.pending_command, pending)
        self.assertTrue(state.conversation_mode)
        self.assertTrue(state.conversation_ready_announced)
        self.assertTrue(state.to_interactive_modes_state().dictation_mode)
        self.assertEqual(state.to_macro_recording_state().macro_name, "rotina")
        self.assertTrue(state.to_post_route_state().conversation_mode)

    def test_assistant_state_converts_and_applies_voice_cycle_state(self):
        state = AssistantState(conversation_mode=True, pending_smart_open_choice="github")

        voice_read = state.to_voice_read_state(voice_mode=True, hotword_mode=True, voice_paused=False)
        state.apply_voice_cycle_result(
            VoiceInputCycleResult(
                user_input="",
                queued_user_input="",
                voice_paused=False,
                should_break=False,
                direct_response_ready_announced=True,
                conversation_ready_announced=True,
                dictation_ready_announced=False,
                repeat_listen_until=123.0,
            )
        )

        self.assertTrue(voice_read.conversation_mode)
        self.assertEqual(voice_read.pending_smart_open_choice, "github")
        self.assertTrue(state.direct_response_ready_announced)
        self.assertEqual(state.repeat_listen_until, 123.0)

    def test_service_slots_start_empty(self):
        runtime = AppRuntime()

        self.assertIsNone(runtime.ui_runtime)
        self.assertIsNone(runtime.improvement_brain)
        self.assertIsNone(runtime.reminder_announcer)
        self.assertIsNone(runtime.response_pipeline)

    def test_runtime_runner_sets_hotword_and_runs_loop_after_startup(self):
        calls = []
        runtime = AppRuntime()
        flags = SimpleNamespace()
        runner = AssistantRuntimeRunner(
            app_runtime=runtime,
            run_startup=lambda **kwargs: calls.append(("startup", kwargs)) or True,
            run_main_loop=lambda **kwargs: calls.append(("loop", kwargs)),
        )

        runner.run(
            AssistantRunConfig(
                flags=flags,
                voice_mode=True,
                hotword_mode=True,
                ui_mode=False,
                voice_paused=True,
            )
        )

        self.assertTrue(runtime.terminal_io.hotword_ui_enabled)
        self.assertEqual(calls[0], ("startup", {"flags": flags, "voice_mode": True, "hotword_mode": True, "ui_mode": False}))
        self.assertEqual(calls[1], ("loop", {"voice_mode": True, "hotword_mode": True, "voice_paused": True}))

    def test_runtime_runner_stops_when_startup_handles_cli(self):
        calls = []
        runtime = AppRuntime()
        runner = AssistantRuntimeRunner(
            app_runtime=runtime,
            run_startup=lambda **kwargs: calls.append(("startup", kwargs)) or False,
            run_main_loop=lambda **kwargs: calls.append(("loop", kwargs)),
        )

        runner.run(
            AssistantRunConfig(
                flags=SimpleNamespace(),
                voice_mode=True,
                hotword_mode=False,
                ui_mode=True,
            )
        )

        self.assertFalse(runtime.terminal_io.hotword_ui_enabled)
        self.assertEqual([call[0] for call in calls], ["startup"])


if __name__ == "__main__":
    unittest.main()
