"""Revenue Assistant API: safe MVP foundation for a pilot deployment."""

import csv
import datetime as dt
import io
import secrets
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from billing import BillingConfigurationError, stripe_billing
from database import Base, SessionLocal, engine, get_db, is_sqlite
import models
from pms import PROFILES, get_profile
from scheduler import start_scheduler, stop_scheduler
from scraper import DataCollectionError, ScrapeResult, scraper_service
from settings import get_settings

settings = get_settings()
ALLOWED_OTA_HOSTS = ("booking.com", "airbnb.com", "jalan.net", "rakuten.co.jp")


def _migrate_local_sqlite() -> None:
    """Small compatibility migration for existing demo databases.

    Production deployments must apply a reviewed migration through their normal
    release process; this helper intentionally runs only for local SQLite.
    """
    if not is_sqlite:
        return
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(competitor_prices)"))}
        if columns and "source" not in columns:
            connection.execute(text("ALTER TABLE competitor_prices ADD COLUMN source VARCHAR DEFAULT 'unknown'"))
        try:
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_competitor_price_date_idx ON competitor_prices (competitor_id, date)"))
        except IntegrityError:
            # Historical demo rows can contain duplicates.  Keep the newest row,
            # then enforce the invariant for all future collection runs.
            connection.execute(text("DELETE FROM competitor_prices WHERE id NOT IN (SELECT MAX(id) FROM competitor_prices GROUP BY competitor_id, date)"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_competitor_price_date_idx ON competitor_prices (competitor_id, date)"))


def _seed_demo_data(db: Session) -> None:
    if db.query(models.DBFacility).first():
        return
    db.add(models.DBFacility(id=1, name="サンプル施設", base_price=10_000, min_price=5_000, max_price=30_000))
    db.add_all([
        models.DBCompetitor(id=1, name="競合A", url="https://travel.rakuten.co.jp/HOTEL/14138/14138.html"),
        models.DBCompetitor(id=2, name="競合B", url="https://www.booking.com/hotel/jp/tokyo-station.ja.html"),
        models.DBCompetitor(id=3, name="競合C", url="https://www.jalan.net/yad000000/"),
    ])
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "production" and not settings.admin_api_key:
        raise RuntimeError("ADMIN_API_KEY is required in production")
    Base.metadata.create_all(bind=engine)
    _migrate_local_sqlite()
    with SessionLocal() as db:
        _seed_demo_data(db)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Revenue Assistant API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "PUT", "POST"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """Protect mutations when an admin key has been configured.

    Demo mode permits unauthenticated local changes.  Production refuses to
    start without the key, making an accidental public write API impossible.
    """
    if settings.admin_api_key and not secrets.compare_digest(x_admin_key or "", settings.admin_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


def _parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Date must be YYYY-MM-DD") from exc


def _validate_ota_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        raise HTTPException(status_code=422, detail="Competitor URL must use HTTPS")
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in ALLOWED_OTA_HOSTS):
        raise HTTPException(status_code=422, detail="Only configured OTA domains are allowed")


def _store_result(db: Session, competitor: models.DBCompetitor, date: dt.date, result: ScrapeResult) -> models.DBCompetitorPrice:
    date_string = date.isoformat()
    existing = db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, date=date_string).first()
    if existing:
        return existing
    record = models.DBCompetitorPrice(
        date=date_string,
        competitor_id=competitor.id,
        price=result.price,
        is_fully_booked=result.is_fully_booked,
        scraped_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        source=result.source,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, date=date_string).one()
    return record


def collect_market_data(db: Session, start: dt.date, days: int) -> list[models.CompetitorPrice]:
    competitors = db.query(models.DBCompetitor).all()
    for offset in range(days):
        date = start + dt.timedelta(days=offset)
        previous_date = date - dt.timedelta(days=1)
        for competitor in competitors:
            try:
                if not db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, date=date.isoformat()).first():
                    _store_result(db, competitor, date, scraper_service.extract_price(competitor.url, date.isoformat(), competitor.id))
                if not db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, date=previous_date.isoformat()).first():
                    _store_result(db, competitor, previous_date, scraper_service.extract_price(competitor.url, previous_date.isoformat(), competitor.id))
            except DataCollectionError as exc:
                db.rollback()
                raise HTTPException(status_code=503, detail=f"Market data is unavailable for {competitor.name}") from exc
    db.commit()

    rows: list[models.CompetitorPrice] = []
    for offset in range(days):
        date = start + dt.timedelta(days=offset)
        previous_date = date - dt.timedelta(days=1)
        for competitor in competitors:
            current = db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, date=date.isoformat()).one()
            previous = db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, date=previous_date.isoformat()).one()
            source = current.source if current.source in {"apify", "simulation"} else "unknown"
            rows.append(models.CompetitorPrice(
                date=date.isoformat(), competitor_id=competitor.id, competitor_name=competitor.name,
                price_today=current.price, price_yesterday=previous.price,
                difference=current.price - previous.price,
                is_fully_booked=current.is_fully_booked, source=source,
            ))
    return rows


