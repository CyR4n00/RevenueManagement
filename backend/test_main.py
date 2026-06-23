import pytest
from fastapi.testclient import TestClient
from main import app, get_db
from database import Base, engine, SessionLocal
import datetime

# Create a test database and use it
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_get_market_data():
    today = datetime.date.today().strftime("%Y-%m-%d")
    response = client.get(f"/market_data?start_date={today}&days=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "date" in data[0]
        assert "competitor_id" in data[0]
        assert "competitor_name" in data[0]
        assert "price_today" in data[0]

def test_get_alerts():
    today = datetime.date.today().strftime("%Y-%m-%d")
    response = client.get(f"/alerts?start_date={today}&days=7")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "date" in data[0]
        assert "message" in data[0]
        assert "type" in data[0]

def test_get_recommendation():
    today = datetime.date.today().strftime("%Y-%m-%d")
    response = client.get(f"/recommendation?date={today}")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "suggested_price" in data
    assert "reasoning" in data
