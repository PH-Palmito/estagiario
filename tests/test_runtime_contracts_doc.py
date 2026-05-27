from pathlib import Path
import unittest


class RuntimeContractsDocTests(unittest.TestCase):
    def test_runtime_contracts_doc_has_core_sections(self):
        path = Path("docs/axel-runtime-contracts.md")

        content = path.read_text(encoding="utf-8")

        for section in (
            "## Contrato De Command",
            "## Contrato De Router",
            "## Contrato De Action",
            "## Contrato De Background",
            "## Contrato De Memoria Local",
            "## Contrato De Cache",
            "## Contrato De Verificacao De Startup",
            "## Checklist Para Nova Feature",
        ):
            self.assertIn(section, content)

    def test_runtime_contracts_doc_mentions_safety_rules(self):
        content = Path("docs/axel-runtime-contracts.md").read_text(encoding="utf-8")

        self.assertIn("Auto-background so aceita action `read_only` sem confirmacao.", content)
        self.assertIn("Cache de tela precisa validar hash", content)
        self.assertIn("Escrita deve ser atomica", content)
        self.assertIn("LocalJsonStorage", content)


if __name__ == "__main__":
    unittest.main()
