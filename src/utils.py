from prompt_toolkit.completion import (
    Completer,
    Completion,
    CompleteEvent,
)
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from src.constants import CWD_PATH


class FileCompleter(Completer):

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> list[Completion]:
        """Return file completions for text after @ anywhere in input."""
        text = document.text
        cursor_pos = document.cursor_position
        text_before_cursor = document.text_before_cursor
        last_at_pos = text_before_cursor.rfind("@")
        if last_at_pos == -1:
            return []

        text_after_at = text[last_at_pos + 1 : cursor_pos]

        base_dir = CWD_PATH
        search_pattern = text_after_at
        prefix = ""

        if "/" in text_after_at:
            dir_part, file_part = text_after_at.rsplit("/", 1)
            base_dir = CWD_PATH / dir_part
            search_pattern = file_part
            prefix = dir_part + "/"

        if not base_dir.is_dir():
            return []

        try:
            dirs = []
            files = []
            for entry in sorted(base_dir.iterdir()):
                name = entry.name
                if search_pattern in name:
                    full_path = prefix + name
                    if entry.is_dir():
                        dirs.append(Completion(full_path, display=name, start_position=-len(text_after_at), style="Blue"))
                    else:
                        files.append(Completion(full_path, display=name, start_position=-len(text_after_at)))

            return dirs + files
        except (PermissionError, OSError):
            return []


def create_key_bindings() -> KeyBindings:
    bindings = KeyBindings()

    @bindings.add(Keys.Backspace)
    def backspace_with_completion(event):
        """Also trigger completion on backspace."""
        buffer = event.current_buffer
        buffer.delete_before_cursor(count=1)
        text_before_cursor = buffer.document.text_before_cursor
        last_at_pos = text_before_cursor.rfind("@")
        if last_at_pos != -1:
            buffer.start_completion()

    @bindings.add(Keys.ControlC)
    def ctrl_c_handler(event):
        """Ctrl+C should raise KeyboardInterrupt."""
        raise KeyboardInterrupt()

    return bindings
