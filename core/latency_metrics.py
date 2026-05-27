from __future__ import annotations

import time
from collections.abc import Callable

LogEvent = Callable[..., None]
NowFn = Callable[[], float]


def duration_ms(started_at: float, *, now_fn: NowFn = time.perf_counter) -> float:
    return round(max(0.0, now_fn() - started_at) * 1000, 2)


def log_latency_stage(
    log_event: LogEvent,
    stage: str,
    started_at: float,
    *,
    now_fn: NowFn = time.perf_counter,
    **payload,
) -> None:
    log_event(
        "latency_stage",
        stage=str(stage or "unknown"),
        duration_ms=duration_ms(started_at, now_fn=now_fn),
        **payload,
    )
