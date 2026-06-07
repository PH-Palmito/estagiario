import unittest

from core.router_system import (
    detect_background_status_command,
    detect_keyboard_led_command,
    detect_run_script,
    detect_type_text,
    detect_whatsapp_bridge_command,
    detect_windows_startup_command,
)


class RouterSystemTests(unittest.TestCase):
    def test_windows_startup_enable(self):
        self.assertEqual(
            detect_windows_startup_command("fazer o Axel iniciar junto com o Windows"),
            {"intent": "windows_startup_enable", "target": None},
        )

    def test_windows_startup_disable(self):
        self.assertEqual(
            detect_windows_startup_command("desativar iniciar junto com o Windows"),
            {"intent": "windows_startup_disable", "target": None},
        )

    def test_windows_startup_status(self):
        self.assertEqual(
            detect_windows_startup_command("status iniciar junto com o Windows"),
            {"intent": "windows_startup_status", "target": None},
        )

    def test_run_script(self):
        self.assertEqual(
            detect_run_script("execute script scripts/teste.py"),
            {"intent": "run_script", "target": "scripts/teste.py"},
        )

    def test_background_status(self):
        self.assertEqual(
            detect_background_status_command("status das tarefas em segundo plano"),
            {"intent": "background_status", "target": None},
        )

    def test_background_latest_result(self):
        self.assertEqual(
            detect_background_status_command("resultado da ultima tarefa em segundo plano"),
            {"intent": "background_latest_result", "target": None},
        )

    def test_background_notifications(self):
        self.assertEqual(
            detect_background_status_command("notificacoes em segundo plano"),
            {"intent": "background_notifications", "target": None},
        )

    def test_whatsapp_bridge_status(self):
        self.assertEqual(
            detect_whatsapp_bridge_command("status do whatsapp"),
            {"intent": "whatsapp.status", "target": None},
        )

    def test_whatsapp_bridge_start(self):
        self.assertEqual(
            detect_whatsapp_bridge_command("iniciar ponte whatsapp"),
            {"intent": "whatsapp.start_local_bridge", "target": None},
        )

    def test_whatsapp_simulate_message(self):
        self.assertEqual(
            detect_whatsapp_bridge_command("simular whatsapp briefing"),
            {"intent": "whatsapp.simulate_message", "target": "briefing"},
        )

    def test_keyboard_led_status(self):
        self.assertEqual(
            detect_keyboard_led_command("status do led do teclado"),
            {"intent": "keyboard_led_status", "target": None},
        )

    def test_keyboard_led_color(self):
        self.assertEqual(
            detect_keyboard_led_command("ligar led do teclado azul perfil foco"),
            {"intent": "keyboard_led_on", "target": {"color": "azul", "profile": "foco", "effect": "foco"}},
        )

    def test_type_text(self):
        self.assertEqual(
            detect_type_text("digite olá mundo"),
            {"intent": "type_text", "target": None, "content": "olá mundo"},
        )

    def test_type_text_without_content(self):
        self.assertIsNone(detect_type_text("digite"))


if __name__ == "__main__":
    unittest.main()
