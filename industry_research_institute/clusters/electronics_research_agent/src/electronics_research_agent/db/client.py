from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from ..io_util import load_dotenv, load_yaml
from ..paths import DB_CONFIG_PATH, ENV_PATH


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    user: str
    database: str
    password: str
    connect_timeout: int = 8

    def dsn_public(self) -> str:
        return f"{self.user}@{self.host}:{self.port}/{self.database}"

    def has_password(self) -> bool:
        return bool(self.password)


def load_db_config() -> DbConfig:
    load_dotenv(ENV_PATH)
    raw = load_yaml(DB_CONFIG_PATH) or {}
    return DbConfig(
        host=os.environ.get("VR_PG_HOST") or str(raw.get("host") or "127.0.0.1"),
        port=int(os.environ.get("VR_PG_PORT") or raw.get("port") or 5432),
        user=os.environ.get("VR_PG_USER") or str(raw.get("user") or "postgres"),
        database=os.environ.get("VR_PG_DATABASE") or str(raw.get("database") or "postgres"),
        password=os.environ.get("VR_PG_PASSWORD") or "",
        connect_timeout=int(raw.get("connect_timeout") or 8),
    )


def connect(cfg: Optional[DbConfig] = None):
    cfg = cfg or load_db_config()
    if not cfg.has_password():
        raise RuntimeError(
            "VR_PG_PASSWORD is not set. Copy .env.example to .env or pass --no-db."
        )
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as exc:
        raise RuntimeError("psycopg2 is required for database access") from exc
    conn = psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        connect_timeout=cfg.connect_timeout,
    )
    return conn


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    try:
        from decimal import Decimal

        if isinstance(value, Decimal):
            return float(value)
    except Exception:
        pass
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value
