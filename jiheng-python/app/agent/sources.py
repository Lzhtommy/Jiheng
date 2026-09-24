import re
from collections.abc import Iterable
from typing import Any

SOURCE_INTENT = re.compile(
    r"行情|股价|涨跌|估值|市值|财报|营收|利润|现金流|公告|新闻|政策|事件|行业|板块|资金流|"
    r"同比|环比|目标价|评级|数据|最新|今日|目前|当前|截至|公司|股票|指数"
)
QUANTIFIED_FACT = re.compile(
    r"(?:\d[\d,.]*\s*(?:%|元|万元|亿元|万亿|倍|点|股|手|家|年|月|日)|"
    r"(?:20\d{2}|19\d{2})[-年/.])"
)


def add_sources(target: dict[str, dict], sources: Iterable[Any]) -> None:
    """Normalize valid tool sources into a stable, URL-keyed collection."""
    for item in sources:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title or not url:
            continue
        source = dict(item)
        source["title"] = title
        source["url"] = url
        source["tag"] = str(source.get("tag") or "数据")
        source["date"] = str(source.get("date") or source.get("retrieved_at") or "")[:10]
        target.setdefault(url, source)


def requires_sources(question: str, answer: str = "") -> bool:
    """Return whether a response relies on current or externally verifiable facts."""
    return bool(SOURCE_INTENT.search(question) or QUANTIFIED_FACT.search(answer))
