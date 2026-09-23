import httpx

from app.config import settings


class SearchClient:
    async def search(self, query: str) -> list[dict]:
        if not settings.search_api_url:
            return []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                settings.search_api_url,
                params={"q": query},
                headers={"Authorization": f"Bearer {settings.search_api_key}"},
            )
            return resp.json().get("results", [])


class QuoteClient:
    async def get_quote(self, symbol: str) -> dict:
        if not settings.quote_api_url:
            return {}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                settings.quote_api_url,
                params={"symbol": symbol},
                headers={"Authorization": f"Bearer {settings.quote_api_key}"},
            )
            return resp.json()


class ResearchClient:
    async def search_research(self, query: str, doc_type: str = "研报") -> list[dict]:
        if not settings.research_api_url:
            return []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                settings.research_api_url,
                params={"q": query, "type": doc_type},
                headers={"Authorization": f"Bearer {settings.research_api_key}"},
            )
            return resp.json().get("results", [])


class NewsClient:
    async def search_news(self, query: str) -> list[dict]:
        if not settings.search_api_url:
            return []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                settings.search_api_url,
                params={"q": query, "type": "news"},
                headers={"Authorization": f"Bearer {settings.search_api_key}"},
            )
            return resp.json().get("results", [])
