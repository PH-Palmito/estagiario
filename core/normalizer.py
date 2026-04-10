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

    if intent == "open_app":
        return Command(
            action="open_app",
            params={"target": target},
            source="router",
        )

    if intent == "close_app":
        return Command(
            action="close_app",
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

    if intent == "close_app":
        return Command(
            action="close_app",
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
