from dataclasses import replace

from scraper import OTAScraper
from settings import get_settings


def test_normalises_explicit_limited_room_signal():
    scraper = OTAScraper(replace(get_settings(), allow_simulated_data=False))
    result = scraper._normalise_item({
        "nightlyPrice": 18_000,
        "isFullyBooked": False,
        "availabilityStatus": "limited",
        "remainingRooms": 2,
        "availabilitySource": "explicit_count",
    })
    assert result.price == 18_000
    assert result.availability_status == "limited"
    assert result.remaining_rooms == 2
    assert result.availability_source == "explicit_count"


def test_normalises_explicit_sold_out_signal():
    scraper = OTAScraper(replace(get_settings(), allow_simulated_data=False))
    result = scraper._normalise_item({
        "nightlyPrice": None,
        "isFullyBooked": True,
        "availabilityStatus": "sold_out",
        "availabilitySource": "symbol",
    })
    assert result.is_fully_booked is True
    assert result.availability_status == "sold_out"
    assert result.remaining_rooms is None
