import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, get_db
from database import Base
import models
import datetime

# Create a static in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    # Setup tables before each test
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Initialize mock data for tests
    db.add(models.DBFacility(id=1, name="テスト自社ホテル", base_price=10000, min_price=5000, max_price=30000))
    db.add(models.DBCompetitor(id=1, name="テストホテルA", url="http://example.com/a"))
    db.add(models.DBCompetitor(id=2, name="テストホテルB", url="http://example.com/b"))
    db.commit()

    yield
    # Teardown tables after each test
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_get_facility():
    with TestClient(app) as client:
        response = client.get("/facility")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "テスト自社ホテル"
        assert data["base_price"] == 10000

def test_get_competitors():
    with TestClient(app) as client:
        response = client.get("/competitors")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "テストホテルA"
        assert data[1]["name"] == "テストホテルB"

def test_get_market_data():
    with TestClient(app) as client:
        today = datetime.date.today().strftime("%Y-%m-%d")
        response = client.get(f"/market_data?start_date={today}&days=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # One entry per competitor

def test_get_recommendation():
    with TestClient(app) as client:
        today = datetime.date.today().strftime("%Y-%m-%d")
        response = client.get(f"/recommendation?date={today}")
        assert response.status_code == 200
        data = response.json()
        assert "suggested_price" in data
        assert "suggested_rank" in data
        assert "reasoning" in data
