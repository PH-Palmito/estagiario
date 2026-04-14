from memory.aliases import resolve_alias
from tools.clipboard_tools import get_clipboard


def _is_ref(value):
    if value is None:
        return True

    if not isinstance(value, str):
        return False

    v = value.lower().strip()

    return v in {
        "",
        "ele",
        "isso",
        "isto",
        "último",
        "ultimo",
        "arquivo",
        "arquivo atual",
    }


def _is_app_ref(value):
    if value is None:
        return True

    if not isinstance(value, str):
        return False

    return value.lower().strip() in {"", "ele", "isso", "isto", "app", "janela", "ela", "ultimo", "atual"}


def _is_clip_ref(value):
    if not isinstance(value, str):
        return False

    v = value.lower().strip()
    return v in {"isso", "isto", "esse texto", "conteúdo", "conteudo"}


def _resolve_alias_if_needed(value):
    if not value or not isinstance(value, str):
        return value

    alias = resolve_alias(value.strip())
    return alias if alias else value


def resolve_params(command, state):
    p = command.params
    action = command.action

    # -------------------------
    # APPLY ALIAS FIRST
    # -------------------------
    if "path" in p:
        p["path"] = _resolve_alias_if_needed(p.get("path"))

    if "src" in p:
        p["src"] = _resolve_alias_if_needed(p.get("src"))

    if "dst" in p:
        p["dst"] = _resolve_alias_if_needed(p.get("dst"))

    # -------------------------
    # CLIPBOARD -> CONTENT
    # -------------------------
    if action in {"file_write", "file_append"}:
        if _is_clip_ref(p.get("content")):
            clip = get_clipboard()
            if clip:
                p["content"] = clip
                state.last_clipboard = clip

    # -------------------------
    # CLIPBOARD -> GOOGLE QUERY
    # -------------------------
    if action == "web_google_search":
        if _is_clip_ref(p.get("query")):
            clip = get_clipboard()
            if clip:
                p["query"] = clip
                state.last_clipboard = clip

    # -------------------------
    # CONTEXTUAL APP / WINDOW ACTIONS
    # -------------------------
    if action in {"focus_app", "minimize_app", "maximize_app", "restore_app", "close_app"}:
        if _is_app_ref(p.get("target")):
            if state.last_app:
                p["target"] = state.last_app
            else:
                command.action = "respond"
                command.params = {"message": "Qual app?"}
                return command

    if action == "context_close":
        if state.last_surface == "browser":
            command.action = "browser_close_tab"
            command.params = {}
            return command

        if state.last_app:
            command.action = "close_app"
            command.params = {"target": state.last_app}
            return command

        command.action = "respond"
        command.params = {"message": "Nao sei o que fechar."}
        return command

    # -------------------------
    # FILE ACTIONS
    # -------------------------
    if action in {
        "file_write",
        "file_append",
        "file_read",
        "file_delete",
        "file_replace",
    }:
        if _is_ref(p.get("path")):
            if state.last_file:
                p["path"] = state.last_file

    # -------------------------
    # COPY / MOVE
    # -------------------------
    if action in {"file_copy", "file_move"}:
        if _is_ref(p.get("src")):
            if state.last_file:
                p["src"] = state.last_file

    # -------------------------
    # RENAME
    # -------------------------
    if action == "file_rename":
        if _is_ref(p.get("src")):
            if state.last_file:
                p["src"] = state.last_file

    # -------------------------
    # FOLDER
    # -------------------------
    if action == "folder_create":
        if _is_ref(p.get("path")):
            if state.last_folder:
                p["path"] = state.last_folder

    # -------------------------
    # SAFETY FALLBACKS
    # -------------------------
    if action.startswith("file_") and "path" in p and p.get("path") in ("", None):
        p["path"] = None

    return command
