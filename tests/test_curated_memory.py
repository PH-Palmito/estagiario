import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from memory import curated_memory


class CuratedMemoryTests(unittest.TestCase):
    def test_ensure_creates_default_memory_files(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with (
                patch.object(curated_memory, "MEMORY_DIR", root),
                patch.object(curated_memory, "CORE_MEMORY_PATH", root / "core_memory.md"),
                patch.object(curated_memory, "USER_PROFILE_PATH", root / "user_profile.md"),
            ):
                curated_memory.ensure_curated_memory_files()

                self.assertTrue((root / "core_memory.md").exists())
                self.assertTrue((root / "user_profile.md").exists())

    def test_format_curated_memory_compacts_markdown(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_path = root / "core_memory.md"
            user_path = root / "user_profile.md"
            core_path.write_text("# Core\n\n- Usar AxelBrain.\n", encoding="utf-8")
            user_path.write_text("# User\n\n- Prefere respostas curtas.\n", encoding="utf-8")

            with (
                patch.object(curated_memory, "MEMORY_DIR", root),
                patch.object(curated_memory, "CORE_MEMORY_PATH", core_path),
                patch.object(curated_memory, "USER_PROFILE_PATH", user_path),
            ):
                text = curated_memory.format_curated_memory()

        self.assertIn("Core", text)
        self.assertIn("Usar AxelBrain", text)
        self.assertIn("Prefere respostas curtas", text)


if __name__ == "__main__":
    unittest.main()
