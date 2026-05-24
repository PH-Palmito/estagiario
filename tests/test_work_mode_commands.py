import unittest
from unittest.mock import Mock, patch

from core.work_mode_commands import maybe_handle_work_mode_command


class WorkModeCommandTests(unittest.TestCase):
    def test_unrelated_command_returns_none(self):
        self.assertIsNone(maybe_handle_work_mode_command("abrir spotify", Mock()))

    def test_programming_mode_summarizes_healthy_project(self):
        show_ui = Mock()
        with (
            patch("core.work_mode_commands.update_ui_state") as update_ui,
            patch("core.work_mode_commands.save_auto_advances", return_value=[{"title": "Extrair comandos"}]),
            patch(
                "core.work_mode_commands.save_operational_context",
                return_value={
                    "current_focus": "reduzir main",
                    "next_advances": ["Extrair comandos"],
                    "open_tasks": ["revisar testes"],
                    "active_bottlenecks": [],
                },
            ),
            patch(
                "core.work_mode_commands.run_estagiario_preflight",
                return_value={
                    "compiled_modules": ["main.py", "core/router.py"],
                    "compile_error": "",
                    "json_ok_count": 8,
                    "json_errors": [],
                    "change_summary": "2 arquivos alterados",
                },
            ),
        ):
            result = maybe_handle_work_mode_command("modo dev", show_ui)

        show_ui.assert_called_once_with()
        update_ui.assert_called_once()
        self.assertIn("Modo programacao do Estagiario ativado. Projeto saudavel.", result)
        self.assertIn("Foco atual: reduzir main.", result)
        self.assertIn("Compilacao ok em 2 modulos-chave.", result)
        self.assertIn("Primeiro passo recomendado: Extrair comandos.", result)

    def test_programming_mode_prioritizes_compile_error(self):
        with (
            patch("core.work_mode_commands.update_ui_state"),
            patch("core.work_mode_commands.save_auto_advances", return_value=[]),
            patch("core.work_mode_commands.load_auto_advances", return_value=[]),
            patch("core.work_mode_commands.save_operational_context", return_value={}),
            patch(
                "core.work_mode_commands.run_estagiario_preflight",
                return_value={
                    "compiled_modules": [],
                    "compile_error": "SyntaxError em main.py",
                    "json_ok_count": 0,
                    "json_errors": [],
                    "change_summary": "sem git",
                },
            ),
        ):
            result = maybe_handle_work_mode_command("modo programacao avancado", Mock())

        self.assertIn("Projeto precisa de atencao.", result)
        self.assertIn("Compilacao falhou: SyntaxError em main.py.", result)
        self.assertIn("Primeiro passo recomendado: corrigir a falha de compilacao apontada no pre-flight.", result)

    def test_programming_mode_prioritizes_json_errors_before_advances(self):
        with (
            patch("core.work_mode_commands.update_ui_state"),
            patch("core.work_mode_commands.save_auto_advances", return_value=[{"title": "Nova melhoria"}]),
            patch(
                "core.work_mode_commands.save_operational_context",
                return_value={"next_advances": ["Nova melhoria"], "active_bottlenecks": ["json quebrado"]},
            ),
            patch(
                "core.work_mode_commands.run_estagiario_preflight",
                return_value={
                    "compiled_modules": ["main.py"],
                    "compile_error": "",
                    "json_ok_count": 1,
                    "json_errors": ["memory/ui_state.json: invalid"],
                    "change_summary": "limpo",
                },
            ),
        ):
            result = maybe_handle_work_mode_command("rotina programacao", Mock())

        self.assertIn("Memorias com erro: memory/ui_state.json: invalid.", result)
        self.assertIn("Gargalos: json quebrado.", result)
        self.assertIn("Primeiro passo recomendado: corrigir o JSON invalido antes de evoluir recursos.", result)


if __name__ == "__main__":
    unittest.main()
