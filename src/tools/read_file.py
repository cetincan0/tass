from src.constants import console

READ_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file's contents (the first 1000 lines by default). When reading a file for the first time, do not change the defaults and always read the first 1000 lines unless you are absolutely certain of which lines need to be read.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the file",
                },
                "start": {
                    "type": "integer",
                    "description": "Which line to start reading from",
                    "default": 1,
                },
                "num_lines": {
                    "type": "integer",
                    "description": "Number of lines to read, defaults to 1000",
                    "default": 1000,
                },
            },
            "required": ["path"],
            "$schema": "http://json-schema.org/draft-07/schema#",
        },
    },
}


def read_file(path: str, start: int = 1, num_lines: int = 1000) -> str:
    if start == 1 and num_lines == 1000:
        console.print(f" └ Reading file [bold]{path}[/]...")
    else:
        last_line = start + num_lines - 1
        console.print(f" └ Reading file [bold]{path}[/] (lines {start}-{last_line})...")

    try:
        with open(path) as f:
            lines = []
            line_num = 1
            for line in f:
                if line_num < start:
                    line_num += 1
                    continue

                lines.append(line)
                line_num += 1

                if len(lines) >= num_lines:
                    lines.append("... (truncated)")
                    break

            console.print("   [green]Command succeeded[/green]")
            return "\n".join(lines)
    except Exception as e:
        console.print("   [red]read_file failed[/red]")
        console.print(f"   [red]{str(e).strip()}[/red]")
        return f"read_file failed: {e}"
