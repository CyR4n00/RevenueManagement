from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal, Optional

from database import Base


class DBFacility(Base):
    __tablename__ = "facilities"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    base_price = Column(Integer, nullable=False)
    min_price = Column(Integer, nullable=False, default=5000)
    max_price = Column(Integer, nullable=False, default=30000)


class DBCompetitor(Base):
    __tablename__ = "competitors"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)


class DBCompetitorPrice(Base):
    __tablename__ = "competitor_prices"
    __table_args__ = (UniqueConstraint("competitor_id", "date", name="uq_competitor_price_date"),)

    id = Column(Integer, primary_key=True)
    date = Column(String, nullable=False, index=True)  # ISO-8601 date, kept portable for SQLite
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)
    price = Column(Integer, nullable=False)
    is_fully_booked = Column(Boolean, nullable=False, default=False)
    scraped_at = Column(String, nullable=False)
    source = Column(String, nullable=False, default="unknown")
    competitor = relationship("DBCompetitor")


class DBSubscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False, unique=True)
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)
    price_id = Column(String)
    status = Column(String, nullable=False, default="inactive")
    updated_at = Column(String, nullable=False)


class Facility(BaseModel):
    id: int
    name: str
    base_price: int
    min_price: int
    max_price: int
    model_config = ConfigDict(from_attributes=True)


class FacilityUpdate(BaseModel):
    min_price: int = Field(ge=0, le=1_000_000)
    max_price: int = Field(ge=0, le=1_000_000)

    @model_validator(mode="after")
    def minimum_must_not_exceed_maximum(self):
        if self.min_price > self.max_price:
            raise ValueError("min_price must be less than or equal to max_price")
        return self


class Competitor(BaseModel):
    id: int
    name: str
    url: str
    model_config = ConfigDict(from_attributes=True)


class CompetitorUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=2048)


class CompetitorPrice(BaseModel):
    date: str
    competitor_id: int
    competitor_name: str
    price_today: int
    price_yesterday: int
    difference: int
    is_fully_booked: bool
    source: Literal["apify", "simulation", "unknown"]


class Alert(BaseModel):
    id: int
    date: str
    message: str
    type: Literal["increase", "decrease", "sold_out"]


class MarketRecommendation(BaseModel):
    date: str
    suggested_price: int
    suggested_rank: str
    reasoning: str


class IntegrationStatus(BaseModel):
    environment: Literal["demo", "production"]
    apify_configured: bool
    line_messaging_configured: bool
    stripe_configured: bool
    simulation_enabled: bool
    ota_sources: list["OtaSourceStatus"]


class OtaSourceStatus(BaseModel):
    key: str
    name: str
    status: Literal["pending", "approved", "disabled"]
    actor_configured: bool


class PmsProfile(BaseModel):
    id: str
    name: str
    verified: bool
    description: str


class CheckoutSession(BaseModel):
    checkout_url: str


class BillingStatus(BaseModel):
    configured: bool
    subscription_status: str
