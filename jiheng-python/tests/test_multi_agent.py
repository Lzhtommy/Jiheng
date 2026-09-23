import asyncio
import itertools
import json

from app.agent.multi_agent.executor import GraphExecutor
from app.agent.multi_agent.plan import Plan, validate_plan
from app.agent.multi_agent.planner import generate_plan

TOOLS = {"search_symbol", "get_realtime_quote", "search_news"}
SPECS = {
    name: {"type": "function", "function": {"name": name, "description": name, "parameters": {}}} for name in TOOLS
}


def make_plan(**overrides) -> Plan:
    data = {
        "goal": "对比茅台与五粮液",
        "nodes": [
            {"id": "n1", "parent": None, "role": "首席分析师", "title": "汇总"},
            {
                "id": "n2",
                "parent": "n1",
                "role": "个股分析员",
                "title": "茅台行情",
                "instruction": "查询 sh600519 行情",
                "tools": ["get_realtime_quote"],
            },
            {
                "id": "n3",
                "parent": "n1",
                "role": "个股分析员",
                "title": "五粮液行情",
                "instruction": "查询 sz000858 行情",
                "tools": ["get_realtime_quote"],
            },
        ],
    }
    data.update(overrides)
    return Plan.model_validate(data)


def test_validate_plan_accepts_valid_tree():
    assert validate_plan(make_plan(), TOOLS) == []


def test_validate_plan_reports_structural_errors():
    plan = make_plan()
    plan.nodes[2].tools = ["unknown_tool"]
    plan.nodes.append(plan.nodes[0].model_copy(update={"id": "n9"}))
    errors = validate_plan(plan, TOOLS)
    assert any("根节点" in error for error in errors)

    deep = make_plan()
    deep.nodes += [
        deep.nodes[1].model_copy(update={"id": "n4", "parent": "n2"}),
        deep.nodes[1].model_copy(update={"id": "n5", "parent": "n4"}),
    ]
    errors = validate_plan(deep, TOOLS)
    assert any("层级" in error for error in errors)

    bad_leaf = make_plan()
    bad_leaf.nodes[1].tools = []
    bad_leaf.nodes[2].tools = ["unknown_tool"]
    errors = validate_plan(bad_leaf, TOOLS)
    assert any("至少需要一个数据工具" in error for error in errors)
    assert any("unknown_tool" in error for error in errors)


def test_validate_plan_enforces_node_limit_and_middle_fanout():
    plan = make_plan()
    leaf = plan.nodes[1]
    plan.nodes += [leaf.model_copy(update={"id": f"n{i}"}) for i in (4, 5)]
    assert validate_plan(plan, TOOLS, max_nodes=5) == []
    assert any("超过上限 4" in error for error in validate_plan(plan, TOOLS, max_nodes=4))

    thin_middle = make_plan()
    thin_middle.nodes.append(leaf.model_copy(update={"id": "n4", "parent": "n2"}))
    errors = validate_plan(thin_middle, TOOLS)
    assert any("中间节点 n2 只有 1 个下级" in error for error in errors)


class FakeChat:
    def __init__(self):
        self.ids = itertools.count(1)
        self.reviews = 0
        self.n3_reviewed = False

    async def step(self, messages, *, model, tools=None, reasoning=False):
        system = messages[0]["content"]
        if "执行成员" in system:
            if messages[-1]["role"] == "user" and tools:
                symbol = "sh600519" if "600519" in messages[1]["content"] else "sz000858"
                call = {
                    "id": f"c{next(self.ids)}",
                    "function": {"name": "get_realtime_quote", "arguments": json.dumps({"symbols": [symbol]})},
                }
                return {"role": "assistant", "content": "", "tool_calls": [call]}
            return {"role": "assistant", "content": "## 行情要点\n最新价 100 元（2026-09-23）"}
        if "负责审核" in system:
            self.reviews += 1
            node_id = "n3" if "### n3" in messages[1]["content"] else "n2"
            verdict = {"node_id": node_id, "verdict": "approve"}
            if node_id == "n3" and not self.n3_reviewed:
                self.n3_reviewed = True
                verdict = {"node_id": "n3", "verdict": "revise", "feedback": "补充市值"}
            return {"role": "assistant", "content": json.dumps({"reviews": [verdict]})}
        raise AssertionError(system[:40])

    async def stream_text(self, messages, *, model):
        for chunk in ["## 结论\n", "两者对比……"]:
            yield chunk


async def fake_tool(name, arguments):
    return {
        "status": "success",
        "data": {"symbols": arguments["symbols"]},
        "sources": [{"title": "腾讯行情", "url": "u1"}],
    }


