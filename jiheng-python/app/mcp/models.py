from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    tag: str
    date: str = ""
    url: str = ""
    provider: str
    retrieved_at: str


class DataResult(BaseModel):
    status: str = "success"
    provider: str
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())  # noqa: UP017
    data: Any
    sources: list[Source] = Field(default_factory=list)
    error: str | None = None

    @classmethod
    def failure(cls, provider: str, error: str) -> "DataResult":
        return cls(status="failed", provider=provider, data={}, error=error)
