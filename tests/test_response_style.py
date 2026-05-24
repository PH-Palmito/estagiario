import unittest

from core.response_style import next_style_variant, should_style_response, style_response

VARIANTS = {
    "unclear_command": ("Nao entendi direito.",),
    "repeat_prompt": ("Pode repetir, por favor?",),
    "ready_prompt_addressed": ("Pode falar, {address_user}.",),
    "ready_prompt": ("Pode falar.",),
    "action_prefix": ("{message}, {address_user}.",),
}


def first_phrase(_key, options):
    return options[0]


class ResponseStyleTests(unittest.TestCase):
    def test_should_style_response_filters_structured_and_long_messages(self):
        self.assertFalse(should_style_response(""))
        self.assertFalse(should_style_response("linha 1\nlinha 2"))
        self.assertFalse(should_style_response("Arquivo salvo."))
        self.assertFalse(should_style_response("x" * 121))
        self.assertTrue(should_style_response("Abrindo chrome."))

    def test_next_style_variant_rotates_with_state(self):
        state = {}

        self.assertEqual(next_style_variant(("a", "b"), state), "a")
        self.assertEqual(next_style_variant(("a", "b"), state), "b")
        self.assertEqual(state["style_variation_index"], 2)

    def test_style_disabled_when_no_assistant_style(self):
        result = style_response(
            "Abrindo chrome.",
            preferences={},
            variants=VARIANTS,
            next_phrase=first_phrase,
        )

        self.assertEqual(result, "Abrindo chrome.")

    def test_assistente_replacement(self):
        result = style_response(
            "Abrindo chrome.",
            preferences={"assistant_style": "assistente"},
            variants=VARIANTS,
            next_phrase=first_phrase,
        )

        self.assertEqual(result, "Perfeitamente. Abrindo Chrome.")

    def test_jarvis_ready_prompt_uses_addressed_variant(self):
        result = style_response(
            "Pode falar.",
            preferences={"assistant_style": "jarvis", "assistant_address_user": "chefe"},
            variants=VARIANTS,
            next_phrase=first_phrase,
        )

        self.assertEqual(result, "Pode falar, chefe.")

    def test_humor_jarvis_enables_jarvis_style(self):
        result = style_response(
            "Ok, nao abri.",
            preferences={"assistant_humor_enabled": True, "assistant_humor_style": "jarvis"},
            variants=VARIANTS,
            next_phrase=first_phrase,
        )

        self.assertEqual(result, "Certo. Não abri.")

    def test_brief_confirmations_can_disable_styling(self):
        result = style_response(
            "Abrindo chrome.",
            preferences={"assistant_style": "jarvis", "assistant_brief_confirmations": False},
            variants=VARIANTS,
            next_phrase=first_phrase,
        )

        self.assertEqual(result, "Abrindo chrome.")


if __name__ == "__main__":
    unittest.main()
