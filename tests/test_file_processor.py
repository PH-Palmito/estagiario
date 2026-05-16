import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from file_processor.processor import process_file


class FileProcessorTests(unittest.TestCase):
    def test_extract_docx_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "briefing.docx"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    """<?xml version="1.0" encoding="UTF-8"?>
                    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                      <w:body>
                        <w:p><w:r><w:t>Briefing curto</w:t></w:r></w:p>
                        <w:p><w:r><w:t>Carteira sem noticias repetidas</w:t></w:r></w:p>
                      </w:body>
                    </w:document>""",
                )

            result = process_file(str(path))

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["file"]["kind"], "document")
        self.assertIn("Briefing curto", result["extracted"]["text"])
        self.assertEqual(result["extracted"]["paragraphs"], 2)

    def test_extract_xlsx_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "carteira.xlsx"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "xl/sharedStrings.xml",
                    """<?xml version="1.0" encoding="UTF-8"?>
                    <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                      <si><t>Ticker</t></si>
                      <si><t>Preco</t></si>
                      <si><t>BBAS3</t></si>
                    </sst>""",
                )
                archive.writestr(
                    "xl/worksheets/sheet1.xml",
                    """<?xml version="1.0" encoding="UTF-8"?>
                    <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                      <sheetData>
                        <row><c t="s"><v>0</v></c><c t="s"><v>1</v></c></row>
                        <row><c t="s"><v>2</v></c><c><v>20.70</v></c></row>
                      </sheetData>
                    </worksheet>""",
                )

            result = process_file(str(path))

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["file"]["kind"], "spreadsheet")
        self.assertIn("BBAS3", result["extracted"]["text"])
        self.assertEqual(result["extracted"]["sheets"][0]["rows"][1], ["BBAS3", "20.70"])

    def test_extract_simple_pdf_literal_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nota.pdf"
            path.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj <<>> stream\n"
                b"BT (Axel le PDF simples) Tj ET\n"
                b"endstream endobj\n%%EOF"
            )

            result = process_file(str(path))

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["file"]["kind"], "pdf")
        self.assertIn("Axel le PDF simples", result["extracted"]["text"])


if __name__ == "__main__":
    unittest.main()
