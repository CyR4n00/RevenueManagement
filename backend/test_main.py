import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import datetime

from main import app, get_db
from database import Base
import models

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Seed initial test data
    if not db.query(models.DBFacility).first():
        db.add(models.DBFacility(id=1, name="自社ホテル（テスト）", base_price=10000))
        db.add(models.DBCompetitor(id=1, name="ホテルA (テスト)", url="http://example.com/a"))
        db.add(models.DBCompetitor(id=2, name="ホテルB (テスト)", url="http://example.com/b"))
        db.commit()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    with TestClient(app) as c:
        yield c

def test_get_facility(client):
    response = client.get("/facility")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "自社ホテル（テスト）"
    assert data["base_price"] == 10000

def test_get_competitors(client):
    response = client.get("/competitors")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "ホテルA (テスト)"

def test_get_market_data(client, test_db):
    # Need to simulate running the scraper logic for specific dates so market_data API can fetch it.
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    response = client.get(f"/market_data?start_date={today_str}&days=1")
    assert response.status_code == 200
    data = response.json()

    # We expect 2 competitors in the response
    assert len(data) == 2
    assert "competitor_name" in data[0]
    assert "price_today" in data[0]

def test_get_recommendation(client):
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    response = client.get(f"/recommendation?date={today_str}")

    assert response.status_code == 200
    data = response.json()
    assert "suggested_price" in data
    assert "suggested_rank" in data
    assert "reasoning" in data
