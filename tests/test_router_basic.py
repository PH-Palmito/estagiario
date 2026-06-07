import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.router_basic import (
    detect_custom_response_command,
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

    def test_project_name_question_is_local(self):
        self.assertEqual(
            detect_greeting("qual o nome do projeto"),
            {
                "intent": "respond",
                "target": None,
                "response": "O projeto se chama Axel. E o assistente local que estamos construindo para voz, arquivos, estudos, automacoes e controle do computador.",
            },
        )

    def test_presence_check(self):
        self.assertEqual(
            detect_greeting("esta ai?"),
            {"intent": "respond", "target": None, "response": "Estou aqui."},
        )
        self.assertEqual(
            detect_greeting("axel?"),
            {"intent": "respond", "target": None, "response": "Estou aqui."},
        )

    def test_introduction(self):
        with TemporaryDirectory() as temp_dir, patch(
            "memory.assistant_customization.CUSTOMIZATION_PATH",
            Path(temp_dir) / "assistant_customization.json",
        ):
            result = detect_greeting("quem e o axel")
            self.assertEqual(result["intent"], "respond")
            self.assertIn("assistente local", result["response"])
            self.assertIn("Axel, o que temos para hoje?", result["response"])
            self.assertNotIn("instagramavel", result["response"])

    def test_introduction_accepts_compact_transcription(self):
        with TemporaryDirectory() as temp_dir, patch(
            "memory.assistant_customization.CUSTOMIZATION_PATH",
            Path(temp_dir) / "assistant_customization.json",
        ):
            result = detect_greeting("apresentese")
            self.assertEqual(result["intent"], "respond")
            self.assertIn("Prazer, eu sou o Axel", result["response"])

    def test_teaches_custom_introduction(self):
        with TemporaryDirectory() as temp_dir, patch(
            "memory.assistant_customization.CUSTOMIZATION_PATH",
            Path(temp_dir) / "assistant_customization.json",
        ):
            learned = detect_custom_response_command("axel aprenda a se apresentar assim: Sou o Axel em modo vitrine.")
            self.assertEqual(learned["intent"], "respond")

            result = detect_greeting("se apresente")
            self.assertEqual(result["response"], "Sou o Axel em modo vitrine.")

    def test_teaches_long_custom_introduction_with_accents(self):
        intro = (
            "Olá, eu sou o Axel. Um assistente pessoal inteligente criado para ajudar na rotina, "
            "nos estudos, nos treinos, nos investimentos e na automação do computador. "
            "Meu objetivo é simples: reunir informações importantes, responder com rapidez e executar ações de forma prática. "
            "Ainda estou em desenvolvimento, mas evoluo a cada nova função. Eu sou o Axel. Seu assistente pessoal."
        )
        with TemporaryDirectory() as temp_dir, patch(
            "memory.assistant_customization.CUSTOMIZATION_PATH",
            Path(temp_dir) / "assistant_customization.json",
        ):
            learned = detect_custom_response_command(f"axel aprenda a se apresentar assim: {intro}")
            self.assertEqual(learned["intent"], "respond")

            result = detect_greeting("apresentese")
            self.assertEqual(result["response"], intro)

    def test_teaches_custom_direct_response(self):
        with TemporaryDirectory() as temp_dir, patch(
            "memory.assistant_customization.CUSTOMIZATION_PATH",
            Path(temp_dir) / "assistant_customization.json",
        ):
            learned = detect_custom_response_command("quando eu disser status bonito responda Sistema elegante e pronto.")
            self.assertEqual(learned["intent"], "respond")

            result = detect_custom_response_command("status bonito")
            self.assertEqual(result["response"], "Sistema elegante e pronto.")

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
