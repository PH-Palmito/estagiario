import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory.json_store import LocalJsonStorage, read_json_file, update_json_file, write_json_atomic


class JsonStoreTests(unittest.TestCase):
    def test_read_json_file_returns_default_when_missing_or_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"

            self.assertEqual(read_json_file(path, {"ok": False}), {"ok": False})

            path.write_text("{invalid", encoding="utf-8")
            self.assertEqual(read_json_file(path, {"ok": False}), {"ok": False})

    def test_write_json_atomic_creates_parent_and_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "nested" / "state.json"

            write_json_atomic(path, {"ok": True}, trailing_newline=True)

            self.assertEqual(read_json_file(path, {}), {"ok": True})
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

    def test_update_json_file_reads_modifies_and_writes_under_one_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "queue.json"

            result = update_json_file(path, [], lambda items: [*items, {"text": "oi"}])

            self.assertEqual(result, [{"text": "oi"}])
            self.assertEqual(read_json_file(path, []), [{"text": "oi"}])

    def test_local_json_storage_implements_same_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            storage = LocalJsonStorage()

            storage.write(path, {"count": 1})
            result = storage.update(path, {}, lambda payload: {"count": payload["count"] + 1})

            self.assertEqual(result, {"count": 2})
            self.assertEqual(storage.read(path, {}), {"count": 2})

    def test_local_json_storage_validator_falls_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            storage = LocalJsonStorage()
            storage.write(path, [])

            result = storage.read(path, {"ok": False}, validator=lambda value: isinstance(value, dict))

            self.assertEqual(result, {"ok": False})

    def test_local_json_storage_retries_permission_error_on_replace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            storage = LocalJsonStorage()
            calls = []
            real_replace = __import__("os").replace

            def flaky_replace(src, dst):
                calls.append((src, dst))
                if len(calls) == 1:
                    raise PermissionError("locked")
                return real_replace(src, dst)

            with (
                patch("memory.json_store.os.replace", side_effect=flaky_replace),
                patch("memory.json_store.time.sleep"),
            ):
                storage.write(path, {"ok": True})

            self.assertGreaterEqual(len(calls), 2)
            self.assertEqual(storage.read(path, {}), {"ok": True})

    def test_local_json_storage_recreates_missing_tmp_on_replace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            storage = LocalJsonStorage()
            calls = []
            real_replace = __import__("os").replace

            def missing_once(src, dst):
                calls.append((src, dst))
                if len(calls) == 1:
                    Path(src).unlink(missing_ok=True)
                    raise FileNotFoundError(str(src))
                return real_replace(src, dst)

            with (
                patch("memory.json_store.os.replace", side_effect=missing_once),
                patch("memory.json_store.time.sleep"),
            ):
                storage.write(path, {"ok": True})

            self.assertGreaterEqual(len(calls), 2)
            self.assertEqual(storage.read(path, {}), {"ok": True})


if __name__ == "__main__":
    unittest.main()
