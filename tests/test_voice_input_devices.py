import unittest

from voice.input_devices import format_input_devices, resolve_input_device


class VoiceInputDeviceTests(unittest.TestCase):
    def test_resolve_input_device_prefers_exact_preference(self):
        devices = [
            {"index": 1, "name": "Microfone Padrao", "is_default": True},
            {"index": 2, "name": "USB Headset", "is_default": False},
        ]

        index, device = resolve_input_device({"audio_input_device": "USB Headset"}, devices=devices)

        self.assertEqual(index, 2)
        self.assertEqual(device["name"], "USB Headset")

    def test_resolve_input_device_falls_back_to_default(self):
        devices = [
            {"index": 1, "name": "Microfone Padrao", "is_default": True},
            {"index": 2, "name": "USB Headset", "is_default": False},
        ]

        index, device = resolve_input_device({"audio_input_device": "Nao existe"}, devices=devices)

        self.assertEqual(index, 1)
        self.assertEqual(device["name"], "Microfone Padrao")

    def test_format_input_devices_marks_default_and_active(self):
        result = format_input_devices(
            [{"index": 1, "name": "USB Headset", "is_default": True}],
            {"index": 1, "name": "USB Headset"},
        )

        self.assertEqual(
            result,
            "Microfones disponiveis: 1. USB Headset (padrao do Windows, em uso pelo assistente).",
        )


if __name__ == "__main__":
    unittest.main()
