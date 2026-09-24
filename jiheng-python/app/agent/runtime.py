from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.agent.profiles import AgentProfile


@dataclass(frozen=True)
class AgentEvent:
    type: str
    data: dict


@dataclass(frozen=True)
class AgentRunContext:
    user_id: str
    conversation_id: str

    def _safe(self, value: str) -> str:
        return "".join(char for char in value if char.isalnum() or char in {"-", "_"}) or "anonymous"

    def session_key(self) -> str:
        return f"{self._safe(self.user_id)}-{self._safe(self.conversation_id)}"

    def root(self, base: str) -> Path:
        return Path(base).resolve() / self._safe(self.user_id) / self._safe(self.conversation_id)


class AgentRuntime(Protocol):
    async def stream(
        self, messages: list[dict], profile: AgentProfile, context: AgentRunContext
    ) -> AsyncGenerator[AgentEvent, None]: ...
