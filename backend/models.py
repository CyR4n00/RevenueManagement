from pydantic import BaseModel
from typing import List, Optional

class Facility(BaseModel):
    id: int
    name: str
    base_price: int

class Competitor(BaseModel):
    id: int
    name: str

class CompetitorPrice(BaseModel):
    date: str
    competitor_id: int
    competitor_name: str
    price_today: int
    price_yesterday: int
    difference: int
    is_fully_booked: bool

class Alert(BaseModel):
    id: int
    date: str
    message: str
    type: str # 'increase', 'decrease', 'sold_out'

class MarketRecommendation(BaseModel):
    date: str
    suggested_price: int
    reasoning: str
