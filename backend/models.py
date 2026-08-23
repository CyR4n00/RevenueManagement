"""Database and API models for the customer-isolated SaaS application."""

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from database import Base, is_sqlite


def id_type():
    """Use native UUIDs in PostgreSQL while keeping readable demo IDs in SQLite."""
    return String(36) if is_sqlite else Uuid(as_uuid=False)


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class DBOrganization(Base):
    __tablename__ = "organizations"

    id = Column(id_type(), primary_key=True, default=new_id)
    name = Column(String(160), nullable=False)
    stripe_customer_id = Column(String, unique=True)
    notification_email = Column(String(320))
    email_notifications_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)


class DBOrganizationMember(Base):
    __tablename__ = "organization_members"

    organization_id = Column(id_type(), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(id_type(), primary_key=True)
    role = Column(String(16), nullable=False, default="owner")
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    organization = relationship("DBOrganization")


class DBFacility(Base):
    __tablename__ = "facilities"

    id = Column(id_type(), primary_key=True, default=new_id)
    organization_id = Column(id_type(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    address = Column(Text)
    base_price = Column(Integer, nullable=False)
    min_price = Column(Integer, nullable=False)
    max_price = Column(Integer, nullable=False)
    onboarding_completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    organization = relationship("DBOrganization")
    rate_ranks = relationship(
        "DBRateRank", cascade="all, delete-orphan", order_by="DBRateRank.sort_order"
    )


class DBRateRank(Base):
    __tablename__ = "facility_rate_ranks"
    __table_args__ = (
        UniqueConstraint("facility_id", "label", name="uq_facility_rate_rank_label"),
        UniqueConstraint("facility_id", "sort_order", name="uq_facility_rate_rank_order"),
    )

    id = Column(id_type(), primary_key=True, default=new_id)
    facility_id = Column(id_type(), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(1), nullable=False)
    price_jpy = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    facility = relationship("DBFacility", back_populates="rate_ranks")


class DBCompetitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("facility_id", "canonical_url", name="uq_competitor_facility_url"),)

    id = Column(id_type(), primary_key=True, default=new_id)
    facility_id = Column(id_type(), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
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
    competitor_id = Column(id_type(), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    stay_date = Column(Date, nullable=False)
    price_jpy = Column(Integer)
    is_fully_booked = Column(Boolean, nullable=False, default=False)
    availability_status = Column(String(16), nullable=False, default="unknown")
    remaining_rooms = Column(Integer)
    availability_source = Column(String(20), nullable=False, default="inferred")
    collected_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    collection_source = Column(String(16), nullable=False)
    competitor = relationship("DBCompetitor")


class DBCompetitorPriceObservation(Base):
    """An immutable collection event used for price-change calculations."""

    __tablename__ = "competitor_price_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(id_type(), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    stay_date = Column(Date, nullable=False)
    price_jpy = Column(Integer)
    is_fully_booked = Column(Boolean, nullable=False, default=False)
    availability_status = Column(String(16), nullable=False, default="unknown")
    remaining_rooms = Column(Integer)
    availability_source = Column(String(20), nullable=False, default="inferred")
    collected_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    collection_source = Column(String(16), nullable=False)
    competitor = relationship("DBCompetitor")


class DBCompetitorCollectionRun(Base):
    """A reserved Actor run; it enforces each provider's daily collection cap."""

    __tablename__ = "competitor_collection_runs"
    __table_args__ = (UniqueConstraint("competitor_id", "collection_day", "slot", name="uq_competitor_collection_run_slot"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(id_type(), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_day = Column(Date, nullable=False)
    slot = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    collection_source = Column(String(16), nullable=False, default="apify")
    competitor = relationship("DBCompetitor")


class DBNotificationDelivery(Base):
    """A successful daily email alert batch, used to prevent duplicate sends."""

    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("organization_id", "fingerprint", name="uq_notification_delivery_fingerprint"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(id_type(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    fingerprint = Column(String(64), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)


class DBSubscription(Base):
    __tablename__ = "subscriptions"

    id = Column(id_type(), primary_key=True, default=new_id)
    organization_id = Column(id_type(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)
    stripe_price_id = Column(String)
    status = Column(String(32), nullable=False, default="inactive")
    current_period_end = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    organization = relationship("DBOrganization")


class RateRank(BaseModel):
    label: str
    price_jpy: int
    sort_order: int
    model_config = ConfigDict(from_attributes=True)


class RateRankInput(BaseModel):
    label: str = Field(pattern=r"^[A-Z]$")
    price_jpy: int = Field(ge=0, le=1_000_000)


def validate_rate_ranks(ranks: list[RateRankInput]) -> list[RateRankInput]:
    expected = [chr(ord("A") + index) for index in range(len(ranks))]
    labels = [item.label for item in ranks]
    if labels != expected:
        raise ValueError("rate rank labels must be sequential from A")
    prices = [item.price_jpy for item in ranks]
    if any(left <= right for left, right in zip(prices, prices[1:])):
        raise ValueError("rate rank prices must strictly decrease from A")
    return ranks


class Facility(BaseModel):
    id: str
    name: str
    address: str | None = None
    base_price: int
    min_price: int
    max_price: int
    rate_ranks: list[RateRank] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class FacilityUpdate(BaseModel):
    min_price: int = Field(ge=0, le=1_000_000)
    max_price: int = Field(ge=0, le=1_000_000)
    rate_ranks: list[RateRankInput] = Field(min_length=4, max_length=12)

    @model_validator(mode="after")
    def minimum_must_not_exceed_maximum(self):
        if self.min_price > self.max_price:
            raise ValueError("min_price must be less than or equal to max_price")
        validate_rate_ranks(self.rate_ranks)
        if self.rate_ranks[0].price_jpy != self.max_price or self.rate_ranks[-1].price_jpy != self.min_price:
            raise ValueError("min_price and max_price must match the last and first rate ranks")
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
    rate_ranks: list[RateRankInput] = Field(min_length=4, max_length=12)
    competitors: list[CompetitorInput] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def guardrail_range_is_valid(self):
        if self.min_price > self.max_price:
            raise ValueError("min_price must be less than or equal to max_price")
        validate_rate_ranks(self.rate_ranks)
        if self.rate_ranks[0].price_jpy != self.max_price or self.rate_ranks[-1].price_jpy != self.min_price:
            raise ValueError("min_price and max_price must match the last and first rate ranks")
        return self


class OnboardingStatus(BaseModel):
    subscription_status: str = "inactive"
    onboarding_complete: bool = False
    facility: Facility | None = None


class NotificationSettings(BaseModel):
    email: str
    enabled: bool
    delivery_configured: bool = False


class NotificationSettingsUpdate(BaseModel):
    enabled: bool


class CompetitorPrice(BaseModel):
    date: str
    competitor_id: str
    competitor_name: str
    price_today: int
    price_yesterday: int
    difference: int
    comparison_available: bool = False
    comparison_days: int = 1
    was_fully_booked: bool | None = None
    is_fully_booked: bool
    availability_status: Literal["available", "limited", "sold_out", "unknown"] = "unknown"
    remaining_rooms: int | None = None
    availability_source: Literal["explicit_count", "symbol", "inferred", "unknown"] = "unknown"
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
    email_delivery_configured: bool
    stripe_configured: bool
    simulation_enabled: bool
    ota_sources: list["OtaSourceStatus"]


class OtaSourceStatus(BaseModel):
    key: str
    name: str
    status: Literal["pending", "approved", "disabled"]
    actor_configured: bool


class CheckoutSession(BaseModel):
    checkout_url: str


class BillingStatus(BaseModel):
    configured: bool
    subscription_status: str
    plan: Literal["standard", "upgrade"] = "standard"
    max_horizon_days: int = 180
    max_competitors: int = 3
