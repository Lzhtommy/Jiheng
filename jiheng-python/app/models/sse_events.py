from typing import Any

from pydantic import BaseModel


class SseEvent(BaseModel):
    event: str
    data: dict[str, Any]


class StartEvent(BaseModel):
    correlation_id: str
    conversation_id: str
    mode: str
    expert: str | None = None


class StageEvent(BaseModel):
    correlation_id: str
    stage: int
    description: str


class ToolCallEvent(BaseModel):
    correlation_id: str
    call_id: str
    tool_name: str
    tool_input: str
    is_skill: bool = False
    node_id: str | None = None


class ToolResultEvent(BaseModel):
    correlation_id: str
    call_id: str
    tool_name: str
    tool_result: str
    success: bool = True
    node_id: str | None = None


class ReasoningStartEvent(BaseModel):
    correlation_id: str
    part_id: str


class ReasoningEndEvent(BaseModel):
    correlation_id: str
    part_id: str


class MessageChunkEvent(BaseModel):
    correlation_id: str
    content: str


class IntroEvent(BaseModel):
    correlation_id: str
    intro: str


class SectionEvent(BaseModel):
    correlation_id: str
    title: str
    para: str | None = None
    items: list[str] | None = None


class TableEvent(BaseModel):
    correlation_id: str
    table_title: str
    table_rows: list[list[str]]


class RiskEvent(BaseModel):
    correlation_id: str
    risk: str


class RefsEvent(BaseModel):
    correlation_id: str
    ref_count: int
    refs: list[dict[str, Any]]


class DoneEvent(BaseModel):
    correlation_id: str
    message_id: str | None = None


class AbortedEvent(BaseModel):
    correlation_id: str
    reason: str
    partial_content: str = ""


class ErrorEvent(BaseModel):
    correlation_id: str
    code: str
    message: str


class WorldCompanyEvent(BaseModel):
    correlation_id: str
    company: dict[str, Any]
