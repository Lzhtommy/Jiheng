import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.mcp.models import DataResult, Source


class ContentProvider:
    async def official_policy(self, limit: int = 20) -> DataResult:
        url = "https://www.gov.cn/zhengce/index.htm"
        try:
            async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds) as client:
                response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            rows = []
            for link in soup.select("a[href]"):
                title = link.get_text(" ", strip=True)
                href = link["href"]
                if title and "content_" in href:
                    rows.append({"title": title, "url": str(httpx.URL(url).join(href))})
                if len(rows) >= limit:
                    break
            return DataResult(provider="gov_cn", data=rows, sources=[self._source("中国政府网政策", "政策", url)])
        except Exception as exc:
            return DataResult.failure("gov_cn", str(exc))

    async def eastmoney_news(self, keyword: str, limit: int = 10) -> DataResult:
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        params = {
            "cb": "jQuery",
            "param": '{"uid":"","keyword":"'
            + keyword
            + '","type":["cmsArticle"],"pageindex":1,"pagesize":'
            + str(min(limit, 50))
            + "}",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds) as client:
                response = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
            text = response.text
            payload = __import__("json").loads(text[text.find("(") + 1 : text.rfind(")")])
            articles = payload.get("result", {}).get("cmsArticle", [])
            rows = [
                {
                    "title": item.get("title", ""),
                    "summary": item.get("content", ""),
                    "published_at": item.get("date", ""),
                    "url": item.get("url", ""),
                    "media": item.get("mediaName", "东方财富"),
                }
                for item in articles
            ]
            return DataResult(
                provider="eastmoney",
                data=rows,
                sources=[self._source("东方财富财经资讯检索", "新闻", str(response.url))],
            )
        except Exception as exc:
            return DataResult.failure("eastmoney", str(exc))

    def _source(self, title: str, tag: str, url: str) -> Source:
        return Source(
            title=title,
            tag=tag,
            url=url,
            provider="公开资讯接口",
            retrieved_at=DataResult(provider="x", data={}).retrieved_at,
        )
