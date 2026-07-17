from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import stripe
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import io
import csv
from typing import List
import datetime
import random

from database import engine, Base, get_db
import models
from scraper import scraper_service
from scheduler import start_scheduler

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Retrieve the dependency mapping, if overridden (e.g. by TestClient)
    db_dependency = app.dependency_overrides.get(get_db, get_db)
    db = next(db_dependency())
    if not db.query(models.DBFacility).first():
        db.add(models.DBFacility(id=1, name="自社ホテル（サンプル）", base_price=10000))
        db.commit()

    if not db.query(models.DBPriceRank).first():
        db.add(models.DBPriceRank(name="ランク A (高需要時)", price=20000))
        db.add(models.DBPriceRank(name="ランク B (やや高需要)", price=15000))
        db.add(models.DBPriceRank(name="ランク C (通常)", price=10000))
        db.add(models.DBPriceRank(name="ランク D (閑散期)", price=8000))
        db.commit()

    # Start the background scheduler
    start_scheduler()
    yield

app = FastAPI(title="Revenue Assistant API - Competitor Focus", lifespan=lifespan)

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
        price_today, is_fully_booked = scraper_service.extract_price(comp.url, date_str, comp.id, db)

        # Ensure yesterday's data exists for difference calculation
        existing_yesterday = db.query(models.DBCompetitorPrice).filter(
            models.DBCompetitorPrice.competitor_id == comp.id,
            models.DBCompetitorPrice.date == yesterday_str
        ).first()

        if not existing_yesterday:
             # Run scraper for yesterday too to get a baseline
             price_yesterday, _ = scraper_service.extract_price(comp.url, yesterday_str, comp.id, db)
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


