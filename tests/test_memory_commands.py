import unittest
from unittest.mock import patch

from core.memory_commands import maybe_handle_long_memory_command, maybe_handle_operational_context_command


class MemoryCommandTests(unittest.TestCase):
    def test_remember_operational_preference_keeps_tail(self):
        with patch(
            "core.memory_commands.remember_operational_preference",
            return_value="Preferencia operacional salva: falar curto.",
        ) as remember:
            result = maybe_handle_operational_context_command(
                "lembre na memoria operacional que falar curto"
            )

        self.assertEqual(result, "Preferencia operacional salva: falar curto.")
        remember.assert_called_once_with("falar curto", kind="preference")

    def test_note_operational_context(self):
        with patch(
            "core.memory_commands.remember_operational_preference",
            return_value="Anotei no contexto operacional: foco em testes.",
        ) as remember:
            result = maybe_handle_operational_context_command("registre no contexto operacional foco em testes")

        self.assertEqual(result, "Anotei no contexto operacional: foco em testes.")
        remember.assert_called_once_with("foco em testes", kind="note")

    def test_recent_apps_formats_context_payload(self):
        with patch(
            "core.memory_commands.save_operational_context",
            return_value={"recent_apps": ["chrome", "spotify"], "recent_sites": [], "recent_topics": []},
        ):
            result = maybe_handle_operational_context_command("apps recentes")

        self.assertEqual(result, "Apps recentes: chrome, spotify.")

    def test_update_context_includes_summary(self):
        with patch(
            "core.memory_commands.save_operational_context",
            return_value={"summary": "Axel acompanhando operador."},
        ):
            result = maybe_handle_operational_context_command("atualizar contexto")

        self.assertEqual(result, "Contexto operacional atualizado. Axel acompanhando operador.")

    def test_show_long_memory(self):
        with patch("core.memory_commands.format_long_memory", return_value="Memoria longa: project: Axel."):
            result = maybe_handle_long_memory_command("mostrar memoria longa")

        self.assertEqual(result, "Memoria longa: project: Axel.")

    def test_list_skills(self):
        with patch("core.memory_commands.format_skill_catalog", return_value="Skills procedurais: programacao."):
            result = maybe_handle_long_memory_command("listar skills do axel")

        self.assertEqual(result, "Skills procedurais: programacao.")

    def test_pending_skill_suggestions(self):
        with patch("core.memory_commands.format_pending_skill_suggestions", return_value="Sugestoes de skills: Atualizar skill."):
            result = maybe_handle_long_memory_command("sugestoes de skills")

        self.assertEqual(result, "Sugestoes de skills: Atualizar skill.")

    def test_create_skill_from_command(self):
        with patch("core.memory_commands.create_skill_from_request", return_value="memory/skills/estudos/SKILL.md") as create:
            result = maybe_handle_long_memory_command("crie uma skill para estudar slides")

        self.assertEqual(result, "Skill procedural criada e salva em memory/skills/estudos/SKILL.md.")
        create.assert_called_once_with("estudar slides")

    def test_approve_skill_suggestion(self):
        with patch("core.memory_commands.approve_pending_skill_suggestion", return_value="Skill procedural aprovada."):
            result = maybe_handle_long_memory_command("aprovar skill")

        self.assertEqual(result, "Skill procedural aprovada.")

    def test_reject_skill_suggestion(self):
        with patch("core.memory_commands.reject_pending_skill_suggestion", return_value="Sugestao de skill rejeitada."):
            result = maybe_handle_long_memory_command("rejeitar skill")

        self.assertEqual(result, "Sugestao de skill rejeitada.")

    def test_search_skills(self):
        with patch("core.memory_commands.format_relevant_skills", return_value="Skills procedurais relevantes: Programacao."):
            result = maybe_handle_long_memory_command("qual skill para revisar codigo")

        self.assertIn("Programacao", result)

    def test_list_toolsets(self):
        with patch("core.memory_commands.format_toolset_catalog", return_value="Toolsets do Axel: Programacao."):
            result = maybe_handle_long_memory_command("listar toolsets do axel")

        self.assertEqual(result, "Toolsets do Axel: Programacao.")

    def test_search_toolsets(self):
        with patch("core.memory_commands.format_relevant_toolsets", return_value="Toolsets relevantes: Pesquisa."):
            result = maybe_handle_long_memory_command("qual toolset para noticia atual")

        self.assertIn("Pesquisa", result)

    def test_list_agents(self):
        with patch("core.memory_commands.format_agent_catalog", return_value="Agentes especialistas do Axel: dev_agent."):
            result = maybe_handle_long_memory_command("listar agentes do axel")

        self.assertEqual(result, "Agentes especialistas do Axel: dev_agent.")

    def test_search_agents(self):
        with patch("core.memory_commands.format_relevant_agents", return_value="Agentes especialistas relevantes: Pesquisa."):
            result = maybe_handle_long_memory_command("qual agente para noticia atual")

        self.assertIn("Pesquisa", result)

    def test_search_old_sessions(self):
        with patch("core.memory_commands.format_session_search", return_value="Encontrei isto nas sessoes antigas: AxelBrain."):
            result = maybe_handle_long_memory_command("lembra quando falamos sobre AxelBrain")

        self.assertIn("AxelBrain", result)

    def test_layered_recall_command(self):
        with patch("core.memory_commands.format_layered_memory_recall", return_value="Recall em camadas: AxelBrain."):
            result = maybe_handle_long_memory_command("recall em camadas sobre AxelBrain")

        self.assertEqual(result, "Recall em camadas: AxelBrain.")

    def test_episodic_memory_command(self):
        with patch("core.memory_commands.format_episode", return_value="Episodio 2026-05-30: Resumo."):
            result = maybe_handle_long_memory_command("memoria episodica")

        self.assertEqual(result, "Episodio 2026-05-30: Resumo.")

    def test_task_evaluation_summary_command(self):
        with patch("core.memory_commands.format_task_evaluation_summary", return_value="Autoavaliacao de tarefas: 1 registro."):
            result = maybe_handle_long_memory_command("autoavaliacao de tarefas")

        self.assertEqual(result, "Autoavaliacao de tarefas: 1 registro.")

    def test_capability_ranking_command(self):
        with patch("core.memory_commands.format_capability_rankings", return_value="Ranking de agentes: research_agent."):
            result = maybe_handle_long_memory_command("ranking de agentes")

        self.assertEqual(result, "Ranking de agentes: research_agent.")

    def test_agent_tool_library_command(self):
        with patch("core.memory_commands.format_agent_tool_library", return_value="Biblioteca de ferramentas de dev_agent."):
            result = maybe_handle_long_memory_command("ferramentas do agente dev_agent")

        self.assertEqual(result, "Biblioteca de ferramentas de dev_agent.")

    def test_latest_task_evaluation_update_command(self):
        with (
            patch("core.memory_commands.update_latest_task_evaluation", return_value={"status": "success"}) as update,
            patch("core.memory_commands.format_latest_task_evaluation", return_value="Ultima autoavaliacao: respond -> success."),
        ):
            result = maybe_handle_long_memory_command("ultima tarefa funcionou resposta boa")

        self.assertEqual(result, "Autoavaliacao registrada. Ultima autoavaliacao: respond -> success.")
        update.assert_called_once_with("funcionou", note="resposta boa")

    def test_latest_task_evaluation_update_without_recent_task(self):
        with patch("core.memory_commands.update_latest_task_evaluation", return_value={}):
            result = maybe_handle_long_memory_command("ultima tarefa falhou")

        self.assertEqual(result, "Ainda nao ha tarefa recente para avaliar.")

    def test_create_workflow_command(self):
        with (
            patch("core.memory_commands.create_workflow_plan", return_value={"title": "melhorar HUD"}),
            patch("core.memory_commands.format_workflow_plan", return_value="Workflow atual: melhorar HUD."),
        ):
            result = maybe_handle_long_memory_command("criar plano duravel para melhorar HUD")

        self.assertEqual(result, "Workflow duravel criado. Workflow atual: melhorar HUD.")

    def test_show_workflow_command(self):
        with patch("core.memory_commands.format_workflow_plan", return_value="Workflow atual: melhorar HUD."):
            result = maybe_handle_long_memory_command("workflow atual")

        self.assertEqual(result, "Workflow atual: melhorar HUD.")

    def test_list_workflow_command(self):
        with patch("core.memory_commands.format_workflow_list", return_value="Workflows duraveis: 1. HUD."):
            result = maybe_handle_long_memory_command("listar planos duraveis")

        self.assertEqual(result, "Workflows duraveis: 1. HUD.")

    def test_curate_long_memory_reports_added_items(self):
        with (
            patch("core.memory_commands.curate_recent_ui_history", return_value=2),
            patch("core.memory_commands.save_operational_context"),
        ):
            result = maybe_handle_long_memory_command("curar memoria longa")

        self.assertEqual(result, "Memoria longa curada. Adicionei 2 item(ns) duraveis.")

    def test_manual_long_memory_save(self):
        with (
            patch("core.memory_commands.maybe_remember_from_user_text", return_value=True) as remember,
            patch("core.memory_commands.save_operational_context"),
        ):
            result = maybe_handle_long_memory_command("lembre na memoria longa que priorizamos modularizacao")

        self.assertEqual(result, "Memoria longa atualizada.")
        remember.assert_called_once_with(
            "lembre que priorizamos modularizacao",
            source="manual-long-memory",
        )


if __name__ == "__main__":
    unittest.main()
