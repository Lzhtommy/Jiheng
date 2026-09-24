from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _asdict(obj: Any) -> dict[str, Any]:
    return asdict(obj)


@dataclass
class CompanyCard:
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
    policy_spec_id: str = ""
    policy_line: str = ""
    value_per_share: Any = None
    close_price: Any = None
    bias_ratio: Any = None
    trade_date: Any = None
    remark: str = ""
    input_scenarios: list[dict[str, Any]] = field(default_factory=list)
    finance: dict[str, Any] | None = None
    industry_sw: dict[str, Any] | None = None
    narrative: str = "待撰写"

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class L3Note:
    l3_code: str
    l3_name: str
    l2_code: str
    l2_name: str
    active: bool
    policy_spec_id: str
    policy_line: str
    playbook_file: str
    companies: list[CompanyCard] = field(default_factory=list)
    synthesis: str = "待撰写"

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class L2Review:
    l2_code: str
    l2_name: str
    active: bool
    policy_spec_id: str
    policy_line: str
    playbook_file: str
    child_l3: list[dict[str, Any]] = field(default_factory=list)
    synthesis: str = "待撰写"

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class L1Brief:
    l1_code: str
    l1_name: str
    playbook_file: str
    child_l2: list[dict[str, Any]] = field(default_factory=list)
    synthesis: str = "待撰写"

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class RunManifest:
    as_of: str
    version: str
    db_used: bool
    llm_enabled: bool
    universe_size: int
    out_dir: str
    l3_written: list[str] = field(default_factory=list)
    l2_written: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)
