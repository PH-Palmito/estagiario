import unittest
from unittest.mock import patch

from llm import ollama_client


class OllamaClientTests(unittest.TestCase):
    def test_local_provider_bypasses_gemini_preference(self):
        with (
            patch.object(ollama_client, "GEMINI_PRIMARY_TEXT_ENABLED", True),
            patch.object(ollama_client, "GEMINI_API_KEY", "key"),
            patch.object(ollama_client, "ask_gemini_model", side_effect=self.fail),
            patch.object(ollama_client, "_ask_ollama_model", return_value="local") as ask_ollama,
        ):
            result = ollama_client.ask_model("prompt", model="qwen", provider="local")

        self.assertEqual(result, "local")
        ask_ollama.assert_called_once()

    def test_cloud_provider_calls_gemini_directly(self):
        with (
            patch.object(ollama_client, "ask_gemini_model", return_value="cloud") as ask_gemini,
            patch.object(ollama_client, "_ask_ollama_model", side_effect=self.fail),
        ):
            result = ollama_client.ask_model("prompt", model="gemini-test", provider="cloud", num_predict=100)

        self.assertEqual(result, "cloud")
        self.assertEqual(ask_gemini.call_args.kwargs["model"], "gemini-test")


if __name__ == "__main__":
    unittest.main()
