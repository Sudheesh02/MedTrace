"""
API and Endpoint Tests for MedTrace FastAPI Service (tests/test_api.py).
Verifies:
1. GET /health status check.
2. POST /run happy path returning valid ActionPack payload and trace file.
3. POST /run error handling for invalid facility ID returning HTTP 404.
4. POST /run error handling for invalid medicine ID returning HTTP 404.
"""

import pytest
from fastapi.testclient import TestClient
from run import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_api_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "MedTrace"

def test_api_run_valid_investigation(client):
    payload = {
        "facility_id": "FAC-CHC-01",
        "medicine_id": "MED-001"
    }
    response = client.post("/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "execution_time_seconds" in data
    assert "output" in data
    pack = data["output"]
    assert pack["facility_id"] == "FAC-CHC-01"
    assert pack["medicine_id"] == "MED-001"
    assert "winning_hypothesis" in pack
    assert len(pack["recommendations"]) >= 2
    assert "agents" in data
    assert len(data["agents"]) == 6

def test_api_run_invalid_facility_returns_404(client):
    payload = {
        "facility_id": "FAC-NONEXISTENT-999",
        "medicine_id": "MED-001"
    }
    response = client.post("/run", json=payload)
    assert response.status_code == 404
    detail = response.json().get("detail", "")
    assert "Unrecognized facility_id" in detail
    assert "FAC-NONEXISTENT-999" in detail

def test_api_run_invalid_medicine_returns_404(client):
    payload = {
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-INVALID-999"
    }
    response = client.post("/run", json=payload)
    assert response.status_code == 404
    detail = response.json().get("detail", "")
    assert "Unrecognized medicine_id" in detail
    assert "MED-INVALID-999" in detail
