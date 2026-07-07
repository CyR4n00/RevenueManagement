import pytest
from fastapi.testclient import TestClient
from main import app
from database import Base, engine

# Ensure we use an isolated database or static pool, but for simple tests
# we can just use the provided engine since it's SQLite.

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_get_facility():
    response = client.get("/facility")
    # In startup event (via lifespan) facility might not be populated in tests
    # unless lifespan is triggered. TestClient natively runs lifespan in recent versions.
    # We just ensure it's a 200.
    assert response.status_code == 200

def test_get_competitors():
    with TestClient(app) as client:
        response = client.get("/competitors")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
