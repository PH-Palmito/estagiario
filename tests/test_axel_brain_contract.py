import unittest

from core.axel_brain_contract import (
    build_axel_brain_contract,
    channel_kind,
    remote_execution_policy,
    remote_permission_summary,
)


class AxelBrainContractTests(unittest.TestCase):
    def test_channel_kind_marks_telegram_as_remote(self):
        self.assertEqual(channel_kind("telegram"), "remote")
        self.assertEqual(channel_kind("turn"), "local")

    def test_remote_policy_allows_safe_read(self):
        policy = remote_execution_policy(
            {"risk_level": "read", "needs_confirmation": False, "response_mode": "answer_with_context"},
            source="telegram",
        )

        self.assertTrue(policy["can_execute"])
        self.assertEqual(policy["decision"], "allow_remote_safe")
        self.assertIn("responder", policy["execution_guidance"])

    def test_remote_policy_blocks_sensitive_action(self):
        policy = remote_execution_policy(
            {"risk_level": "high", "needs_confirmation": True, "response_mode": "confirm_then_act"},
            source="telegram",
        )

        self.assertFalse(policy["can_execute"])
        self.assertEqual(policy["decision"], "block_remote_confirm_on_pc")

    def test_remote_policy_marks_light_media_as_chat_confirmable(self):
        policy = remote_execution_policy(
            {"risk_level": "low", "needs_confirmation": False, "response_mode": "execute_short"},
            source="telegram",
            action_name="browser_search_music",
        )

        self.assertFalse(policy["can_execute"])
        self.assertTrue(policy["can_confirm_remotely"])
        self.assertEqual(policy["decision"], "confirm_remote_light")
        self.assertEqual(policy["safety_profile"], "remote_light_media_confirmation")
        self.assertIn("confirmacao no chat", policy["execution_guidance"])

    def test_remote_policy_allows_safe_reminder_write(self):
        policy = remote_execution_policy(
            {"risk_level": "low", "needs_confirmation": False, "response_mode": "execute_short"},
            source="telegram",
            action_name="reminder_add",
        )

        self.assertTrue(policy["can_execute"])
        self.assertFalse(policy["can_confirm_remotely"])
        self.assertEqual(policy["decision"], "allow_remote_safe_write")
        self.assertEqual(policy["safety_profile"], "remote_safe_write")

    def test_remote_permission_summary_documents_current_limits(self):
        summary = remote_permission_summary()

        self.assertEqual(summary["remote_mode"], "expanded_disabled")
        self.assertIn("volume_mute", summary["confirmable_actions"])
        self.assertIn("reminder_add", summary["safe_write_actions"])
        self.assertTrue(any(item["tier"] == "sensitive_or_write" for item in summary["tiers"]))
        self.assertIn("Somente ampliar", summary["next_review_gate"])

    def test_builds_contract_from_plan_and_brief(self):
        contract = build_axel_brain_contract(
            source="telegram",
            user_input="resuma minha carteira",
            raw_action={"intent": "investment_summary", "target": None},
            plan={
                "agent": "investment_agent",
                "toolset": "carteira",
                "risk_level": "read",
                "needs_confirmation": False,
                "response_mode": "answer_with_context",
                "decision_type": "INFORMATION",
                "capability": "investment_memory_answer",
                "capability_source": "normalizer/actions",
                "model_policy": "grounded_cloud_when_current",
                "coordination_mode": "single_agent",
            },
            brief={
                "brain_version": "2.0",
                "next_step": "Responder usando camadas.",
                "memory_layers": [
                    {"name": "memoria_curta"},
                    {
                        "name": "memoria_profunda",
                        "influences": [
                            {
                                "domain": "investimentos",
                                "section": "projetos_dominios_ativos",
                                "source": "memory/profile.py:financas.estrategia",
                                "scope": "investimentos",
                                "confidence": 0.78,
                                "priority": "media",
                                "reason": "estrategia local",
                                "text": "Watchlist de investimentos: BBAS3",
                            }
                        ],
                    },
                    {"name": "sessoes_relevantes"},
                ],
                "success_criteria": ["resposta curta"],
                "post_task_signals": ["registrar sucesso"],
            },
            route_trace={"group": "investment_questions"},
        )

        self.assertEqual(contract["version"], "2.0")
        self.assertEqual(contract["channel"], "remote")
        self.assertEqual(contract["decision_type"], "INFORMATION")
        self.assertEqual(contract["capability"], "investment_memory_answer")
        self.assertEqual(contract["agent"], "investment_agent")
        self.assertEqual(contract["memory_layers"], ["memoria_curta", "memoria_profunda", "sessoes_relevantes"])
        self.assertEqual(contract["memory_influences"][0]["source"], "memory/profile.py:financas.estrategia")
        self.assertEqual(contract["memory_influences"][0]["domain"], "investimentos")
        self.assertTrue(contract["remote_policy"]["can_execute"])
        self.assertIn("responder", contract["execution_guidance"])


if __name__ == "__main__":
    unittest.main()
