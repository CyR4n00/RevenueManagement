"""Single-instance background market sync scheduler."""

import datetime as dt
import hashlib
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from notifier import notifier_service
from settings import get_settings

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone="Asia/Tokyo")


def scheduled_scraping_job(mode: str = "refresh"):
    # Imported here to avoid a module cycle during FastAPI application creation.
    from main import _subscription_plan, collect_market_data, create_alerts
    from models import DBFacility, DBNotificationDelivery, DBOrganization, DBSubscription

    with SessionLocal() as db:
        today = dt.date.today()
        for facility in db.query(DBFacility).filter(DBFacility.onboarding_completed_at.is_not(None)).all():
            try:
                start = today
                days = get_settings().sync_lookahead_days
                refresh = True
                if mode == "future":
                    subscription = db.query(DBSubscription).filter_by(
                        organization_id=facility.organization_id,
                    ).first()
                    _, horizon_days = _subscription_plan(subscription)
                    future_days = max(0, horizon_days - days)
                    chunk_count = max(1, (future_days + 30) // 31)
                    chunk_index = today.toordinal() % chunk_count
                    start = today + dt.timedelta(days=days + chunk_index * 31)
                    days = min(31, horizon_days - (start - today).days)
                    refresh = True
                    if days <= 0:
                        continue
                alerts = create_alerts(collect_market_data(
                    db, facility, start, days, refresh=refresh,
                ))
                organization = db.query(DBOrganization).filter_by(id=facility.organization_id).first()
                if not alerts or not organization or not organization.email_notifications_enabled:
                    continue
                if not organization.notification_email or not notifier_service.configured:
                    logger.info("Email delivery is not configured for organization %s", facility.organization_id)
                    continue
                delivery_day = dt.date.today().isoformat()
                pending = []
                for alert in alerts:
                    fingerprint = hashlib.sha256(
                        f"{delivery_day}|{facility.id}|{alert.type}|{alert.message}".encode("utf-8")
                    ).hexdigest()
                    exists = db.query(DBNotificationDelivery).filter_by(
                        organization_id=facility.organization_id, fingerprint=fingerprint,
                    ).first()
                    if exists is None:
                        pending.append((fingerprint, alert))
                if pending and notifier_service.send_alerts(
                    organization.notification_email,
                    facility.name,
                    [alert.message for _, alert in pending],
                ):
                    db.add_all([
                        DBNotificationDelivery(
                            organization_id=facility.organization_id, fingerprint=fingerprint,
                        )
                        for fingerprint, _ in pending
                    ])
                    db.commit()
            except Exception:
                db.rollback()
                logger.exception("Scheduled market sync failed for facility %s", facility.id)
        logger.info("Scheduled market sync completed")


def start_scheduler():
    settings = get_settings()
    if not settings.scheduler_enabled or _scheduler.running:
        return
    if settings.environment == "demo":
        _scheduler.add_job(
            scheduled_scraping_job,
            "interval",
            minutes=settings.demo_sync_interval_minutes,
            id="market-sync",
            replace_existing=True,
        )
    else:
        _scheduler.add_job(
            scheduled_scraping_job, "cron", hour=settings.daily_sync_hours[0],
            minute=settings.daily_sync_minute, id="market-sync-current",
            kwargs={"mode": "refresh"}, replace_existing=True,
        )
        if len(settings.daily_sync_hours) > 1:
            _scheduler.add_job(
                scheduled_scraping_job, "cron", hour=settings.daily_sync_hours[1],
                minute=settings.daily_sync_minute, id="market-sync-future",
                kwargs={"mode": "future"}, replace_existing=True,
            )
    _scheduler.start()


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
