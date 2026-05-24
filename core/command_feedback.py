from __future__ import annotations

from collections.abc import Callable, Mapping

NextPhrase = Callable[[str, tuple[str, ...]], str]

STATIC_PROGRESS_MESSAGES = {
    "image_analyze_screen": "Lendo a imagem da tela...",
    "image_analyze_screen_graph": "Lendo o gráfico da tela...",
    "image_analyze_browser": "Lendo o visual do navegador...",
    "image_analyze_clipboard": "Lendo a imagem copiada...",
    "image_analyze": "Analisando a imagem...",
}

VARIANT_PROGRESS_KEYS = {
    "vision_answer_question": "vision_answer_question",
    "browser_describe_screen": "browser_describe_screen",
    "browser_explain_screen": "browser_explain_screen",
    "browser_summarize_screen": "browser_summarize_screen",
    "browser_investment_snapshot": "browser_investment_snapshot",
    "browser_open_wallet_and_summarize": "browser_open_wallet_and_summarize",
    "investment_refresh_public_wallet": "investment_refresh_public_wallet",
    "investment_memory_summary": "investment_memory_summary",
    "investment_memory_answer": "investment_memory_answer",
    "investment_memory_status": "investment_memory_status",
    "browser_read_selection": "browser_read_selection",
    "browser_read_selected_products": "browser_read_selected_products",
    "browser_translate_last_selection": "browser_translate_last_selection",
    "browser_translate_selection": "browser_translate_selection",
    "browser_read_more": "browser_read_more",
    "browser_find": "browser_find",
    "browser_search_site": "browser_search_site",
    "code_inspect_workspace": "code_inspect_workspace",
    "code_inspect_target": "code_inspect_target",
    "code_inspect_selection": "code_inspect_selection",
    "weather_summary": "weather_summary",
    "daily_briefing": "daily_briefing",
    "agenda_list_today": "agenda_list",
    "agenda_list_tomorrow": "agenda_list",
    "agenda_list_all": "agenda_list",
}


def action_progress_message(
    command,
    *,
    next_phrase: NextPhrase,
    variants: Mapping[str, tuple[str, ...]],
) -> str | None:
    action_name = getattr(command, "action", "")
    if action_name in STATIC_PROGRESS_MESSAGES:
        return STATIC_PROGRESS_MESSAGES[action_name]

    variant_key = VARIANT_PROGRESS_KEYS.get(action_name)
    if not variant_key:
        return None

    options = variants.get(variant_key)
    if not options:
        return None

    return next_phrase(f"progress_{variant_key}", options)


def command_preview(command) -> str:
    if command is None:
        return ""

    action = getattr(command, "action", None)
    params = getattr(command, "params", None)

    if action and isinstance(params, dict) and params:
        summary = ", ".join(f"{key}={value}" for key, value in list(params.items())[:3])
        return f"{action} ({summary})"

    if action:
        return str(action)

    return str(command)
