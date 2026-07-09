from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from scraper import scraper_service
from notifier import notifier_service

def scheduled_scraping_job():
    print(f"[{datetime.datetime.now()}] [Scheduler] Starting daily market data sync...")
    db: Session = SessionLocal()

    try:
        # 1. Scrape data for today and next 6 days (7 days total)
        today = datetime.datetime.now().date()
        competitors = db.query(models.DBCompetitor).all()

        alerts_generated = []

        for i in range(7):
            target_date = today + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            yesterday_str = (target_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

            for comp in competitors:
                # Check if data already exists
                existing = db.query(models.DBCompetitorPrice).filter(
                    models.DBCompetitorPrice.competitor_id == comp.id,
                    models.DBCompetitorPrice.date == date_str
                ).first()

                if not existing:
                    try:
                        price, is_booked = scraper_service.extract_price(comp.url, date_str, comp.id)
                    except Exception as e:
                        print(f"[Scheduler Error] Failed to extract price for {comp.name} on {date_str}: {e}")
                        continue

                    db.add(models.DBCompetitorPrice(
                        date=date_str,
                        competitor_id=comp.id,
                        price=price,
                        is_fully_booked=is_booked,
                        scraped_at=datetime.datetime.now().isoformat()
                    ))

                    # Ensure yesterday's data exists for comparison
                    yesterday_data = db.query(models.DBCompetitorPrice).filter(
                        models.DBCompetitorPrice.competitor_id == comp.id,
                        models.DBCompetitorPrice.date == yesterday_str
                    ).first()

                    if not yesterday_data:
                         try:
                             y_price, _ = scraper_service.extract_price(comp.url, yesterday_str, comp.id)
                             db.add(models.DBCompetitorPrice(
                                date=yesterday_str,
                                competitor_id=comp.id,
                                price=y_price,
                                is_fully_booked=False,
                                scraped_at=datetime.datetime.now().isoformat()
                            ))
                             yesterday_data = models.DBCompetitorPrice(price=y_price)
                         except Exception as e:
                             print(f"[Scheduler Error] Failed to extract yesterday price for {comp.name}: {e}")
                             pass

                    # 2. Check for alert conditions (Hardcoded > 3000 JPY or sellout for now)
                    if yesterday_data:
                        diff = price - yesterday_data.price
                    else:
                        diff = 0

                    if is_booked:
                        alerts_generated.append(f"【{date_str}】 {comp.name} が満室になりました。")
                    elif diff >= 3000:
                        alerts_generated.append(f"【{date_str}】 {comp.name} が {diff:,}円 の大幅値上げを行いました。")
                    elif diff <= -3000:
                        alerts_generated.append(f"【{date_str}】 {comp.name} が {abs(diff):,}円 の大幅値下げを行いました。")

        db.commit()

        # 3. Send consolidated LINE notification if there are alerts
        if alerts_generated:
            msg = "\n".join(["\n[マーケティングアシスタント アラート]"] + alerts_generated)
            notifier_service.send_message(msg)

        print(f"[{datetime.datetime.now()}] [Scheduler] Sync completed.")

    except Exception as e:
        print(f"[Scheduler Error] {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run daily at 10:00 AM for production
    scheduler.add_job(scheduled_scraping_job, 'cron', hour=10, minute=0)

    scheduler.start()
