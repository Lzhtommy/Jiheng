from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["data_mode"] == "demo"


def test_screen_endpoint():
    response = client.post("/api/screen", json={"query": "高成长科技股"})
    assert response.status_code == 200
    body = response.json()
    assert body["results"]
    assert body["interpreted"]["profit_growth_min"] == 20


def test_frontend_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "玑衡 AI" in response.text


def test_world_route_and_scenario_api_are_served():
    page = client.get("/world?code=300750")
    response = client.get("/api/world/300750")
    assert page.status_code == 200
    assert "产业链世界" in page.text
    assert response.status_code == 200
    assert response.json()["world_name"] == "电池环城"


def test_world_v2_is_served_as_a_separate_investigation_version():
    page = client.get("/world-v2?code=300750")
    assert page.status_code == 200
    assert "WORLD · FIELDWORK" in page.text
    assert "没有选择题，先把这里的东西看明白" in page.text


def test_procurement_journey_page_and_scene_asset_are_served():
    page = client.get("/procurement-explore")
    asset = client.get("/assets/salt-lake-mine-v1.png")
    logo = client.get("/assets/jiheng-world-logo.png")
    assert page.status_code == 200
    assert "玑衡 World · 产业链走访" in page.text
    assert "assets/jiheng-world-logo.png" in page.text
    assert asset.status_code == 200
    assert asset.headers["content-type"] == "image/png"
    assert logo.status_code == 200
    assert logo.headers["content-type"] == "image/png"


def test_procurement_npc_has_scripted_fallback_without_model(monkeypatch):
    for name in ("JIHENG_NPC_API_URL", "JIHENG_NPC_API_KEY", "JIHENG_NPC_MODEL"):
        monkeypatch.delenv(name, raising=False)
    status = client.get("/api/procurement/npc/status")
    reply = client.post(
        "/api/procurement/npc",
        json={"scene_id": "salt", "player_message": "价格依据是什么？", "fallback_reply": "请看报价牌。"},
    )
    assert status.json() == {"enabled": False}
    assert reply.status_code == 200
    assert reply.json() == {"reply": "请看报价牌。", "mode": "scripted"}
