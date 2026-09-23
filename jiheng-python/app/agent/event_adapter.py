import json
from collections.abc import AsyncGenerator
from typing import Any

from app.agent.runtime import AgentEvent
from app.core.sse_emitter import SseEmitter
from app.models.sse_events import MessageChunkEvent, RefsEvent, ToolCallEvent, ToolResultEvent

GRAPH_EVENTS = {"agent_graph", "agent_status", "agent_message", "agent_output", "phase"}


async def as_sse(events: AsyncGenerator[AgentEvent, None], correlation_id: str) -> AsyncGenerator[str, None]:
    async for event in events:
        if event.type == "text":
            yield SseEmitter.message_chunk(
                MessageChunkEvent(correlation_id=correlation_id, content=event.data["content"])
            )
        elif event.type == "tool_call":
            yield SseEmitter.tool_call(
                ToolCallEvent(
                    correlation_id=correlation_id,
                    call_id=event.data["id"],
                    tool_name=event.data["name"],
                    tool_input=json.dumps(event.data["arguments"], ensure_ascii=False),
                    node_id=event.data.get("node_id"),
                )
            )
        elif event.type == "tool_result":
            yield SseEmitter.tool_result(
                ToolResultEvent(
                    correlation_id=correlation_id,
                    call_id=event.data["id"],
                    tool_name=event.data["name"],
                    tool_result=_as_text(event.data["result"] if event.data["success"] else event.data["error"]),
                    success=event.data["success"],
                    node_id=event.data.get("node_id"),
                )
            )
        elif event.type == "refs":
            yield SseEmitter.refs(
                RefsEvent(correlation_id=correlation_id, ref_count=len(event.data["refs"]), refs=event.data["refs"])
            )
        elif event.type in GRAPH_EVENTS:
            yield SseEmitter.format(event.type, {"correlation_id": correlation_id, **event.data})


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
