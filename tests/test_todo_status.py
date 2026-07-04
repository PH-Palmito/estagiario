import tempfile
import unittest
import json
from pathlib import Path

from memory.todo_status import (
    add_current_priority_evidence,
    format_current_priority_evidence,
    format_next_todo_step,
    format_todo_evidence_audit,
    format_todo_priorities,
    load_todo_items,
    parse_and_add_current_priority_evidence,
    update_current_priority_status,
)


TODO_SAMPLE = """# Lista

## Fase antiga

- [x] Item antigo concluído.

## Transformar fachada em capacidade real

- [x] Criar inventário.
- [ ] Transformar metas/lista de afazeres em sistema operacional útil.
  - [ ] Fazer as metas deixarem rastros verificáveis.
- [ ] Evoluir agentes especialistas.

## Depois

- [ ] App final.
"""


class TodoStatusTests(unittest.TestCase):
    def test_load_todo_items_keeps_section_and_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            items = load_todo_items(path)

        self.assertEqual(len(items), 6)
        self.assertEqual(items[2].section, "Transformar fachada em capacidade real")
        self.assertFalse(items[2].done)
        self.assertGreater(items[2].line_number, 0)

    def test_format_priorities_uses_first_pending_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            result = format_todo_priorities(path, limit=2)

        self.assertIn("Prioridade atual do Axel: Transformar fachada em capacidade real", result)
        self.assertIn("2/6 itens concluídos", result)
        self.assertIn("Transformar metas/lista", result)
        self.assertIn("Fazer as metas", result)
        self.assertNotIn("App final", result)

    def test_format_next_todo_step_includes_evidence_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            result = format_next_todo_step(path)

        self.assertIn("Próximo passo do Axel", result)
        self.assertIn("Transformar metas/lista", result)
        self.assertIn("memory/todo.md", result)
        self.assertIn("comando, efeito observável, teste ou evidência", result)

    def test_update_current_priority_status_marks_selected_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            result = update_current_priority_status(2, done=True, path=path)
            items = load_todo_items(path)
            evidence_payload = json.loads((Path(tmp) / "todo_evidence.json").read_text(encoding="utf-8"))

        self.assertIn("Meta 2 concluída", result)
        self.assertTrue(items[3].done)
        self.assertFalse(items[2].done)
        records = list(evidence_payload["items"].values())
        self.assertTrue(any((record.get("status_events") or [{}])[-1].get("status") == "concluída" for record in records))

    def test_update_current_priority_status_rejects_unknown_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            result = update_current_priority_status(99, done=True, path=path)

        self.assertIn("Não encontrei a meta 99", result)

    def test_add_current_priority_evidence_records_files_tests_and_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            result = add_current_priority_evidence(
                1,
                files=["memory/todo_status.py"],
                tests=["tests.test_todo_status"],
                note="Comando validado.",
                path=path,
            )
            shown = format_current_priority_evidence(1, path=path)

        self.assertIn("Evidência registrada", result)
        self.assertIn("memory/todo_status.py", shown)
        self.assertIn("tests.test_todo_status", shown)
        self.assertIn("Comando validado", shown)

    def test_parse_and_add_current_priority_evidence_understands_labeled_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            result = parse_and_add_current_priority_evidence(
                1,
                "arquivos: core/memory_commands.py, memory/todo_status.py | testes: tests.test_memory_commands | nota: integrado ao comando",
                path=path,
            )

        self.assertIn("core/memory_commands.py", result)
        self.assertIn("tests.test_memory_commands", result)

    def test_format_current_priority_evidence_handles_empty_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            result = format_current_priority_evidence(1, path=path)

        self.assertIn("Ainda sem evidências registradas", result)

    def test_format_todo_evidence_audit_lists_completed_items_without_strong_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")

            result = format_todo_evidence_audit(path)

        self.assertIn("Auditoria de evidências das metas", result)
        self.assertIn("sem evidência forte", result)
        self.assertIn("Item antigo concluído", result)

    def test_format_todo_evidence_audit_counts_strong_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "todo.md"
            path.write_text(TODO_SAMPLE, encoding="utf-8")
            add_current_priority_evidence(1, files=["memory/todo_status.py"], path=path)
            update_current_priority_status(1, done=True, path=path)

            result = format_todo_evidence_audit(path)

        self.assertIn("1 com evidência forte", result)


if __name__ == "__main__":
    unittest.main()
