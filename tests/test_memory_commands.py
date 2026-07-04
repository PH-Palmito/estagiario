import unittest
from unittest.mock import patch

from core.memory_commands import maybe_handle_long_memory_command, maybe_handle_operational_context_command


class MemoryCommandTests(unittest.TestCase):
    def test_last_user_question_skips_current_meta_question(self):
        turns = [
            {"role": "user", "text": "o arquivo fala sobre bananas?"},
            {"role": "assistant", "text": "Nao. O arquivo fala sobre redes."},
            {"role": "user", "text": "qual foi minha ultima pergunta?"},
        ]

        with patch("core.memory_commands.recent_turns", return_value=turns):
            result = maybe_handle_operational_context_command("qual foi minha ultima pergunta?")

        self.assertEqual(result, "Sua ultima pergunta foi: o arquivo fala sobre bananas?")

    def test_last_assistant_response_uses_recent_session_turn(self):
        turns = [
            {"role": "user", "text": "o arquivo fala sobre bananas?"},
            {"role": "assistant", "text": "Nao. O arquivo fala sobre redes."},
            {"role": "user", "text": "qual foi sua ultima resposta?"},
        ]

        with patch("core.memory_commands.recent_turns", return_value=turns):
            result = maybe_handle_operational_context_command("qual foi sua ultima resposta?")

        self.assertEqual(result, "Minha ultima resposta foi: Nao. O arquivo fala sobre redes.")

    def test_last_user_question_handles_empty_session(self):
        with patch("core.memory_commands.recent_turns", return_value=[]):
            result = maybe_handle_operational_context_command("qual foi minha ultima pergunta?")

        self.assertEqual(result, "Ainda nao tenho uma pergunta anterior guardada nesta sessao.")

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

    def test_workspace_context_command(self):
        with patch("core.memory_commands.format_workspace_context", return_value="Contexto de workspace carregado."):
            result = maybe_handle_operational_context_command("contexto do workspace")

        self.assertEqual(result, "Contexto de workspace carregado.")

    def test_product_cache_commands(self):
        with patch("core.memory_commands.format_cached_products", return_value="Produtos recentes em cache: 1. Produto."):
            result = maybe_handle_operational_context_command("produtos recentes")

        self.assertEqual(result, "Produtos recentes em cache: 1. Produto.")

        with patch("core.memory_commands.cheapest_cached_product", return_value="O mais barato no cache recente e o item 1: Produto."):
            result = maybe_handle_operational_context_command("mais barato em cache")

        self.assertEqual(result, "O mais barato no cache recente e o item 1: Produto.")

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

    def test_agent_operations_overview_command(self):
        with patch("core.memory_commands.format_agent_operations_overview", return_value="Agentes operacionais do Axel: dev_agent."):
            result = maybe_handle_long_memory_command("agentes operacionais do axel")

        self.assertEqual(result, "Agentes operacionais do Axel: dev_agent.")

    def test_agent_operations_detail_command(self):
        with patch("core.memory_commands.format_agent_operations_detail", return_value="Agente de Programação: uso 3.") as detail:
            result = maybe_handle_long_memory_command("detalhar agente dev_agent")

        detail.assert_called_once_with("dev_agent")
        self.assertEqual(result, "Agente de Programação: uso 3.")

    def test_agent_handoff_command(self):
        with patch("core.memory_commands.format_handoff_plan_for_task", return_value="Handoff para a tarefa: ok.") as handoff:
            result = maybe_handle_long_memory_command("handoff para pesquisar fontes e revisar código")

        handoff.assert_called_once_with("pesquisar fontes e revisar código")
        self.assertEqual(result, "Handoff para a tarefa: ok.")

    def test_actionable_skills_overview_command(self):
        with patch("core.memory_commands.format_actionable_skills_overview", return_value="Skills acionáveis: estudos pronta."):
            result = maybe_handle_long_memory_command("skills acionáveis")

        self.assertEqual(result, "Skills acionáveis: estudos pronta.")

    def test_actionable_skill_detail_command(self):
        with patch("core.memory_commands.format_actionable_skill_detail", return_value="Skill estudos: pronta.") as detail:
            result = maybe_handle_long_memory_command("validar skill estudos")

        detail.assert_called_once_with("estudos")
        self.assertEqual(result, "Skill estudos: pronta.")

    def test_todo_priorities_command(self):
        with patch("core.memory_commands.format_todo_priorities", return_value="Prioridade atual do Axel: Transformar fachada."):
            result = maybe_handle_long_memory_command("como estamos na lista de prioridades")

        self.assertEqual(result, "Prioridade atual do Axel: Transformar fachada.")

    def test_todo_evidence_audit_command(self):
        with patch("core.memory_commands.format_todo_evidence_audit", return_value="Auditoria de evidências das metas: ok."):
            result = maybe_handle_long_memory_command("auditar evidências das metas")

        self.assertEqual(result, "Auditoria de evidências das metas: ok.")

    def test_next_todo_step_command(self):
        with patch("core.memory_commands.format_next_todo_step", return_value="Próximo passo do Axel: tornar metas úteis."):
            result = maybe_handle_long_memory_command("qual o próximo passo")

        self.assertEqual(result, "Próximo passo do Axel: tornar metas úteis.")

    def test_complete_todo_priority_command(self):
        with patch("core.memory_commands.update_current_priority_status", return_value="Meta 2 concluída.") as update:
            result = maybe_handle_long_memory_command("concluir meta 2")

        update.assert_called_once_with(2, done=True)
        self.assertEqual(result, "Meta 2 concluída.")

    def test_show_todo_evidence_command(self):
        with patch("core.memory_commands.format_current_priority_evidence", return_value="Meta: X. Arquivos: a.py."):
            result = maybe_handle_long_memory_command("mostrar evidência da meta 2")

        self.assertEqual(result, "Meta: X. Arquivos: a.py.")

    def test_add_todo_evidence_command(self):
        with patch("core.memory_commands.parse_and_add_current_priority_evidence", return_value="Evidência registrada.") as add:
            result = maybe_handle_long_memory_command(
                "registrar evidência da meta 2 arquivos: core/memory_commands.py | testes: tests.test_memory_commands"
            )

        add.assert_called_once_with(2, "arquivos: core/memory_commands.py | testes: tests.test_memory_commands")
        self.assertEqual(result, "Evidência registrada.")

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

    def test_latency_report_command(self):
        with patch("core.memory_commands.format_latency_report", return_value="Latencia do Axel: 3 comandos medidos."):
            result = maybe_handle_long_memory_command("gargalos do axel")

        self.assertEqual(result, "Latencia do Axel: 3 comandos medidos.")

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

    def test_clean_long_memory_command(self):
        with patch("core.memory_commands.format_clean_long_memory_report", return_value="Memoria longa limpa: 3 -> 1 itens."):
            result = maybe_handle_long_memory_command("limpar memoria longa")

        self.assertEqual(result, "Memoria longa limpa: 3 -> 1 itens.")

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
