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
        async with httpx.AsyncClient(timeout=90) as client:
            for _ in range(profile.max_tool_rounds):
                payload = {
                    "model": profile.model,
                    "messages": conversation,
                    "tools": openai_tools(profile.tool_names),
                    "tool_choice": "auto",
                    "stream": False,
                }
                if profile.reasoning_effort:
                    payload["reasoning_effort"] = profile.reasoning_effort
                    payload["thinking"] = {"type": "enabled"}
                response = await client.post(
                    f"{settings.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                message = response.json()["choices"][0]["message"]
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    if message.get("content"):
                        yield AgentEvent("text", {"content": message["content"]})
                    yield AgentEvent("refs", {"refs": refs})
                    return
                conversation.append(message)
                for call in tool_calls:
                    name = call["function"]["name"]
                    arguments = json.loads(call["function"].get("arguments") or "{}")
                    yield AgentEvent("tool_call", {"id": call["id"], "name": name, "arguments": arguments})
                    try:
                        result = await execute(name, arguments)
                        refs.extend(result.get("sources", []))
                        success = result.get("status") == "success"
                        yield AgentEvent(
                            "tool_result",
                            {
                                "id": call["id"],
                                "name": name,
                                "success": success,
                                "result": result.get("data", {}),
                                "error": result.get("error"),
                            },
                        )
                    except Exception as exc:
                        result = {"status": "failed", "error": str(exc), "data": {}}
                        yield AgentEvent(
                            "tool_result",
                            {"id": call["id"], "name": name, "success": False, "result": {}, "error": str(exc)},
                        )
                    conversation.append(
                        {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, ensure_ascii=False)}
                    )
        yield AgentEvent("text", {"content": "本次分析的工具调用轮次已达到上限。"})
        yield AgentEvent("refs", {"refs": refs})
