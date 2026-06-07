import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.command_schema import Command
from core.golden_commands import GOLDEN_UI_COMMANDS_V2, golden_ui_command_count
from core.ui_bridge import UIBridge
from core.work_mode_commands import maybe_handle_work_mode_command


def make_bridge():
    return UIBridge(
        root_dir=Path("."),
        python_executable="python.exe",
        runtime_patch=lambda: {"assistant_name": "Axel", "status": "INATIVO"},
        normalize_text=lambda text: " ".join(str(text or "").lower().split()),
        route=lambda text: {"intent": "ui_show_map", "target": {"label": "Salvador"}}
        if "mapa" in str(text).lower()
        else {"intent": "respond", "target": None},
        process_action=lambda _raw: Command(action="ui_show_map", params={"target": {"label": "Salvador"}}),
        training_snapshot=lambda: {"workout": {"label": "hoje", "title": "superior"}},
    )


class GoldenUICommandsV2Tests(unittest.TestCase):
    def test_v2_has_expected_command_count(self):
        self.assertEqual(golden_ui_command_count(), 8)

    def test_ids_are_unique(self):
        ids = [item["id"] for item in GOLDEN_UI_COMMANDS_V2]
        self.assertEqual(len(ids), len(set(ids)))

    def test_hud_contains_command_deck_controls(self):
        html = Path("ui/axel_web_hud.html").read_text(encoding="utf-8")

        self.assertIn('id="commandDeckSearch"', html)
        self.assertIn('id="commandDeckFilters"', html)
        self.assertIn('id="commandsVisibleCount"', html)
        self.assertIn("data-command-filter", html)

    @patch("core.ui_bridge.build_project_health_snapshot", return_value={"status": "saudavel"})
    @patch("core.ui_bridge.subprocess.Popen")
    @patch("core.ui_bridge.load_ui_state", return_value={"visible": True})
    @patch("core.ui_bridge.update_ui_state")
    def test_ui_bridge_commands_match_contract(self, _update, _load, _popen, _snapshot):
        bridge = make_bridge()
        items = [item for item in GOLDEN_UI_COMMANDS_V2 if item["surface"] == "ui_bridge"]

        for item in items:
            with self.subTest(command=item["id"]):
                result = bridge.maybe_handle_command(item["phrase"])

                if item.get("expected_response"):
                    self.assertEqual(result, item["expected_response"])
                if item.get("expected_response_contains"):
                    self.assertIn(item["expected_response_contains"], result)

    @patch("core.work_mode_commands.update_ui_state")
    def test_work_mode_commands_match_contract(self, _update):
        items = [item for item in GOLDEN_UI_COMMANDS_V2 if item["surface"] == "work_mode"]

        for item in items:
            with self.subTest(command=item["id"]):
                result = maybe_handle_work_mode_command(item["phrase"], Mock())

                self.assertIsNotNone(result)
                self.assertIn(item["expected_response_contains"], result)


if __name__ == "__main__":
    unittest.main()
