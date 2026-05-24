import unittest
from pathlib import Path


class GitignorePolicyTests(unittest.TestCase):
    def test_memory_runtime_artifacts_are_ignored(self):
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        expected_patterns = [
            "memory/*.json",
            "memory/*.jsonl",
            "memory/*.md",
            "memory/*.tmp",
            "memory/*.html",
            "memory/*.txt",
            "memory/*.playwright.txt",
            "memory/obsidian_vault/",
            "memory/audio_diagnostics/",
            "memory/chunks/",
            "memory/map_cache/",
            "!memory/*.py",
            "!memory/todo.md",
        ]

        for pattern in expected_patterns:
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, gitignore)

    def test_memory_artifacts_policy_document_exists(self):
        policy = Path("docs/memory-artifacts-policy.md").read_text(encoding="utf-8")

        self.assertIn("O que fica fora do Git", policy)
        self.assertIn("memory/*.tmp", policy)
        self.assertIn("memory/*.html", policy)
        self.assertIn("memory/todo.md", policy)


if __name__ == "__main__":
    unittest.main()
