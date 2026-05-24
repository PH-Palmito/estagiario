import unittest

from core.interactive_modes import InteractiveModesState, handle_interactive_modes


class InteractiveModesTests(unittest.TestCase):
    def _state(self, **kwargs):
        defaults = {
            "dictation_mode": False,
            "dictation_ready_announced": False,
            "conversation_mode": False,
            "conversation_ready_announced": False,
        }
        defaults.update(kwargs)
        return InteractiveModesState(**defaults)

    def test_stops_dictation_and_restores_hotkey_status(self):
        statuses = []
        result = handle_interactive_modes(
            "parar ditado",
            self._state(dictation_mode=True),
            voice_mode=True,
            hotword_mode=True,
            hotkey_name="F8",
            waiting_for_direct_response=lambda: False,
            set_voice_status=statuses.append,
            type_text=lambda text: "Texto inserido no campo ativo.",
            chat_response=lambda text: "",
        )

        self.assertTrue(result.handled)
        self.assertFalse(result.state.dictation_mode)
        self.assertEqual(result.message, "Modo ditado encerrado.")
        self.assertEqual(statuses, ["BOTAO F8"])

    def test_dictates_text_without_spoken_response_on_success(self):
        typed = []
        result = handle_interactive_modes(
            "texto livre",
            self._state(dictation_mode=True),
            voice_mode=True,
            hotword_mode=False,
            hotkey_name="F8",
            waiting_for_direct_response=lambda: False,
            set_voice_status=lambda status: None,
            type_text=lambda text: typed.append(text) or "Texto inserido no campo ativo.",
            chat_response=lambda text: "",
        )

        self.assertTrue(result.handled)
        self.assertEqual(result.message, "")
        self.assertEqual(typed, ["texto livre"])

    def test_starts_dictation_and_stops_conversation(self):
        statuses = []
        result = handle_interactive_modes(
            "modo ditado",
            self._state(conversation_mode=True, conversation_ready_announced=True),
            voice_mode=True,
            hotword_mode=True,
            hotkey_name="F8",
            waiting_for_direct_response=lambda: False,
            set_voice_status=statuses.append,
            type_text=lambda text: "",
            chat_response=lambda text: "",
        )

        self.assertTrue(result.state.dictation_mode)
        self.assertFalse(result.state.conversation_mode)
        self.assertEqual(statuses, ["DITADO"])

    def test_conversation_reply_uses_chat_response(self):
        result = handle_interactive_modes(
            "bom dia",
            self._state(conversation_mode=True),
            voice_mode=True,
            hotword_mode=False,
            hotkey_name="F8",
            waiting_for_direct_response=lambda: False,
            set_voice_status=lambda status: None,
            type_text=lambda text: "",
            chat_response=lambda text: "Bom dia, chefe.",
        )

        self.assertTrue(result.handled)
        self.assertEqual(result.message, "Bom dia, chefe.")

    def test_conversation_waits_for_direct_response(self):
        result = handle_interactive_modes(
            "sim",
            self._state(conversation_mode=True),
            voice_mode=True,
            hotword_mode=False,
            hotkey_name="F8",
            waiting_for_direct_response=lambda: True,
            set_voice_status=lambda status: None,
            type_text=lambda text: "",
            chat_response=lambda text: self.fail("chat should not run"),
        )

        self.assertFalse(result.handled)


if __name__ == "__main__":
    unittest.main()
