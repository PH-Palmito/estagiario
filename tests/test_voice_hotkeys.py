import unittest

from voice.hotkeys import (
    VIRTUAL_KEYS,
    consume_key_press,
    hotkey_name,
    hotkey_vk,
    speech_interrupt_keys,
)


class VoiceHotkeyTests(unittest.TestCase):
    def test_hotkey_name_and_vk_use_preferences_with_fallback(self):
        name = hotkey_name({"trigger_hotkey": "f10"}, "trigger_hotkey", "F8")

        self.assertEqual(name, "F10")
        self.assertEqual(hotkey_vk(name, "F8"), VIRTUAL_KEYS["F10"])
        self.assertEqual(hotkey_vk("INVALID", "F8"), VIRTUAL_KEYS["F8"])

    def test_speech_interrupt_keys_include_hotkey_toggle_and_escape(self):
        result = speech_interrupt_keys(VIRTUAL_KEYS["F8"], VIRTUAL_KEYS["F9"])

        self.assertEqual(result, {VIRTUAL_KEYS["F8"], VIRTUAL_KEYS["F9"], VIRTUAL_KEYS["ESC"]})

    def test_consume_key_press_only_reports_transition_to_down(self):
        state = {}
        sequence = iter([0x8000, 0x8000, 0, 0x8000])

        self.assertTrue(consume_key_press(123, key_state=state, get_async_key_state=lambda _vk: next(sequence)))
        self.assertFalse(consume_key_press(123, key_state=state, get_async_key_state=lambda _vk: next(sequence)))
        self.assertFalse(consume_key_press(123, key_state=state, get_async_key_state=lambda _vk: next(sequence)))
        self.assertTrue(consume_key_press(123, key_state=state, get_async_key_state=lambda _vk: next(sequence)))


if __name__ == "__main__":
    unittest.main()
