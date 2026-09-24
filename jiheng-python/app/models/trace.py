from typing import Any

from pydantic import BaseModel


class TraceRecord(BaseModel):
    trace_id: str
    correlation_id: str
    conversation_id: str
    mode: str
    expert: str | None = None
    model_input: dict[str, Any]
    model_output: dict[str, Any]
    tool_calls: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    total_duration_ms: int = 0
    created_at: str
