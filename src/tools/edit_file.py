from dataclasses import dataclass
from difflib import SequenceMatcher, unified_diff
from pathlib import Path

from rich.markdown import Markdown

from src.constants import console

EDIT_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Edits (or creates) a file. Can make multiple edits in one call. Each edit finds the instance of 'find' and replaces it with 'replace'. When creating a file, only return a single edit where 'find' is empty and 'replace' is the entire contents of the file. Both 'find' and 'replace' must always be entire lines and never parts of a line, and they must always have correct dnd complete indentation. You must use the read_file tool before editing a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the file",
                },
                "edits": {
                    "type": "array",
                    "description": "List of edits to apply.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "find": {
                                "type": "string",
                                "description": "Content to find. Include additional previous/following lines if necessary to uniquely identify the section.",
                            },
                            "replace": {
                                "type": "string",
                                "description": "The content to replace with. Must have the correct spacing and indentation for all lines.",
                            },
                        },
                        "required": ["find", "replace"],
                    },
                },
            },
            "required": ["path", "edits"],
            "$schema": "http://json-schema.org/draft-07/schema#",
        },
    },
}


@dataclass
class LineEdit:

    line_start: int
    line_end: int
    replace: str
    applied: bool = False


def remove_empty_lines(s: str) -> str:
    while "\n\n" in s:
        s = s.replace("\n\n", "\n")
    return s


def fuzzy_match(edit_find: str, lines: list[str]) -> tuple[int, int] | None:
    if not lines:
        return None

    num_edit_find_lines = len(edit_find.split("\n"))
    edit_find_trimmed = remove_empty_lines(edit_find)
    best_ratio = 0.0
    best_start = -1
    best_window_len = 1
    for i in range(len(lines)):
        for j in range(1, min(num_edit_find_lines * 2, len(lines) - i)):
            window_text = remove_empty_lines("\n".join(lines[i : i + j]))
            ratio = SequenceMatcher(None, edit_find_trimmed, window_text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i
                best_window_len = j
                if best_ratio == 1.0:
                    return best_start + 1, best_start + best_window_len

    if best_ratio >= 0.9:
        return best_start + 1, best_start + best_window_len

    return None


def convert_edit_to_line_edit(edit: dict, original_content: str) -> LineEdit:
    if not original_content and not edit["find"]:
        return LineEdit(1, 1, edit["replace"], False)

    lines = original_content.split("\n")
    edit_lines = edit["find"].split("\n")

    # First try exact matches
    for i in range(len(lines)):
        if lines[i : i + len(edit_lines)] == edit_lines:
            return LineEdit(i + 1, i + len(edit_lines), edit["replace"], False)

    # Then try matching without spacing
    for i in range(len(lines)):
        stripped_lines = [line.strip() for line in lines[i : i + len(edit_lines)]]
        stripped_edit_lines = [line.strip() for line in edit_lines]
        if stripped_lines == stripped_edit_lines:
            return LineEdit(i + 1, i + len(edit_lines), edit["replace"], False)

    # Finally try sequence matching while ignoring whitespace
    fuzzy_edit = fuzzy_match(edit["find"], lines)
    if fuzzy_edit:
        return LineEdit(*fuzzy_edit, edit["replace"], False)

    raise Exception("Edit not found in file")


def edit_file(path: str, edits: list[dict], yolo_mode: bool = False) -> str:
    def find_line_edit(n: int) -> LineEdit | None:
        for line_edit in line_edits:
            if line_edit.line_start <= n <= line_edit.line_end:
                return line_edit

        return None

    file_exists = Path(path).exists()
    if file_exists:
        with open(path) as f:
            original_content = f.read()
    else:
        original_content = ""

    line_edits: list[LineEdit] = [
        convert_edit_to_line_edit(edit, original_content)
        for edit in edits
    ]

    final_lines = []
    original_lines = original_content.split("\n")
    for i, line in enumerate(original_lines):
        line_num = i + 1
        line_edit = find_line_edit(line_num)
        if not line_edit:
            final_lines.append(line)
            continue

        if line_edit.applied:
            continue

        replace_lines = line_edit.replace.split("\n")
        if line_edit.replace:
            final_lines.extend(replace_lines)
        original_lines = original_content.split("\n")
        line_edit.applied = True

    unified_diff_md = ""
    for line in unified_diff(
        [f"{line}\n" for line in original_lines],
        [f"{line}\n" for line in final_lines],
        fromfile=path,
        tofile=path,
    ):
        unified_diff_md += line

    console.print()
    console.print(Markdown(f"```diff\n{unified_diff_md}\n```"))

    if not yolo_mode:
        answer = console.input("\n[bold]Run?[/] ([bold]Y[/]/n): ").strip().lower()
        if answer not in ("yes", "y", ""):
            reason = console.input("Why not? (optional, press Enter to skip): ").strip()
            return f"User declined: {reason or 'no reason'}"
    console.print(" └ Running...")
    try:
        with open(path, "w") as f:
            f.write("\n".join(final_lines))
    except Exception as e:
        console.print("   [red]edit_file failed[/red]")
        console.print(f"   [red]{str(e).strip()}[/red]")
        return f"edit_file failed: {str(e).strip()}"

    console.print("   [green]Command succeeded[/green]")
    return f"Successfully edited {path}"
