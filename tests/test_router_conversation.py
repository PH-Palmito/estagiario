import unittest
from unittest.mock import patch

from core.router_conversation import (
    detect_builtin_general_answer,
    detect_general_question_early,
    detect_question_fallback,
    detect_light_conversation,
    detect_llm_action_command,
    detect_ollama_chat,
    detect_short_unclear_text,
    detect_useful_conversation,
)
from core.router import route


class RouterConversationTests(unittest.TestCase):
    def test_repeat_last(self):
        self.assertEqual(detect_short_unclear_text("repete"), {"intent": "repeat_last", "target": None})

    def test_vague_action_asks_for_target(self):
        result = detect_short_unclear_text("faz aquilo")
        self.assertEqual(result["intent"], "respond")
        self.assertIn("vago", result["response"])

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

    def test_builtin_general_answers_common_questions(self):
        self.assertIn("streamer brasileiro", detect_builtin_general_answer("quem e alanzoca?")["response"])
        self.assertIn("Nikola Tesla", detect_builtin_general_answer("oq e tesla?")["response"])
        self.assertIn("caso base", detect_builtin_general_answer("me explique recursao em python")["response"])
        english = detect_builtin_general_answer("pode me ajudar a aprender ingles?")
        self.assertEqual(english["intent"], "respond")
        self.assertIn("inglês", english["response"])
        self.assertIn("misturar português e inglês", english["response"])

    @patch("core.router_conversation.chat_response", return_value="Banana e uma fruta.")
    def test_general_question_early_uses_chat_for_random_question(self, _chat):
        result = detect_general_question_early("o que e banana?")

        self.assertEqual(result, {"intent": "respond", "target": None, "response": "Banana e uma fruta."})

    @patch("core.router_conversation.chat_response", return_value="Nao deve usar chat.")
    def test_general_question_early_skips_explicit_screen_file_and_investments(self, _chat):
        self.assertIsNone(detect_general_question_early("o que tem na tela?"))
        self.assertIsNone(detect_general_question_early("o que tem no arquivo atual?"))
        self.assertIsNone(detect_general_question_early("qual a cotacao de BBAS3?"))

    def test_builtin_general_answers_night_intern_mode(self):
        result = detect_builtin_general_answer("oq faz o estagiario noturno?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("noite", result["response"])

    def test_builtin_general_answers_minor_symptom_statement(self):
        result = detect_builtin_general_answer("axel minha rinite esta atacada")
        self.assertEqual(result["intent"], "respond")
        self.assertIn("Não consigo diagnosticar", result["response"])
        self.assertIn("soro", result["response"])
        self.assertIsNotNone(detect_builtin_general_answer("estou espirrando muitp"))
        self.assertIsNotNone(detect_builtin_general_answer("estou espirrando muito"))

    def test_builtin_general_answers_sleep_and_stomach_statements(self):
        stomach = detect_builtin_general_answer("to com dor de barriga")
        self.assertEqual(stomach["intent"], "respond")
        self.assertIn("Não consigo diagnosticar", stomach["response"])

        sleepy = detect_builtin_general_answer("estou com vontade de dormir")
        self.assertEqual(sleepy["intent"], "respond")
        self.assertIn("salvar", sleepy["response"])
        self.assertIn("lembrar", sleepy["response"])

    @patch("core.router_conversation.select_read_action", return_value={"name": "background.run_action", "arguments": {"name": "recursao"}})
    def test_explanation_request_does_not_become_action(self, _select):
        self.assertIsNone(detect_llm_action_command("me explique recursao em python"))

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
        self.assertIn("Não vou inventar", result["response"])
        self.assertIn("Nikola Tesla", result["response"])
        self.assertIn("pesquisar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_practical_question_gets_useful_fallback_when_chat_fails(self, _chat):
        result = route("qual a receita de bolo de cenoura?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("bolo de cenoura", result["response"])
        self.assertIn("forno médio", result["response"])
        self.assertNotIn("Não vou inventar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_factual_question_keeps_cautious_fallback_when_chat_fails(self, _chat):
        result = route("quem foi Marie Curie?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("Não vou inventar", result["response"])
        self.assertIn("Marie Curie", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_english_learning_uses_builtin_answer(self, _chat):
        result = route("pode me ajudar a aprender ingles?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("inglês", result["response"])
        self.assertNotIn("Não vou inventar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_english_practice_uses_correction_mode(self, _chat):
        result = route("axel how are you?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("I'm doing well", result["response"])
        self.assertIn("Correção leve", result["response"])
        self.assertNotIn("Não vou inventar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_english_meaning_question_translates_short_phrase(self, _chat):
        result = route('"I\'m doing well" oq significa?')

        self.assertEqual(result["intent"], "respond")
        self.assertIn("Estou bem", result["response"])
        self.assertNotIn("Não vou inventar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_english_meaning_without_quotes_translates_short_phrase(self, _chat):
        result = route("I'm doing well significa o que?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("Estou bem", result["response"])
        self.assertNotIn("Não vou inventar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_mixed_english_gets_language_coaching(self, _chat):
        result = route("axel do you have um telegram?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("Do you have Telegram?", result["response"])
        self.assertIn("Telegram", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_help_request_stays_useful_without_chat(self, _chat):
        result = route("me ajuda a estudar redes")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("estudar redes", result["response"])
        self.assertIn("perguntas de fixação", result["response"])
        self.assertNotIn("Não vou inventar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_teaching_request_gets_tutor_response_without_chat(self, _chat):
        result = route("me ensina o básico de banco de dados")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("banco de dados", result["response"])
        self.assertIn("revisão dos erros", result["response"])
        self.assertNotIn("Não vou inventar", result["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_useful_conversation_answers_gift_workout_and_food_requests(self, _chat):
        gift = route("ideia de presente para minha namorada?")
        workout = route("dicas de treino em casa")
        food = route("quero comer melhor sem fazer dieta")

        self.assertEqual(gift["intent"], "respond")
        self.assertIn("namorada", gift["response"])
        self.assertIn("carta curta", gift["response"])
        self.assertEqual(workout["intent"], "respond")
        self.assertIn("treino em casa", workout["response"])
        self.assertIn("flexão", workout["response"])
        self.assertEqual(food["intent"], "respond")
        self.assertIn("sem chamar isso de dieta", food["response"])

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_useful_conversation_personalizes_common_life_advice(self, _chat):
        mother_gift = route("me da uma ideia de presente para minha mãe")
        home_workout = route("dicas de treino sem equipamento")
        no_diet = route("quero comer melhor mas não faço dieta")

        self.assertEqual(mother_gift["intent"], "respond")
        self.assertIn("sua mãe", mother_gift["response"])
        self.assertIn("sinal de cuidado", mother_gift["response"])
        self.assertEqual(home_workout["intent"], "respond")
        self.assertIn("3 dias por semana", home_workout["response"])
        self.assertIn("sem equipamento", home_workout["response"])
        self.assertEqual(no_diet["intent"], "respond")
        self.assertIn("troca óbvia", no_diet["response"])
        self.assertNotIn("Não vou inventar", no_diet["response"])

    @patch("core.router_conversation.load_current_topic", return_value={"topic": "redes de computadores"})
    @patch("core.router_conversation.chat_response", return_value=None)
    def test_contextual_followup_uses_current_topic_when_chat_fails(self, _chat, _topic):
        examples = route("me da exemplos")
        plan = route("faz um plano")
        questions = route("cria perguntas")
        explain = route("explica melhor")

        self.assertEqual(examples["intent"], "respond")
        self.assertIn("redes de computadores", examples["response"])
        self.assertIn("exercícios", examples["response"])
        self.assertEqual(plan["intent"], "respond")
        self.assertIn("Plano curto", plan["response"])
        self.assertEqual(questions["intent"], "respond")
        self.assertIn("Perguntas", questions["response"])
        self.assertEqual(explain["intent"], "respond")
        self.assertIn("Indo um pouco mais fundo", explain["response"])

    @patch("core.router_conversation.update_current_topic_from_conversation")
    @patch("core.router_conversation.chat_response", return_value=None)
    def test_useful_local_answer_updates_current_topic_for_followups(self, _chat, update_topic):
        result = route("me ajuda a estudar redes")

        self.assertEqual(result["intent"], "respond")
        update_topic.assert_called()
        kwargs = update_topic.call_args.kwargs
        self.assertEqual(kwargs["topic"], "estudar redes")
        self.assertIn("perguntas de fixação", kwargs["assistant_response"])

    @patch("core.router_conversation.chat_response", return_value="Não consegui confirmar uma resposta boa agora.")
    def test_practical_open_question_prefers_useful_answer_over_weak_chat(self, _chat):
        result = route("pode me dar ideias de presente para minha namorada?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("presente", result["response"])
        self.assertIn("carta curta", result["response"])
        self.assertNotIn("Não consegui confirmar", result["response"])

    @patch("llm.chat.ask_model", return_value="Não vou inventar sem uma resposta confiável do chat local.")
    def test_full_route_uses_useful_fallback_when_model_returns_weak_answer(self, _ask_model):
        result = route("me ajuda a estudar redes")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("perguntas de fixação", result["response"])
        self.assertNotIn("Não vou inventar", result["response"])

    def test_useful_conversation_detector_ignores_clear_music_command(self):
        self.assertIsNone(detect_useful_conversation("toque uma musica"))

    @patch("core.router_conversation.chat_response", return_value="Tesla foi uma empresa/pessoa dependendo do contexto.")
    def test_full_route_keeps_factual_question_out_of_screen(self, _chat):
        result = route("oq é tesla?")

        self.assertEqual(result["intent"], "respond")
        self.assertNotEqual(result["intent"], "browser_describe_screen")

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_full_route_random_question_uses_conversation_fallback(self, _chat):
        result = route("o que e banana?")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("confirmar", result["response"])
        self.assertIn("banana", result["response"])
        self.assertNotIn(result["intent"], {"browser_describe_screen", "investment_memory_answer"})

    @patch("core.router_conversation.chat_response", return_value="Resposta geral.")
    def test_full_route_keeps_explicit_special_contexts(self, _chat):
        self.assertEqual(route("o que tem na tela?")["intent"], "browser_describe_screen")
        self.assertEqual(route("qual a cotacao de BBAS3?")["intent"], "investment_memory_answer")

    def test_full_route_presence_check_stays_out_of_screen(self):
        for phrase in ("está aí?", "ta ai?", "axel?", "axel está aí?"):
            with self.subTest(phrase=phrase):
                result = route(phrase)

                self.assertEqual(result["intent"], "respond")
                self.assertEqual(result["response"], "Estou aqui.")
                self.assertNotEqual(result["intent"], "browser_describe_screen")


if __name__ == "__main__":
    unittest.main()
