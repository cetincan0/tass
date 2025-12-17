# tass

A terminal assistant that allows you to ask an LLM to run commands.

## Warning

This tool can run commands including ones that can modify, move, or delete files. Use at your own risk.

## Installation

```
uv tools install tass
```

You can run it with

```
tass
```

tass has only been tested with gpt-oss-120b using llama.cpp so far, but in theory any LLM with tool calling capabilities should work. By default, it will try connecting to http://localhost:8080. If you want to use another host, set the `TASS_HOST` environment variable.

Once it's running, you can ask questions like "Can you create an empty file called test.txt?" and it will propose a command to run after user confirmation.
