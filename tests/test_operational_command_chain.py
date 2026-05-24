import unittest
from unittest.mock import patch

from core.operational_command_chain import maybe_handle_operational_command


class OperationalCommandChainTests(unittest.TestCase):
    @patch("core.operational_command_chain.maybe_handle_auto_advance_command", return_value="Auto avanco pronto.")
    def test_auto_advance_refreshes_and_announces(self, _handler):
        result = maybe_handle_operational_command("auto evolucao")

        self.assertIsNotNone(result)
        self.assertEqual(result.response, "Auto avanco pronto.")
        self.assertTrue(result.refresh_improvement_brain)
        self.assertTrue(result.announce_codex_suggestion)

    @patch("core.operational_command_chain.maybe_handle_directives_command", return_value="Diretriz registrada.")
    def test_directives_do_not_announce_codex(self, _handler):
        result = maybe_handle_operational_command("diretriz nova")

        self.assertIsNotNone(result)
        self.assertEqual(result.response, "Diretriz registrada.")
        self.assertFalse(result.refresh_improvement_brain)
        self.assertFalse(result.announce_codex_suggestion)

    @patch("core.operational_command_chain.maybe_handle_auto_advance_command", return_value=None)
    @patch("core.operational_command_chain.maybe_handle_bottleneck_command", return_value="Gargalo registrado.")
    def test_stops_at_first_response(self, bottleneck_handler, auto_handler):
        result = maybe_handle_operational_command("registrar gargalo")

        self.assertEqual(result.response, "Gargalo registrado.")
        auto_handler.assert_called_once()
        bottleneck_handler.assert_called_once()


if __name__ == "__main__":
    unittest.main()
