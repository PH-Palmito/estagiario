import unittest
from unittest.mock import Mock, patch

from core.input_device_commands import maybe_handle_input_device_command


class InputDeviceCommandTests(unittest.TestCase):
    def test_list_input_devices(self):
        with patch("core.input_device_commands.format_input_devices", return_value="Microfones disponiveis: 1. Headset."):
            result = maybe_handle_input_device_command("listar microfones", Mock())

        self.assertEqual(result, "Microfones disponiveis: 1. Headset.")

    def test_active_input_device(self):
        with patch("core.input_device_commands.get_active_input_device_info", return_value={"name": "Headset"}):
            result = maybe_handle_input_device_command("microfone atual", Mock())

        self.assertEqual(result, "Microfone ativo: Headset.")

    def test_reset_to_windows_default_refreshes_preferences(self):
        refresh = Mock()
        with (
            patch("core.input_device_commands.update_voice_preferences") as update,
            patch("core.input_device_commands.get_active_input_device_info", return_value={"name": "Default Mic"}),
        ):
            result = maybe_handle_input_device_command("usar microfone padrao", refresh)

        self.assertEqual(result, "Voltei para o microfone padrao do Windows: Default Mic.")
        update.assert_called_once_with({"audio_input_device": ""})
        refresh.assert_called_once_with()

    def test_select_exact_microphone(self):
        refresh = Mock()
        devices = [{"index": 1, "name": "USB Headset"}]
        with (
            patch("core.input_device_commands.format_input_devices", return_value="Microfones disponiveis: 1. USB Headset."),
            patch("core.input_device_commands.list_input_devices", return_value=devices),
            patch("core.input_device_commands.get_active_input_device_info", return_value=None),
            patch("core.input_device_commands.update_voice_preferences") as update,
        ):
            result = maybe_handle_input_device_command("usar microfone USB Headset", refresh)

        self.assertEqual(result, "Agora vou usar este microfone: USB Headset.")
        update.assert_called_once_with({"audio_input_device": "USB Headset"})
        refresh.assert_called_once_with()

    def test_select_already_active_microphone(self):
        refresh = Mock()
        devices = [{"index": 1, "name": "USB Headset"}]
        with (
            patch("core.input_device_commands.format_input_devices", return_value="Microfones disponiveis: 1. USB Headset."),
            patch("core.input_device_commands.list_input_devices", return_value=devices),
            patch("core.input_device_commands.get_active_input_device_info", return_value={"index": 1, "name": "USB Headset"}),
            patch("core.input_device_commands.update_voice_preferences"),
        ):
            result = maybe_handle_input_device_command("microfone headset", refresh)

        self.assertEqual(result, "Microfone confirmado: USB Headset.")

    def test_unknown_microphone_includes_device_list(self):
        devices = [{"index": 1, "name": "USB Headset"}]
        with (
            patch("core.input_device_commands.format_input_devices", return_value="Microfones disponiveis: 1. USB Headset."),
            patch("core.input_device_commands.list_input_devices", return_value=devices),
            patch("core.input_device_commands.get_active_input_device_info", return_value=None),
        ):
            result = maybe_handle_input_device_command("usar microfone espacial", Mock())

        self.assertEqual(
            result,
            "Nao encontrei um microfone parecido com espacial. Microfones disponiveis: 1. USB Headset.",
        )

    def test_unrelated_command_returns_none(self):
        self.assertIsNone(maybe_handle_input_device_command("abrir treino", Mock()))


if __name__ == "__main__":
    unittest.main()
