import json
import os
import subprocess
from pathlib import Path

import requests

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from src.constants import (
    SYSTEM_PROMPT,
    TOOLS,
)
from src.utils import is_read_only_command

console = Console()


class TassApp:

    def __init__(self):
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.host = os.environ.get("TASS_HOST", "http://localhost:8080")
        self.TOOLS_MAP = {
            "execute": self.execute,
            "read_file": self.read_file,
            "edit_file": self.edit_file,
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
        except Exception:
            console.print(f"[red]Unable to verify new host {self.host}. Continuing with it anyway.[/red]")

    def summarize(self):
        max_messages = 20
        if len(self.messages) <= max_messages:
            return

        prompt = (
            "The conversation is becoming long and might soon go beyond the "
            "context limit. Please provide a detailed summary of the conversation, "
            "preserving all important details. Make sure context is not lost so that "
            "the conversation can continue without needing to reclarify anything. "
            "You don't have to preserve entire contents of files that have been read "
            " or edited, they can be read again if necessary."
        )

        console.print("\n - Summarizing conversation...")
        response = requests.post(
            f"{self.host}/v1/chat/completions",
            json={
                "messages": self.messages + [{"role": "user", "content": prompt}],
                "tools": TOOLS,  # For caching purposes
                "chat_template_kwargs": {
                    "reasoning_effort": "medium",
                },
            },
        )
        data = response.json()
        summary = data["choices"][0]["message"]["content"]
        self.messages = [self.messages[0], {"role": "assistant", "content": f"Summary of the conversation so far:\n{summary}"}]
        console.print("   [green]Summarization completed[/green]")

    def call_llm(self) -> bool:
        response = requests.post(
            f"{self.host}/v1/chat/completions",
            json={
                "messages": self.messages,
                "tools": TOOLS,
                "chat_template_kwargs": {
                    "reasoning_effort": "medium",
                },
                "stream": True,
            },
            stream=True,
        )

        content = ""
        reasoning_content = ""
        tool_calls_map = {}
        timings_str = ""

        def generate_layout():
            groups = []

            if reasoning_content:
                last_three_lines = "\n".join(reasoning_content.rstrip().split("\n")[-3:])
                groups.append(Text(""))
                groups.append(
                    Panel(
                        Text(
                            last_three_lines,
                            style="grey50",
                        ),
                        title="Thought process",
                        title_align="left",
                        subtitle=timings_str,
                        style="grey50",
                    )
                )

            if content:
                groups.append(Text(""))
                groups.append(Markdown(content.rstrip()))

            return Group(*groups)

        with Live(generate_layout(), refresh_per_second=10) as live:
            for line in response.iter_lines():
                line = line.decode("utf-8")
                if not line.strip():
                    continue

                if line == "data: [DONE]":
                    continue

                chunk = json.loads(line.removeprefix("data:"))
                if all(k in chunk.get("timings", {}) for k in ["prompt_n", "prompt_per_second", "predicted_n", "predicted_per_second"]):
                    timings = chunk["timings"]
                    timings_str = (
                        f"Input: {timings['prompt_n']:,} tokens, {timings['prompt_per_second']:,.2f} tok/s | "
                        f"Output: {timings['predicted_n']:,} tokens, {timings['predicted_per_second']:,.2f} tok/s"
                    )

                if chunk["choices"][0]["finish_reason"]:
                    live.update(generate_layout())

                delta = chunk["choices"][0]["delta"]
                if not any([delta.get(key) for key in ["content", "reasoning_content", "tool_calls"]]):
                    continue

                if delta.get("reasoning_content"):
                    reasoning_content += delta["reasoning_content"]
                    live.update(generate_layout())

                if delta.get("content"):
                    content += delta["content"]
                    live.update(generate_layout())

                for tool_call_delta in delta.get("tool_calls") or []:
                    index = tool_call_delta["index"]
                    if index not in tool_calls_map:
                        tool_calls_map[index] = (
                            {
                                "index": index,
                                "id": "",
                                "type": "",
                                "function": {
                                    "name": "",
                                    "arguments": "",
                                },
                            }
                        )

                    tool_call = tool_calls_map[index]
                    if tool_call_delta.get("id"):
                        tool_call["id"] += tool_call_delta["id"]
                    if tool_call_delta.get("type"):
                        tool_call["type"] += tool_call_delta["type"]
                    if tool_call_delta.get("function"):
                        function = tool_call_delta["function"]
                        if function.get("name"):
                            tool_call["function"]["name"] += function["name"]
                        if function.get("arguments"):
                            tool_call["function"]["arguments"] += function["arguments"]

        self.messages.append(
            {
                "role": "assistant",
                "content": content.strip() or None,
                "reasoning_content": reasoning_content.strip() or None,
                "tool_calls": list(tool_calls_map.values()) or None,
            }
        )

        if not tool_calls_map:
            return True

        try:
            for tool_call in tool_calls_map.values():
                tool = self.TOOLS_MAP[tool_call["function"]["name"]]
                tool_args = json.loads(tool_call["function"]["arguments"])
                result = tool(**tool_args)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "content": result,
                    }
                )
            return False
        except Exception as e:
            self.messages.append({"role": "user", "content": str(e)})
            return self.call_llm()

    def read_file(self, path: str, start: int = 1) -> str:
        if start == 1:
            console.print(f" └ Reading file [bold]{path}[/]...")
        else:
            console.print(f" └ Reading file [bold]{path}[/] (from line {start})...")

        try:
            result = subprocess.run(
                f"cat -n {path}",
                shell=True,
                capture_output=True,
                text=True,
            )
        except Exception as e:
            console.print("   [red]read_file failed[/red]")
            console.print(f"   [red]{str(e).strip()}[/red]")
            return f"read_file failed: {str(e)}"

        out = result.stdout
        err = result.stderr.strip()
        if result.returncode != 0:
            console.print("   [red]read_file failed[/red]")
            if err:
                console.print(f"   [red]{err}[/red]")
            return f"read_file failed: {err}"

        lines = []
        line_num = 1
        for line in out.split("\n"):
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

    def edit_file(self, path: str, edits: list[dict]) -> str:
        for edit in edits:
            edit["applied"] = False

        def find_edit(n: int) -> dict | None:
            for edit in edits:
                if edit["line_start"] <= n <= edit["line_end"]:
                    return edit

            return None

        file_exists = Path(path).exists()
        if file_exists:
            with open(path, "r") as f:
                original_content = f.read()
        else:
            original_content = ""

        final_lines = []
        original_lines = original_content.split("\n")
        diff_text = f"{'Editing' if file_exists else 'Creating'} {path}"
        for i, line in enumerate(original_lines):
            line_num = i + 1
            edit = find_edit(line_num)
            if not edit:
                final_lines.append(line)
                continue

            if edit["applied"]:
                continue

            replace_lines = edit["replace"].split("\n")
            final_lines.extend(replace_lines)
            original_lines = original_content.split("\n")
            replaced_lines = original_lines[edit["line_start"] - 1:edit["line_end"]]

            prev_line_num = line_num if line_num == 1 else line_num - 1
            line_before = "" if i == 0 else f" {original_lines[i - 1]}\n"
            line_after = "" if edit["line_end"] == len(original_lines) else f"\n {original_lines[edit['line_end']]}"
            replaced_with_minuses = "\n".join([f"-{line}" for line in replaced_lines]) if file_exists else ""
            replace_with_pluses = "\n".join([f"+{line}" for line in edit["replace"].split("\n")])
            diff_text = f"{diff_text}\n\n@@ -{prev_line_num},{len(replaced_lines)} +{prev_line_num},{len(replace_lines)} @@\n{line_before}{replaced_with_minuses}\n{replace_with_pluses}{line_after}"
            edit["applied"] = True

        console.print()
        console.print(Markdown(f"```diff\n{diff_text}\n```"))
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
            console.print(f"   [red]{str(e).strip()}[/red]")
            return f"subprocess.run failed: {str(e).strip()}"

        out = result.stdout
        err = result.stderr.strip()
        if result.returncode == 0:
            console.print("   [green]Command succeeded[/green]")
        else:
            console.print(f"   [red]Command failed[/red] (code {result.returncode})")
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

        return f"Command output (exit {result.returncode}):\n{out}\n{err}"

    def run(self):
        try:
            self._check_llm_host()
        except KeyboardInterrupt:
            console.print("\nBye!")
            return

        while True:
            console.print()
            try:
                input_lines = []
                while True:
                    input_line = console.input("> ")
                    if not input_line or input_line[-1] != "\\":
                        input_lines.append(input_line)
                        break
                    input_lines.append(input_line[:-1])

                user_input = "\n".join(input_lines)
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
                    finished = self.call_llm()
                except Exception as e:
                    console.print(f"Failed to call LLM: {str(e)}")
                    break

                if finished:
                    self.summarize()
                    break
