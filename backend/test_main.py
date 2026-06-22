from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_facility():
    response = client.get("/facility")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert "base_price" in data

def test_get_competitors():
    response = client.get("/competitors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "name" in data[0]
        assert "url" in data[0]

def test_get_market_data():
    response = client.get("/market_data?start_date=2026-07-20&days=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "date" in data[0]
        assert "competitor_id" in data[0]
        assert "price_today" in data[0]

def test_get_alerts():
    response = client.get("/alerts?start_date=2026-07-20&days=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_recommendation():
    response = client.get("/recommendation?date=2026-07-20")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "suggested_price" in data
    assert "reasoning" in data
