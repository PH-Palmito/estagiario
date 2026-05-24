import unittest
from unittest.mock import patch

from core.router_conversation import (
    detect_light_conversation,
    detect_llm_action_command,
    detect_ollama_chat,
    detect_short_unclear_text,
)


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


if __name__ == "__main__":
    unittest.main()
