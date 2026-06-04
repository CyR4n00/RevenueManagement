from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
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
    total_rooms: int

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

# In-memory storage for demonstration
facilities = [
    Facility(id=1, name="Sample Hotel", base_price=10000, total_rooms=50),
    Facility(id=2, name="Sample Space", base_price=5000, total_rooms=10)
]

rules = [
    Rule(id=1, facility_id=1, occupancy_threshold_percent=0.8, price_multiplier=1.3, active=True),
    Rule(id=2, facility_id=1, occupancy_threshold_percent=0.5, price_multiplier=1.1, active=True),
    Rule(id=3, facility_id=2, occupancy_threshold_percent=0.9, price_multiplier=1.5, active=True)
]

# dynamic generation for mock
def get_mock_occupancy(facility_id: int, date_str: str) -> int:
    facility = next((f for f in facilities if f.id == facility_id), None)
    if not facility:
        return 0

    # Use date as a seed so it's consistent for the same date but varies across dates
    seed_str = f"{facility_id}_{date_str}"
    random.seed(seed_str)

    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    # Simulate higher demand on weekends
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
    # Dynamic dummy data for demo purposes
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

    # 1. Rule-based recommendation
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
            rule_applied = f"Occupancy >= {rule.occupancy_threshold_percent*100}% (x{rule.price_multiplier})"
            break

    # 2. ML-based recommendation
    recommended_price_ml = ml_predictor.predict_optimal_price(
        date_str=date,
        current_occupancy_rate=occupancy_rate,
        base_price=facility.base_price
    )

    return PriceRecommendation(
        facility_id=facility_id,
        date=date,
        recommended_price_rule_based=recommended_price_rule,
        rule_applied=rule_applied,
        recommended_price_ml_based=recommended_price_ml
    )
