import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from memory import procedural_skills


class ProceduralSkillsTests(unittest.TestCase):
    def test_loads_skill_markdown(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "programacao"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "# Programacao\n\n## Gatilhos\n- codigo\n- teste\n\n## Riscos\n- cuidado\n",
                encoding="utf-8",
            )

            skills = procedural_skills.load_skills(root)

        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "programacao")
        self.assertIn("codigo", skills[0].triggers)

    def test_search_skills_prioritizes_trigger_match(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "carteira"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "# Carteira\n\n## Gatilhos\n- dividendos\n- investimentos\n\n## Riscos\n- mercado muda\n",
                encoding="utf-8",
            )

            matches = procedural_skills.search_skills("resumo de dividendos", skills_dir=root)

        self.assertEqual(matches[0]["name"], "carteira")
        self.assertIn("dividendos", matches[0]["matched_terms"])

    def test_format_catalog_lists_skills(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = root / "voz"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Voz\n\n## Gatilhos\n- microfone\n", encoding="utf-8")

            catalog = procedural_skills.format_skill_catalog(root)

        self.assertIn("voz: Voz", catalog)

    def test_upsert_skill_from_suggestion_writes_markdown(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = procedural_skills.upsert_skill_from_suggestion(
                {
                    "skill_name": "code-review-tests",
                    "toolset": "programacao",
                    "agent": "dev_agent",
                    "intent": "respond_code_review",
                    "examples": ["revisar codigo e rodar testes"],
                },
                skills_dir=root,
            )

            content = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, "SKILL.md")
        self.assertEqual(path.parent.name, "code-review-tests")
        self.assertIn("Skill Code Review Tests", content)
        self.assertIn("revisar codigo e rodar testes", content)
        self.assertIn("dev_agent", content)

    def test_create_study_skill_from_request_writes_rich_markdown(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = procedural_skills.create_skill_from_request(
                "me ajudar a estudar, resumir slides, analisar arquivos e gerar questoes",
                skills_dir=root,
            )

            content = path.read_text(encoding="utf-8")

        self.assertEqual(path.parent.name, "estudos")
        self.assertIn("# Skill Estudos", content)
        self.assertIn("resumir slides", content)
        self.assertIn("gerar questoes", content)
        self.assertIn("corrigir respostas", content)
        self.assertIn("study_agent", content)

    def test_create_generic_skill_from_request_writes_markdown(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = procedural_skills.create_skill_from_request(
                "organizar referencias de pesquisa",
                skills_dir=root,
            )

            content = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, "SKILL.md")
        self.assertIn("Organizar Referencias Pesquisa", content)
        self.assertIn("organizar referencias de pesquisa", content)


if __name__ == "__main__":
    unittest.main()
