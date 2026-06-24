import pytest
from fastapi.testclient import TestClient
from main import app, get_db
from database import Base, engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
import datetime

# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_revenue_assistant.db"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

Base.metadata.create_all(bind=engine_test)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)

    db = TestingSessionLocal()

    # Add seed data
    db.add(models.DBFacility(id=1, name="Test Facility", base_price=10000))
    db.add(models.DBCompetitor(id=1, name="Test Competitor A", url="http://test.com/a"))
    db.add(models.DBCompetitor(id=2, name="Test Competitor B", url="http://test.com/b"))
    db.commit()

    db.close()
    yield

def test_get_facility():
    response = client.get("/facility")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Facility"
    assert data["base_price"] == 10000

def test_get_competitors():
    response = client.get("/competitors")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Test Competitor A"
    assert data[1]["name"] == "Test Competitor B"

def test_get_market_data():
    today = datetime.date.today().strftime("%Y-%m-%d")
    response = client.get(f"/market_data?start_date={today}&days=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2 # 2 competitors
    assert "competitor_name" in data[0]
    assert "price_today" in data[0]

def test_get_alerts():
    today = datetime.date.today().strftime("%Y-%m-%d")
    response = client.get(f"/alerts?start_date={today}&days=1")
    assert response.status_code == 200
    data = response.json()
    # Scraper logic may or may not generate alerts based on random logic,
    # but the endpoint should return a list.
    assert isinstance(data, list)

def test_get_recommendation():
    today = datetime.date.today().strftime("%Y-%m-%d")
    response = client.get(f"/recommendation?date={today}")
    assert response.status_code == 200
    data = response.json()
    assert "suggested_price" in data
    assert "reasoning" in data
