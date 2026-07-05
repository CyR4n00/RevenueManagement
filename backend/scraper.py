import requests
from bs4 import BeautifulSoup
import re
import datetime
import random
import os
import json
from apify_client import ApifyClient

class OTAScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }
        # Use the API key provided via environment variable
        api_token = os.environ.get("APIFY_API_KEY")
        self.apify_client = ApifyClient(api_token) if api_token else None

    def extract_price(self, url: str, target_date: str, comp_id: int) -> tuple[int, bool]:
        """
        Attempts to scrape the price from the given OTA URL.
        Returns a tuple: (price, is_fully_booked)
        """
        try:
            # Note: A real implementation would append the target_date to the URL parameters
            # e.g., url + f"?checkin={target_date}&checkout=..."
            response = requests.get(url, headers=self.headers, timeout=5)

            # If the request is successful and it's a known site, try to parse
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Simple HTTP parsers (These often break if layout changes or JS is required)
                if "rakuten.co.jp" in url or "jalan.net" in url or "ikyu.com" in url:
                    prices = soup.find_all(string=re.compile(r'[0-9,]+円'))
                    if prices:
                        for p in prices:
                            clean_price = int(re.sub(r'[^0-9]', '', p))
                            if 3000 <= clean_price <= 300000:
                                return clean_price, False

                # Add parsers for booking.com, airbnb, etc., when not blocked

            # If standard HTTP requests fail or are blocked (e.g. 403 on booking/airbnb), use Apify
            if self.apify_client:
                print(f"[Scraper] Attempting to use Apify API for {url}")
                try:
                    # OTA-specific Apify Actors or configuration
                    if "booking.com" in url:
                        # Use Apify's Booking.com Scraper (example actor: dtrungtin/booking-scraper or similar, or custom script)
                        run_input = {
                            "startUrls": [{"url": url}],
                            # Simplified properties for Apify's Web Scraper as a generic example
                            "pageFunction": """
                            async function pageFunction(context) {
                                const { $, request } = context;
                                // Example selector for Booking.com price
                                const priceText = $('.bui-price-display__value').text() || $('body').text();
                                return { html: priceText };
                            }
                            """
                        }
                        actor_id = "apify/web-scraper" # Replace with specific booking actor id in prod
                    elif "airbnb." in url:
                        run_input = {
                            "startUrls": [{"url": url}],
                            "pageFunction": "async function pageFunction(context) { return { html: $('body').text() }; }"
                        }
                        actor_id = "apify/web-scraper"
                    elif "agoda.com" in url:
                        run_input = {
                            "startUrls": [{"url": url}],
                            "pageFunction": "async function pageFunction(context) { return { html: $('body').text() }; }"
                        }
                        actor_id = "apify/web-scraper"
                    else: # Rakuten, Jalan, Ikyu fallback
                        run_input = {
                            "runMode": "DEVELOPMENT",
                            "startUrls": [{"url": url}],
                            "pageFunction": "async function pageFunction(context) { return { html: $('body').text() }; }"
                        }
                        actor_id = "apify/web-scraper"

                    print(f"[Scraper] Launching Apify Actor '{actor_id}' for {url}...")
                    run = self.apify_client.actor(actor_id).call(run_input=run_input, build="latest")

                    if run and "defaultDatasetId" in run:
                        for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                            # We search for price patterns in the returned HTML/text
                            if "html" in item:
                                text_data = item["html"]
                                # Search for generic price patterns (e.g., ¥12,000, 12,000円)
                                prices = re.findall(r'(?:¥|￥)?([0-9,]+)(?:円)?', text_data)
                                if prices:
                                    for p in prices:
                                        clean_price = int(re.sub(r'[^0-9]', '', p))
                                        if 3000 <= clean_price <= 300000:
                                            print(f"[Scraper] Successfully extracted {clean_price} via Apify!")
                                            return clean_price, False
                except Exception as apify_err:
                    print(f"[Scraper Warning] Apify extraction failed: {apify_err}")

            # If all attempts fail, raise an exception instead of mocking
            print(f"[Scraper] Could not reliably parse {url}. No mock data fallback is configured.")
            raise Exception("Failed to extract price data from target OTA URL.")

        except Exception as e:
            print(f"[Scraper Error] Failed to scrape {url}: {e}")
            raise e

scraper_service = OTAScraper()
