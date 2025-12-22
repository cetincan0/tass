from pathlib import Path

_apply_patch_path = Path(__file__).resolve().parent / "third_party" / "apply_patch.md"
APPLY_PATCH_PROMPT = _apply_patch_path.read_text().strip()

_cwd_path = Path.cwd().resolve()

SYSTEM_PROMPT = f"""You are Terminal-Assistant, a helpful AI that executes shell commands based on natural-language requests.

If the user's request involves making changes to the filesystem such as creating or deleting files or directories, you MUST first check whether the file or directory exists before proceeding.

If a user asks for an answer or explanation to something instead of requesting to run a command, answer briefly and concisely. Do not supply extra information, suggestions, tips, or anything of the sort.

Current working directory: {_cwd_path}

{APPLY_PATCH_PROMPT}"""

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
            "name": "apply_patch",
            "description": "Patch a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {
                        "type": "string",
                        "description": "Formatted patch code",
                        "default": "*** Begin Patch\n*** End Patch\n",
                    },
                },
                "required": ["patch"],
                "$schema": "http://json-schema.org/draft-07/schema#",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's contents (up to 1000 lines)",
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
]
