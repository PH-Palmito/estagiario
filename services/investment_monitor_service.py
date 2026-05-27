from __future__ import annotations

from dataclasses import dataclass

from services import investment_service

NO_SIGNAL_MARKERS = (
    "nao encontrei sinal forte",
    "não encontrei sinal forte",
    "sem alerta critico",
    "sem alerta crítico",
    "ainda nao tenho dados suficientes",
    "ainda não tenho dados suficientes",
)


@dataclass(frozen=True)
class PortfolioMonitorResult:
    message: str
    has_alert: bool


def is_material_portfolio_alert(message: str) -> bool:
    compact = " ".join(str(message or "").split()).strip().lower()
    if not compact:
        return False
    return not any(marker in compact for marker in NO_SIGNAL_MARKERS)


def portfolio_monitor_message() -> PortfolioMonitorResult:
    message = investment_service.investment_answer("radar da carteira")
    return PortfolioMonitorResult(
        message=str(message or "").strip(),
        has_alert=is_material_portfolio_alert(str(message or "")),
    )


def publish_portfolio_monitor_alert(message: str) -> None:
    if not is_material_portfolio_alert(message):
        return
    from memory.ui_state import append_ui_notification, append_voice_notification, load_ui_state

    compact = " ".join(str(message or "").split()).strip()
    append_ui_notification("investments", compact, level="warning")
    if bool(load_ui_state().get("voice_notifications_enabled")):
        append_voice_notification(compact, source="investment_monitor")


def run_portfolio_monitor_once(*, notify: bool = False) -> str:
    result = portfolio_monitor_message()
    if notify and result.has_alert:
        publish_portfolio_monitor_alert(result.message)
    return result.message
