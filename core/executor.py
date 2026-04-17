from core.command_schema import Command
from core.normalizer import normalize_action
from tools.browser_tools import (
    browser_close_tab,
    browser_back,
    browser_click_center,
    browser_forward,
    browser_find,
    browser_new_tab,
    browser_next_tab,
    browser_open_first_result,
    browser_open_focused_item,
    browser_prev_tab,
    browser_refresh,
    browser_search,
    browser_search_music,
    browser_search_site,
    browser_scroll_bottom,
    browser_scroll_down,
    browser_scroll_top,
    browser_scroll_up,
    browser_zoom_in,
    browser_zoom_out,
    browser_zoom_reset,
    spotify_diagnostic,
)
from tools.bluetooth_tools import (
    bluetooth_off,
    bluetooth_on,
    bluetooth_settings,
    bluetooth_status,
)
from tools.media_tools import (
    media_next,
    media_next_target,
    media_pause_target,
    media_play_target,
    media_play_pause,
    media_play_pause_target,
    media_previous,
    media_previous_target,
    volume_down,
    volume_mute,
    volume_up,
)
from tools.smart_open_tools import (
    forget_smart_memory,
    list_smart_memory,
    close_smart_target,
    open_smart_target,
    open_smart_target_as_kind,
    remember_target_kind,
)
from tools.system_tools import (
    close_app,
    focus_app,
    maximize_app,
    minimize_app,
    open_app,
    open_url,
    restore_app,
    run_script,
)
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
    "smart_open": lambda p: open_smart_target(p["target"]),
    "smart_open_choice": lambda p: open_smart_target_as_kind(p["target"], p["kind"]),
    "remember_target_kind": lambda p: remember_target_kind(p["target"], p["kind"]),
    "forget_smart_memory": lambda p: forget_smart_memory(p["target"]),
    "list_smart_memory": lambda p: list_smart_memory(),
    "close_app": lambda p: close_app(p["target"]),
    "smart_close_app": lambda p: close_smart_target(p["target"]),
    "focus_app": lambda p: focus_app(p["target"]),
    "minimize_app": lambda p: minimize_app(p["target"]),
    "maximize_app": lambda p: maximize_app(p["target"]),
    "restore_app": lambda p: restore_app(p["target"]),
    "run_script": lambda p: run_script(p["target"]),
    "open_url": lambda p: open_url(p["target"]),
    "browser_new_tab": lambda p: browser_new_tab(),
    "browser_close_tab": lambda p: browser_close_tab(),
    "browser_next_tab": lambda p: browser_next_tab(),
    "browser_prev_tab": lambda p: browser_prev_tab(),
    "browser_back": lambda p: browser_back(),
    "browser_forward": lambda p: browser_forward(),
    "browser_refresh": lambda p: browser_refresh(),
    "browser_open_first_result": lambda p: browser_open_first_result(),
    "browser_open_focused_item": lambda p: browser_open_focused_item(),
    "browser_click_center": lambda p: browser_click_center(),
    "browser_search": lambda p: browser_search(p["query"]),
    "browser_find": lambda p: browser_find(p["query"]),
    "browser_scroll_down": lambda p: browser_scroll_down(),
    "browser_scroll_up": lambda p: browser_scroll_up(),
    "browser_scroll_top": lambda p: browser_scroll_top(),
    "browser_scroll_bottom": lambda p: browser_scroll_bottom(),
    "browser_zoom_in": lambda p: browser_zoom_in(),
    "browser_zoom_out": lambda p: browser_zoom_out(),
    "browser_zoom_reset": lambda p: browser_zoom_reset(),
    "browser_search_site": lambda p: browser_search_site(p["site"], p["query"]),
    "browser_search_music": lambda p: browser_search_music(p["service"], p["query"]),
    "spotify_diagnostic": lambda p: spotify_diagnostic(),
    "media_play_pause": lambda p: media_play_pause(),
    "media_next": lambda p: media_next(),
    "media_previous": lambda p: media_previous(),
    "media_play_pause_target": lambda p: media_play_pause_target(p["target"]),
    "media_play_target": lambda p: media_play_target(p["target"]),
    "media_pause_target": lambda p: media_pause_target(p["target"]),
    "media_next_target": lambda p: media_next_target(p["target"]),
    "media_previous_target": lambda p: media_previous_target(p["target"]),
    "volume_up": lambda p: volume_up(),
    "volume_down": lambda p: volume_down(),
    "volume_mute": lambda p: volume_mute(),
    "bluetooth_on": lambda p: bluetooth_on(),
    "bluetooth_off": lambda p: bluetooth_off(),
    "bluetooth_settings": lambda p: bluetooth_settings(),
    "bluetooth_status": lambda p: bluetooth_status(),
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
