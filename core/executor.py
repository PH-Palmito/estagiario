from core.command_schema import Command
from core.normalizer import normalize_action
from tools.browser_tools import (
    browser_close_tab,
    browser_new_tab,
    browser_next_tab,
    browser_prev_tab,
    browser_search,
)
from tools.system_tools import close_app, open_app, open_url, run_script
from tools.file_tools import (
    list_files,
    create_file,
    write_file,
    read_file,
    append_file,
    replace_in_file,
    delete_file,
    copy_file,
    move_file,
    rename_file,
)
from tools.folder_tools import create_folder
from tools.web_tools import google_search, open_chatgpt


def execute_many(raw_steps):
    results = []

    for step in raw_steps:
        try:
            if isinstance(step, dict) and "action" not in step:
                command = normalize_action(step)
            elif isinstance(step, Command):
                command = step
            else:
                results.append("Etapa inválida.")
                continue

            result = execute(command)
            results.append(result)
        except Exception as e:
            results.append(f"Erro em macro: {e}")

    return "\n".join(results)


ACTIONS = {
    "open_app": lambda p: open_app(p["target"]),
    "close_app": lambda p: close_app(p["target"]),
    "run_script": lambda p: run_script(p["target"]),
    "open_url": lambda p: open_url(p["target"]),
    "browser_new_tab": lambda p: browser_new_tab(),
    "browser_close_tab": lambda p: browser_close_tab(),
    "browser_next_tab": lambda p: browser_next_tab(),
    "browser_prev_tab": lambda p: browser_prev_tab(),
    "browser_search": lambda p: browser_search(p["query"]),
    "list_files": lambda p: list_files(p.get("path", "")),
    "file_create": lambda p: create_file(p["path"]),
    "file_write": lambda p: write_file(p["path"], p.get("content", "")),
    "file_append": lambda p: append_file(p["path"], p.get("content", "")),
    "file_replace": lambda p: replace_in_file(
        p["path"],
        p["old_text"],
        p["new_text"],
    ),
    "file_read": lambda p: read_file(p["path"]),
    "file_delete": lambda p: delete_file(p["path"]),
    "file_copy": lambda p: copy_file(p["src"], p["dst"]),
    "file_move": lambda p: move_file(p["src"], p["dst"]),
    "file_rename": lambda p: rename_file(p["src"], p["new_name"]),
    "folder_create": lambda p: create_folder(p["path"]),
    "web_google_search": lambda p: google_search(p["query"]),
    "web_open_chatgpt": lambda p: open_chatgpt(),
    "run_macro": lambda p: execute_many(p["steps"]),
    "respond": lambda p: p["message"],
}


def execute(command: Command):
    if command.action not in ACTIONS:
        return f"Ação desconhecida: {command.action}"

    try:
        return ACTIONS[command.action](command.params)
    except Exception as e:
        return f"Erro ao executar {command.action}: {e}"
