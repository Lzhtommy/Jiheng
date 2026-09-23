import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Protocol

import httpx

from app.config import settings

RETRY_STATUS = {429, 500, 502, 503, 504}


class ChatModel(Protocol):
    async def step(
        self, messages: list[dict], *, model: str, tools: list[dict] | None = None, reasoning: bool = False
    ) -> dict: ...

    def stream_text(self, messages: list[dict], *, model: str) -> AsyncGenerator[str, None]: ...


class DeepSeekChat:
    def __init__(self, timeout: float = 120, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        self.headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
        self.url = f"{settings.deepseek_base_url}/chat/completions"

    def _payload(self, messages: list[dict], model: str, tools: list[dict] | None, reasoning: bool) -> dict:
        payload: dict = {"model": model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if reasoning:
            payload["reasoning_effort"] = "high"
            payload["thinking"] = {"type": "enabled"}
        return payload

    async def step(
        self, messages: list[dict], *, model: str, tools: list[dict] | None = None, reasoning: bool = False
    ) -> dict:
        payload = self._payload(messages, model, tools, reasoning)
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(self.url, headers=self.headers, json=payload)
                if response.status_code in RETRY_STATUS and attempt < self.retries:
                    await asyncio.sleep(2**attempt)
                    continue
                response.raise_for_status()
                return response.json()["choices"][0]["message"]
            except (httpx.TransportError, httpx.TimeoutException):
                if attempt >= self.retries:
                    raise
                await asyncio.sleep(2**attempt)
        raise RuntimeError("unreachable")

    async def stream_text(self, messages: list[dict], *, model: str) -> AsyncGenerator[str, None]:
        payload = self._payload(messages, model, None, False) | {"stream": True}
        async with (
            httpx.AsyncClient(timeout=self.timeout) as client,
            client.stream("POST", self.url, headers=self.headers, json=payload) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    choices = json.loads(data).get("choices") or []
                except json.JSONDecodeError:
                    continue
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                if delta.get("content"):
                    yield delta["content"]
