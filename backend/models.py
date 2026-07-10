from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# --- SQLAlchemy Models (Database) ---

class DBFacility(Base):
    __tablename__ = "facilities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    base_price = Column(Integer)
    min_price = Column(Integer, default=5000)
    max_price = Column(Integer, default=30000)
    notify_line = Column(Boolean, default=True)
    notify_email = Column(Boolean, default=False)
    email_address = Column(String, default="")
    notify_threshold = Column(Integer, default=3000)
    notify_timing = Column(String, default="morning")

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
    min_price: int = 5000
    max_price: int = 30000
    notify_line: bool = True
    notify_email: bool = False
    email_address: str = ""
    notify_threshold: int = 3000
    notify_timing: str = "morning"
    model_config = ConfigDict(from_attributes=True)

class FacilityUpdate(BaseModel):
    min_price: int
    max_price: int
    notify_line: bool
    notify_email: bool
    email_address: str
    notify_threshold: int
    notify_timing: str

class Competitor(BaseModel):
    id: int
    name: str
    url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class CompetitorUpdate(BaseModel):
    id: Optional[int] = None
    name: str
    url: str

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
    suggested_rank: str
    reasoning: str
