import asyncio
import json
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field

from app.agent.multi_agent.llm import ChatModel
from app.agent.multi_agent.plan import Plan, PlanNode
from app.agent.multi_agent.prompts import leaf_prompt, reviewer_prompt, summarizer_prompt
from app.agent.runtime import AgentEvent

ToolExecutor = Callable[[str, dict], Awaitable[dict]]

MAX_TOOL_RESULT_CHARS = 6000
PHASES = [("research", "并行调研"), ("review", "审核"), ("writing", "成稿")]


@dataclass
class NodeState:
    node: PlanNode
    is_leaf: bool
    status: str = "pending"
    attempt: int = 0
    messages: list[dict] = field(default_factory=list)
    submission: str = ""
    tool_ok: int = 0


class GraphExecutor:
    def __init__(
        self,
        *,
        plan: Plan,
        question: str,
        expert_name: str,
        llm: ChatModel,
        leaf_model: str,
        lead_model: str,
        tool_specs: dict[str, dict],
        execute_tool: ToolExecutor,
        max_parallel: int = 4,
        time_budget: float = 240,
        max_leaf_rounds: int = 6,
        max_revisions: int = 2,
    ):
        self.plan = plan
        self.question = question
        self.expert_name = expert_name
        self.llm = llm
        self.leaf_model = leaf_model
        self.lead_model = lead_model
        self.tool_specs = tool_specs
        self.execute_tool = execute_tool
        self.sem = asyncio.Semaphore(max_parallel)
        self.time_budget = time_budget
        self.max_leaf_rounds = max_leaf_rounds
        self.max_revisions = max_revisions
        self.states = {node.id: NodeState(node, not plan.children(node.id)) for node in plan.nodes}
        self.refs: dict[str, dict] = {}
        self._queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()
        self._phase_index = -1
        self._message_seq = 0
        self._deadline = 0.0

    async def stream(self) -> AsyncGenerator[AgentEvent, None]:
        self._deadline = time.monotonic() + self.time_budget
        self._emit("agent_graph", self.plan.model_dump())
        task = asyncio.create_task(self._run_node(self.states[self.plan.root().id]))
        task.add_done_callback(lambda _: self._queue.put_nowait(None))
        try:
            while (event := await self._queue.get()) is not None:
                yield event
            await task
        finally:
            if not task.done():
                task.cancel()
        yield AgentEvent("refs", {"refs": list(self.refs.values())})

    async def _run_node(self, state: NodeState) -> None:
        if state.is_leaf:
            await self._run_leaf(state)
            return
        kids = [self.states[child.id] for child in self.plan.children(state.node.id)]
        self._status(state, "waiting")
        for kid in kids:
            self._message(state.node.id, kid.node.id, "assign", kid.node.title)
        await asyncio.gather(*(self._run_node(kid) for kid in kids))
        await self._review(state, kids)
        await self._summarize(state, kids)

    async def _run_leaf(self, state: NodeState, feedback: str | None = None) -> None:
        self._phase("research")
        state.attempt += 1
        self._status(state, "revising" if feedback else "running")
        node = state.node
        if not state.messages:
            state.messages = [
                {"role": "system", "content": leaf_prompt(node.role)},
                {
                    "role": "user",
                    "content": f"用户问题：{self.question}\n研究目标：{self.plan.goal}\n你的任务：{node.title}\n"
                    f"任务说明：{node.instruction}\n完成标准：{node.expected_output or '按任务说明完成'}",
                },
            ]
        if feedback:
            state.messages.append(
                {"role": "user", "content": f"上级审核意见：{feedback}\n请在原任务范围内补充，然后重新提交完整结果。"}
            )
        tools = [self.tool_specs[name] for name in node.tools if name in self.tool_specs]
        try:
            for _ in range(self.max_leaf_rounds):
                if self._late():
                    break
                async with self.sem:
                    message = await self.llm.step(state.messages, model=self.leaf_model, tools=tools or None)
                state.messages.append(message)
                calls = message.get("tool_calls") or []
                if not calls:
                    self._submit(state, message.get("content") or "")
                    return
                state.messages.extend(await asyncio.gather(*(self._call_tool(state, call) for call in calls)))
            state.messages.append({"role": "user", "content": "工具轮次或时间已用尽，请基于已获得的数据立即提交结果。"})
            async with self.sem:
                message = await self.llm.step(state.messages, model=self.leaf_model)
            state.messages.append(message)
            self._submit(state, message.get("content") or "")
        except Exception as exc:
            state.submission = f"执行失败：{exc}"
            self._status(state, "failed")
            self._emit("agent_output", {"node_id": node.id, "output": state.submission, "attempt": state.attempt})
            self._message(node.id, node.parent, "submit", "执行失败")

    async def _call_tool(self, state: NodeState, call: dict) -> dict:
        name = call["function"]["name"]
        arguments = _parse_json(call["function"].get("arguments"))
        event_id = f"{state.node.id}:{call['id']}"
        self._emit("tool_call", {"id": event_id, "name": name, "arguments": arguments, "node_id": state.node.id})
        if name not in state.node.tools:
            result = {"status": "failed", "error": f"工具 {name} 未分配给本任务", "data": {}}
        else:
            try:
                result = await self.execute_tool(name, arguments)
            except Exception as exc:
                result = {"status": "failed", "error": str(exc), "data": {}}
        success = result.get("status") == "success"
        if success:
            state.tool_ok += 1
            for source in result.get("sources") or []:
                if isinstance(source, dict) and source.get("url"):
                    self.refs.setdefault(source["url"], source)
        self._emit(
            "tool_result",
            {
                "id": event_id,
                "name": name,
                "success": success,
                "result": result.get("data", {}),
                "error": result.get("error"),
                "node_id": state.node.id,
            },
        )
        content = json.dumps(result, ensure_ascii=False, default=str)
        if len(content) > MAX_TOOL_RESULT_CHARS:
            content = content[:MAX_TOOL_RESULT_CHARS] + "…（已截断）"
        return {"role": "tool", "tool_call_id": call["id"], "content": content}

    async def _review(self, state: NodeState, kids: list[NodeState]) -> None:
        self._phase("review")
        for round_index in range(self.max_revisions + 1):
            pending = [kid for kid in kids if kid.status not in {"approved", "failed_final"}]
            if not pending:
                return
            self._status(state, "reviewing")
            verdicts = await self._ask_review(state, pending)
            revisions: list[tuple[NodeState, str]] = []
            for kid in pending:
                verdict = verdicts.get(kid.node.id) or {}
                can_revise = round_index < self.max_revisions and not self._late()
                if verdict.get("verdict") == "revise" and can_revise:
                    feedback = str(verdict.get("feedback") or "请补充完整")
                    self._message(state.node.id, kid.node.id, "feedback", feedback)
                    revisions.append((kid, feedback))
                elif kid.status == "failed":
                    kid.status = "failed_final"
                    self._message(state.node.id, kid.node.id, "approve", "执行失败，按数据缺失处理")
                else:
                    self._status(kid, "approved")
                    note = "通过" if verdict.get("verdict") != "revise" else "已达补充上限，按现有结果通过"
                    self._message(state.node.id, kid.node.id, "approve", note)
            if not revisions:
                return
            self._status(state, "waiting")
            await asyncio.gather(*(self._revise(kid, feedback) for kid, feedback in revisions))

    async def _revise(self, state: NodeState, feedback: str) -> None:
        if state.is_leaf:
            await self._run_leaf(state, feedback)
        else:
            kids = [self.states[child.id] for child in self.plan.children(state.node.id)]
            await self._summarize(state, kids, feedback)

    async def _ask_review(self, state: NodeState, pending: list[NodeState]) -> dict[str, dict]:
        parts = []
        for kid in pending:
            note = (
                "\n【系统提示】该节点未成功调用任何数据工具，其中数值不可信。"
                if kid.is_leaf and kid.tool_ok == 0
                else ""
            )
            parts.append(
                f"### {kid.node.id} · {kid.node.title}\n完成标准：{kid.node.expected_output or kid.node.instruction}"
                f"{note}\n提交内容：\n{kid.submission}"
            )
        messages = [
            {"role": "system", "content": reviewer_prompt(state.node.role)},
            {"role": "user", "content": f"研究目标：{self.plan.goal}\n\n" + "\n\n".join(parts)},
        ]
        try:
            async with self.sem:
                message = await self.llm.step(messages, model=self.lead_model)
        except Exception:
            return {}
        return {str(item.get("node_id")): item for item in _parse_reviews(message.get("content") or "")}

    async def _summarize(self, state: NodeState, kids: list[NodeState], feedback: str | None = None) -> None:
        is_root = state.node.parent is None
        if is_root:
            self._phase("writing")
        state.attempt += 1
        self._status(state, "revising" if feedback else "running")
        results = "\n\n".join(f"### {kid.node.title}（{kid.node.role}）\n{kid.submission}" for kid in kids)
        scope = ""
        if is_root and self.plan.excluded:
            scope = "\n本次未覆盖的维度（需在回答中简要说明）：" + "；".join(self.plan.excluded)
        prompt = (
            f"用户问题：{self.question}\n研究目标：{self.plan.goal}\n你的任务：{state.node.title}"
            f"{scope}\n\n团队研究结果：\n{results}"
        )
        if feedback:
            prompt += f"\n\n上级审核意见：{feedback}\n请据此修订汇总。"
        messages = [
            {"role": "system", "content": summarizer_prompt(state.node.role, is_root, self.expert_name)},
            {"role": "user", "content": prompt},
        ]
        if not is_root:
            async with self.sem:
                message = await self.llm.step(messages, model=self.lead_model)
            self._submit(state, message.get("content") or "")
            return
        chunks: list[str] = []
        async with self.sem:
            async for chunk in self.llm.stream_text(messages, model=self.lead_model):
                chunks.append(chunk)
                self._emit("text", {"content": chunk})
        state.submission = "".join(chunks)
        self._status(state, "done")

    def _submit(self, state: NodeState, content: str) -> None:
        state.submission = content
        self._status(state, "submitted")
        self._emit("agent_output", {"node_id": state.node.id, "output": content, "attempt": state.attempt})
        self._message(state.node.id, state.node.parent, "submit", _summary(content))

    def _status(self, state: NodeState, status: str) -> None:
        state.status = status
        self._emit("agent_status", {"node_id": state.node.id, "status": status, "attempt": state.attempt})

    def _message(self, source: str, target: str | None, kind: str, summary: str) -> None:
        self._message_seq += 1
        self._emit(
            "agent_message",
            {"id": self._message_seq, "from": source, "to": target, "kind": kind, "summary": summary[:120]},
        )

    def _phase(self, name: str) -> None:
        index = next(i for i, (key, _) in enumerate(PHASES) if key == name)
        if index > self._phase_index:
            self._phase_index = index
            self._emit("phase", {"name": name, "label": PHASES[index][1]})

    def _late(self) -> bool:
        return time.monotonic() > self._deadline

    def _emit(self, event_type: str, data: dict) -> None:
        self._queue.put_nowait(AgentEvent(event_type, data))


def _summary(content: str) -> str:
    for line in content.splitlines():
        text = line.strip().lstrip("#").strip()
        if text:
            return text[:60]
    return "已提交"


def _parse_json(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _parse_reviews(content: str) -> list[dict]:
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end <= start:
        return []
    try:
        reviews = json.loads(content[start : end + 1]).get("reviews")
    except (json.JSONDecodeError, AttributeError):
        return []
    return [item for item in reviews if isinstance(item, dict)] if isinstance(reviews, list) else []
