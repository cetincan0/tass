import argparse

from src.app import TassApp


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
        "prompt",
        nargs="?",
        help="Prompt to run (enclose in quotes; runs in single-shot mode and exits)",
    )
    args = parser.parse_args()

    app = TassApp(yolo_mode=args.yolo)

    if args.prompt:
        app.run(initial_input=args.prompt)
    else:
        app.run()
