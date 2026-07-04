import unittest
from types import SimpleNamespace

from core.axel_brain_commands import (
    axel_brain_recommendations,
    format_axel_brain_history,
    format_axel_brain_insights,
    format_axel_brain_runtime_decision,
    format_axel_brain_timeline,
    format_last_response_reality,
    format_axel_route_trace,
    maybe_handle_axel_brain_runtime_command,
)


class AxelBrainCommandTests(unittest.TestCase):
    def test_formats_runtime_decision(self):
        text = format_axel_brain_runtime_decision(
            {
                "intent": "respond",
                "agent": "dev_agent",
                "toolset": "programacao",
                "risk_level": "read",
                "confidence": 0.82,
                "response_mode": "answer_with_context",
                "model_policy": "nvidia_or_gemini_for_reasoning",
                "reason": "toolset por gatilho; agente dev_agent; risco read",
                "coordination_mode": "multi_agent_handoff",
                "handoff_chain": [
                    {"agent": "dev_agent", "toolset": "programacao"},
                    {"agent": "research_agent", "toolset": "pesquisa"},
                ],
                "tool_libraries": [
                    {"agent": "dev_agent", "actions": [{"name": "code_inspect_workspace"}]},
                    {"agent": "research_agent", "actions": [{"name": "web_google_search"}]},
                ],
            },
            {
                "mission": "Ajudar com codigo.",
                "brain_version": "2.0",
                "next_step": "Responder usando as camadas de memoria e fontes relevantes.",
                "success_criteria": ["resposta curta", "contexto usado"],
                "post_task_signals": ["registrar sucesso"],
                "memory_layers": [{"name": "memoria_curta"}, {"name": "skills_procedurais"}],
            },
            {
                "channel": "remote",
                "remote_policy": {
                    "channel": "remote",
                    "decision": "confirm_remote_light",
                    "safety_profile": "remote_light_media_confirmation",
                    "can_confirm_remotely": True,
                    "execution_guidance": "pedir confirmacao no chat antes de executar midia leve",
                },
            },
        )

        self.assertIn("AxelBrain 2.0", text)
        self.assertIn("agente dev_agent", text)
        self.assertIn("toolset programacao", text)
        self.assertIn("confianca 82%", text)
        self.assertIn("coordenacao multi_agent_handoff", text)
        self.assertIn("handoff: dev_agent via programacao -> research_agent via pesquisa", text)
        self.assertIn("ferramentas por agente: dev_agent: code_inspect_workspace", text)
        self.assertIn("motivo: toolset por gatilho", text)
        self.assertIn("missao do agente: Ajudar com codigo.", text)
        self.assertIn("proximo passo: Responder usando", text)
        self.assertIn("criterios de sucesso: resposta curta", text)
        self.assertIn("sinais pos-tarefa: registrar sucesso", text)
        self.assertIn("memoria consultada: memoria_curta, skills_procedurais", text)
        self.assertIn("politica de canal: canal remote", text)
        self.assertIn("perfil remote_light_media_confirmation", text)
        self.assertIn("confirmacao remota sim", text)
        self.assertIn("guia de execucao: pedir confirmacao no chat", text)

    def test_reports_missing_decision(self):
        text = format_axel_brain_runtime_decision({})

        self.assertEqual(text, "Ainda nao tenho uma decisao recente do AxelBrain para explicar.")

    def test_handles_runtime_command(self):
        runtime_state = SimpleNamespace(
            axel_brain_plan={
                "intent": "open_app",
                "agent": "system_agent",
                "toolset": "sistema",
                "risk_level": "low",
                "confidence": 0.78,
                "response_mode": "execute_short",
                "model_policy": "local_first",
                "reason": "toolset por fallback de intent; agente system_agent; risco low",
            },
            axel_brain_brief={"mission": "Executar comando local."},
            axel_brain_contract={
                "channel": "local",
                "remote_policy": {"decision": "local_flow", "safety_profile": "local_normal"},
            },
            last_route_trace={},
        )

        result = maybe_handle_axel_brain_runtime_command("por que o axel decidiu isso", runtime_state)

        self.assertIsNotNone(result)
        self.assertIn("system_agent", result)
        self.assertIn("sistema", result)

    def test_reports_real_brain_effects(self):
        runtime_state = SimpleNamespace(
            axel_brain_plan={
                "agent": "study_agent",
                "toolset": "estudos",
                "model_policy": "nvidia_or_gemini_for_reasoning",
                "needs_confirmation": False,
                "response_mode": "answer_with_context",
                "tool_libraries": [{"actions": [{"name": "study.analyze_files"}]}],
            },
            axel_brain_brief={"memory_layers": [{"name": "skills_procedurais"}]},
            axel_brain_contract={"channel": "local"},
        )

        result = maybe_handle_axel_brain_runtime_command("efeitos do axelbrain", runtime_state)

        self.assertIn("Efeitos reais do AxelBrain", result)
        self.assertIn("study_agent", result)

    def test_audits_last_response_without_sensitive_details(self):
        timeline = [
            {
                "action": "study.analyze_files",
                "context": {"memory_layers": ["skills_procedurais", "sessoes_relevantes"]},
                "execution": {"action": "study.analyze_files"},
                "response": {
                    "provenance": {
                        "models": [{"provider": "cloud", "model": "nvidia/model", "success": True}],
                        "tools": ["study.analyze_files"],
                        "files": ["RedesBasico.pdf"],
                    }
                },
            }
        ]

        text = format_last_response_reality(timeline)

        self.assertIn("cloud/nvidia/model", text)
        self.assertIn("study.analyze_files", text)
        self.assertIn("RedesBasico.pdf", text)
        self.assertIn("skills_procedurais", text)
        self.assertNotIn("C:\\Users", text)

    def test_handles_response_reality_command(self):
        runtime_state = SimpleNamespace(
            axel_brain_timeline=[
                {
                    "action": "respond",
                    "context": {"memory_layers": ["memoria_curta"]},
                    "response": {"provenance": {"models": [], "tools": [], "files": []}},
                }
            ]
        )

        result = maybe_handle_axel_brain_runtime_command("o que foi real nessa resposta?", runtime_state)

        self.assertIn("Auditoria da", result)
        self.assertIn("nenhum modelo registrado", result)

    def test_formats_brain_history(self):
        text = format_axel_brain_history([
            {
                "intent": "daily_briefing",
                "agent": "daily_agent",
                "toolset": "rotina",
                "risk_level": "read",
                "channel": "remote",
                "safety_profile": "remote_read_only",
                "route_group": "daily",
            }
        ])

        self.assertIn("Ultimas decisoes do AxelBrain", text)
        self.assertIn("daily_briefing", text)
        self.assertIn("perfil remote_read_only", text)

    def test_handles_history_command(self):
        runtime_state = SimpleNamespace(
            axel_brain_plan={},
            axel_brain_brief={},
            axel_brain_history=[{"intent": "respond", "agent": "conversation_agent"}],
            last_route_trace={},
        )

        result = maybe_handle_axel_brain_runtime_command("historico do axelbrain", runtime_state)

        self.assertIsNotNone(result)
        self.assertIn("respond", result)

    def test_formats_brain_insights(self):
        history = [
            {"agent": "daily_agent", "toolset": "rotina", "risk_level": "read", "channel": "remote", "safety_profile": "remote_read_only"},
            {"agent": "system_agent", "toolset": "midia", "risk_level": "low", "channel": "remote", "safety_profile": "remote_light_media_confirmation"},
            {"agent": "system_agent", "toolset": "sistema", "risk_level": "low", "channel": "remote", "safety_profile": "remote_blocked"},
        ]
        text = format_axel_brain_insights(history)

        self.assertIn("3 decisoes", text)
        self.assertIn("system_agent 2x", text)
        self.assertIn("remoto 3x", text)
        self.assertIn("bloqueios remotos 1x", text)
        self.assertIn("Recomendacoes:", text)

    def test_brain_recommendations_notice_remote_blocks(self):
        recommendations = axel_brain_recommendations([
            {"safety_profile": "remote_blocked", "risk_level": "low"},
            {"safety_profile": "remote_read_only", "risk_level": "read"},
        ])

        self.assertIn("manter bloqueio remoto ampliado", recommendations[0])

    def test_handles_insights_command(self):
        runtime_state = SimpleNamespace(
            axel_brain_history=[{"intent": "respond", "agent": "conversation_agent"}],
        )

        result = maybe_handle_axel_brain_runtime_command("insights do axelbrain", runtime_state)

        self.assertIsNotNone(result)
        self.assertIn("Insights do AxelBrain", result)

    def test_formats_axel_brain_timeline(self):
        text = format_axel_brain_timeline([
            {
                "source": "turn",
                "input": "fechar spotify",
                "route_group": "system",
                "detector": "detect_close_app",
                "intent": "close_app",
                "agent": "system_agent",
                "toolset": "sistema",
                "risk_level": "high",
                "needs_confirmation": True,
                "action": "close_app",
                "result": "Spotify fechado.",
                "decision": {
                    "intent": "close_app",
                    "agent": "system_agent",
                    "toolset": "sistema",
                    "risk_level": "high",
                    "reason": "comando local de sistema",
                },
                "context": {
                    "source": "turn",
                    "input": "fechar spotify",
                    "route_group": "system",
                    "detector": "detect_close_app",
                    "memory_layers": ["memoria_curta"],
                },
                "execution": {"action": "close_app", "needs_confirmation": True},
                "response": {"final": "Spotify fechado."},
            }
        ])

        self.assertIn("Timeline auditavel do AxelBrain", text)
        self.assertIn("entrada 'fechar spotify'", text)
        self.assertIn("decisao intent close_app", text)
        self.assertIn("motivo comando local de sistema", text)
        self.assertIn("contexto rota system/detect_close_app", text)
        self.assertIn("memoria memoria_curta", text)
        self.assertIn("execucao action close_app", text)
        self.assertIn("confirmacao sim", text)
        self.assertIn("resposta final Spotify fechado.", text)

    def test_formats_legacy_axel_brain_timeline(self):
        text = format_axel_brain_timeline([
            {
                "source": "turn",
                "input": "abrir chrome",
                "route_group": "apps",
                "detector": "detect_open_app",
                "intent": "open_app",
                "agent": "system_agent",
                "toolset": "sistema",
                "risk_level": "low",
                "needs_confirmation": False,
                "action": "open_app",
                "result": "Chrome aberto.",
            }
        ])

        self.assertIn("entrada 'abrir chrome'", text)
        self.assertIn("decisao intent open_app", text)
        self.assertIn("contexto rota apps/detect_open_app", text)
        self.assertIn("resposta final Chrome aberto.", text)

    def test_handles_timeline_command(self):
        runtime_state = SimpleNamespace(
            axel_brain_timeline=[
                {
                    "source": "turn",
                    "input": "briefing",
                    "route_group": "daily",
                    "detector": "detect_daily_briefing",
                    "intent": "daily_briefing",
                    "agent": "daily_agent",
                    "toolset": "rotina",
                    "risk_level": "read",
                    "needs_confirmation": False,
                    "action": "daily_briefing",
                    "result": "Briefing pronto.",
                }
            ]
        )

        result = maybe_handle_axel_brain_runtime_command("timeline do axelbrain", runtime_state)

        self.assertIsNotNone(result)
        self.assertIn("daily_briefing", result)
        self.assertIn("Briefing pronto.", result)

    def test_ignores_unrelated_text(self):
        runtime_state = SimpleNamespace(axel_brain_plan={}, axel_brain_brief={})

        self.assertIsNone(maybe_handle_axel_brain_runtime_command("abrir chrome", runtime_state))

    def test_formats_route_trace(self):
        text = format_axel_route_trace(
            {
                "intent": "vision_answer_question",
                "target": "oq e tesla?",
                "group": "vision",
                "detector": "detect_visual_question_command",
                "intent_level": "pergunta",
                "complexity": "simple_command",
                "checked_detectors": 42,
                "checked_groups": ["fast_path", "screen", "vision"],
            }
        )

        self.assertIn("grupo vision", text)
        self.assertIn("detect_visual_question_command", text)
        self.assertIn("vision_answer_question", text)

    def test_handles_route_trace_command(self):
        runtime_state = SimpleNamespace(
            axel_brain_plan={},
            axel_brain_brief={},
            last_route_trace={
                "intent": "respond",
                "group": "conversation",
                "detector": "detect_ollama_chat",
                "intent_level": "conversa",
                "complexity": "simple_conversation",
            },
        )

        result = maybe_handle_axel_brain_runtime_command("qual detector pegou", runtime_state)

        self.assertIsNotNone(result)
        self.assertIn("detect_ollama_chat", result)


if __name__ == "__main__":
    unittest.main()
