import asyncio
import json
from collections.abc import AsyncGenerator

import httpx

from app.agent.profiles import AgentProfile
from app.agent.runtime import AgentEvent, AgentRunContext
from app.agent.sources import add_sources, requires_sources
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
        refs: dict[str, dict] = {}
        headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
        tools = await openai_tools(profile.tool_names)
        wrote_text = False
        source_retry_used = False
        question = str(messages[-1].get("content", "")) if messages else ""
        async with httpx.AsyncClient(timeout=httpx.Timeout(10, read=60)) as client:
            for round_index in range(profile.max_tool_rounds + 1):
                if round_index == profile.max_tool_rounds:
                    # 网关在 tool_choice=none 时仍可能把工具调用当正文吐出，最后一轮不再提供工具
                    conversation.append({"role": "user", "content": FINAL_ROUND_INSTRUCTION})
                    payload = {"model": profile.model, "messages": conversation}
                else:
                    payload = {"model": profile.model, "messages": conversation, "tools": tools, "tool_choice": "auto"}
                if profile.reasoning_effort:
                    payload["reasoning_effort"] = profile.reasoning_effort
                    payload["thinking"] = {"type": "enabled"}
                message: dict = {}
                separated = False
                pending: list[str] = []
                try:
                    async for delta in _stream_completion(
                        client,
                        headers,
                        payload,
                        message,
                        suppress_tool_markup=round_index == profile.max_tool_rounds,
                    ):
                        if profile.mode == "expert":
                            pending.append(delta)
                        else:
                            if wrote_text and not separated:
                                delta = "\n\n" + delta
                            wrote_text = True
                            yield AgentEvent("text", {"content": delta})
                        separated = True
                except httpx.TimeoutException as exc:
                    if round_index == 0 and not separated:
                        raise RuntimeError("模型接口响应超时，请稍后重试") from exc
                    note = "（模型响应中断，以上为已生成的内容）" if separated else NO_ANSWER_TEXT
                    yield AgentEvent("text", {"content": ("\n\n" if wrote_text else "") + note})
                    yield AgentEvent("refs", {"refs": list(refs.values())})
                    return
                tool_calls = message.get("tool_calls") or []
                if not tool_calls or round_index == profile.max_tool_rounds:
                    answer = "".join(pending) if profile.mode == "expert" else str(message.get("content") or "")
                    needs_sources = profile.mode == "expert" and requires_sources(question, answer)
                    if needs_sources and not refs and not source_retry_used and round_index < profile.max_tool_rounds:
                        conversation.append(message)
                        conversation.append({"role": "user", "content": SOURCE_REQUIRED_INSTRUCTION})
                        source_retry_used = True
                        continue
                    if needs_sources and not refs:
                        answer = NO_SOURCE_TEXT
                    if profile.mode == "expert":
                        if wrote_text and answer:
                            answer = "\n\n" + answer
                        if answer:
                            wrote_text = True
                            yield AgentEvent("text", {"content": answer})
                    elif not separated:
                        yield AgentEvent("text", {"content": ("\n\n" if wrote_text else "") + NO_ANSWER_TEXT})
                    yield AgentEvent("refs", {"refs": list(refs.values())})
                    return
                conversation.append(message)
                parsed = [(call, _arguments(call)) for call in tool_calls]
                for call, arguments in parsed:
                    yield AgentEvent(
                        "tool_call", {"id": call["id"], "name": call["function"]["name"], "arguments": arguments}
                    )
                results = await asyncio.gather(*(_run_tool(call["function"]["name"], args) for call, args in parsed))
                for (call, _), result in zip(parsed, results):
                    if result.get("status") == "success":
                        add_sources(refs, result.get("sources") or [])
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
        yield AgentEvent("refs", {"refs": list(refs.values())})


async def _stream_completion(
    client: httpx.AsyncClient,
    headers: dict,
    payload: dict,
    message: dict,
    *,
    suppress_tool_markup: bool = False,
) -> AsyncGenerator[str, None]:
    """Yields content deltas; fills ``message`` with the assembled assistant message."""
    content: list[str] = []
    reasoning: list[str] = []
    calls: dict[int, dict] = {}
    emitted = 0
    markup_at = -1
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
                if suppress_tool_markup and markup_at < 0:
                    text = "".join(content)
                    markup_at = text.find(TOOL_MARKUP)
                    safe = markup_at if markup_at >= 0 else len(text) - _partial_markup_len(text)
                    if safe > emitted:
                        yield text[emitted:safe]
                        emitted = safe
                elif not suppress_tool_markup:
                    yield delta["content"]
            for part in delta.get("tool_calls") or []:
                slot = calls.setdefault(
                    part.get("index", len(calls)),
                    {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                )
                if part.get("id"):
                    slot["id"] = part["id"]
                function = part.get("function") or {}
                slot["function"]["name"] += function.get("name") or ""
                slot["function"]["arguments"] += function.get("arguments") or ""
    text = "".join(content)
    if suppress_tool_markup and markup_at >= 0:
        text = text[:markup_at]
    elif suppress_tool_markup and len(text) > emitted:
        yield text[emitted:]
    message.update({"role": "assistant", "content": text})
    if reasoning:
        message["reasoning_content"] = "".join(reasoning)
    if calls:
        message["tool_calls"] = [calls[index] for index in sorted(calls)]


MAX_TOOL_CONTENT_CHARS = 6000
TOOL_MARKUP = "<｜DSML｜"
FINAL_ROUND_INSTRUCTION = (
    "工具调用次数已用完。请只根据上面已经取得的工具数据写出最终回答，缺失的数据写明暂无，不要再调用任何工具。"
)
SOURCE_REQUIRED_INSTRUCTION = (
    "这个问题涉及外部可验证的金融事实，但你尚未取得可引用来源。不要直接回答；"
    "请先调用最相关的数据工具，取得来源后再基于工具结果作答。"
)
NO_SOURCE_TEXT = "暂未取得可核验的数据来源，因此无法给出可靠的事实性分析。请稍后重试或缩小查询范围。"
NO_ANSWER_TEXT = (
    "（本次取数已结束，但模型没有给出完整结论。上方工具卡片里是已取得的数据，可以换成深度研究或分析师模式再问一次。）"
)


def _partial_markup_len(text: str) -> int:
    for size in range(min(len(TOOL_MARKUP) - 1, len(text)), 0, -1):
        if TOOL_MARKUP.startswith(text[-size:]):
            return size
    return 0


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
