import unittest
from unittest.mock import patch

from core.response_provenance import (
    begin_response_provenance,
    record_model_use,
    record_tool_use,
    response_provenance_snapshot,
)


class ResponseProvenanceTests(unittest.TestCase):
    def setUp(self):
        begin_response_provenance()

    def test_records_safe_model_tool_and_file_metadata(self):
        record_model_use(provider="cloud", model="nvidia/model", policy="reasoning", success=True)
        record_tool_use("study.analyze_files", {"paths": [r"C:\Users\Pedro\Downloads\RedesBasico.pdf"]})

        snapshot = response_provenance_snapshot()

        self.assertEqual(snapshot["models"][-1]["model"], "nvidia/model")
        self.assertEqual(snapshot["tools"], ["study.analyze_files"])
        self.assertEqual(snapshot["files"], ["RedesBasico.pdf"])
        self.assertNotIn("Users", str(snapshot))

    def test_new_turn_clears_previous_provenance(self):
        record_tool_use("file_read", {"path": "segredo.txt"})
        begin_response_provenance()

        self.assertEqual(response_provenance_snapshot()["tools"], [])
        self.assertEqual(response_provenance_snapshot()["files"], [])

    def test_respond_is_not_reported_as_external_tool(self):
        record_tool_use("respond", {"message": "oi"})

        self.assertEqual(response_provenance_snapshot()["tools"], [])

    def test_chat_model_log_updates_provenance(self):
        from llm import chat

        with patch.object(chat, "append_execution_log"):
            chat._log_model_call(
                "model_call_end",
                provider="cloud",
                model="nvidia/model",
                model_policy="reasoning",
                success=True,
                fallback_used=False,
            )

        self.assertEqual(response_provenance_snapshot()["models"][-1]["model"], "nvidia/model")

    def test_rejected_model_attempt_is_still_auditable(self):
        from llm import chat

        chat._record_rejected_model_attempt("local", "qwen", "local_first", fallback_used=False)

        model = response_provenance_snapshot()["models"][-1]
        self.assertEqual(model["model"], "qwen")
        self.assertFalse(model["success"])


if __name__ == "__main__":
    unittest.main()
