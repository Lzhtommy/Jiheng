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
