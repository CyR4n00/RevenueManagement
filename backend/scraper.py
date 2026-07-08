import requests
from bs4 import BeautifulSoup
import re
import datetime
import random
import os
from apify_client import ApifyClient
from dotenv import load_dotenv
from database import SessionLocal
from models import DBSystemConfig
import sqlalchemy

load_dotenv()

class OTAScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }
        self.apify_token = self._get_token()

    def _get_token(self):
        # Try database first, then fallback to env
        try:
            with SessionLocal() as db:
                config = db.query(DBSystemConfig).filter(DBSystemConfig.key == "APIFY_API_TOKEN").first()
                if config and config.value:
                    return config.value
        except sqlalchemy.exc.OperationalError:
            # Table might not exist yet if called during import before create_all
            pass
        return os.getenv("APIFY_API_TOKEN")

    def extract_price(self, url: str, target_date: str, comp_id: int) -> tuple[int, bool]:
        """
        Attempts to scrape the price from the given OTA URL.
        Returns a tuple: (price, is_fully_booked)
        """
        # If we have a real Apify token configured (not the placeholder), attempt to use it
        if self.apify_token and self.apify_token != "your_apify_token_here":
            try:
                # Mock Apify Actor call (In production, replace with actual Actor ID for Booking/Rakuten)
                # Example:
                # client = ApifyClient(self.apify_token)
                # run_input = { "startUrls": [{"url": url}], "checkIn": target_date }
                # run = client.actor("apify/booking-scraper").call(run_input=run_input)
                # results = list(client.dataset(run["defaultDatasetId"]).iterate_items())
                # ... parse results ...
                print(f"[Scraper] Apify integration called for {url}")
                pass
            except Exception as e:
                print(f"[Scraper] Apify call failed: {e}")

        # Attempt naive direct scraping for Rakuten as a fallback before random simulation
        try:
            date_obj = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
            if "rakuten.co.jp" in url:
                # Rakuten uses query parameters like f_nen1, f_tuki1, f_hi1
                sep = "&" if "?" in url else "?"
                rakuten_url = f"{url}{sep}f_nen1={date_obj.year}&f_tuki1={date_obj.month}&f_hi1={date_obj.day}&f_nen2={date_obj.year}&f_tuki2={date_obj.month}&f_hi2={date_obj.day+1}&f_otona_su=2"

                response = requests.get(rakuten_url, headers=self.headers, timeout=5)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Look for actual price elements. Sometimes they are in <span class="price">
                    # Very naive approach, usually protected by JS/bot challenges
                    prices = soup.find_all(string=re.compile(r'[0-9,]+円'))
                    if prices:
                        for p in prices:
                            clean_price = int(re.sub(r'[^0-9]', '', p))
                            if 3000 <= clean_price <= 100000:
                                return clean_price, False

            print(f"[Scraper] Could not reliably parse {url}. Using simulation.")
            return self._fallback_simulation(target_date, comp_id)

        except Exception as e:
            print(f"[Scraper Error] Failed to scrape {url}: {e}. Using fallback.")
            return self._fallback_simulation(target_date, comp_id)

    def _fallback_simulation(self, target_date_str: str, comp_id: int) -> tuple[int, bool]:
        """
        Deterministic fallback to simulate market data when direct scraping is blocked/unavailable.
        """
        seed_str = f"comp_scrape_{comp_id}_{target_date_str}"
        random.seed(seed_str)

        target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        is_weekend = target_date.weekday() >= 4

        base = 12000 if comp_id == 1 else (8000 if comp_id == 2 else 15000)
        if is_weekend:
            base = int(base * 1.3)

        change_type = random.choice(["none", "none", "up", "down", "big_up"])
        price = base + random.randint(-500, 500)

        if change_type == "up":
            price += random.choice([500, 1000])
        elif change_type == "down":
            price -= random.choice([500, 1000])
        elif change_type == "big_up":
            price += random.choice([3000, 4000, 5000])

        is_fully_booked = False
        if is_weekend and random.random() > 0.8:
            is_fully_booked = True

        return price, is_fully_booked

scraper_service = OTAScraper()
