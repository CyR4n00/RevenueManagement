import requests
from bs4 import BeautifulSoup
import re
import datetime
import random
import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

class OTAScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }
        self.apify_token = os.getenv("APIFY_API_KEY")

    def extract_price(self, url: str, target_date: str, comp_id: int) -> tuple[int, bool]:
        """
        Attempts to scrape the price from the given OTA URL.
        Returns a tuple: (price, is_fully_booked)
        """
        last_exception = None

        if self.apify_token and self.apify_token != "your_apify_token_here":
            try:
                client = ApifyClient(self.apify_token)
                run_input = { "startUrls": [{"url": url}], "checkIn": target_date }

                # Note: The specific Apify actor used here is a placeholder and should be updated
                # based on actual chosen actor for booking/rakuten scraping.
                run = client.actor("apify/booking-scraper").call(run_input=run_input)
                results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

                print(f"[Scraper] Apify integration called for {url}")

                if not results:
                    raise Exception("Apify returned no results.")

                # Naive parsing logic for demonstration since exact structure isn't known
                # Real production logic would extract exact price from actor results
                # We assume it extracts a price and booking status
                price = results[0].get("price", 10000)
                is_fully_booked = results[0].get("isFullyBooked", False)

                return int(price), is_fully_booked
            except Exception as e:
                print(f"[Scraper Error] Failed to scrape {url} via Apify: {e}")
                last_exception = e
        else:
            print("[Scraper] APIFY_API_KEY is not set or invalid, skipping Apify.")
            last_exception = Exception("APIFY_API_KEY is not set or is invalid.")

        # Attempt naive direct scraping for Rakuten as a fallback
        try:
            date_obj = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
            if "rakuten.co.jp" in url:
                sep = "&" if "?" in url else "?"
                rakuten_url = f"{url}{sep}f_nen1={date_obj.year}&f_tuki1={date_obj.month}&f_hi1={date_obj.day}&f_nen2={date_obj.year}&f_tuki2={date_obj.month}&f_hi2={date_obj.day+1}&f_otona_su=2"
                response = requests.get(rakuten_url, headers=self.headers, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    prices = soup.find_all(string=re.compile(r'[0-9,]+円'))
                    if prices:
                        for p in prices:
                            clean_price = int(re.sub(r'[^0-9]', '', p))
                            if 3000 <= clean_price <= 100000:
                                return clean_price, False
        except Exception as direct_e:
            print(f"[Scraper Error] Direct scraping fallback failed: {direct_e}")
            last_exception = direct_e

        raise Exception(f"Failed to scrape data for {url}. Last reason: {last_exception}")

scraper_service = OTAScraper()
