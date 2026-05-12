from core.command_schema import Command


ALLOWED_ACTIONS = {
    "respond",
    "start_conversation",
    "stop_conversation",
    "open_app",
    "smart_open",
    "smart_open_choice",
    "remember_target_kind",
    "forget_smart_memory",
    "list_smart_memory",
    "close_app",
    "smart_close_app",
    "focus_app",
    "minimize_app",
    "maximize_app",
    "restore_app",
    "run_script",
    "type_text",
    "open_url",
    "ui_show_map",
    "weather_summary",
    "daily_briefing",
    "reminder_add",
    "reminder_list",
    "reminder_remove",
    "agenda_add",
    "agenda_list_today",
    "agenda_list_tomorrow",
    "agenda_list_all",
    "agenda_remove",
    "browser_new_tab",
    "browser_close_tab",
    "browser_next_tab",
    "browser_prev_tab",
    "browser_search",
    "browser_find",
    "browser_click_text",
    "browser_describe_listed_item",
    "browser_scroll_down",
    "browser_scroll_down_small",
    "browser_scroll_up",
    "browser_scroll_up_small",
    "browser_scroll_top",
    "browser_scroll_bottom",
    "browser_back",
    "browser_forward",
    "browser_refresh",
    "browser_open_first_result",
    "browser_open_focused_item",
    "browser_click_center",
    "browser_cheapest_listed_item",
    "browser_explain_screen",
    "browser_investment_snapshot",
    "browser_open_wallet_and_summarize",
    "investment_refresh_public_wallet",
    "investment_memory_summary",
    "investment_financial_report",
    "investment_memory_answer",
    "investment_memory_status",
    "investment_set_price_ceiling",
    "investment_set_auto_ceiling_margin",
    "investment_get_auto_ceiling_settings",
    "investment_add_watchlist",
    "investment_remove_watchlist",
    "investment_list_watchlist",
    "investment_set_thesis",
    "browser_summarize_screen",
    "browser_zoom_in",
    "browser_describe_screen",
    "browser_read_selection",
    "browser_read_selected_products",
    "browser_translate_last_selection",
    "browser_translate_selection",
    "browser_read_more",
    "browser_click_listed_item",
    "browser_zoom_out",
    "browser_zoom_reset",
    "browser_search_site",
    "browser_search_music",
    "browser_surprise_music",
    "browser_music_session",
    "browser_queue_music",
    "spotify_diagnostic",
    "spotify_like_current_track",
    "spotify_dislike_current_track",
    "spotify_more_like_current_track",
    "spotify_less_music_vibe",
    "media_play_pause",
    "media_next",
    "media_previous",
    "media_play_pause_target",
    "media_play_target",
    "media_pause_target",
    "media_next_target",
    "media_previous_target",
    "volume_up",
    "volume_down",
    "volume_mute",
    "bluetooth_on",
    "bluetooth_off",
    "bluetooth_settings",
    "bluetooth_status",
    "web_google_search",
    "web_open_chatgpt",
    "code_inspect_workspace",
    "code_inspect_target",
    "code_inspect_selection",
    "image_analyze",
    "image_analyze_screen",
    "image_analyze_screen_graph",
    "image_analyze_browser",
    "image_analyze_clipboard",
    "vision_status",
    "vision_install_hint",
    "vision_download_light_model",
    "vision_active_model",
    "vision_last_analysis",
    "vision_answer_question",
    "list_files",
    "file_create",
    "file_write",
    "file_append",
    "file_replace",
    "file_read",
    "file_delete",
    "file_copy",
    "file_move",
    "file_rename",
    "folder_create",
    "run_macro",
}


