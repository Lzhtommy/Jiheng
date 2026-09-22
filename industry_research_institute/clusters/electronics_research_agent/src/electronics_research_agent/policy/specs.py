from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Optional

from ..config import SliceHint, load_settings
from ..io_util import load_yaml
from ..paths import SPECS_PATH


@dataclass
class PolicyCard:
    spec_id: str
    spec_type: str
    name: str
    l2_code: str
    l2_name: str
    primary_chain: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    forbid_hard: list[str] = field(default_factory=list)
    absolute_models: list[str] = field(default_factory=list)
    rationale: str = ""
    slice_hint: Optional[SliceHint] = None
    sliced: bool = False
    fallback_note: str = ""

    def summary_line(self) -> str:
        primary = " → ".join(self.primary_chain) or "(none)"
        alt = ", ".join(self.alternatives) or "—"
        return f"{self.spec_id} | {self.name} | 主链 {primary} | 备选 {alt}"


def _chain(spec: dict[str, Any]) -> tuple[list[str], list[str]]:
    default = ((spec.get("valuation_chain") or {}).get("default")) or {}
    return list(default.get("primary_chain") or []), list(default.get("alternatives") or [])


def _card(spec: dict[str, Any], sliced: bool = False, hint: Optional[SliceHint] = None, note: str = "") -> PolicyCard:
    chain, alts = _chain(spec)
    meta = spec.get("meta") or {}
    forbid = spec.get("forbid") or {}
    absolute = spec.get("absolute") or {}
    return PolicyCard(
        spec_id=str(spec.get("id") or ""),
        spec_type=str(spec.get("type") or ""),
        name=str(spec.get("name") or ""),
        l2_code=str(spec.get("sw_l2_code") or ""),
        l2_name=str(spec.get("sw_l2_name") or ""),
        primary_chain=chain,
        alternatives=alts,
        forbid_hard=list(forbid.get("metrics_hard") or []),
        absolute_models=list(absolute.get("models") or []),
        rationale=str(meta.get("rationale") or meta.get("notes") or ""),
        slice_hint=hint,
        sliced=sliced,
        fallback_note=note,
    )


@dataclass
class PolicyBook:
    l2: dict[str, dict[str, Any]]
    l3: dict[str, dict[str, Any]]

    def by_id(self, spec_id: str) -> Optional[dict[str, Any]]:
        if spec_id in self.l2:
            return self.l2[spec_id]
        if spec_id in self.l3:
            return self.l3[spec_id]
        return None


@lru_cache(maxsize=1)
def load_policy() -> PolicyBook:
    doc = load_yaml(SPECS_PATH) or {}
    l2 = {str(e["id"]): e for e in (doc.get("l2_specs") or []) if e.get("id")}
    l3 = {str(e["id"]): e for e in (doc.get("l3_specs") or []) if e.get("id")}
    return PolicyBook(l2=l2, l3=l3)


def policy_for(l2_code: str, l3_code: str | None = None) -> PolicyCard:
    settings = load_settings()
    book = load_policy()
    l2_id = f"sw2_{l2_code}"
    l2_spec = book.l2.get(l2_id)
    if not l2_spec:
        return PolicyCard(
            spec_id=l2_id,
            spec_type="L2",
            name="",
            l2_code=l2_code,
            l2_name="",
            fallback_note="无政策卡",
        )
    hint = settings.slice_map.get(str(l3_code or ""))
    if hint and hint.spec_id:
        l3_spec = book.by_id(hint.spec_id)
        if l3_spec:
            return _card(l3_spec, sliced=True, hint=hint)
    note = ""
    if l3_code and str(l3_code) in settings.active_l3 and not hint:
        note = "该三级无独立切片政策，跟随二级默认链。"
    return _card(l2_spec, sliced=False, hint=hint, note=note)
