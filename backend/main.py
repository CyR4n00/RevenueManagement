"""レベナビ API with Supabase-authenticated, customer-isolated data."""

import datetime as dt
import json
from pathlib import Path
from contextlib import asynccontextmanager
from urllib.parse import urlparse, urlunparse
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from auth import CurrentUser, require_current_user
from billing import BillingConfigurationError, stripe_billing
from database import Base, SessionLocal, engine, get_db
from notifier import notifier_service
from scheduler import start_scheduler, stop_scheduler
from scraper import DataCollectionError, ScrapeResult, scraper_service
from settings import OtaSourceRuntime, get_settings

settings = get_settings()


def _default_rate_rank_values(minimum: int, maximum: int) -> list[tuple[str, int]]:
    """Build a backwards-compatible A-D ladder for facilities created before rank pricing."""
    span = max(maximum - minimum, 3)
    return [
        ("A", maximum),
        ("B", minimum + round(span * 2 / 3)),
        ("C", minimum + round(span / 3)),
        ("D", minimum),
    ]


def _ensure_rate_ranks(db: Session, facility: models.DBFacility) -> None:
    if facility.rate_ranks:
        return
    for order, (label, price) in enumerate(_default_rate_rank_values(facility.min_price, facility.max_price)):
        db.add(models.DBRateRank(facility_id=facility.id, label=label, price_jpy=price, sort_order=order))


def _replace_rate_ranks(db: Session, facility: models.DBFacility, ranks: list[models.RateRankInput]) -> None:
    db.query(models.DBRateRank).filter_by(facility_id=facility.id).delete(synchronize_session=False)
    for order, rank in enumerate(ranks):
        db.add(models.DBRateRank(
            facility_id=facility.id, label=rank.label, price_jpy=rank.price_jpy, sort_order=order,
        ))


def _rate_rank_values(facility: models.DBFacility) -> list[tuple[str, int]]:
    ranks = sorted(facility.rate_ranks, key=lambda item: item.sort_order)
    return [(rank.label, rank.price_jpy) for rank in ranks] or _default_rate_rank_values(
        facility.min_price, facility.max_price
    )


def _seed_demo_data(db: Session) -> None:
    """Create one isolated demo organization only for local sales demonstrations."""
    if settings.environment != "demo" or db.query(models.DBOrganization).first():
        return
    organization = models.DBOrganization(
        id="demo-organization", name="サンプル施設", notification_email="demo@example.invalid",
    )
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


def _ensure_sqlite_compatibility_columns() -> None:
    """Bring an existing local demo DB forward without replacing its data."""
    if engine.dialect.name != "sqlite":
        return
    additions = {
        "organizations": (
            ("notification_email", "VARCHAR(320)"),
            ("email_notifications_enabled", "BOOLEAN NOT NULL DEFAULT 1"),
        ),
        "competitor_prices": (
            ("availability_status", "VARCHAR(16) NOT NULL DEFAULT 'unknown'"),
            ("remaining_rooms", "INTEGER"),
            ("availability_source", "VARCHAR(20) NOT NULL DEFAULT 'inferred'"),
        ),
        "competitor_price_observations": (
            ("availability_status", "VARCHAR(16) NOT NULL DEFAULT 'unknown'"),
            ("remaining_rooms", "INTEGER"),
            ("availability_source", "VARCHAR(20) NOT NULL DEFAULT 'inferred'"),
        ),
        "competitor_collection_runs": (
            ("completed_at", "DATETIME"),
            ("status", "VARCHAR(16) NOT NULL DEFAULT 'started'"),
            ("records_collected", "INTEGER NOT NULL DEFAULT 0"),
            ("error_message", "TEXT"),
        ),
    }
    with engine.begin() as connection:
        schema = inspect(connection)
        for table_name, columns in additions.items():
            if not schema.has_table(table_name):
                continue
            existing = {column["name"] for column in schema.get_columns(table_name)}
            for column_name, definition in columns:
                if column_name not in existing:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
            if table_name in {"competitor_prices", "competitor_price_observations"}:
                connection.execute(text(
                    f"UPDATE {table_name} SET availability_status = "
                    "CASE WHEN is_fully_booked = 1 THEN 'sold_out' "
                    "WHEN price_jpy IS NOT NULL THEN 'available' ELSE 'unknown' END "
                    "WHERE availability_status = 'unknown'"
                ))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "production":
        if not settings.supabase_auth_required or not settings.supabase_url or not settings.supabase_publishable_key:
            raise RuntimeError("Production requires SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, and SUPABASE_AUTH_REQUIRED=true")
        if settings.allow_simulated_data:
            raise RuntimeError("ALLOW_SIMULATED_DATA must be false in production")
        if settings.demo_bypass_billing:
            raise RuntimeError("DEMO_BYPASS_BILLING must be false in production")
        if engine.dialect.name != "postgresql":
            raise RuntimeError("Production requires a PostgreSQL DATABASE_URL; SQLite is demo-only")
    if settings.environment == "demo":
        Base.metadata.create_all(bind=engine)
        _ensure_sqlite_compatibility_columns()
    with SessionLocal() as db:
        _seed_demo_data(db)
        if settings.environment == "demo":
            for facility in db.query(models.DBFacility).all():
                _ensure_rate_ranks(db, facility)
            db.commit()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="レベナビ API", version="2.1.0", lifespan=lifespan)
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
        raise HTTPException(status_code=422, detail="日付の形式が正しくありません") from exc


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def _validate_ota_url(url: str) -> OtaSourceRuntime:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(status_code=422, detail="予約サイトのURLはhttps://から始まるものを入力してください")
    source = settings.source_for_url(url)
    if source is None:
        raise HTTPException(status_code=422, detail="現在対応している予約サイトのURLを入力してください")
    if source.status != "approved" or not source.actor_id or not settings.apify_api_token:
        raise HTTPException(status_code=422, detail=f"{source.name}は現在データ取得の準備中です")
    return source


