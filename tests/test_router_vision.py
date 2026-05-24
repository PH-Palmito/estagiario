import unittest
from unittest.mock import patch

from core.router_vision import detect_vision_model_command, detect_visual_question_command


class RouterVisionTests(unittest.TestCase):
    def test_explicit_visual_question(self):
        self.assertEqual(
            detect_visual_question_command("sobre a imagem qual item venceu?"),
            {"intent": "vision_answer_question", "target": "qual item venceu?"},
        )

    def test_chart_question_without_context(self):
        self.assertEqual(
            detect_visual_question_command("qual categoria ganhou?"),
            {"intent": "vision_answer_question", "target": "qual categoria ganhou?"},
        )

    @patch("core.router_vision.time.time", return_value=1000.0)
    @patch("core.router_vision.load_current_topic", return_value={})
    @patch("core.router_vision.last_vision_item", return_value={"created_at": 950.0})
    def test_followup_with_recent_visual_context(self, _last_item, _topic, _time):
        self.assertEqual(
            detect_visual_question_command("e por que isso aconteceu?"),
            {"intent": "vision_answer_question", "target": "e por que isso aconteceu?"},
        )

    @patch("core.router_vision.load_current_topic", return_value={"topic": "grafico de vendas"})
    @patch("core.router_vision.last_vision_item", return_value=None)
    def test_referential_question_with_topic_context(self, _last_item, _topic):
        self.assertEqual(
            detect_visual_question_command("qual o assunto desse grafico?"),
            {"intent": "vision_answer_question", "target": "qual o assunto desse grafico?"},
        )

    def test_investment_question_is_not_visual(self):
        self.assertIsNone(detect_visual_question_command("qual a cotacao de PETR4?"))

    @patch("core.router_vision.docs_context_relevant", return_value=True)
    def test_docs_context_is_not_visual(self, _docs):
        self.assertIsNone(detect_visual_question_command("qual funcao faz isso?"))

    def test_vision_status(self):
        self.assertEqual(detect_vision_model_command("status da visao"), {"intent": "vision_status", "target": None})

    def test_vision_install_hint(self):
        self.assertEqual(
            detect_vision_model_command("como instalar visao"),
            {"intent": "vision_install_hint", "target": None},
        )

    def test_vision_download_light_model(self):
        self.assertEqual(
            detect_vision_model_command("baixar modelo visual leve"),
            {"intent": "vision_download_light_model", "target": None},
        )

    def test_vision_active_model(self):
        self.assertEqual(
            detect_vision_model_command("qual modelo de visao"),
            {"intent": "vision_active_model", "target": None},
        )

    def test_vision_history(self):
        self.assertEqual(detect_vision_model_command("historico visual"), {"intent": "vision_history", "target": None})

    def test_vision_last_analysis(self):
        self.assertEqual(
            detect_vision_model_command("ultima analise visual"),
            {"intent": "vision_last_analysis", "target": None},
        )


if __name__ == "__main__":
    unittest.main()
