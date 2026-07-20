"""Revenue Assistant API with Supabase-authenticated, customer-isolated data."""

import csv
import datetime as dt
import io
from contextlib import asynccontextmanager
from urllib.parse import urlparse, urlunparse
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from auth import CurrentUser, require_current_user
from billing import BillingConfigurationError, stripe_billing
from database import Base, SessionLocal, engine, get_db
from pms import PROFILES, get_profile
from scheduler import start_scheduler, stop_scheduler
from scraper import DataCollectionError, ScrapeResult, scraper_service
from settings import OtaSourceRuntime, get_settings

settings = get_settings()


def _seed_demo_data(db: Session) -> None:
    """Create one isolated demo organization only for local sales demonstrations."""
    if settings.environment != "demo" or db.query(models.DBOrganization).first():
        return
    organization = models.DBOrganization(id="demo-organization", name="サンプル施設")
    db.add_all([
        organization,
        models.DBOrganizationMember(organization_id=organization.id, user_id="demo-user", role="owner"),
        models.DBSubscription(organization_id=organization.id, status="active"),
    ])
    facility = models.DBFacility(
        id="demo-facility", organization_id=organization.id, name="サンプル施設",
        address="東京都", base_price=10_000, min_price=5_000, max_price=30_000,
        onboarding_completed_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(facility)
    db.add_all([
        models.DBCompetitor(id="demo-competitor-1", facility_id=facility.id, ota_source_key="rakuten", name="競合旅館A", url="https://travel.rakuten.co.jp/HOTEL/14138/14138.html", canonical_url="https://travel.rakuten.co.jp/HOTEL/14138/14138.html"),
        models.DBCompetitor(id="demo-competitor-2", facility_id=facility.id, ota_source_key="booking", name="競合ホテルB", url="https://www.booking.com/hotel/jp/tokyo-station.ja.html", canonical_url="https://www.booking.com/hotel/jp/tokyo-station.ja.html"),
        models.DBCompetitor(id="demo-competitor-3", facility_id=facility.id, ota_source_key="jalan", name="競合旅館C", url="https://www.jalan.net/yad000000/", canonical_url="https://www.jalan.net/yad000000/"),
    ])
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "production":
        if not settings.supabase_auth_required or not settings.supabase_url or not settings.supabase_publishable_key:
            raise RuntimeError("Production requires SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, and SUPABASE_AUTH_REQUIRED=true")
        if settings.allow_simulated_data:
            raise RuntimeError("ALLOW_SIMULATED_DATA must be false in production")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _seed_demo_data(db)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Revenue Assistant API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "PUT", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key"],
)


def _parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Date must be YYYY-MM-DD") from exc


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def _validate_ota_url(url: str) -> OtaSourceRuntime:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Competitor URL must use HTTPS")
    source = settings.source_for_url(url)
    if source is None:
        raise HTTPException(status_code=422, detail="Only configured OTA domains are allowed")
    if source.status != "approved" or not source.actor_id or not settings.apify_api_token:
        raise HTTPException(status_code=422, detail=f"{source.name} is not available for collection yet")
    return source


def _organization_for_user(db: Session, user: CurrentUser) -> models.DBOrganization | None:
    membership = db.query(models.DBOrganizationMember).filter_by(user_id=user.id).first()
    if membership is None:
        return None
    return db.query(models.DBOrganization).filter_by(id=membership.organization_id).first()


def _require_organization(db: Session, user: CurrentUser, write: bool = False) -> models.DBOrganization:
    membership = db.query(models.DBOrganizationMember).filter_by(user_id=user.id).first()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account setup has not started")
    if write and membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner or administrator can change this facility")
    organization = db.query(models.DBOrganization).filter_by(id=membership.organization_id).first()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


def _subscription_for_organization(db: Session, organization_id: str) -> models.DBSubscription | None:
    return db.query(models.DBSubscription).filter_by(organization_id=organization_id).first()


def _has_active_subscription(subscription: models.DBSubscription | None) -> bool:
    # No free trial is provisioned.  The extra status is retained for safe
    # handling of legacy Stripe data but is never created by this application.
    return settings.demo_bypass_billing or bool(subscription and subscription.status in {"active", "trialing"})


def _ready_facility(db: Session, user: CurrentUser, write: bool = False) -> models.DBFacility:
    organization = _require_organization(db, user, write=write)
    if not _has_active_subscription(_subscription_for_organization(db, organization.id)):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="An active subscription is required")
    facility = db.query(models.DBFacility).filter_by(organization_id=organization.id).first()
    if facility is None or facility.onboarding_completed_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Facility setup has not been completed")
    return facility


