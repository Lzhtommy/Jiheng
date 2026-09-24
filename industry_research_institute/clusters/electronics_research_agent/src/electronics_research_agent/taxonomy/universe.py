from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from ..io_util import load_yaml
from ..paths import UNIVERSE_PATH
from .codes import normalize_code


@dataclass(frozen=True)
class UniverseStock:
    stock_code: str
    stock_name: str
    class_name: str
    l1_code: str
    l1_name: str
    l2_code: str
    l2_name: str
    l3_code: str
    l3_name: str
    class_sw_note: str = ""


@lru_cache(maxsize=1)
def load_universe() -> list[UniverseStock]:
    doc = load_yaml(UNIVERSE_PATH) or {}
    l1_code = str(doc.get("l1_code") or "270000")
    l1_name = str(doc.get("l1_name") or "电子")
    rows: list[UniverseStock] = []
    for raw in doc.get("stocks") or []:
        rows.append(
            UniverseStock(
                stock_code=normalize_code(str(raw["stock_code"])),
                stock_name=str(raw.get("stock_name") or ""),
                class_name=str(raw.get("class_name") or ""),
                l1_code=l1_code,
                l1_name=l1_name,
                l2_code=str(raw.get("l2_code") or ""),
                l2_name=str(raw.get("l2_name") or ""),
                l3_code=str(raw.get("l3_code") or ""),
                l3_name=str(raw.get("l3_name") or ""),
                class_sw_note=str(raw.get("class_sw_note") or ""),
            )
        )
    return rows


def universe_by_code() -> dict[str, UniverseStock]:
    return {s.stock_code: s for s in load_universe()}


def stocks_for_l3(l3_code: str) -> list[UniverseStock]:
    return [s for s in load_universe() if s.l3_code == l3_code]


def stocks_for_l2(l2_code: str) -> list[UniverseStock]:
    return [s for s in load_universe() if s.l2_code == l2_code]


def get_universe_stock(code: str) -> Optional[UniverseStock]:
    return universe_by_code().get(normalize_code(code))
