import json
from typing import Any

from app.models.sse_events import (
    AbortedEvent,
    DoneEvent,
    ErrorEvent,
    IntroEvent,
    MessageChunkEvent,
    ReasoningEndEvent,
    ReasoningStartEvent,
    RefsEvent,
    RiskEvent,
    SectionEvent,
    StageEvent,
    StartEvent,
    TableEvent,
    ToolCallEvent,
    ToolResultEvent,
)


class SseEmitter:
    """SSE 事件生成器（15 类事件）"""

    @staticmethod
    def format(event_type: str, data: dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    @staticmethod
    def start(event: StartEvent) -> str:
        return SseEmitter.format("start", event.model_dump())

    @staticmethod
    def stage(event: StageEvent) -> str:
        return SseEmitter.format("stage", event.model_dump())

    @staticmethod
    def tool_call(event: ToolCallEvent) -> str:
        return SseEmitter.format("tool_call", event.model_dump())

    @staticmethod
    def tool_result(event: ToolResultEvent) -> str:
        return SseEmitter.format("tool_result", event.model_dump())

    @staticmethod
    def reasoning_start(event: ReasoningStartEvent) -> str:
        return SseEmitter.format("reasoning_start", event.model_dump())

    @staticmethod
    def reasoning_end(event: ReasoningEndEvent) -> str:
        return SseEmitter.format("reasoning_end", event.model_dump())

    @staticmethod
    def message_chunk(event: MessageChunkEvent) -> str:
        return SseEmitter.format("message_chunk", event.model_dump())

    @staticmethod
    def intro(event: IntroEvent) -> str:
        return SseEmitter.format("intro", event.model_dump())

    @staticmethod
    def section(event: SectionEvent) -> str:
        return SseEmitter.format("section", event.model_dump())

    @staticmethod
    def table(event: TableEvent) -> str:
        return SseEmitter.format("table", event.model_dump())

    @staticmethod
    def risk(event: RiskEvent) -> str:
        return SseEmitter.format("risk", event.model_dump())

    @staticmethod
    def refs(event: RefsEvent) -> str:
        return SseEmitter.format("refs", event.model_dump())

    @staticmethod
    def done(event: DoneEvent) -> str:
        return SseEmitter.format("done", event.model_dump())

    @staticmethod
    def aborted(event: AbortedEvent) -> str:
        return SseEmitter.format("aborted", event.model_dump())

    @staticmethod
    def error(event: ErrorEvent) -> str:
        return SseEmitter.format("error", event.model_dump())
