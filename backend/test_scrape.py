import pytest
from scraper import OTAScraper

def test_extract_price_fallback():
    scraper = OTAScraper()
    # Test the fallback simulation
    price, is_fully_booked = scraper._fallback_simulation("2026-07-20", 1)

    # Assert return types
    assert isinstance(price, int)
    assert isinstance(is_fully_booked, bool)

    # Assert reasonable range based on the logic in scraper.py
    # base is 12000 for comp_id 1.
    # It adds/subtracts a few thousands.
    assert 5000 <= price <= 25000

def test_get_demo_prices_mock():
    scraper = OTAScraper()
    # Assuming extract_price falls back gracefully on a dummy URL
    price, is_fully_booked = scraper.extract_price("https://dummy.url", "2026-07-20", 1)

    # Assert return types
    assert isinstance(price, int)
    assert isinstance(is_fully_booked, bool)
    assert 5000 <= price <= 25000
