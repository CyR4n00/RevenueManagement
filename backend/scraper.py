"""OTA data collection through Apify only.

The app deliberately does not perform direct OTA requests.  Each actor must be
validated against the OTA's terms and output a nightly rate in its dataset.
"""

import datetime as dt
import random
import re
from dataclasses import dataclass
from typing import Any, Iterable

from apify_client import ApifyClient

from settings import Settings, get_settings


class DataCollectionError(RuntimeError):
    """A real data source was unavailable or returned an unrecognised response."""


@dataclass(frozen=True)
class ScrapeResult:
    price: int
    is_fully_booked: bool
    source: str
    availability_status: str = "available"
    remaining_rooms: int | None = None
    availability_source: str = "inferred"


class OTAScraper:
    PRICE_KEYS = {"price", "pricepernight", "nightlyprice", "amount", "rate", "totalprice"}
    SOLD_OUT_KEYS = {"soldout", "isfullybooked", "unavailable", "isavailable"}

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def extract_price(self, url: str, target_date: str, comp_id: int) -> ScrapeResult:
        """Compatibility wrapper for a one-night collection."""
        return self.extract_prices(url, [target_date], comp_id)[target_date]

    def extract_prices(self, url: str, target_dates: list[str], comp_id: int) -> dict[str, ScrapeResult]:
        """Collect a facility's requested stay dates in one approved Actor run."""
        dates = list(dict.fromkeys(target_dates))
        if not dates:
            return {}
        if len(dates) > 90:
            raise DataCollectionError("At most 90 stay dates may be collected in one run")
        try:
            return self._from_apify(url, dates)
        except DataCollectionError:
            if self.settings.allow_simulated_data:
                results = {}
                for target_date in dates:
                    price, sold_out = self._fallback_simulation(target_date, comp_id)
                    results[target_date] = ScrapeResult(
                        price=price, is_fully_booked=sold_out, source="simulation",
                        availability_status="sold_out" if sold_out else "available",
                        availability_source="inferred",
                    )
                return results
            raise

    def _from_apify(self, url: str, target_dates: list[str]) -> dict[str, ScrapeResult]:
        # Secret Manager values may contain a trailing newline when they were
        # entered from a terminal. HTTP authorization headers cannot contain it.
        token = self.settings.apify_api_token.strip()
        ota_source = self.settings.source_for_url(url)
        if not ota_source or ota_source.status != "approved":
            raise DataCollectionError("OTA collection is not approved for this source")
        actor_id = ota_source.actor_id.strip()
        if not token or not actor_id:
            raise DataCollectionError("Apify token or OTA actor is not configured")

        try:
            client = ApifyClient(token)
            run = client.actor(actor_id).call(
                run_input={
                    "startUrls": [{"url": url}],
                    "stayDates": target_dates,
                    "adults": 2,
                    "currency": "JPY",
                }
            )
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        except Exception as exc:
            raise DataCollectionError("Apify run failed") from exc

        if not items:
            raise DataCollectionError("Apify actor returned no offers")
        results: dict[str, ScrapeResult] = {}
        requested_dates = set(target_dates)
        for item in items:
            stay_date = item.get("checkIn")
            if stay_date not in requested_dates or stay_date in results:
                continue
            results[stay_date] = self._normalise_item(item)
        # Keep valid partial results. A 90-day Actor run can occasionally lose
        # one request to a transient OTA timeout; discarding the other 89 days
        # makes the dashboard look empty and forces an unnecessarily expensive
        # full rerun. Missing dates remain visibly uncollected and are retried
        # by the next scheduled sync.
        if not results:
            raise DataCollectionError("Apify actor did not return any requested stay date")
        return results

    def _normalise_item(self, item: dict[str, Any]) -> ScrapeResult:
        sold_out = self._find_sold_out(item)
        remaining_rooms = self._remaining_rooms(item.get("remainingRooms"))
        raw_status = str(item.get("availabilityStatus") or item.get("availability") or "unknown").lower()
        status = raw_status if raw_status in {"available", "limited", "sold_out", "unknown"} else "unknown"
        if remaining_rooms == 0 or sold_out:
            sold_out, status = True, "sold_out"
        elif status == "sold_out":
            sold_out = True
        availability_source = str(item.get("availabilitySource") or "inferred").lower()
        if availability_source not in {"explicit_count", "symbol", "inferred", "unknown"}:
            availability_source = "unknown"
        prices = list(self._find_prices(item))
        if sold_out and not prices:
            return ScrapeResult(
                price=0, is_fully_booked=True, source="apify",
                availability_status="sold_out", remaining_rooms=remaining_rooms,
                availability_source=availability_source,
            )
        valid_prices = [price for price in prices if 3_000 <= price <= 1_000_000]
        if not valid_prices:
            raise DataCollectionError("Apify actor response does not contain a valid nightly price")
        if status in {"unknown", "sold_out"}:
            status = "available"
            availability_source = "inferred"
        return ScrapeResult(
            price=min(valid_prices), is_fully_booked=False, source="apify",
            availability_status=status, remaining_rooms=remaining_rooms,
            availability_source=availability_source,
        )

    @staticmethod
    def _remaining_rooms(value: Any) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            parsed = int(value)
        elif isinstance(value, str):
            digits = re.sub(r"[^0-9]", "", value)
            if not digits:
                return None
            parsed = int(digits)
        else:
            return None
        return parsed if 0 <= parsed <= 10_000 else None

    def _find_sold_out(self, value: Any) -> bool:
        if isinstance(value, dict):
            for key, nested in value.items():
                normalised = re.sub(r"[^a-z]", "", key.lower())
                if normalised in self.SOLD_OUT_KEYS:
                    if normalised == "isavailable":
                        return nested is False
                    return bool(nested)
                if self._find_sold_out(nested):
                    return True
        elif isinstance(value, list):
            return any(self._find_sold_out(item) for item in value)
        return False

    def _find_prices(self, value: Any) -> Iterable[int]:
        if isinstance(value, dict):
            for key, nested in value.items():
                normalised = re.sub(r"[^a-z]", "", key.lower())
                if normalised in self.PRICE_KEYS:
                    parsed = self._parse_price(nested)
                    if parsed is not None:
                        yield parsed
                yield from self._find_prices(nested)
        elif isinstance(value, list):
            for item in value:
                yield from self._find_prices(item)

    @staticmethod
    def _parse_price(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            digits = re.sub(r"[^0-9]", "", value)
            return int(digits) if digits else None
        if isinstance(value, dict):
            for key in ("amount", "value", "price"):
                if key in value:
                    return OTAScraper._parse_price(value[key])
        return None

    @staticmethod
    def _fallback_simulation(target_date: str, comp_id: int) -> tuple[int, bool]:
        rng = random.Random(f"comp_scrape_{comp_id}_{target_date}")
        date = dt.date.fromisoformat(target_date)
        base = {1: 12_000, 2: 8_000, 3: 15_000}.get(comp_id, 10_000)
        if date.weekday() >= 4:
            base = int(base * 1.3)
        price = base + rng.randint(-500, 500) + rng.choice([0, 0, 500, -500, 3_000])
        return price, date.weekday() >= 4 and rng.random() > 0.8


scraper_service = OTAScraper()