@app.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    event = None

    if not endpoint_secret:
        raise HTTPException(status_code=400, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_details', {}).get('email')

        if customer_email:
            user = db.query(models.DBUser).filter(models.DBUser.email == customer_email).first()
            if user:
                user.subscription_status = 'active'
                user.stripe_customer_id = session.get('customer')
                db.commit()
                print(f"[Webhook] Activated subscription for {customer_email}")

    return {"status": "success"}

# --- ENDPOINTS ---

@app.post("/create-checkout-session")
async def create_checkout_session(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        email = data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        # Check if user already exists
        user = db.query(models.DBUser).filter(models.DBUser.email == email).first()
        if not user:
            user = models.DBUser(email=email)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Dynamically create or retrieve a Product and Price to make this zero-config for the user
        prices = stripe.Price.list(limit=1, lookup_keys=["revenue_assistant_monthly"])

        if not prices.data:
            # Create a test product and price
            product = stripe.Product.create(
                name="レベニューアシスタント 月額プラン",
                description="競合の価格・空室状況を自動監視し、最適な価格提案を行うアシスタントツールです。"
            )
            price = stripe.Price.create(
                product=product.id,
                unit_amount=9800, # e.g. 9800 JPY
                currency="jpy",
                recurring={"interval": "month"},
                lookup_key="revenue_assistant_monthly"
            )
            price_id = price.id
        else:
            price_id = prices.data[0].id

        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url='http://localhost:3000/?success=true&session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/',
        )

        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config", response_model=List[models.SystemConfig])
def get_configs(db: Session = Depends(get_db)):
    return db.query(models.DBSystemConfig).all()

@app.get("/config/{key}", response_model=models.SystemConfig)
def get_config(key: str, db: Session = Depends(get_db)):
    config = db.query(models.DBSystemConfig).filter(models.DBSystemConfig.key == key).first()
    if not config:
        # Return empty string if not found
        return models.SystemConfig(key=key, value="")
    return config

@app.post("/config", response_model=models.SystemConfig)
def set_config_body(payload: models.SystemConfig, db: Session = Depends(get_db)):
    config = db.query(models.DBSystemConfig).filter(models.DBSystemConfig.key == payload.key).first()
    if not config:
        config = models.DBSystemConfig(key=payload.key, value=payload.value)
        db.add(config)
    else:
        config.value = payload.value
    db.commit()
    db.refresh(config)
    return config

@app.post("/config/{key}", response_model=models.SystemConfig)
def set_config(key: str, payload: models.SystemConfig, db: Session = Depends(get_db)):
    config = db.query(models.DBSystemConfig).filter(models.DBSystemConfig.key == key).first()
    if not config:
        config = models.DBSystemConfig(key=key, value=payload.value)
        db.add(config)
    else:
        config.value = payload.value
    db.commit()
    db.refresh(config)
    return config

@app.get("/facility", response_model=models.Facility)
def get_facility(db: Session = Depends(get_db)):
    return db.query(models.DBFacility).first()

@app.post("/facility", response_model=models.Facility)
def update_facility(facility: models.Facility, db: Session = Depends(get_db)):
    db_fac = db.query(models.DBFacility).filter(models.DBFacility.id == facility.id).first()
    if db_fac:
        db_fac.min_price = facility.min_price
        db_fac.max_price = facility.max_price
        db_fac.name = facility.name
        db_fac.base_price = facility.base_price
        db.commit()
        db.refresh(db_fac)
        return db_fac
    else:
        new_fac = models.DBFacility(id=facility.id, name=facility.name, base_price=facility.base_price, min_price=facility.min_price, max_price=facility.max_price)
        db.add(new_fac)
        db.commit()
        db.refresh(new_fac)
        return new_fac

@app.get("/ranks", response_model=List[models.PriceRank])
def get_ranks(db: Session = Depends(get_db)):
    return db.query(models.DBPriceRank).order_by(models.DBPriceRank.price.desc()).all()

@app.post("/ranks", response_model=List[models.PriceRank])
def set_ranks(ranks: List[models.PriceRank], db: Session = Depends(get_db)):
    db.query(models.DBPriceRank).delete()
    db.commit()
    for rank in ranks:
        db.add(models.DBPriceRank(name=rank.name, price=rank.price))
    db.commit()
    return db.query(models.DBPriceRank).order_by(models.DBPriceRank.price.desc()).all()

@app.get("/competitors", response_model=List[models.Competitor])
def get_competitors(db: Session = Depends(get_db)):
    return db.query(models.DBCompetitor).all()

@app.post("/competitors", response_model=List[models.Competitor])
def set_competitors(competitors: List[models.Competitor], db: Session = Depends(get_db)):
    db.query(models.DBCompetitor).delete()
    db.commit()
    for comp in competitors:
        db.add(models.DBCompetitor(name=comp.name, url=comp.url))
    db.commit()
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

def price_to_rank(price: int, ranks: List[models.DBPriceRank]) -> str:
    if not ranks:
        return "未設定"

    # Ranks should already be sorted descending, but just in case
    sorted_ranks = sorted(ranks, key=lambda r: r.price, reverse=True)
    for r in sorted_ranks:
        if price >= r.price:
            return r.name

    # If it's below the lowest rank, return the lowest rank
    return sorted_ranks[-1].name
@app.get("/recommendation", response_model=models.MarketRecommendation)
def get_recommendation(date: str, db: Session = Depends(get_db)):
    comp_data = get_market_data(start_date=date, days=1, db=db)
    facility = get_facility(db)
    ranks = db.query(models.DBPriceRank).order_by(models.DBPriceRank.price.desc()).all()

    if not facility:
        return models.MarketRecommendation(
            date=date,
            suggested_price=0,
            suggested_rank="D",
            reasoning="自社施設が登録されていません。"
        )

    available_comps = [c for c in comp_data if not c.is_fully_booked]
    if not available_comps:
         raw_suggested = int(facility.base_price * 1.5)
         suggested = min(max(raw_suggested, facility.min_price), facility.max_price)
         return models.MarketRecommendation(
            date=date,
            suggested_price=suggested,
            suggested_rank=price_to_rank(suggested, ranks),
            reasoning="ベンチマーク施設がすべて満室です。強気の価格設定を推奨しますが、上限・下限設定（ガードレール）の範囲内に調整しました。"
        )

    avg_comp_price = sum(c.price_today for c in available_comps) / len(available_comps)

    major_increases = [c for c in available_comps if c.difference >= 3000]
    major_decreases = [c for c in available_comps if c.difference <= -3000]

    if major_increases:
        raw_suggested = int(avg_comp_price * 0.95)
        suggested = min(max(raw_suggested, facility.min_price), facility.max_price)
        names = "、".join([c.competitor_name for c in major_increases])
        reasoning = f"{names} が大幅に値上げしています。市場平均に合わせて上限・下限の範囲内で価格を引き上げることを推奨します。"
    elif major_decreases:
        # Conservative downward pricing: don't match the drop fully, just a slight adjustment
        raw_suggested = int(facility.base_price * 0.90)
        # Ensure we don't drop below min_price
        suggested = max(raw_suggested, facility.min_price)
        names = "、".join([c.competitor_name for c in major_decreases])
        reasoning = f"{names} が大幅に値下げしています。価格競争を避けるため、急激な値下げは行わず、自社の下限価格（ガードレール）の範囲内で小幅な調整にとどめることを推奨します。"
    else:
        suggested = int(facility.base_price)
        suggested = min(max(suggested, facility.min_price), facility.max_price)
        reasoning = "競合の価格に大きな変動はありません。現在の基本価格を維持して様子を見ることを推奨します。"

    suggested = round(suggested / 100) * 100

    return models.MarketRecommendation(
        date=date,
        suggested_price=suggested,
        suggested_rank=price_to_rank(suggested, ranks),
        reasoning=reasoning
    )

@app.get("/export_csv")
def export_csv(start_date: str, days: int = 7, db: Session = Depends(get_db)):
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()

    output = io.StringIO()
    # 日本語のサイトコントローラー向けにBOM付きUTF-8で出力する（Excelでの文字化け防止）
    output.write('\ufeff')
    writer = csv.writer(output)

    # 国内の代表的なサイトコントローラー（ねっぱん！等）のCSV取込フォーマットを模したヘッダー
    writer.writerow(["対象年月日", "部屋タイプコード", "部屋タイプ名", "適用料金ランク", "設定料金(参考)"])

    for i in range(days):
        current_date_str = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        rec = get_recommendation(current_date_str, db)

        # デモ用に固定の部屋タイプに対してランクを出力
        # 日付は YYYY/MM/DD 形式に変換
        formatted_date = current_date_str.replace("-", "/")
        writer.writerow([formatted_date, "RM01", "スタンダードツイン", rec.suggested_rank, rec.suggested_price])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pms_upload_{start_date}.csv"}
    )
