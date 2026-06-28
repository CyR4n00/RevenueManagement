from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
import pytest

from main import app
from database import Base, get_db
import models


from sqlalchemy.pool import StaticPool

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Use a fixture to set up the DB for tests
@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Add initial facility
    db.add(models.DBFacility(id=1, name="自社ホテル（サンプル）", base_price=10000))
    # Add competitors
    db.add(models.DBCompetitor(id=1, name="ホテルA (アパ新宿)", url="https://travel.rakuten.co.jp/HOTEL/14138/14138.html"))
    db.add(models.DBCompetitor(id=2, name="ゲストハウスB (東京駅前)", url="https://www.booking.com/hotel/jp/tokyo-station.ja.html"))
    db.add(models.DBCompetitor(id=3, name="Cヴィラ (京都鴨川)", url="https://travel.rakuten.co.jp/HOTEL/180290/180290.html"))

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def test_get_market_data():
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    response = client.get(f"/market_data?start_date={date_str}&days=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3  # We have 3 competitors added in setup

    # Check the fields of a market data entry
    entry = data[0]
    assert "date" in entry
    assert "competitor_id" in entry
    assert "competitor_name" in entry
    assert "price_today" in entry
    assert "price_yesterday" in entry
    assert "difference" in entry
    assert "is_fully_booked" in entry

def test_get_alerts():
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    response = client.get(f"/alerts?start_date={date_str}&days=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    if len(data) > 0:
        entry = data[0]
        assert "id" in entry
        assert "date" in entry
        assert "message" in entry
        assert "type" in entry

def test_get_recommendation():
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    response = client.get(f"/recommendation?date={date_str}")
    assert response.status_code == 200
    data = response.json()

    assert "date" in data
    assert "suggested_price" in data
    assert "reasoning" in data
