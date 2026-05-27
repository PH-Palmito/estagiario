import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import image_tools


def write_fake_screen(path: Path, content: bytes = b"same-screen") -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {"width": 800, "height": 600}


class VisionScreenCacheTests(unittest.TestCase):
    def test_screen_analysis_reuses_cache_for_same_image_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            calls = []

            with (
                patch.object(image_tools, "SCREENSHOT_DIR", temp_path / "screens"),
                patch.object(image_tools, "VISION_SCREEN_CACHE_PATH", temp_path / "vision_screen_cache.json"),
                patch.object(image_tools, "_browser_local_image_from_foreground", return_value=None),
                patch.object(image_tools, "_capture_foreground_window", side_effect=write_fake_screen),
                patch.object(image_tools, "_make_screen_content_crop", return_value=None),
                patch.object(image_tools.time, "time", return_value=1000),
                patch.object(image_tools, "_remember_visual_result"),
                patch.object(image_tools, "_ocr_image", side_effect=lambda _path: calls.append("ocr") or {"text": "texto"}),
                patch.object(image_tools, "_semantic_image_analysis", return_value="Analise visual da tela: texto"),
            ):
                first = image_tools.analyze_screen_image()
                second = image_tools.analyze_screen_image()

        self.assertEqual(first, "Analise visual da tela: texto")
        self.assertEqual(second, "Analise visual da tela: texto")
        self.assertEqual(calls, ["ocr"])

    def test_screen_analysis_refreshes_when_cache_expires(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            calls = []

            with (
                patch.object(image_tools, "SCREENSHOT_DIR", temp_path / "screens"),
                patch.object(image_tools, "VISION_SCREEN_CACHE_PATH", temp_path / "vision_screen_cache.json"),
                patch.object(image_tools, "_browser_local_image_from_foreground", return_value=None),
                patch.object(image_tools, "_capture_foreground_window", side_effect=write_fake_screen),
                patch.object(image_tools, "_make_screen_content_crop", return_value=None),
                patch.object(image_tools, "_remember_visual_result"),
                patch.object(image_tools, "_ocr_image", side_effect=lambda _path: calls.append("ocr") or {"text": "texto"}),
                patch.object(image_tools, "_semantic_image_analysis", side_effect=["primeira", "segunda"]),
            ):
                with patch.object(image_tools.time, "time", return_value=1000):
                    first = image_tools.analyze_screen_image(ttl_seconds=10)
                with patch.object(image_tools.time, "time", return_value=1020):
                    second = image_tools.analyze_screen_image(ttl_seconds=10)

        self.assertEqual(first, "primeira")
        self.assertEqual(second, "segunda")
        self.assertEqual(calls, ["ocr", "ocr"])

    def test_screen_analysis_does_not_reuse_cache_for_different_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            calls = []

            with (
                patch.object(image_tools, "SCREENSHOT_DIR", temp_path / "screens"),
                patch.object(image_tools, "VISION_SCREEN_CACHE_PATH", temp_path / "vision_screen_cache.json"),
                patch.object(image_tools, "_browser_local_image_from_foreground", return_value=None),
                patch.object(image_tools, "_capture_foreground_window", side_effect=write_fake_screen),
                patch.object(image_tools, "_make_screen_content_crop", return_value=None),
                patch.object(image_tools.time, "time", return_value=1000),
                patch.object(image_tools, "_remember_visual_result"),
                patch.object(image_tools, "_ocr_image", side_effect=lambda _path: calls.append("ocr") or {"text": "texto"}),
                patch.object(image_tools, "_semantic_image_analysis", side_effect=["geral", "grafico"]),
            ):
                first = image_tools.analyze_screen_image(mode="general")
                second = image_tools.analyze_screen_image(mode="chart")

        self.assertEqual(first, "geral")
        self.assertEqual(second, "grafico")
        self.assertEqual(calls, ["ocr", "ocr"])


if __name__ == "__main__":
    unittest.main()
