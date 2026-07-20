"""Database and API models for the customer-isolated SaaS application."""

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class DBOrganization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String(160), nullable=False)
    stripe_customer_id = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)


class DBOrganizationMember(Base):
    __tablename__ = "organization_members"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), primary_key=True)
    role = Column(String(16), nullable=False, default="owner")
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    organization = relationship("DBOrganization")


class DBFacility(Base):
    __tablename__ = "facilities"

    id = Column(String(36), primary_key=True, default=new_id)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    address = Column(Text)
    base_price = Column(Integer, nullable=False)
    min_price = Column(Integer, nullable=False)
    max_price = Column(Integer, nullable=False)
    onboarding_completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    organization = relationship("DBOrganization")


class DBCompetitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("facility_id", "canonical_url", name="uq_competitor_facility_url"),)

    id = Column(String(36), primary_key=True, default=new_id)
    facility_id = Column(String(36), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    ota_source_key = Column(String(32), nullable=False)
    name = Column(String(160))
    url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    facility = relationship("DBFacility")


class DBCompetitorPrice(Base):
    __tablename__ = "competitor_prices"
    __table_args__ = (UniqueConstraint("competitor_id", "stay_date", name="uq_competitor_price_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(String(36), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    stay_date = Column(Date, nullable=False)
    price_jpy = Column(Integer)
    is_fully_booked = Column(Boolean, nullable=False, default=False)
    collected_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    collection_source = Column(String(16), nullable=False)
    competitor = relationship("DBCompetitor")


class DBCompetitorPriceObservation(Base):
    """An immutable collection event used for price-change calculations."""

    __tablename__ = "competitor_price_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(String(36), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    stay_date = Column(Date, nullable=False)
    price_jpy = Column(Integer)
    is_fully_booked = Column(Boolean, nullable=False, default=False)
    collected_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    collection_source = Column(String(16), nullable=False)
    competitor = relationship("DBCompetitor")


class DBSubscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=new_id)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)
    stripe_price_id = Column(String)
    status = Column(String(32), nullable=False, default="inactive")
    current_period_end = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    organization = relationship("DBOrganization")


class Facility(BaseModel):
    id: str
    name: str
    address: str | None = None
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
    id: str
    name: str | None = None
    url: str
    model_config = ConfigDict(from_attributes=True)


class CompetitorUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=2048)


class CompetitorInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=2048)


class OnboardingRequest(BaseModel):
    facility_name: str = Field(min_length=1, max_length=160)
    address: str = Field(min_length=1, max_length=500)
    base_price: int = Field(ge=0, le=1_000_000)
    min_price: int = Field(ge=0, le=1_000_000)
    max_price: int = Field(ge=0, le=1_000_000)
    competitors: list[CompetitorInput] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def guardrail_range_is_valid(self):
        if self.min_price > self.max_price:
            raise ValueError("min_price must be less than or equal to max_price")
        return self


class OnboardingStatus(BaseModel):
    subscription_status: str = "inactive"
    onboarding_complete: bool = False
    facility: Facility | None = None


class CompetitorPrice(BaseModel):
    date: str
    competitor_id: str
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
