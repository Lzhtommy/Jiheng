from app.mcp.server import mcp
from app.mcp.tools import invoke

_tool_specs: dict[str, dict] = {}


async def tool_specs() -> dict[str, dict]:
    if not _tool_specs:
        for tool in await mcp.list_tools():
            _tool_specs[tool.name] = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or tool.name,
                    "parameters": tool.inputSchema,
                },
            }
    return _tool_specs


async def openai_tools(names: tuple[str, ...] | list[str]) -> list[dict]:
    specs = await tool_specs()
    return [specs[name] for name in names if name in specs]


async def execute(name: str, arguments: dict) -> dict:
    return await invoke(name, **arguments)
