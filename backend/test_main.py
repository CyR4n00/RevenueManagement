import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, get_db
from database import Base

# Setup in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    # Setup test data using the lifespan context manager concept manually or directly creating DB records
    # Since lifespan executes in the real app, we simulate the database seeding here
    db = TestingSessionLocal()
    from models import DBFacility, DBCompetitor
    if not db.query(DBFacility).first():
        db.add(DBFacility(id=1, name="Test Hotel", base_price=10000))
        db.add(DBCompetitor(id=1, name="Test Comp A", url="http://example.com/a"))
        db.add(DBCompetitor(id=2, name="Test Comp B", url="http://example.com/b"))
        db.commit()
    db.close()

    with TestClient(app) as c:
        yield c

def test_get_recommendation(client):
    response = client.get("/recommendation?date=2026-07-20")
    assert response.status_code == 200
    data = response.json()
    assert "suggested_price" in data
    assert "suggested_rank" in data
    assert "reasoning" in data

def test_get_market_data(client):
    response = client.get("/market_data?start_date=2026-07-20&days=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # We added 2 competitors, over 3 days = 6 entries expected
    assert len(data) == 6
    assert "price_today" in data[0]

def test_get_alerts(client):
    response = client.get("/alerts?start_date=2026-07-20&days=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # We might not have alerts generated depending on the random scraping fallback,
    # but the endpoint should return successfully and conform to the model.
