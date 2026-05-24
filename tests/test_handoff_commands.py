import unittest
from unittest.mock import patch

from core.handoff_commands import (
    maybe_handle_handoff_application_command,
    maybe_handle_handoff_retry_command,
    maybe_handle_handoff_validation_command,
    maybe_handle_implementation_handoff_command,
)


class HandoffCommandTests(unittest.TestCase):
    def test_prepare_handoff_reports_ready_payload(self):
        with patch(
            "core.handoff_commands.save_implementation_handoff",
            return_value={"status": "ready", "title": "Extrair comandos"},
        ):
            result = maybe_handle_implementation_handoff_command("preparar handoff")

        self.assertEqual(result, "Handoff preparado para o Codex: Extrair comandos. Status: ready.")

    def test_show_handoff_formats_files_and_validation(self):
        with patch(
            "core.handoff_commands.load_implementation_handoff",
            return_value={
                "status": "ready",
                "title": "Extrair comandos",
                "files": ["main.py", "core/commands.py"],
                "validation": ["python -m py_compile main.py", "python -m unittest"],
            },
        ):
            result = maybe_handle_implementation_handoff_command("handoff")

        self.assertEqual(
            result,
            "Handoff do Axel para o Codex: Extrair comandos. Arquivos: main.py, core/commands.py. Validacao: python -m py_compile main.py; python -m unittest.",
        )

    def test_mark_handoff_applied_starts_verification(self):
        with (
            patch(
                "core.handoff_commands.mark_handoff_applied",
                return_value={"status": "applied", "handoff": {"title": "Extrair comandos"}},
            ),
            patch("core.handoff_commands.start_verification", return_value={"status": "pending"}),
        ):
            result = maybe_handle_handoff_application_command("handoff aplicado")

        self.assertEqual(
            result,
            "Registrei o handoff como aplicado: Extrair comandos. Iniciei a verificacao da melhoria.",
        )

    def test_validation_checklist_formats_items(self):
        with patch(
            "core.handoff_commands.save_handoff_validation",
            return_value={
                "status": "ready",
                "title": "Extrair comandos",
                "checklist": ["rodar testes", "testar voz"],
            },
        ):
            result = maybe_handle_handoff_validation_command("validar handoff")

        self.assertEqual(result, "Checklist para validar Extrair comandos: rodar testes; testar voz.")

    def test_retry_plan_can_enqueue_codex_request(self):
        with (
            patch(
                "core.handoff_commands.save_handoff_retry_plan",
                return_value={
                    "status": "ready",
                    "title": "Corrigir validação",
                    "evidence": ["teste falhou"],
                },
            ),
            patch(
                "core.handoff_commands.save_codex_implementation_request",
                return_value={"source": "handoff_retry_plan"},
            ),
        ):
            result = maybe_handle_handoff_retry_command("plano de nova tentativa")

        self.assertEqual(
            result,
            "Plano de nova tentativa pronto para o Codex: Corrigir validação. Principal pista: teste falhou.",
        )


if __name__ == "__main__":
    unittest.main()
