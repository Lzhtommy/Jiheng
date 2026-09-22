# -*- coding: utf-8 -*-
"""Postgres connection settings. Password only from VR_PG_PASSWORD or .env."""
from __future__ import annotations

import os
from pathlib import Path

_INSTITUTE_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _INSTITUTE_ROOT / ".env"


def _load_dotenv() -> None:
    if not _ENV_PATH.is_file():
        return
    for raw in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def db_config() -> dict:
    _load_dotenv()
    password = os.environ.get("VR_PG_PASSWORD") or ""
    if not password:
        raise RuntimeError(
            "VR_PG_PASSWORD is not set. Copy industry_research_institute/.env.example to .env."
        )
    return {
        "host": os.environ.get("VR_PG_HOST", ""),
        "port": int(os.environ.get("VR_PG_PORT", "5432")),
        "user": os.environ.get("VR_PG_USER", "postgres"),
        "password": password,
        "database": os.environ.get("VR_PG_DATABASE", ""),
    }
