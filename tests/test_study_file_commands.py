import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from core.study_commands import maybe_handle_study_command
from memory.study_context import clear_study_context, load_study_context, save_study_context


class StudyFileCommandTests(unittest.TestCase):
    def setUp(self):
        self._study_context_backup = load_study_context()

    def tearDown(self):
        if self._study_context_backup:
            save_study_context(self._study_context_backup)
        else:
            clear_study_context()

    def test_study_command_analyzes_attached_files(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tema.txt"
            path.write_text("Ecossistemas dependem de fluxo de energia e ciclos da materia.", encoding="utf-8")
            show_hud = Mock(return_value="hud")

            with patch("core.study_commands.study_snapshot", return_value={}), patch(
                "core.study_commands.update_ui_state"
            ) as update_ui:
                result = maybe_handle_study_command(
                    f"analisar arquivos anexados: {json.dumps([str(path)])} :: gere questoes",
                    show_hud,
                )

        self.assertIn("Análise de estudo dos arquivos", result)
        self.assertIn("Questões para praticar", result)
        show_hud.assert_not_called()
        update_ui.assert_called_once_with({"study_snapshot": {}})

    def test_general_file_analysis_does_not_open_study_panel(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cv.txt"
            path.write_text(
                "Pedro Henrique Bispo Palmito Objetivo Acadêmico de Engenharia de Software "
                "com foco em Desenvolvimento Mobile. Tecnologias React Native, Supabase e Git.",
                encoding="utf-8",
            )
            show_hud = Mock(return_value="hud")

            with patch("core.study_commands.update_ui_state") as update_ui:
                result = maybe_handle_study_command(
                    f"analisar arquivos anexados: {json.dumps([str(path)])} :: oque tem nesse pdf",
                    show_hud,
                )

        self.assertIn("Análise dos arquivos", result)
        self.assertNotIn("Pedido considerado", result)
        show_hud.assert_not_called()
        update_ui.assert_not_called()

    def test_study_command_blocks_corrupted_analysis_response(self):
        corrupted = (
            "Analise de estudo dos arquivos: 1. questoes.pdf: - "
            "T m s t m s m Q u i t q l i l m l m S o n t w i r m "
            "Qumstao ciqxi quivtos cisos lm tmstm couxtmx trivsn qvvat."
        )

        with patch("core.study_commands.analyze_study_files", return_value=corrupted):
            result = maybe_handle_study_command(
                'analisar arquivos anexados: ["C:/fake/questoes.pdf"] :: resuma',
                Mock(return_value="hud"),
            )

        self.assertIn("verificação de confiança", result)
        self.assertNotIn("T m s t m s", result)

    def test_study_command_handles_followup_before_general_routing(self):
        with patch("core.study_commands.answer_study_followup", return_value="Resposta da questao 1."), patch(
            "core.study_commands.study_snapshot", return_value={}
        ), patch("core.study_commands.update_ui_state"):
            result = maybe_handle_study_command("pode responder a questao 1?", Mock(return_value="hud"))

        self.assertEqual(result, "Resposta da questão 1.")

    def test_page_question_uses_followup_instead_of_file_search(self):
        with patch("core.study_commands.parse_study_file_command", return_value=None) as parse_command, patch(
            "core.study_commands.answer_study_followup", return_value="Na pÃ¡gina 2 de RedesBasico.pdf: Comunicacao Digital."
        ) as followup, patch("core.study_commands.study_snapshot", return_value={}), patch("core.study_commands.update_ui_state"):
            result = maybe_handle_study_command("oq tem na pagina 2?", Mock(return_value="hud"))

        parse_command.assert_called_once()
        followup.assert_called_once_with("oq tem na pagina 2?")
        self.assertIn("RedesBasico.pdf", result)

    def test_self_test_current_file_does_not_open_study_panel(self):
        fake_context = {
            "files": [
                {
                    "path": "C:/fake/RedesBasico.pdf",
                    "name": "RedesBasico.pdf",
                    "kind": "pdf",
                    "text": "Redes de Computadores Comunicacao Digital Conceitos Basicos",
                    "raw_text": "Redes de Computadores Comunicacao Digital Conceitos Basicos",
                    "topic": "Redes de Computadores",
                    "pages": [
                        {"index": 1, "text": "Redes de Computadores"},
                        {"index": 2, "text": "Comunicacao Digital"},
                    ],
                }
            ]
        }
        show_hud = Mock(return_value="hud")

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context), patch(
            "core.study_commands.study_snapshot", return_value={}
        ), patch("core.study_commands.update_ui_state") as update_ui:
            result = maybe_handle_study_command("testar arquivo atual", show_hud)

        self.assertIn("Auto teste do arquivo atual: RedesBasico.pdf", result)
        self.assertIn("pagina 2", result)
        self.assertIn("bananas", result)
        show_hud.assert_not_called()
        update_ui.assert_called_once_with({"study_snapshot": {}})

    def test_general_file_followup_does_not_refresh_study_panel(self):
        save_study_context(
            {
                "files": [
                    {
                        "path": "C:/fake/cv Pedro.docx",
                        "name": "cv Pedro.docx",
                        "kind": "docx",
                        "text": "Pedro Henrique Objetivo Academico Engenharia de Software React Native Supabase Git.",
                        "raw_text": "Pedro Henrique Objetivo Academico Engenharia de Software React Native Supabase Git.",
                        "topic": "curriculo profissional",
                    }
                ],
                "current_file_path": "C:/fake/cv Pedro.docx",
                "last_file_path": "C:/fake/cv Pedro.docx",
            }
        )

        with patch("core.study_commands.update_ui_state") as update_ui:
            result = maybe_handle_study_command("o arquivo fala sobre React?", Mock(return_value="hud"))

        self.assertIn("react", result.lower())
        update_ui.assert_not_called()

    def test_study_file_followup_refreshes_study_snapshot_without_opening_panel(self):
        save_study_context(
            {
                "files": [
                    {
                        "path": "C:/fake/RedesBasico.pdf",
                        "name": "RedesBasico.pdf",
                        "kind": "pdf",
                        "text": "Redes de Computadores Comunicacao Digital Conceitos Basicos Professor Marco Antonio.",
                        "raw_text": "Redes de Computadores Comunicacao Digital Conceitos Basicos Professor Marco Antonio.",
                        "topic": "Redes de Computadores",
                    }
                ],
                "current_file_path": "C:/fake/RedesBasico.pdf",
                "last_file_path": "C:/fake/RedesBasico.pdf",
            }
        )

        with patch("core.study_commands.study_snapshot", return_value={}), patch(
            "core.study_commands.update_ui_state"
        ) as update_ui:
            result = maybe_handle_study_command("o arquivo fala sobre bananas?", Mock(return_value="hud"))

        self.assertIn("bananas", result)
        update_ui.assert_called_once_with({"study_snapshot": {}})

    def test_general_file_self_test_does_not_refresh_study_panel(self):
        save_study_context(
            {
                "files": [
                    {
                        "path": "C:/fake/README_CineRadar.md",
                        "name": "README_CineRadar.md",
                        "kind": "text",
                        "text": "Sobre o projeto CineRadar. Como executar o projeto. Tecnologias utilizadas.",
                        "raw_text": "Sobre o projeto CineRadar. Como executar o projeto. Tecnologias utilizadas.",
                        "topic": "projeto CineRadar",
                        "pages": [],
                    }
                ],
                "current_file_path": "C:/fake/README_CineRadar.md",
                "last_file_path": "C:/fake/README_CineRadar.md",
            }
        )

        with patch("core.study_commands.update_ui_state") as update_ui:
            result = maybe_handle_study_command("testar arquivo atual", Mock(return_value="hud"))

        self.assertIn("Auto teste do arquivo atual: README_CineRadar.md", result)
        update_ui.assert_not_called()

    def test_file_context_does_not_steal_general_background_commands(self):
        save_study_context(
            {
                "files": [
                    {
                        "path": "C:/fake/RedesBasico.pdf",
                        "name": "RedesBasico.pdf",
                        "text": "Redes de Computadores Comunicacao Digital",
                        "raw_text": "Redes de Computadores Comunicacao Digital",
                        "topic": "Redes de Computadores",
                    }
                ]
            }
        )

        self.assertIsNone(maybe_handle_study_command("status das tarefas em segundo plano", Mock(return_value="hud")))
        self.assertIsNone(maybe_handle_study_command("resuma a tela", Mock(return_value="hud")))
        self.assertIsNone(maybe_handle_study_command("o que tem na tela?", Mock(return_value="hud")))
        self.assertIsNone(maybe_handle_study_command("analisar grafico", Mock(return_value="hud")))
        self.assertIsNone(maybe_handle_study_command("leia arquivo teste.txt", Mock(return_value="hud")))

    def test_file_context_does_not_steal_general_study_help_request(self):
        save_study_context(
            {
                "files": [
                    {
                        "path": "C:/fake/clinicas.html",
                        "name": "clinicas.html",
                        "text": "Cadastro de clinicas e pacientes.",
                        "raw_text": "Cadastro de clinicas e pacientes.",
                        "topic": "clinicas",
                    }
                ]
            }
        )

        self.assertIsNone(maybe_handle_study_command("pode me ajudar a estudar redes?", Mock(return_value="hud")))

    def test_file_context_still_answers_file_followups(self):
        save_study_context(
            {
                "files": [
                    {
                        "path": "C:/fake/RedesBasico.pdf",
                        "name": "RedesBasico.pdf",
                        "text": "Redes de Computadores Comunicacao Digital",
                        "raw_text": "Redes de Computadores Comunicacao Digital",
                        "topic": "Redes de Computadores",
                        "pages": [{"index": 2, "text": "Agenda de Redes de Computadores"}],
                    }
                ]
            }
        )

        self.assertIn("página 2", maybe_handle_study_command("oq tem na pagina 2?", Mock(return_value="hud")))
        self.assertIn("bananas", maybe_handle_study_command("o arquivo fala sobre bananas?", Mock(return_value="hud")))


if __name__ == "__main__":
    unittest.main()
