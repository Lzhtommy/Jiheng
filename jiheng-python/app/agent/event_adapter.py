from collections.abc import AsyncGenerator

from app.agent.runtime import AgentEvent
from app.core.sse_emitter import SseEmitter
from app.models.sse_events import MessageChunkEvent, RefsEvent, ToolCallEvent, ToolResultEvent


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
                    tool_input=str(event.data["arguments"]),
                )
            )
        elif event.type == "tool_result":
            yield SseEmitter.tool_result(
                ToolResultEvent(
                    correlation_id=correlation_id,
                    call_id=event.data["id"],
                    tool_name=event.data["name"],
                    tool_result=str(event.data["result"] if event.data["success"] else event.data["error"]),
                    success=event.data["success"],
                )
            )
        elif event.type == "refs":
            yield SseEmitter.refs(
                RefsEvent(correlation_id=correlation_id, ref_count=len(event.data["refs"]), refs=event.data["refs"])
            )
