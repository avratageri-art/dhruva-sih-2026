import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "project": "DHRUVA"}

def test_get_actors():
    response = client.get("/api/actors")
    # Will return 200 even if empty
    assert response.status_code == 200
    assert isinstance(response.json(), list)
