from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import datetime
import random
from ml_model import ml_predictor

app = FastAPI(title="Revenue Control System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Facility(BaseModel):
    id: int
    name: str
    base_price: int
    min_price: int
    max_price: int
    total_rooms: int
    plan: str # "Standard", "Pro", "Enterprise"

class Rule(BaseModel):
    id: int
    facility_id: int
    occupancy_threshold_percent: float
    price_multiplier: float
    active: bool = True

class OccupancyData(BaseModel):
    facility_id: int
    date: str
    booked_rooms: int

class PriceRecommendation(BaseModel):
    facility_id: int
    date: str
    recommended_price_rule_based: int
    rule_applied: Optional[str]
    recommended_price_ml_based: Optional[int]
    event_multiplier: float
    final_price: int # Price after limits and all calculations

class PerformanceData(BaseModel):
    facility_id: int
    month: str
    target_revenue: int
    actual_revenue: int

# In-memory storage for demonstration
facilities = [
    Facility(id=1, name="サンプル ホテル", base_price=10000, min_price=6000, max_price=20000, total_rooms=50, plan="Enterprise"),
    Facility(id=2, name="サンプル ゲストハウス", base_price=5000, min_price=3000, max_price=10000, total_rooms=10, plan="Standard")
]

rules = [
    Rule(id=1, facility_id=1, occupancy_threshold_percent=0.8, price_multiplier=1.3, active=True),
    Rule(id=2, facility_id=1, occupancy_threshold_percent=0.5, price_multiplier=1.1, active=True),
    Rule(id=3, facility_id=2, occupancy_threshold_percent=0.9, price_multiplier=1.5, active=True)
]

# Mock Events database (date string to event multiplier)
mock_events = {
    # Let's say weekends have local events
}

def get_event_multiplier(date_str: str) -> float:
    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    # Mock event: 20% increase on Fridays and Saturdays due to local events
    if target_date.weekday() in [4, 5]:
        return 1.2
    return 1.0

# dynamic generation for mock occupancy
def get_mock_occupancy(facility_id: int, date_str: str) -> int:
    facility = next((f for f in facilities if f.id == facility_id), None)
    if not facility:
        return 0

    seed_str = f"{facility_id}_{date_str}"
    random.seed(seed_str)

    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    if target_date.weekday() >= 5:
        base_rate = random.uniform(0.7, 1.0)
    else:
        base_rate = random.uniform(0.3, 0.7)

    return int(base_rate * facility.total_rooms)


@app.on_event("startup")
def startup_event():
    print("Training ML model with historical dummy data...")
    all_data = []
    for facility in facilities:
        df = ml_predictor.generate_dummy_data(facility.id, facility.base_price, facility.total_rooms)
        all_data.append(df)

    if all_data:
        combined_df = __import__("pandas").concat(all_data)
        ml_predictor.train(combined_df)
    print("ML model trained successfully!")

@app.get("/facilities", response_model=List[Facility])
def get_facilities():
    return facilities

@app.get("/rules", response_model=List[Rule])
def get_rules(facility_id: Optional[int] = None):
    if facility_id:
        return [r for r in rules if r.facility_id == facility_id]
    return rules

@app.put("/rules/{rule_id}/toggle", response_model=Rule)
def toggle_rule(rule_id: int):
    rule = next((r for r in rules if r.id == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.active = not rule.active
    return rule

@app.get("/occupancy", response_model=List[OccupancyData])
def get_occupancy(facility_id: Optional[int] = None, date: Optional[str] = None):
    if not date:
        date = datetime.date.today().isoformat()

    result = []
    target_facilities = [f for f in facilities if f.id == facility_id] if facility_id else facilities

    for f in target_facilities:
        booked = get_mock_occupancy(f.id, date)
        result.append(OccupancyData(facility_id=f.id, date=date, booked_rooms=booked))

    return result

@app.get("/recommendations/{facility_id}/{date}", response_model=PriceRecommendation)
def get_recommendation(facility_id: int, date: str):
    facility = next((f for f in facilities if f.id == facility_id), None)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    booked_rooms = get_mock_occupancy(facility_id, date)
    occupancy_rate = booked_rooms / facility.total_rooms if facility.total_rooms > 0 else 0

    # Event Multiplier (Pro & Enterprise feature)
    event_mult = 1.0
    if facility.plan in ["Pro", "Enterprise"]:
        event_mult = get_event_multiplier(date)

    # 1. Rule-based recommendation (Standard & Pro)
    facility_rules = sorted(
        [r for r in rules if r.facility_id == facility_id and r.active],
        key=lambda x: x.occupancy_threshold_percent,
        reverse=True
    )

    recommended_price_rule = facility.base_price
    rule_applied = None

    for rule in facility_rules:
        if occupancy_rate >= rule.occupancy_threshold_percent:
            recommended_price_rule = int(facility.base_price * rule.price_multiplier)
            rule_applied = f"稼働率 {int(rule.occupancy_threshold_percent*100)}% 以上 (x{rule.price_multiplier})"
            break

    # Apply event multiplier to rule-based price
    recommended_price_rule = int(recommended_price_rule * event_mult)

    # 2. ML-based recommendation (Enterprise only feature)
    recommended_price_ml = None
    if facility.plan == "Enterprise":
        recommended_price_ml = ml_predictor.predict_optimal_price(
            date_str=date,
            current_occupancy_rate=occupancy_rate,
            base_price=facility.base_price
        )
        # Assuming ML already factors in day of week/season, but we can explicitly cap it

    # 3. Final Price Calculation (Choose Best depending on plan, apply Limits)
    raw_final_price = recommended_price_ml if (recommended_price_ml is not None) else recommended_price_rule

    # Apply Safety Limits (Min/Max Price constraint)
    final_price = max(facility.min_price, min(raw_final_price, facility.max_price))

    return PriceRecommendation(
        facility_id=facility_id,
        date=date,
        recommended_price_rule_based=recommended_price_rule,
        rule_applied=rule_applied,
        recommended_price_ml_based=recommended_price_ml,
        event_multiplier=event_mult,
        final_price=final_price
    )

@app.get("/performance/{facility_id}", response_model=List[PerformanceData])
def get_performance(facility_id: int):
    # Mock performance data for PDCA cycle verification
    months = ["2026-03", "2026-04", "2026-05"]
    facility = next((f for f in facilities if f.id == facility_id), None)
    base_rev = facility.base_price * facility.total_rooms * 20 if facility else 0

    return [
        PerformanceData(facility_id=facility_id, month=months[0], target_revenue=int(base_rev*1.0), actual_revenue=int(base_rev*0.95)),
        PerformanceData(facility_id=facility_id, month=months[1], target_revenue=int(base_rev*1.05), actual_revenue=int(base_rev*1.08)),
        PerformanceData(facility_id=facility_id, month=months[2], target_revenue=int(base_rev*1.1), actual_revenue=int(base_rev*1.15))
    ]
