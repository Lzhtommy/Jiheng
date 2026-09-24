import asyncio
import json

import httpx

from app.agent.profiles import AgentProfile
from app.agent.runtime import AgentRunContext
from app.agent.tool_runtime import FINAL_ROUND_INSTRUCTION, DeepSeekToolRuntime, _stream_completion
from app.config import settings


def _sse(*deltas: dict) -> bytes:
    lines = [f"data: {json.dumps({'choices': [{'delta': delta}]}, ensure_ascii=False)}" for delta in deltas]
    return ("\n\n".join([*lines, "data: [DONE]"]) + "\n\n").encode()


async def _completion(content: bytes, *, suppress_tool_markup: bool) -> tuple[list[str], dict]:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=content))
    message = {}
    async with httpx.AsyncClient(transport=transport) as client:
        chunks = [
            chunk
            async for chunk in _stream_completion(
                client, {}, {"model": "test", "messages": []}, message, suppress_tool_markup=suppress_tool_markup
            )
        ]
    return chunks, message


def test_stream_completion_keeps_dsml_text_during_tool_round():
    content = _sse({"content": "先取数<｜DS"}, {"content": "ML｜call"})

    chunks, message = asyncio.run(_completion(content, suppress_tool_markup=False))

    assert "".join(chunks) == "先取数<｜DSML｜call"
    assert message["content"] == "先取数<｜DSML｜call"


def test_stream_completion_suppresses_split_dsml_on_final_round():
    content = _sse({"content": "最终结论<｜DS"}, {"content": "ML｜call"})

    chunks, message = asyncio.run(_completion(content, suppress_tool_markup=True))

    assert "".join(chunks) == "最终结论"
    assert message["content"] == "最终结论"


def test_runtime_removes_tools_and_requests_answer_on_final_round(monkeypatch):
    requests = []

    async def fake_openai_tools(tool_names):
        return [{"type": "function", "function": {"name": "financials"}}]

    async def fake_run_tool(name, arguments):
        return {"status": "success", "data": {"years": [2023, 2024, 2025]}, "sources": []}

    async def fake_completion(client, headers, payload, message, *, suppress_tool_markup=False):
        requests.append((payload, suppress_tool_markup))
        if len(requests) == 1:
            message.update(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"id": "call-1", "function": {"name": "financials", "arguments": '{"years": 3}'}}],
                }
            )
            return
        message.update({"role": "assistant", "content": "近三年营收持续增长。"})
        yield "近三年营收持续增长。"

    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr("app.agent.tool_runtime.openai_tools", fake_openai_tools)
    monkeypatch.setattr("app.agent.tool_runtime._run_tool", fake_run_tool)
    monkeypatch.setattr("app.agent.tool_runtime._stream_completion", fake_completion)
    profile = AgentProfile("quick", "test", "system", ("financials",), 1, None)

    async def collect():
        runtime = DeepSeekToolRuntime()
        context = AgentRunContext("user", "conversation")
        return [event async for event in runtime.stream([{"role": "user", "content": "近三年财报"}], profile, context)]

    events = asyncio.run(collect())

    assert [event.data["content"] for event in events if event.type == "text"] == ["近三年营收持续增长。"]
    final_payload, suppress_tool_markup = requests[1]
    assert "tools" not in final_payload
    assert final_payload["messages"][-1] == {"role": "user", "content": FINAL_ROUND_INSTRUCTION}
    assert suppress_tool_markup is True