def _organization_for_user(db: Session, user: CurrentUser) -> models.DBOrganization | None:
    membership = db.query(models.DBOrganizationMember).filter_by(user_id=user.id).first()
    if membership is None:
        return None
    return db.query(models.DBOrganization).filter_by(id=membership.organization_id).first()


def require_operator(user: CurrentUser = Depends(require_current_user)) -> CurrentUser:
    """Allow only Supabase-verified operator emails configured by the platform."""
    if user.email.strip().lower() not in settings.operator_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="運営者権限が必要です")
    return user


def _require_organization(db: Session, user: CurrentUser, write: bool = False) -> models.DBOrganization:
    membership = db.query(models.DBOrganizationMember).filter_by(user_id=user.id).first()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="利用開始の設定がまだ始まっていません")
    if write and membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="この設定を変更できる権限がありません")
    organization = db.query(models.DBOrganization).filter_by(id=membership.organization_id).first()
    if organization is None:
        raise HTTPException(status_code=404, detail="施設の契約情報が見つかりませんでした")
    return organization


def _subscription_for_organization(db: Session, organization_id: str) -> models.DBSubscription | None:
    return db.query(models.DBSubscription).filter_by(organization_id=organization_id).first()


def _has_active_subscription(subscription: models.DBSubscription | None) -> bool:
    # No free trial is provisioned.  The extra status is retained for safe
    # handling of legacy Stripe data but is never created by this application.
    if settings.demo_bypass_billing:
        return True
    if not subscription or subscription.status not in {"active", "trialing"}:
        return False
    if subscription.current_period_end is None:
        return True
    period_end = subscription.current_period_end
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=dt.timezone.utc)
    return period_end > dt.datetime.now(dt.timezone.utc)


def _subscription_plan(subscription: models.DBSubscription | None) -> tuple[str, int]:
    """Return the server-authoritative dashboard horizon entitlement."""
    if settings.demo_bypass_billing:
        return "upgrade", 365
    if (
        subscription
        and settings.stripe_price_id_upgrade
        and subscription.stripe_price_id == settings.stripe_price_id_upgrade
    ):
        return "upgrade", 365
    return "standard", 180


def _enforce_horizon(db: Session, user: CurrentUser, days: int) -> None:
    organization = _require_organization(db, user)
    _, maximum = _subscription_plan(_subscription_for_organization(db, organization.id))
    if days > maximum:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"現在のプランで表示できる期間は最大{maximum}日です",
        )


def _ready_facility(db: Session, user: CurrentUser, write: bool = False) -> models.DBFacility:
    organization = _require_organization(db, user, write=write)
    if not _has_active_subscription(_subscription_for_organization(db, organization.id)):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="利用を続けるには、ご契約の確認が必要です")
    facility = db.query(models.DBFacility).filter_by(organization_id=organization.id).first()
    if facility is None or facility.onboarding_completed_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="施設の初期設定が完了していません")
    return facility


