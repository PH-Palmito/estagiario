import unittest
from unittest.mock import patch

from core.router_conversation import (
    detect_question_fallback,
    detect_light_conversation,
    detect_llm_action_command,
    detect_ollama_chat,
    detect_short_unclear_text,
)
from core.router import route


class RouterConversationTests(unittest.TestCase):
    def test_repeat_last(self):
        self.assertEqual(detect_short_unclear_text("repete"), {"intent": "repeat_last", "target": None})

    def test_short_unclear_text(self):
        self.assertEqual(
            detect_short_unclear_text("oi"),
            {"intent": "respond", "target": None, "response": "Pode repetir?"},
        )

    def test_light_conversation_capability(self):
        self.assertEqual(
            detect_light_conversation("voce consegue conversar?")["intent"],
            "respond",
        )

    @patch("core.router_conversation.select_read_action", return_value={"name": "memory.list", "arguments": {"namespace": "general"}})
    def test_llm_action_command(self, _select):
        self.assertEqual(
            detect_llm_action_command("liste memoria"),
            {
                "intent": "action_tool_execute",
                "target": {"name": "memory.list", "arguments": {"namespace": "general"}},
            },
        )

    @patch("core.router_conversation.chat_response", return_value="Resposta local.")
    def test_ollama_chat(self, _chat):
        self.assertEqual(
            detect_ollama_chat("me fale algo util"),
            {"intent": "respond", "target": None, "response": "Resposta local."},
        )

    @patch("core.router_conversation.chat_response", return_value="Alanzoca e um streamer brasileiro.")
    def test_factual_question_without_question_mark_uses_chat(self, _chat):
        self.assertEqual(
            detect_ollama_chat("quem é alanzoca"),
            {"intent": "respond", "target": None, "response": "Alanzoca e um streamer brasileiro."},
        )

    def test_question_fallback_when_chat_does_not_answer(self):
        result = detect_question_fallback("quem foi Nikola Tesla?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("Não consegui confirmar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_question_does_not_become_unclear_when_chat_fails(self, _chat):
        result = route("qual a receita de bolo de cenoura?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("Não consegui confirmar", result["response"])

    @patch("core.router_conversation.chat_response", return_value="Tesla foi uma empresa/pessoa dependendo do contexto.")
    def test_full_route_keeps_factual_question_out_of_screen(self, _chat):
        result = route("oq é tesla?")

        self.assertEqual(result["intent"], "respond")
        self.assertNotEqual(result["intent"], "browser_describe_screen")


if __name__ == "__main__":
    unittest.main()
