import unittest
from unittest.mock import patch

from core.evolution_commands import (
    maybe_handle_auto_advance_command,
    maybe_handle_bottleneck_command,
    maybe_handle_patch_proposal_command,
)


class EvolutionCommandTests(unittest.TestCase):
    def test_auto_advance_update_uses_saved_items(self):
        with patch(
            "core.evolution_commands.save_auto_advances",
            return_value=[{"title": "Extrair handlers"}, {"title": "Criar dashboard"}],
        ):
            result = maybe_handle_auto_advance_command("gerar proximos avancos")

        self.assertIn("Atualizei os proximos avancos", result)
        self.assertIn("Extrair handlers", result)
        self.assertIn("Criar dashboard", result)

    def test_auto_advance_list_formats_loaded_items(self):
        with patch(
            "core.evolution_commands.load_auto_advances",
            return_value=[{"title": "Revisar voz"}, {"title": "Melhorar browser"}],
        ):
            result = maybe_handle_auto_advance_command("proximos avancos")

        self.assertEqual(result, "Proximos avancos do Axel: 1. Revisar voz; 2. Melhorar browser")

    def test_bottleneck_list_formats_counts(self):
        with patch(
            "core.evolution_commands.load_bottlenecks",
            return_value=[{"title": "Entendimento de voz instavel", "count": 3}],
        ):
            result = maybe_handle_bottleneck_command("gargalos")

        self.assertEqual(result, "Gargalos detectados: Entendimento de voz instavel (3)")

    def test_patch_proposals_list_formats_files(self):
        with patch(
            "core.evolution_commands.load_patch_proposals",
            return_value=[{"title": "Melhorar leitura de tela", "files": ["tools/browser_tools.py", "main.py"]}],
        ):
            result = maybe_handle_patch_proposal_command("propostas de patch")

        self.assertEqual(result, "Propostas de patch do Axel: Melhorar leitura de tela em tools/browser_tools.py, main.py")

    def test_unknown_evolution_command_returns_none(self):
        self.assertIsNone(maybe_handle_auto_advance_command("abrir spotify"))
        self.assertIsNone(maybe_handle_bottleneck_command("abrir spotify"))
        self.assertIsNone(maybe_handle_patch_proposal_command("abrir spotify"))


if __name__ == "__main__":
    unittest.main()
