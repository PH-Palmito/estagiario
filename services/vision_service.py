from __future__ import annotations

from tools.image_tools import (
    analyze_browser_image,
    analyze_clipboard_image,
    analyze_graph_target,
    analyze_image_target,
    analyze_screen_graph,
    analyze_screen_image,
)
from tools.vision_tools import (
    active_vision_model,
    answer_visual_question_with_context_memory,
    last_visual_analysis,
    start_light_vision_model_download,
    vision_install_hint,
    vision_status,
)


def analyze_image(path: str | None = None) -> str:
    return analyze_image_target(path)


def analyze_graph(path: str | None = None) -> str:
    return analyze_graph_target(path)


def analyze_screen() -> str:
    return analyze_screen_image()


def analyze_screen_chart() -> str:
    return analyze_screen_graph()


def analyze_browser() -> str:
    return analyze_browser_image()


def analyze_clipboard() -> str:
    return analyze_clipboard_image()


def answer_question(question: str) -> str:
    return answer_visual_question_with_context_memory(question)
