from __future__ import annotations

import re
from typing import Any

from .data import DEMO_UNIVERSE, StockRecord, get_stock
from .models import Evidence, ScreenResult


DATA_NOTICE = "当前为可重复的演示数据，非实时行情，不构成投资建议；接入真实数据后将保留字段级来源。"


def _number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def interpret_query(query: str) -> dict[str, Any]:
    normalized = query.lower().replace(" ", "")
    filters: dict[str, Any] = {}

    pe_max = _number(normalized, [r"(?:pe|市盈率)(?:ttm)?[<≤不超过低于]{1,3}(\d+(?:\.\d+)?)", r"(?:pe|市盈率)(?:低于|小于|不超过)(\d+(?:\.\d+)?)"])
    roe_min = _number(normalized, [r"roe[>≥高于超过]{1,3}(\d+(?:\.\d+)?)", r"roe(?:大于|高于|超过)(\d+(?:\.\d+)?)"])
    profit_min = _number(normalized, [r"(?:净利润|利润)(?:增长率|增速)?[>≥高于超过]{1,3}(\d+(?:\.\d+)?)%?", r"(?:净利润|利润)(?:增长率|增速)?(?:大于|高于|超过)(\d+(?:\.\d+)?)%?"])
    dividend_min = _number(normalized, [r"(?:股息率|分红率)[>≥高于超过]{1,3}(\d+(?:\.\d+)?)%?", r"(?:股息率|分红率)(?:大于|高于|超过)(\d+(?:\.\d+)?)%?"])

    if pe_max is not None:
        filters["pe_max"] = pe_max
    if roe_min is not None:
        filters["roe_min"] = roe_min
    if profit_min is not None:
        filters["profit_growth_min"] = profit_min
    if dividend_min is not None:
        filters["dividend_yield_min"] = dividend_min

    if "低估值" in normalized and "pe_max" not in filters:
        filters["pe_max"] = 20.0
    if any(word in normalized for word in ("高股息", "高分红")) and "dividend_yield_min" not in filters:
        filters["dividend_yield_min"] = 3.0
    if any(word in normalized for word in ("高成长", "高增长")) and "profit_growth_min" not in filters:
        filters["profit_growth_min"] = 20.0
    if any(word in normalized for word in ("现金流为正", "现金流健康", "经营现金流")):
        filters["cashflow_positive_3y"] = True
    if "科技" in normalized:
        filters["industry_keywords"] = ["半导体", "电子", "新能源", "软件", "智能制造"]
    elif "新能源" in normalized:
        filters["industry_keywords"] = ["新能源"]

    mentioned = re.findall(r"(?:300\d{3}|600\d{3}|601\d{3}|603\d{3}|688\d{3}|000\d{3}|002\d{3}|003\d{3})", query)
    if mentioned:
        filters["codes"] = mentioned

    return filters


