from pathlib import Path

cwd_path = Path.cwd().resolve()

SYSTEM_PROMPT = f"""You are tass, or Terminal Assistant, a helpful AI that executes shell commands based on natural-language requests.

If the user's request involves making changes to the filesystem such as creating or deleting files or directories, you MUST first check whether the file or directory exists before proceeding.

If a user asks for an answer or explanation to something instead of requesting to run a command, answer briefly and concisely. Do not supply extra information, suggestions, tips, or anything of the sort.

Current working directory: {cwd_path}"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute",
            "description": "Executes a shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Full shell command to be executed.",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "A brief explanation of why you want to run this command. Keep it to a single sentence.",
                    },
                },
                "required": ["command", "explanation"],
                "$schema": "http://json-schema.org/draft-07/schema#",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edits (or creates) a file. Can make multiple edits in one call. Each edit replaces the contents between 'line_start' and 'line_end' inclusive with 'content'. If creating a file, only return a single edit where 'line_start' and 'line_end' are both 1 and 'content' is the entire contents of the file. You must use the read_file tool before editing a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path of the file",
                    },
                    "edits": {
                        "type": "array",
                        "description": "List of edits to apply. Each edit must contain 'line_start', 'line_end', and 'content'.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "line_start": {
                                    "type": "integer",
                                    "description": "The first line to remove (inclusive)",
                                },
                                "line_end": {
                                    "type": "integer",
                                    "description": "The last line to remove (inclusive)",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "The content to replace with. Must have the correct spacing and indentation for all lines.",
                                },
                            },
                            "required": ["line_start", "line_end", "content"],
                        },
                    },
                },
                "required": ["path", "edits"],
                "$schema": "http://json-schema.org/draft-07/schema#",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's contents (the first 1000 lines by default). When reading a file for the first time, do not change the defaults and always read the first 1000 lines unless you are absolutely certain of which lines need to be read. The output will be identical to calling `cat -n <path>` with preceding spaces, line number and a tab.",
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
    },
]

READ_ONLY_COMMANDS = [
    "ls",
    "cat",
    "less",
    "more",
    "echo",
    "head",
    "tail",
    "wc",
    "grep",
    "find",
    "ack",
    "which",
    "sed",
    "find",
    "test",
]
