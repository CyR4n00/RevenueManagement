import datetime as dt
import os
from dataclasses import replace
from types import SimpleNamespace

import pytest

os.environ["APP_ENV"] = "demo"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["ALLOW_SIMULATED_DATA"] = "true"
os.environ["DEMO_BYPASS_BILLING"] = "false"
os.environ["SUPABASE_AUTH_REQUIRED"] = "false"

from fastapi import HTTPException
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
        db.query(models.DBNotificationDelivery).delete()
        db.query(models.DBCompetitorCollectionRun).delete()
        db.query(models.DBCompetitorPriceObservation).delete()
        db.query(models.DBCompetitorPrice).delete()
        db.query(models.DBCompetitor).delete()
        db.query(models.DBRateRank).delete()
        db.query(models.DBSubscription).delete()
        db.query(models.DBFacility).delete()
        db.query(models.DBOrganizationMember).delete()
        db.query(models.DBOrganization).delete()
        db.commit()


def test_subscription_with_future_end_is_active():
    import main

    subscription = SimpleNamespace(
        status="active",
        current_period_end=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1),
    )

    assert main._has_active_subscription(subscription) is True


def test_subscription_with_expired_end_is_inactive():
    import main

    subscription = SimpleNamespace(
        status="active",
        current_period_end=dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1),
    )

    assert main._has_active_subscription(subscription) is False


def test_manual_subscription_without_end_remains_active():
    import main

    subscription = SimpleNamespace(status="active", current_period_end=None)

    assert main._has_active_subscription(subscription) is True


def test_reference_rank_uses_competitor_average_without_hidden_markup():
    import main

    facility = SimpleNamespace(
        base_price=8_000,
        min_price=5_000,
        max_price=30_000,
        rate_ranks=[
            SimpleNamespace(label="A", price_jpy=30_000, sort_order=0),
            SimpleNamespace(label="B", price_jpy=20_000, sort_order=1),
            SimpleNamespace(label="C", price_jpy=10_000, sort_order=2),
            SimpleNamespace(label="D", price_jpy=5_000, sort_order=3),
        ],
    )
    stay_date = dt.date(2026, 9, 1)
    market_data = [
        models.CompetitorPrice(
            date=stay_date.isoformat(), competitor_id="one", competitor_name="競合1",
            price_today=16_000, price_yesterday=15_000, difference=1_000,
            comparison_available=True, comparison_days=1, is_fully_booked=False,
            availability_status="available", availability_source="inferred", source="apify",
        ),
        models.CompetitorPrice(
            date=stay_date.isoformat(), competitor_id="two", competitor_name="競合2",
            price_today=18_000, price_yesterday=18_000, difference=0,
            comparison_available=True, comparison_days=1, is_fully_booked=False,
            availability_status="available", availability_source="inferred", source="apify",
        ),
    ]

    recommendation = main.build_recommendation(None, facility, stay_date, market_data)

    assert recommendation.suggested_rank == "B"
    assert recommendation.suggested_price == 20_000
    assert "平均最安値は¥17,000" in recommendation.reasoning
    assert "自動的な上乗せや値下げには使用していません" in recommendation.reasoning


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
        db.add_all([
            models.DBRateRank(facility_id="facility-1", label="A", price_jpy=30_000, sort_order=0),
            models.DBRateRank(facility_id="facility-1", label="B", price_jpy=20_000, sort_order=1),
            models.DBRateRank(facility_id="facility-1", label="C", price_jpy=10_000, sort_order=2),
            models.DBRateRank(facility_id="facility-1", label="D", price_jpy=5_000, sort_order=3),
        ])
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
        response = client.put("/facility", json={
            "min_price": 30_001, "max_price": 30_000,
            "rate_ranks": [
                {"label": "A", "price_jpy": 30_000}, {"label": "B", "price_jpy": 20_000},
                {"label": "C", "price_jpy": 10_000}, {"label": "D", "price_jpy": 5_000},
            ],
        })
    assert response.status_code == 422


def test_facility_can_add_extended_rate_ranks():
    reset_database()
    seed_ready_account()
    ranks = [
        {"label": "A", "price_jpy": 40_000}, {"label": "B", "price_jpy": 32_000},
        {"label": "C", "price_jpy": 24_000}, {"label": "D", "price_jpy": 18_000},
        {"label": "E", "price_jpy": 12_000}, {"label": "F", "price_jpy": 8_000},
    ]
    with TestClient(app) as client:
        response = client.put("/facility", json={"min_price": 8_000, "max_price": 40_000, "rate_ranks": ranks})
    assert response.status_code == 200
    assert [rank["label"] for rank in response.json()["rate_ranks"]] == ["A", "B", "C", "D", "E", "F"]


