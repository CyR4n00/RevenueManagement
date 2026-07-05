from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import datetime
import random

from database import engine, Base, get_db
import models
from scraper import scraper_service

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Revenue Assistant API - Competitor Focus")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_scraper(db: Session, date_str: str):
    """
    Runs the scraper for all competitors for a given date.
    If direct scraping fails, it uses the fallback simulation.
    """
    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    yesterday_str = (target_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    competitors = db.query(models.DBCompetitor).all()
    if not competitors:
        return

    for comp in competitors:
        # Check if we already have data for today
        existing = db.query(models.DBCompetitorPrice).filter(
            models.DBCompetitorPrice.competitor_id == comp.id,
            models.DBCompetitorPrice.date == date_str
        ).first()

        if existing:
            continue # Already scraped

        print(f"[API] Running scraper for {comp.name} on {date_str}...")

        try:
            price_today, is_fully_booked = scraper_service.extract_price(comp.url, date_str, comp.id)

            # Ensure yesterday's data exists for difference calculation
            existing_yesterday = db.query(models.DBCompetitorPrice).filter(
                models.DBCompetitorPrice.competitor_id == comp.id,
                models.DBCompetitorPrice.date == yesterday_str
            ).first()

            if not existing_yesterday:
                # Run scraper for yesterday too to get a baseline
                price_yesterday, _ = scraper_service.extract_price(comp.url, yesterday_str, comp.id)
                db.add(models.DBCompetitorPrice(
                    date=yesterday_str,
                    competitor_id=comp.id,
                    price=price_yesterday,
                    is_fully_booked=False,
                    scraped_at=datetime.datetime.now().isoformat()
                ))

            db.add(models.DBCompetitorPrice(
                date=date_str,
                competitor_id=comp.id,
                price=price_today,
                is_fully_booked=is_fully_booked,
                scraped_at=datetime.datetime.now().isoformat()
            ))
            db.commit()
        except Exception as e:
            print(f"[API Error] Skipping {comp.name} on {date_str} due to scraping failure: {e}")
            db.rollback()


@app.on_event("startup")
def startup_event():
    db = next(get_db())
    if not db.query(models.DBFacility).first():
        db.add(models.DBFacility(id=1, name="自社ホテル（サンプル）", base_price=10000))
        # Add real URLs for demonstration
        db.add(models.DBCompetitor(id=1, name="ホテルA (アパ新宿)", url="https://travel.rakuten.co.jp/HOTEL/14138/14138.html"))
        db.add(models.DBCompetitor(id=2, name="ゲストハウスB (東京駅前)", url="https://www.booking.com/hotel/jp/tokyo-station.ja.html"))
        db.add(models.DBCompetitor(id=3, name="Cヴィラ (京都鴨川)", url="https://travel.rakuten.co.jp/HOTEL/180290/180290.html"))
        db.commit()

# --- ENDPOINTS ---

@app.get("/facility", response_model=models.Facility)
def get_facility(db: Session = Depends(get_db)):
    return db.query(models.DBFacility).first()

@app.get("/competitors", response_model=List[models.Competitor])
def get_competitors(db: Session = Depends(get_db)):
    return db.query(models.DBCompetitor).all()

@app.get("/market_data", response_model=List[models.CompetitorPrice])
def get_market_data(start_date: str, days: int = 7, db: Session = Depends(get_db)):
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    results = []

    # Run scraper to ensure we have data for requested dates
    for i in range(days):
        current_date = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        run_scraper(db, current_date)

    for i in range(days):
        current_date = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        yesterday_str = (start + datetime.timedelta(days=i-1)).strftime("%Y-%m-%d")

        comps = db.query(models.DBCompetitor).all()
        for comp in comps:
            today_data = db.query(models.DBCompetitorPrice).filter(
                models.DBCompetitorPrice.competitor_id == comp.id,
                models.DBCompetitorPrice.date == current_date
            ).first()

            yesterday_data = db.query(models.DBCompetitorPrice).filter(
                models.DBCompetitorPrice.competitor_id == comp.id,
                models.DBCompetitorPrice.date == yesterday_str
            ).first()

            if today_data:
                price_today = today_data.price
                price_yesterday = yesterday_data.price if yesterday_data else price_today

                results.append(models.CompetitorPrice(
                    date=current_date,
                    competitor_id=comp.id,
                    competitor_name=comp.name,
                    price_today=price_today,
                    price_yesterday=price_yesterday,
                    difference=price_today - price_yesterday,
                    is_fully_booked=today_data.is_fully_booked
                ))
    return results

@app.get("/alerts", response_model=List[models.Alert])
def get_alerts(start_date: str, days: int = 7, db: Session = Depends(get_db)):
    market_data = get_market_data(start_date, days, db)
    alerts = []
    alert_id = 1

    for c in market_data:
        if c.is_fully_booked:
            alerts.append(models.Alert(
                id=alert_id, date=c.date,
                message=f"{c.competitor_name} が満室になりました。需要が非常に高まっています。",
                type="sold_out"
            ))
            alert_id += 1
        elif c.difference >= 3000:
            alerts.append(models.Alert(
                id=alert_id, date=c.date,
                message=f"{c.competitor_name} が {c.date} の料金を +{c.difference:,}円 大幅に値上げしました！",
                type="increase"
            ))
            alert_id += 1
        elif c.difference <= -3000:
            alerts.append(models.Alert(
                id=alert_id, date=c.date,
                message=f"{c.competitor_name} が {c.date} の料金を {c.difference:,}円 大幅に値下げしました。",
                type="decrease"
            ))
            alert_id += 1

    return alerts

@app.get("/recommendation", response_model=models.MarketRecommendation)
def get_recommendation(date: str, db: Session = Depends(get_db)):
    comp_data = get_market_data(start_date=date, days=1, db=db)
    facility = get_facility(db)

    available_comps = [c for c in comp_data if not c.is_fully_booked]
    if not available_comps:
         return models.MarketRecommendation(
            date=date,
            suggested_price=int(facility.base_price * 1.5),
            reasoning="ベンチマーク施設がすべて満室です。強気の価格設定（通常比1.5倍）を推奨します。"
        )

    avg_comp_price = sum(c.price_today for c in available_comps) / len(available_comps)

    major_increases = [c for c in available_comps if c.difference >= 3000]

    if major_increases:
        suggested = int(avg_comp_price * 0.95)
        names = "、".join([c.competitor_name for c in major_increases])
        reasoning = f"{names} が大幅に値上げしています。周辺需要が高まっているため、市場平均に近い {suggested:,}円 に引き上げることを推奨します。"
    else:
        suggested = int(facility.base_price)
        reasoning = "競合の価格に大きな変動はありません。現在の基本価格を維持して様子を見ることを推奨します。"

    suggested = round(suggested / 100) * 100

    return models.MarketRecommendation(
        date=date,
        suggested_price=suggested,
        reasoning=reasoning
    )
