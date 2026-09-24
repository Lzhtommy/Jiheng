from __future__ import annotations

from typing import Optional

from ..agents.roles import OrgChart
from ..artifacts.schema import CompanyCard, L1Brief, L2Review, L3Note
from ..db.queries import StockBundle
from ..policy.specs import policy_for
from ..taxonomy.universe import UniverseStock


def _card(stock: UniverseStock, bundle: Optional[StockBundle], policy_line: str, spec_id: str) -> CompanyCard:
    summary = bundle.summary if bundle else None
    return CompanyCard(
        stock_code=stock.stock_code,
        stock_name=stock.stock_name,
        class_name=stock.class_name,
        l1_code=stock.l1_code,
        l1_name=stock.l1_name,
        l2_code=stock.l2_code,
        l2_name=stock.l2_name,
        l3_code=stock.l3_code,
        l3_name=stock.l3_name,
        class_sw_note=stock.class_sw_note,
        policy_spec_id=spec_id,
        policy_line=policy_line,
        value_per_share=(summary or {}).get("value_per_share") if summary else None,
        close_price=(summary or {}).get("close_price") if summary else None,
        bias_ratio=(summary or {}).get("bias_ratio") if summary else None,
        trade_date=(summary or {}).get("trade_date") if summary else None,
        remark=(summary or {}).get("remark") or "" if summary else "",
        input_scenarios=list(bundle.inputs) if bundle else [],
        finance=bundle.finance if bundle else None,
        industry_sw=bundle.industry_sw if bundle else None,
        narrative="待撰写（llm.enabled=false）",
    )


def _l3_synth(note: L3Note) -> str:
    names = "、".join(f"{c.stock_code} {c.stock_name}" for c in note.companies) or "无"
    lines = [
        f"{note.l3_name}（{note.l3_code}）v1 覆盖 {len(note.companies)} 只：{names}。",
        f"估值政策：{note.policy_line}",
    ]
    if note.policy_line and "跟随二级" in (note.companies[0].policy_line if note.companies else ""):
        lines.append("本三级尚无独立切片，指标跟随二级默认链。")
    notes = [c.class_sw_note for c in note.companies if c.class_sw_note]
    if notes:
        lines.append("分类差异：" + "；".join(sorted(set(notes))))
    lines.append("叙事待撰写（llm.enabled=false）。")
    return "\n".join(lines)


def _l2_synth(review: L2Review) -> str:
    active_children = [c for c in review.child_l3 if c.get("n_companies")]
    lines = [
        f"{review.l2_name}（{review.l2_code}）活跃下属三级 {len(active_children)} 个，政策：{review.policy_line}。",
    ]
    for ch in active_children:
        lines.append(f"- {ch['l3_name']} ({ch['l3_code']}): {ch['n_companies']} 只")
    if not review.active:
        lines.append("本主管为 stub，不产出投资结论。")
    lines.append("叙事待撰写（llm.enabled=false）。")
    return "\n".join(lines)


def _l1_synth(brief: L1Brief) -> str:
    active = [c for c in brief.child_l2 if c.get("active")]
    lines = [
        f"{brief.l1_name} v1 活跃二级主管 {len(active)} 个。",
    ]
    for ch in brief.child_l2:
        flag = "活跃" if ch.get("active") else "stub"
        lines.append(f"- {ch['l2_name']} ({ch['l2_code']}) [{flag}] {ch['n_companies']} 只")
    lines.append("叙事待撰写（llm.enabled=false）。")
    return "\n".join(lines)


def build_l3_note(
    l3_code: str,
    org: OrgChart,
    stocks: list[UniverseStock],
    bundles: dict[str, StockBundle],
) -> L3Note:
    role = org.researcher(l3_code)
    if role is None:
        raise KeyError(l3_code)
    policy = policy_for(role.parent_code, l3_code)
    line = policy.summary_line()
    if policy.fallback_note:
        line = f"{line} | {policy.fallback_note}"
    companies = [_card(s, bundles.get(s.stock_code), line, policy.spec_id) for s in stocks]
    note = L3Note(
        l3_code=l3_code,
        l3_name=role.name,
        l2_code=role.parent_code,
        l2_name=role.parent_name,
        active=role.active,
        policy_spec_id=policy.spec_id,
        policy_line=line,
        playbook_file=role.playbook_file,
        companies=companies,
    )
    note.synthesis = _l3_synth(note)
    return note


def build_l2_review(l2_code: str, org: OrgChart, l3_notes: list[L3Note]) -> L2Review:
    role = org.supervisor(l2_code)
    if role is None:
        raise KeyError(l2_code)
    policy = policy_for(l2_code, None)
    children = []
    by_code = {n.l3_code: n for n in l3_notes}
    for code in role.child_codes:
        note = by_code.get(code)
        l3_role = org.researcher(code)
        children.append(
            {
                "l3_code": code,
                "l3_name": l3_role.name if l3_role else "",
                "active": bool(l3_role and l3_role.active),
                "n_companies": len(note.companies) if note else 0,
                "policy_spec_id": note.policy_spec_id if note else "",
                "synthesis": note.synthesis if note else "",
            }
        )
    review = L2Review(
        l2_code=l2_code,
        l2_name=role.name,
        active=role.active,
        policy_spec_id=policy.spec_id,
        policy_line=policy.summary_line(),
        playbook_file=role.playbook_file,
        child_l3=children,
    )
    review.synthesis = _l2_synth(review)
    return review


def build_l1_brief(org: OrgChart, reviews: list[L2Review]) -> L1Brief:
    by_code = {r.l2_code: r for r in reviews}
    children = []
    for code in org.chief.child_codes:
        review = by_code.get(code)
        role = org.supervisor(code)
        n = 0
        if review:
            n = sum(int(ch.get("n_companies") or 0) for ch in review.child_l3)
        children.append(
            {
                "l2_code": code,
                "l2_name": role.name if role else "",
                "active": bool(role and role.active),
                "n_companies": n,
                "synthesis": review.synthesis if review else "",
            }
        )
    brief = L1Brief(
        l1_code=org.chief.code,
        l1_name=org.chief.name,
        playbook_file=org.chief.playbook_file,
        child_l2=children,
    )
    brief.synthesis = _l1_synth(brief)
    return brief
