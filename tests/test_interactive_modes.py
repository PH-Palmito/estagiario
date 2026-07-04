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

    def test_conversation_mode_lets_clear_commands_route_normally(self):
        result = handle_interactive_modes(
            "abrir youtube",
            self._state(conversation_mode=True),
            voice_mode=True,
            hotword_mode=False,
            hotkey_name="F8",
            waiting_for_direct_response=lambda: False,
            set_voice_status=lambda status: None,
            type_text=lambda text: "",
            chat_response=lambda text: self.fail("chat should not run for commands"),
        )

        self.assertFalse(result.handled)
        self.assertTrue(result.state.conversation_mode)

    def test_conversation_mode_lets_operational_questions_route_normally(self):
        result = handle_interactive_modes(
            "agenda de hoje",
            self._state(conversation_mode=True),
            voice_mode=True,
            hotword_mode=False,
            hotkey_name="F8",
            waiting_for_direct_response=lambda: False,
            set_voice_status=lambda status: None,
            type_text=lambda text: "",
            chat_response=lambda text: self.fail("chat should not run for routed questions"),
        )

        self.assertFalse(result.handled)
        self.assertTrue(result.state.conversation_mode)

    def test_conversation_mode_lets_trailing_commands_route_normally(self):
        examples = [
            "me explica redes e abre youtube",
            "me explica redes e toca musica para estudar",
            "me explica redes e pesquise tcp no youtube",
        ]

        for phrase in examples:
            with self.subTest(phrase=phrase):
                result = handle_interactive_modes(
                    phrase,
                    self._state(conversation_mode=True),
                    voice_mode=True,
                    hotword_mode=False,
                    hotkey_name="F8",
                    waiting_for_direct_response=lambda: False,
                    set_voice_status=lambda status: None,
                    type_text=lambda text: "",
                    chat_response=lambda text: self.fail("chat should not run for trailing commands"),
                )

                self.assertFalse(result.handled)
                self.assertTrue(result.state.conversation_mode)

    def test_conversation_mode_keeps_open_chat_inside_mode(self):
        result = handle_interactive_modes(
            "pode me ajudar a aprender inglês?",
            self._state(conversation_mode=True),
            voice_mode=True,
            hotword_mode=False,
            hotkey_name="F8",
            waiting_for_direct_response=lambda: False,
            set_voice_status=lambda status: None,
            type_text=lambda text: "",
            chat_response=lambda text: "",
        )

        self.assertTrue(result.handled)
        self.assertIn("inglês", result.message.lower())
        self.assertIn("misturar português e inglês", result.message.lower())

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