def _store_result(db: Session, competitor: models.DBCompetitor, date: dt.date, result: ScrapeResult) -> models.DBCompetitorPrice:
    existing = db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, stay_date=date).first()
    price_jpy = None if result.is_fully_booked else result.price
    collected_at = dt.datetime.now(dt.timezone.utc)
    if existing:
        existing.price_jpy = price_jpy
        existing.is_fully_booked = result.is_fully_booked
        existing.collection_source = result.source
        existing.collected_at = collected_at
        record = existing
    else:
        record = models.DBCompetitorPrice(
            competitor_id=competitor.id,
            stay_date=date,
            price_jpy=price_jpy,
            is_fully_booked=result.is_fully_booked,
            collected_at=collected_at,
            collection_source=result.source,
        )
        db.add(record)
    db.add(models.DBCompetitorPriceObservation(
        competitor_id=competitor.id,
        stay_date=date,
        price_jpy=price_jpy,
        is_fully_booked=result.is_fully_booked,
        collected_at=collected_at,
        collection_source=result.source,
    ))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, stay_date=date).one()
    return record


def _reserve_collection_run(db: Session, competitor: models.DBCompetitor) -> None:
    """Reserve a production Actor invocation before it leaves our system.

    Failed provider requests still consume a slot: retrying indefinitely is not
    compatible with the written daily collection limit.
    """
    if settings.environment != "production":
        return
    collection_day = dt.datetime.now(ZoneInfo("Asia/Tokyo")).date()
    limit = len(settings.daily_sync_hours)
    used = db.query(models.DBCompetitorCollectionRun).filter_by(
        competitor_id=competitor.id, collection_day=collection_day,
    ).count()
    if used >= limit:
        raise DataCollectionError("The approved daily collection limit has been reached")
    db.add(models.DBCompetitorCollectionRun(
        competitor_id=competitor.id,
        collection_day=collection_day,
        slot=used + 1,
        collection_source="apify",
    ))
    try:
        # Commit before calling Apify so a failed call cannot erase its slot.
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DataCollectionError("A concurrent collection already used this daily slot") from exc


def collect_market_data(
    db: Session,
    facility: models.DBFacility,
    start: dt.date,
    days: int,
    *,
    refresh: bool = False,
) -> list[models.CompetitorPrice]:
    competitors = db.query(models.DBCompetitor).filter_by(facility_id=facility.id, is_active=True).all()
    dates = [start + dt.timedelta(days=offset) for offset in range(days)]
    for competitor in competitors:
        dates_to_collect: list[dt.date] = []
        for date in dates:
            existing = db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, stay_date=date).first()
            if refresh or not existing:
                if date < dt.date.today() and not existing:
                    raise HTTPException(status_code=503, detail=f"Market data is unavailable for {competitor.name}")
                dates_to_collect.append(date)
        if not dates_to_collect:
            continue
        try:
            # A dashboard horizon is one approved Actor run per competitor,
            # rather than one run for every stay date.
            _reserve_collection_run(db, competitor)
            results = scraper_service.extract_prices(
                competitor.url, [date.isoformat() for date in dates_to_collect], competitor.id,
            )
            for date in dates_to_collect:
                _store_result(db, competitor, date, results[date.isoformat()])
        except DataCollectionError as exc:
            db.rollback()
            raise HTTPException(status_code=503, detail=f"Market data is unavailable for {competitor.name}") from exc
    db.commit()

    rows: list[models.CompetitorPrice] = []
    for date in dates:
        for competitor in competitors:
            current = db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, stay_date=date).one()
            observations = db.query(models.DBCompetitorPriceObservation).filter_by(
                competitor_id=competitor.id, stay_date=date,
            ).order_by(
                models.DBCompetitorPriceObservation.collected_at.desc(),
                models.DBCompetitorPriceObservation.id.desc(),
            ).limit(2).all()
            source = current.collection_source if current.collection_source in {"apify", "simulation"} else "unknown"
            current_price = current.price_jpy or 0
            previous_price = (observations[1].price_jpy or 0) if len(observations) > 1 else current_price
            rows.append(models.CompetitorPrice(
                date=date.isoformat(), competitor_id=competitor.id, competitor_name=competitor.name or "競合施設",
                price_today=current_price, price_yesterday=previous_price,
                difference=current_price - previous_price,
                is_fully_booked=current.is_fully_booked, source=source,
            ))
    return rows


