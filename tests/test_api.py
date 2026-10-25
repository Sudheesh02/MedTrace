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
    assert "sample_mode" in data
    assert "zetaris_enabled" in data

def test_api_run_with_sample_mode_option(client):
    payload = {
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-007",
        "options": {"sample_mode": True}
    }
    response = client.post("/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    pack = data["output"]
    assert pack["facility_id"] == "FAC-DH-01"
    assert pack["medicine_id"] == "MED-007"


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
    assert "p_stockout_risk" in pack
    assert 0.0 <= pack["p_stockout_risk"] <= 1.0
    assert len(pack["recommendations"]) >= 2
    assert "agents" in data
    assert len(data["agents"]) == 7

def test_api_triage_endpoint(client):
    """Verify GET /triage executes proactive district portfolio triage scanning."""
    response = client.get("/triage?top_n=5")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "triage" in data
    triage = data["triage"]
    assert triage["total_evaluated"] >= 12
    assert "critical_count" in triage
    assert "warning_count" in triage
    assert "top_urgent_items" in triage
    assert len(triage["top_urgent_items"]) <= 5
    for item in triage["top_urgent_items"]:
        assert "facility_id" in item
        assert "medicine_id" in item
        assert "urgency_tier" in item
        assert item["urgency_tier"] in ("CRITICAL", "WARNING", "SECURE")

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

@pytest.mark.parametrize("fac_id,med_id", [
    ("FAC-DH-01", "MED-007"),
    ("FAC-PHC-01", "MED-004"),
])
def test_api_run_multiple_facilities_dynamism(client, fac_id, med_id):
    """Verify API dynamically returns distinct, valid results across varied facilities."""
    payload = {"facility_id": fac_id, "medicine_id": med_id}
    response = client.post("/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    pack = data["output"]
    assert pack["facility_id"] == fac_id
    assert pack["medicine_id"] == med_id
    assert pack["days_of_cover_trust"] >= 0.0
    assert len(pack["recommendations"]) >= 2
    assert "trace_file" in data

def test_api_record_officer_decision_and_hmem_adaptation(client):
    """
    Test Phase 4 H-MEM API Integration:
    1. Runs baseline investigation where PEER_TRANSFER has high feasibility (0.90).
    2. Records an officer rejection via POST /decision, storing the decision in H-MEM.
    3. Re-runs investigation, asserting that H-MEM cross-session recall penalizes PEER_TRANSFER feasibility.
    4. Records an officer approval via POST /decision, asserting deterministic contradiction resolution.
    5. Re-runs investigation, asserting feasibility penalty is cleared and restored.
    """
    import os
    from run import orchestrator

    # Reset any active memory in orchestrator
    orchestrator.hmem.episodic_memory.clear()
    orchestrator.hmem.long_term_beliefs = {
        "supplier_delays": {},
        "officer_action_preferences": {},
        "rejected_patterns": []
    }

    # Step 1: Baseline investigation for FAC-CHC-01 and MED-001
    res_base = client.post("/run", json={"facility_id": "FAC-CHC-01", "medicine_id": "MED-001"})
    assert res_base.status_code == 200
    base_pack = res_base.json()["output"]
    base_transfer = [r for r in base_pack["recommendations"] if r["action_type"] == "PEER_TRANSFER"][0]
    base_feasibility = base_transfer["feasibility_score"]
    assert base_feasibility == 0.90

    # Step 2: Officer rejects PEER_TRANSFER via POST /decision
    decision_payload = {
        "facility_id": "FAC-CHC-01",
        "medicine_id": "MED-001",
        "action_type": "PEER_TRANSFER",
        "decision": "REJECTED",
        "reason": "Primary route flooded; mountain pass blocked"
    }
    dec_res = client.post("/decision", json=decision_payload)
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["status"] == "success"
    assert "memory_state" in dec_data
    assert dec_data["memory_state"]["preferences"]["rejected"] == 1
    assert any("PEER_TRANSFER" in p for p in dec_data["memory_state"]["rejected_patterns"])

    # Step 3: Re-run investigation and verify feasibility is penalized
    res_penalized = client.post("/run", json={"facility_id": "FAC-CHC-01", "medicine_id": "MED-001"})
    assert res_penalized.status_code == 200
    penalized_pack = res_penalized.json()["output"]
    penalized_transfer = [r for r in penalized_pack["recommendations"] if r["action_type"] == "PEER_TRANSFER"][0]
    assert penalized_transfer["feasibility_score"] == round(base_feasibility - 0.20, 2)
    assert penalized_transfer["feasibility_score"] == 0.70

    # Step 4: Contradiction Resolution — Officer later approves PEER_TRANSFER
    approval_payload = {
        "facility_id": "FAC-CHC-01",
        "medicine_id": "MED-001",
        "action_type": "PEER_TRANSFER",
        "decision": "APPROVED",
        "reason": "Road repair complete; alternative route certified"
    }
    app_res = client.post("/decision", json=approval_payload)
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert app_data["status"] == "success"
    assert app_data["memory_state"]["preferences"]["approved"] == 1
    assert app_data["memory_state"]["preferences"]["rejected"] == 0
    assert not any("PEER_TRANSFER" in p for p in app_data["memory_state"]["rejected_patterns"])

    # Step 5: Re-run investigation and verify feasibility penalty is restored
    res_restored = client.post("/run", json={"facility_id": "FAC-CHC-01", "medicine_id": "MED-001"})
    assert res_restored.status_code == 200
    restored_pack = res_restored.json()["output"]
    restored_transfer = [r for r in restored_pack["recommendations"] if r["action_type"] == "PEER_TRANSFER"][0]
    assert restored_transfer["feasibility_score"] == base_feasibility

    # Cleanup memory and persistence file
    orchestrator.hmem.episodic_memory.clear()
    orchestrator.hmem.long_term_beliefs = {
        "supplier_delays": {},
        "officer_action_preferences": {},
        "rejected_patterns": []
    }
    if os.path.exists("logs/hmem_store.json"):
        os.remove("logs/hmem_store.json")

def test_api_decision_validation_errors(client):
    """Verify POST /decision returns structured 404/400 errors for invalid inputs."""
    # Invalid facility
    res_fac = client.post("/decision", json={
        "facility_id": "FAC-NONEXISTENT",
        "medicine_id": "MED-001",
        "action_type": "PEER_TRANSFER",
        "decision": "APPROVED"
    })
    assert res_fac.status_code == 404
    assert "Unrecognized facility_id" in res_fac.json()["detail"]

    # Invalid medicine
    res_med = client.post("/decision", json={
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-NONEXISTENT",
        "action_type": "PEER_TRANSFER",
        "decision": "APPROVED"
    })
    assert res_med.status_code == 404
    assert "Unrecognized medicine_id" in res_med.json()["detail"]

    # Invalid decision string
    res_dec = client.post("/decision", json={
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-007",
        "action_type": "PEER_TRANSFER",
        "decision": "MAYBE"
    })
    assert res_dec.status_code == 400
    assert "Invalid decision" in res_dec.json()["detail"]
