import pytest
from fastapi.testclient import TestClient
from main import app, get_db
import datetime

client = TestClient(app)

def test_get_market_data():
    target_date = "2026-07-20"
    response = client.get(f"/market_data?start_date={target_date}&days=1")

    # Assert successful response
    assert response.status_code == 200

    # Assert data structure
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        first_item = data[0]
        assert "date" in first_item
        assert "competitor_id" in first_item
        assert "competitor_name" in first_item
        assert "price_today" in first_item
        assert "price_yesterday" in first_item
        assert "difference" in first_item
        assert "is_fully_booked" in first_item
        assert first_item["date"] == target_date