def _store_result(db: Session, competitor: models.DBCompetitor, date: dt.date, result: ScrapeResult) -> models.DBCompetitorPrice:
    existing = db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, stay_date=date).first()
    price_jpy = None if result.is_fully_booked else result.price
    collected_at = dt.datetime.now(dt.timezone.utc)
    if existing:
        existing.price_jpy = price_jpy
        existing.is_fully_booked = result.is_fully_booked
        existing.availability_status = result.availability_status
        existing.remaining_rooms = result.remaining_rooms
        existing.availability_source = result.availability_source
        existing.collection_source = result.source
        existing.collected_at = collected_at
        record = existing
    else:
        record = models.DBCompetitorPrice(
            competitor_id=competitor.id,
            stay_date=date,
            price_jpy=price_jpy,
            is_fully_booked=result.is_fully_booked,
            availability_status=result.availability_status,
            remaining_rooms=result.remaining_rooms,
            availability_source=result.availability_source,
            collected_at=collected_at,
            collection_source=result.source,
        )
        db.add(record)
    db.add(models.DBCompetitorPriceObservation(
        competitor_id=competitor.id,
        stay_date=date,
        price_jpy=price_jpy,
        is_fully_booked=result.is_fully_booked,
        availability_status=result.availability_status,
        remaining_rooms=result.remaining_rooms,
        availability_source=result.availability_source,
        collected_at=collected_at,
        collection_source=result.source,
    ))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, stay_date=date).one()
    return record


def _reserve_collection_run(db: Session, competitor: models.DBCompetitor) -> int | None:
    """Reserve a production Actor invocation before it leaves our system.

    Failed provider requests still consume a slot: retrying indefinitely is not
    compatible with the written daily collection limit.
    """
    if settings.environment != "production":
        return None
    collection_day = dt.datetime.now(ZoneInfo("Asia/Tokyo")).date()
    if settings.apify_monthly_run_limit:
        month_start = collection_day.replace(day=1)
        monthly_used = db.query(models.DBCompetitorCollectionRun).filter(
            models.DBCompetitorCollectionRun.collection_day >= month_start,
        ).count()
        if monthly_used >= settings.apify_monthly_run_limit:
            raise DataCollectionError("The configured monthly Apify run limit has been reached")
    limit = len(settings.daily_sync_hours)
    used = db.query(models.DBCompetitorCollectionRun).filter_by(
        competitor_id=competitor.id, collection_day=collection_day,
    ).count()
    if used >= limit:
        raise DataCollectionError("The approved daily collection limit has been reached")
    run = models.DBCompetitorCollectionRun(
        competitor_id=competitor.id,
        collection_day=collection_day,
        slot=used + 1,
        collection_source="apify",
    )
    db.add(run)
    try:
        # Commit before calling Apify so a failed call cannot erase its slot.
        db.flush()
        run_id = run.id
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DataCollectionError("A concurrent collection already used this daily slot") from exc
    return run_id


def _finish_collection_run(
    db: Session,
    run_id: int | None,
    *,
    run_status: str,
    records_collected: int = 0,
    error_message: str | None = None,
) -> None:
    if run_id is None:
        return
    run = db.query(models.DBCompetitorCollectionRun).filter_by(id=run_id).one_or_none()
    if run is None:
        return
    run.status = run_status
    run.completed_at = dt.datetime.now(dt.timezone.utc)
    run.records_collected = records_collected
    run.error_message = error_message[:1000] if error_message else None
    db.commit()


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
                    raise HTTPException(status_code=503, detail=f"{competitor.name}の最新データを取得できませんでした")
                dates_to_collect.append(date)
        if not dates_to_collect:
            continue
        run_id: int | None = None
        try:
            # A dashboard horizon is one approved Actor run per competitor,
            # rather than one run for every stay date.
            run_id = _reserve_collection_run(db, competitor)
            results = scraper_service.extract_prices(
                competitor.url, [date.isoformat() for date in dates_to_collect], competitor.id,
            )
            for date in dates_to_collect:
                result = results.get(date.isoformat())
                if result is not None:
                    _store_result(db, competitor, date, result)
            _finish_collection_run(
                db, run_id, run_status="succeeded", records_collected=len(results),
            )
        except DataCollectionError as exc:
            db.rollback()
            _finish_collection_run(
                db, run_id, run_status="failed", error_message=str(exc),
            )
            raise HTTPException(status_code=503, detail=f"{competitor.name}の最新データを取得できませんでした") from exc
    db.commit()

    rows: list[models.CompetitorPrice] = []
    for date in dates:
        for competitor in competitors:
            current = db.query(models.DBCompetitorPrice).filter_by(competitor_id=competitor.id, stay_date=date).one_or_none()
            if current is None:
                continue
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
                availability_status=current.availability_status,
                remaining_rooms=current.remaining_rooms,
                availability_source=current.availability_source,
            ))
    return rows


