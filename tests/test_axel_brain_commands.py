import unittest
from types import SimpleNamespace

from core.axel_brain_commands import (
    format_axel_brain_runtime_decision,
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
            {"mission": "Ajudar com codigo."},
        )

        self.assertIn("agente dev_agent", text)
        self.assertIn("toolset programacao", text)
        self.assertIn("confianca 82%", text)
        self.assertIn("coordenacao multi_agent_handoff", text)
        self.assertIn("handoff: dev_agent via programacao -> research_agent via pesquisa", text)
        self.assertIn("ferramentas por agente: dev_agent: code_inspect_workspace", text)
        self.assertIn("motivo: toolset por gatilho", text)
        self.assertIn("missao do agente: Ajudar com codigo.", text)

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
            last_route_trace={},
        )

        result = maybe_handle_axel_brain_runtime_command("por que o axel decidiu isso", runtime_state)

        self.assertIsNotNone(result)
        self.assertIn("system_agent", result)
        self.assertIn("sistema", result)

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
