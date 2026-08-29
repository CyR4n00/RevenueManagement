"""Runtime configuration.  Secrets remain in environment variables, never in the database."""

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

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


def _sync_hours() -> tuple[int, ...]:
    """Return one or two Tokyo collection times, preserving the legacy setting."""
    raw = os.getenv("DAILY_SYNC_HOURS", os.getenv("DAILY_SYNC_HOUR", "10")).replace(";", ",")
    try:
        hours = tuple(sorted({int(value.strip()) for value in raw.split(",") if value.strip()}))
    except ValueError as exc:
        raise RuntimeError("DAILY_SYNC_HOURS must be comma-separated hours from 0 to 23") from exc
    if not hours or len(hours) > 2 or any(hour < 0 or hour > 23 for hour in hours):
        raise RuntimeError("DAILY_SYNC_HOURS must contain one or two hours from 0 to 23")
    return hours


def _csv_values(name: str) -> tuple[str, ...]:
    return tuple(value.strip().lower() for value in os.getenv(name, "").split(",") if value.strip())


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
    supabase_url: str
    supabase_publishable_key: str
    supabase_auth_required: bool
    demo_bypass_billing: bool
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
    resend_api_key: str
    alert_from_email: str
    frontend_app_url: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_price_id_pro: str
    stripe_price_id_upgrade: str
    scheduler_enabled: bool
    demo_sync_interval_minutes: int
    daily_sync_hours: tuple[int, ...]
    daily_sync_minute: int
    sync_lookahead_days: int
    apify_monthly_run_limit: int
    apify_actor_memory_mbytes: int
    operator_emails: tuple[str, ...]
    business_name: str
    business_representative: str
    business_address: str
    business_phone: str
    support_email: str

    def source_for_url(self, url: str) -> OtaSourceRuntime | None:
        host = (urlparse(url).hostname or "").lower()
        if host == "www.booking.com" or host.endswith(".booking.com"):
            return OtaSourceRuntime("booking", "Booking.com", ("booking.com",), self.ota_status_booking, self.apify_actor_booking)
        if host == "airbnb.com" or host.endswith(".airbnb.com"):
            return OtaSourceRuntime("airbnb", "Airbnb", ("airbnb.com",), self.ota_status_airbnb, self.apify_actor_airbnb)
        if host in {"jalan.net", "www.jalan.net"}:
            return OtaSourceRuntime("jalan", "じゃらんnet", ("jalan.net",), self.ota_status_jalan, self.apify_actor_jalan)
        if host == "travel.rakuten.co.jp":
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
        supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
        supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
        supabase_auth_required=_bool("SUPABASE_AUTH_REQUIRED", environment == "production"),
        demo_bypass_billing=_bool("DEMO_BYPASS_BILLING", False),
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
        resend_api_key=os.getenv("RESEND_API_KEY", ""),
        alert_from_email=os.getenv("ALERT_FROM_EMAIL", ""),
        frontend_app_url=os.getenv("FRONTEND_APP_URL", origins[0]).rstrip("/"),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY", ""),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        stripe_price_id_pro=os.getenv("STRIPE_PRICE_ID_PRO", ""),
        stripe_price_id_upgrade=os.getenv("STRIPE_PRICE_ID_UPGRADE", ""),
        scheduler_enabled=_bool("SCHEDULER_ENABLED", True),
        demo_sync_interval_minutes=max(5, int(os.getenv("DEMO_SYNC_INTERVAL_MINUTES", "30"))),
        daily_sync_hours=_sync_hours(),
        daily_sync_minute=int(os.getenv("DAILY_SYNC_MINUTE", "0")),
        sync_lookahead_days=max(1, min(90, int(os.getenv("SYNC_LOOKAHEAD_DAYS", "90")))),
        apify_monthly_run_limit=max(0, int(os.getenv("APIFY_MONTHLY_RUN_LIMIT", "0"))),
        # The Actors are network-bound and do not need Apify's former 4 GiB
        # default.  Two GiB keeps three Playwright pages stable while roughly
        # halving compute-unit consumption per run.
        apify_actor_memory_mbytes=max(1024, min(4096, int(os.getenv("APIFY_ACTOR_MEMORY_MBYTES", "2048")))),
        operator_emails=_csv_values("OPERATOR_EMAILS"),
        business_name=os.getenv("BUSINESS_NAME", "").strip(),
        business_representative=os.getenv("BUSINESS_REPRESENTATIVE", "").strip(),
        business_address=os.getenv("BUSINESS_ADDRESS", "").strip(),
        business_phone=os.getenv("BUSINESS_PHONE", "").strip(),
        support_email=os.getenv("SUPPORT_EMAIL", "").strip(),
    )
