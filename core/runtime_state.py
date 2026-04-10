class RuntimeState:
    def __init__(self):
        self.last_file = None
        self.last_folder = None
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

        self.last_action = a
        self.last_result = result

        if a != "respond":
            self.last_command = command
