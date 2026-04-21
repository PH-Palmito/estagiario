from core.command_schema import Command


def normalize_action(old_action: dict) -> Command:
    intent = old_action.get("intent")
    target = old_action.get("target")
    content = old_action.get("content")
    old_text = old_action.get("old_text")
    new_text = old_action.get("new_text")

    if intent == "respond":
        return Command(
            action="respond",
            params={"message": old_action.get("response", "Não entendi.")},
            source="router",
        )

    if intent in {"start_conversation", "stop_conversation"}:
        return Command(
            action=intent,
            params={},
            source="router",
        )

    if intent == "open_app":
        return Command(
            action="open_app",
            params={"target": target},
            source="router",
        )

    if intent == "smart_open":
        return Command(
            action="smart_open",
            params={"target": target},
            source="router",
        )

    if intent == "smart_open_choice":
        return Command(
            action="smart_open_choice",
            params={
                "target": target.get("name") if isinstance(target, dict) else None,
                "kind": target.get("kind") if isinstance(target, dict) else None,
            },
            source="router",
        )

    if intent == "remember_target_kind":
        return Command(
            action="remember_target_kind",
            params={
                "target": target.get("name") if isinstance(target, dict) else None,
                "kind": target.get("kind") if isinstance(target, dict) else None,
            },
            source="router",
        )

    if intent == "forget_smart_memory":
        return Command(
            action="forget_smart_memory",
            params={"target": target},
            source="router",
        )

    if intent == "list_smart_memory":
        return Command(
            action="list_smart_memory",
            params={},
            source="router",
        )

    if intent == "close_app":
        return Command(
            action="close_app",
            params={"target": target},
            source="router",
        )

    if intent == "smart_close_app":
        return Command(
            action="smart_close_app",
            params={"target": target},
            source="router",
        )

    if intent == "context_close":
        return Command(
            action="context_close",
            params={},
            source="router",
        )

    if intent == "focus_app":
        return Command(
            action="focus_app",
            params={"target": target},
            source="router",
        )

    if intent == "minimize_app":
        return Command(
            action="minimize_app",
            params={"target": target},
            source="router",
        )

    if intent == "maximize_app":
        return Command(
            action="maximize_app",
            params={"target": target},
            source="router",
        )

    if intent == "restore_app":
        return Command(
            action="restore_app",
            params={"target": target},
            source="router",
        )

    if intent == "run_script":
        return Command(
            action="run_script",
            params={"target": target},
            source="router",
        )

    if intent == "open_url":
        return Command(
            action="open_url",
            params={"target": target},
            source="router",
        )

    if intent == "google_search":
        return Command(
            action="web_google_search",
            params={"query": target},
            source="router",
        )

    if intent == "browser_new_tab":
        return Command(
            action="browser_new_tab",
            params={},
            source="router",
        )

    if intent == "browser_close_tab":
        return Command(
            action="browser_close_tab",
            params={},
            source="router",
        )

    if intent == "browser_next_tab":
        return Command(
            action="browser_next_tab",
            params={},
            source="router",
        )

    if intent == "browser_prev_tab":
        return Command(
            action="browser_prev_tab",
            params={},
            source="router",
        )

    if intent == "browser_search":
        return Command(
            action="browser_search",
            params={"query": target},
            source="router",
        )

    if intent in {
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
        "browser_describe_screen",
        "browser_explain_screen",
        "browser_summarize_screen",
        "browser_read_selection",
        "browser_read_selected_products",
        "browser_translate_last_selection",
        "browser_translate_selection",
        "browser_read_more",
        "browser_zoom_in",
        "browser_zoom_out",
        "browser_zoom_reset",
    }:
        return Command(
            action=intent,
            params={},
            source="router",
        )

    if intent == "browser_click_text":
        return Command(
            action="browser_click_text",
            params={"query": target},
            source="router",
        )

    if intent == "browser_click_listed_item":
        return Command(
            action="browser_click_listed_item",
            params={"index": target},
            source="router",
        )

    if intent == "browser_describe_listed_item":
        return Command(
            action="browser_describe_listed_item",
            params={"index": target},
            source="router",
        )

    if intent == "browser_find":
        return Command(
            action="browser_find",
            params={"query": target},
            source="router",
        )

    if intent == "browser_search_site":
        return Command(
            action="browser_search_site",
            params={
                "site": target.get("site") if isinstance(target, dict) else None,
                "query": target.get("query") if isinstance(target, dict) else None,
            },
            source="router",
        )

    if intent == "browser_search_music":
        return Command(
            action="browser_search_music",
            params={
                "service": target.get("service") if isinstance(target, dict) else None,
                "query": target.get("query") if isinstance(target, dict) else None,
            },
            source="router",
        )

    if intent == "spotify_diagnostic":
        return Command(
            action="spotify_diagnostic",
            params={},
            source="router",
        )

    if intent in {
        "media_play_pause",
        "media_next",
        "media_previous",
        "volume_up",
        "volume_down",
        "volume_mute",
    }:
        return Command(
            action=intent,
            params={},
            source="router",
        )

    if intent in {
        "bluetooth_on",
        "bluetooth_off",
        "bluetooth_settings",
        "bluetooth_status",
    }:
        return Command(
            action=intent,
            params={},
            source="router",
        )

    if intent in {
        "media_play_pause_target",
        "media_play_target",
        "media_pause_target",
        "media_next_target",
        "media_previous_target",
    }:
        return Command(
            action=intent,
            params={"target": target},
            source="router",
        )

    if intent == "open_chatgpt":
        return Command(
            action="web_open_chatgpt",
            params={},
            source="router",
        )

    if intent == "list_files":
        return Command(
            action="list_files",
            params={"path": target or ""},
            source="router",
        )

    if intent == "create_file":
        return Command(
            action="file_create",
            params={"path": target},
            source="router",
        )

    if intent == "write_file":
        return Command(
            action="file_write",
            params={
                "path": target,
                "content": content or "",
            },
            source="router",
        )

    if intent == "append_file":
        return Command(
            action="file_append",
            params={
                "path": target,
                "content": content or "",
            },
            source="router",
        )

    if intent == "replace_in_file":
        return Command(
            action="file_replace",
            params={
                "path": target,
                "old_text": old_text or "",
                "new_text": new_text or "",
            },
            source="router",
            requires_confirmation=False,
        )

    if intent == "read_file":
        return Command(
            action="file_read",
            params={"path": target},
            source="router",
        )

    if intent == "delete_file":
        return Command(
            action="file_delete",
            params={"path": target},
            source="router",
            requires_confirmation=True,
        )

    if intent == "copy_file":
        return Command(
            action="file_copy",
            params={
                "src": target.get("src") if isinstance(target, dict) else None,
                "dst": target.get("dst") if isinstance(target, dict) else None,
            },
            source="router",
        )

    if intent == "move_file":
        return Command(
            action="file_move",
            params={
                "src": target.get("src") if isinstance(target, dict) else None,
                "dst": target.get("dst") if isinstance(target, dict) else None,
            },
            source="router",
            requires_confirmation=True,
        )

    if intent == "rename_file":
        return Command(
            action="file_rename",
            params={
                "src": target.get("src") if isinstance(target, dict) else None,
                "new_name": target.get("new_name") if isinstance(target, dict) else None,
            },
            source="router",
        )

    if intent == "create_folder":
        return Command(
            action="folder_create",
            params={"path": target},
            source="router",
        )

    if intent == "run_macro":
        return Command(
            action="run_macro",
            params={"steps": target or []},
            source="router",
        )

    return Command(
        action="respond",
        params={"message": old_action.get("response", "Não entendi.")},
        source="fallback",
        confidence=0.0,
    )
