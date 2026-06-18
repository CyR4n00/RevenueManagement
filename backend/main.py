from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import datetime
import random
from models import Facility, Competitor, CompetitorPrice, Alert, MarketRecommendation

app = FastAPI(title="Revenue Assistant API - Competitor Focus")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MOCK DATA ---
my_facility = Facility(id=1, name="自社ホテル（サンプル）", base_price=10000)

competitors = [
    Competitor(id=101, name="ホテルA (近隣リゾート)"),
    Competitor(id=102, name="ゲストハウスB (駅前)"),
    Competitor(id=103, name="Cヴィラ (一棟貸し)")
]

def generate_mock_competitor_data(date_str: str) -> List[CompetitorPrice]:
    seed_str = f"comp_data_{date_str}"
    random.seed(seed_str)

    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    is_weekend = target_date.weekday() >= 4 # Fri, Sat, Sun

    results = []
    for comp in competitors:
        base = 12000 if comp.id == 101 else (8000 if comp.id == 102 else 15000)
        if is_weekend:
            base = int(base * 1.3)

        # Simulate price changes from yesterday's scan to today's scan
        # Most of the time it doesn't change much, but sometimes big shifts
        change_type = random.choice(["none", "none", "none", "up", "down", "big_up"])

        price_yesterday = base + random.randint(-1000, 1000)

        if change_type == "none":
            price_today = price_yesterday
        elif change_type == "up":
            price_today = price_yesterday + random.choice([500, 1000])
        elif change_type == "down":
            price_today = price_yesterday - random.choice([500, 1000])
        elif change_type == "big_up":
            price_today = price_yesterday + random.choice([3000, 4000, 5000])

        # Simulate sold out
        is_fully_booked = False
        if is_weekend and random.random() > 0.8:
            is_fully_booked = True

        results.append(CompetitorPrice(
            date=date_str,
            competitor_id=comp.id,
            competitor_name=comp.name,
            price_today=price_today,
            price_yesterday=price_yesterday,
            difference=price_today - price_yesterday,
            is_fully_booked=is_fully_booked
        ))
    return results

# --- ENDPOINTS ---

@app.get("/facility", response_model=Facility)
def get_facility():
    return my_facility

@app.get("/competitors", response_model=List[Competitor])
def get_competitors():
    return competitors

@app.get("/market_data", response_model=List[CompetitorPrice])
def get_market_data(start_date: str, days: int = 7):
    """Gets competitor pricing for a range of dates"""
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    data = []
    for i in range(days):
        current_date = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        data.extend(generate_mock_competitor_data(current_date))
    return data

@app.get("/alerts", response_model=List[Alert])
def get_alerts(start_date: str, days: int = 7):
    """Generates alerts if competitor prices changed by >= 3000 JPY or sold out"""
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    alerts = []
    alert_id = 1

    for i in range(days):
        current_date = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        comp_data = generate_mock_competitor_data(current_date)

        for c in comp_data:
            if c.is_fully_booked:
                alerts.append(Alert(
                    id=alert_id, date=current_date,
                    message=f"{c.competitor_name} が満室になりました。需要が非常に高まっています。",
                    type="sold_out"
                ))
                alert_id += 1
            elif c.difference >= 3000:
                alerts.append(Alert(
                    id=alert_id, date=current_date,
                    message=f"{c.competitor_name} が {current_date} の料金を +{c.difference:,}円 大幅に値上げしました！",
                    type="increase"
                ))
                alert_id += 1
            elif c.difference <= -3000:
                alerts.append(Alert(
                    id=alert_id, date=current_date,
                    message=f"{c.competitor_name} が {current_date} の料金を {c.difference:,}円 大幅に値下げしました。",
                    type="decrease"
                ))
                alert_id += 1

    return alerts

@app.get("/recommendation", response_model=MarketRecommendation)
def get_recommendation(date: str):
    """Simple AI recommendation based strictly on today's competitor prices"""
    comp_data = generate_mock_competitor_data(date)

    # Calculate average competitor price (excluding sold out)
    available_comps = [c for c in comp_data if not c.is_fully_booked]
    if not available_comps:
         return MarketRecommendation(
            date=date,
            suggested_price=int(my_facility.base_price * 1.5),
            reasoning="ベンチマーク施設がすべて満室です。強気の価格設定（通常比1.5倍）を推奨します。"
        )

    avg_comp_price = sum(c.price_today for c in available_comps) / len(available_comps)

    # Check if there was a major increase
    major_increases = [c for c in available_comps if c.difference >= 3000]

    if major_increases:
        suggested = int(avg_comp_price * 0.95) # Just below the increased market
        # Round to nearest 100 before formatting reasoning text
        suggested = round(suggested / 100) * 100
        names = "、".join([c.competitor_name for c in major_increases])
        reasoning = f"{names} が大幅に値上げしています。周辺需要が高まっているため、市場平均に近い {suggested:,}円 に引き上げることを推奨します。"
    else:
        suggested = int(my_facility.base_price)
        # Round to nearest 100
        suggested = round(suggested / 100) * 100
        reasoning = "競合の価格に大きな変動はありません。現在の基本価格を維持して様子を見ることを推奨します。"

    return MarketRecommendation(
        date=date,
        suggested_price=suggested,
        reasoning=reasoning
    )
