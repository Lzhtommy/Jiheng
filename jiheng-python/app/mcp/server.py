from mcp.server.fastmcp import FastMCP

from app.mcp.tools import invoke

mcp = FastMCP("jiheng-public-data", instructions="Public-data tools return normalized data and traceable sources.")


@mcp.tool()
async def search_symbol(keyword: str) -> dict:
    return await invoke("search_symbol", keyword=keyword)


@mcp.tool()
async def get_realtime_quote(symbols: list[str]) -> dict:
    return await invoke("get_realtime_quote", symbols=symbols)


@mcp.tool()
async def get_kline(symbol: str, period: str = "day", count: int = 260, adjust: str = "qfq") -> dict:
    return await invoke("get_kline", symbol=symbol, period=period, count=count, adjust=adjust)


@mcp.tool()
async def get_minute_kline(symbol: str, period: int = 5, count: int = 240) -> dict:
    return await invoke("get_minute_kline", symbol=symbol, period=period, count=count)


@mcp.tool()
async def get_index_quote() -> dict:
    return await invoke("get_index_quote")


@mcp.tool()
async def get_sector_quote() -> dict:
    return await invoke("get_sector_quote")


@mcp.tool()
async def get_fund_flow() -> dict:
    return await invoke("get_fund_flow")


@mcp.tool()
async def list_announcements(
    stock_code: str = "", start_date: str = "", end_date: str = "", keyword: str = "", limit: int = 10
) -> dict:
    return await invoke(
        "list_announcements",
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        limit=limit,
    )


@mcp.tool()
async def get_corporate_calendar(limit: int = 20) -> dict:
    return await invoke("get_corporate_calendar", limit=limit)


@mcp.tool()
async def search_news(keyword: str, limit: int = 10) -> dict:
    return await invoke("search_news", keyword=keyword, limit=limit)


@mcp.tool()
async def get_official_policy(limit: int = 20) -> dict:
    return await invoke("get_official_policy", limit=limit)


@mcp.tool()
async def call_financial_mcp(tool_name: str, arguments: dict) -> dict:
    return await invoke("call_financial_mcp", tool_name=tool_name, arguments=arguments)


if __name__ == "__main__":
    mcp.run()
