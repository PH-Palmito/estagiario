import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main
from core.interactive_modes import InteractiveModesState
from core.macro_recording import MacroRecordingState
from core.post_route_flow import PostRouteState
from core.voice_loop import VoiceInputCycleResult


class MainTurnFlowTests(unittest.TestCase):
    def test_record_user_turn_start_logs_origin_and_saves_memory_when_changed(self):
        calls = []

        with (
            patch.object(main, "terminal_print_user_command", side_effect=lambda source, text: calls.append(("print", source, text))),
            patch.object(main, "log_execution_event", side_effect=lambda event, **payload: calls.append(("log", event, payload))),
            patch.object(main, "current_ui_mode_label", return_value="comando"),
            patch.object(main, "maybe_remember_from_user_text", side_effect=lambda text, source: calls.append(("remember", text, source)) or True),
            patch.object(main, "save_operational_context", side_effect=lambda: calls.append("save")),
        ):
            main.record_user_turn_start("abrir painel", queued_user_input="abrir painel", voice_mode=False)

        self.assertEqual(calls[0], ("print", "painel", "abrir painel"))
        self.assertEqual(calls[1][0:2], ("log", "user_input"))
        self.assertEqual(calls[1][2]["mode"], "comando")
        self.assertEqual(calls[2], ("remember", "abrir painel", "conversation"))
        self.assertEqual(calls[3], "save")

    def test_record_user_turn_start_ignores_memory_errors(self):
        calls = []

        with (
            patch.object(main, "terminal_print_user_command", side_effect=lambda source, text: calls.append(("print", source, text))),
            patch.object(main, "log_execution_event", side_effect=lambda event, **payload: calls.append(("log", event))),
            patch.object(main, "current_ui_mode_label", return_value="voz"),
            patch.object(main, "maybe_remember_from_user_text", side_effect=RuntimeError("falha")),
            patch.object(main, "save_operational_context", side_effect=lambda: calls.append("save")),
        ):
            main.record_user_turn_start("oi", queued_user_input="", voice_mode=False)

        self.assertEqual(calls, [("print", "texto", "oi"), ("log", "user_input")])

    def test_record_user_turn_start_defers_memory_in_voice_mode(self):
        calls = []

        with (
            patch.object(main, "terminal_print_user_command"),
            patch.object(main, "log_execution_event"),
            patch.object(main, "current_ui_mode_label", return_value="voz"),
            patch.object(main, "run_noncritical_task", side_effect=lambda name, task, defer=False: calls.append((name, defer))),
        ):
            main.record_user_turn_start("abrir painel", queued_user_input="", voice_mode=True)

        self.assertEqual(calls, [("conversation_memory", True)])

    def test_auto_curates_long_memory_after_turn_threshold(self):
        previous_turns = main.app_runtime.runtime_state.turns_since_long_memory_curated
        previous_at = main.app_runtime.runtime_state.last_long_memory_curated_at
        calls = []
        try:
            main.app_runtime.runtime_state.turns_since_long_memory_curated = main.LONG_MEMORY_AUTOCURATE_TURNS - 1
            main.app_runtime.runtime_state.last_long_memory_curated_at = 0.0
            with (
                patch.object(main, "maybe_remember_from_user_text", return_value=False),
                patch.object(main, "curate_recent_ui_history", side_effect=lambda limit=30: calls.append(("curate", limit)) or 2),
                patch.object(main, "save_operational_context", side_effect=lambda: calls.append("save")),
                patch.object(main, "log_execution_event", side_effect=lambda event, **payload: calls.append(("log", event, payload))),
                patch.object(main.time, "time", return_value=1234.0),
            ):
                main.remember_user_context_from_turn("vamos fazer uma memoria duravel")

            self.assertEqual(main.app_runtime.runtime_state.turns_since_long_memory_curated, 0)
            self.assertEqual(main.app_runtime.runtime_state.last_long_memory_curated_at, 1234.0)
            self.assertIn(("curate", 30), calls)
            self.assertIn(("log", "long_memory_autocurated", {"added": 2}), calls)
            self.assertIn("save", calls)
        finally:
            main.app_runtime.runtime_state.turns_since_long_memory_curated = previous_turns
            main.app_runtime.runtime_state.last_long_memory_curated_at = previous_at

    def test_handle_interactive_command_outputs_message_with_result_voice_mode(self):
        calls = []
        result = SimpleNamespace(
            handled=True,
            message="Modo conversa ativado.",
            voice_mode=False,
            state=InteractiveModesState(False, False, True, False),
        )

        with (
            patch.object(main, "handle_interactive_modes", return_value=result) as handle,
            patch.object(main.assistant_state, "apply_interactive_modes_state", side_effect=lambda state: calls.append(("apply", state))),
            patch.object(main, "output_response", side_effect=lambda message, voice_mode: calls.append(("output", message, voice_mode))),
        ):
            handled = main.handle_interactive_command("conversar", voice_mode=True, hotword_mode=True)

        self.assertTrue(handled)
        self.assertTrue(handle.call_args.kwargs["voice_mode"])
        self.assertEqual(calls[0][0], "apply")
        self.assertEqual(calls[1], ("output", "Modo conversa ativado.", False))

    def test_handle_interactive_command_returns_false_without_output_when_unhandled(self):
        calls = []
        result = SimpleNamespace(
            handled=False,
            message="",
            voice_mode=None,
            state=InteractiveModesState(False, False, False, False),
        )

        with (
            patch.object(main, "handle_interactive_modes", return_value=result),
            patch.object(main.assistant_state, "apply_interactive_modes_state", side_effect=lambda state: calls.append(("apply", state))),
            patch.object(main, "output_response", side_effect=lambda *_args, **_kwargs: calls.append("output")),
        ):
            handled = main.handle_interactive_command("abrir chrome", voice_mode=False, hotword_mode=False)

        self.assertFalse(handled)
        self.assertEqual(calls[0][0], "apply")
        self.assertNotIn("output", calls)

    def test_normalize_user_command_logs_change_and_refreshes_ui(self):
        calls = []

        with (
            patch.object(main, "maybe_normalize_voice_command_core", side_effect=lambda text, voice_mode, apply, route: "abrir chrome"),
            patch.object(main, "log_execution_event", side_effect=lambda event, **payload: calls.append(("log", event, payload))),
            patch.object(main, "refresh_ui_runtime_state", side_effect=lambda patch=None: calls.append(("refresh", patch))),
        ):
            original, normalized = main.normalize_user_command("abre cromi", voice_mode=True)

        self.assertEqual((original, normalized), ("abre cromi", "abrir chrome"))
        self.assertEqual(calls[0][0:2], ("log", "voice_input_normalized"))
        self.assertEqual(calls[0][2]["normalized"], "abrir chrome")
        self.assertEqual(calls[1], ("refresh", {"last_command": "abrir chrome"}))

    def test_normalize_user_command_remembers_last_voice_when_unchanged(self):
        previous = main.assistant_state.last_voice_text

        try:
            with (
                patch.object(main, "maybe_normalize_voice_command_core", side_effect=lambda text, voice_mode, apply, route: text),
                patch.object(main, "log_execution_event", side_effect=lambda *_args, **_kwargs: self.fail("should not log normalization")),
                patch.object(main, "refresh_ui_runtime_state"),
            ):
                original, normalized = main.normalize_user_command("abrir painel", voice_mode=True)

            self.assertEqual((original, normalized), ("abrir painel", "abrir painel"))
            self.assertEqual(main.assistant_state.last_voice_text, "abrir painel")
        finally:
            main.assistant_state.last_voice_text = previous

    def test_music_action_opens_media_panel(self):
        calls = []

        with patch.object(main, "refresh_ui_runtime_state", side_effect=lambda patch=None: calls.append(patch)):
            main.maybe_open_media_panel_for_action({"intent": "browser_music_session", "target": {"service": "spotify"}})

        self.assertEqual(calls, [{"active_panel": "midia", "open_panels": ["midia"]}])

    def test_handle_macro_command_outputs_when_handled(self):
        calls = []
        route_calls = []
        result = SimpleNamespace(
            handled=True,
            message="Passo adicionado.",
            state=MacroRecordingState(True, "manha", [{"intent": "daily_briefing"}]),
        )

        with (
            patch.object(main, "handle_macro_recording", return_value=result) as handle,
            patch.object(
                main,
                "route_user_input",
                side_effect=lambda text, source="turn": route_calls.append((text, source)) or {"intent": "daily_briefing"},
            ),
            patch.object(main.assistant_state, "apply_macro_recording_state", side_effect=lambda state: calls.append(("apply", state))),
            patch.object(main, "output_response", side_effect=lambda message, voice_mode: calls.append(("output", message, voice_mode))),
        ):
            handled = main.handle_macro_command("briefing", voice_mode=True)
            routed = handle.call_args.kwargs["route"]("briefing")

        self.assertTrue(handled)
        self.assertEqual(handle.call_args.kwargs["add_macro"], main.add_macro)
        self.assertEqual(routed, {"intent": "daily_briefing"})
        self.assertEqual(route_calls, [("briefing", "macro_recording")])
        self.assertEqual(calls[0][0], "apply")
        self.assertEqual(calls[1], ("output", "Passo adicionado.", True))

    def test_handle_macro_command_returns_false_when_unhandled(self):
        calls = []
        result = SimpleNamespace(
            handled=False,
            message="",
            state=MacroRecordingState(False, None, []),
        )

        with (
            patch.object(main, "handle_macro_recording", return_value=result),
            patch.object(main.assistant_state, "apply_macro_recording_state", side_effect=lambda state: calls.append(("apply", state))),
            patch.object(main, "output_response", side_effect=lambda *_args, **_kwargs: calls.append("output")),
        ):
            handled = main.handle_macro_command("abrir chrome", voice_mode=False)

        self.assertFalse(handled)
        self.assertEqual(calls[0][0], "apply")
        self.assertNotIn("output", calls)

    def test_handle_direct_response_command_outputs_when_handled(self):
        calls = []
        result = SimpleNamespace(handled=True, message="Executado.")

        with (
            patch.object(main, "run_direct_response_flow", return_value=result) as run_flow,
            patch.object(main, "output_response", side_effect=lambda message, voice_mode: calls.append(("output", message, voice_mode))),
        ):
            handled = main.handle_direct_response_command(
                "sim",
                voice_mode=True,
                retry_invalid_smart_open=False,
            )

        self.assertTrue(handled)
        self.assertFalse(run_flow.call_args.kwargs["retry_invalid_smart_open"])
        self.assertEqual(calls, [("output", "Executado.", True)])

    def test_handle_direct_response_command_returns_false_when_unhandled(self):
        calls = []
        result = SimpleNamespace(handled=False, message="")

        with (
            patch.object(main, "run_direct_response_flow", return_value=result),
            patch.object(main, "output_response", side_effect=lambda *_args, **_kwargs: calls.append("output")),
        ):
            handled = main.handle_direct_response_command(
                "abrir chrome",
                voice_mode=False,
                retry_invalid_smart_open=True,
            )

        self.assertFalse(handled)
        self.assertEqual(calls, [])

    def test_handle_routed_command_short_circuits_multi_step(self):
        calls = []

        with (
            patch.object(main, "looks_like_multi_step_request", return_value=True),
            patch.object(main, "handle_multi_step_request", side_effect=lambda text: calls.append(("multi", text)) or "feito em etapas"),
            patch.object(main, "output_response", side_effect=lambda message, voice_mode: calls.append(("output", message, voice_mode))),
            patch.object(main, "route_user_input", side_effect=lambda text, **kwargs: self.fail("route_user_input should not run")),
        ):
            handled = main.handle_routed_command("abra chrome e depois spotify", original_user_input="original", voice_mode=True)

        self.assertTrue(handled)
        self.assertEqual(calls, [("multi", "abra chrome e depois spotify"), ("output", "feito em etapas", True)])

    def test_handle_routed_command_routes_and_applies_post_route_state(self):
        calls = []
        post_state = PostRouteState(None, "", None, 0, False, True, False)
        post_result = SimpleNamespace(handled=True, message="executado", state=post_state)

        with (
            patch.object(main, "looks_like_multi_step_request", return_value=False),
            patch.object(
                main,
                "route_user_input",
                side_effect=lambda text, source="turn": calls.append(("route", text, source)) or {"intent": "open_app", "target": "chrome"},
            ),
            patch.object(main, "log_execution_event", side_effect=lambda event, **payload: calls.append(("log", event, payload))),
            patch.object(main, "handle_post_route_action", return_value=post_result) as post_route,
            patch.object(main.assistant_state, "apply_post_route_state", side_effect=lambda state: calls.append(("apply", state))),
            patch.object(main, "output_response", side_effect=lambda message, voice_mode: calls.append(("output", message, voice_mode))),
        ):
            handled = main.handle_routed_command("abrir chrome", original_user_input="abrir chrome", voice_mode=False)

        self.assertTrue(handled)
        self.assertEqual(calls[0], ("route", "abrir chrome", "turn"))
        self.assertEqual(post_route.call_args.kwargs["original_user_input"], "abrir chrome")
        self.assertIn("decision_plan", post_route.call_args.kwargs)
        self.assertEqual(calls[-2], ("apply", post_state))
        self.assertEqual(calls[-1], ("output", "executado", False))

    def test_route_user_input_logs_route_trace_metadata(self):
        calls = []

        with (
            patch.object(
                main,
                "route_trace",
                return_value=SimpleNamespace(
                    match=None,
                    checked_detectors=20,
                    checked_groups=("fast_path", "conversation"),
                ),
            ),
            patch.object(main, "log_execution_event", side_effect=lambda event, **payload: calls.append((event, payload))),
            patch.object(main, "append_ui_notification", side_effect=lambda *args, **kwargs: calls.append(("notify", args, kwargs))),
            patch.object(main, "run_noncritical_task", side_effect=lambda name, task, defer=False: calls.append(("defer", name, defer))),
        ):
            raw_action = main.route_user_input("???", source="unit")

        self.assertEqual(raw_action, {"intent": "respond", "target": None, "response": "Nao entendi."})
        self.assertEqual(calls[0][0], "route_result")
        self.assertEqual(calls[0][1]["source"], "unit")
        self.assertEqual(calls[0][1]["intent"], "respond")
        self.assertEqual(calls[0][1]["group"], "")
        self.assertEqual(calls[0][1]["detector"], "")
        self.assertEqual(calls[0][1]["intent_level"], "conversa")
        self.assertEqual(calls[0][1]["complexity"], "simple_command")
        self.assertTrue(calls[0][1]["should_use_llm"])
        self.assertEqual(calls[0][1]["checked_detectors"], 20)
        self.assertIn("decision_plan", calls[0][1])
        self.assertIn("specialist_brief", calls[0][1])
        self.assertEqual(main.app_runtime.runtime_state.axel_brain_plan["intent"], "respond")
        self.assertEqual(main.app_runtime.runtime_state.axel_brain_contract["version"], "2.0")
        self.assertEqual(main.app_runtime.runtime_state.axel_brain_contract["channel"], "local")
        self.assertEqual(main.app_runtime.runtime_state.axel_brain_contract["remote_policy"]["decision"], "local_flow")
        self.assertEqual(main.app_runtime.runtime_state.axel_brain_history[-1]["intent"], "respond")
        self.assertEqual(main.app_runtime.runtime_state.axel_brain_history[-1]["safety_profile"], "local_normal")
        self.assertEqual(main.app_runtime.runtime_state.last_route_trace["intent"], "respond")
        self.assertEqual(main.app_runtime.runtime_state.last_route_trace["checked_detectors"], 20)
        self.assertEqual(
            main.app_runtime.runtime_state.axel_brain_brief["agent"],
            main.app_runtime.runtime_state.axel_brain_plan["agent"],
        )
        self.assertIn("risco", main.app_runtime.runtime_state.axel_brain_plan["reason"])
        self.assertEqual(calls[1][0], "latency_stage")
        self.assertEqual(calls[1][1]["stage"], "routing")
        self.assertEqual(calls[1][1]["source"], "unit")
        self.assertEqual(calls[1][1]["intent"], "respond")
        self.assertEqual(calls[1][1]["intent_level"], "conversa")
        self.assertEqual(calls[1][1]["complexity"], "simple_command")

    def test_ui_runtime_patch_exposes_axel_brain_decision(self):
        previous_plan = main.app_runtime.runtime_state.axel_brain_plan
        previous_brief = main.app_runtime.runtime_state.axel_brain_brief
        previous_contract = main.app_runtime.runtime_state.axel_brain_contract
        previous_history = main.app_runtime.runtime_state.axel_brain_history
        previous_route = main.app_runtime.runtime_state.last_route_trace
        try:
            main.app_runtime.runtime_state.axel_brain_plan = {
                "agent": "dev_agent",
                "toolset": "programacao",
                "risk_level": "read",
                "confidence": 0.86,
                "reason": "toolset por gatilho; agente dev_agent; risco read",
            }
            main.app_runtime.runtime_state.axel_brain_brief = {
                "agent": "dev_agent",
                "toolset": "programacao",
                "mission": "Ajudar com codigo.",
            }
            main.app_runtime.runtime_state.axel_brain_contract = {
                "version": "2.0",
                "channel": "local",
            }
            main.app_runtime.runtime_state.axel_brain_history = [
                {"intent": "respond", "agent": "conversation_agent", "channel": "remote", "safety_profile": "remote_blocked"}
            ]
            main.app_runtime.runtime_state.last_route_trace = {
                "group": "conversation",
                "detector": "detect_ollama_chat",
            }
            with (
                patch.object(main, "get_active_input_device_info", return_value={"name": "Mic"}),
                patch("memory.ui_state.load_ui_state", return_value={}),
                patch("memory.skill_learning.pending_skill_suggestions", return_value=[{"title": "Criar skill"}]),
            ):
                payload = main._ui_runtime_patch()

            self.assertEqual(payload["axel_brain_plan"]["agent"], "dev_agent")
            self.assertEqual(payload["axel_brain_plan"]["toolset"], "programacao")
            self.assertEqual(payload["axel_brain_plan"]["reason"], "toolset por gatilho; agente dev_agent; risco read")
            self.assertEqual(payload["axel_brain_brief"]["mission"], "Ajudar com codigo.")
            self.assertEqual(payload["axel_brain_contract"]["version"], "2.0")
            self.assertEqual(payload["axel_brain_history"][0]["intent"], "respond")
            self.assertEqual(payload["axel_brain_history_summary"]["total"], 1)
            self.assertEqual(payload["axel_brain_history_summary"]["remote_blocked"], 1)
            self.assertIn("recommendations", payload["axel_brain_history_summary"])
            self.assertEqual(payload["last_route_trace"]["detector"], "detect_ollama_chat")
            self.assertEqual(payload["skill_suggestions"][0]["title"], "Criar skill")
        finally:
            main.app_runtime.runtime_state.axel_brain_plan = previous_plan
            main.app_runtime.runtime_state.axel_brain_brief = previous_brief
            main.app_runtime.runtime_state.axel_brain_contract = previous_contract
            main.app_runtime.runtime_state.axel_brain_history = previous_history
            main.app_runtime.runtime_state.last_route_trace = previous_route

    def test_route_user_input_defers_routine_learning_for_turn_source(self):
        calls = []

        with (
            patch.object(
                main,
                "route_trace",
                return_value=SimpleNamespace(
                    match=SimpleNamespace(
                        result={"intent": "open_app", "target": "chrome"},
                        intent_level="comando_direto",
                        group_name="apps",
                        detector_name="detect_open_app",
                    ),
                    checked_detectors=3,
                    checked_groups=("fast_path", "apps"),
                ),
            ),
            patch.object(main, "log_execution_event"),
            patch.object(main, "run_noncritical_task", side_effect=lambda name, task, defer=False: calls.append((name, defer))),
        ):
            raw_action = main.route_user_input("abrir chrome", source="turn")

        self.assertEqual(raw_action["intent"], "open_app")
        self.assertEqual(calls, [("routine_learning", True)])

    def test_read_user_input_logs_stt_latency_in_voice_mode(self):
        calls = []

        with (
            patch.object(main.app_runtime.terminal_io, "read_user_input", return_value="abrir painel") as read,
            patch.object(main, "log_execution_event", side_effect=lambda event, **payload: calls.append((event, payload))),
        ):
            result = main.read_user_input(True, announce_ready=False, fallback_to_text=False, listener=lambda: None)

        self.assertEqual(result, "abrir painel")
        read.assert_called_once()
        self.assertEqual(calls[-1][0], "latency_stage")
        self.assertEqual(calls[-1][1]["stage"], "stt")
        self.assertFalse(calls[-1][1]["announce_ready"])
        self.assertFalse(calls[-1][1]["fallback_to_text"])
        self.assertTrue(calls[-1][1]["listener"])

    def test_ui_runtime_routes_with_ui_bridge_source(self):
        previous = main.app_runtime.ui_runtime
        calls = []
        try:
            main.app_runtime.ui_runtime = None
            with patch.object(
                main,
                "route_user_input",
                side_effect=lambda text, source="turn": calls.append((text, source)) or {"intent": "respond", "target": None},
            ):
                ui_runtime = main.get_ui_runtime()
                result = ui_runtime.route("mostre mapa")

            self.assertEqual(result, {"intent": "respond", "target": None})
            self.assertEqual(calls, [("mostre mapa", "ui_bridge")])
        finally:
            main.app_runtime.ui_runtime = previous

    def test_handle_user_turn_short_circuits_at_pre_route(self):
        calls = []

        with (
            patch.object(main, "record_user_turn_start", side_effect=lambda *args, **kwargs: calls.append("record")),
            patch.object(main, "handle_pre_route_command", side_effect=lambda *args, **kwargs: calls.append("pre") or True),
            patch.object(main, "handle_interactive_command", side_effect=lambda *args, **kwargs: calls.append("interactive") or False),
        ):
            handled = main.handle_user_turn(
                "abrir painel",
                queued_user_input="",
                voice_mode=False,
                hotword_mode=False,
            )

        self.assertTrue(handled)
        self.assertEqual(calls, ["record", "pre"])

    def test_handle_user_turn_runs_full_route_after_normalization(self):
        calls = []

        with (
            patch.object(main, "record_user_turn_start", side_effect=lambda *args, **kwargs: calls.append("record")),
            patch.object(main, "handle_pre_route_command", side_effect=lambda *args, **kwargs: calls.append("pre") or False),
            patch.object(main, "handle_interactive_command", side_effect=lambda *args, **kwargs: calls.append("interactive") or False),
            patch.object(main, "handle_direct_response_command", side_effect=[False, False]) as direct,
            patch.object(main, "normalize_user_command", side_effect=lambda text, voice_mode: calls.append(("normalize", text, voice_mode)) or ("abre cromi", "abrir chrome")),
            patch.object(main, "handle_macro_command", side_effect=lambda *args, **kwargs: calls.append("macro") or False),
            patch.object(main, "handle_routed_command", side_effect=lambda **kwargs: calls.append(("route", kwargs)) or True),
        ):
            handled = main.handle_user_turn(
                "abre cromi",
                queued_user_input="",
                voice_mode=True,
                hotword_mode=True,
            )

        self.assertTrue(handled)
        self.assertEqual(direct.call_args_list[0].kwargs["retry_invalid_smart_open"], True)
        self.assertEqual(direct.call_args_list[1].kwargs["retry_invalid_smart_open"], False)
        self.assertEqual(calls[:4], ["record", "pre", "interactive", ("normalize", "abre cromi", True)])
        self.assertEqual(calls[-1][0], "route")
        self.assertEqual(calls[-1][1]["user_input"], "abrir chrome")
        self.assertEqual(calls[-1][1]["original_user_input"], "abre cromi")

    def test_read_next_turn_input_applies_cycle_state_and_hotword_flag(self):
        calls = []
        result = VoiceInputCycleResult(
            user_input="abrir chrome",
            queued_user_input="",
            voice_paused=True,
            should_break=False,
            direct_response_ready_announced=True,
            conversation_ready_announced=False,
            dictation_ready_announced=False,
            hotword_ui_enabled=False,
        )
        previous_hotword = main.app_runtime.terminal_io.hotword_ui_enabled

        try:
            main.app_runtime.terminal_io.hotword_ui_enabled = True
            with (
                patch.object(main.assistant_state, "to_voice_read_state", side_effect=lambda **kwargs: calls.append(("state", kwargs)) or "state"),
                patch.object(main, "run_voice_input_cycle", return_value=result) as run_cycle,
                patch.object(main.assistant_state, "apply_voice_cycle_result", side_effect=lambda value: calls.append(("apply", value))),
            ):
                returned = main.read_next_turn_input(voice_mode=True, hotword_mode=True, voice_paused=False)

            self.assertIs(returned, result)
            self.assertEqual(calls[0], ("state", {"voice_mode": True, "hotword_mode": True, "voice_paused": False}))
            self.assertEqual(calls[1], ("apply", result))
            self.assertEqual(run_cycle.call_args.kwargs["state"], "state")
            self.assertFalse(main.app_runtime.terminal_io.hotword_ui_enabled)
        finally:
            main.app_runtime.terminal_io.hotword_ui_enabled = previous_hotword

    def test_handle_voice_cycle_break_outputs_message(self):
        calls = []
        result = VoiceInputCycleResult(
            user_input="sair",
            queued_user_input="",
            voice_paused=False,
            should_break=True,
            break_message="Encerrando.",
            break_voice_mode=False,
        )

        with (
            patch.object(main, "clear_status_line", side_effect=lambda: calls.append("clear")),
            patch.object(main, "output_response", side_effect=lambda message, voice_mode: calls.append(("output", message, voice_mode))),
        ):
            should_break = main.handle_voice_cycle_break(result)

        self.assertTrue(should_break)
        self.assertEqual(calls, ["clear", ("output", "Encerrando.", False)])

    def test_run_main_loop_processes_turn_until_break(self):
        calls = []
        first = VoiceInputCycleResult(
            user_input="abrir chrome",
            queued_user_input="painel",
            voice_paused=True,
            should_break=False,
        )
        second = VoiceInputCycleResult(
            user_input="sair",
            queued_user_input="",
            voice_paused=True,
            should_break=True,
        )

        with (
            patch.object(main, "maybe_announce_due_reminders", side_effect=lambda voice_mode: calls.append(("reminders", voice_mode))),
            patch.object(main, "read_next_turn_input", side_effect=[first, second]),
            patch.object(main, "handle_voice_cycle_break", side_effect=lambda result: result.should_break),
            patch.object(main, "is_transcription_artifact", return_value=False),
            patch.object(main, "handle_user_turn", side_effect=lambda *args, **kwargs: calls.append(("turn", args, kwargs))),
        ):
            main.run_main_loop(voice_mode=False, hotword_mode=False)

        self.assertEqual(calls[0], ("reminders", False))
        self.assertEqual(calls[1][0], "turn")
        self.assertEqual(calls[1][2]["queued_user_input"], "painel")
        self.assertEqual(calls[2], ("reminders", False))

    def test_run_main_loop_skips_empty_and_transcription_artifact(self):
        calls = []
        empty = VoiceInputCycleResult(user_input="", queued_user_input="", voice_paused=False, should_break=False)
        artifact = VoiceInputCycleResult(user_input="legendas automáticas", queued_user_input="", voice_paused=False, should_break=False)
        stop = VoiceInputCycleResult(user_input="sair", queued_user_input="", voice_paused=False, should_break=True)

        with (
            patch.object(main, "maybe_announce_due_reminders", side_effect=lambda voice_mode: None),
            patch.object(main, "read_next_turn_input", side_effect=[empty, artifact, stop]),
            patch.object(main, "handle_voice_cycle_break", side_effect=lambda result: result.should_break),
            patch.object(main, "is_transcription_artifact", side_effect=lambda text: calls.append(("artifact", text)) or text.startswith("legendas")),
            patch.object(main, "handle_user_turn", side_effect=lambda *args, **kwargs: calls.append("turn")),
        ):
            main.run_main_loop(voice_mode=True, hotword_mode=True)

        self.assertEqual(calls, [("artifact", "legendas automáticas")])

    def test_run_main_loop_handles_keyboard_interrupt(self):
        calls = []
        previous_hotword = main.app_runtime.terminal_io.hotword_ui_enabled

        try:
            main.app_runtime.terminal_io.hotword_ui_enabled = True
            with (
                patch.object(main, "maybe_announce_due_reminders", side_effect=lambda voice_mode: None),
                patch.object(main, "read_next_turn_input", side_effect=KeyboardInterrupt),
                patch.object(main, "clear_status_line", side_effect=lambda: calls.append("clear")),
                patch.object(main, "output_response", side_effect=lambda message, voice_mode: calls.append(("output", message, voice_mode))),
            ):
                main.run_main_loop(voice_mode=True, hotword_mode=True)

            self.assertFalse(main.app_runtime.terminal_io.hotword_ui_enabled)
            self.assertEqual(calls, ["clear", ("output", "Encerrando.", False)])
        finally:
            main.app_runtime.terminal_io.hotword_ui_enabled = previous_hotword


if __name__ == "__main__":
    unittest.main()
