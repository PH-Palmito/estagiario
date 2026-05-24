import unittest
from unittest.mock import patch

from core.approval_verification_commands import (
    maybe_handle_approval_gate_command,
    maybe_handle_verification_command,
)


class ApprovalVerificationCommandTests(unittest.TestCase):
    def test_show_current_proposal_formats_files(self):
        with patch(
            "core.approval_verification_commands.load_approval_gate",
            return_value={
                "status": "pending",
                "proposal": {
                    "title": "Extrair verificacao",
                    "files": ["main.py", "core/approval.py"],
                },
            },
        ):
            result = maybe_handle_approval_gate_command("proposta atual")

        self.assertEqual(
            result,
            "Proposta atual: Extrair verificacao. Status: pending. Arquivos alvo: main.py, core/approval.py.",
        )

    def test_approve_current_proposal_reports_title(self):
        with patch(
            "core.approval_verification_commands.approve_current_proposal",
            return_value={"proposal": {"title": "Criar contratos de roteador"}},
        ):
            result = maybe_handle_approval_gate_command("aprovar proposta")

        self.assertEqual(
            result,
            "Proposta aprovada. O Axel pode levar ao Codex esta melhoria: Criar contratos de roteador.",
        )

    def test_start_verification_requires_approved_proposal(self):
        with patch(
            "core.approval_verification_commands.start_verification",
            return_value={"approval_status": "pending", "proposal": {"title": "Extrair modulo"}},
        ):
            result = maybe_handle_verification_command("iniciar verificacao")

        self.assertEqual(result, "Ainda nao ha uma proposta aprovada para verificar.")

    def test_start_verification_formats_checklist(self):
        with patch(
            "core.approval_verification_commands.start_verification",
            return_value={
                "approval_status": "approved",
                "proposal": {"title": "Extrair modulo"},
                "checklist": ["Compilar", "Rodar testes", "Validar fluxo"],
            },
        ):
            result = maybe_handle_verification_command("iniciar verificacao")

        self.assertEqual(
            result,
            "Verificacao iniciada para Extrair modulo. Checklist: Compilar; Rodar testes; Validar fluxo.",
        )

    def test_failed_verification_can_replan(self):
        with (
            patch(
                "core.approval_verification_commands.load_verification_runs",
                return_value={"status": "failed", "proposal": {"title": "Extrair modulo"}},
            ),
            patch("core.approval_verification_commands.save_patch_proposals") as save_patch,
            patch("core.approval_verification_commands.save_auto_advances") as save_advances,
            patch("core.approval_verification_commands.save_codex_request") as save_request,
        ):
            result = maybe_handle_verification_command("aprender da falha")

        self.assertEqual(
            result,
            "Perfeito. O Axel replanejou a melhoria apos a falha de verificacao em Extrair modulo.",
        )
        save_patch.assert_called_once_with()
        save_advances.assert_called_once_with()
        save_request.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
