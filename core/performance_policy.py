from __future__ import annotations

from dataclasses import dataclass


BACKGROUND_CANDIDATE_ACTIONS = {
    "daily_briefing",
    "image_analyze_screen",
    "image_analyze_screen_graph",
    "image_analyze_browser",
    "image_analyze_clipboard",
    "investment_financial_report",
}

CACHE_CANDIDATE_ACTIONS = {
    "daily_briefing",
    "image_analyze_screen",
    "image_analyze_screen_graph",
    "investment_memory_summary",
    "investment_financial_report",
    "weather_briefing",
}


@dataclass(frozen=True)
class ActionPerformanceAdvice:
    action: str
    mode: str
    reason: str
    should_background: bool
    should_cache: bool


def action_performance_advice(
    action: str,
    *,
    avg_ms: float,
    max_ms: float,
    count: int = 1,
) -> ActionPerformanceAdvice:
    action_name = str(action or "unknown").strip() or "unknown"
    should_background = action_name in BACKGROUND_CANDIDATE_ACTIONS or max_ms >= 2500 or avg_ms >= 1500
    should_cache = action_name in CACHE_CANDIDATE_ACTIONS or (count >= 2 and avg_ms >= 900)

    if should_background and should_cache:
        mode = "background_with_cache"
        reason = "acao recorrente ou pesada; mover para background e reaproveitar resultado recente"
    elif should_background:
        mode = "background_candidate"
        reason = "acao lenta o bastante para travar a experiencia em foreground"
    elif should_cache:
        mode = "cache_candidate"
        reason = "acao repetida com custo perceptivel; cache reduz latencia"
    else:
        mode = "foreground_ok"
        reason = "latencia aceitavel para execucao direta"

    return ActionPerformanceAdvice(
        action=action_name,
        mode=mode,
        reason=reason,
        should_background=should_background,
        should_cache=should_cache,
    )


def default_action_performance_advice(action: str) -> ActionPerformanceAdvice:
    action_name = str(action or "unknown").strip() or "unknown"
    return action_performance_advice(
        action_name,
        avg_ms=1500 if action_name in BACKGROUND_CANDIDATE_ACTIONS else 0,
        max_ms=2500 if action_name in BACKGROUND_CANDIDATE_ACTIONS else 0,
        count=1,
    )
