import httpx

from app.config import settings
from app.mcp.models import DataResult, Source


class FinancialMcpProvider:
    """Minimal Streamable HTTP MCP JSON-RPC bridge for configured remote financial tools."""

    async def call(self, tool_name: str, arguments: dict) -> DataResult:
        if not settings.financial_mcp_api_key:
            return DataResult.failure("financial_mcp", "FINANCIAL_MCP_API_KEY is not configured")
        headers = {
            "Authorization": f"Bearer {settings.financial_mcp_api_key}",
            "Accept": "application/json, text/event-stream",
        }
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(settings.financial_mcp_url, json=request, headers=headers)
                response.raise_for_status()
            return DataResult(
                provider="financial_mcp",
                data=response.json(),
                sources=[
                    Source(
                        title=f"财报 MCP：{tool_name}",
                        tag="财报",
                        url=settings.financial_mcp_url,
                        provider="财报 MCP",
                        retrieved_at=DataResult(provider="x", data={}).retrieved_at,
                    )
                ],
            )
        except Exception as exc:
            return DataResult.failure("financial_mcp", str(exc))
