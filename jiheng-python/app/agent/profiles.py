from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class AgentProfile:
    mode: str
    model: str
    system_prompt: str
    tool_names: tuple[str, ...]
    max_tool_rounds: int
    reasoning_effort: str | None


DEFAULT_TOOLS = (
    "search_symbol",
    "get_realtime_quote",
    "get_kline",
    "get_minute_kline",
    "get_index_quote",
    "get_sector_quote",
    "get_fund_flow",
    "list_announcements",
    "search_news",
    "get_official_policy",
)


def build_profile(mode: str, expert: dict | None = None) -> AgentProfile:
    is_deep = mode in {"deep", "expert"}
    model = settings.deepseek_model_deep if is_deep else settings.deepseek_model_quick
    prompt = "你是玑衡AI金融研究助手。只能依据工具返回的数据作数值结论，引用必须来自工具来源。不得给出买卖指令。"
    if expert:
        prompt += "\n专家角色：" + str(expert.get("name", expert.get("expertId", "金融研究专家")))
        instruction = expert.get("systemPrompt") or expert.get("system_prompt") or expert.get("description") or ""
        if instruction:
            prompt += "\n" + str(instruction)
    return AgentProfile(
        mode=mode,
        model=model,
        system_prompt=prompt,
        tool_names=DEFAULT_TOOLS,
        max_tool_rounds=6 if is_deep else 2,
        reasoning_effort="high" if is_deep else None,
    )
