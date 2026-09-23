from typing import Any

from app.mcp.providers.cninfo import CninfoProvider
from app.mcp.providers.content import ContentProvider
from app.mcp.providers.financial import FinancialMcpProvider
from app.mcp.providers.market import MarketProvider

market = MarketProvider()
cninfo = CninfoProvider()
content = ContentProvider()
financial = FinancialMcpProvider()


async def invoke(tool: str, **params: Any) -> dict:
    handlers = {
        "search_symbol": lambda: market.search_symbol(params["keyword"]),
        "get_realtime_quote": lambda: market.quote(params["symbols"]),
        "get_kline": lambda: market.kline(
            params["symbol"], params.get("period", "day"), params.get("count", 260), params.get("adjust", "qfq")
        ),
        "get_minute_kline": lambda: market.minute_kline(
            params["symbol"], params.get("period", 5), params.get("count", 240)
        ),
        "get_index_quote": lambda: market.eastmoney_rank("m:1 s:2,m:0 s:2", "东方财富指数行情"),
        "get_sector_quote": lambda: market.eastmoney_rank("m:90 t:2", "东方财富行业板块行情"),
        "get_fund_flow": lambda: market.eastmoney_rank("m:90 t:2", "东方财富板块资金流", fid="f62"),
        "list_announcements": lambda: cninfo.list_announcements(**params),
        "download_announcement": lambda: cninfo.download(params["url"], params["cache_key"]),
        "get_corporate_calendar": lambda: cninfo.company_events(params.get("limit", 20)),
        "search_news": lambda: content.eastmoney_news(params["keyword"], params.get("limit", 10)),
        "get_official_policy": lambda: content.official_policy(params.get("limit", 20)),
        "call_financial_mcp": lambda: financial.call(params["tool_name"], params.get("arguments", {})),
    }
    if tool not in handlers:
        raise ValueError(f"Unknown data tool: {tool}")
    return (await handlers[tool]()).model_dump()
