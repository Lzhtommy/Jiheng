from typing import Any

from app.mcp.tools import invoke
from app.tools.base import BaseTool, ToolResult, result_from_data


class ResearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "研报检索"

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}, "doc_type": {"type": "string"}},
            "required": ["query"],
        }

    async def run(self, query: str = "", doc_type: str = "研报", **kwargs) -> ToolResult:
        if doc_type == "公告":
            return result_from_data(await invoke("list_announcements", keyword=query))
        return result_from_data(await invoke("search_news", keyword=query))
