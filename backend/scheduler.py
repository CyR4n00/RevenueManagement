"""Single-instance background market sync scheduler."""

import datetime as dt
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from notifier import notifier_service
from settings import get_settings

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone="Asia/Tokyo")


def scheduled_scraping_job():
    # Imported here to avoid a module cycle during FastAPI application creation.
    from main import collect_market_data, create_alerts
    from models import DBFacility

    with SessionLocal() as db:
        today = dt.date.today()
        try:
            alerts = []
            for facility in db.query(DBFacility).filter(DBFacility.onboarding_completed_at.is_not(None)).all():
                alerts.extend(create_alerts(collect_market_data(
                    db, facility, today, get_settings().sync_lookahead_days, refresh=True,
                )))
            # A single LINE user ID is safe only for the local demo owner.
            # Production delivery is enabled after each organization connects
            # its own LINE recipient in the onboarding flow.
            if alerts and get_settings().environment == "demo":
                body = "[Revenue Assistant alert]\n" + "\n".join(alert.message for alert in alerts)
                notifier_service.send_message(body)
            logger.info("Scheduled market sync completed")
        except Exception:
            logger.exception("Scheduled market sync failed")


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
            scheduled_scraping_job,
            "cron",
            hour=",".join(str(hour) for hour in settings.daily_sync_hours),
            minute=settings.daily_sync_minute,
            id="market-sync",
            replace_existing=True,
        )
    _scheduler.start()


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
