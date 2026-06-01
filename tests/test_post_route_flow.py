import unittest

from actions import ActionSpec, register_action
from core.command_schema import Command
from core.post_route_flow import PostRouteState, handle_post_route_action


class PostRouteFlowTests(unittest.TestCase):
    def _state(self, **kwargs):
        defaults = {
            "pending_command": None,
            "pending_command_learning_text": "",
            "pending_smart_open_choice": None,
            "pending_smart_open_invalid_attempts": 0,
            "direct_response_ready_announced": False,
            "conversation_mode": False,
            "conversation_ready_announced": False,
        }
        defaults.update(kwargs)
        return PostRouteState(**defaults)

    def _handle(self, raw_action, **overrides):
        callbacks = {
            "user_input": "texto",
            "original_user_input": "texto original",
            "voice_mode": False,
            "state": self._state(),
            "last_command": None,
            "process_action": lambda raw: Command(action=raw["intent"], params=raw.get("target") or {}),
            "execute_command": lambda command: f"executed:{command.action}",
            "execute_routine_steps": lambda steps: "rotina ok",
            "clear_chat_history": lambda: None,
            "confirmation_prompt": lambda command: f"confirmar {command.action}?",
            "smart_open_needs_choice": lambda target: False,
            "show_map_in_ui": lambda target: "mapa ok",
            "update_runtime_state": lambda command, result: None,
            "is_unclear_response": lambda raw: False,
            "maybe_suggest_probable_command": lambda text: None,
        }
        callbacks.update(overrides)
        return handle_post_route_action(raw_action, **callbacks)

    def test_run_routine(self):
        result = self._handle({"intent": "run_routine", "target": ["abrir chrome"]})
        self.assertEqual(result.message, "rotina ok")

    def test_start_and_stop_conversation(self):
        started = []
        start = self._handle({"intent": "start_conversation"}, clear_chat_history=lambda: started.append(True))
        stop = self._handle({"intent": "stop_conversation"}, state=start.state)

        self.assertTrue(start.state.conversation_mode)
        self.assertEqual(started, [True])
        self.assertFalse(stop.state.conversation_mode)

    def test_repeat_last(self):
        command = Command(action="open_app", params={"target": "chrome"})
        result = self._handle({"intent": "repeat_last"}, last_command=command)
        self.assertEqual(result.message, "executed:open_app")

    def test_suggestion_creates_pending_command(self):
        result = self._handle(
            {"intent": "respond", "response": "Pode repetir?"},
            voice_mode=True,
            is_unclear_response=lambda raw: True,
            maybe_suggest_probable_command=lambda text: {
                "question": "Voce quis abrir Chrome?",
                "action": {"intent": "open_app", "target": "chrome"},
            },
        )

        self.assertEqual(result.message, "Voce quis abrir Chrome?")
        self.assertEqual(result.state.pending_command.action, "open_app")
        self.assertEqual(result.state.pending_command_learning_text, "texto original")

    def test_smart_open_choice_prompt(self):
        result = self._handle(
            {"intent": "open", "target": "github"},
            process_action=lambda raw: Command(action="smart_open", params={"target": "github"}),
            smart_open_needs_choice=lambda target: True,
        )

        self.assertEqual(result.state.pending_smart_open_choice, "github")
        self.assertIn("Quer abrir como app ou site?", result.message)

    def test_ui_map_updates_runtime_state(self):
        updates = []
        result = self._handle(
            {"intent": "map"},
            process_action=lambda raw: Command(action="ui_show_map", params={"target": {"q": "Salvador"}}),
            update_runtime_state=lambda command, message: updates.append((command.action, message)),
        )

        self.assertEqual(result.message, "mapa ok")
        self.assertEqual(updates, [("ui_show_map", "mapa ok")])

    def test_confirmation_prompt(self):
        result = self._handle(
            {"intent": "delete"},
            process_action=lambda raw: Command(action="file_delete", params={"path": "x"}, requires_confirmation=True),
        )

        self.assertEqual(result.state.pending_command.action, "file_delete")
        self.assertEqual(result.message, "confirmar file_delete?")

    def test_registered_sensitive_command_is_pending_even_when_command_flag_is_false(self):
        register_action(
            ActionSpec(
                name="unit.post_route_sensitive",
                description="Action de teste.",
                handler=lambda _args: "ok",
                category="system",
                read_only=False,
                requires_confirmation=True,
            )
        )

        result = self._handle(
            {"intent": "unit"},
            process_action=lambda raw: Command(action="unit.post_route_sensitive", params={}, requires_confirmation=False),
        )

        self.assertEqual(result.state.pending_command.action, "unit.post_route_sensitive")
        self.assertEqual(result.message, "confirmar unit.post_route_sensitive?")

    def test_axel_brain_plan_can_require_confirmation(self):
        result = self._handle(
            {"intent": "unit_unregistered"},
            process_action=lambda raw: Command(action="unit_unregistered", params={}, requires_confirmation=False),
            decision_plan={"needs_confirmation": True, "risk_level": "high"},
        )

        self.assertEqual(result.state.pending_command.action, "unit_unregistered")
        self.assertTrue(result.state.pending_command.requires_confirmation)
        self.assertEqual(result.message, "confirmar unit_unregistered?")


if __name__ == "__main__":
    unittest.main()
