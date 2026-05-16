import unittest
from pathlib import Path
from unittest.mock import patch

from core.command_schema import Command
from core.ui_bridge import UIBridge


def make_bridge(route=None, process_action=None, training_snapshot=None):
    return UIBridge(
        root_dir=Path("."),
        python_executable="python.exe",
        runtime_patch=lambda: {"assistant_name": "Axel", "status": "INATIVO"},
        normalize_text=lambda text: " ".join(str(text or "").lower().split()),
        route=route or (lambda _text: {"intent": "respond", "target": None}),
        process_action=process_action or (lambda _raw: "invalido"),
        training_snapshot=training_snapshot or (lambda: {"workout": {"label": "hoje", "title": "superior"}}),
    )


class UIBridgeTests(unittest.TestCase):
    @patch("core.ui_bridge.subprocess.Popen")
    @patch("core.ui_bridge.load_ui_state", return_value={"visible": False})
    @patch("core.ui_bridge.update_ui_state")
    def test_show_hud_marks_visible_and_launches_panel(self, update_mock, _load_mock, popen_mock):
        bridge = make_bridge()

        result = bridge.show_hud()

        self.assertEqual(result, "Interface ativada. Deixei o painel no ar.")
        update_mock.assert_any_call({"visible": True})
        self.assertTrue(popen_mock.called)

    @patch("core.ui_bridge.update_ui_state")
    def test_hide_hud_marks_panel_hidden(self, update_mock):
        bridge = make_bridge()
        bridge.hud_started = True

        result = bridge.hide_hud()

        self.assertEqual(result, "Interface oculta.")
        self.assertFalse(bridge.hud_started)
        update_mock.assert_any_call({"visible": False})

    @patch("core.ui_bridge.load_ui_state", return_value={"visible": True})
    def test_status_command_reports_interface_state(self, _load_mock):
        bridge = make_bridge()

        result = bridge.maybe_handle_command("status da interface")

        self.assertEqual(result, "Interface ativa.")

    @patch("core.ui_bridge.subprocess.Popen")
    @patch("core.ui_bridge.load_ui_state", return_value={"visible": False})
    @patch("core.ui_bridge.update_ui_state")
    def test_map_command_routes_to_ui_map(self, update_mock, _load_mock, _popen_mock):
        raw = {"intent": "ui_show_map", "target": {"label": "Salvador"}}
        command = Command(action="ui_show_map", params={"target": {"label": "Salvador"}})
        bridge = make_bridge(route=lambda _text: raw, process_action=lambda _raw: command)

        result = bridge.maybe_handle_command("mostre o mapa de Salvador")

        self.assertEqual(result, "Mapa aberto na interface: Salvador.")
        patch_payloads = [call.args[0] for call in update_mock.call_args_list]
        self.assertTrue(any(payload.get("map_panel_open") for payload in patch_payloads))


if __name__ == "__main__":
    unittest.main()
