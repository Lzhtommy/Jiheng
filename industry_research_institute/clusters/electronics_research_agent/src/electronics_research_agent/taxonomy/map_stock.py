from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

from .codes import normalize_code
from .sw import Taxonomy, load_taxonomy
from .universe import UniverseStock, get_universe_stock

__all__ = ["IndustryHit", "map_stock", "normalize_code"]


@dataclass(frozen=True)
class IndustryHit:
    stock_code: str
    stock_name: str
    l1_code: str
    l1_name: str
    l2_code: str
    l2_name: str
    l3_code: str
    l3_name: str
    source: str
    class_name: str = ""
    class_sw_note: str = ""
    found: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _from_universe(row: UniverseStock) -> IndustryHit:
    return IndustryHit(
        stock_code=row.stock_code,
        stock_name=row.stock_name,
        l1_code=row.l1_code,
        l1_name=row.l1_name,
        l2_code=row.l2_code,
        l2_name=row.l2_name,
        l3_code=row.l3_code,
        l3_name=row.l3_name,
        source="universe_v1",
        class_name=row.class_name,
        class_sw_note=row.class_sw_note,
    )


def map_stock(code: str, taxonomy: Optional[Taxonomy] = None) -> IndustryHit:
    """Map a stock code to Shenwan L1/L2/L3.

    Prefers the frozen v1 universe; falls back to the electronics member table.
    """
    bare = normalize_code(code)
    uni = get_universe_stock(bare)
    if uni:
        return _from_universe(uni)
    tax = taxonomy or load_taxonomy()
    member = tax.members.get(bare)
    if member:
        return IndustryHit(
            stock_code=bare,
            stock_name=member.stock_name,
            l1_code=member.l1_code,
            l1_name=member.l1_name,
            l2_code=member.l2_code,
            l2_name=member.l2_name,
            l3_code=member.l3_code,
            l3_name=member.l3_name,
            source="members_csv",
        )
    return IndustryHit(
        stock_code=bare,
        stock_name="",
        l1_code="",
        l1_name="",
        l2_code="",
        l2_name="",
        l3_code="",
        l3_name="",
        source="miss",
        found=False,
    )
