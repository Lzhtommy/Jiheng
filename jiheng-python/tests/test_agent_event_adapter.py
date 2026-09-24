import asyncio

from app.agent.event_adapter import as_sse
from app.agent.runtime import AgentEvent


async def events():
    yield AgentEvent("tool_call", {"id": "1", "name": "get_realtime_quote", "arguments": {"symbols": ["sz000001"]}})
    yield AgentEvent(
        "tool_result",
        {"id": "1", "name": "get_realtime_quote", "success": True, "result": {"price": 10}, "error": None},
    )
    yield AgentEvent("text", {"content": "测试回答"})
    yield AgentEvent("refs", {"refs": []})


def test_event_adapter_emits_contract_events():
    async def collect():
        return [item.split("\n", 1)[0] async for item in as_sse(events(), "trace")]

    assert asyncio.run(collect()) == ["event: tool_call", "event: tool_result", "event: message_chunk", "event: refs"]