def test_executor_runs_tree_with_revision():
    executor = GraphExecutor(
        plan=make_plan(),
        question="茅台和五粮液谁更好？",
        expert_name="个股分析师",
        llm=FakeChat(),
        leaf_model="flash",
        lead_model="pro",
        tool_specs=SPECS,
        execute_tool=fake_tool,
    )

    async def collect():
        return [event async for event in executor.stream()]

    events = asyncio.run(collect())
    types = [event.type for event in events]
    assert types[0] == "agent_graph"
    assert [e.data["name"] for e in events if e.type == "phase"] == ["research", "review", "writing"]
    assert all(e.data["node_id"] in {"n2", "n3"} for e in events if e.type in {"tool_call", "tool_result"})
    feedback = [e.data for e in events if e.type == "agent_message" and e.data["kind"] == "feedback"]
    assert feedback == [{"id": feedback[0]["id"], "from": "n1", "to": "n3", "kind": "feedback", "summary": "补充市值"}]
    assert executor.states["n3"].attempt == 2
    assert executor.states["n2"].attempt == 1
    assert "".join(e.data["content"] for e in events if e.type == "text") == "## 结论\n两者对比……"
    assert events[-1].type == "refs" and events[-1].data["refs"] == [{"title": "腾讯行情", "url": "u1"}]
    assert executor.states["n1"].status == "done"
    assert executor.llm.reviews == 3


def test_parent_reviews_each_child_as_soon_as_it_submits():
    class SlowN3(FakeChat):
        async def step(self, messages, *, model, tools=None, reasoning=False):
            if "执行成员" in messages[0]["content"] and "000858" in messages[1]["content"]:
                await asyncio.sleep(0.05)
            return await super().step(messages, model=model, tools=tools, reasoning=reasoning)

    executor = GraphExecutor(
        plan=make_plan(),
        question="q",
        expert_name="分析师",
        llm=SlowN3(),
        leaf_model="flash",
        lead_model="pro",
        tool_specs=SPECS,
        execute_tool=fake_tool,
    )

    async def collect():
        return [event async for event in executor.stream()]

    messages = [e.data for e in asyncio.run(collect()) if e.type == "agent_message"]
    order = [(m["from"], m["kind"]) for m in messages if m["kind"] in {"submit", "approve"}]
    assert order.index(("n1", "approve")) < order.index(("n3", "submit"))


def test_executor_marks_failed_leaf_without_crashing():
    class Broken(FakeChat):
        async def step(self, messages, *, model, tools=None, reasoning=False):
            if "执行成员" in messages[0]["content"]:
                raise RuntimeError("upstream down")
            return {"role": "assistant", "content": '{"reviews": []}'}

    executor = GraphExecutor(
        plan=make_plan(),
        question="q",
        expert_name="分析师",
        llm=Broken(),
        leaf_model="flash",
        lead_model="pro",
        tool_specs=SPECS,
        execute_tool=fake_tool,
        max_revisions=0,
    )

    async def collect():
        return [event async for event in executor.stream()]

    events = asyncio.run(collect())
    failed = {e.data["node_id"] for e in events if e.type == "agent_status" and e.data["status"] == "failed"}
    assert failed == {"n2", "n3"}
    assert executor.states["n1"].status == "done"


def test_planner_retries_until_plan_is_valid():
    valid = make_plan().model_dump()
    invalid = {**valid, "nodes": valid["nodes"][:1]}
    replies = iter(
        [
            {"tool_calls": [{"id": "p1", "function": {"name": "search_symbol", "arguments": '{"keyword": "茅台"}'}}]},
            {"tool_calls": [{"id": "p2", "function": {"name": "submit_plan", "arguments": json.dumps(invalid)}}]},
            {"tool_calls": [{"id": "p3", "function": {"name": "submit_plan", "arguments": json.dumps(valid)}}]},
        ]
    )
    seen: list[list[dict]] = []

    class Planner:
        async def step(self, messages, *, model, tools=None, reasoning=False):
            seen.append(list(messages))
            return {"role": "assistant", "content": "", **next(replies)}

    async def run():
        return await generate_plan(
            llm=Planner(),
            model="pro",
            question="对比茅台与五粮液",
            history=[],
            expert_name="个股分析师",
            expert_id="expert_stock_research",
            tool_specs=SPECS,
            execute_tool=fake_tool,
        )

    plan = asyncio.run(run())
    assert [node.id for node in plan.nodes] == ["n1", "n2", "n3"]
    assert "根节点至少需要两个下级任务" in seen[-1][-1]["content"]
