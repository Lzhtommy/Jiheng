from __future__ import annotations

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    id: str
    label: str
    source_type: str
    locator: str
    excerpt: str
    derived: bool = False


class ScreenRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)


class ScreenResult(BaseModel):
    code: str
    name: str
    industry: str
    price: float
    change_1d: float
    pe_ttm: float
    roe: float
    profit_growth: float
    dividend_yield: float
    cashflow_positive_3y: bool
    match_score: int
    match_reason: list[str]
    evidence: list[Evidence]


class ScreenResponse(BaseModel):
    query: str
    interpreted: dict[str, object]
    results: list[ScreenResult]
    data_notice: str
