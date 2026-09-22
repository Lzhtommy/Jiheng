from __future__ import annotations

from pathlib import Path


# src/electronics_research_agent/paths.py → package folder root
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PACKAGE_ROOT / "src"
DATA_DIR = PACKAGE_ROOT / "data"
CONFIG_DIR = PACKAGE_ROOT / "config"
RUNS_DIR = PACKAGE_ROOT / "runs"
PLAYBOOKS_DIR = CONFIG_DIR / "playbooks"
SW_DIR = DATA_DIR / "sw2021"
SPECS_PATH = DATA_DIR / "specs" / "electronics_specs.yaml"
UNIVERSE_PATH = DATA_DIR / "universe" / "valuation_inputs_v1.yaml"
SETTINGS_PATH = CONFIG_DIR / "settings.yaml"
DB_CONFIG_PATH = CONFIG_DIR / "db.yaml"
ENV_PATH = PACKAGE_ROOT / ".env"


def require_layout() -> None:
    missing = [p for p in (DATA_DIR, CONFIG_DIR, SW_DIR, SPECS_PATH, UNIVERSE_PATH) if not p.exists()]
    if missing:
        names = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(
            f"electronics_research_agent layout incomplete, missing: {names}. "
            "Run from this package folder (or pip install -e .)."
        )
