class RuntimeState:
    def __init__(self):
        self.last_file = None
        self.last_folder = None
        self.last_app = None
        self.last_surface = None
        self.last_action = None
        self.last_result = None
        self.last_clipboard = None
        self.last_command = None

    def update(self, command, result):
        a = command.action
        p = command.params

        if a in {"file_create", "file_write", "file_append", "file_read"}:
            self.last_file = p.get("path")

        elif a in {"file_copy", "file_move"}:
            self.last_file = p.get("dst")

        elif a == "file_rename":
            self.last_file = p.get("new_name")

        elif a == "folder_create":
            self.last_folder = p.get("path")

        elif a in {"open_app", "close_app", "smart_close_app", "focus_app", "minimize_app", "maximize_app", "restore_app"}:
            self.last_app = p.get("target")
            self.last_surface = "app"

        elif a == "smart_open_choice":
            self.last_app = p.get("target")
            self.last_surface = "app" if p.get("kind") == "app" else "browser"

        elif a == "smart_open":
            result_text = str(result or "").lower()
            self.last_app = p.get("target")
            self.last_surface = "browser" if "site" in result_text else "app"

        elif a in {
            "open_url",
            "browser_new_tab",
            "browser_close_tab",
            "browser_next_tab",
            "browser_prev_tab",
            "browser_back",
            "browser_forward",
            "browser_refresh",
            "browser_open_first_result",
            "browser_open_focused_item",
            "browser_click_center",
            "browser_search",
            "browser_find",
            "browser_scroll_down",
            "browser_scroll_up",
            "browser_scroll_top",
            "browser_scroll_bottom",
            "browser_search_site",
            "browser_zoom_in",
            "browser_zoom_out",
            "browser_zoom_reset",
            "web_google_search",
            "web_open_chatgpt",
        }:
            self.last_app = "chrome"
            self.last_surface = "browser"

        self.last_action = a
        self.last_result = result

        if a != "respond":
            self.last_command = command
