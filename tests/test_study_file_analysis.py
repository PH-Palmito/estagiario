import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

from core.study_file_analysis import analyze_study_files, answer_study_followup, parse_study_file_command
from file_processor.extractors import _extract_pdf_text_ocr, extract_pdf
from file_processor.processor import process_file


def write_minimal_pptx(path: Path, slide_texts: list[str]) -> None:
    with ZipFile(path, "w") as archive:
        for index, text in enumerate(slide_texts, start=1):
            archive.writestr(
                f"ppt/slides/slide{index}.xml",
                f"""<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>""",
            )


class StudyFileAnalysisTests(unittest.TestCase):
    def test_parse_attached_file_command_with_json_paths(self):
        result = parse_study_file_command(
            'analisar arquivos anexados: ["C:/a/aula.pptx","C:/a/resumo.pdf"] :: gere questoes'
        )

        self.assertEqual(result, (["C:/a/aula.pptx", "C:/a/resumo.pdf"], "gere questoes"))

    def test_process_file_extracts_pptx_slide_text(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "aula.pptx"
            write_minimal_pptx(path, ["Fotossintese transforma luz em energia", "Clorofila absorve luz"])

            result = process_file(str(path))

        self.assertTrue(result["ok"])
        self.assertEqual(result["file"]["kind"], "presentation")
        self.assertIn("Slide 1", result["extracted"]["text"])
        self.assertEqual(result["extracted"]["slide_count"], 2)

    def test_analyze_study_files_summarizes_and_generates_questions(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tema.txt"
            path.write_text(
                "A mitose divide uma celula em duas celulas geneticamente identicas.\n"
                "A meiose forma gametas e reduz pela metade o numero de cromossomos.\n",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="crie questoes")

        self.assertIn("Analise de estudo dos arquivos", result)
        self.assertIn("tema.txt", result)
        self.assertIn("Questoes para praticar", result)
        self.assertIn("mitose", result.lower())

    def test_analyze_study_files_answers_about_request_without_practice_questions(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "questoes.txt"
            path.write_text(
                "Testes e Qualidade de Software - Lista de exercicios. "
                "Tecnicas de Caixa Preta e Caixa Branca. "
                "As questoes abordam particionamento por equivalencia e grafo de fluxo.",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="esse pdf e sobre o que?")

        self.assertIn("Testes e Qualidade de Software", result)
        self.assertIn("caixa preta", result.lower())
        self.assertNotIn("Questoes para praticar", result)

    def test_analyze_study_files_summary_does_not_force_practice_questions(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "questoes.txt"
            path.write_text(
                "Testes e Qualidade de Software. Tecnicas de Caixa Preta e Caixa Branca. "
                "Particionamento por equivalencia e complexidade ciclomatica.",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="resuma")

        self.assertIn("material sobre", result)
        self.assertNotIn("Questoes para praticar", result)

    def test_analyze_study_files_practice_uses_domain_questions(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "questoes.txt"
            path.write_text(
                "Testes e Qualidade de Software. Tecnicas de Caixa Preta e Caixa Branca. "
                "Particionamento por equivalencia, analise de valor limite e tabela de decisao.",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="crie perguntas")

        self.assertIn("Questoes para praticar", result)
        self.assertIn("classes de equivalencia", result)
        self.assertIn("valores voce testaria", result)

    def test_analyze_study_files_numbers_multiple_files(self):
        with TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "a.txt"
            second = Path(temp_dir) / "b.txt"
            first.write_text("Testes e Qualidade de Software com Caixa Preta.", encoding="utf-8")
            second.write_text("Complexidade ciclomatica e caminhos de teste.", encoding="utf-8")

            result = analyze_study_files([str(first), str(second)], request="sobre o que?")

        self.assertIn("1. a.txt", result)
        self.assertIn("2. b.txt", result)

    def test_pdf_extractor_uses_tounicode_cmap_when_available(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mapped.pdf"
            path.write_bytes(
                b"""
1 0 obj << /Length 120 /Filter /FlateDecode >> stream
""" + __import__("zlib").compress(
                    b"""
beginbfchar
<37> <0054>
<48> <0065>
<56> <0073>
<57> <0074>
endbfchar
"""
                ) + b"""
endstream endobj
2 0 obj << /Length 30 /Filter /FlateDecode >> stream
""" + __import__("zlib").compress(b"BT /F1 12 Tf (7HVWHV) Tj ET") + b"""
endstream endobj
"""
            )

            result = extract_pdf(str(path))

        self.assertIn("Testes", result["text"])
        self.assertEqual(result["engine"], "basic_cmap")

    def test_pdf_extractor_rejects_garbled_text(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "garbled.pdf"
            path.write_bytes(b"stream\n(7 H V W H V \xe2\x99\xa5 H \xe2\x99\xa5 4 X D O L G D G H)\nendstream")

            result = extract_pdf(str(path))

        self.assertEqual(result["text"], "")
        self.assertIn("ilegivel", result["note"])

    def test_pdf_extractor_rejects_long_spaced_symbol_pattern(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "garbled_long.pdf"
            garbled = "7 H V W H V ♥ H ♥ 4 X D O L G D G H ♥ G H ♥ 6 R I W Z D U H ♥ " * 8
            path.write_bytes(f"stream\n({garbled})\nendstream".encode("utf-8"))

            result = extract_pdf(str(path))

        self.assertEqual(result["text"], "")
        self.assertIn("ilegivel", result["note"])

    def test_pdf_ocr_helper_reads_rendered_pages(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "page_1.png"
            image.write_bytes(b"fake")

            result = _extract_pdf_text_ocr(
                root / "aula.pdf",
                render_pages=lambda _path, max_pages=3: [image],
                ocr_image=lambda _path: "Testes de software e caixa preta",
            )

        self.assertEqual(result["text"], "Testes de software e caixa preta")
        self.assertEqual(result["pages"], 1)

    def test_pdf_extractor_uses_ocr_when_text_is_garbled(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "garbled_ocr.pdf"
            garbled = "7 H V W H V ♥ H ♥ 4 X D O L G D G H ♥ " * 6
            path.write_bytes(f"stream\n({garbled})\nendstream".encode("utf-8"))

            with patch(
                "file_processor.extractors._extract_pdf_text_ocr",
                return_value={"text": "Testes de software lista de exercicios", "pages": 1, "note": ""},
            ):
                result = extract_pdf(str(path))

        self.assertIn("Testes de software", result["text"])
        self.assertIn("ocr", result["engine"])
        self.assertEqual(result["ocr_pages"], 1)

    def test_pdf_extractor_uses_ocr_when_text_has_glyph_substitution(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "substituted_glyphs.pdf"
            substituted = (
                "T m s t m s m Q u i t q l i l m l m S o n t w i r m "
                "Qumstao 1 ciqxi xrmti xor mquqvitmvcqi com quivtos cisos lm tmstm. "
                "Qumstao 2 ivatqsm lm vitor tquqtm m ciqxi brivci. "
            ) * 3
            path.write_bytes(f"stream\n({substituted})\nendstream".encode("utf-8"))

            with patch(
                "file_processor.extractors._extract_pdf_text_ocr",
                return_value={"text": "Testes e Qualidade de Software lista de exercicios", "pages": 1, "note": ""},
            ):
                result = extract_pdf(str(path))

        self.assertIn("Testes e Qualidade", result["text"])
        self.assertIn("ocr", result["engine"])
        self.assertEqual(result["ocr_pages"], 1)

    def test_pdf_extractor_uses_external_ocr_before_local_ocr(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "external_ocr.pdf"
            garbled = "T m s t m s Qumstao ciqxi quivtos cisos lm tmstm couxtmx " * 5
            path.write_bytes(f"stream\n({garbled})\nendstream".encode("utf-8"))

            with patch(
                "file_processor.extractors._extract_pdf_text_with_external_ocr",
                return_value={
                    "text": "Testes e Qualidade de Software lista de exercicios",
                    "provider": "external_ocr",
                    "note": "",
                },
            ), patch("file_processor.extractors._extract_pdf_text_ocr") as local_ocr:
                result = extract_pdf(str(path))

        self.assertIn("Testes e Qualidade", result["text"])
        self.assertIn("external_ocr", result["engine"])
        self.assertEqual(result["external_ocr"], "external_ocr")
        local_ocr.assert_not_called()

    def test_analyze_study_files_reports_pdf_extraction_note(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "garbled.pdf"
            path.write_bytes(b"stream\n(7 H V W H V \xe2\x99\xa5 H \xe2\x99\xa5 4 X D O L G D G H)\nendstream")

            result = analyze_study_files([str(path)], request="resuma")

        self.assertIn("ilegivel", result)
        self.assertNotIn("Questoes para praticar", result)

    def test_analyze_study_files_does_not_trust_substituted_glyph_text(self):
        substituted = (
            "T m s t m s m Q u i t q l i l m l m S o n t w i r m "
            "Qumstao 1 ciqxi xrmti xor mquqvitmvcqi com quivtos cisos lm tmstm. "
            "Qumstao 2 ivatqsm lm vitor tquqtm m ciqxi brivci. "
        ) * 3
        fake_result = {
            "ok": True,
            "file": {"name": "questoes_testes_software.pdf"},
            "extracted": {"text": substituted},
        }

        with patch("core.study_file_analysis.process_file", return_value=fake_result):
            result = analyze_study_files(["C:/fake/questoes_testes_software.pdf"], request="resuma")

        self.assertIn("verificacao de confianca", result)
        self.assertNotIn("T m s t m s", result)
        self.assertNotIn("Questoes para praticar", result)

    def test_analyze_study_files_does_not_trust_substituted_glyph_text_with_nuls(self):
        substituted = (
            "T m s t m s m Q u i t q l i l m l m S o n t w i r m "
            "Qumstao 1 ciqxi xrmti xor mquqvitmvcqi com quivtos cisos lm tmstm. "
        ) * 3
        with_nuls = "".join("\x00" + char for char in substituted)
        fake_result = {
            "ok": True,
            "file": {"name": "questoes_testes_software.pdf"},
            "extracted": {"text": with_nuls},
        }

        with patch("core.study_file_analysis.process_file", return_value=fake_result):
            result = analyze_study_files(["C:/fake/questoes_testes_software.pdf"], request="resuma")

        self.assertIn("verificacao de confianca", result)
        self.assertNotIn("Questoes para praticar", result)

    def test_answer_study_followup_answers_question_from_last_context(self):
        fake_context = {
            "files": [
                {
                    "name": "questoes.pdf",
                    "text": "Testes e Qualidade de Software Caixa Preta",
                    "questions": {
                        "1": (
                            "Questao 1 Particionamento em Classes de Equivalencia. "
                            "Um aplicativo bancario permite transferencias via Pix somente "
                            "com valores entre R$ 1,00 e R$ 5.000,00."
                        )
                    },
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("pode responder a questao 1?")

        self.assertIn("3 casos", result)
        self.assertIn("valor < 1", result)

    def test_answer_study_followup_answers_cyclomatic_question(self):
        fake_context = {
            "files": [
                {
                    "name": "questoes.pdf",
                    "text": "Complexidade ciclomatica",
                    "questions": {
                        "5": "Questao 5 Complexidade Ciclomatica. O testador obteve 9 nos e 11 arestas, com 3 nos de predicado."
                    },
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("responda a questao 5")

        self.assertIn("11 - 9 + 2 = 4", result)
        self.assertIn("3 + 1 = 4", result)

    def test_answer_study_followup_corrects_user_answer(self):
        fake_context = {
            "files": [
                {
                    "name": "questoes.pdf",
                    "text": "Valor limite",
                    "questions": {
                        "2": "Questao 2 Analise de Valor Limite. Saque minimo R$ 50 e maximo R$ 1.000."
                    },
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("corrija minha resposta da questao 2: eu testaria 50 e 1000")

        self.assertIn("incompleta", result)
        self.assertIn("49", result)

    def test_answer_study_followup_answers_all_questions(self):
        fake_context = {
            "files": [
                {
                    "name": "questoes.pdf",
                    "text": "Testes e Qualidade",
                    "questions": {
                        "1": "Questao 1 Particionamento por equivalencia Pix R$ 1 a R$ 5000.",
                        "5": "Questao 5 Complexidade Ciclomatica 9 nos 11 arestas 3 predicados.",
                    },
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("responda todas as questoes")

        self.assertIn("Questao 1", result)
        self.assertIn("Questao 5", result)
        self.assertIn("4 caminhos", result)


if __name__ == "__main__":
    unittest.main()
