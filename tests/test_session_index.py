import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from unittest.mock import patch

from memory import session_index


class SessionIndexTests(unittest.TestCase):
    def test_indexes_and_searches_turns_with_fts(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sessions.sqlite3"
            session_index.index_exchange(
                "vamos criar agentes especialistas para o Axel",
                "Sim, isso entra na arquitetura do AxelBrain.",
                session_id="test-session",
                path=path,
            )

            results = session_index.search_session_turns("agentes AxelBrain", path=path)

        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(any("agentes" in item["text"] or "AxelBrain" in item["text"] for item in results))

    def test_format_session_search_reports_empty_result(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sessions.sqlite3"
            with patch.object(session_index, "SESSION_INDEX_PATH", path):
                text = session_index.format_session_search("assunto inexistente", limit=2)

        self.assertIn("Nao encontrei", text)


if __name__ == "__main__":
    unittest.main()