def create_alerts(market_data: list[models.CompetitorPrice]) -> list[models.Alert]:
    alerts: list[models.Alert] = []
    for item in market_data:
        if item.is_fully_booked:
            message, alert_type = f"{item.date}: {item.competitor_name} が満室です", "sold_out"
        elif item.difference >= 3_000:
            message, alert_type = f"{item.date}: {item.competitor_name} が前日比 ¥{item.difference:,} 値上げしました", "increase"
        elif item.difference <= -3_000:
            message, alert_type = f"{item.date}: {item.competitor_name} が前日比 ¥{abs(item.difference):,} 値下げしました", "decrease"
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


def build_recommendation(db: Session, facility: models.DBFacility, date: dt.date) -> models.MarketRecommendation:
    data = collect_market_data(db, facility, date, 1)
    available = [item for item in data if not item.is_fully_booked]
    if not available:
        raw, reasoning = int(facility.base_price * 1.5), "全競合が満室のため、上限内で強気の価格を提案します。"
    else:
        average = sum(item.price_today for item in available) / len(available)
        increases = [item for item in available if item.difference >= 3_000]
        if increases:
            raw = int(average * 0.95)
            reasoning = "競合の値上げを確認したため、相場を見ながら価格を引き上げます。"
        else:
            raw = facility.base_price
            reasoning = "大きな需給変化がないため、基準価格を提案します。"
    suggested = round(min(max(raw, facility.min_price), facility.max_price) / 100) * 100
    return models.MarketRecommendation(date=date.isoformat(), suggested_price=suggested, suggested_rank=_price_to_rank(suggested), reasoning=reasoning)


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/integrations/status", response_model=models.IntegrationStatus)
def integration_status():
    ota_sources = [
        models.OtaSourceStatus(
            key=source.key, name=source.name, status=source.status,
            actor_configured=bool(settings.apify_api_token and source.actor_id),
        )
        for source in settings.ota_sources()
    ]
    return models.IntegrationStatus(
        environment=settings.environment,
        apify_configured=any(source.actor_configured and source.status == "approved" for source in ota_sources),
        line_messaging_configured=bool(settings.line_channel_access_token and settings.line_user_id),
        stripe_configured=stripe_billing.configured,
        simulation_enabled=settings.allow_simulated_data,
        ota_sources=ota_sources,
    )


