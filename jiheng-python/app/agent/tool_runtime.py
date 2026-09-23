import asyncio
import json
from collections.abc import AsyncGenerator

import httpx

from app.agent.profiles import AgentProfile
from app.agent.runtime import AgentEvent, AgentRunContext
from app.agent.tool_registry import execute, openai_tools
from app.config import settings


class DeepSeekToolRuntime:
    """Online agent runtime using the official DeepSeek-compatible Tool Calls API."""

    async def stream(
        self, messages: list[dict], profile: AgentProfile, context: AgentRunContext
    ) -> AsyncGenerator[AgentEvent, None]:
        if not settings.deepseek_api_key:
            yield AgentEvent("text", {"content": "暂未配置 DeepSeek API，无法执行智能体分析。"})
            return
        conversation = [{"role": "system", "content": profile.system_prompt}, *messages]
        refs: list[dict] = []
        headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
        tools = await openai_tools(profile.tool_names)
        wrote_text = False
        async with httpx.AsyncClient(timeout=httpx.Timeout(10, read=60)) as client:
            for round_index in range(profile.max_tool_rounds + 1):
                payload = {"model": profile.model, "messages": conversation, "tools": tools}
                # 轮次用尽后强制基于已有数据作答，避免只回一句“已达上限”
                payload["tool_choice"] = "none" if round_index == profile.max_tool_rounds else "auto"
                if profile.reasoning_effort:
                    payload["reasoning_effort"] = profile.reasoning_effort
                    payload["thinking"] = {"type": "enabled"}
                message: dict = {}
                separated = False
                try:
                    async for delta in _stream_completion(client, headers, payload, message):
                        if wrote_text and not separated:
                            delta = "\n\n" + delta
                        separated = True
                        wrote_text = True
                        yield AgentEvent("text", {"content": delta})
                except httpx.TimeoutException as exc:
                    if not separated:
                        raise RuntimeError("模型接口响应超时，请稍后重试") from exc
                    yield AgentEvent("text", {"content": "\n\n（模型响应中断，以上为已生成的内容）"})
                    yield AgentEvent("refs", {"refs": refs})
                    return
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    yield AgentEvent("refs", {"refs": refs})
                    return
                conversation.append(message)
                parsed = [(call, _arguments(call)) for call in tool_calls]
                for call, arguments in parsed:
                    yield AgentEvent("tool_call", {"id": call["id"], "name": call["function"]["name"], "arguments": arguments})
                results = await asyncio.gather(*(_run_tool(call["function"]["name"], args) for call, args in parsed))
                for (call, _), result in zip(parsed, results):
                    refs.extend(result.get("sources", []))
                    yield AgentEvent(
                        "tool_result",
                        {
                            "id": call["id"],
                            "name": call["function"]["name"],
                            "success": result.get("status") == "success",
                            "result": result.get("data", {}),
                            "error": result.get("error"),
                        },
                    )
                    conversation.append({"role": "tool", "tool_call_id": call["id"], "content": _tool_content(result)})
        yield AgentEvent("refs", {"refs": refs})


async def _stream_completion(
    client: httpx.AsyncClient, headers: dict, payload: dict, message: dict
) -> AsyncGenerator[str, None]:
    """Yields content deltas; fills ``message`` with the assembled assistant message."""
    content: list[str] = []
    reasoning: list[str] = []
    calls: dict[int, dict] = {}
    async with client.stream(
        "POST", f"{settings.deepseek_base_url}/chat/completions", headers=headers, json={**payload, "stream": True}
    ) as response:
        if response.status_code >= 400:
            body = (await response.aread()).decode(errors="replace")[:300]
            raise RuntimeError(f"模型接口返回 {response.status_code}：{body}")
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
            if delta.get("reasoning_content"):
                reasoning.append(delta["reasoning_content"])
            if delta.get("content"):
                content.append(delta["content"])
                yield delta["content"]
            for part in delta.get("tool_calls") or []:
                slot = calls.setdefault(
                    part.get("index", len(calls)), {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                )
                if part.get("id"):
                    slot["id"] = part["id"]
                function = part.get("function") or {}
                slot["function"]["name"] += function.get("name") or ""
                slot["function"]["arguments"] += function.get("arguments") or ""
    message.update({"role": "assistant", "content": "".join(content)})
    if reasoning:
        message["reasoning_content"] = "".join(reasoning)
    if calls:
        message["tool_calls"] = [calls[index] for index in sorted(calls)]


MAX_TOOL_CONTENT_CHARS = 6000


def _tool_content(result: dict) -> str:
    text = json.dumps(result, ensure_ascii=False, default=str)
    if len(text) <= MAX_TOOL_CONTENT_CHARS:
        return text
    return text[:MAX_TOOL_CONTENT_CHARS] + "…（数据过长已截断）"


def _arguments(call: dict) -> dict:
    try:
        value = json.loads(call["function"].get("arguments") or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


async def _run_tool(name: str, arguments: dict) -> dict:
    try:
        return await execute(name, arguments)
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "data": {}}