def test_add_competitor_from_settings(monkeypatch):
    reset_database()
    seed_ready_account()
    import main

    monkeypatch.setattr(main, "_validate_ota_url", lambda _url: SimpleNamespace(key="jalan"))
    with TestClient(app) as client:
        response = client.post("/competitors", json={
            "name": "New Competitor",
            "url": "https://www.jalan.net/yad123456/",
        })
    assert response.status_code == 201
    assert response.json()["name"] == "New Competitor"


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
    assert recommendation.json()["suggested_price"] in {5_000, 10_000, 20_000, 30_000}
    assert recommendation.json()["suggested_rank"] in {"A", "B", "C", "D"}


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


def test_market_data_persists_explicit_limited_room_signal(monkeypatch):
    reset_database()
    seed_ready_account(with_competitor=True)
    import main

    monkeypatch.setattr(
        main.scraper_service,
        "extract_prices",
        lambda _url, target_dates, _comp_id: {
            target_date: ScrapeResult(
                price=12_000, is_fully_booked=False, source="apify",
                availability_status="limited", remaining_rooms=2,
                availability_source="explicit_count",
            )
            for target_date in target_dates
        },
    )
    stay_date = dt.date.today().isoformat()
    with TestClient(app) as client:
        response = client.get("/market_data", params={"start_date": stay_date, "days": 1})
    assert response.status_code == 200
    assert response.json()[0]["availability_status"] == "limited"
    assert response.json()[0]["remaining_rooms"] == 2
    assert response.json()[0]["availability_source"] == "explicit_count"
    with TestSession() as db:
        observation = db.query(models.DBCompetitorPriceObservation).one()
        assert observation.availability_status == "limited"
        assert observation.remaining_rooms == 2


def test_production_limits_each_competitor_to_configured_daily_actor_runs(monkeypatch):
    reset_database()
    seed_ready_account(with_competitor=True)
    import main

    monkeypatch.setattr(main, "settings", replace(main.settings, environment="production", daily_sync_hours=(9, 18)))
    monkeypatch.setattr(
        main.scraper_service,
        "extract_prices",
        lambda _url, target_dates, _comp_id: {
            target_date: ScrapeResult(price=12_000, is_fully_booked=False, source="apify")
            for target_date in target_dates
        },
    )
    with TestSession() as db:
        facility = db.query(models.DBFacility).filter_by(id="facility-1").one()
        main.collect_market_data(db, facility, dt.date.today(), 1, refresh=True)
        main.collect_market_data(db, facility, dt.date.today(), 1, refresh=True)
        with pytest.raises(HTTPException) as error:
            main.collect_market_data(db, facility, dt.date.today(), 1, refresh=True)
    assert error.value.status_code == 503


def test_dashboard_requires_an_active_subscription():
    reset_database()
    with TestSession() as db:
        db.add(models.DBOrganization(id="org-1", name="Test Organization"))
        db.add(models.DBOrganizationMember(organization_id="org-1", user_id="demo-user", role="owner"))
        db.commit()
    with TestClient(app) as client:
        response = client.get("/facility")
    assert response.status_code == 402


def test_standard_plan_horizon_is_limited_to_six_months():
    reset_database()
    seed_ready_account()
    with TestClient(app) as client:
        allowed = client.get("/market_data/cached", params={"start_date": dt.date.today().isoformat(), "days": 180})
        denied = client.get("/market_data/cached", params={"start_date": dt.date.today().isoformat(), "days": 365})
    assert allowed.status_code == 200
    assert denied.status_code == 403


def test_upgrade_plan_can_read_one_year(monkeypatch):
    reset_database()
    seed_ready_account()
    import main

    monkeypatch.setattr(main, "settings", replace(main.settings, stripe_price_id_upgrade="price_upgrade"))
    with TestSession() as db:
        subscription = db.query(models.DBSubscription).filter_by(organization_id="org-1").one()
        subscription.stripe_price_id = "price_upgrade"
        db.commit()
    with TestClient(app) as client:
        response = client.get("/market_data/cached", params={"start_date": dt.date.today().isoformat(), "days": 365})
    assert response.status_code == 200


def test_future_scheduler_rotates_one_31_day_chunk(monkeypatch):
    reset_database()
    seed_ready_account()
    import main
    import scheduler

    calls: list[tuple[dt.date, int, bool]] = []

    def collect_chunk(_db, _facility, start, days, *, refresh=False):
        calls.append((start, days, refresh))
        return []

    monkeypatch.setattr(main, "collect_market_data", collect_chunk)
    monkeypatch.setattr(scheduler, "SessionLocal", TestSession)
    scheduler.scheduled_scraping_job(mode="future")
    assert len(calls) == 1
    start, days, refresh = calls[0]
    assert 31 <= (start - dt.date.today()).days < 180
    assert 1 <= days <= 31
    assert refresh is True
