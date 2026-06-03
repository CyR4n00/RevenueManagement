from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime

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
    occupancy_threshold_percent: float # e.g. 0.8 for 80%
    price_multiplier: float # e.g. 1.2 for 20% increase
    active: bool = True

class OccupancyData(BaseModel):
    facility_id: int
    date: str # YYYY-MM-DD
    booked_rooms: int

class PriceRecommendation(BaseModel):
    facility_id: int
    date: str
    recommended_price: int
    rule_applied: Optional[str]

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

    facility_rules = sorted(
        [r for r in rules if r.facility_id == facility_id and r.active],
        key=lambda x: x.occupancy_threshold_percent,
        reverse=True
    )

    recommended_price = facility.base_price
    rule_applied = None

    for rule in facility_rules:
        if occupancy_rate >= rule.occupancy_threshold_percent:
            recommended_price = int(facility.base_price * rule.price_multiplier)
            rule_applied = f"Occupancy >= {rule.occupancy_threshold_percent*100}%"
            break

    return PriceRecommendation(
        facility_id=facility_id,
        date=date,
        recommended_price=recommended_price,
        rule_applied=rule_applied
    )

@app.post("/rules", response_model=Rule)
def create_rule(rule: Rule):
    rules.append(rule)
    return rule
