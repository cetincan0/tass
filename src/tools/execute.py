import subprocess
from time import time

from rich.markdown import Markdown

from src.constants import (
    CWD_PATH,
    console,
)

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

EXECUTE_TOOL = {
    "type": "function",
    "function": {
        "name": "execute",
        "description": f"Executes a shell command. The current working directory for all commands will be {CWD_PATH}",
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
}


def is_read_only_command(command: str) -> bool:
    """A simple check to see if the command is only for reading files.

    Not a comprehensive or foolproof check by any means, and will
    return false negatives to be safe.
    """
    if ">" in command:
        return False

    # Replace everything that potentially runs another command with a pipe
    command = command.replace("&&", "|")
    command = command.replace("||", "|")
    command = command.replace(";", "|")

    pipes = command.split("|")
    return all(pipe.strip().split()[0] in READ_ONLY_COMMANDS for pipe in pipes)


def execute(command: str, explanation: str, yolo_mode: bool = False) -> str:
    command = command.strip()
    requires_confirmation = not yolo_mode and not is_read_only_command(command)
    if requires_confirmation:
        console.print(Markdown(f"```shell\n{command}\n```"))
        if explanation:
            console.print(f"Explanation: {explanation}")
        answer = console.input("\n[bold]Run?[/] ([bold]Y[/]/n): ").strip().lower()
        if answer not in ("yes", "y", ""):
            reason = console.input("Why not? (optional, press Enter to skip): ").strip()
            return f"User declined: {reason or 'no reason'}"
        console.print(" └ Running...")
    else:
        console.print(f" └ Running [bold]{command}[/] (Explanation: {explanation})")

    try:
        start = time()
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
        took = time() - start
    except Exception as e:
        console.print("   [red]subprocess.run failed[/red]")
        console.print(f"   [red]{str(e).strip()}[/red]")
        return f"subprocess.run failed: {str(e).strip()}"

    out = result.stdout
    err = result.stderr.strip()
    if result.returncode == 0:
        console.print(f"   [green]Command succeeded[/green] [grey50]({took:,.2f}s)[/grey50]", highlight=False)
    else:
        console.print(f"   [red]Command failed[/red] (code {result.returncode}) [grey50]({took:,.2f}s)[/grey50]", highlight=False)
        if err:
            console.print(f"   [red]{err}[/red]")

    if len(out.split("\n")) > 1000:
        out_first_1000 = "\n".join(out.split("\n")[:1000])
        out = f"{out_first_1000}... (Truncated)"

    if len(err.split("\n")) > 1000:
        err_first_1000 = "\n".join(err.split("\n")[:1000])
        err = f"{err_first_1000}... (Truncated)"

    if len(out) > 20000:
        out = f"{out[:20000]}... (Truncated)"

    if len(err) > 20000:
        err = f"{err[:20000]}... (Truncated)"

    return f"Command output (exit {result.returncode}):\n{out}\n{err}\nTook {took:,.2f}s"
