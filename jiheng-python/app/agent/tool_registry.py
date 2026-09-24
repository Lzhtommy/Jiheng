from app.mcp.tools import invoke

TOOL_SCHEMAS = {
    "search_symbol": {"type": "object", "properties": {"keyword": {"type": "string"}}, "required": ["keyword"]},
    "get_realtime_quote": {
        "type": "object",
        "properties": {"symbols": {"type": "array", "items": {"type": "string"}}},
        "required": ["symbols"],
    },
    "get_kline": {
        "type": "object",
        "properties": {"symbol": {"type": "string"}, "period": {"type": "string"}},
        "required": ["symbol"],
    },
    "get_minute_kline": {
        "type": "object",
        "properties": {"symbol": {"type": "string"}, "period": {"type": "integer"}},
        "required": ["symbol"],
    },
    "list_announcements": {
        "type": "object",
        "properties": {"stock_code": {"type": "string"}, "keyword": {"type": "string"}},
    },
    "search_news": {"type": "object", "properties": {"keyword": {"type": "string"}}, "required": ["keyword"]},
    "get_official_policy": {"type": "object", "properties": {}},
    "get_index_quote": {"type": "object", "properties": {}},
    "get_sector_quote": {"type": "object", "properties": {}},
    "get_fund_flow": {"type": "object", "properties": {}},
}


def openai_tools(names: tuple[str, ...]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"Jiheng market data tool: {name}",
                "parameters": TOOL_SCHEMAS[name],
            },
        }
        for name in names
    ]


async def execute(name: str, arguments: dict) -> dict:
    return await invoke(name, **arguments)
