from fastapi.testclient import TestClient
from back.main import app

def test_health():
    assert TestClient(app).get("/health").status_code == 200