def read_cached_market_data(
    db: Session,
    facility: models.DBFacility,
    start: dt.date,
    days: int,
    comparison_days: int = 1,
) -> list[models.CompetitorPrice]:
    """Read stored market data without starting an OTA collection."""
    if comparison_days not in {1, 7, 30}:
        raise HTTPException(status_code=422, detail="比較期間は前日・先週・先月から選んでください")
    competitors = db.query(models.DBCompetitor).filter_by(facility_id=facility.id, is_active=True).all()
    comparison_cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=comparison_days)
    comparison_floor = comparison_cutoff - dt.timedelta(days=1)
    comparison_ceiling = comparison_cutoff + dt.timedelta(days=1)
    end = start + dt.timedelta(days=days)
    competitor_ids = [competitor.id for competitor in competitors]
    current_by_key = {
        (item.competitor_id, item.stay_date): item
        for item in db.query(models.DBCompetitorPrice).filter(
            models.DBCompetitorPrice.competitor_id.in_(competitor_ids),
            models.DBCompetitorPrice.stay_date >= start,
            models.DBCompetitorPrice.stay_date < end,
        ).all()
    } if competitor_ids else {}
    historical_by_key: dict[tuple[str, dt.date], models.DBCompetitorPriceObservation] = {}
    if competitor_ids:
        historical_rows = db.query(models.DBCompetitorPriceObservation).filter(
            models.DBCompetitorPriceObservation.competitor_id.in_(competitor_ids),
            models.DBCompetitorPriceObservation.stay_date >= start,
            models.DBCompetitorPriceObservation.stay_date < end,
            models.DBCompetitorPriceObservation.collected_at <= comparison_ceiling,
            models.DBCompetitorPriceObservation.collected_at >= comparison_floor,
        ).order_by(
            models.DBCompetitorPriceObservation.collected_at.asc(),
            models.DBCompetitorPriceObservation.id.asc(),
        ).all()
        for item in historical_rows:
            key = (item.competitor_id, item.stay_date)
            selected = historical_by_key.get(key)
            item_time = item.collected_at.replace(tzinfo=dt.timezone.utc) if item.collected_at.tzinfo is None else item.collected_at
            selected_time = None if selected is None else (
                selected.collected_at.replace(tzinfo=dt.timezone.utc)
                if selected.collected_at.tzinfo is None else selected.collected_at
            )
            if selected is None or abs(item_time - comparison_cutoff) < abs(selected_time - comparison_cutoff):
                historical_by_key[key] = item
    rows: list[models.CompetitorPrice] = []
    for offset in range(days):
        date = start + dt.timedelta(days=offset)
        for competitor in competitors:
            key = (competitor.id, date)
            current = current_by_key.get(key)
            if current is None:
                continue
            historical = historical_by_key.get(key)
            source = current.collection_source if current.collection_source in {"apify", "simulation"} else "unknown"
            current_price = current.price_jpy or 0
            previous_price = (historical.price_jpy or 0) if historical else current_price
            difference = current_price - previous_price if historical and not current.is_fully_booked and not historical.is_fully_booked else 0
            rows.append(models.CompetitorPrice(
                date=date.isoformat(), competitor_id=competitor.id, competitor_name=competitor.name or "競合施設",
                price_today=current_price, price_yesterday=previous_price,
                difference=difference, comparison_available=historical is not None,
                comparison_days=comparison_days,
                was_fully_booked=historical.is_fully_booked if historical else None,
                is_fully_booked=current.is_fully_booked, source=source,
                availability_status=current.availability_status,
                remaining_rooms=current.remaining_rooms,
                availability_source=current.availability_source,
            ))
    return rows


def create_alerts(market_data: list[models.CompetitorPrice]) -> list[models.Alert]:
    alerts: list[models.Alert] = []
    for item in market_data:
        if item.is_fully_booked:
            message, alert_type = f"{item.date}: {item.competitor_name} が満室です", "sold_out"
        elif item.comparison_available and item.difference >= 3_000:
            label = {1: "前日比", 7: "先週比", 30: "先月比"}[item.comparison_days]
            message, alert_type = f"{item.date}: {item.competitor_name} が{label} ¥{item.difference:,} 値上げしました", "increase"
        elif item.comparison_available and item.difference <= -3_000:
            label = {1: "前日比", 7: "先週比", 30: "先月比"}[item.comparison_days]
            message, alert_type = f"{item.date}: {item.competitor_name} が{label} ¥{abs(item.difference):,} 値下げしました", "decrease"
        else:
            continue
        alerts.append(models.Alert(id=len(alerts) + 1, date=item.date, message=message, type=alert_type))
    return alerts


