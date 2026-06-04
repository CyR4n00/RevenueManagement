from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime
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
    Rule(id=1, facility_id=1, occupancy_threshold_percent=0.8, price_multiplier=1.3),
    Rule(id=2, facility_id=1, occupancy_threshold_percent=0.5, price_multiplier=1.1),
    Rule(id=3, facility_id=2, occupancy_threshold_percent=0.9, price_multiplier=1.5)
]

occupancy_db = [
    OccupancyData(facility_id=1, date=datetime.date.today().isoformat(), booked_rooms=42), # 84% occupancy
    OccupancyData(facility_id=2, date=datetime.date.today().isoformat(), booked_rooms=9) # 90% occupancy
]

# Initialize and train ML model with dummy data on startup
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

@app.get("/occupancy", response_model=List[OccupancyData])
def get_occupancy(facility_id: Optional[int] = None):
    if facility_id:
        return [o for o in occupancy_db if o.facility_id == facility_id]
    return occupancy_db

@app.get("/recommendations/{facility_id}/{date}", response_model=PriceRecommendation)
def get_recommendation(facility_id: int, date: str):
    facility = next((f for f in facilities if f.id == facility_id), None)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    occupancy = next((o for o in occupancy_db if o.facility_id == facility_id and o.date == date), None)
    booked_rooms = occupancy.booked_rooms if occupancy else 0

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
            rule_applied = f"Occupancy >= {rule.occupancy_threshold_percent*100}%"
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

@app.post("/rules", response_model=Rule)
def create_rule(rule: Rule):
    rules.append(rule)
    return rule
