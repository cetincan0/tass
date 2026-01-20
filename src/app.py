import json

from prompt_toolkit import prompt
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from src.constants import (
    SYSTEM_PROMPT,
    console,
)
from src.llm_client import LLMClient
from src.tools import (
    EDIT_FILE_TOOL,
    EXECUTE_TOOL,
    READ_FILE_TOOL,
    edit_file,
    execute,
    read_file,
)
from src.utils import (
    FileCompleter,
    create_key_bindings,
)


class TassApp:

    def __init__(self):
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.llm_client = LLMClient()
        self.key_bindings = create_key_bindings()
        self.file_completer = FileCompleter()
        self.TOOLS_MAP = {
            "execute": execute,
            "read_file": read_file,
            "edit_file": edit_file,
        }

    def check_llm_host(self):
        try:
            response = self.llm_client.get_models()
            console.print("Terminal Assistant [green](LLM connection ✓)[/green]")
            if response.status_code == 200:
                return
        except Exception:
            console.print("Terminal Assistant [red](LLM connection ✗)[/red]")

        console.print("\n[red]Could not connect to LLM[/red]")
        console.print(f"If your LLM isn't running on {self.llm_client.host}, you can set the [bold]TASS_HOST[/] environment variable to a different URL.")
        new_host = console.input(
            "Enter a different URL for this session (or press Enter to keep current): "
        ).strip()

        if new_host:
            self.llm_client.host = new_host

        try:
            response = self.llm_client.get_models()
            if response.status_code == 200:
                console.print(f"[green]Connection established to {self.llm_client.host}[/green]")
        except Exception:
            console.print(f"[red]Unable to verify new host {self.llm_client.host}. Continuing with it anyway.[/red]")

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
        response = self.llm_client.get_chat_completions(
            messages=[*self.messages, {"role": "user", "content": prompt}],
            tools=[
                EDIT_FILE_TOOL,
                EXECUTE_TOOL,
                READ_FILE_TOOL,
            ],  # For caching purposes
        )
        data = response.json()
        summary = data["choices"][0]["message"]["content"]
        self.messages = [self.messages[0], {"role": "assistant", "content": f"Summary of the conversation so far:\n{summary}"}]
        console.print("   [green]Summarization completed[/green]")

    def call_llm(self) -> bool:
        response = self.llm_client.get_chat_completions(
            messages=self.messages,
            tools=[
                EDIT_FILE_TOOL,
                EXECUTE_TOOL,
                READ_FILE_TOOL,
            ],
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
                if not any(delta.get(key) for key in ["content", "reasoning_content", "tool_calls"]):
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
                "content": content.strip(),
                "reasoning_content": reasoning_content.strip(),
                "tool_calls": list(tool_calls_map.values()) or [],
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
            self.messages.append({"role": "user", "content": f"Tool call failed: {e}"})
            console.print(f"   [red]Tool call failed: {str(e).strip()}[/red]")
            return self.call_llm()

    def run(self):
        try:
            self.check_llm_host()
        except KeyboardInterrupt:
            console.print("\nBye!")
            return

        while True:
            console.print()
            try:
                input_lines = []
                while True:
                    input_line = prompt(
                        "> ",
                        completer=self.file_completer,
                        complete_while_typing=True,
                        key_bindings=self.key_bindings,
                    )
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
                    console.print(f"Failed to call LLM: {e}")
                    break

                if finished:
                    self.summarize()
                    break
