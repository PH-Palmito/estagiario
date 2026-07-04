import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.skill_operations import format_actionable_skill_detail, format_actionable_skills_overview


SKILL_SAMPLE = """# Skill Estudos

## Gatilhos
- resumir slides
- analisar arquivo de estudo

## Procedimento
- Extrair conteudo.

## Riscos
- OCR ruim.

## Exemplos recentes
- resuma esses slides para mim

## Origem
- Agente sugerido: `study_agent`
- Toolset sugerido: `estudos`
"""


class SkillOperationsTests(unittest.TestCase):
    @patch(
        "core.skill_operations.tool_library_for_agent",
        return_value={
            "actions": [
                {"name": "study.analyze_files", "category": "study"},
                {"name": "study.status", "category": "study"},
            ]
        },
    )
    def test_actionable_skill_detail_marks_ready_skill(self, _library):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            skill_dir = root / "estudos"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(SKILL_SAMPLE, encoding="utf-8")

            with patch("core.skill_operations.load_skills") as load:
                from memory.procedural_skills import ProceduralSkill

                load.return_value = [
                    ProceduralSkill(
                        name="estudos",
                        title="Skill Estudos",
                        triggers=("resumir slides", "analisar arquivo de estudo"),
                        risks=("OCR ruim.",),
                        path=skill_dir / "SKILL.md",
                        content=SKILL_SAMPLE,
                    )
                ]
                result = format_actionable_skill_detail("estudos")

        self.assertIn("status pronta", result)
        self.assertIn("study_agent", result)
        self.assertIn("study.analyze_files", result)
        self.assertIn("resuma esses slides", result)
        self.assertIn("Exemplos validados: 1/1", result)

    @patch("core.skill_operations.tool_library_for_agent", return_value={"actions": []})
    def test_actionable_skills_overview_lists_readiness(self, _library):
        with patch("core.skill_operations.load_skills") as load:
            from memory.procedural_skills import ProceduralSkill

            load.return_value = [
                ProceduralSkill(
                    name="demo",
                    title="Skill Demo",
                    triggers=("demo",),
                    risks=(),
                    path=Path("memory/skills/demo/SKILL.md"),
                    content="# Skill Demo\n\n## Gatilhos\n- demo\n",
                )
            ]
            result = format_actionable_skills_overview()

        self.assertIn("Skills acion\u00e1veis do Axel", result)
        self.assertIn("demo: documentada", result)

    @patch(
        "core.skill_operations.tool_library_for_agent",
        return_value={
            "actions": [
                {"name": "bluetooth_status", "category": "system"},
                {"name": "telegram.start_bot", "category": "telegram"},
            ]
        },
    )
    def test_skill_actions_prioritize_primary_domain(self, _library):
        with patch("core.skill_operations.load_skills") as load:
            from memory.procedural_skills import ProceduralSkill

            skill = ProceduralSkill(
                name="sistema",
                title="Sistema",
                triggers=("iniciar bot telegram",),
                risks=(),
                path=Path("memory/skills/sistema/SKILL.md"),
                content="# Sistema\n\n## Gatilhos\n- iniciar bot telegram\n\n## Exemplos recentes\n- iniciar bot telegram\n",
            )
            load.return_value = [skill]
            result = format_actionable_skill_detail("sistema")

        self.assertLess(result.index("telegram.start_bot"), result.index("bluetooth_status"))

    @patch(
        "core.skill_operations.tool_library_for_agent",
        return_value={"actions": [{"name": "study.status", "category": "study"}]},
    )
    def test_skill_with_misrouted_example_is_partial(self, _library):
        with patch("core.skill_operations.load_skills") as load:
            from memory.procedural_skills import ProceduralSkill

            skill = ProceduralSkill(
                name="estudos",
                title="Estudos",
                triggers=("resumir slides",),
                risks=(),
                path=Path("memory/skills/estudos/SKILL.md"),
                content="# Estudos\n\n## Gatilhos\n- resumir slides\n\n## Exemplos recentes\n- iniciar bot telegram\n",
            )
            load.return_value = [skill]
            result = format_actionable_skill_detail("estudos")

        self.assertIn("status parcial", result)
        self.assertIn("Exemplos validados: 0/1", result)


if __name__ == "__main__":
    unittest.main()
