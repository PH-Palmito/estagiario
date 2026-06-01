import unittest
from contextlib import ExitStack
from unittest.mock import patch

from llm import chat


class ChatPromptAxelBrainTests(unittest.TestCase):
    def test_random_factual_question_uses_research_policy(self):
        plan = chat._chat_decision_plan("quem foi Nikola Tesla?", complex_request=False)

        self.assertEqual(plan.intent_level, "pergunta")
        self.assertEqual(plan.toolset, "pesquisa")
        self.assertEqual(plan.model_policy, "cloud_with_sources")

    def test_random_casual_text_stays_local_conversation(self):
        plan = chat._chat_decision_plan("abacate azul dançando", complex_request=False)

        self.assertEqual(plan.intent_level, "conversa")
        self.assertEqual(plan.toolset, "voz_rapida")
        self.assertEqual(plan.model_policy, "local_first")

    def test_chat_prompt_includes_axel_brain_brief(self):
        captured = {}

        def fake_ask_model(prompt, **kwargs):
            captured["prompt"] = prompt
            return "Resposta do Axel."

        with ExitStack() as stack:
            stack.enter_context(patch.object(chat, "chat_enabled", return_value=True))
            select_route = stack.enter_context(patch.object(chat, "select_chat_model_route"))
            stack.enter_context(patch.object(chat, "ask_model", side_effect=fake_ask_model))
            stack.enter_context(patch.object(chat, "format_conversation_brief", return_value="AxelBrain escolheu dev_agent."))
            stack.enter_context(patch.object(chat, "format_curated_memory", return_value="memoria curta"))
            stack.enter_context(patch.object(chat, "format_relevant_session_memory", return_value="sessoes"))
            stack.enter_context(patch.object(chat, "format_layered_memory_recall", return_value="recall camadas"))
            stack.enter_context(patch.object(chat, "format_relevant_skills", return_value="skills"))
            stack.enter_context(patch.object(chat, "format_relevant_toolsets", return_value="toolsets"))
            stack.enter_context(patch.object(chat, "format_relevant_agents", return_value="agentes"))
            stack.enter_context(patch.object(chat, "format_relevant_long_memory", return_value="memoria longa"))
            stack.enter_context(patch.object(chat, "format_research_sources", return_value="fontes"))
            stack.enter_context(patch.object(chat, "_vault_context_text", return_value="vault"))
            stack.enter_context(patch.object(chat, "_targeted_vault_context_text", return_value="vault alvo"))
            stack.enter_context(patch.object(chat, "_targeted_docs_context_text", return_value="docs"))
            stack.enter_context(patch.object(chat, "_profile_text", return_value="perfil"))
            stack.enter_context(patch.object(chat, "_operational_context_text", return_value="operacional"))
            stack.enter_context(patch.object(chat, "_current_topic_text", return_value="topico"))
            stack.enter_context(patch.object(chat, "_directives_text", return_value="diretrizes"))
            stack.enter_context(patch.object(chat, "update_current_topic_from_conversation"))
            stack.enter_context(patch.object(chat, "index_exchange"))
            stack.enter_context(patch.object(chat, "docs_context_relevant", return_value=False))
            chat_plan = stack.enter_context(patch.object(chat, "_chat_decision_plan"))
            chat_plan.return_value = type("Plan", (), {"model_policy": "local_first"})()
            select_route.return_value = type(
                "Route",
                (),
                {"uses_cloud": False, "provider": "local", "model": "qwen", "reason": "teste"},
            )()
            response = chat.chat_response("revisar codigo")

        self.assertEqual(response, "Resposta do Axel.")
        self.assertIn("Briefing do AxelBrain para esta resposta:", captured["prompt"])
        self.assertIn("AxelBrain escolheu dev_agent.", captured["prompt"])
        self.assertIn("Politica de modelo do AxelBrain:", captured["prompt"])
        self.assertIn("Recall de memoria em camadas:", captured["prompt"])


if __name__ == "__main__":
    unittest.main()
