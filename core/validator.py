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
    "open_url",
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
    "spotify_diagnostic",
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
    "open_url": ["target"],
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
    "spotify_diagnostic": [],
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
            if field == "index":
                return False, "Qual item?"
            if field == "kind":
                return False, "Isso e app ou site?"
            if field == "site":
                return False, "Qual site?"
            if field == "service":
                return False, "Qual servico?"
            if field == "steps":
                return False, "A macro está vazia."
            return False, f"Parâmetro obrigatório ausente: {field}"

    return True, None
