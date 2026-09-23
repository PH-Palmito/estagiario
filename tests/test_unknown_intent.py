import unittest
from unittest.mock import Mock, patch

from core.axel_brain_contract import build_axel_brain_contract
from core.decision_orchestrator import build_decision_plan
from core.normalizer import normalize_action
from core.permission_policy import command_requires_confirmation
from core.router_registry import INTENT_LEVEL_CONVERSATION, INTENT_LEVEL_DIRECT_COMMAND
from core.unknown_intent import action_from_unknown_intent, interpret_unknown_intent
from services import telegram_gateway


class UnknownIntentTests(unittest.TestCase):
    def test_rephrased_music_request_finds_existing_capability(self):
        action = action_from_unknown_intent("quero ouvir alguma coisa")

        self.assertEqual(action["intent"], "browser_surprise_music")
        self.assertEqual(action["__decision_type"], "KNOWN_CAPABILITY")
        self.assertEqual(action["__capability"], "browser_surprise_music")
        command = normalize_action(action)
        self.assertEqual(command.action, "browser_surprise_music")

    def test_information_market_question_uses_investment_capability(self):
        action = action_from_unknown_intent("ve se aconteceu alguma coisa importante no mercado hoje")
        plan = build_decision_plan(
            "ve se aconteceu alguma coisa importante no mercado hoje",
            action,
            intent_level=INTENT_LEVEL_CONVERSATION,
        )

        self.assertEqual(action["intent"], "investment_memory_answer")
        self.assertEqual(plan.decision_type, "INFORMATION")
        self.assertEqual(plan.capability, "investment_memory_answer")
        self.assertEqual(plan.response_mode, "conversational")

    def test_planning_request_does_not_execute_plan(self):
        action = action_from_unknown_intent("me ajuda a organizar meus estudos")
        plan = build_decision_plan(
            "me ajuda a organizar meus estudos",
            action,
            intent_level=INTENT_LEVEL_CONVERSATION,
        )

        self.assertEqual(action["intent"], "respond")
        self.assertEqual(plan.decision_type, "PLANNING")
        self.assertIn("planejamento", action["response"])

    def test_ambiguous_desktop_organization_requests_clarification(self):
        interpretation = interpret_unknown_intent("organiza minha area de trabalho")

        self.assertEqual(interpretation.decision_type, "CLARIFICATION")
        self.assertEqual(interpretation.raw_action["intent"], "respond")
        self.assertIn("janelas", interpretation.raw_action["response"])
        self.assertIn("arquivos", interpretation.raw_action["response"])

    def test_missing_capability_does_not_invent_action(self):
        action = action_from_unknown_intent("faca teletransporte quantico do meu monitor")

        self.assertEqual(action["intent"], "respond")
        self.assertEqual(action["__decision_type"], "UNKNOWN")
        self.assertIn("nao tenho capacidade", action["response"].lower())

    def test_broad_dangerous_file_request_is_blocked_before_execution(self):
        action = action_from_unknown_intent("apague todos os meus arquivos")
        command = normalize_action(action)

        self.assertEqual(command.action, "respond")
        self.assertFalse(command_requires_confirmation(command))
        self.assertEqual(action["__decision_type"], "BLOCKED")
        self.assertIn("Bloqueei esse pedido", action["response"])
        plan = build_decision_plan(
            "apague todos os meus arquivos",
            action,
            intent_level=INTENT_LEVEL_DIRECT_COMMAND,
        )
        self.assertEqual(plan.decision_type, "BLOCKED")
        self.assertFalse(plan.needs_confirmation)

    def test_remote_semantic_music_does_not_bypass_telegram_confirmation(self):
        fake_trace = Mock()
        fake_trace.match = None
        fake_trace.checked_detectors = 99
        fake_trace.checked_groups = ["fast_path", "conversation"]
        with patch.object(telegram_gateway, "route_trace", return_value=fake_trace):
            result = telegram_gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "quero ouvir alguma coisa"}},
                allowed_chat_ids={"123"},
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "confirmation_required")
        self.assertEqual(result.action, "browser_surprise_music")
        self.assertEqual(result.contract["decision_type"], "KNOWN_CAPABILITY")
        self.assertEqual(result.contract["remote_policy"]["decision"], "confirm_remote_light")

    def test_contract_exposes_semantic_fallback_metadata(self):
        action = action_from_unknown_intent("organiza minha area de trabalho")
        plan = build_decision_plan(
            "organiza minha area de trabalho",
            action,
            intent_level=INTENT_LEVEL_CONVERSATION,
        )
        contract = build_axel_brain_contract(
            source="turn",
            user_input="organiza minha area de trabalho",
            raw_action=action,
            plan=plan,
            brief={"brain_version": "2.0", "memory_layers": []},
            route_trace={"intent": action["intent"]},
        )

        self.assertEqual(contract["decision_type"], "CLARIFICATION")
        self.assertEqual(contract["capability"], "organizacao de ambiente")
        self.assertEqual(contract["semantic_fallback"]["reason"], "pedido de organizacao tem multiplas interpretacoes plausiveis")


if __name__ == "__main__":
    unittest.main()
