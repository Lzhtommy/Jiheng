from typing import Any

from app.tools.base import BaseTool, ToolResult


class SkillPack:
    """技能工具包：按需从 Java 读取技能配置并挂载为工具"""

    def __init__(self):
        self._mounted: dict[str, BaseTool] = {}

    async def mount(self, skill_id: str) -> BaseTool:
        from app.clients.java_internal import JavaInternalClient

        if skill_id in self._mounted:
            return self._mounted[skill_id]

        client = JavaInternalClient()
        skill_config = await client.get_skill_config(skill_id)

        class SkillTool(BaseTool):
            @property
            def name(self) -> str:
                return f"技能·{skill_config.get('name', skill_id)}"

            @property
            def schema(self) -> dict[str, Any]:
                return {"type": "object", "properties": {"input": {"type": "string"}}}

            async def run(self, input: str = "", **kwargs) -> ToolResult:
                return ToolResult(content=skill_config.get("prompt_template", ""), sources=[])

        tool = SkillTool()
        self._mounted[skill_id] = tool
        return tool

    def unmount(self, skill_id: str):
        self._mounted.pop(skill_id, None)
