from pydantic import BaseModel, Field

MAX_DEPTH = 3
MAX_NODES = 12
MAX_CHILDREN = 4
MIN_MIDDLE_CHILDREN = 3


class PlanNode(BaseModel):
    id: str
    parent: str | None = None
    role: str
    title: str
    instruction: str = ""
    expected_output: str = ""
    tools: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    goal: str
    coverage: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    nodes: list[PlanNode]

    def root(self) -> PlanNode:
        return next(node for node in self.nodes if node.parent is None)

    def children(self, node_id: str) -> list[PlanNode]:
        return [node for node in self.nodes if node.parent == node_id]

    def get(self, node_id: str) -> PlanNode:
        return next(node for node in self.nodes if node.id == node_id)


def validate_plan(plan: Plan, allowed_tools: set[str], max_nodes: int = MAX_NODES) -> list[str]:
    errors: list[str] = []
    ids = [node.id for node in plan.nodes]
    if len(ids) != len(set(ids)):
        errors.append("节点 id 重复")
    limit = min(max_nodes, MAX_NODES)
    if len(ids) > limit:
        errors.append(f"节点数 {len(ids)} 超过上限 {limit}，请合并同类任务")
    roots = [node for node in plan.nodes if node.parent is None]
    if len(roots) != 1:
        return [*errors, f"必须有且只有一个根节点，当前 {len(roots)} 个"]
    known = set(ids)
    for node in plan.nodes:
        if node.parent is not None and node.parent not in known:
            errors.append(f"节点 {node.id} 的上级 {node.parent} 不存在")
    if errors:
        return errors

    depth = {roots[0].id: 1}
    frontier = [roots[0].id]
    while frontier:
        current = frontier.pop()
        kids = plan.children(current)
        if len(kids) > MAX_CHILDREN:
            errors.append(f"节点 {current} 的下级有 {len(kids)} 个，超过上限 {MAX_CHILDREN}")
        for kid in kids:
            depth[kid.id] = depth[current] + 1
            frontier.append(kid.id)
    unreachable = known - depth.keys()
    if unreachable:
        errors.append(f"存在环或孤立节点：{', '.join(sorted(unreachable))}")
    if depth and max(depth.values()) > MAX_DEPTH:
        errors.append(f"层级超过上限 {MAX_DEPTH}")
    if len(plan.children(roots[0].id)) < 2:
        errors.append("根节点至少需要两个下级任务")

    for node in plan.nodes:
        kids = plan.children(node.id)
        if node.parent is not None and kids and len(kids) < MIN_MIDDLE_CHILDREN:
            errors.append(
                f"中间节点 {node.id} 只有 {len(kids)} 个下级，少于 {MIN_MIDDLE_CHILDREN} 个时请把下级直接挂到上一级"
            )
        if not node.title.strip():
            errors.append(f"节点 {node.id} 缺少标题")
        unknown = [tool for tool in node.tools if tool not in allowed_tools]
        if unknown:
            errors.append(f"节点 {node.id} 使用了不可用的工具：{', '.join(unknown)}")
        if not plan.children(node.id):
            if not node.instruction.strip():
                errors.append(f"执行节点 {node.id} 缺少任务说明")
            if not node.tools:
                errors.append(f"执行节点 {node.id} 至少需要一个数据工具")
    return errors
