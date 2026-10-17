from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)


def test_optional_api_key_roles():
    previous_analyst = settings.ANALYST_API_KEY
    previous_admin = settings.ADMIN_API_KEY
    settings.ANALYST_API_KEY = "test-analyst-key"
    settings.ADMIN_API_KEY = "test-admin-key"
    try:
        assert client.get("/api/actors").status_code == 401
        assert client.get("/api/actors", headers={"X-API-Key": "test-analyst-key"}).status_code == 200
        assert client.post("/api/ingest/live", headers={"X-API-Key": "test-analyst-key"}).status_code == 403
    finally:
        settings.ANALYST_API_KEY = previous_analyst
        settings.ADMIN_API_KEY = previous_admin
