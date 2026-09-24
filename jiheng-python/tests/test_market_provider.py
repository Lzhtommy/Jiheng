import asyncio

import httpx

from app.mcp.providers.market import MarketProvider


def test_quote_normalizes_tencent_response(monkeypatch):
    fields = [""] * 46
    fields[1], fields[2], fields[3], fields[4], fields[5], fields[6] = (
        "TestCo",
        "000001",
        "10.5",
        "10.0",
        "10.1",
        "123",
    )
    fields[30], fields[32], fields[37], fields[39], fields[45] = "20260923103000", "5.0", "1000", "15", "2000"

    async def fake_get(self, url, **kwargs):
        return httpx.Response(200, text=f'v_sz000001="{"~".join(fields)}";', request=httpx.Request("GET", url))

    monkeypatch.setattr(MarketProvider, "_get", fake_get)
    result = asyncio.run(MarketProvider().quote(["sz000001"]))

    assert result.status == "success"
    assert result.data[0]["name"] == "TestCo"
    assert result.data[0]["change_percent"] == "5.0"
    assert result.sources[0].url.startswith("https://qt.gtimg.cn/")


def test_quote_returns_failure_when_provider_fails(monkeypatch):
    async def fake_get(self, url, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(MarketProvider, "_get", fake_get)
    result = asyncio.run(MarketProvider().quote(["sz000001"]))

    assert result.status == "failed"
    assert "offline" in result.error
