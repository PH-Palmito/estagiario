from core.command_schema import Command


ALLOWED_ACTIONS = {
    "respond",
    "open_app",
    "close_app",
    "run_script",
    "open_url",
    "browser_new_tab",
    "browser_close_tab",
    "browser_next_tab",
    "browser_prev_tab",
    "browser_search",
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
    "open_app": ["target"],
    "close_app": ["target"],
    "run_script": ["target"],
    "open_url": ["target"],
    "browser_new_tab": [],
    "browser_close_tab": [],
    "browser_next_tab": [],
    "browser_prev_tab": [],
    "browser_search": ["query"],
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
            if field == "steps":
                return False, "A macro está vazia."
            return False, f"Parâmetro obrigatório ausente: {field}"

    return True, None
