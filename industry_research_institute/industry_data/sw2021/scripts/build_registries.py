# -*- coding: utf-8 -*-
"""Build SW2021 L1/L2/L3 registries from the official classification table.

Baseline root: industry_data/sw2021/
Source: source/sw2021_index_classify.md

Usage (repo root):
  python industry_data/sw2021/scripts/build_registries.py
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "source" / "sw2021_index_classify.md"
OUT = ROOT / "registries"


def parse_table(text: str) -> tuple[list[dict], list[dict], list[dict]]:
    l1, l2, l3 = [], [], []
    for line in text.splitlines():
        if "|" not in line or "行业代码" in line or line.startswith("----"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 6:
            continue
        code, index_code, a, b, c, kind = parts[:6]
        if not re.fullmatch(r"\d{6}", code):
            continue
        is_pub = parts[6] if len(parts) > 6 else ""
        members = parts[8] if len(parts) > 8 else ""
        if kind == "一级行业":
            l1.append(
                {
                    "code": code,
                    "index_code": index_code,
                    "name": a,
                    "is_pub": is_pub,
                    "members": members,
                }
            )
        elif kind == "二级行业":
            l2.append(
                {
                    "code": code,
                    "index_code": index_code,
                    "l1_name": a,
                    "name": b,
                    "is_pub": is_pub,
                    "members": members,
                }
            )
        elif kind == "三级行业":
            l3.append(
                {
                    "code": code,
                    "index_code": index_code,
                    "l1_name": a,
                    "l2_name": b,
                    "name": c,
                    "is_pub": is_pub,
                    "members": members,
                }
            )
    l1_by_name = {r["name"]: r["code"] for r in l1}
    l2_by_name = {r["name"]: r["code"] for r in l2}
    for r in l2:
        r["l1_code"] = l1_by_name.get(r["l1_name"])
    for r in l3:
        r["l1_code"] = l1_by_name.get(r["l1_name"])
        r["l2_code"] = l2_by_name.get(r["l2_name"])
    return l1, l2, l3


def aliases_for_l2(name: str) -> list[str]:
    out: list[str] = []
    stripped = name.replace("Ⅱ", "").replace("Ⅲ", "").strip()
    if stripped and stripped != name:
        out.append(stripped)
    extras = {
        "白酒Ⅱ": ["白酒"],
        "证券Ⅱ": ["证券"],
        "保险Ⅱ": ["保险"],
        "中药Ⅱ": ["中药"],
        "IT服务Ⅱ": ["IT服务", "it服务"],
        "游戏Ⅱ": ["游戏"],
        "综合Ⅱ": ["综合"],
        "贸易Ⅱ": ["贸易"],
    }
    out.extend(extras.get(name, []))
    seen: set[str] = set()
    uniq: list[str] = []
    for a in out:
        if a not in seen and a != name:
            seen.add(a)
            uniq.append(a)
    return uniq


def q(v: object) -> str:
    if v is None:
        return "null"
    return f"\"{v}\""


def write_items(path: Path, header: list[str], rows: list[dict], fields: list[str]) -> None:
    lines = list(header) + ["industries:"]
    for r in rows:
        first = True
        for f in fields:
            if f == "aliases":
                continue
            prefix = "  - " if first else "    "
            lines.append(f"{prefix}{f}: {q(r.get(f))}")
            first = False
        if "aliases" in fields:
            al = r.get("aliases") or []
            if not al:
                lines.append("    aliases: []")
            else:
                lines.append("    aliases:")
                for item in al:
                    lines.append(f"      - {q(item)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    l1, l2, l3 = parse_table(text)
    if len(l1) != 31 or len(l2) != 134 or len(l3) != 346:
        raise SystemExit(f"unexpected counts L1={len(l1)} L2={len(l2)} L3={len(l3)}")

    for r in l1:
        r["spec_id"] = f"sw1_{r['code']}"
    for r in l2:
        r["aliases"] = aliases_for_l2(r["name"])
        r["spec_id"] = f"sw2_{r['code']}"
    for r in l3:
        r["spec_id"] = f"sw3_{r['code']}"

    OUT.mkdir(parents=True, exist_ok=True)
    common = [
        "# AUTO-GENERATED. Do not edit by hand.",
        "# Baseline: industry_data/sw2021",
        "# Rebuild: python industry_data/sw2021/scripts/build_registries.py",
        "# Source: source/sw2021_index_classify.md",
        "version: SW2021",
    ]

    write_items(
        OUT / "l1.yaml",
        common + ["level: L1", f"count: {len(l1)}"],
        l1,
        ["code", "index_code", "name", "spec_id", "is_pub", "members"],
    )
    write_items(
        OUT / "l2.yaml",
        common + ["level: L2", f"count: {len(l2)}"],
        l2,
        [
            "code",
            "index_code",
            "l1_code",
            "l1_name",
            "name",
            "spec_id",
            "is_pub",
            "members",
            "aliases",
        ],
    )
    write_items(
        OUT / "l3.yaml",
        common + ["level: L3", f"count: {len(l3)}"],
        l3,
        [
            "code",
            "index_code",
            "l1_code",
            "l1_name",
            "l2_code",
            "l2_name",
            "name",
            "spec_id",
            "is_pub",
            "members",
        ],
    )

    lookup = [
        "# AUTO-GENERATED name lookup for THS industry_l1 / industry_l2",
        "version: SW2021",
        "l1_by_name:",
    ]
    for r in sorted(l1, key=lambda x: x["name"]):
        lookup.append(f"  {q(r['name'])}: {q(r['code'])}")
    lookup.append("l2_by_name:")
    seen: set[str] = set()
    for r in sorted(l2, key=lambda x: x["name"]):
        lookup.append(f"  {q(r['name'])}: {q(r['code'])}")
        seen.add(r["name"])
        for a in r["aliases"]:
            if a not in seen:
                lookup.append(f"  {q(a)}: {q(r['code'])}")
                seen.add(a)
    (OUT / "name_to_code.yaml").write_text("\n".join(lookup) + "\n", encoding="utf-8")

    print(f"L1={len(l1)} L2={len(l2)} L3={len(l3)}")
    print(f"wrote under {OUT}")


if __name__ == "__main__":
    main()
