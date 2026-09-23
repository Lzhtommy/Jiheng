from app.agent.multi_agent.executor import GraphExecutor
from app.agent.multi_agent.llm import DeepSeekChat
from app.agent.multi_agent.plan import Plan, validate_plan
from app.agent.multi_agent.planner import generate_plan
from app.agent.tool_registry import execute, tool_specs
from app.clients.java_internal import JavaInternalClient
from app.config import settings
from app.models.chat import MultiAgentRequest, PlanRequest

EXPERT_NAMES = {
    "expert_stock_research": "个股分析师",
    "expert_industry_research": "行业分析师",
    "expert_research_report": "财报分析师",
}


async def expert_name(expert_id: str) -> str:
    try:
        experts = await JavaInternalClient().get_experts()
    except Exception:
        experts = []
    for item in experts:
        if expert_id in {item.get("expertId"), item.get("expert_id")} and item.get("name"):
            return str(item["name"])
    return EXPERT_NAMES.get(expert_id, "金融研究专家")


def _split(req: PlanRequest) -> tuple[str, list[dict]]:
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    return messages[-1]["content"], messages[:-1]


async def build_plan(req: PlanRequest) -> tuple[Plan, list[str]]:
    specs = await tool_specs()
    question, history = _split(req)
    plan = await generate_plan(
        llm=DeepSeekChat(),
        model=settings.deepseek_model_deep,
        question=question,
        history=history,
        expert_name=await expert_name(req.expert),
        expert_id=req.expert,
        tool_specs=specs,
        execute_tool=execute,
        max_nodes=settings.multi_agent_max_nodes,
    )
    return plan, list(specs)


async def plan_errors(plan: Plan) -> list[str]:
    return validate_plan(plan, set(await tool_specs()), settings.multi_agent_max_nodes)


async def build_executor(req: MultiAgentRequest) -> GraphExecutor:
    question, _ = _split(req)
    return GraphExecutor(
        plan=req.plan,
        question=question,
        expert_name=await expert_name(req.expert),
        llm=DeepSeekChat(),
        leaf_model=settings.multi_agent_leaf_model or settings.deepseek_model_quick,
        lead_model=settings.deepseek_model_deep,
        tool_specs=await tool_specs(),
        execute_tool=execute,
        max_parallel=settings.multi_agent_max_parallel,
        time_budget=settings.multi_agent_time_budget_seconds,
    )