REQUIRED_FIELDS = {
    "respond": ["message"],
    "start_conversation": [],
    "stop_conversation": [],
    "open_app": ["target"],
    "smart_open": ["target"],
    "smart_open_choice": ["target", "kind"],
    "remember_target_kind": ["target", "kind"],
    "forget_smart_memory": ["target"],
    "list_smart_memory": [],
    "close_app": ["target"],
    "smart_close_app": ["target"],
    "focus_app": ["target"],
    "minimize_app": ["target"],
    "maximize_app": ["target"],
    "restore_app": ["target"],
    "run_script": ["target"],
    "type_text": ["content"],
    "open_url": ["target"],
    "ui_show_map": ["target"],
    "weather_summary": ["location"],
    "daily_briefing": [],
    "reminder_add": ["text"],
    "reminder_list": [],
    "reminder_remove": ["index"],
    "agenda_add": ["text"],
    "agenda_list_today": [],
    "agenda_list_tomorrow": [],
    "agenda_list_all": [],
    "agenda_remove": ["index"],
    "browser_new_tab": [],
    "browser_close_tab": [],
    "browser_next_tab": [],
    "browser_prev_tab": [],
    "browser_search": ["query"],
    "browser_find": ["query"],
    "browser_click_text": ["query"],
    "browser_describe_listed_item": ["index"],
    "browser_scroll_down": [],
    "browser_scroll_down_small": [],
    "browser_scroll_up": [],
    "browser_scroll_up_small": [],
    "browser_scroll_top": [],
    "browser_scroll_bottom": [],
    "browser_back": [],
    "browser_forward": [],
    "browser_refresh": [],
    "browser_open_first_result": [],
    "browser_open_focused_item": [],
    "browser_click_center": [],
    "browser_cheapest_listed_item": [],
    "browser_explain_screen": [],
    "browser_investment_snapshot": [],
    "browser_open_wallet_and_summarize": [],
    "investment_refresh_public_wallet": [],
    "investment_memory_summary": [],
    "investment_financial_report": [],
    "investment_memory_answer": ["question"],
    "investment_memory_status": [],
    "investment_set_price_ceiling": ["ticker", "price"],
    "investment_set_auto_ceiling_margin": ["value"],
    "investment_get_auto_ceiling_settings": [],
    "investment_add_watchlist": ["ticker"],
    "investment_remove_watchlist": ["ticker"],
    "investment_list_watchlist": [],
    "investment_set_thesis": ["ticker", "thesis"],
    "browser_summarize_screen": [],
    "browser_describe_screen": [],
    "browser_read_selection": [],
    "browser_read_selected_products": [],
    "browser_translate_last_selection": [],
    "browser_translate_selection": [],
    "browser_read_more": [],
    "browser_click_listed_item": ["index"],
    "browser_zoom_in": [],
    "browser_zoom_out": [],
    "browser_zoom_reset": [],
    "browser_search_site": ["site", "query"],
    "browser_search_music": ["service", "query"],
    "browser_surprise_music": ["service"],
    "browser_music_session": ["service", "vibe"],
    "browser_queue_music": ["service", "query"],
    "spotify_diagnostic": [],
    "spotify_like_current_track": [],
    "spotify_dislike_current_track": [],
    "spotify_more_like_current_track": [],
    "spotify_less_music_vibe": ["vibe"],
    "media_play_pause": [],
    "media_next": [],
    "media_previous": [],
    "media_play_pause_target": ["target"],
    "media_play_target": ["target"],
    "media_pause_target": ["target"],
    "media_next_target": ["target"],
    "media_previous_target": ["target"],
    "volume_up": [],
    "volume_down": [],
    "volume_mute": [],
    "bluetooth_on": [],
    "bluetooth_off": [],
    "bluetooth_settings": [],
    "bluetooth_status": [],
    "web_google_search": ["query"],
    "web_open_chatgpt": [],
    "code_inspect_workspace": [],
    "code_inspect_target": ["target"],
    "code_inspect_selection": [],
    "image_analyze": ["target"],
    "image_analyze_screen": [],
    "image_analyze_screen_graph": [],
    "image_analyze_browser": [],
    "image_analyze_clipboard": [],
    "vision_status": [],
    "vision_install_hint": [],
    "vision_download_light_model": [],
    "vision_active_model": [],
    "vision_last_analysis": [],
    "vision_answer_question": ["question"],
    "list_files": [],
    "file_create": ["path"],
    "file_write": ["path"],
    "file_append": ["path"],
    "file_replace": ["path", "old_text", "new_text"],
    "file_read": ["path"],
    "file_delete": ["path"],
    "file_copy": ["src", "dst"],
    "file_move": ["src", "dst"],
    "file_rename": ["src", "new_name"],
    "folder_create": ["path"],
    "run_macro": ["steps"],
}


def validate_command(command: Command):
    if command.action not in ALLOWED_ACTIONS:
        return False, f"Ação não permitida: {command.action}"

    required = REQUIRED_FIELDS.get(command.action, [])

    for field in required:
        value = command.params.get(field)

        if value in (None, "", []):
            if field == "path":
                return False, "Qual arquivo?"
            if field == "src":
                return False, "Qual arquivo de origem?"
            if field == "dst":
                return False, "Qual destino?"
            if field == "new_name":
                return False, "Qual o novo nome?"
            if field == "query":
                return False, "Qual pesquisa?"
            if field == "target":
                return False, "Qual alvo?"
            if field == "content":
                return False, "Qual texto?"
            if field == "text":
                return False, "Qual compromisso devo registrar?"
            if field == "location":
                return False, "Qual lugar devo consultar?"
            if field == "vibe":
                return False, "Qual clima ou gênero musical?"
            if field == "index":
                return False, "Qual item?"
            if field == "kind":
                return False, "Isso e app ou site?"
            if field == "site":
                return False, "Qual site?"
            if field == "service":
                return False, "Qual servico?"
            if field == "question":
                return False, "Qual pergunta?"
            if field == "steps":
                return False, "A macro está vazia."
            if field == "ticker":
                return False, "Qual ticker?"
            if field == "price":
                return False, "Qual preço?"
            if field == "value":
                return False, "Qual valor?"
            if field == "thesis":
                return False, "Qual tese?"
            return False, f"Parâmetro obrigatório ausente: {field}"

    return True, None
