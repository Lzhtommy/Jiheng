from typing import Any

from app.mcp.tools import invoke
from app.tools.base import BaseTool, ToolResult, result_from_data


class QuoteTool(BaseTool):
    @property
    def name(self) -> str:
        return "行情查询"

    @property
    def schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}

    async def run(self, symbol: str = "", **kwargs) -> ToolResult:
        return result_from_data(await invoke("get_realtime_quote", symbols=[symbol]))
