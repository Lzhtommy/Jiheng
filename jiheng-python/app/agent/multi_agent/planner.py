import json
from collections.abc import Awaitable, Callable

from pydantic import ValidationError

from app.agent.multi_agent.llm import ChatModel
from app.agent.multi_agent.plan import MAX_NODES, Plan, validate_plan
from app.agent.multi_agent.prompts import planner_prompt

ToolExecutor = Callable[[str, dict], Awaitable[dict]]

MAX_PLANNER_STEPS = 6

SUBMIT_PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_plan",
        "description": "提交完整的多智能体任务树。",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "一句话研究目标"},
                "coverage": {"type": "array", "items": {"type": "string"}},
                "excluded": {"type": "array", "items": {"type": "string"}},
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "如 n1、n2"},
                            "parent": {"type": ["string", "null"], "description": "根节点为 null"},
                            "role": {"type": "string", "description": "角色，如 首席分析师、个股分析员"},
                            "title": {"type": "string"},
                            "instruction": {"type": "string"},
                            "expected_output": {"type": "string"},
                            "tools": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["id", "parent", "role", "title"],
                    },
                },
            },
            "required": ["goal", "nodes"],
        },
    },
}


class PlanningError(RuntimeError):
    pass


async def generate_plan(
    *,
    llm: ChatModel,
    model: str,
    question: str,
    history: list[dict],
    expert_name: str,
    expert_id: str,
    tool_specs: dict[str, dict],
    execute_tool: ToolExecutor,
    max_nodes: int = MAX_NODES,
) -> Plan:
    tools_desc = "\n".join(
        f"- {name}：{spec['function']['description'].splitlines()[0]}" for name, spec in tool_specs.items()
    )
    messages = [
        {"role": "system", "content": planner_prompt(expert_name, expert_id, tools_desc, max_nodes)},
        *history,
        {"role": "user", "content": question},
    ]
    tools = [tool_specs["search_symbol"], SUBMIT_PLAN_TOOL] if "search_symbol" in tool_specs else [SUBMIT_PLAN_TOOL]
    last_errors: list[str] = []
    for _ in range(MAX_PLANNER_STEPS):
        message = await llm.step(messages, model=model, tools=tools, reasoning=True)
        calls = message.get("tool_calls") or []
        if not calls:
            messages.append(message)
            messages.append({"role": "user", "content": "请调用 submit_plan 提交计划。"})
            continue
        messages.append(message)
        for call in calls:
            name = call["function"]["name"]
            arguments = _parse(call["function"].get("arguments"))
            if name == "submit_plan":
                plan, last_errors = _check(arguments, set(tool_specs), max_nodes)
                if plan is not None:
                    return plan
                content = "计划校验未通过，请修正后重新提交：\n" + "\n".join(last_errors)
            elif name == "search_symbol":
                try:
                    content = json.dumps(await execute_tool(name, arguments), ensure_ascii=False)[:4000]
                except Exception as exc:
                    content = f"工具调用失败：{exc}"
            else:
                content = f"规划阶段不可调用 {name}"
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})
    raise PlanningError("未能生成有效计划" + (f"：{'；'.join(last_errors)}" if last_errors else ""))


def _check(arguments: dict, allowed: set[str], max_nodes: int) -> tuple[Plan | None, list[str]]:
    try:
        plan = Plan.model_validate(arguments)
    except ValidationError as exc:
        return None, [f"格式错误：{error['loc']} {error['msg']}" for error in exc.errors()]
    errors = validate_plan(plan, allowed, max_nodes)
    return (None, errors) if errors else (plan, [])


def _parse(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}
