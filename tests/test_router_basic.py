import unittest
from unittest.mock import patch

from core.router_basic import (
    detect_bluetooth_command,
    detect_greeting,
    detect_math,
    detect_profile_question,
    detect_user_name,
)


class RouterBasicTests(unittest.TestCase):
    @patch("core.router_basic.set_value")
    def test_user_name(self, set_value):
        self.assertEqual(
            detect_user_name("meu nome e Pedro"),
            {"intent": "respond", "target": None, "response": "Ok, vou lembrar que seu nome e Pedro."},
        )
        set_value.assert_called_once_with("nome", "Pedro")

    @patch("core.router_basic.get_value", return_value="Pedro")
    def test_profile_question(self, _get_value):
        self.assertEqual(
            detect_profile_question("qual meu nome"),
            {"intent": "respond", "target": None, "response": "Seu nome e Pedro."},
        )

    def test_greeting(self):
        self.assertEqual(
            detect_greeting("bom dia"),
            {"intent": "respond", "target": None, "response": "Bom dia. Vamos colocar esse computador em movimento."},
        )

    def test_introduction(self):
        result = detect_greeting("quem e o axel")
        self.assertEqual(result["intent"], "respond")
        self.assertIn("assistente local", result["response"])

    def test_math(self):
        result = detect_math("2 + 2")
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "respond")

    def test_bluetooth_on(self):
        self.assertEqual(detect_bluetooth_command("ligar bluetooth"), {"intent": "bluetooth_on", "target": None})

    def test_bluetooth_status(self):
        self.assertEqual(
            detect_bluetooth_command("status do bluetooth"),
            {"intent": "bluetooth_status", "target": None},
        )


if __name__ == "__main__":
    unittest.main()
