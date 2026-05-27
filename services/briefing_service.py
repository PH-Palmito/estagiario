from __future__ import annotations

from tools.briefing_tools import daily_briefing as build_daily_briefing
from tools.briefing_tools import daily_routine as build_daily_routine


def daily_briefing() -> str:
    return build_daily_briefing()


def daily_routine() -> str:
    return build_daily_routine()
