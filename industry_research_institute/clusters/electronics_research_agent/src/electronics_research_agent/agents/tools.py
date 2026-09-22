"""Tools the orchestrator (and a future LLM runtime) may call.

Researchers only see their L3 universe. Supervisors only see child L3.
The chief only sees L2 reviews — not raw company cards.
"""
from __future__ import annotations

from typing import Any

from ..policy.specs import policy_for
from ..taxonomy.map_stock import map_stock
from ..taxonomy.universe import stocks_for_l2, stocks_for_l3


def tool_map_stock(code: str) -> dict[str, Any]:
    return map_stock(code).to_dict()


def tool_policy(l2_code: str, l3_code: str | None = None) -> dict[str, Any]:
    card = policy_for(l2_code, l3_code)
    return {
        "spec_id": card.spec_id,
        "spec_type": card.spec_type,
        "name": card.name,
        "primary_chain": card.primary_chain,
        "alternatives": card.alternatives,
        "forbid_hard": card.forbid_hard,
        "absolute_models": card.absolute_models,
        "rationale": card.rationale,
        "sliced": card.sliced,
        "fallback_note": card.fallback_note,
    }


def tool_l3_universe(l3_code: str) -> list[dict[str, str]]:
    return [
        {
            "stock_code": s.stock_code,
            "stock_name": s.stock_name,
            "class_name": s.class_name,
            "class_sw_note": s.class_sw_note,
        }
        for s in stocks_for_l3(l3_code)
    ]


def tool_l2_universe(l2_code: str) -> list[dict[str, str]]:
    return [
        {
            "stock_code": s.stock_code,
            "stock_name": s.stock_name,
            "l3_code": s.l3_code,
            "l3_name": s.l3_name,
        }
        for s in stocks_for_l2(l2_code)
    ]
