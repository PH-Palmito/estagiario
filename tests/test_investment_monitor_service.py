import unittest
from unittest.mock import patch

from services import investment_monitor_service as monitor


class InvestmentMonitorServiceTests(unittest.TestCase):
    def test_detects_material_portfolio_alert(self):
        self.assertTrue(monitor.is_material_portfolio_alert("Monitoramento atual da carteira: Preco-teto com mudanca relevante."))
        self.assertFalse(monitor.is_material_portfolio_alert("No momento, eu nao encontrei sinal forte de monitoramento."))

    def test_portfolio_monitor_message_uses_investment_answer(self):
        with patch.object(monitor.investment_service, "investment_answer", return_value="alerta"):
            result = monitor.portfolio_monitor_message()

        self.assertEqual(result.message, "alerta")
        self.assertTrue(result.has_alert)

    def test_publish_alert_updates_ui_and_voice_when_enabled(self):
        with (
            patch("memory.ui_state.append_ui_notification") as ui_notify,
            patch("memory.ui_state.load_ui_state", return_value={"voice_notifications_enabled": True}),
            patch("memory.ui_state.append_voice_notification") as voice_notify,
        ):
            monitor.publish_portfolio_monitor_alert("Alerta de carteira")

        ui_notify.assert_called_once_with("investments", "Alerta de carteira", level="warning")
        voice_notify.assert_called_once_with("Alerta de carteira", source="investment_monitor")

    def test_run_once_notifies_only_when_alert_exists(self):
        with (
            patch.object(monitor, "portfolio_monitor_message", return_value=monitor.PortfolioMonitorResult("ok", True)),
            patch.object(monitor, "publish_portfolio_monitor_alert") as publish,
        ):
            result = monitor.run_portfolio_monitor_once(notify=True)

        self.assertEqual(result, "ok")
        publish.assert_called_once_with("ok")


if __name__ == "__main__":
    unittest.main()
