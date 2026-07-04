import unittest
from pathlib import Path
from unittest.mock import patch

from core.ui_runtime import UIRuntimeService


class FakeBridge:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    def refresh_runtime_state(self, extra=None):
        self.calls.append(("refresh", extra))

    def launch_hud(self):
        self.calls.append(("launch", None))

    def show_hud(self):
        return "show"

    def hide_hud(self):
        return "hide"

    def show_map(self, map_request=None):
        return f"map:{map_request}"

    def show_training(self):
        return "training"

    def maybe_handle_command(self, user_input):
        return f"handled:{user_input}"


class UIRuntimeServiceTests(unittest.TestCase):
    def _service(self, queued_items=None, history=None):
        items = iter(queued_items or [])
        history = history if history is not None else []
        return UIRuntimeService(
            root_dir=Path("."),
            runtime_patch=lambda: {"status": "OK"},
            normalize_text=lambda text: text,
            route=lambda text: {"intent": "respond"},
            process_action=lambda raw: raw,
            training_snapshot=lambda: {},
            dequeue_ui_command_item=lambda: next(items, None),
            append_ui_history=lambda *args, **kwargs: history.append((args, kwargs)),
            history_max_items=7,
            python_executable="python",
        )

    def test_bridge_is_created_lazily_and_reused(self):
        with patch("core.ui_runtime.UIBridge", FakeBridge):
            service = self._service()
            first = service.bridge()
            second = service.bridge()

        self.assertIs(first, second)
        self.assertEqual(first.kwargs["python_executable"], "python")

    def test_delegates_hud_and_panels(self):
        with patch("core.ui_runtime.UIBridge", FakeBridge):
            service = self._service()

            self.assertEqual(service.show_hud(), "show")
            self.assertEqual(service.hide_hud(), "hide")
            self.assertEqual(service.show_map({"label": "casa"}), "map:{'label': 'casa'}")
            self.assertEqual(service.show_training(), "training")
            self.assertEqual(service.maybe_handle_command("abrir painel"), "handled:abrir painel")

    def test_poll_text_command_updates_history_and_runtime(self):
        history = []
        runtime = []
        service = self._service(
            queued_items=[{"id": "cmd-1", "text": " briefing ", "silent": True}],
            history=history,
        )

        result = service.poll_text_command(refresh_runtime_state=runtime.append)

        self.assertEqual(result, "briefing")
        self.assertTrue(service.silent_command_active)
        self.assertEqual(history[0][0], ("user", "briefing"))
        self.assertEqual(history[0][1], {"max_items": 7})
        self.assertEqual(runtime[0]["last_heard"], "briefing")
        self.assertEqual(runtime[0]["command_feedback"]["id"], "cmd-1")
        self.assertEqual(runtime[0]["command_feedback"]["status"], "processing")
        self.assertEqual(service.active_command_id, "cmd-1")

    def test_complete_active_command_publishes_result_and_clears_active_id(self):
        service = self._service(queued_items=[{"id": "cmd-2", "text": "status", "silent": False}])
        runtime = []
        service.poll_text_command(refresh_runtime_state=runtime.append)
        service.refresh_runtime_state = runtime.append

        service.complete_active_command("Tudo certo.", status="success")

        self.assertEqual(runtime[-1]["command_feedback"]["status"], "success")
        self.assertEqual(runtime[-1]["command_feedback"]["message"], "Tudo certo.")
        self.assertEqual(service.active_command_id, "")

    def test_poll_text_command_clears_silent_flag_when_empty(self):
        service = self._service(queued_items=[{"text": "", "silent": True}])
        service.silent_command_active = True

        result = service.poll_text_command(refresh_runtime_state=lambda patch: None)

        self.assertEqual(result, "")
        self.assertFalse(service.silent_command_active)


if __name__ == "__main__":
    unittest.main()
