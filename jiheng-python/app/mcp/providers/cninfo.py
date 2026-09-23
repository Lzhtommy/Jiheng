from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.mcp.models import DataResult, Source

QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
TOP_SEARCH_URL = "https://www.cninfo.com.cn/new/information/topSearch/query"
STATIC_BASE = "https://static.cninfo.com.cn/"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn/"}


class CninfoProvider:
    async def company_events(self, limit: int = 20) -> DataResult:
        """Expose CNINFO's official trading-tips page as a traceable event calendar source."""
        url = "https://www.cninfo.com.cn/new/commonUrl?url=disclosure/tradingTips"
        try:
            async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds, headers=HEADERS) as client:
                response = await client.get(url)
                response.raise_for_status()
            return DataResult(
                provider="cninfo",
                data={"calendar_url": str(response.url), "limit": min(limit, 100)},
                sources=[
                    Source(
                        title="巨潮资讯网交易日历",
                        tag="事件",
                        url=str(response.url),
                        provider="巨潮资讯网",
                        retrieved_at=DataResult(provider="x", data={}).retrieved_at,
                    )
                ],
            )
        except Exception as exc:
            return DataResult.failure("cninfo", str(exc))

    async def list_announcements(
        self, stock_code: str = "", start_date: str = "", end_date: str = "", keyword: str = "", limit: int = 10
    ) -> DataResult:
        params = {
            "pageNum": 1,
            "pageSize": min(max(limit, 1), 30),
            "column": "szse",
            "tabName": "fulltext",
            "plate": "sz;sh;bj",
            "stock": "",
            "searchkey": keyword,
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": f"{start_date}~{end_date}" if start_date or end_date else "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds, headers=HEADERS) as client:
                if stock_code:
                    code = stock_code.zfill(6)
                    org_id = await self._org_id(client, code)
                    if not org_id:
                        return DataResult.failure("cninfo", f"未找到证券代码 {code}")
                    params["stock"] = f"{code},{org_id}"
                response = await client.post(
                    QUERY_URL,
                    content=urlencode(params),
                    headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
            items = []
            for row in response.json().get("announcements") or []:
                path = row.get("adjunctUrl", "")
                items.append(
                    {
                        "stock_code": row.get("secCode"),
                        "name": row.get("secName"),
                        "title": row.get("announcementTitle", "").replace("<em>", "").replace("</em>", ""),
                        "published_at": row.get("announcementTime"),
                        "announcement_id": row.get("announcementId"),
                        "url": path if path.startswith("http") else STATIC_BASE + path.lstrip("/"),
                    }
                )
            return DataResult(
                provider="cninfo",
                data=items,
                sources=[
                    Source(
                        title="巨潮资讯网公告检索",
                        tag="公告",
                        url=QUERY_URL,
                        provider="巨潮资讯网",
                        retrieved_at=DataResult(provider="x", data={}).retrieved_at,
                    )
                ],
            )
        except Exception as exc:
            return DataResult.failure("cninfo", str(exc))

    async def _org_id(self, client: httpx.AsyncClient, code: str) -> str:
        """CNINFO only filters by stock when given "code,orgId"; resolve orgId via its search API."""
        response = await client.post(TOP_SEARCH_URL, data={"keyWord": code, "maxNum": 10})
        response.raise_for_status()
        return next((row.get("orgId", "") for row in response.json() or [] if row.get("code") == code), "")

    async def download(self, url: str, cache_key: str) -> DataResult:
        try:
            async with httpx.AsyncClient(timeout=60, headers=HEADERS, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
            path = Path(settings.cninfo_cache_dir) / f"{cache_key}.pdf"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
            return DataResult(
                provider="cninfo", data={"path": str(path), "size": len(response.content), "url": url}, sources=[]
            )
        except Exception as exc:
            return DataResult.failure("cninfo", str(exc))
