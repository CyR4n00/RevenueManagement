import requests
from bs4 import BeautifulSoup
import re
import datetime
import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

import models
from sqlalchemy.orm import Session

class OTAScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }

    def _get_apify_token(self, db: Session) -> str:
        if not db:
            return os.getenv("APIFY_API_KEY")
        config = db.query(models.DBSystemConfig).filter(models.DBSystemConfig.key == "APIFY_API_KEY").first()
        if config and config.value:
            return config.value
        return os.getenv("APIFY_API_KEY")

    def extract_price(self, url: str, target_date: str, comp_id: int, db: Session = None) -> tuple[int, bool]:
        """
        Attempts to scrape the price from the given OTA URL.
        Returns a tuple: (price, is_fully_booked)
        Returns (0, False) if scraping fails gracefully without simulation.
        """
        apify_token = self._get_apify_token(db)
        # If we have a real Apify token configured (not the placeholder), attempt to use it
        if apify_token and apify_token != "your_apify_token_here" and apify_token != "test_api_key_123":
            try:
                client = ApifyClient(apify_token)
                run_input = {
                    "startUrls": [{"url": url}],
                    "checkIn": target_date
                }

                print(f"[Scraper] Calling Apify integration for {url}")
                # Real call to Apify actor (e.g. apify/booking-scraper)
                run = client.actor("apify/booking-scraper").call(run_input=run_input)
                if run:
                    results = list(client.dataset(run["defaultDatasetId"]).iterate_items())
                    if results and len(results) > 0:
                        price = results[0].get('price')
                        if price:
                           return int(price), False
            except Exception as e:
                print(f"[Scraper] Apify call failed: {e}")

        # Attempt naive direct scraping for Rakuten as a fallback before failing
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

            print(f"[Scraper] Could not reliably parse {url}. Skipping.")
            return 0, False

        except Exception as e:
            print(f"[Scraper Error] Failed to scrape {url}: {e}. Skipping.")
            return 0, False

scraper_service = OTAScraper()
