import json
import os
import subprocess

import requests
from rich.console import Console
from rich.markdown import Markdown

from src.constants import (
    SYSTEM_PROMPT,
    TOOLS,
)
from src.third_party.apply_patch import apply_patch
from src.utils import (
    is_read_only_command,
)

console = Console()


class TassApp:

    def __init__(self):
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.host = os.environ.get("TASS_HOST", "http://localhost:8080")
        self.TOOLS_MAP = {
            "execute": self.execute,
            "apply_patch": self.apply_patch_tass,
            "read_file": self.read_file,
        }

    def _check_llm_host(self):
        test_url = f"{self.host}/v1/models"
        try:
            response = requests.get(test_url, timeout=2)
            console.print("Terminal Assistant [green](LLM connection ✓)[/green]")
            if response.status_code == 200:
                return
        except Exception:
            console.print("Terminal Assistant [red](LLM connection ✗)[/red]")

        console.print("\n[red]Could not connect to LLM[/red]")
        console.print(f"If your LLM isn't running on {self.host}, you can set the [bold]TASS_HOST[/] environment variable to a different URL.")
        new_host = console.input(
            "Enter a different URL for this session (or press Enter to keep current): "
        ).strip()

        if new_host:
            self.host = new_host

        try:
            response = requests.get(f"{self.host}/v1/models", timeout=2)
            if response.status_code == 200:
                console.print(f"[green]Connection established to {self.host}[/green]")
                return
        except Exception:
            console.print(f"[red]Unable to verify new host {self.host}. Continuing with it anyway.[/red]")

    def summarize(self):
        max_messages = 10
        if len(self.messages) <= max_messages:
            return

        prompt = (
            "The conversation is becoming long and might soon go beyond the "
            "context limit. Please provide a concise summary of the conversation, "
            "preserving all important details. Keep the summary short enough "
            "to fit within a few paragraphs at the most."
        )

        response = requests.post(
            f"{self.host}/v1/chat/completions",
            json={
                "messages": self.messages + [{"role": "user", "content": prompt}],
                "chat_template_kwargs": {"reasoning_effort": "medium"},
            },
        )
        data = response.json()
        summary = data["choices"][0]["message"]["content"]
        self.messages = [self.messages[0], {"role": "assistant", "content": f"Summary of the conversation so far:\n{summary}"}]

    def call_llm(self) -> str | None:
        response = requests.post(
            f"{self.host}/v1/chat/completions",
            json={
                "messages": self.messages,
                "tools": TOOLS,
                "chat_template_kwargs": {
                    "reasoning_effort": "medium",
                }
            },
        )

        data = response.json()
        message = data["choices"][0]["message"]
        if not message.get("tool_calls"):
            return message["content"]

        tool_name = message["tool_calls"][0]["function"]["name"]
        tool_args_str = message["tool_calls"][0]["function"]["arguments"]
        self.messages.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "id1",
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tool_args_str
                        }
                    }
                ]
            }
        )
        try:
            tool = self.TOOLS_MAP[tool_name]
            tool_args = json.loads(tool_args_str)
            result = tool(**tool_args)
            self.messages.append({"role": "tool", "content": result})
            return None
        except Exception as e:
            self.messages.append({"role": "user", "content": str(e)})
            return self.call_llm()

    def read_file(self, path: str, start: int = 1) -> str:
        console.print(f" └ Reading file [bold]{path}[/]...")

        lines = []
        with open(path) as f:
            line_num = 1
            for line in f:
                if line_num < start:
                    line_num += 1
                    continue

                lines.append(line)
                line_num += 1

                if len(lines) >= 1000:
                    lines.append("... (truncated)")
                    break

        console.print("   [green]Command succeeded[/green]")
        return "".join(lines)

    def apply_patch_tass(self, patch: str) -> str:
        console.print()
        console.print(Markdown(f"```diff\n{patch}\n```"))
        answer = console.input("\n[bold]Run?[/] ([bold]Y[/]/n): ").strip().lower()
        if answer not in ("yes", "y", ""):
            reason = console.input("Why not? (optional, press Enter to skip): ").strip()
            return f"User declined: {reason or 'no reason'}"

        console.print(" └ Running...")

        try:
            apply_patch(patch)
        except Exception as e:
            console.print("   [red]apply_patch failed[/red]")
            console.print(f"   [red]{str(e)}[/red]")
            return f"apply_patch failed: {str(e)}"

        console.print("   [green]Command succeeded[/green]")

        return "Command output (exit 0): apply_patch succeeded"

    def execute(self, command: str, explanation: str) -> str:
        command = command.strip()
        requires_confirmation = not is_read_only_command(command)
        if requires_confirmation:
            console.print()
            console.print(Markdown(f"```shell\n{command}\n```"))
            if explanation:
                console.print(f"Explanation: {explanation}")
            answer = console.input("\n[bold]Run?[/] ([bold]Y[/]/n): ").strip().lower()
            if answer not in ("yes", "y", ""):
                reason = console.input("Why not? (optional, press Enter to skip): ").strip()
                return f"User declined: {reason or 'no reason'}"

        if requires_confirmation:
            console.print(" └ Running...")
        else:
            console.print(f" └ Running [bold]{command}[/] (Explanation: {explanation})...")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
            )
        except Exception as e:
            console.print("   [red]subprocess.run failed[/red]")
            console.print(f"   [red]{str(e)}[/red]")
            return f"subprocess.run failed: {str(e)}"

        out = result.stdout.strip()
        err = result.stderr.strip()
        if result.returncode == 0:
            console.print("   [green]Command succeeded[/green]")
        else:
            console.print(f"   [red]Command failed[/red] (code {result.returncode})")
            console.print(f"   [red]{err}[/red]")

        if len(out) > 5000:
            out = f"{out[:5000]}... (Truncated)"

        if len(err) > 5000:
            err = f"{err[:5000]}... (Truncated)"

        return f"Command output (exit {result.returncode}):\n{out}\n{err}"

    def run(self):
        try:
            self._check_llm_host()
        except KeyboardInterrupt:
            console.print("\nBye!")
            return

        while True:
            try:
                user_input = console.input("\n> ").strip()
            except KeyboardInterrupt:
                console.print("\nBye!")
                break

            if not user_input:
                continue

            if user_input.lower().strip() == "exit":
                console.print("\nBye!")
                break

            self.messages.append({"role": "user", "content": user_input})

            while True:
                try:
                    llm_resp = self.call_llm()
                except Exception as e:
                    console.print(f"Failed to call LLM: {str(e)}")
                    break

                if llm_resp is not None:
                    console.print("")
                    console.print(Markdown(llm_resp))
                    self.messages.append({"role": "assistant", "content": llm_resp})
                    self.summarize()
                    break
