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

    with SessionLocal() as db:
        today = dt.date.today()
        try:
            data = collect_market_data(db, today, 7)
            alerts = create_alerts(data)
            if alerts:
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
            hour=settings.daily_sync_hour,
            minute=settings.daily_sync_minute,
            id="market-sync",
            replace_existing=True,
        )
    _scheduler.start()


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
