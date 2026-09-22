from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import CompanyCard, L1Brief, L2Review, L3Note, RunManifest


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    line = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join([line, sep, body]) if rows else line + "\n" + sep + "\n| （无） |"


def render_company(card: CompanyCard) -> str:
    rows = [
        ["申万", f"{card.l1_name} / {card.l2_name} / {card.l3_name}"],
        ["class_name", card.class_name or "—"],
        ["分类差异", card.class_sw_note or "无"],
        ["政策", card.policy_line or "—"],
        ["内在价值/股", _fmt(card.value_per_share)],
        ["收盘价", _fmt(card.close_price)],
        ["溢价率", _fmt(card.bias_ratio)],
        ["交易日", _fmt(card.trade_date)],
        ["备注", card.remark or "—"],
        ["情景数", str(len(card.input_scenarios))],
    ]
    parts = [
        f"### {card.stock_code} {card.stock_name}",
        "",
        _md_table(["字段", "值"], rows),
        "",
        card.narrative,
    ]
    return "\n".join(parts)


def render_l3(note: L3Note) -> str:
    status = "活跃" if note.active else "stub"
    stock_rows = [
        [
            c.stock_code,
            c.stock_name,
            c.class_name or "—",
            _fmt(c.value_per_share),
            _fmt(c.close_price),
            _fmt(c.bias_ratio),
        ]
        for c in note.companies
    ]
    blocks = [
        f"# L3 研究员笔记：{note.l3_name} ({note.l3_code})",
        "",
        f"- 状态：{status}",
        f"- 上级主管：{note.l2_name} ({note.l2_code})",
        f"- 政策：{note.policy_line}",
        f"- playbook：`{note.playbook_file}`",
        "",
        "## 成分股（v1 宇宙）",
        "",
        _md_table(["代码", "名称", "class_name", "内在价值", "现价", "溢价率"], stock_rows),
        "",
        "## 个股卡",
        "",
    ]
    if note.companies:
        blocks.append("\n\n".join(render_company(c) for c in note.companies))
    else:
        blocks.append("（本三级在 v1 宇宙中无股票）")
    blocks.extend(["", "## 综述", "", note.synthesis, ""])
    return "\n".join(blocks)


def render_l2(review: L2Review) -> str:
    status = "活跃" if review.active else "stub"
    rows = [
        [
            str(ch.get("l3_code") or ""),
            str(ch.get("l3_name") or ""),
            str(ch.get("n_companies") or 0),
            str(ch.get("policy_spec_id") or ""),
        ]
        for ch in review.child_l3
    ]
    return "\n".join(
        [
            f"# L2 主管综述：{review.l2_name} ({review.l2_code})",
            "",
            f"- 状态：{status}",
            f"- 政策：{review.policy_line}",
            f"- playbook：`{review.playbook_file}`",
            "",
            "## 下属三级",
            "",
            _md_table(["L3 代码", "名称", "v1 股票数", "政策 id"], rows),
            "",
            "## 综述",
            "",
            review.synthesis,
            "",
            "> 主管只审下属 L3 综述与政策，不改个股数字。",
            "",
        ]
    )


def render_l1(brief: L1Brief) -> str:
    rows = [
        [
            str(ch.get("l2_code") or ""),
            str(ch.get("l2_name") or ""),
            "活跃" if ch.get("active") else "stub",
            str(ch.get("n_companies") or 0),
        ]
        for ch in brief.child_l2
    ]
    return "\n".join(
        [
            f"# L1 首席简报：{brief.l1_name} ({brief.l1_code})",
            "",
            f"- playbook：`{brief.playbook_file}`",
            "",
            "## 二级主管",
            "",
            _md_table(["L2 代码", "名称", "状态", "v1 股票数"], rows),
            "",
            "## 简报",
            "",
            brief.synthesis,
            "",
            "> 首席只读主管综述，不直接改个股卡。",
            "",
        ]
    )


def write_run(
    out_dir: Path,
    notes: list[L3Note],
    reviews: list[L2Review],
    brief: L1Brief,
    manifest: RunManifest,
) -> None:
    for note in notes:
        folder = out_dir / "l3" / note.l3_code
        _write(folder / "note.md", render_l3(note))
        _json(folder / "note.json", note.to_dict())
    for review in reviews:
        folder = out_dir / "l2" / review.l2_code
        _write(folder / "review.md", render_l2(review))
        _json(folder / "review.json", review.to_dict())
    _write(out_dir / "l1" / "brief.md", render_l1(brief))
    _json(out_dir / "l1" / "brief.json", brief.to_dict())
    _json(out_dir / "manifest.json", manifest.to_dict())
