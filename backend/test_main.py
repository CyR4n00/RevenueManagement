import datetime as dt
import os

os.environ["APP_ENV"] = "demo"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["ALLOW_SIMULATED_DATA"] = "true"
os.environ["DEMO_BYPASS_BILLING"] = "false"
os.environ["SUPABASE_AUTH_REQUIRED"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
import models
from scraper import ScrapeResult


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    with TestSession() as db:
        yield db


app.dependency_overrides[get_db] = override_get_db


def reset_database():
    with TestSession() as db:
        db.query(models.DBCompetitorPriceObservation).delete()
        db.query(models.DBCompetitorPrice).delete()
        db.query(models.DBCompetitor).delete()
        db.query(models.DBSubscription).delete()
        db.query(models.DBFacility).delete()
        db.query(models.DBOrganizationMember).delete()
        db.query(models.DBOrganization).delete()
        db.commit()


def seed_ready_account(with_competitor: bool = False):
    with TestSession() as db:
        db.add(models.DBOrganization(id="org-1", name="Test Organization"))
        db.add(models.DBOrganizationMember(organization_id="org-1", user_id="demo-user", role="owner"))
        db.add(models.DBSubscription(organization_id="org-1", status="active"))
        db.add(models.DBFacility(
            id="facility-1", organization_id="org-1", name="Test Facility", address="Tokyo",
            base_price=10_000, min_price=5_000, max_price=30_000,
            onboarding_completed_at=dt.datetime.now(dt.timezone.utc),
        ))
        if with_competitor:
            db.add(models.DBCompetitor(
                id="competitor-1", facility_id="facility-1", ota_source_key="booking", name="Competitor",
                url="https://www.booking.com/hotel/jp/example.html", canonical_url="https://www.booking.com/hotel/jp/example.html",
            ))
        db.commit()


def test_read_facility():
    reset_database()
    seed_ready_account()
    with TestClient(app) as client:
        response = client.get("/facility")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Facility"


def test_rejects_invalid_price_guardrail():
    reset_database()
    seed_ready_account()
    with TestClient(app) as client:
        response = client.put("/facility", json={"min_price": 30_001, "max_price": 30_000})
    assert response.status_code == 422


def test_market_data_is_explicitly_marked_as_simulated_in_demo():
    reset_database()
    seed_ready_account(with_competitor=True)
    stay_date = dt.date.today().isoformat()
    with TestClient(app) as client:
        market = client.get("/market_data", params={"start_date": stay_date, "days": 1})
        recommendation = client.get("/recommendation", params={"date": stay_date})
    assert market.status_code == 200
    assert market.json()[0]["source"] == "simulation"
    assert recommendation.status_code == 200
    assert 5_000 <= recommendation.json()["suggested_price"] <= 30_000


def test_market_data_batches_stay_dates_into_one_collection_run(monkeypatch):
    reset_database()
    seed_ready_account(with_competitor=True)
    import main

    requested_dates: list[str] = []

    def collect_once(url: str, target_dates: list[str], comp_id: str):
        assert url == "https://www.booking.com/hotel/jp/example.html"
        assert comp_id == "competitor-1"
        requested_dates.extend(target_dates)
        return {
            target_date: ScrapeResult(price=12_000, is_fully_booked=False, source="apify")
            for target_date in target_dates
        }

    monkeypatch.setattr(main.scraper_service, "extract_prices", collect_once)
    start_date = dt.date.today().isoformat()
    with TestClient(app) as client:
        response = client.get("/market_data", params={"start_date": start_date, "days": 3})
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert requested_dates == [(dt.date.today() + dt.timedelta(days=offset)).isoformat() for offset in range(3)]


def test_dashboard_requires_an_active_subscription():
    reset_database()
    with TestSession() as db:
        db.add(models.DBOrganization(id="org-1", name="Test Organization"))
        db.add(models.DBOrganizationMember(organization_id="org-1", user_id="demo-user", role="owner"))
        db.commit()
    with TestClient(app) as client:
        response = client.get("/facility")
    assert response.status_code == 402
