import argparse

from rich.console import Console

from src.app import TassApp

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Terminal Assistant - Ask an LLM to run commands"
    )
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="YOLO mode: execute all commands and edit files without asking for confirmation",
    )
    parser.add_argument(
        "--resume",
        nargs="?",
        const=True,
        type=str,
        default=None,
        help="Resume the most recent conversation, or a specific one by ID",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Prompt to run (enclose in quotes; runs in single-shot mode and exits)",
    )
    args = parser.parse_args()

    app = TassApp(yolo_mode=args.yolo)

    conversation_id = None
    resume_picker = False
    if args.resume is not None and args.resume is not False:
        if args.resume is True:
            # --resume without an ID: show interactive picker
            resume_picker = True
        else:
            # --resume <id>
            conversation_id = args.resume

    if args.prompt:
        if conversation_id or resume_picker:
            console.print("[red]Cannot use --resume with a single-shot prompt.[/red]")
            return
        app.run(initial_input=args.prompt)
    else:
        app.run(conversation_id=conversation_id, resume_picker=resume_picker)
