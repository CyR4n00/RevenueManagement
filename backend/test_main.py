import os

os.environ["APP_ENV"] = "demo"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["ALLOW_SIMULATED_DATA"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
import models


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    with TestSession() as db:
        yield db


app.dependency_overrides[get_db] = override_get_db


def reset_database():
    with TestSession() as db:
        db.query(models.DBCompetitorPrice).delete()
        db.query(models.DBCompetitor).delete()
        db.query(models.DBFacility).delete()
        db.commit()


def test_read_facility():
    reset_database()
    with TestSession() as db:
        db.add(models.DBFacility(id=1, name="Test Facility", base_price=10_000, min_price=5_000, max_price=30_000))
        db.commit()
    with TestClient(app) as client:
        response = client.get("/facility")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Facility"


def test_rejects_invalid_price_guardrail():
    reset_database()
    with TestSession() as db:
        db.add(models.DBFacility(id=1, name="Test Facility", base_price=10_000, min_price=5_000, max_price=30_000))
        db.commit()
    with TestClient(app) as client:
        response = client.put("/facility", json={"min_price": 30_001, "max_price": 30_000})
    assert response.status_code == 422


def test_market_data_is_explicitly_marked_as_simulated_in_demo():
    reset_database()
    with TestSession() as db:
        db.add(models.DBFacility(id=1, name="Test Facility", base_price=10_000, min_price=5_000, max_price=30_000))
        db.add(models.DBCompetitor(id=1, name="Competitor", url="https://www.booking.com/hotel/jp/example.html"))
        db.commit()
    with TestClient(app) as client:
        market = client.get("/market_data", params={"start_date": "2026-07-20", "days": 1})
        recommendation = client.get("/recommendation", params={"date": "2026-07-20"})
    assert market.status_code == 200
    assert market.json()[0]["source"] == "simulation"
    assert recommendation.status_code == 200
    assert 5_000 <= recommendation.json()["suggested_price"] <= 30_000
