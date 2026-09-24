from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .client import connect, json_safe, load_db_config


def _rows(cur, sql: str, params: tuple) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    out = []
    for raw in cur.fetchall():
        out.append({k: json_safe(v) for k, v in dict(raw).items()})
    return out


@dataclass
class StockBundle:
    stock_code: str
    inputs: list[dict[str, Any]] = field(default_factory=list)
    summary: Optional[dict[str, Any]] = None
    industry_sw: Optional[dict[str, Any]] = None
    finance: Optional[dict[str, Any]] = None


def fetch_stock_bundle(codes: list[str], use_db: bool = True) -> dict[str, StockBundle]:
    bundles = {c: StockBundle(stock_code=c) for c in codes}
    if not use_db or not codes:
        return bundles
    cfg = load_db_config()
    if not cfg.has_password():
        return bundles
    try:
        import psycopg2.extras
    except ImportError:
        return bundles

    conn = connect(cfg)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        params = (codes,)
        for row in _rows(
            cur,
            """
            SELECT id, stock_code, stock_name, class_name, total_assets, financial_assets,
                   total_liabilities, financial_liabilities, preferred_stock, minority_equity,
                   sales0, oi0, shares_outstanding, forecast_years, cost_of_capital_rate,
                   terminal_growth_rate, sales_growth_rates, operating_margins,
                   created_at, updated_at
            FROM valuation_inputs
            WHERE stock_code = ANY(%s)
            ORDER BY stock_code, updated_at DESC NULLS LAST, id
            """,
            params,
        ):
            bundles[row["stock_code"]].inputs.append(row)
        for row in _rows(
            cur,
            """
            SELECT DISTINCT ON (stock_code)
                   id, stock_code, stock_name, class_name, value_per_share, close_price,
                   trade_date, price_bias, bias_ratio, remark, updated_at
            FROM valuation_summary
            WHERE stock_code = ANY(%s)
            ORDER BY stock_code, updated_at DESC NULLS LAST
            """,
            params,
        ):
            bundles[row["stock_code"]].summary = row
        for row in _rows(
            cur,
            """
            SELECT stock_code, industry_l1, industry_l2, industry_raw, source, updated_at
            FROM vr_industry_sw
            WHERE stock_code = ANY(%s)
            """,
            params,
        ):
            bundles[row["stock_code"]].industry_sw = row
        for row in _rows(
            cur,
            """
            SELECT DISTINCT ON (stock_code)
                   stock_code, stock_name, industry_l1, close_price, market_cap, pe_ttm, pb,
                   report_period, net_income, revenue, total_assets, batch_date
            FROM vr_finance_snapshot
            WHERE stock_code = ANY(%s)
            ORDER BY stock_code, batch_date DESC NULLS LAST
            """,
            params,
        ):
            bundles[row["stock_code"]].finance = row
    finally:
        conn.close()
    return bundles