def _closest_rate_rank(facility: models.DBFacility, target_price: int) -> tuple[str, int]:
    """Select the customer-defined rank closest to the guarded market target."""
    ranks = _rate_rank_values(facility)
    return min(ranks, key=lambda item: (abs(item[1] - target_price), item[0]))


def build_recommendation(
    db: Session,
    facility: models.DBFacility,
    date: dt.date,
    market_data: list[models.CompetitorPrice] | None = None,
) -> models.MarketRecommendation:
    data = market_data if market_data is not None else collect_market_data(db, facility, date, 1)
    data = [item for item in data if item.date == date.isoformat()]
    available = [item for item in data if not item.is_fully_booked]
    comparison_days = data[0].comparison_days if data else 1
    comparison_label = {1: "前日比", 7: "先週比", 30: "先月比"}.get(comparison_days, "過去比")
    if not available:
        # A sold-out market is useful context, but it is not enough on its own
        # to calculate a defensible price.  Keep the initial release neutral
        # and let the operator decide from the signal.
        raw = facility.base_price
        reasoning = (
            f"OTA上で競合{len(data)}施設すべてが部屋なしのため、競合最安値から参考価格を計算できません。"
            f"今回は自施設の基準価格¥{facility.base_price:,}を参考値にしています。"
            "部屋なしは需要の強さを示す判断材料ですが、自動的な値上げには使用していません。"
        )
    else:
        average = sum(item.price_today for item in available) / len(available)
        comparable = [item for item in available if item.comparison_available and not item.was_fully_booked]
        increases = [item for item in comparable if item.difference > 0]
        decreases = [item for item in comparable if item.difference < 0]
        limited = [item for item in available if item.availability_status == "limited"]
        explicit_rooms = [item.remaining_rooms for item in available if item.remaining_rooms is not None]
        # Meeting decision (2026-08-14): the MVP presents an explainable
        # reference rank.  It does not claim to optimise revenue before enough
        # operating history and feedback have been accumulated.
        raw = int(average)
        movement = (
            f"{comparison_label}で値上げ{len(increases)}施設・値下げ{len(decreases)}施設"
            if comparable else f"{comparison_label}の比較履歴はまだありません"
        )
        sold_out_count = len(data) - len(available)
        reasoning = (
            f"競合{len(data)}施設中、空室あり{len(available)}施設の平均最安値は¥{average:,.0f}です。"
            f"{movement}、OTA上の部屋なしは{sold_out_count}施設です。"
            f"残りわずかは{len(limited)}施設です。"
            + (f"画面に明示された残室数の最少は{min(explicit_rooms)}室です。" if explicit_rooms else "")
            +
            "初期版では、空室のある競合施設の平均最安値をそのまま参考価格にしています。"
            "価格変動・部屋なし・残室状況は判断材料として表示しますが、自動的な上乗せや値下げには使用していません。"
        )
    guarded_target = round(min(max(raw, facility.min_price), facility.max_price) / 100) * 100
    if guarded_target != round(raw / 100) * 100:
        boundary = "最低価格" if raw < facility.min_price else "最高価格"
        reasoning += f" 計算結果は安全設定の{boundary}に合わせています。"
    rank_label, suggested = _closest_rate_rank(facility, guarded_target)
    reasoning += (
        f" 目標価格¥{guarded_target:,}に最も近い、施設設定の{rank_label}ランク"
        f"（¥{suggested:,}）を参考ランクとして表示しています。最終的な販売判断は施設側で行います。"
    )
    return models.MarketRecommendation(
        date=date.isoformat(), suggested_price=suggested,
        suggested_rank=rank_label,
        reasoning=reasoning,
    )


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness check that verifies the configured production database."""
    db.execute(text("select 1"))
    return {"status": "ready", "database": engine.dialect.name}


@app.get("/app-config.js", include_in_schema=False)
def browser_runtime_config():
    """Expose browser-safe runtime configuration to the bundled React app."""
    payload = {
        "apiUrl": "",
        "supabaseUrl": settings.supabase_url,
        "supabasePublishableKey": settings.supabase_publishable_key,
        "demoMode": settings.environment == "demo",
    }
    return Response(
        content=f"window.__REVENAVI_CONFIG__ = {json.dumps(payload)};",
        media_type="application/javascript",
        headers={"Cache-Control": "no-store"},
    )


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
        email_delivery_configured=notifier_service.configured,
        stripe_configured=stripe_billing.configured,
        simulation_enabled=settings.allow_simulated_data,
        ota_sources=ota_sources,
    )


@app.get("/public/legal-config")
def public_legal_config():
    """Expose only business details that are intended for public legal pages."""
    values = {
        "business_name": settings.business_name,
        "representative": settings.business_representative,
        "address": settings.business_address,
        "phone": settings.business_phone,
        "support_email": settings.support_email,
    }
    return {**values, "complete": all(values.values())}


@app.get("/operator/summary", response_model=models.OperatorSummary)
def operator_summary(
    _operator: CurrentUser = Depends(require_operator),
    db: Session = Depends(get_db),
):
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    successful = db.query(models.DBCompetitorCollectionRun).filter(
        models.DBCompetitorCollectionRun.status == "succeeded",
    ).order_by(models.DBCompetitorCollectionRun.completed_at.desc()).first()
    local_today = dt.datetime.now(ZoneInfo("Asia/Tokyo")).date()
    month_start = local_today.replace(day=1)
    return models.OperatorSummary(
        organizations=db.query(models.DBOrganization).count(),
        active_subscriptions=db.query(models.DBSubscription).filter_by(status="active").count(),
        collection_runs_7d=db.query(models.DBCompetitorCollectionRun).filter(
            models.DBCompetitorCollectionRun.started_at >= cutoff,
        ).count(),
        failed_collection_runs_7d=db.query(models.DBCompetitorCollectionRun).filter(
            models.DBCompetitorCollectionRun.started_at >= cutoff,
            models.DBCompetitorCollectionRun.status == "failed",
        ).count(),
        last_success_at=successful.completed_at if successful else None,
        collection_runs_month=db.query(models.DBCompetitorCollectionRun).filter(
            models.DBCompetitorCollectionRun.collection_day >= month_start,
        ).count(),
        monthly_run_limit=settings.apify_monthly_run_limit,
    )


@app.get("/operator/accounts", response_model=list[models.OperatorAccount])
def operator_accounts(
    _operator: CurrentUser = Depends(require_operator),
    db: Session = Depends(get_db),
):
    rows: list[models.OperatorAccount] = []
    for organization in db.query(models.DBOrganization).order_by(models.DBOrganization.created_at.desc()).all():
        facility = db.query(models.DBFacility).filter_by(organization_id=organization.id).first()
        subscription = _subscription_for_organization(db, organization.id)
        payment_method = "none"
        if subscription:
            payment_method = "stripe" if subscription.stripe_customer_id else "bank_transfer"
        rows.append(models.OperatorAccount(
            organization_id=organization.id,
            organization_name=organization.name,
            facility_name=facility.name if facility else None,
            notification_email=organization.notification_email,
            subscription_status=subscription.status if subscription else "inactive",
            current_period_end=subscription.current_period_end if subscription else None,
            payment_method=payment_method,
        ))
    return rows


@app.put("/operator/accounts/{organization_id}/subscription", response_model=models.OperatorAccount)
def update_operator_subscription(
    organization_id: str,
    payload: models.OperatorSubscriptionUpdate,
    _operator: CurrentUser = Depends(require_operator),
    db: Session = Depends(get_db),
):
    organization = db.query(models.DBOrganization).filter_by(id=organization_id).one_or_none()
    if organization is None:
        raise HTTPException(status_code=404, detail="対象の顧客が見つかりません")
    if payload.status == "active" and payload.current_period_end:
        period_end = payload.current_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=dt.timezone.utc)
        if period_end <= dt.datetime.now(dt.timezone.utc):
            raise HTTPException(status_code=422, detail="利用期限は未来の日付を指定してください")
    subscription = _subscription_for_organization(db, organization_id)
    if subscription is None:
        subscription = models.DBSubscription(organization_id=organization_id)
        db.add(subscription)
    if subscription.stripe_customer_id:
        raise HTTPException(status_code=409, detail="カード契約はStripeの契約画面から変更してください")
    subscription.status = payload.status
    subscription.current_period_end = payload.current_period_end
    db.commit()
    facility = db.query(models.DBFacility).filter_by(organization_id=organization.id).first()
    return models.OperatorAccount(
        organization_id=organization.id,
        organization_name=organization.name,
        facility_name=facility.name if facility else None,
        notification_email=organization.notification_email,
        subscription_status=subscription.status,
        current_period_end=subscription.current_period_end,
        payment_method="bank_transfer",
    )


@app.get("/operator/payments", response_model=list[models.PaymentLedger])
def operator_payments(
    _operator: CurrentUser = Depends(require_operator),
    db: Session = Depends(get_db),
):
    return db.query(models.DBPaymentLedger).order_by(
        models.DBPaymentLedger.billing_month.desc(), models.DBPaymentLedger.created_at.desc(),
    ).all()


@app.post("/operator/payments", response_model=models.PaymentLedger, status_code=status.HTTP_201_CREATED)
def create_operator_payment(
    payload: models.PaymentLedgerCreate,
    _operator: CurrentUser = Depends(require_operator),
    db: Session = Depends(get_db),
):
    organization = db.query(models.DBOrganization).filter_by(id=payload.organization_id).one_or_none()
    if organization is None:
        raise HTTPException(status_code=404, detail="対象の顧客が見つかりません")
    if payload.status == "paid" and payload.paid_at is None:
        raise HTTPException(status_code=422, detail="入金済みの場合は入金日を入力してください")
    if payload.service_end < payload.billing_month:
        raise HTTPException(status_code=422, detail="利用期限は請求月以降を指定してください")
    record = models.DBPaymentLedger(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/onboarding/status", response_model=models.OnboardingStatus)
def onboarding_status(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _organization_for_user(db, user)
    if organization is None:
        return models.OnboardingStatus(
            subscription_status="active" if settings.demo_bypass_billing else "inactive"
        )
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
    if not organization.notification_email:
        organization.notification_email = user.email
    if not _has_active_subscription(_subscription_for_organization(db, organization.id)):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="初期設定を始めるには、ご契約の確認が必要です")
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
    _replace_rate_ranks(db, facility, payload.rate_ranks)
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


@app.get("/notification-settings", response_model=models.NotificationSettings)
def get_notification_settings(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _require_organization(db, user)
    if not organization.notification_email:
        organization.notification_email = user.email
        db.commit()
    return models.NotificationSettings(
        email=organization.notification_email,
        enabled=organization.email_notifications_enabled,
        delivery_configured=notifier_service.configured,
    )


@app.put("/notification-settings", response_model=models.NotificationSettings)
def update_notification_settings(payload: models.NotificationSettingsUpdate, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _require_organization(db, user, write=True)
    organization.notification_email = organization.notification_email or user.email
    organization.email_notifications_enabled = payload.enabled
    db.commit()
    return models.NotificationSettings(
        email=organization.notification_email,
        enabled=organization.email_notifications_enabled,
        delivery_configured=notifier_service.configured,
    )


@app.put("/facility", response_model=models.Facility)
def update_facility(payload: models.FacilityUpdate, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    facility = _ready_facility(db, user, write=True)
    facility.min_price, facility.max_price = payload.min_price, payload.max_price
    _replace_rate_ranks(db, facility, payload.rate_ranks)
    db.commit()
    db.refresh(facility)
    return facility


@app.get("/competitors", response_model=list[models.Competitor])
def get_competitors(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    facility = _ready_facility(db, user)
    return db.query(models.DBCompetitor).filter_by(facility_id=facility.id, is_active=True).all()


@app.post("/competitors", response_model=models.Competitor, status_code=status.HTTP_201_CREATED)
def add_competitor(payload: models.CompetitorInput, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    facility = _ready_facility(db, user, write=True)
    organization = _require_organization(db, user)
    plan, _ = _subscription_plan(_subscription_for_organization(db, organization.id))
    maximum = 10 if plan == "upgrade" else 3
    current_count = db.query(models.DBCompetitor).filter_by(facility_id=facility.id, is_active=True).count()
    if current_count >= maximum:
        raise HTTPException(status_code=403, detail=f"現在のプランで登録できる競合施設は最大{maximum}件です")
    source = _validate_ota_url(payload.url)
    competitor = models.DBCompetitor(
        facility_id=facility.id, ota_source_key=source.key, name=payload.name,
        url=payload.url, canonical_url=_canonical_url(payload.url), is_active=True,
    )
    db.add(competitor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="この競合施設のURLはすでに登録されています") from exc
    db.refresh(competitor)
    return competitor


@app.put("/competitors/{comp_id}", response_model=models.Competitor)
def update_competitor(comp_id: str, payload: models.CompetitorUpdate, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    facility = _ready_facility(db, user, write=True)
    source = _validate_ota_url(payload.url)
    competitor = db.query(models.DBCompetitor).filter_by(id=comp_id, facility_id=facility.id).first()
    if not competitor:
        raise HTTPException(status_code=404, detail="競合施設が見つかりませんでした")
    competitor.name, competitor.url = payload.name, payload.url
    competitor.canonical_url, competitor.ota_source_key = _canonical_url(payload.url), source.key
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="この競合施設のURLはすでに登録されています") from exc
    db.refresh(competitor)
    return competitor


@app.get("/market_data", response_model=list[models.CompetitorPrice])
def get_market_data(start_date: str, days: int = Query(default=90, ge=1, le=90), user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    _enforce_horizon(db, user, days)
    return collect_market_data(db, _ready_facility(db, user), _parse_date(start_date), days)


@app.get("/market_data/cached", response_model=list[models.CompetitorPrice])
def get_cached_market_data(start_date: str, days: int = Query(default=90, ge=1, le=365), comparison_days: int = Query(default=1), user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    _enforce_horizon(db, user, days)
    return read_cached_market_data(db, _ready_facility(db, user), _parse_date(start_date), days, comparison_days)


@app.get("/alerts", response_model=list[models.Alert])
def get_alerts(start_date: str, days: int = Query(default=7, ge=1, le=31), comparison_days: int = Query(default=1), user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    return create_alerts(read_cached_market_data(db, _ready_facility(db, user), _parse_date(start_date), days, comparison_days))


@app.get("/recommendation", response_model=models.MarketRecommendation)
def get_recommendation(date: str, user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    return build_recommendation(db, _ready_facility(db, user), _parse_date(date))


@app.get("/recommendations", response_model=list[models.MarketRecommendation])
def get_recommendations(start_date: str, days: int = Query(default=90, ge=1, le=365), comparison_days: int = Query(default=1), user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    _enforce_horizon(db, user, days)
    facility = _ready_facility(db, user)
    start = _parse_date(start_date)
    market_data = read_cached_market_data(db, facility, start, days, comparison_days)
    competitor_count = db.query(models.DBCompetitor).filter_by(facility_id=facility.id, is_active=True).count()
    return [
        build_recommendation(db, facility, date, market_data)
        for offset in range(days)
        for date in [start + dt.timedelta(days=offset)]
        if len([item for item in market_data if item.date == date.isoformat()]) == competitor_count
    ]


@app.get("/billing/status", response_model=models.BillingStatus)
def billing_status(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _organization_for_user(db, user)
    subscription = _subscription_for_organization(db, organization.id) if organization else None
    plan, max_horizon_days = _subscription_plan(subscription)
    return models.BillingStatus(
        configured=stripe_billing.configured,
        subscription_status="active" if settings.demo_bypass_billing else (subscription.status if subscription else "inactive"),
        plan=plan,
        max_horizon_days=max_horizon_days,
        max_competitors=10 if plan == "upgrade" else 3,
    )


@app.post("/billing/checkout", response_model=models.CheckoutSession)
def create_checkout(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _organization_for_user(db, user)
    if organization is None:
        organization = models.DBOrganization(
            name=f"{user.email.split('@')[0]} の事業者", notification_email=user.email,
        )
        db.add(organization)
        db.flush()
        db.add(models.DBOrganizationMember(organization_id=organization.id, user_id=user.id, role="owner"))
        db.commit()
    if settings.demo_bypass_billing:
        return models.CheckoutSession(checkout_url=f"{settings.frontend_app_url}/?checkout=success")
    subscription = _subscription_for_organization(db, organization.id)
    if _has_active_subscription(subscription):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="このアカウントはすでに契約中です")
    try:
        return models.CheckoutSession(checkout_url=stripe_billing.create_checkout(organization.id, user.email))
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail="現在はカード決済の準備中です") from exc


@app.post("/billing/portal", response_model=models.CheckoutSession)
def create_portal(user: CurrentUser = Depends(require_current_user), db: Session = Depends(get_db)):
    organization = _require_organization(db, user, write=True)
    subscription = _subscription_for_organization(db, organization.id)
    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(status_code=404, detail="この契約は画面から変更できません。運営者へお問い合わせください")
    try:
        return models.CheckoutSession(checkout_url=stripe_billing.create_portal(subscription.stripe_customer_id))
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail="現在はカード決済の準備中です") from exc


@app.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None)):
    try:
        event = stripe_billing.verify_event(await request.body(), stripe_signature)
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=400, detail="決済通知を確認できませんでした") from exc

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


# The production image bundles the React build into the same Cloud Run service.
# API routes are registered first, so this catch-all only serves browser assets.
static_directory = Path(__file__).resolve().parent / "static"
if static_directory.is_dir():
    app.mount("/", StaticFiles(directory=static_directory, html=True), name="frontend")