def create_alerts(market_data: list[models.CompetitorPrice]) -> list[models.Alert]:
    alerts: list[models.Alert] = []
    for item in market_data:
        if item.is_fully_booked:
            message, alert_type = f"{item.date}: {item.competitor_name} が満室です。", "sold_out"
        elif item.difference >= 3_000:
            message, alert_type = f"{item.date}: {item.competitor_name} が前日比 ¥{item.difference:,} 値上げしました。", "increase"
        elif item.difference <= -3_000:
            message, alert_type = f"{item.date}: {item.competitor_name} が前日比 ¥{abs(item.difference):,} 値下げしました。", "decrease"
        else:
            continue
        alerts.append(models.Alert(id=len(alerts) + 1, date=item.date, message=message, type=alert_type))
    return alerts


def _price_to_rank(price: int) -> str:
    if price >= 20_000:
        return "A"
    if price >= 15_000:
        return "B"
    if price >= 10_000:
        return "C"
    return "D"


def build_recommendation(db: Session, date: dt.date) -> models.MarketRecommendation:
    facility = db.query(models.DBFacility).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    data = collect_market_data(db, date, 1)
    available = [item for item in data if not item.is_fully_booked]
    if not available:
        raw, reasoning = int(facility.base_price * 1.5), "全競合が満室のため、上限内で需要の強い価格を提案します。"
    else:
        average = sum(item.price_today for item in available) / len(available)
        increases = [item for item in available if item.difference >= 3_000]
        if increases:
            raw = int(average * 0.95)
            reasoning = "競合の大幅値上げを検知したため、競争力を維持しつつ価格を引き上げます。"
        else:
            raw = facility.base_price
            reasoning = "大きな市場変動がないため、基準価格を維持します。"
    suggested = round(min(max(raw, facility.min_price), facility.max_price) / 100) * 100
    return models.MarketRecommendation(date=date.isoformat(), suggested_price=suggested, suggested_rank=_price_to_rank(suggested), reasoning=reasoning)


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/integrations/status", response_model=models.IntegrationStatus)
def integration_status():
    actors = (settings.apify_actor_booking, settings.apify_actor_airbnb, settings.apify_actor_jalan, settings.apify_actor_rakuten)
    return models.IntegrationStatus(
        environment=settings.environment,
        apify_configured=bool(settings.apify_api_token and any(actors)),
        line_messaging_configured=bool(settings.line_channel_access_token and settings.line_user_id),
        stripe_configured=stripe_billing.configured,
        simulation_enabled=settings.allow_simulated_data,
    )


@app.get("/facility", response_model=models.Facility)
def get_facility(db: Session = Depends(get_db)):
    facility = db.query(models.DBFacility).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


@app.put("/facility", response_model=models.Facility, dependencies=[Depends(require_admin)])
def update_facility(payload: models.FacilityUpdate, db: Session = Depends(get_db)):
    facility = db.query(models.DBFacility).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    facility.min_price, facility.max_price = payload.min_price, payload.max_price
    db.commit()
    db.refresh(facility)
    return facility


@app.get("/competitors", response_model=list[models.Competitor])
def get_competitors(db: Session = Depends(get_db)):
    return db.query(models.DBCompetitor).all()


@app.put("/competitors/{comp_id}", response_model=models.Competitor, dependencies=[Depends(require_admin)])
def update_competitor(comp_id: int, payload: models.CompetitorUpdate, db: Session = Depends(get_db)):
    _validate_ota_url(payload.url)
    competitor = db.query(models.DBCompetitor).filter_by(id=comp_id).first()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    competitor.name, competitor.url = payload.name, payload.url
    db.commit()
    db.refresh(competitor)
    return competitor


