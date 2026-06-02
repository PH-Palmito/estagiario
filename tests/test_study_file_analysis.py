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

    def test_parse_file_command_with_direct_existing_html_path(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pagina teste.html"
            path.write_text("<html><body>Portfolio pessoal</body></html>", encoding="utf-8")

            result = parse_study_file_command(f"analise {path} :: o que tem nesse arquivo")

        self.assertEqual(result, ([str(path)], "o que tem nesse arquivo"))

    def test_parse_file_command_accepts_directory_path(self):
        with TemporaryDirectory() as temp_dir:
            result = parse_study_file_command(f"analise a pasta {temp_dir} :: resuma")

        self.assertEqual(result, ([temp_dir], "resuma"))

    def test_parse_file_command_resolves_partial_file_name(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "cv Pedro Henrique Bispo Palmito.txt"
            path.write_text("Curriculo Pedro", encoding="utf-8")

            with patch("core.study_file_analysis._candidate_file_search_roots", return_value=[root]):
                result = parse_study_file_command("oq tem no arquivo cv pedro")

        self.assertEqual(result, ([str(path)], "o que tem no arquivo cv pedro"))

    def test_parse_explain_command_resolves_filename_in_search_roots(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "README_CineRadar.md"
            path.write_text("# CineRadar", encoding="utf-8")

            with patch("core.study_file_analysis._candidate_file_search_roots", return_value=[root]):
                result = parse_study_file_command("explique README_CineRadar.md")

        self.assertEqual(result, ([str(path)], "explique"))

    def test_parse_file_command_accepts_casual_variations(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "cv Pedro Henrique.txt"
            path.write_text("Pedro email@exemplo.com Objetivo Tecnologia", encoding="utf-8")

            with patch("core.study_file_analysis._candidate_file_search_roots", return_value=[root]):
                first = parse_study_file_command("fale sobre cv Pedro")
                second = parse_study_file_command("oq tem em cv Pedro")
                third = parse_study_file_command("leia cv Pedro")

        self.assertEqual(first, ([str(path)], "explique"))
        self.assertEqual(second, ([str(path)], "o que tem no arquivo cv Pedro"))
        self.assertEqual(third, ([str(path)], "o que tem nesse arquivo"))

    def test_partial_file_search_prefers_exact_name_in_earlier_root(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            downloads = root / "Documents" / "Downloads"
            desktop = root / "OneDrive" / "Área de Trabalho"
            downloads.mkdir(parents=True)
            desktop.mkdir(parents=True)
            wanted = downloads / "README_CineRadar.md"
            other = desktop / "README_CineRadar.md"
            wanted.write_text("# Downloads", encoding="utf-8")
            other.write_text("# Desktop", encoding="utf-8")

            with patch("core.study_file_analysis._candidate_file_search_roots", return_value=[downloads, desktop]):
                result = parse_study_file_command("explique README_CineRadar.md")

        self.assertEqual(result, ([str(wanted)], "explique"))

    def test_process_file_extracts_pptx_slide_text(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "aula.pptx"
            write_minimal_pptx(path, ["Fotossintese transforma luz em energia", "Clorofila absorve luz"])

            result = process_file(str(path))

        self.assertTrue(result["ok"])
        self.assertEqual(result["file"]["kind"], "presentation")
        self.assertIn("Slide 1", result["extracted"]["text"])
        self.assertEqual(result["extracted"]["slide_count"], 2)

    def test_analyze_html_file_from_direct_path(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "index.html"
            path.write_text(
                "<html><head><title>Portfólio</title></head><body><h1>Pedro</h1><p>Projetos em React Native e APIs.</p></body></html>",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="o que tem nesse arquivo")

        self.assertIn("Análise dos arquivos", result)
        self.assertIn("index.html", result)
        self.assertIn("React Native", result)
        self.assertNotIn("Pedido considerado", result)

    def test_analyze_readme_answers_project_name_directly(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "README_CineRadar.md"
            path.write_text(
                "# CineRadar\n\n"
                "**CineRadar** é um sistema recomendador de filmes por perfil cinéfilo.\n\n"
                "## Sobre o projeto\n"
                "O projeto recomenda filmes com base no perfil do usuário.\n\n"
                "## Tecnologias utilizadas\n"
                "- Java 21\n- Spring Boot\n- JUnit 5\n",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="qual o nome do projeto")

        self.assertIn("O projeto do arquivo README_CineRadar.md se chama CineRadar.", result)
        self.assertIn("Análise dos arquivos", result)
        self.assertNotIn("Análise de estudo dos arquivos", result)
        self.assertNotIn("Pontos centrais", result)
        self.assertNotIn("Pedido considerado", result)

    def test_analyze_readme_answers_other_direct_questions(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "README_CineRadar.md"
            path.write_text(
                "# CineRadar\n\n"
                "## Integrantes\n"
                "- Pedro Henrique Bispo\n- Isaac Nascimento\n\n"
                "## Tecnologias utilizadas\n"
                "- Java 21\n- Spring Boot\n- Maven\n- JUnit 5\n\n"
                "## Como executar o projeto\n"
                "No Windows: `mvnw.cmd spring-boot:run`.\n",
                encoding="utf-8",
            )

            tech = analyze_study_files([str(path)], request="quais tecnologias foram usadas?")
            people = analyze_study_files([str(path)], request="quem sao os integrantes?")
            run = analyze_study_files([str(path)], request="como executar o projeto?")

        self.assertIn("Tecnologias utilizadas:", tech)
        self.assertIn("Spring Boot", tech)
        self.assertNotIn("Pontos centrais", tech)
        self.assertIn("Integrantes:", people)
        self.assertIn("Pedro Henrique Bispo", people)
        self.assertIn("Como executar:", run)
        self.assertIn("spring-boot:run", run)

    def test_analyze_directory_expands_supported_files(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.txt").write_text("Resumo do projeto Axel com automações locais.", encoding="utf-8")
            (root / "b.html").write_text("<h1>Dashboard</h1><p>Interface HTML local.</p>", encoding="utf-8")
            (root / "ignore.bin").write_bytes(b"\x00\x01")

            result = analyze_study_files([str(root)], request="o que tem nessa pasta")

        self.assertIn("Análise dos arquivos", result)
        self.assertIn("a.txt", result)
        self.assertIn("b.html", result)
        self.assertIn("analisei 2 arquivo(s) da pasta", result)

    def test_analyze_study_files_summarizes_and_generates_questions(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tema.txt"
            path.write_text(
                "A mitose divide uma celula em duas celulas geneticamente identicas.\n"
                "A meiose forma gametas e reduz pela metade o numero de cromossomos.\n",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="crie questoes")

        self.assertIn("Análise de estudo dos arquivos", result)
        self.assertIn("tema.txt", result)
        self.assertIn("Questões para praticar", result)
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
        self.assertNotIn("Questões para praticar", result)

    def test_analyze_study_files_o_que_tem_uses_about_style(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "redes.txt"
            path.write_text(
                "Redes de Computadores. Comunicacao Digital. Conceitos Basicos. Meios Fisicos.",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="o que tem nesse arquivo")

        self.assertIn("Redes de Computadores", result)
        self.assertNotIn("Pontos centrais", result)

    def test_analyze_general_cv_does_not_use_study_framing(self):
        fake_result = {
            "ok": True,
            "file": {"name": "cv Pedro.docx"},
            "extracted": {
                "text": (
                    "Pedro Henrique Bispo Palmito 📞 (71) 98839-3851 | 📧 email@exemplo.com "
                    "Salvador - BA | 19 anosObjetivo Acadêmico de Engenharia de Software "
                    "com foco em Desenvolvimento Mobile e Front-end. "
                    "Perfil Profissional Estudante com experiência prática com React, React native,Supabase, "
                    "MySQL, consumo de APIs e versionamento com Git.Tecnologias Mobile & Front-end: "
                    "React Native, React.js, Gerenciamento de Estados (Hooks)."
                )
            },
        }

        with patch("core.study_file_analysis.process_file", return_value=fake_result):
            result = analyze_study_files(["C:/fake/cv Pedro.docx"], request="oque tem nesse pdf")

        self.assertIn("Análise dos arquivos", result)
        self.assertIn("é um currículo de Pedro Henrique Bispo Palmito", result)
        self.assertIn("Objetivo: Acadêmico de Engenharia de Software", result)
        self.assertIn("React Native", result)
        self.assertNotIn("Análise de estudo dos arquivos", result)
        self.assertNotIn("Pedido considerado", result)
        self.assertNotIn("Pontos centrais", result)
        self.assertNotIn("Gerenciamento de Estados", result)

    def test_explain_cv_with_network_skill_does_not_become_study_material(self):
        fake_result = {
            "ok": True,
            "file": {"name": "cv Pedro Henrique Bispo Palmito.docx"},
            "extracted": {
                "text": (
                    "Pedro Henrique Bispo Palmito Objetivo Academico de Engenharia de Software "
                    "com foco em Desenvolvimento Mobile e Front-end. Perfil Profissional estudante "
                    "com experiencia pratica em React Native, APIs, Git e Redes de Computadores. "
                    "Tecnologias TypeScript JavaScript HTML5 CSS3."
                )
            },
        }

        with patch("core.study_file_analysis.process_file", return_value=fake_result):
            result = analyze_study_files(["C:/fake/cv Pedro Henrique Bispo Palmito.docx"], request="explique")

        self.assertIn("curr", result)
        self.assertIn("Pedro Henrique Bispo Palmito", result)
        self.assertNotIn("material sobre Redes de Computadores", result)
        self.assertNotIn("Pontos centrais", result)

    def test_cv_without_curriculum_word_is_detected_by_contact_and_sections(self):
        fake_result = {
            "ok": True,
            "file": {"name": "Pedro Henrique.docx"},
            "extracted": {
                "text": (
                    "Pedro Henrique Bispo Palmito email pedro@email.com telefone 71988393851 "
                    "Objetivo atuar com desenvolvimento mobile. Formacao Engenharia de Software. "
                    "Habilidades TypeScript React Native Git APIs."
                )
            },
        }

        with patch("core.study_file_analysis.process_file", return_value=fake_result):
            result = analyze_study_files(["C:/fake/Pedro Henrique.docx"], request="o que tem nesse arquivo")

        self.assertIn("curr", result)
        self.assertIn("Pedro Henrique Bispo Palmito", result)
        self.assertNotIn("material sobre", result)

    def test_untitled_article_is_described_as_technical_text(self):
        fake_result = {
            "ok": True,
            "file": {"name": "arquivo_sem_titulo.pdf"},
            "extracted": {
                "text": (
                    "Resumo Este trabalho investiga seguranca em redes sem fio e autenticacao. "
                    "Introducao Redes sem fio exigem controles de acesso e criptografia. "
                    "Metodologia Foram analisados protocolos WPA2 e WPA3 em cenarios academicos. "
                    "Conclusao A configuracao correta reduz riscos de acesso indevido. "
                    "Referencias artigos de seguranca de redes."
                )
            },
        }

        with patch("core.study_file_analysis.process_file", return_value=fake_result):
            result = analyze_study_files(["C:/fake/arquivo_sem_titulo.pdf"], request="explique")

        self.assertIn("artigo ou texto tecnico", result)
        self.assertIn("Resumo:", result)
        self.assertNotIn("curr", result.lower())

    def test_explain_readme_does_not_become_curriculum(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "README_CineRadar.md"
            path.write_text(
                "# CineRadar\n\n"
                "**CineRadar** e um sistema recomendador de filmes.\n\n"
                "## Sobre o projeto\n"
                "O projeto recomenda filmes com base no perfil do usuario.\n\n"
                "## Tecnologias utilizadas\n"
                "- Java 21\n- Spring Boot\n- Maven\n- JUnit 5\n\n"
                "## Integrantes\n"
                "- Pedro Henrique Bispo\n",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="explique README_CineRadar.md")

        self.assertIn("README de projeto", result)
        self.assertIn("CineRadar", result)
        self.assertIn("Tecnologias", result)
        self.assertNotIn("curr", result.lower())
        self.assertNotIn("material sobre", result)

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
        self.assertNotIn("Questões para praticar", result)

    def test_analyze_study_files_practice_uses_domain_questions(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "questoes.txt"
            path.write_text(
                "Testes e Qualidade de Software. Tecnicas de Caixa Preta e Caixa Branca. "
                "Particionamento por equivalencia, analise de valor limite e tabela de decisao.",
                encoding="utf-8",
            )

            result = analyze_study_files([str(path)], request="crie perguntas")

        self.assertIn("Questões para praticar", result)
        self.assertIn("classes de equivalência", result)
        self.assertIn("valores você testaria", result)

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
        self.assertNotIn("Questões para praticar", result)

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

        self.assertIn("verificação de confiança", result)
        self.assertNotIn("T m s t m s", result)
        self.assertNotIn("Questões para praticar", result)

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

        self.assertIn("verificação de confiança", result)
        self.assertNotIn("Questões para praticar", result)

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

    def test_answer_study_followup_project_name_from_last_file(self):
        fake_context = {
            "files": [
                {
                    "name": "portfolio.html",
                    "text": "Projetos: FinTrack - dashboard financeiro. Axel Study - assistente de estudos. Tecnologias: React Native.",
                    "topic": "portfólio",
                    "questions": {},
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("qual o nome do projeto?")

        self.assertIn("FinTrack", result)
        self.assertIn("Axel Study", result)

    def test_answer_study_followup_project_name_does_not_invent(self):
        fake_context = {
            "files": [
                {
                    "name": "cv Pedro.docx",
                    "text": "Pedro Henrique. Objetivo Acadêmico de Engenharia de Software. Tecnologias: React Native, Supabase e Git.",
                    "topic": "currículo de Pedro Henrique",
                    "questions": {},
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("qual o nome do projeto?")

        self.assertIn("não encontrei um nome de projeto explícito", result)
        self.assertIn("cv Pedro.docx", result)

    def test_answer_study_followup_identifies_recent_slide_file(self):
        fake_context = {
            "files": [
                {
                    "path": "C:/fake/aula_redes.pptx",
                    "name": "aula_redes.pptx",
                    "kind": "presentation",
                    "text": "Redes de Computadores. Comunicacao Digital. Meios Fisicos.",
                    "raw_text": "Redes de Computadores. Comunicacao Digital. Meios Fisicos.",
                    "topic": "Redes de Computadores, Comunicacao Digital, Meios Fisicos",
                    "questions": {},
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("voce consegue ver que isso e um slide?")

        self.assertIn("apresentacao/slide", result)
        self.assertIn("aula_redes.pptx", result)
        self.assertIn("Redes de Computadores", result)

    def test_answer_study_followup_main_concepts_from_last_file(self):
        fake_context = {
            "files": [
                {
                    "name": "RedesBasico.pdf",
                    "raw_text": "Redes de Computadores. Comunicação Digital e Conceitos Básicos. Meios Físicos. Informações Digitais e Binárias.",
                    "text": "Redes de Computadores. Comunicação Digital e Conceitos Básicos. Meios Físicos. Informações Digitais e Binárias.",
                    "topic": "redes de computadores",
                    "questions": {},
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("quais conceitos principais aparecem?")

        self.assertIn("Conceitos principais", result)
        self.assertIn("Redes de Computadores", result)
        self.assertIn("Comunicação Digital", result)
        self.assertNotIn("Marco", result)

    def test_answer_study_followup_generates_questions_even_with_study_word(self):
        fake_context = {
            "files": [
                {
                    "name": "RedesBasico.pdf",
                    "raw_text": "Redes de Computadores. Comunicação Digital. Meios Físicos. Informações Digitais e Binárias.",
                    "text": "Redes de Computadores. Comunicação Digital. Meios Físicos. Informações Digitais e Binárias.",
                    "topic": "redes de computadores",
                    "questions": {},
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("crie 5 perguntas para eu estudar esse arquivo")

        self.assertIn("Perguntas para praticar", result)
        self.assertNotIn("Plano rápido", result)
        self.assertNotIn("Professor", result)

    def test_answer_study_followup_says_when_technical_topic_is_not_in_file(self):
        fake_context = {
            "files": [
                {
                    "name": "RedesBasico.pdf",
                    "raw_text": "Redes de Computadores. Comunicação Digital. Meios Físicos.",
                    "text": "Redes de Computadores. Comunicação Digital. Meios Físicos.",
                    "topic": "redes de computadores",
                    "questions": {},
                }
            ]
        }

        with patch("core.study_file_analysis.load_study_context", return_value=fake_context):
            result = answer_study_followup("qual a diferenca entre TCP e UDP?")

        self.assertIn("não encontrei uma resposta clara", result.lower())
        self.assertIn("TCP", result)
        self.assertIn("UDP", result)
        self.assertIn("RedesBasico.pdf", result)

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

        self.assertIn("Questão 1", result)
        self.assertIn("Questão 5", result)
        self.assertIn("4 caminhos", result)


if __name__ == "__main__":
    unittest.main()
