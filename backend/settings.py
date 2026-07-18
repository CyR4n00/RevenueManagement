"""Runtime configuration.  Secrets remain in environment variables, never in the database."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def _ota_status(name: str) -> str:
    status = os.getenv(name, "pending").strip().lower()
    if status not in {"pending", "approved", "disabled"}:
        raise RuntimeError(f"{name} must be pending, approved, or disabled")
    return status


@dataclass(frozen=True)
class OtaSourceRuntime:
    key: str
    name: str
    domains: tuple[str, ...]
    status: str
    actor_id: str


@dataclass(frozen=True)
class Settings:
    environment: str
    cors_origins: list[str]
    admin_api_key: str
    apify_api_token: str
    apify_actor_booking: str
    apify_actor_airbnb: str
    apify_actor_jalan: str
    apify_actor_rakuten: str
    ota_status_booking: str
    ota_status_airbnb: str
    ota_status_jalan: str
    ota_status_rakuten: str
    allow_simulated_data: bool
    line_channel_access_token: str
    line_user_id: str
    frontend_app_url: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_price_id_pro: str
    scheduler_enabled: bool
    demo_sync_interval_minutes: int
    daily_sync_hour: int
    daily_sync_minute: int

    def source_for_url(self, url: str) -> OtaSourceRuntime | None:
        host = url.lower()
        if "booking.com" in host:
            return OtaSourceRuntime("booking", "Booking.com", ("booking.com",), self.ota_status_booking, self.apify_actor_booking)
        if "airbnb." in host:
            return OtaSourceRuntime("airbnb", "Airbnb", ("airbnb.com",), self.ota_status_airbnb, self.apify_actor_airbnb)
        if "jalan.net" in host:
            return OtaSourceRuntime("jalan", "じゃらんnet", ("jalan.net",), self.ota_status_jalan, self.apify_actor_jalan)
        if "rakuten.co.jp" in host:
            return OtaSourceRuntime("rakuten", "楽天トラベル", ("travel.rakuten.co.jp",), self.ota_status_rakuten, self.apify_actor_rakuten)
        return None

    def ota_sources(self) -> tuple[OtaSourceRuntime, ...]:
        return (
            OtaSourceRuntime("booking", "Booking.com", ("booking.com",), self.ota_status_booking, self.apify_actor_booking),
            OtaSourceRuntime("airbnb", "Airbnb", ("airbnb.com",), self.ota_status_airbnb, self.apify_actor_airbnb),
            OtaSourceRuntime("jalan", "じゃらんnet", ("jalan.net",), self.ota_status_jalan, self.apify_actor_jalan),
            OtaSourceRuntime("rakuten", "楽天トラベル", ("travel.rakuten.co.jp",), self.ota_status_rakuten, self.apify_actor_rakuten),
        )


@lru_cache
def get_settings() -> Settings:
    environment = os.getenv("APP_ENV", "demo").lower()
    if environment not in {"demo", "production"}:
        raise RuntimeError("APP_ENV must be either demo or production")
    origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
    return Settings(
        environment=environment,
        cors_origins=origins,
        admin_api_key=os.getenv("ADMIN_API_KEY", ""),
        apify_api_token=os.getenv("APIFY_API_TOKEN", ""),
        apify_actor_booking=os.getenv("APIFY_ACTOR_BOOKING", ""),
        apify_actor_airbnb=os.getenv("APIFY_ACTOR_AIRBNB", ""),
        apify_actor_jalan=os.getenv("APIFY_ACTOR_JALAN", ""),
        apify_actor_rakuten=os.getenv("APIFY_ACTOR_RAKUTEN", ""),
        ota_status_booking=_ota_status("OTA_STATUS_BOOKING"),
        ota_status_airbnb=_ota_status("OTA_STATUS_AIRBNB"),
        ota_status_jalan=_ota_status("OTA_STATUS_JALAN"),
        ota_status_rakuten=_ota_status("OTA_STATUS_RAKUTEN"),
        allow_simulated_data=_bool("ALLOW_SIMULATED_DATA", environment == "demo"),
        line_channel_access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""),
        line_user_id=os.getenv("LINE_USER_ID", ""),
        frontend_app_url=os.getenv("FRONTEND_APP_URL", origins[0]).rstrip("/"),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY", ""),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        stripe_price_id_pro=os.getenv("STRIPE_PRICE_ID_PRO", ""),
        scheduler_enabled=_bool("SCHEDULER_ENABLED", True),
        demo_sync_interval_minutes=max(5, int(os.getenv("DEMO_SYNC_INTERVAL_MINUTES", "30"))),
        daily_sync_hour=int(os.getenv("DAILY_SYNC_HOUR", "10")),
        daily_sync_minute=int(os.getenv("DAILY_SYNC_MINUTE", "0")),
    )
