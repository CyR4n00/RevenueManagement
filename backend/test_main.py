import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
import models

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

# Initialize DB for tests
def setup_db():
    db = TestingSessionLocal()
    if not db.query(models.DBFacility).first():
        db.add(models.DBFacility(id=1, name="自社ホテル（サンプル）", base_price=10000))
        db.add(models.DBCompetitor(id=1, name="ホテルA", url="http://example.com/a"))
        db.add(models.DBCompetitor(id=2, name="ホテルB", url="http://example.com/b"))
        db.commit()
    db.close()

setup_db()

client = TestClient(app)

def test_get_facility():
    response = client.get("/facility")
    assert response.status_code == 200
    assert response.json()["name"] == "自社ホテル（サンプル）"

def test_get_competitors():
    response = client.get("/competitors")
    assert response.status_code == 200
    assert len(response.json()) >= 2
