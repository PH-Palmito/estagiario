import unittest

from core.axel_personality import apply_personality_layer, contextual_adaptive_tone, contextual_humor_observation


PREFERENCES = {
    "assistant_personality_enabled": True,
    "assistant_adaptive_tone_enabled": True,
    "assistant_proactivity_enabled": True,
    "assistant_humor_enabled": True,
    "assistant_humor_style": "seco",
    "assistant_humor_level": 2,
}


class AxelPersonalityTests(unittest.TestCase):
    def test_adds_adaptive_tone_for_error_context(self):
        result = apply_personality_layer(
            "Nao funcionou de novo: a permissao negada voltou.",
            preferences=PREFERENCES,
            state={},
        )

        self.assertEqual(
            result,
            "Nao funcionou de novo: a permissao negada voltou. Vou manter curto: primeiro isolar a causa, depois aplicar a correcao.",
        )

    def test_adds_adaptive_tone_for_sensitive_context_without_humor(self):
        result = apply_personality_layer(
            "Resumo da carteira concluido.",
            preferences=PREFERENCES,
            state={},
        )

        self.assertEqual(
            result,
            "Resumo da carteira concluido. Vou tratar isso com contexto e sem chute.",
        )

    def test_adaptive_tone_can_be_disabled(self):
        preferences = dict(PREFERENCES, assistant_adaptive_tone_enabled=False)
        result = contextual_adaptive_tone(
            "Nao tenho certeza se esse arquivo e o certo.",
            preferences=preferences,
            state={},
        )

        self.assertIsNone(result)

    def test_does_not_repeat_same_adaptive_tone(self):
        state = {}
        message = "Nao funcionou de novo: a permissao negada voltou."

        first = apply_personality_layer(message, preferences=PREFERENCES, state=state)
        second = apply_personality_layer(message, preferences=PREFERENCES, state=state)

        self.assertIn("Vou manter curto", first)
        self.assertEqual(second, message)

    def test_adds_contextual_humor_for_duplicate_files(self):
        result = apply_personality_layer(
            "Encontrei 4 versoes do arquivo final_final.pdf.",
            preferences=PREFERENCES,
            state={},
        )

        self.assertEqual(
            result,
            "Encontrei 4 versoes do arquivo final_final.pdf. Todas aparentemente definitivas.",
        )

    def test_skips_humor_for_sensitive_financial_context(self):
        result = contextual_humor_observation(
            "Compilacao concluida para relatorio da carteira.",
            preferences=PREFERENCES,
            state={},
        )

        self.assertIsNone(result)

    def test_skips_humor_for_frustration_or_errors(self):
        result = contextual_humor_observation(
            "Nao funcionou de novo. Compilacao concluida.",
            preferences=PREFERENCES,
            state={},
        )

        self.assertIsNone(result)

    def test_humor_respects_disabled_preference(self):
        preferences = dict(PREFERENCES, assistant_humor_enabled=False)
        result = apply_personality_layer(
            "Detectei 37 abas abertas.",
            preferences=preferences,
            state={},
        )

        self.assertEqual(result, "Detectei 37 abas abertas.")

    def test_adds_proactive_suggestion_for_missing_file(self):
        result = apply_personality_layer(
            "README_CineRadar.md: Arquivo nao encontrado.",
            preferences=PREFERENCES,
            state={},
        )

        self.assertEqual(
            result,
            "README_CineRadar.md: Arquivo nao encontrado. Próximo passo útil: procurar pelo nome em Downloads e pastas recentes.",
        )

    def test_does_not_repeat_same_personality_addition(self):
        state = {}
        message = "Encontrei 4 versoes do arquivo final_final.pdf."

        first = apply_personality_layer(message, preferences=PREFERENCES, state=state)
        second = apply_personality_layer(message, preferences=PREFERENCES, state=state)

        self.assertIn("Todas aparentemente definitivas.", first)
        self.assertEqual(second, message)


if __name__ == "__main__":
    unittest.main()
