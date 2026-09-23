import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from memory import adaptive_preferences


class AdaptivePreferencesTests(unittest.TestCase):
    def _isolated(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return patch.object(adaptive_preferences, "ADAPTIVE_PREFERENCES_PATH", Path(tmpdir.name) / "adaptive.json")

    def test_learns_suppression_from_natural_training_request(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "ah eu nao quero que voce me avise sobre o treino",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou evitar treino daqui em diante.")
            self.assertTrue(adaptive_preferences.is_adaptive_preference_suppressed("training", text="hora do treino"))

    def test_learns_tomorrow_only_briefing_suppression(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "nao faz briefing amanha",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou evitar briefing amanha.")
            self.assertFalse(
                adaptive_preferences.is_adaptive_preference_suppressed(
                    "briefing",
                    action="run",
                    now=datetime(2026, 7, 24, 12, 0),
                )
            )
            self.assertTrue(
                adaptive_preferences.is_adaptive_preference_suppressed(
                    "briefing",
                    action="run",
                    now=datetime(2026, 7, 25, 9, 0),
                )
            )
            self.assertFalse(
                adaptive_preferences.is_adaptive_preference_suppressed(
                    "briefing",
                    action="run",
                    now=datetime(2026, 7, 26, 9, 0),
                )
            )

    def test_restore_natural_request_disables_suppression(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "nao me avise sobre treino",
                now=datetime(2026, 7, 24, 10, 0),
            )
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "pode voltar a me avisar sobre treino",
                now=datetime(2026, 7, 24, 11, 0),
            )

            self.assertEqual(response, "Entendi. Voltei a permitir treino.")
            self.assertFalse(adaptive_preferences.is_adaptive_preference_suppressed("training", text="hora do treino"))

    def test_ignores_unrelated_text(self):
        with self._isolated():
            self.assertIsNone(adaptive_preferences.maybe_handle_adaptive_preference_request("abrir treino"))

    def test_learns_teacher_tone_for_study_context(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "quando eu estiver estudando, seja mais professor",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou usar tom professor em estudos daqui em diante.")
            adapted = adaptive_preferences.apply_adaptive_response_tone(
                "Vamos revisar redes.",
                "quero estudar redes",
                now=datetime(2026, 7, 24, 10, 1),
            )
            self.assertIn("passo a passo", adapted)

    def test_learns_gym_attendance_tracking_rule(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "estou indo para academia, marque os dias que eu fui",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou usar registro de idas a academia daqui em diante.")
            rules = adaptive_preferences.adaptive_rules_for_domain("training", now=datetime(2026, 7, 24, 10, 1))
            self.assertEqual(rules[0]["kind"], "tracking")
            self.assertEqual(rules[0]["origin"]["source"], "user_natural_language")
            self.assertIn("undo", rules[0])

    def test_important_training_plan_change_creates_pending_candidate(self):
        with self._isolated():
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "vou mandar uma foto da ficha, use ela como meu novo plano",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertIn("mudanca pendente", response)
            self.assertFalse(adaptive_preferences.adaptive_rules_for_domain("training"))
            accepted = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "sim",
                now=datetime(2026, 7, 24, 10, 1),
            )
            self.assertIn("Confirmado", accepted)
            rules = adaptive_preferences.adaptive_rules_for_domain("training", now=datetime(2026, 7, 24, 10, 2))
            self.assertEqual(rules[0]["kind"], "pending_change_accepted")

    def test_natural_undo_disables_last_general_rule(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "quando eu estiver estudando, seja mais professor",
                now=datetime(2026, 7, 24, 10, 0),
            )
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "volta como era",
                now=datetime(2026, 7, 24, 10, 5),
            )

            self.assertEqual(response, "Entendi. Desfiz a regra de tom professor em estudos.")
            self.assertIsNone(
                adaptive_preferences.adaptive_response_tone_instruction(
                    "quero estudar redes",
                    now=datetime(2026, 7, 24, 10, 6),
                )
            )

    def test_explains_last_adaptation_rule_origin_and_undo(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "nao quero que voce me avise sobre treino",
                now=datetime(2026, 7, 24, 10, 0),
            )
            self.assertTrue(
                adaptive_preferences.is_adaptive_preference_suppressed(
                    "training",
                    text="treino",
                    now=datetime(2026, 7, 24, 10, 1),
                )
            )
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "por que voce se adaptou assim?",
                now=datetime(2026, 7, 24, 10, 2),
            )

            self.assertIn("regra 'treino'", response)
            self.assertIn("nao quero que voce me avise sobre treino", response)
            self.assertIn("volta como era", response)

    def test_identity_name_change_requires_confirmation(self):
        with self._isolated():
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "muda seu nome para Atlas",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertIn("mudanca pendente", response)
            self.assertEqual(adaptive_preferences.get_adaptive_assistant_name(), "Axel")

            accepted = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "sim",
                now=datetime(2026, 7, 24, 10, 1),
            )

            self.assertIn("Vou me apresentar como Atlas", accepted)
            self.assertEqual(adaptive_preferences.get_adaptive_assistant_name(now=datetime(2026, 7, 24, 10, 2)), "Atlas")

    def test_briefing_layout_can_remove_section(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "tira o foco do dia do briefing",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou ajustar o briefing: remover foco do dia do briefing.")
            sections = adaptive_preferences.apply_adaptive_briefing_layout(
                [{"id": "agenda", "text": "Agenda."}, {"id": "focus", "text": "Foco do dia."}],
                now=datetime(2026, 7, 24, 10, 1),
            )
            self.assertEqual([section["id"] for section in sections], ["agenda"])

    def test_briefing_focus_stop_request_does_not_fall_to_chat(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "pode parar de me informar sobre o foco do dia",
                now=datetime(2026, 8, 5, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou ajustar o briefing: remover foco do dia do briefing.")
            sections = adaptive_preferences.apply_adaptive_briefing_layout(
                [{"id": "agenda", "text": "Agenda."}, {"id": "focus", "text": "Foco do dia."}],
                now=datetime(2026, 8, 5, 10, 1),
            )
            self.assertEqual([section["id"] for section in sections], ["agenda"])

    def test_briefing_layout_can_move_section_first(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "coloca agenda primeiro no briefing",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou ajustar o briefing: agenda primeiro no briefing.")
            sections = adaptive_preferences.apply_adaptive_briefing_layout(
                [{"id": "climate", "text": "Clima."}, {"id": "agenda", "text": "Agenda."}],
                now=datetime(2026, 7, 24, 10, 1),
            )
            self.assertEqual([section["id"] for section in sections], ["agenda", "climate"])

    def test_briefing_layout_can_add_custom_note(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "adiciona beber agua no briefing",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou ajustar o briefing: adicionar beber agua ao briefing.")
            sections = adaptive_preferences.apply_adaptive_briefing_layout(
                [{"id": "agenda", "text": "Agenda."}],
                now=datetime(2026, 7, 24, 10, 1),
            )
            self.assertEqual(sections[-1]["text"], "beber agua")

    def test_briefing_layout_can_set_complete_order(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "quero o briefing nessa ordem: agenda, clima, carteira, foco",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou ajustar o briefing: ordem do briefing: agenda, clima, carteira, foco do dia.")
            sections = adaptive_preferences.apply_adaptive_briefing_layout(
                [
                    {"id": "greeting", "text": "Bom dia."},
                    {"id": "climate", "text": "Clima."},
                    {"id": "agenda", "text": "Agenda."},
                    {"id": "investments", "text": "Carteira."},
                    {"id": "focus", "text": "Foco."},
                ],
                now=datetime(2026, 7, 24, 10, 1),
            )
            self.assertEqual([section["id"] for section in sections[:4]], ["agenda", "climate", "investments", "focus"])
            self.assertEqual(sections[-1]["id"], "greeting")

    def test_briefing_layout_condition_by_time_of_day(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "de manha tira foco do dia do briefing",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou ajustar o briefing: remover foco do dia do briefing de manha.")
            sections = [{"id": "agenda", "text": "Agenda."}, {"id": "focus", "text": "Foco."}]
            morning = adaptive_preferences.apply_adaptive_briefing_layout(
                sections,
                now=datetime(2026, 7, 25, 8, 0),
            )
            afternoon = adaptive_preferences.apply_adaptive_briefing_layout(
                sections,
                now=datetime(2026, 7, 25, 15, 0),
            )

            self.assertEqual([section["id"] for section in morning], ["agenda"])
            self.assertEqual([section["id"] for section in afternoon], ["agenda", "focus"])

    def test_briefing_layout_stores_context_condition_for_future_consumers(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "quando eu estiver estudando tira radar do briefing",
                now=datetime(2026, 7, 24, 10, 0),
            )

            sections = [{"id": "radar", "text": "Radar."}, {"id": "agenda", "text": "Agenda."}]
            normal = adaptive_preferences.apply_adaptive_briefing_layout(
                sections,
                now=datetime(2026, 7, 25, 8, 0),
            )
            studying = adaptive_preferences.apply_adaptive_briefing_layout(
                sections,
                now=datetime(2026, 7, 25, 8, 0),
                context="studies",
            )

            self.assertEqual([section["id"] for section in normal], ["radar", "agenda"])
            self.assertEqual([section["id"] for section in studying], ["agenda"])

    def test_current_context_learns_and_expires_from_natural_text(self):
        with self._isolated():
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "estou estudando redes agora",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertEqual(response, "Entendi. Vou considerar que voce esta estudando pelas proximas horas.")
            current = adaptive_preferences.get_current_adaptive_context(now=datetime(2026, 7, 24, 10, 1))
            self.assertEqual(current["context"], "studies")
            expired = adaptive_preferences.get_current_adaptive_context(now=datetime(2026, 7, 24, 14, 0))
            self.assertEqual(expired, {})

    def test_current_context_can_be_cleared_naturally(self):
        with self._isolated():
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "estou com pressa",
                now=datetime(2026, 7, 24, 10, 0),
            )
            response = adaptive_preferences.maybe_handle_adaptive_preference_request(
                "sem pressa",
                now=datetime(2026, 7, 24, 10, 5),
            )

            self.assertEqual(response, "Entendi. Nao vou mais considerar que voce esta com pressa agora.")
            self.assertEqual(adaptive_preferences.get_current_adaptive_context(now=datetime(2026, 7, 24, 10, 6)), {})

    def test_briefing_layout_uses_current_context_automatically(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "quando eu estiver estudando tira radar do briefing",
                now=datetime(2026, 7, 24, 9, 0),
            )
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "estou estudando",
                now=datetime(2026, 7, 24, 10, 0),
            )

            sections = adaptive_preferences.apply_adaptive_briefing_layout(
                [{"id": "radar", "text": "Radar."}, {"id": "agenda", "text": "Agenda."}],
                now=datetime(2026, 7, 24, 10, 1),
            )

            self.assertEqual([section["id"] for section in sections], ["agenda"])

    def test_conditional_suppression_uses_current_context(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "quando eu estiver estudando nao me avise sobre treino",
                now=datetime(2026, 7, 24, 9, 0),
            )

            self.assertFalse(
                adaptive_preferences.is_adaptive_preference_suppressed(
                    "training",
                    text="training_reminder",
                    now=datetime(2026, 7, 24, 9, 5),
                )
            )

            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "estou estudando",
                now=datetime(2026, 7, 24, 10, 0),
            )

            self.assertTrue(
                adaptive_preferences.is_adaptive_preference_suppressed(
                    "training",
                    text="training_reminder",
                    now=datetime(2026, 7, 24, 10, 5),
                )
            )

    def test_response_tone_uses_live_study_context(self):
        with self._isolated(), patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "quando eu estiver estudando, seja mais professor",
                now=datetime(2026, 7, 24, 9, 0),
            )
            normal = adaptive_preferences.apply_adaptive_response_tone(
                "Vamos por partes.",
                "me explica isso",
                now=datetime(2026, 7, 24, 9, 5),
            )
            adaptive_preferences.maybe_handle_adaptive_preference_request(
                "estou estudando",
                now=datetime(2026, 7, 24, 10, 0),
            )
            adapted = adaptive_preferences.apply_adaptive_response_tone(
                "Vamos por partes.",
                "me explica isso",
                now=datetime(2026, 7, 24, 10, 5),
            )

            self.assertEqual(normal, "Vamos por partes.")
            self.assertIn("passo a passo", adapted)


if __name__ == "__main__":
    unittest.main()
