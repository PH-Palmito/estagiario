import unittest
from unittest.mock import patch

from core.router_macros import (
    detect_create_macro_start,
    detect_delete_macro,
    detect_list_macros,
    detect_run_macro,
    detect_run_routine,
)


class RouterMacrosTests(unittest.TestCase):
    def test_create_macro_start(self):
        self.assertEqual(
            detect_create_macro_start("crie macro briefing rapido"),
            {"intent": "start_macro", "target": "briefing rapido"},
        )

    @patch("core.router_macros.get_macro", return_value=[{"intent": "daily_briefing"}])
    def test_run_macro(self, _get_macro):
        self.assertEqual(
            detect_run_macro("execute briefing"),
            {"intent": "run_macro", "target": [{"intent": "daily_briefing"}]},
        )

    @patch("core.router_macros.get_routine", side_effect=lambda name: [{"intent": "focus"}] if name == "modo foco" else None)
    def test_run_routine_with_mode_prefix(self, _get_routine):
        self.assertEqual(
            detect_run_routine("rotina foco"),
            {"intent": "run_routine", "target": [{"intent": "focus"}], "name": "modo foco"},
        )

    @patch("core.router_macros.list_macros", return_value=["briefing", "estudo"])
    def test_list_macros(self, _list_macros):
        self.assertEqual(
            detect_list_macros("listar macros"),
            {"intent": "respond", "target": None, "response": "Macros: briefing, estudo"},
        )

    @patch("core.router_macros.delete_macro", return_value=True)
    def test_delete_macro(self, _delete_macro):
        self.assertEqual(
            detect_delete_macro("delete macro briefing"),
            {"intent": "respond", "target": None, "response": "Macro 'briefing' removida."},
        )


if __name__ == "__main__":
    unittest.main()
