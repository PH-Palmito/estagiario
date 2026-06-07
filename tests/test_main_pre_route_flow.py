import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main


class MainPreRouteFlowTests(unittest.TestCase):
    def _patch_pre_route_defaults(self, calls):
        return (
            patch.object(main, "maybe_learn_correction_for_last_voice", side_effect=lambda text: calls.append("correction") or None),
            patch.object(main, "maybe_handle_shared_command", side_effect=lambda text, **kwargs: calls.append("shared") or None),
            patch.object(main, "maybe_handle_pronunciation_command_core", side_effect=lambda text: calls.append("pronunciation") or None),
            patch.object(main, "maybe_handle_humor_command_core", side_effect=lambda text, prefs, refresh: calls.append("humor") or None),
            patch.object(main, "maybe_handle_input_device_command_core", side_effect=lambda text, refresh: calls.append("input") or None),
            patch.object(main, "maybe_handle_voice_profile_command_core", side_effect=lambda text, prefs, refresh: calls.append("voice_profile") or None),
            patch.object(main, "maybe_handle_work_mode_command_core", side_effect=lambda text, show_ui: calls.append("work") or None),
            patch.object(main, "maybe_handle_ui_command", side_effect=lambda text: calls.append("ui") or None),
            patch.object(main, "maybe_handle_training_command_core", side_effect=lambda text, show_training: calls.append("training") or None),
            patch.object(main, "maybe_handle_study_command_core", side_effect=lambda text, show_hud: calls.append("study") or None),
            patch.object(main, "maybe_handle_axel_brain_runtime_command", side_effect=lambda text, state: calls.append("axel_brain") or None),
            patch.object(main, "maybe_handle_operational_command", side_effect=lambda text: calls.append("operational") or None),
            patch.object(main, "output_response", side_effect=lambda *args, **kwargs: calls.append(("output", args, kwargs))),
            patch.object(main, "refresh_improvement_brain", side_effect=lambda force=False: calls.append(("brain", force))),
            patch.object(main, "maybe_announce_codex_suggestion", side_effect=lambda voice_mode: calls.append(("suggest", voice_mode))),
        )

    def test_pre_route_short_circuits_on_first_response(self):
        calls = []

        with (
            patch.object(main, "maybe_learn_correction_for_last_voice", side_effect=lambda text: calls.append("correction") or "corrigido"),
            patch.object(main, "maybe_handle_pronunciation_command_core", side_effect=lambda text: calls.append("pronunciation") or None),
            patch.object(main, "output_response", side_effect=lambda *args, **kwargs: calls.append(("output", args, kwargs))),
        ):
            handled = main.handle_pre_route_command("texto", voice_mode=True)

        self.assertTrue(handled)
        self.assertEqual(calls, ["correction", ("output", ("corrigido", True), {})])

    def test_pre_route_runs_operational_side_effects(self):
        calls = []
        operational_result = SimpleNamespace(
            refresh_improvement_brain=True,
            response="feito",
            announce_codex_suggestion=True,
        )

        patches = list(self._patch_pre_route_defaults(calls))
        patches[11] = patch.object(
            main,
            "maybe_handle_operational_command",
            side_effect=lambda text: calls.append("operational") or operational_result,
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patches[12], patches[13], patches[14]:
            handled = main.handle_pre_route_command("comando operacional", voice_mode=False)

        self.assertTrue(handled)
        self.assertIn(("brain", True), calls)
        self.assertIn(("output", ("feito", False), {}), calls)
        self.assertIn(("suggest", False), calls)

    def test_pre_route_returns_false_when_nothing_handles(self):
        calls = []

        patches = self._patch_pre_route_defaults(calls)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patches[12], patches[13], patches[14]:
            handled = main.handle_pre_route_command("sem match", voice_mode=False)

        self.assertFalse(handled)
        self.assertEqual(calls[:12], ["correction", "shared", "pronunciation", "humor", "input", "voice_profile", "work", "ui", "training", "study", "axel_brain", "operational"])

    def test_pre_route_handles_axel_brain_runtime_command(self):
        calls = []

        patches = list(self._patch_pre_route_defaults(calls))
        patches[10] = patch.object(
            main,
            "maybe_handle_axel_brain_runtime_command",
            side_effect=lambda text, state: calls.append(("axel_brain", state is main.app_runtime.runtime_state)) or "ultima decisao",
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patches[12], patches[13], patches[14]:
            handled = main.handle_pre_route_command("por que o axel decidiu isso", voice_mode=False)

        self.assertTrue(handled)
        self.assertIn(("axel_brain", True), calls)
        self.assertIn(("output", ("ultima decisao", False), {}), calls)

    def test_pre_route_handles_shared_command_before_router_helpers(self):
        calls = []

        patches = list(self._patch_pre_route_defaults(calls))
        patches[1] = patch.object(
            main,
            "maybe_handle_shared_command",
            side_effect=lambda text, **kwargs: calls.append(
                (
                    "shared",
                    kwargs.get("runtime_state") is main.app_runtime.runtime_state,
                    bool(kwargs.get("allow_state_changes")),
                    bool(kwargs.get("clear_chat")),
                    bool(kwargs.get("reset_ui")),
                    bool(kwargs.get("stop_pending")),
                    bool(kwargs.get("retry_last")),
                    bool(kwargs.get("undo_last")),
                )
            )
            or "status comum",
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patches[12], patches[13], patches[14]:
            handled = main.handle_pre_route_command("/status", voice_mode=False)

        self.assertTrue(handled)
        self.assertIn(("shared", True, True, True, True, True, True, True), calls)
        self.assertIn(("output", ("status comum", False), {}), calls)


if __name__ == "__main__":
    unittest.main()
