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


def rotating_phrase():
    indexes = {}

    def next_phrase(key, options):
        index = indexes.get(key, 0)
        indexes[key] = index + 1
        return options[index % len(options)]

    return next_phrase


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

    def test_contextual_app_response_rotates_without_verbose_text(self):
        next_phrase = rotating_phrase()

        first = style_response(
            "Abrindo chrome.",
            preferences={"assistant_style": "jarvis"},
            variants=VARIANTS,
            next_phrase=next_phrase,
        )
        second = style_response(
            "Abrindo chrome.",
            preferences={"assistant_style": "jarvis"},
            variants=VARIANTS,
            next_phrase=next_phrase,
        )

        self.assertEqual(first, "Certamente. Abrindo Chrome.")
        self.assertEqual(second, "Abrindo Chrome.")

    def test_contextual_status_response_rotates(self):
        next_phrase = rotating_phrase()

        first = style_response(
            "Escuta pausada.",
            preferences={"assistant_style": "assistente"},
            variants=VARIANTS,
            next_phrase=next_phrase,
        )
        second = style_response(
            "Escuta pausada.",
            preferences={"assistant_style": "assistente"},
            variants=VARIANTS,
            next_phrase=next_phrase,
        )

        self.assertEqual(first, "Escuta em pausa.")
        self.assertEqual(second, "Modo escuta pausado.")

    def test_brief_confirmations_can_disable_styling(self):
        result = style_response(
            "Abrindo chrome.",
            preferences={"assistant_style": "jarvis", "assistant_brief_confirmations": False},
            variants=VARIANTS,
            next_phrase=first_phrase,
        )

        self.assertEqual(result, "Abrindo chrome.")

    def test_repeated_long_response_is_not_replaced_by_confirmation(self):
        state = {}
        message = (
            "Analise dos arquivos: 1. README_CineRadar.md: este arquivo descreve "
            "um projeto com tecnologias, integrantes, instrucoes de execucao e testes automatizados."
        )

        first = style_response(message, preferences={}, variants=VARIANTS, next_phrase=first_phrase, state=state)
        second = style_response(message, preferences={}, variants=VARIANTS, next_phrase=first_phrase, state=state)

        self.assertEqual(first, message)
        self.assertEqual(second, message)


if __name__ == "__main__":
    unittest.main()