def _passes(record: StockRecord, filters: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if filters.get("codes") and record.code not in filters["codes"]:
        return False, reasons
    if "pe_max" in filters:
        if record.pe_ttm > filters["pe_max"]:
            return False, reasons
        reasons.append(f"PE {record.pe_ttm:.1f} ≤ {filters['pe_max']:.1f}")
    if "roe_min" in filters:
        if record.roe < filters["roe_min"]:
            return False, reasons
        reasons.append(f"ROE {record.roe:.1f}% ≥ {filters['roe_min']:.1f}%")
    if "profit_growth_min" in filters:
        if record.profit_growth < filters["profit_growth_min"]:
            return False, reasons
        reasons.append(f"净利润增速 {record.profit_growth:.1f}% ≥ {filters['profit_growth_min']:.1f}%")
    if "dividend_yield_min" in filters:
        if record.dividend_yield < filters["dividend_yield_min"]:
            return False, reasons
        reasons.append(f"股息率 {record.dividend_yield:.1f}% ≥ {filters['dividend_yield_min']:.1f}%")
    if filters.get("cashflow_positive_3y"):
        if not record.cashflow_positive_3y:
            return False, reasons
        reasons.append("近三年经营现金流为正")
    if filters.get("industry_keywords"):
        if not any(keyword in record.industry for keyword in filters["industry_keywords"]):
            return False, reasons
        reasons.append(f"行业匹配：{record.industry}")
    if not filters:
        reasons.append("未识别到硬条件，展示演示股票池")
    return True, reasons


def _screen_result(record: StockRecord, reasons: list[str]) -> ScreenResult:
    return ScreenResult(
        code=record.code,
        name=record.name,
        industry=record.industry,
        price=record.price,
        change_1d=record.change_1d,
        pe_ttm=record.pe_ttm,
        roe=record.roe,
        profit_growth=record.profit_growth,
        dividend_yield=record.dividend_yield,
        cashflow_positive_3y=record.cashflow_positive_3y,
        match_score=len(reasons),
        match_reason=reasons,
        evidence=record.evidence(),
    )


def screen(query: str) -> tuple[dict[str, Any], list[ScreenResult]]:
    filters = interpret_query(query)
    results = []
    for record in DEMO_UNIVERSE:
        matched, reasons = _passes(record, filters)
        if matched:
            results.append(_screen_result(record, reasons))
    results.sort(key=lambda item: (-item.match_score, item.pe_ttm))
    return filters, results


def _derived(record: StockRecord) -> list[dict[str, Any]]:
    quality = "较强" if record.cashflow_positive_3y and record.profit_growth >= record.revenue_growth else "需核验"
    return [
        {
            "label": "增长质量",
            "value": quality,
            "kind": "AI 衍生",
            "confidence": 0.72,
            "formula": "经营现金流状态 + 净利润增速与营收增速对比",
        },
        {
            "label": "估值观察",
            "value": "相对温和" if record.pe_ttm < 20 else "需要解释",
            "kind": "AI 衍生",
            "confidence": 0.68,
            "formula": "仅依据演示 PE 快照，不等同于合理价值判断",
        },
    ]


def diagnosis(code: str) -> dict[str, Any] | None:
    record = get_stock(code)
    if record is None:
        return None
    signals: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    if record.roe >= 15:
        signals.append({"title": "资本回报率较高", "detail": f"ROE 为 {record.roe:.1f}%", "evidence_id": f"demo:{code}:financial"})
    if record.profit_growth >= 20:
        signals.append({"title": "利润增速较快", "detail": f"净利润增速为 {record.profit_growth:.1f}%", "evidence_id": f"demo:{code}:financial"})
    if record.cashflow_positive_3y:
        signals.append({"title": "现金流连续为正", "detail": "近三年经营现金流状态为正", "evidence_id": f"demo:{code}:cashflow"})
    if record.pe_ttm >= 30:
        risks.append({"title": "估值解释压力", "detail": f"PE(TTM) 为 {record.pe_ttm:.1f}，需要更强的增长或竞争壁垒证据", "evidence_id": f"demo:{code}:market"})
    if record.profit_growth < record.revenue_growth:
        risks.append({"title": "利润增速低于营收增速", "detail": "需要进一步检查毛利率、费用率和非经常性损益", "evidence_id": f"demo:{code}:financial"})
    if not record.cashflow_positive_3y:
        risks.append({"title": "现金流需要核验", "detail": "演示快照显示经营现金流并非连续为正", "evidence_id": f"demo:{code}:cashflow"})

    return {
        "code": record.code,
        "name": record.name,
        "industry": record.industry,
        "as_of": record.updated_at,
        "summary": f"{record.name}处于{record.industry}行业。当前证据显示：{len(signals)} 项支持因素、{len(risks)} 项待核验风险。该页面呈现研究线索，不输出买卖结论。",
        "metrics": {
            "price": record.price,
            "change_1d": record.change_1d,
            "pe_ttm": record.pe_ttm,
            "pb": record.pb,
            "roe": record.roe,
            "revenue_growth": record.revenue_growth,
            "profit_growth": record.profit_growth,
            "dividend_yield": record.dividend_yield,
        },
        "signals": signals,
        "risks": risks,
        "derived": _derived(record),
        "evidence": [item.model_dump() for item in record.evidence()],
        "data_notice": DATA_NOTICE,
    }


def debate(code: str) -> dict[str, Any] | None:
    record = get_stock(code)
    report = diagnosis(code)
    if record is None or report is None:
        return None
    bull = [
        {"point": f"ROE 为 {record.roe:.1f}%，资本回报能力值得继续研究。", "evidence_ids": [f"demo:{code}:financial"]},
        {"point": f"净利润增速为 {record.profit_growth:.1f}%，高于营收增速 {record.revenue_growth:.1f}% 。", "evidence_ids": [f"demo:{code}:financial"]},
    ]
    bear = [
        {"point": f"PE(TTM) 为 {record.pe_ttm:.1f}，估值是否匹配未来增长需要额外证据。", "evidence_ids": [f"demo:{code}:market"]},
        {"point": "演示数据不是实时数据，无法替代最新公告、财报和市场价格核验。", "evidence_ids": [f"demo:{code}:market", f"demo:{code}:financial"]},
    ]
    if not record.cashflow_positive_3y:
        bear.append({"point": "经营现金流没有显示为连续正值，应优先核对现金流量表。", "evidence_ids": [f"demo:{code}:cashflow"]})
    return {
        "code": code,
        "name": record.name,
        "bull": bull,
        "bear": bear,
        "judge": "当前只能形成待验证的研究假设；需要核对最新财报、公告和行业数据后再判断逻辑是否成立。",
        "falsify": [
            "最新财报中经营现金流持续恶化",
            "核心产品或行业增速显著低于当前假设",
            "估值继续上升但盈利预期没有同步改善",
        ],
        "evidence": [item.model_dump() for item in record.evidence()],
        "data_notice": DATA_NOTICE,
    }

