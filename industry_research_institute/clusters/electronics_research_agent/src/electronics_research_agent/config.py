from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .io_util import load_dotenv, load_yaml
from .paths import ENV_PATH, SETTINGS_PATH, require_layout


@dataclass(frozen=True)
class SliceHint:
    tag: str
    value: str
    spec_id: str


@dataclass(frozen=True)
class Settings:
    version: str
    l1_code: str
    l1_name: str
    llm_enabled: bool
    active_l2: frozenset[str]
    active_l3: frozenset[str]
    slice_map: dict[str, SliceHint]
    playbooks: dict[str, Any] = field(default_factory=dict)


def load_settings() -> Settings:
    require_layout()
    load_dotenv(ENV_PATH)
    raw = load_yaml(SETTINGS_PATH) or {}
    slice_map = {}
    for code, item in (raw.get("slice_map") or {}).items():
        slice_map[str(code)] = SliceHint(
            tag=str(item["tag"]),
            value=str(item["value"]),
            spec_id=str(item.get("spec_id") or ""),
        )
    active = raw.get("active") or {}
    return Settings(
        version=str(raw.get("version") or "0.1.0"),
        l1_code=str(raw.get("l1_code") or "270000"),
        l1_name=str(raw.get("l1_name") or "电子"),
        llm_enabled=bool((raw.get("llm") or {}).get("enabled", False)),
        active_l2=frozenset(str(x) for x in (active.get("l2") or [])),
        active_l3=frozenset(str(x) for x in (active.get("l3") or [])),
        slice_map=slice_map,
        playbooks=raw.get("playbooks") or {},
    )
