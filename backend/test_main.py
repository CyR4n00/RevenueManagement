import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db
from main import app
import models

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def test_read_facility():
    # Insert a dummy facility for test
    db = TestingSessionLocal()
    db.add(models.DBFacility(id=1, name="Test Facility", base_price=10000))
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.get("/facility")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Facility"
