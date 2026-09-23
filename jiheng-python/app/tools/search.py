from typing import Any

from app.mcp.tools import invoke
from app.tools.base import BaseTool, ToolResult, result_from_data


class SearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "聚合搜索"

    @property
    def schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}

    async def run(self, query: str = "", **kwargs) -> ToolResult:
        return result_from_data(await invoke("search_news", keyword=query))
