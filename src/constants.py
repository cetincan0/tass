import os
import platform
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()
CWD_PATH = Path.cwd().resolve()


def get_shell_info() -> str:
    shell_path = os.environ.get('SHELL', '')
    shell_name = shell_path.split('/')[-1] if shell_path else 'unknown'
    return shell_name


def get_git_info() -> str:
    try:
        git_info = []

        subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True, check=True, cwd=CWD_PATH)
        result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, cwd=CWD_PATH)
        branch = result.stdout.strip()
        if branch:
            git_info.append(f"Branch: {branch}")

        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, cwd=CWD_PATH)
        has_changes = bool(result.stdout.strip())
        git_info.append(f"Uncommitted changes: {'Yes' if has_changes else 'No'}")

        return '\n'.join(git_info)
    except Exception:
        return "Not a git repository"


def get_directory_listing() -> str:
    try:
        entries = []
        iterdir = CWD_PATH.iterdir()
        for count, entry in enumerate(sorted(iterdir)):
            if count >= 100:
                entries.append(f"... and {len(list(iterdir)) - 100} more items")
                break
            if entry.is_dir():
                entries.append(f"{entry.name}/")
            else:
                entries.append(entry.name)
        return '\n'.join(entries) if entries else "Empty directory"
    except PermissionError:
        return "Permission denied"


SYSTEM_PROMPT = f"""You are tass, or Terminal Assistant, a helpful AI that executes shell commands based on natural-language requests.

If the user's request involves making changes to the filesystem such as creating or deleting files or directories, you MUST first check whether the file or directory exists before proceeding.

If a user asks for an answer or explanation to something instead of requesting to run a command, answer briefly and concisely. Do not supply extra information, suggestions, tips, or anything of the sort.

This app has a feature where the user can refer to files or directories by typing @ which will open an file autocomplete dropdown. When this feature is used, the @ will remain in the filename. When working with said file, ignore the preceding @.

Current working directory: {CWD_PATH}

# Directory Context
OS: {platform.system()}
Shell: {get_shell_info()}

# Git Info
{get_git_info()}

# Directory Listing
{get_directory_listing()}
"""
