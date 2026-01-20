import os
from typing import Literal

import requests


class LLMClient:

    def __init__(self):
        self.host = os.environ.get("TASS_HOST", "http://localhost:8080")
        self.api_key = os.environ.get("TASS_API_KEY", "")

    def request(
        self,
        method: Literal["get", "post"],
        url: str,
        **kwargs,
    ):
        return requests.request(
            method,
            f"{self.host}{url}",
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            **kwargs,
        )

    def get(self, url: str, **kwargs):
        return self.request("get", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("post", url, **kwargs)

    def get_models(self):
        return self.get("/v1/models", timeout=2)

    def get_chat_completions(self, messages: list[dict], tools: list[dict], stream: bool = False):
        return self.post(
            "/v1/chat/completions",
            json={
                "messages": messages,
                "tools": tools,
                "stream": stream,
                "chat_template_kwargs": {
                    "reasoning_effort": "medium",
                },
            },
            stream=stream,
        )
