import unittest
from unittest.mock import patch

from core.supervised_execution_commands import (
    maybe_handle_action_candidate_command,
    maybe_handle_execution_package_command,
)


class SupervisedExecutionCommandTests(unittest.TestCase):
    def test_action_candidate_list_formats_status_and_files(self):
        with patch(
            "core.supervised_execution_commands.load_action_candidates",
            return_value=[
                {
                    "title": "Extrair handoff",
                    "status": "pending",
                    "files": ["main.py", "core/handoff.py"],
                }
            ],
        ):
            result = maybe_handle_action_candidate_command("acoes candidatas")

        self.assertEqual(
            result,
            "Acoes candidatas: 1. Extrair handoff. Status: pending. Alvos: main.py, core/handoff.py",
        )

    def test_approve_action_candidate_reports_title(self):
        with patch(
            "core.supervised_execution_commands.approve_first_action_candidate",
            return_value={"title": "Criar painel de saude"},
        ):
            result = maybe_handle_action_candidate_command("aprovar acao candidata")

        self.assertEqual(
            result,
            "Acao candidata aprovada: Criar painel de saude. Ainda nao executei; deixei pronta para aplicacao supervisionada.",
        )

    def test_approve_next_advance_prepares_full_chain(self):
        with (
            patch(
                "core.supervised_execution_commands.approve_current_proposal",
                return_value={"proposal": {"title": "Refinar roteador"}},
            ),
            patch(
                "core.supervised_execution_commands.approve_first_action_candidate",
                return_value={"title": "Extrair roteador"},
            ),
            patch(
                "core.supervised_execution_commands.save_execution_package",
                return_value={"status": "ready_for_codex"},
            ),
            patch(
                "core.supervised_execution_commands.save_implementation_handoff",
                return_value={"status": "ready"},
            ),
            patch("core.supervised_execution_commands.sync_handoff_application"),
            patch(
                "core.supervised_execution_commands.save_codex_implementation_request",
                return_value={"status": "queued"},
            ),
        ):
            result = maybe_handle_action_candidate_command("aprovar proximo avanco")

        self.assertEqual(
            result,
            "Aprovei e preparei o proximo avanco: Extrair roteador. Pacote: ready_for_codex; handoff: ready; pedido ao Codex: queued.",
        )

    def test_execution_package_waiting_for_approval(self):
        with patch(
            "core.supervised_execution_commands.save_execution_package",
            return_value={"status": "waiting_for_approval", "title": ""},
        ):
            result = maybe_handle_execution_package_command("gerar pacote de execucao")

        self.assertEqual(result, "Ainda nao ha acao candidata aprovada para montar pacote de execucao.")

    def test_execution_package_list_formats_validation(self):
        with patch(
            "core.supervised_execution_commands.load_execution_package",
            return_value={
                "status": "ready_for_codex",
                "title": "Extrair comandos",
                "files": ["main.py", "core/commands.py"],
                "validation": ["python -m py_compile main.py", "python -m unittest"],
            },
        ):
            result = maybe_handle_execution_package_command("pacote de execucao")

        self.assertEqual(
            result,
            "Pacote de execucao: Extrair comandos. Status: ready_for_codex. Arquivos: main.py, core/commands.py. Validacao: python -m py_compile main.py; python -m unittest.",
        )


if __name__ == "__main__":
    unittest.main()
