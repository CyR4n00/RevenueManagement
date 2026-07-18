from scraper import OTAScraper

def test_actor_output_uses_lowest_available_nightly_price():
    scraper = OTAScraper()
    result = scraper._normalise_item({"offers": [{"price": "JPY 13,400"}, {"price": 12_800}]})
    assert result.price == 12_800
    assert result.is_fully_booked is False
    assert result.source == "apify"


def test_actor_output_marks_a_sold_out_property():
    scraper = OTAScraper()
    result = scraper._normalise_item({"soldOut": True})
    assert result.is_fully_booked is True
    assert result.price == 0
