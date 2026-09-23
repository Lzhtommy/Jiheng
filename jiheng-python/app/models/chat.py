from enum import Enum

from pydantic import BaseModel, Field

from app.agent.multi_agent.plan import Plan


class ChatMode(str, Enum):
    QUICK = "quick"
    DEEP = "deep"
    EXPERT = "expert"


class ChatMessage(BaseModel):
    role: str = Field(..., description="user / assistant")
    content: str
    created_at: str | None = None


class ChatRequest(BaseModel):
    mode: ChatMode = ChatMode.QUICK
    expert: str | None = Field(None, description="专家 ID，mode=expert 时必填")
    conversation_id: str
    messages: list[ChatMessage] = Field(..., min_length=1)
    model: str | None = None
    system_prompt: str | None = None


class PlanRequest(BaseModel):
    expert: str
    conversation_id: str
    messages: list[ChatMessage] = Field(..., min_length=1)


class MultiAgentRequest(PlanRequest):
    plan: Plan
