from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from ..io_util import load_yaml
from ..paths import SW_DIR
from .codes import normalize_code


@dataclass(frozen=True)
class IndustryNode:
    code: str
    name: str
    spec_id: str = ""
    index_code: str = ""
    l1_code: str = ""
    l1_name: str = ""
    l2_code: str = ""
    l2_name: str = ""
    aliases: tuple[str, ...] = ()
    members_hint: str = ""
    is_pub: str = ""


@dataclass
class MemberRow:
    stock_code: str
    ts_code: str
    stock_name: str
    l1_code: str
    l1_name: str
    l2_code: str
    l2_name: str
    l3_code: str
    l3_name: str
    include_date: str = ""


@dataclass
class Taxonomy:
    l1: dict[str, IndustryNode] = field(default_factory=dict)
    l2: dict[str, IndustryNode] = field(default_factory=dict)
    l3: dict[str, IndustryNode] = field(default_factory=dict)
    members: dict[str, MemberRow] = field(default_factory=dict)
    l2_by_name: dict[str, str] = field(default_factory=dict)
    l3_by_name: dict[str, str] = field(default_factory=dict)

    def children_l2(self, l1_code: str = "270000") -> list[IndustryNode]:
        return [n for n in self.l2.values() if n.l1_code == l1_code]

    def children_l3(self, l2_code: str) -> list[IndustryNode]:
        return [n for n in self.l3.values() if n.l2_code == l2_code]

    def parent_l2(self, l3_code: str) -> Optional[IndustryNode]:
        node = self.l3.get(l3_code)
        if not node:
            return None
        return self.l2.get(node.l2_code)


def _nodes(path_name: str, level: str) -> dict[str, IndustryNode]:
    doc = load_yaml(SW_DIR / path_name) or {}
    out: dict[str, IndustryNode] = {}
    for row in doc.get("industries") or []:
        code = str(row["code"])
        out[code] = IndustryNode(
            code=code,
            name=str(row.get("name") or ""),
            spec_id=str(row.get("spec_id") or ""),
            index_code=str(row.get("index_code") or ""),
            l1_code=str(row.get("l1_code") or ("270000" if level == "L1" else "")),
            l1_name=str(row.get("l1_name") or ("电子" if level == "L1" else "")),
            l2_code=str(row.get("l2_code") or (code if level == "L2" else "")),
            l2_name=str(row.get("l2_name") or (row.get("name") if level == "L2" else "")),
            aliases=tuple(row.get("aliases") or []),
            members_hint=str(row.get("members") or ""),
            is_pub=str(row.get("is_pub") or ""),
        )
    return out


def _load_members() -> dict[str, MemberRow]:
    path = SW_DIR / "members_electronics.csv"
    out: dict[str, MemberRow] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            ts = (row.get("ts_code") or row.get("股票代码") or "").strip()
            bare = normalize_code(ts)
            if not bare:
                continue
            out[bare] = MemberRow(
                stock_code=bare,
                ts_code=ts,
                stock_name=str(row.get("股票简称") or ""),
                l1_code=str(row.get("l1_code") or ""),
                l1_name=str(row.get("l1_name") or ""),
                l2_code=str(row.get("l2_code") or ""),
                l2_name=str(row.get("l2_name") or ""),
                l3_code=str(row.get("l3_industry_code") or ""),
                l3_name=str(row.get("l3_name") or row.get("申万3级") or ""),
                include_date=str(row.get("纳入时间") or ""),
            )
    return out


@lru_cache(maxsize=1)
def load_taxonomy() -> Taxonomy:
    l1 = _nodes("l1_electronics.yaml", "L1")
    l2 = _nodes("l2_electronics.yaml", "L2")
    l3 = _nodes("l3_electronics.yaml", "L3")
    tax = Taxonomy(l1=l1, l2=l2, l3=l3, members=_load_members())
    for node in l2.values():
        tax.l2_by_name[node.name] = node.code
        for alias in node.aliases:
            tax.l2_by_name[alias] = node.code
    for node in l3.values():
        tax.l3_by_name[node.name] = node.code
    return tax
