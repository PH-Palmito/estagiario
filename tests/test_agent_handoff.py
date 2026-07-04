import unittest

from core.agent_handoff import format_handoff_plan_for_task


class AgentHandoffTests(unittest.TestCase):
    def test_handoff_plan_explains_cross_domain_task(self):
        result = format_handoff_plan_for_task("pesquisar notícia atual com fontes e revisar código do projeto")

        self.assertIn("Handoff para a tarefa", result)
        self.assertIn("Coordenação: handoff multiagente", result)
        self.assertIn("research_agent", result)
        self.assertIn("dev_agent", result)
        self.assertIn("Actions iniciais", result)

    def test_handoff_plan_uses_study_agent_for_file_study_memory_task(self):
        result = format_handoff_plan_for_task("analisar um PDF de estudo, gerar questões e salvar contexto na memória")

        self.assertIn("study_agent", result)
        self.assertIn("memory_agent", result)

    def test_handoff_plan_handles_empty_task(self):
        result = format_handoff_plan_for_task("")

        self.assertIn("Diga a tarefa", result)


if __name__ == "__main__":
    unittest.main()
