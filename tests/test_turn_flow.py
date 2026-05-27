import unittest

from core.turn_flow import TurnFlowHandlers, handle_user_turn


class TurnFlowTests(unittest.TestCase):
    def _handlers(self, calls, **overrides):
        handlers = {
            "record_user_turn_start": lambda text, **kwargs: calls.append(("record", text, kwargs)),
            "handle_pre_route_command": lambda text, **kwargs: calls.append(("pre", text, kwargs)) or False,
            "handle_interactive_command": lambda text, **kwargs: calls.append(("interactive", text, kwargs)) or False,
            "handle_direct_response_command": lambda text, **kwargs: calls.append(("direct", text, kwargs)) or False,
            "normalize_user_command": lambda text, **kwargs: calls.append(("normalize", text, kwargs)) or (text, text),
            "handle_macro_command": lambda text, **kwargs: calls.append(("macro", text, kwargs)) or False,
            "handle_routed_command": lambda **kwargs: calls.append(("route", kwargs)) or True,
        }
        handlers.update(overrides)
        return TurnFlowHandlers(**handlers)

    def test_short_circuits_at_pre_route(self):
        calls = []
        handlers = self._handlers(
            calls,
            handle_pre_route_command=lambda text, **kwargs: calls.append(("pre", text, kwargs)) or True,
        )

        handled = handle_user_turn(
            "abrir painel",
            queued_user_input="",
            voice_mode=False,
            hotword_mode=False,
            handlers=handlers,
        )

        self.assertTrue(handled)
        self.assertEqual([call[0] for call in calls], ["record", "pre"])

    def test_full_flow_uses_normalized_text_after_first_direct_response(self):
        calls = []
        handlers = self._handlers(
            calls,
            normalize_user_command=lambda text, **kwargs: calls.append(("normalize", text, kwargs)) or ("abre cromi", "abrir chrome"),
        )

        handled = handle_user_turn(
            "abre cromi",
            queued_user_input="",
            voice_mode=True,
            hotword_mode=True,
            handlers=handlers,
        )

        self.assertTrue(handled)
        self.assertEqual([call[0] for call in calls], ["record", "pre", "interactive", "direct", "normalize", "macro", "direct", "route"])
        self.assertTrue(calls[3][2]["retry_invalid_smart_open"])
        self.assertFalse(calls[6][2]["retry_invalid_smart_open"])
        self.assertEqual(calls[5][1], "abrir chrome")
        self.assertEqual(calls[-1][1]["user_input"], "abrir chrome")
        self.assertEqual(calls[-1][1]["original_user_input"], "abre cromi")

    def test_returns_false_when_routed_handler_does_not_handle(self):
        calls = []
        handlers = self._handlers(
            calls,
            handle_routed_command=lambda **kwargs: calls.append(("route", kwargs)) or False,
        )

        handled = handle_user_turn(
            "???",
            queued_user_input="",
            voice_mode=False,
            hotword_mode=False,
            handlers=handlers,
        )

        self.assertFalse(handled)


if __name__ == "__main__":
    unittest.main()
