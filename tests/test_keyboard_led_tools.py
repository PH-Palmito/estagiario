import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import keyboard_led_tools


class KeyboardLedToolsTests(unittest.TestCase):
    def test_keyboard_led_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "keyboard_led_state.json"
            with patch.object(keyboard_led_tools, "KEYBOARD_LED_STATE_PATH", path):
                enabled = keyboard_led_tools.keyboard_led_on(color="azul", profile="foco", effect="pulso")
                status = keyboard_led_tools.keyboard_led_status()
                disabled = keyboard_led_tools.keyboard_led_off()

        self.assertIn("LED do teclado ligado", enabled)
        self.assertIn("cor azul", status)
        self.assertIn("perfil foco", status)
        self.assertIn("LED do teclado desligado", disabled)


if __name__ == "__main__":
    unittest.main()
