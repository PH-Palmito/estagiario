import unittest

from core.router_registry import (
    INTENT_LEVEL_CONVERSATION,
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
)
from llm.model_selection import PROVIDER_CLOUD, PROVIDER_LOCAL, normalize_provider, select_chat_model_route


class ModelSelectionTests(unittest.TestCase):
    def test_normalizes_provider_aliases(self):
        self.assertEqual(normalize_provider("gemini"), PROVIDER_CLOUD)
        self.assertEqual(normalize_provider("nuvem"), PROVIDER_CLOUD)
        self.assertEqual(normalize_provider("ollama"), PROVIDER_LOCAL)
        self.assertEqual(normalize_provider("???"), "auto")

    def test_explicit_local_preference_wins(self):
        route = select_chat_model_route(
            "explique um tema complexo",
            preferences={"ai_text_provider": "local"},
            local_model="qwen",
            cloud_model="gemini",
            cloud_available=True,
            complex_request=True,
            intent_level=INTENT_LEVEL_QUESTION,
        )

        self.assertEqual(route.provider, PROVIDER_LOCAL)
        self.assertEqual(route.model, "qwen")

    def test_complex_question_uses_cloud_when_available(self):
        route = select_chat_model_route(
            "compare cenarios com bastante contexto",
            preferences={},
            local_model="qwen",
            cloud_model="gemini",
            cloud_available=True,
            complex_request=True,
            intent_level=INTENT_LEVEL_QUESTION,
        )

        self.assertEqual(route.provider, PROVIDER_CLOUD)
        self.assertEqual(route.fallback_provider, PROVIDER_LOCAL)

    def test_direct_command_stays_local_even_when_complex(self):
        route = select_chat_model_route(
            "abra o chrome e organize a tela",
            preferences={},
            local_model="qwen",
            cloud_model="gemini",
            cloud_available=True,
            complex_request=True,
            intent_level=INTENT_LEVEL_DIRECT_COMMAND,
        )

        self.assertEqual(route.provider, PROVIDER_LOCAL)

    def test_unavailable_cloud_falls_back_to_local(self):
        route = select_chat_model_route(
            "qual sua opiniao?",
            preferences={"ai_text_provider": "cloud"},
            local_model="qwen",
            cloud_model="gemini",
            cloud_available=False,
            complex_request=True,
            intent_level=INTENT_LEVEL_CONVERSATION,
        )

        self.assertEqual(route.provider, PROVIDER_LOCAL)
        self.assertIn("indisponivel", route.reason)


if __name__ == "__main__":
    unittest.main()
