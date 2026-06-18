from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel
from typing import List, Optional

# --- SQLAlchemy Models (Database) ---

class DBFacility(Base):
    __tablename__ = "facilities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    base_price = Column(Integer)

class DBCompetitor(Base):
    __tablename__ = "competitors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String)

class DBCompetitorPrice(Base):
    __tablename__ = "competitor_prices"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"))
    price = Column(Integer)
    is_fully_booked = Column(Boolean, default=False)
    scraped_at = Column(String)

    competitor = relationship("DBCompetitor")

# --- Pydantic Models (API) ---

class Facility(BaseModel):
    id: int
    name: str
    base_price: int
    class Config:
        orm_mode = True

class Competitor(BaseModel):
    id: int
    name: str
    url: Optional[str] = None
    class Config:
        orm_mode = True

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
