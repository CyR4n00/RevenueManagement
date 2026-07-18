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


class OTAScraper:
    PRICE_KEYS = {"price", "pricepernight", "nightlyprice", "amount", "rate", "totalprice"}
    SOLD_OUT_KEYS = {"soldout", "isfullybooked", "unavailable", "isavailable"}

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def extract_price(self, url: str, target_date: str, comp_id: int) -> ScrapeResult:
        try:
            return self._from_apify(url, target_date)
        except DataCollectionError:
            if self.settings.allow_simulated_data:
                result = self._fallback_simulation(target_date, comp_id)
                return ScrapeResult(*result, source="simulation")
            raise

    def _from_apify(self, url: str, target_date: str) -> ScrapeResult:
        token = self.settings.apify_api_token
        ota_source = self.settings.source_for_url(url)
        if not ota_source or ota_source.status != "approved":
            raise DataCollectionError("OTA collection is not approved for this source")
        actor_id = ota_source.actor_id
        if not token or not actor_id:
            raise DataCollectionError("Apify token or OTA actor is not configured")

        try:
            client = ApifyClient(token)
            run = client.actor(actor_id).call(
                run_input={
                    "startUrls": [{"url": url}],
                    "checkIn": target_date,
                    "checkOut": (dt.date.fromisoformat(target_date) + dt.timedelta(days=1)).isoformat(),
                    "adults": 2,
                    "currency": "JPY",
                }
            )
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        except Exception as exc:
            raise DataCollectionError("Apify run failed") from exc

        if not items:
            raise DataCollectionError("Apify actor returned no offers")
        return self._normalise_item(items[0])

    def _normalise_item(self, item: dict[str, Any]) -> ScrapeResult:
        sold_out = self._find_sold_out(item)
        prices = list(self._find_prices(item))
        if sold_out and not prices:
            return ScrapeResult(price=0, is_fully_booked=True, source="apify")
        valid_prices = [price for price in prices if 3_000 <= price <= 1_000_000]
        if not valid_prices:
            raise DataCollectionError("Apify actor response does not contain a valid nightly price")
        return ScrapeResult(price=min(valid_prices), is_fully_booked=False, source="apify")

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
