import unittest
from unittest.mock import patch

from core.self_evolution_commands import maybe_handle_self_evolution_command

PLAN = {
    "current_focus": "Reduzir main.py",
    "steps": [
        {"status": "done", "title": "HUD operacional"},
        {"status": "next", "title": "Extrair comandos", "reason": "main.py ainda concentra fluxo"},
        {"status": "planned", "title": "Validar no uso"},
    ],
}


class SelfEvolutionCommandTests(unittest.TestCase):
    def test_show_plan_formats_focus_and_first_steps(self):
        with patch("core.self_evolution_commands.load_self_evolution_plan", return_value=PLAN):
            result = maybe_handle_self_evolution_command("plano de auto evolucao")

        self.assertEqual(
            result,
            "Foco atual: Reduzir main.py. Plano de auto evolucao do Axel: done: HUD operacional; next: Extrair comandos; planned: Validar no uso",
        )

    def test_empty_plan_reports_missing_plan(self):
        with patch("core.self_evolution_commands.load_self_evolution_plan", return_value={"steps": []}):
            result = maybe_handle_self_evolution_command("auto evolucao")

        self.assertEqual(result, "Ainda nao consegui montar um plano de auto evolucao.")

    def test_progress_counts_steps_and_next_item(self):
        with patch("core.self_evolution_commands.save_self_evolution_plan", return_value=PLAN):
            result = maybe_handle_self_evolution_command("status da auto evolucao")

        self.assertEqual(
            result,
            "Auto evolucao do Axel: 1/3 passos concluidos. Faltam 2; 1 ainda planejados. Proximo passo: Extrair comandos.",
        )

    def test_missing_steps_lists_not_done_items(self):
        with patch("core.self_evolution_commands.save_self_evolution_plan", return_value=PLAN):
            result = maybe_handle_self_evolution_command("passos restantes")

        self.assertEqual(
            result,
            "Passos faltantes: 1. next: Extrair comandos; 2. planned: Validar no uso",
        )

    def test_next_step_uses_reason(self):
        with patch("core.self_evolution_commands.save_self_evolution_plan", return_value=PLAN):
            result = maybe_handle_self_evolution_command("proximo passo da auto evolucao")

        self.assertEqual(
            result,
            "Proximo passo da auto evolucao: Extrair comandos. Motivo: main.py ainda concentra fluxo",
        )

    def test_update_plan_reports_focus(self):
        with patch(
            "core.self_evolution_commands.save_self_evolution_plan",
            return_value={"current_focus": "Testar contratos", "steps": []},
        ):
            result = maybe_handle_self_evolution_command("atualizar plano de auto evolucao")

        self.assertEqual(result, "Atualizei o plano de auto evolucao. Foco atual: Testar contratos.")


if __name__ == "__main__":
    unittest.main()