@app.get("/market_data", response_model=list[models.CompetitorPrice])
def get_market_data(start_date: str, days: int = Query(default=7, ge=1, le=31), db: Session = Depends(get_db)):
    return collect_market_data(db, _parse_date(start_date), days)


@app.get("/alerts", response_model=list[models.Alert])
def get_alerts(start_date: str, days: int = Query(default=7, ge=1, le=31), db: Session = Depends(get_db)):
    return create_alerts(collect_market_data(db, _parse_date(start_date), days))


@app.get("/recommendation", response_model=models.MarketRecommendation)
def get_recommendation(date: str, db: Session = Depends(get_db)):
    return build_recommendation(db, _parse_date(date))


@app.get("/pms/profiles", response_model=list[models.PmsProfile])
def get_pms_profiles():
    return [models.PmsProfile(id=item.id, name=item.name, verified=item.verified, description=item.description) for item in PROFILES.values()]


@app.get("/billing/status", response_model=models.BillingStatus, dependencies=[Depends(require_admin)])
def billing_status(db: Session = Depends(get_db)):
    subscription = db.query(models.DBSubscription).first()
    return models.BillingStatus(
        configured=stripe_billing.configured,
        subscription_status=subscription.status if subscription else "inactive",
    )


@app.post("/billing/checkout", response_model=models.CheckoutSession, dependencies=[Depends(require_admin)])
def create_checkout(db: Session = Depends(get_db)):
    facility = db.query(models.DBFacility).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    try:
        return models.CheckoutSession(checkout_url=stripe_billing.create_checkout(facility.id))
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Stripe Billing is not configured") from exc


@app.post("/billing/portal", response_model=models.CheckoutSession, dependencies=[Depends(require_admin)])
def create_portal(db: Session = Depends(get_db)):
    subscription = db.query(models.DBSubscription).first()
    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No Stripe customer is linked to this facility")
    try:
        return models.CheckoutSession(checkout_url=stripe_billing.create_portal(subscription.stripe_customer_id))
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Stripe Billing is not configured") from exc


@app.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None)):
    try:
        event = stripe_billing.verify_event(await request.body(), stripe_signature)
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook") from exc

    event_type = event["type"]
    data = event["data"]["object"]
    if event_type not in {"checkout.session.completed", "customer.subscription.updated", "customer.subscription.deleted"}:
        return {"received": True}

    facility_id = None
    customer_id = None
    subscription_id = None
    subscription_status = "inactive"
    price_id = settings.stripe_price_id_pro
    if event_type == "checkout.session.completed":
        facility_id = int(data.get("metadata", {}).get("facility_id") or data.get("client_reference_id") or 0)
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        subscription_status = "active"
    else:
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        subscription_status = data.get("status", "inactive")
        items = data.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id", price_id)

    if not subscription_id:
        return {"received": True}
    with SessionLocal() as db:
        record = db.query(models.DBSubscription).filter_by(stripe_subscription_id=subscription_id).first()
        if not record and facility_id:
            record = db.query(models.DBSubscription).filter_by(facility_id=facility_id).first()
        if record is None and facility_id:
            record = models.DBSubscription(facility_id=facility_id, updated_at=dt.datetime.now(dt.timezone.utc).isoformat())
            db.add(record)
        if record:
            record.stripe_customer_id = customer_id or record.stripe_customer_id
            record.stripe_subscription_id = subscription_id
            record.status = subscription_status
            record.price_id = price_id
            record.updated_at = dt.datetime.now(dt.timezone.utc).isoformat()
            db.commit()
    return {"received": True}


@app.get("/export_csv")
def export_csv(start_date: str, days: int = Query(default=7, ge=1, le=31), profile: str = "generic", db: Session = Depends(get_db)):
    try:
        export_profile = get_profile(profile)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    start = _parse_date(start_date)
    facility = db.query(models.DBFacility).first()
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(export_profile.headers)
    for offset in range(days):
        date = start + dt.timedelta(days=offset)
        recommendation = build_recommendation(db, date)
        writer.writerow([date.isoformat(), f"facility-{facility.id}", "standard", "standard", recommendation.suggested_rank, recommendation.suggested_price])
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=revenue_{profile}_{start.isoformat()}.csv"},
    )
