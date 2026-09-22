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

