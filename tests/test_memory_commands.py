import unittest
from unittest.mock import patch

from core.memory_commands import maybe_handle_long_memory_command, maybe_handle_operational_context_command


class MemoryCommandTests(unittest.TestCase):
    def test_remember_operational_preference_keeps_tail(self):
        with patch(
            "core.memory_commands.remember_operational_preference",
            return_value="Preferencia operacional salva: falar curto.",
        ) as remember:
            result = maybe_handle_operational_context_command(
                "lembre na memoria operacional que falar curto"
            )

        self.assertEqual(result, "Preferencia operacional salva: falar curto.")
        remember.assert_called_once_with("falar curto", kind="preference")

    def test_note_operational_context(self):
        with patch(
            "core.memory_commands.remember_operational_preference",
            return_value="Anotei no contexto operacional: foco em testes.",
        ) as remember:
            result = maybe_handle_operational_context_command("registre no contexto operacional foco em testes")

        self.assertEqual(result, "Anotei no contexto operacional: foco em testes.")
        remember.assert_called_once_with("foco em testes", kind="note")

    def test_recent_apps_formats_context_payload(self):
        with patch(
            "core.memory_commands.save_operational_context",
            return_value={"recent_apps": ["chrome", "spotify"], "recent_sites": [], "recent_topics": []},
        ):
            result = maybe_handle_operational_context_command("apps recentes")

        self.assertEqual(result, "Apps recentes: chrome, spotify.")

    def test_update_context_includes_summary(self):
        with patch(
            "core.memory_commands.save_operational_context",
            return_value={"summary": "Axel acompanhando operador."},
        ):
            result = maybe_handle_operational_context_command("atualizar contexto")

        self.assertEqual(result, "Contexto operacional atualizado. Axel acompanhando operador.")

    def test_show_long_memory(self):
        with patch("core.memory_commands.format_long_memory", return_value="Memoria longa: project: Axel."):
            result = maybe_handle_long_memory_command("mostrar memoria longa")

        self.assertEqual(result, "Memoria longa: project: Axel.")

    def test_curate_long_memory_reports_added_items(self):
        with (
            patch("core.memory_commands.curate_recent_ui_history", return_value=2),
            patch("core.memory_commands.save_operational_context"),
        ):
            result = maybe_handle_long_memory_command("curar memoria longa")

        self.assertEqual(result, "Memoria longa curada. Adicionei 2 item(ns) duraveis.")

    def test_manual_long_memory_save(self):
        with (
            patch("core.memory_commands.maybe_remember_from_user_text", return_value=True) as remember,
            patch("core.memory_commands.save_operational_context"),
        ):
            result = maybe_handle_long_memory_command("lembre na memoria longa que priorizamos modularizacao")

        self.assertEqual(result, "Memoria longa atualizada.")
        remember.assert_called_once_with(
            "lembre que priorizamos modularizacao",
            source="manual-long-memory",
        )


if __name__ == "__main__":
    unittest.main()
