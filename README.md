# tass

<p align="center">
  <img src="assets/tass.gif" alt="Demo" />
</p>

A terminal assistant that allows you to ask an LLM to run commands.

## Warning

This tool can run commands including ones that can modify, move, or delete files. Use at your own risk.

## Installation

### Using uv

```
uv tool install tass
```

### Using pip

```
pip install tass
```

You can run it with

```
tass
```

tass has only been tested with llama.cpp with LLMs such as gpt-oss-120b and MiniMax M2.1, but any LLM with tool calling capabilities should work.

By default, tass will try connecting to http://localhost:8080. To use another host, set the `TASS_HOST` environment variable. If your server requires an API key, you can set the `TASS_API_KEY` environment variable. At the moment there's no support for connecting tass to a non-local API, nor are there plans for it. I plan on keeping tass completely local. There's no telemetry, no logs, just a simple REPL loop.

Once it's running, you can ask questions or give commands like "Create an empty file called test.txt" and it will propose a command to run after user confirmation.

You can enter multiline input by ending lines with a backslash (\\). The continuation prompt will keep appearing until you enter a line without a trailing backslash.

## Upgrade

### Using uv

```
uv tool upgrade tass
```

### Using pip

```
pip install --upgrade tass
```
