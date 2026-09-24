from abc import ABC, abstractmethod
from typing import Any


class ToolResult:
    def __init__(self, content: str, sources: list[dict[str, Any]], success: bool = True):
        self.content = content
        self.sources = sources
        self.success = success


def result_from_data(data: dict) -> ToolResult:
    return ToolResult(
        content=str(data.get("data", {})),
        sources=data.get("sources", []),
        success=data.get("status") == "success",
    )


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def schema(self) -> dict[str, Any]: ...

    @abstractmethod
    async def run(self, **params) -> ToolResult: ...
