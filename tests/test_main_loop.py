import unittest
from types import SimpleNamespace

from core.main_loop import MainLoopHandlers, run_main_loop


class MainLoopTests(unittest.TestCase):
    def _handlers(self, calls, cycles=None, **overrides):
        cycle_iter = iter(cycles or [])

        handlers = {
            "maybe_announce_due_reminders": lambda voice_mode: calls.append(("reminders", voice_mode)),
            "read_next_turn_input": lambda **kwargs: calls.append(("read", kwargs)) or next(cycle_iter),
            "handle_voice_cycle_break": lambda cycle: calls.append(("break?", cycle.user_input)) or cycle.should_break,
            "handle_keyboard_interrupt": lambda: calls.append("keyboard"),
            "is_transcription_artifact": lambda text: calls.append(("artifact?", text)) or False,
            "handle_user_turn": lambda *args, **kwargs: calls.append(("turn", args, kwargs)) or True,
        }
        handlers.update(overrides)
        return MainLoopHandlers(**handlers)

    def test_processes_turn_until_break(self):
        calls = []
        cycles = [
            SimpleNamespace(user_input="abrir chrome", queued_user_input="painel", voice_paused=True, should_break=False),
            SimpleNamespace(user_input="sair", queued_user_input="", voice_paused=True, should_break=True),
        ]

        run_main_loop(
            voice_mode=False,
            hotword_mode=False,
            handlers=self._handlers(calls, cycles),
        )

        self.assertEqual(calls[0], ("reminders", False))
        self.assertEqual(calls[1], ("read", {"voice_mode": False, "hotword_mode": False, "voice_paused": False}))
        self.assertEqual(calls[3][0], "artifact?")
        self.assertEqual(calls[4][0], "turn")
        self.assertEqual(calls[4][2]["queued_user_input"], "painel")
        self.assertEqual(calls[6], ("read", {"voice_mode": False, "hotword_mode": False, "voice_paused": True}))

    def test_skips_empty_and_artifact_inputs(self):
        calls = []
        cycles = [
            SimpleNamespace(user_input="", queued_user_input="", voice_paused=False, should_break=False),
            SimpleNamespace(user_input="legendas", queued_user_input="", voice_paused=False, should_break=False),
            SimpleNamespace(user_input="sair", queued_user_input="", voice_paused=False, should_break=True),
        ]

        run_main_loop(
            voice_mode=True,
            hotword_mode=True,
            handlers=self._handlers(
                calls,
                cycles,
                is_transcription_artifact=lambda text: calls.append(("artifact?", text)) or text == "legendas",
            ),
        )

        self.assertNotIn("turn", [call[0] if isinstance(call, tuple) else call for call in calls])
        self.assertIn(("artifact?", "legendas"), calls)

    def test_keyboard_interrupt_uses_handler_and_stops(self):
        calls = []

        run_main_loop(
            voice_mode=True,
            hotword_mode=True,
            handlers=self._handlers(
                calls,
                read_next_turn_input=lambda **kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
            ),
        )

        self.assertIn("keyboard", calls)
        self.assertEqual(calls[-1], "keyboard")


if __name__ == "__main__":
    unittest.main()
