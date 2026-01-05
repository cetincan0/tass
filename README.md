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

tass has only been tested with gpt-oss-120b using llama.cpp so far, but in theory any LLM with tool calling capabilities should work. By default, it will try connecting to http://localhost:8080. If you want to use another host, set the `TASS_HOST` environment variable. At the moment there's no support for connecting tass to a non-local API, nor are there plans for it. For the time being, I plan on keeping tass completely local. There's no telemetry, no logs, just a simple REPL loop.

Once it's running, you can ask questions or give commands like "Create an empty file called test.txt" and it will propose a command to run after user confirmation.

You can enter multiline input by ending lines with a backslash (\\). The continuation prompt will appear until you enter a line without a trailing backslash.

## Upgrade

### Using uv

```
uv tool upgrade tass
```

### Using pip

```
pip install --upgrade tass
```