@app.get("/onboarding/status", response_model=models.OnboardingStatus)
def onboarding_status(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _organization_for_user(db, user)
    if organization is None:
        return models.OnboardingStatus()
    subscription = _subscription_for_organization(db, organization.id)
    facility = db.query(models.DBFacility).filter_by(organization_id=organization.id).first()
    complete = bool(facility and facility.onboarding_completed_at and _has_active_subscription(subscription))
    return models.OnboardingStatus(
        subscription_status="active" if settings.demo_bypass_billing else (subscription.status if subscription else "inactive"),
        onboarding_complete=complete,
        facility=models.Facility.model_validate(facility) if facility else None,
    )


@app.post("/onboarding", response_model=models.Facility)
def complete_onboarding(payload: models.OnboardingRequest, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _require_organization(db, user, write=True)
    if not _has_active_subscription(_subscription_for_organization(db, organization.id)):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="An active subscription is required before setup")
    sources = [_validate_ota_url(item.url) for item in payload.competitors]
    facility = db.query(models.DBFacility).filter_by(organization_id=organization.id).first()
    if facility is None:
        facility = models.DBFacility(organization_id=organization.id)
        db.add(facility)
    facility.name = payload.facility_name
    facility.address = payload.address
    facility.base_price = payload.base_price
    facility.min_price = payload.min_price
    facility.max_price = payload.max_price
    facility.onboarding_completed_at = dt.datetime.now(dt.timezone.utc)
    db.flush()
    db.query(models.DBCompetitor).filter_by(facility_id=facility.id).delete()
    for item, source in zip(payload.competitors, sources, strict=True):
        db.add(models.DBCompetitor(
            facility_id=facility.id, ota_source_key=source.key, name=item.name,
            url=item.url, canonical_url=_canonical_url(item.url), is_active=True,
        ))
    db.commit()
    db.refresh(facility)
    return facility


@app.get("/facility", response_model=models.Facility)
def get_facility(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    return _ready_facility(db, user)


@app.put("/facility", response_model=models.Facility)
def update_facility(payload: models.FacilityUpdate, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    facility = _ready_facility(db, user, write=True)
    facility.min_price, facility.max_price = payload.min_price, payload.max_price
    db.commit()
    db.refresh(facility)
    return facility


@app.get("/competitors", response_model=list[models.Competitor])
def get_competitors(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    facility = _ready_facility(db, user)
    return db.query(models.DBCompetitor).filter_by(facility_id=facility.id, is_active=True).all()


@app.put("/competitors/{comp_id}", response_model=models.Competitor)
def update_competitor(comp_id: str, payload: models.CompetitorUpdate, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    facility = _ready_facility(db, user, write=True)
    source = _validate_ota_url(payload.url)
    competitor = db.query(models.DBCompetitor).filter_by(id=comp_id, facility_id=facility.id).first()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    competitor.name, competitor.url = payload.name, payload.url
    competitor.canonical_url, competitor.ota_source_key = _canonical_url(payload.url), source.key
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="This competitor URL is already registered") from exc
    db.refresh(competitor)
    return competitor


@app.get("/market_data", response_model=list[models.CompetitorPrice])
def get_market_data(start_date: str, days: int = Query(default=7, ge=1, le=31), user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    return collect_market_data(db, _ready_facility(db, user), _parse_date(start_date), days)


@app.get("/alerts", response_model=list[models.Alert])
def get_alerts(start_date: str, days: int = Query(default=7, ge=1, le=31), user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    return create_alerts(collect_market_data(db, _ready_facility(db, user), _parse_date(start_date), days))


@app.get("/recommendation", response_model=models.MarketRecommendation)
def get_recommendation(date: str, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    return build_recommendation(db, _ready_facility(db, user), _parse_date(date))


@app.get("/pms/profiles", response_model=list[models.PmsProfile])
def get_pms_profiles(user: CurrentUser = Depends(require_current_user)):
    return [models.PmsProfile(id=item.id, name=item.name, verified=item.verified, description=item.description) for item in PROFILES.values()]


@app.get("/billing/status", response_model=models.BillingStatus)
def billing_status(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _organization_for_user(db, user)
    subscription = _subscription_for_organization(db, organization.id) if organization else None
    return models.BillingStatus(configured=stripe_billing.configured, subscription_status=subscription.status if subscription else "inactive")


@app.post("/billing/checkout", response_model=models.CheckoutSession)
def create_checkout(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _organization_for_user(db, user)
    if organization is None:
        organization = models.DBOrganization(name=f"{user.email.split('@')[0]} の事業者")
        db.add(organization)
        db.flush()
        db.add(models.DBOrganizationMember(organization_id=organization.id, user_id=user.id, role="owner"))
        db.commit()
    subscription = _subscription_for_organization(db, organization.id)
    if _has_active_subscription(subscription):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subscription is already active")
    try:
        return models.CheckoutSession(checkout_url=stripe_billing.create_checkout(organization.id, user.email))
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Stripe Billing is not configured") from exc


@app.post("/billing/portal", response_model=models.CheckoutSession)
def create_portal(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _require_organization(db, user, write=True)
    subscription = _subscription_for_organization(db, organization.id)
    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No Stripe customer is linked to this organization")
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

    organization_id = data.get("metadata", {}).get("organization_id") or data.get("client_reference_id")
    customer_id = data.get("customer")
    subscription_id = data.get("subscription") if event_type == "checkout.session.completed" else data.get("id")
    subscription_status = "active" if event_type == "checkout.session.completed" else data.get("status", "inactive")
    price_id = settings.stripe_price_id_pro
    if event_type != "checkout.session.completed":
        items = data.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id", price_id)
    if not subscription_id:
        return {"received": True}

    with SessionLocal() as db:
        record = db.query(models.DBSubscription).filter_by(stripe_subscription_id=subscription_id).first()
        if record is None and organization_id:
            record = db.query(models.DBSubscription).filter_by(organization_id=organization_id).first()
        if record is None and organization_id:
            record = models.DBSubscription(organization_id=organization_id)
            db.add(record)
        if record:
            record.stripe_customer_id = customer_id or record.stripe_customer_id
            record.stripe_subscription_id = subscription_id
            record.status = subscription_status
            record.stripe_price_id = price_id
            current_period_end = data.get("current_period_end")
            if isinstance(current_period_end, (int, float)):
                record.current_period_end = dt.datetime.fromtimestamp(current_period_end, tz=dt.timezone.utc)
            db.commit()
    return {"received": True}


@app.get("/export_csv")
def export_csv(start_date: str, days: int = Query(default=7, ge=1, le=31), profile: str = "generic", user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    try:
        export_profile = get_profile(profile)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    start = _parse_date(start_date)
    facility = _ready_facility(db, user)
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(export_profile.headers)
    for offset in range(days):
        date = start + dt.timedelta(days=offset)
        recommendation = build_recommendation(db, facility, date)
        writer.writerow([date.isoformat(), f"facility-{facility.id}", "standard", "standard", recommendation.suggested_rank, recommendation.suggested_price])
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=revenue_{profile}_{start.isoformat()}.csv"},
    )
