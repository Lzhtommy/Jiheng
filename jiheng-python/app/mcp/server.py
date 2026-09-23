from mcp.server.fastmcp import FastMCP

from app.mcp.tools import invoke

mcp = FastMCP("jiheng-public-data", instructions="Public-data tools return normalized data and traceable sources.")


@mcp.tool()
async def search_symbol(keyword: str) -> dict:
    """按公司名称、拼音或代码检索证券，返回 symbol（如 sh600519、sz000001），供其他行情工具使用。"""
    return await invoke("search_symbol", keyword=keyword)


@mcp.tool()
async def get_realtime_quote(symbols: list[str]) -> dict:
    """批量查询实时行情。symbols 格式为交易所小写前缀+6 位代码：沪市 sh600519、深市 sz000001、北交所 bj430047；
    指数如 sh000001（上证指数）、sz399001（深证成指）。不要使用 600519.SH 这类格式。"""
    return await invoke("get_realtime_quote", symbols=symbols)


@mcp.tool()
async def get_kline(symbol: str, period: str = "day", count: int = 260, adjust: str = "qfq") -> dict:
    """日/周/月 K 线（period=day|week|month），symbol 格式同 get_realtime_quote（如 sh600519）。"""
    return await invoke("get_kline", symbol=symbol, period=period, count=count, adjust=adjust)


@mcp.tool()
async def get_minute_kline(symbol: str, period: int = 5, count: int = 240) -> dict:
    """分钟 K 线（period=1|5|15|30|60），symbol 格式同 get_realtime_quote（如 sh600519）。"""
    return await invoke("get_minute_kline", symbol=symbol, period=period, count=count)


@mcp.tool()
async def get_index_quote() -> dict:
    """沪深主要指数行情排行（东方财富）。查询单个指数可改用 get_realtime_quote（如 sh000001）。"""
    return await invoke("get_index_quote")


@mcp.tool()
async def get_sector_quote() -> dict:
    """行业板块涨跌幅排行（东方财富）。"""
    return await invoke("get_sector_quote")


@mcp.tool()
async def get_fund_flow() -> dict:
    """行业板块主力资金净流入排行（东方财富）。"""
    return await invoke("get_fund_flow")


@mcp.tool()
async def list_announcements(
    stock_code: str = "", start_date: str = "", end_date: str = "", keyword: str = "", limit: int = 10
) -> dict:
    """巨潮资讯公告检索。stock_code 为不带前缀的 6 位代码（如 600519）；日期格式 yyyy-MM-dd。"""
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
    """巨潮资讯近期公司大事日历（分红、股东大会、解禁等）。"""
    return await invoke("get_corporate_calendar", limit=limit)


@mcp.tool()
async def search_news(keyword: str, limit: int = 10) -> dict:
    """按关键词检索财经新闻（东方财富），keyword 用公司简称或行业词，如“贵州茅台”“白酒”。"""
    return await invoke("search_news", keyword=keyword, limit=limit)


@mcp.tool()
async def get_official_policy(limit: int = 20) -> dict:
    """中国政府网最新政策文件列表。"""
    return await invoke("get_official_policy", limit=limit)


@mcp.tool()
async def call_financial_mcp(tool_name: str, arguments: dict) -> dict:
    """调用远程财报 MCP（A 股/港股定期报告全文）。tool_name 可选：
    searchCompanyInfo{query, market: CN-A|HK} → 得到 stockCode；
    financialKeywordSearch{keywords[], stockCode, reportType 如 2025a4 年报 / 2026h2 半年报} → 定位页码；
    getFinancialReportPages{stockCode, reportType, startPage, pageCount<=5} → 读取页面；
    searchReportsByPublishDate{days<=7 或 startDate/endDate} → 按披露日期查公司。"""
    return await invoke("call_financial_mcp", tool_name=tool_name, arguments=arguments)


if __name__ == "__main__":
    mcp.run()
