from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# --- SQLAlchemy Models (Database) ---

class DBSystemConfig(Base):
    __tablename__ = "system_config"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

class DBFacility(Base):
    __tablename__ = "facilities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    base_price = Column(Integer)
    min_price = Column(Integer, default=5000)
    max_price = Column(Integer, default=30000)

class DBPriceRank(Base):
    __tablename__ = "price_ranks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Integer)

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

class SystemConfig(BaseModel):
    key: str
    value: str
    model_config = ConfigDict(from_attributes=True)

class Facility(BaseModel):
    id: int
    name: str
    base_price: int
    min_price: int = 5000
    max_price: int = 30000
    model_config = ConfigDict(from_attributes=True)

class PriceRank(BaseModel):
    id: Optional[int] = None
    name: str
    price: int
    model_config = ConfigDict(from_attributes=True)

class Competitor(BaseModel):
    id: int
    name: str
    url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

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
