import re
from urllib.parse import quote

import httpx

from app.config import settings
from app.mcp.models import DataResult, Source

HEADERS = {"User-Agent": "Mozilla/5.0"}
EASTMONEY_HEADERS = {"Referer": "https://quote.eastmoney.com/"}
EASTMONEY_HOSTS = ("push2.eastmoney.com", "17.push2.eastmoney.com", "82.push2.eastmoney.com")


class MarketProvider:
    """Public Tencent/Sina/Eastmoney adapters. Responses are normalized before use."""

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(
            timeout=settings.data_request_timeout_seconds, headers=HEADERS, follow_redirects=True
        ) as client:
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            return response

    async def search_symbol(self, keyword: str) -> DataResult:
        try:
            response = await self._get(f"https://suggest3.sinajs.cn/suggest/type=&key={quote(keyword)}")
            response.encoding = "gbk"
            body = response.text.split('"', 1)[-1].rsplit('"', 1)[0]
            rows = []
            for item in filter(None, body.split(";")):
                fields = item.split(",")
                if len(fields) >= 4:
                    rows.append({"name": fields[0], "code": fields[2], "symbol": fields[3]})
            return DataResult(provider="sina", data=rows, sources=[self._source("证券代码检索", "数据", response.url)])
        except Exception as exc:
            return DataResult.failure("sina", str(exc))

    async def quote(self, symbols: list[str]) -> DataResult:
        try:
            response = await self._get(f"https://qt.gtimg.cn/q={','.join(symbols)}")
            response.encoding = "gbk"
            quotes = []
            for line in response.text.splitlines():
                match = re.match(r"v_(\w+)=\"(.*)\";", line)
                if not match:
                    continue
                fields = match.group(2).split("~")
                if len(fields) < 38:
                    continue
                quotes.append(
                    {
                        "symbol": match.group(1),
                        "name": fields[1],
                        "code": fields[2],
                        "last_price": fields[3],
                        "previous_close": fields[4],
                        "open": fields[5],
                        "volume": fields[6],
                        "change_percent": fields[32],
                        "turnover": fields[37],
                        "pe_ttm": fields[39] if len(fields) > 39 else None,
                        "market_cap": fields[45] if len(fields) > 45 else None,
                        "quoted_at": fields[30] if len(fields) > 30 else "",
                    }
                )
            return DataResult(
                provider="tencent", data=quotes, sources=[self._source("腾讯财经实时行情", "数据", response.url)]
            )
        except Exception as exc:
            return DataResult.failure("tencent", str(exc))

    async def kline(self, symbol: str, period: str = "day", count: int = 260, adjust: str = "qfq") -> DataResult:
        try:
            url = (
                "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?"
                f"param={symbol},{period},,,{min(count, 1000)},{adjust}"
            )
            payload = (await self._get(url)).json()
            stock = payload.get("data", {}).get(symbol, {})
            rows = stock.get(f"{adjust}{period}") or stock.get(period) or []
            return DataResult(
                provider="tencent",
                data={"symbol": symbol, "period": period, "adjust": adjust, "klines": [r[:6] for r in rows]},
                sources=[self._source(f"腾讯财经 {symbol} K线", "数据", url)],
            )
        except Exception as exc:
            return DataResult.failure("tencent", str(exc))

    async def minute_kline(self, symbol: str, period: int = 5, count: int = 240) -> DataResult:
        try:
            period = period if period in {1, 5, 15, 30, 60} else 5
            url = f"https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={symbol},m{period},,{min(count, 320)}"
            text = (await self._get(url)).text.split("=", 1)[-1]
            rows = __import__("json").loads(text).get("data", {}).get(symbol, {}).get(f"m{period}", [])
            return DataResult(
                provider="tencent",
                data={"symbol": symbol, "period": period, "klines": [r[:6] for r in rows]},
                sources=[self._source(f"腾讯财经 {symbol} 分钟K线", "数据", url)],
            )
        except Exception as exc:
            return DataResult.failure("tencent", str(exc))

    async def eastmoney_rank(self, fs: str, title: str, fid: str = "f3") -> DataResult:
        """Generic Eastmoney ranking endpoint for indices, sectors and capital-flow rankings."""
        params = {
            "pn": 1,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": fid,
            "fs": fs,
            "fields": "f12,f14,f2,f3,f4,f5,f6,f8,f20,f21,f62",
        }
        errors = []
        for host in EASTMONEY_HOSTS:
            url = f"https://{host}/api/qt/clist/get"
            try:
                payload = (await self._get(url, params=params, headers=EASTMONEY_HEADERS)).json()
                rows = list((payload.get("data") or {}).get("diff") or [])
                return DataResult(
                    provider="eastmoney",
                    data=rows,
                    sources=[self._source(title, "数据", str(httpx.URL(url, params=params)))],
                )
            except Exception as exc:
                errors.append(f"{host}: {exc}")
        return DataResult.failure(
            "eastmoney",
            f"东方财富{title}接口暂不可用（已重试 {len(EASTMONEY_HOSTS)} 个节点），"
            "请在回答中说明该项数据缺失，不要编造。" + "；".join(errors)[:300],
        )

    def _source(self, title: str, tag: str, url: object) -> Source:
        return Source(
            title=title,
            tag=tag,
            url=str(url),
            provider="公开行情接口",
            retrieved_at=DataResult(provider="x", data={}).retrieved_at,
        )
