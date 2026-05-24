import unittest
from unittest.mock import patch

from core.directives_commands import maybe_handle_directives_command


class DirectivesCommandTests(unittest.TestCase):
    def test_unknown_command_returns_none(self):
        self.assertIsNone(maybe_handle_directives_command("abrir spotify"))

    def test_show_core_directives_formats_first_items(self):
        with patch(
            "core.directives_commands.load_axel_directives",
            return_value={
                "core_directives": [
                    "Priorizar utilidade real.",
                    "Pedir confirmacao em acoes sensiveis.",
                    "Ser honesto sobre limitacoes.",
                    "Melhorar por ciclos pequenos.",
                    "Nao incluir a quinta.",
                ]
            },
        ):
            result = maybe_handle_directives_command("diretrizes do axel")

        self.assertEqual(
            result,
            "Diretrizes do Axel: Priorizar utilidade real.; Pedir confirmacao em acoes sensiveis.; Ser honesto sobre limitacoes.; Melhorar por ciclos pequenos..",
        )

    def test_investment_mode_short_help_does_not_require_rules(self):
        with patch("core.directives_commands.load_axel_directives", return_value={"core_directives": []}):
            result = maybe_handle_directives_command("modo investimentos")

        self.assertEqual(
            result,
            "Modo investimentos pronto para leitura de tela. Abra sua carteira ou ativo e diga: analisar investimentos, resumo financeiro ou analisar carteira.",
        )

    def test_investment_directives_include_goal_and_rules(self):
        with patch(
            "core.directives_commands.load_axel_directives",
            return_value={
                "investment_mode": {
                    "goal": "Acompanhar carteira sem prometer resultado.",
                    "rules": ["Separar fato e opiniao.", "Buscar dados atuais.", "Explicar risco.", "Quarta regra."],
                }
            },
        ):
            result = maybe_handle_directives_command("base do modo investimentos")

        self.assertEqual(
            result,
            "Modo investimentos preparado. Acompanhar carteira sem prometer resultado. Regras: Separar fato e opiniao.; Buscar dados atuais.; Explicar risco..",
        )

    def test_empty_payload_reports_load_failure(self):
        with patch("core.directives_commands.load_axel_directives", return_value={}):
            result = maybe_handle_directives_command("diretrizes")

        self.assertEqual(result, "Ainda nao consegui carregar minhas diretrizes.")


if __name__ == "__main__":
    unittest.main()
