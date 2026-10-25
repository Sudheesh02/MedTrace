"""
API and Endpoint Tests for MedTrace FastAPI Service (tests/test_api.py).
Verifies:
1. GET /health status check.
2. POST /run happy path returning valid ActionPack payload and trace file.
3. POST /run error handling for invalid facility ID returning HTTP 404.
4. POST /run error handling for invalid medicine ID returning HTTP 404.
"""

import os
import json
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


def test_api_run_unhandled_exception_returns_500(client, monkeypatch):
    """Verify that unexpected orchestrator crashes return HTTP 500 rather than masked HTTP 200."""
    from run import orchestrator

    def mock_fail(*args, **kwargs):
        raise RuntimeError("Simulated unexpected database or pipeline failure")

    monkeypatch.setattr(orchestrator, "run_investigation", mock_fail)
    response = client.post("/run", json={"facility_id": "FAC-DH-01", "medicine_id": "MED-007"})
    assert response.status_code == 500
    assert "Simulated unexpected database or pipeline failure" in response.json()["detail"]


def test_cli_subprocess_execution_modes():
    """Verify end-to-end subprocess execution across all CLI entry modes."""
    import subprocess
    import sys

    # 1. Standard investigation with --explain
    res_cli = subprocess.run(
        [sys.executable, "run.py", "--cli", "--sample-mode", "--facility", "FAC-DH-01", "--medicine", "MED-007", "--explain"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert res_cli.returncode == 0
    assert "MEDTRACE ACTION PACK SUMMARY" in res_cli.stdout
    assert "MEDTRACE MULTI-AGENT REASONING & AUDIT TIMELINE" in res_cli.stdout
    assert "Number Auditor" in res_cli.stdout

    # 2. Triage scanning mode
    res_triage = subprocess.run(
        [sys.executable, "run.py", "--triage", "--sample-mode", "--top-n", "3"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert res_triage.returncode == 0
    assert "MEDTRACE PROACTIVE DISTRICT TRIAGE LEADERBOARD" in res_triage.stdout
    assert "CRITICAL" in res_triage.stdout

    # 3. Interactive decision recording mode
    res_rec = subprocess.run(
        [sys.executable, "run.py", "--record-decision", "--sample-mode", "--facility", "FAC-CHC-01", "--medicine", "MED-001", "--action-type", "PEER_TRANSFER", "--decision", "APPROVED"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert res_rec.returncode == 0
    assert "Successfully recorded officer decision in H-MEM" in res_rec.stdout


def test_metadata_json_and_docs_integrity():
    """Verify metadata.json, SPONSOR_TECH.md, and PRE_EXISTING_COMPONENTS.md conform to honest hackathon reporting."""
    import json
    import os

    # 1. metadata.json validation
    assert os.path.exists("metadata.json")
    with open("metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["project_name"] == "MedTrace"
    assert "zetaris" in meta["sponsor_technology"]
    assert "meterless" in meta["sponsor_technology"]
    assert "nvidia" in meta["sponsor_technology"]
    nvidia_model = meta["sponsor_technology"]["nvidia"]["model"]
    assert "NIM" not in nvidia_model
    assert "NVIDIA API" in nvidia_model or "Meterless" in nvidia_model

    # 2. SPONSOR_TECH.md truth checks
    with open("SPONSOR_TECH.md", "r", encoding="utf-8") as f:
        sponsor_doc = f.read()
    assert "61-test" not in sponsor_doc
    assert "89-test" not in sponsor_doc
    assert "96-test" not in sponsor_doc
    assert "101-test" not in sponsor_doc
    assert "103-test" not in sponsor_doc
    assert "115-test" not in sponsor_doc
    assert "116-test" not in sponsor_doc
    assert "117-test" not in sponsor_doc
    assert "120-test" not in sponsor_doc
    assert "122-test" not in sponsor_doc
    assert "124-test" not in sponsor_doc
    assert "126-test" not in sponsor_doc
    assert "127-test" not in sponsor_doc
    assert "128-test pytest suite" in sponsor_doc
    assert "Status: 100% Fully Verified" not in sponsor_doc
    assert "128/128 Automated Tests Verified" in sponsor_doc

    # 3. PRE_EXISTING_COMPONENTS.md declarations
    with open("PRE_EXISTING_COMPONENTS.md", "r", encoding="utf-8") as f:
        pre_existing_doc = f.read()
    assert "Gemini Autonomous Coding Assistant & Harness" in pre_existing_doc
    assert "Calibrated Assumption" in pre_existing_doc
    assert "88 automated tests" not in pre_existing_doc
    assert "103 automated tests" not in pre_existing_doc
    assert "115 automated tests" not in pre_existing_doc
    assert "116 automated tests" not in pre_existing_doc
    assert "117 automated tests" not in pre_existing_doc
    assert "120 automated tests" not in pre_existing_doc
    assert "122 automated tests" not in pre_existing_doc
    assert "124 automated tests" not in pre_existing_doc
    assert "126 automated tests" not in pre_existing_doc
    assert "127 automated tests" not in pre_existing_doc
    assert "128 automated tests passing" in pre_existing_doc

    # 4. data/README.md modeling assumptions
    with open("data/README.md", "r", encoding="utf-8") as f:
        data_doc = f.read()
    assert "Explicit Modeling Assumptions" in data_doc
    assert "who_surveillance_multiplier = 1.35" in data_doc


def test_smoke_test_provider_handling_and_zero_hardcoding(monkeypatch):
    """Verify smoke_test.py enforces zero hardcoded credentials and supports both Meterless and NVIDIA."""
    import smoke_test

    # 1. Verify zero hardcoded default password in source code
    with open("smoke_test.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "<REDACTED>" not in content, "smoke_test.py must not contain hardcoded default Zetaris password"

    # 2. Verify zetaris_sql raises clean ValueError when password is missing
    monkeypatch.setenv("ZETARIS_PASSWORD", "")
    monkeypatch.setenv("ZETARIS_API_KEY", "")
    with pytest.raises(ValueError) as exc:
        smoke_test.zetaris_sql()
    assert "ZETARIS_PASSWORD is not set" in str(exc.value)

    # 3. Verify power_model raises clean ValueError when NVIDIA key is placeholder
    monkeypatch.delenv("METERLESS_RUNTIME_TOKEN", raising=False)
    monkeypatch.setenv("MODEL_API_KEY", "your-nvapi-key")
    with pytest.raises(ValueError) as exc_nv:
        smoke_test.power_model()
    assert "MODEL_API_KEY is not configured" in str(exc_nv.value)


def test_explain_trace_sample_trace_fallback(capsys):
    """Verify scripts/explain_trace.py falls back cleanly to tracked sample trace on fresh clones."""
    from scripts.explain_trace import find_latest_trace, render_trace

    # Verify tracked sample trace exists
    sample_trace = "logs/sample_trace_FAC-DH-01_MED-007.jsonl"
    assert os.path.exists(sample_trace), "Tracked judge sample trace must exist in logs/"

    # Test find_latest_trace fallback with non-existent empty directory
    res_trace = find_latest_trace("logs_empty_sandbox_test")
    assert res_trace is None

    # Test render_trace on the tracked sample trace
    render_trace(sample_trace)
    captured = capsys.readouterr().out
    assert "MEDTRACE MULTI-AGENT REASONING & AUDIT TIMELINE" in captured
    assert "ReconcilerAgent" in captured
    assert "InvestigatorAgent" in captured
    assert "SkepticAgent & Number Auditor" in captured
    assert "ActionPlannerAgent" in captured


def test_explain_trace_renders_verdict_flip_card(capsys, client):
    """
    Verify render_verdict_flip_card outputs structured winning verdict,
    counterfactual triggers, dissent log, and cognitive memory impact.
    Tests CLI, module functions, and API endpoints.
    """
    import subprocess
    import sys
    import json
    from scripts.explain_trace import render_verdict_flip_card, build_verdict_flip_card

    # 1. Test build_verdict_flip_card and render_verdict_flip_card on sample trace
    sample_trace = "logs/sample_trace_FAC-DH-01_MED-007.jsonl"
    with open(sample_trace, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    card = build_verdict_flip_card(events)
    assert "winning_verdict" in card
    assert "counterfactual_trigger" in card
    assert "dissent_log" in card
    assert "cognitive_memory_impact" in card

    assert card["winning_verdict"]["facility_id"] == "FAC-DH-01"
    assert card["winning_verdict"]["medicine_id"] == "MED-007"
    assert "Phantom Stock Drift" in card["winning_verdict"]["hypothesis"]
    assert card["winning_verdict"]["primary_action"] == "INVENTORY_AUDIT_ADJUSTMENT"
    assert "reversal_condition" in card["counterfactual_trigger"]
    assert "minimum_missing_evidence" in card["counterfactual_trigger"]
    assert len(card["dissent_log"]["challenges"]) >= 1
    assert len(card["dissent_log"]["auditor_checks"]) >= 4

    render_verdict_flip_card(events, use_rich=False)
    captured = capsys.readouterr().out
    assert "EXECUTIVE VERDICT-FLIP CARD & DISSENT LOG" in captured
    assert "WINNING VERDICT & ROOT CAUSE" in captured
    assert "COUNTERFACTUAL REVERSAL TRIGGER" in captured
    assert "DISSENT LOG & ADVERSARIAL SKEPTIC CRITIQUE" in captured
    assert "COGNITIVE MEMORY IMPACT" in captured
    assert "Phantom Stock Drift in Warehouse Ledger" in captured

    # 2. Test golden quarantine trace
    golden_trace = "logs/golden_trace_FAC-CHC-01_MED-001.jsonl"
    with open(golden_trace, "r", encoding="utf-8") as f:
        g_events = [json.loads(line) for line in f if line.strip()]
    g_card = build_verdict_flip_card(g_events)
    assert "Batch Quality Assurance Quarantine" in g_card["winning_verdict"]["hypothesis"]
    assert g_card["winning_verdict"]["primary_action"] == "PEER_TRANSFER"
    assert "CoA" in g_card["counterfactual_trigger"]["reversal_condition"] or "Certificate of Analysis" in g_card["counterfactual_trigger"]["reversal_condition"]

    render_verdict_flip_card(g_events, use_rich=False)
    g_captured = capsys.readouterr().out
    assert "PEER_TRANSFER" in g_captured
    assert "Batch Quality Assurance Quarantine" in g_captured

    # 3. Test memory trace
    mem_trace = "logs/trace_with_memory.jsonl"
    with open(mem_trace, "r", encoding="utf-8") as f:
        m_events = [json.loads(line) for line in f if line.strip()]
    m_card = build_verdict_flip_card(m_events)
    assert any("SUP-001" in fact or "Monsoon" in fact for fact in m_card["cognitive_memory_impact"]["memory_facts"])
    assert "H-MEM" in m_card["cognitive_memory_impact"]["decision_impact"]

    # 4. Test subprocess execution of scripts/explain_trace.py --latest
    res_explain = subprocess.run(
        [sys.executable, "scripts/explain_trace.py", "--latest", "--plain"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert res_explain.returncode == 0
    assert "EXECUTIVE VERDICT-FLIP CARD & DISSENT LOG" in res_explain.stdout
    assert "MEDTRACE MULTI-AGENT REASONING & AUDIT TIMELINE" in res_explain.stdout

    # 5. Test subprocess execution with --verdict-flip-only
    res_card_only = subprocess.run(
        [sys.executable, "scripts/explain_trace.py", "--verdict-flip-only", "--plain"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert res_card_only.returncode == 0
    assert "EXECUTIVE VERDICT-FLIP CARD & DISSENT LOG" in res_card_only.stdout
    assert "MEDTRACE MULTI-AGENT REASONING & AUDIT TIMELINE" not in res_card_only.stdout

    # 6. Test run.py with --verdict-flip
    res_run_flip = subprocess.run(
        [sys.executable, "run.py", "--cli", "--case", "golden", "--sample-mode", "--verdict-flip"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert res_run_flip.returncode == 0
    assert "EXECUTIVE VERDICT-FLIP CARD & DISSENT LOG" in res_run_flip.stdout

    # 7. Test FastAPI endpoints GET /trace/latest and GET /trace/verdict-flip
    res_api_latest = client.get("/trace/latest")
    assert res_api_latest.status_code == 200
    latest_data = res_api_latest.json()
    assert "verdict_flip_card" in latest_data
    assert "winning_verdict" in latest_data["verdict_flip_card"]

    res_api_flip = client.get("/trace/verdict-flip")
    assert res_api_flip.status_code == 200
    flip_data = res_api_flip.json()
    assert flip_data["status"] == "success"
    assert "verdict_flip_card" in flip_data
    assert "counterfactual_trigger" in flip_data["verdict_flip_card"]


def test_explain_trace_rich_and_plain_modes(capsys):
    """Verify scripts/explain_trace.py renders cleanly in both rich and plain text modes."""
    import json
    from scripts.explain_trace import render_verdict_flip_card

    sample_trace = "logs/sample_trace_FAC-DH-01_MED-007.jsonl"
    with open(sample_trace, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    # Force plain text mode
    render_verdict_flip_card(events, use_rich=False)
    plain_out = capsys.readouterr().out
    assert "EXECUTIVE VERDICT-FLIP CARD & DISSENT LOG" in plain_out
    assert "WINNING VERDICT & ROOT CAUSE" in plain_out

    # Force rich mode
    render_verdict_flip_card(events, use_rich=True)
    rich_out = capsys.readouterr().out
    assert "WINNING VERDICT & ROOT CAUSE" in rich_out


def test_export_action_pack_memorandum(tmp_path):
    """Verify scripts/export_action_pack.py generates an executive printable Markdown memorandum."""
    from scripts.export_action_pack import generate_memorandum
    from app.orchestrator import MedTraceOrchestrator

    orchestrator = MedTraceOrchestrator(use_zetaris=False)
    pack = orchestrator.run_investigation("FAC-DH-01", "MED-007")

    out_file = tmp_path / "test_memo.md"
    generated_path = generate_memorandum(pack, output_path=str(out_file))

    assert os.path.exists(generated_path)
    with open(generated_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "DISTRICT HEALTH PROCUREMENT & INVENTORY RECONCILIATION MEMORANDUM" in content
    assert "Document Control & Provenance Metadata" in content
    assert "Executive Inventory Divergence Assessment" in content
    assert "Multi-Agent Root Cause Deliberation" in content
    assert "Ranked Procurement & Transfer Indents" in content
    assert "Official Verification & Indent Authorization Sign-off" in content
    assert "Skeptic Number Auditor" in content
    assert "FAC-DH-01" in content
    assert "MED-007" in content


def test_api_concurrency_and_state_isolation(client):
    """
    Verify that rapid alternating requests to POST /run with varying sample_mode
    options preserve orchestrator state across sessions without state bleeding.
    """
    from run import orchestrator

    orig_sample_mode = orchestrator.llm_client.sample_mode
    orig_use_zetaris = orchestrator.data_store.use_zetaris

    # Send request with sample_mode override True
    res1 = client.post("/run", json={
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-007",
        "options": {"sample_mode": True}
    })
    assert res1.status_code == 200
    assert orchestrator.llm_client.sample_mode == orig_sample_mode
    assert orchestrator.data_store.use_zetaris == orig_use_zetaris

    # Send request without sample_mode override
    res2 = client.post("/run", json={
        "facility_id": "FAC-CHC-01",
        "medicine_id": "MED-001"
    })
    assert res2.status_code == 200
    assert orchestrator.llm_client.sample_mode == orig_sample_mode
    assert orchestrator.data_store.use_zetaris == orig_use_zetaris


def test_validate_clean_clone_script_execution(tmp_path):
    """Verify scripts/validate_clean_clone.py executes cleanly, passes all offline checks, and protects git tree."""
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "scripts/validate_clean_clone.py"],
        capture_output=True,
        text=True,
        env={**os.environ, "SAMPLE_MODE": "true", "USE_ZETARIS": "false", "MEDTRACE_OUTPUT_DIR": str(tmp_path)}
    )
    assert res.returncode == 0, f"validate_clean_clone failed with stderr: {res.stderr}"
    assert "SUCCESS: Clean-clone environment and all quickstart entry points verified!" in res.stdout

    # Assert tracked output/ and logs/ artifacts are strictly untouched
    git_res = subprocess.run(
        ["git", "status", "--porcelain", "output/", "logs/"],
        capture_output=True,
        text=True
    )
    assert git_res.stdout.strip() == "", f"Tracked artifacts were modified by validate_clean_clone:\n{git_res.stdout}"


def test_export_action_pack_respects_custom_output_dir(tmp_path, monkeypatch):
    """Verify generate_memorandum writes to custom output_path and respects MEDTRACE_OUTPUT_DIR."""
    import json
    from scripts.export_action_pack import generate_memorandum

    with open("output_examples/sample_1_district_hospital_metformin.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Custom output path
    target_path = os.path.join(str(tmp_path), "custom_memo.md")
    out = generate_memorandum(data, output_path=target_path)
    assert os.path.exists(out)
    assert out == target_path

    # 2. MEDTRACE_OUTPUT_DIR environment variable
    custom_dir = str(tmp_path / "memo_dir")
    monkeypatch.setenv("MEDTRACE_OUTPUT_DIR", custom_dir)
    out2 = generate_memorandum(data)
    assert os.path.exists(out2)
    assert str(custom_dir) in out2


def test_openapi_documentation_schema_and_metadata(client):
    """Verify OpenAPI Swagger schema contains rich metadata, descriptions, and examples (Item 9)."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    assert "MedTrace" in schema["info"]["title"]
    assert "Zero LLM Arithmetic" in schema["info"]["description"]
    assert "summary" in schema["info"]
    assert "/run" in schema["paths"]
    assert "/decision" in schema["paths"]
    assert "/triage" in schema["paths"]

    run_schema = schema["components"]["schemas"]["RunRequest"]
    assert "properties" in run_schema
    assert "description" in run_schema["properties"]["facility_id"]
    assert "example" in run_schema


def test_docker_compose_configuration():
    """Verify docker-compose.yml exists, is valid YAML, and configures backend service (Item 11)."""
    import yaml

    assert os.path.exists("docker-compose.yml")
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    assert "services" in compose
    assert "backend" in compose["services"]
    backend = compose["services"]["backend"]
    assert "8000:8000" in backend["ports"]
    assert "SAMPLE_MODE=true" in backend["environment"]
    assert "healthcheck" in backend
    assert "postgres" in compose["services"]
    postgres = compose["services"]["postgres"]
    assert postgres["environment"]["POSTGRES_PASSWORD"] == "${POSTGRES_PASSWORD:?set in .env}"
    with open(".env.example", "r", encoding="utf-8") as f:
        env_ex = f.read()
    assert "POSTGRES_PASSWORD" in env_ex


def test_api_get_memo_endpoint(client):
    """Verify GET /memo/{facility_id}/{medicine_id} returns formatted Markdown procurement memo."""
    res = client.get("/memo/FAC-DH-01/MED-007")
    assert res.status_code == 200
    assert "text/markdown" in res.headers.get("content-type", "")
    content = res.text
    assert "DISTRICT HEALTH PROCUREMENT & INVENTORY RECONCILIATION MEMORANDUM" in content
    assert "Target Facility ID**: `FAC-DH-01`" in content
    assert "Confidence Rating" in content
    assert "Skeptic Number Auditor" in content


def test_api_get_trace_latest_endpoint(client):
    """Verify GET /trace/latest returns latest structured debate trace events."""
    res = client.get("/trace/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "trace_file" in data
    assert data["events_count"] >= 5
    assert isinstance(data["events"], list)
    first_event = data["events"][0]
    assert "timestamp" in first_event
    assert "agent" in first_event
    assert "action" in first_event


def test_api_case_insensitive_and_whitespace_tolerant(client):
    """Verify API handles lowercase and whitespace-padded IDs cleanly."""
    res = client.post("/run", json={
        "facility_id": "  fac-dh-01  ",
        "medicine_id": " med-007 "
    })
    assert res.status_code == 200
    pack = res.json()["output"]
    assert pack["facility_id"] == "FAC-DH-01"
    assert pack["medicine_id"] == "MED-007"


def test_output_examples_schema_and_financial_costs_conformance():
    """Verify output_examples/*.json adhere strictly to the live ActionPack schema with financial costs."""
    ex_dir = "output_examples"
    assert os.path.exists(ex_dir)
    files = [f for f in os.listdir(ex_dir) if f.endswith(".json")]
    assert len(files) == 3

    for f in files:
        path = os.path.join(ex_dir, f)
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        assert data["status"] == "success"
        out = data["output"]
        assert "run_id" in out
        assert "winning_hypothesis" in out
        assert "recommendations" in out
        recs = out["recommendations"]
        assert len(recs) >= 2
        for r in recs:
            assert "estimated_cost_usd" in r
            assert r["estimated_cost_usd"] >= 0.0
            assert "number_provenance" in r
            assert "estimated_cost_usd" in r["number_provenance"]


def test_trace_conformance_validator_execution():
    """Verify scripts/validate_traces.py executes and passes validation on active traces."""
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "scripts/validate_traces.py"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0, f"validate_traces.py failed with: {res.stderr}\n{res.stdout}"
    assert "SUCCESS: All multi-agent deliberation traces strictly conform" in res.stdout


def test_dockerfile_configuration():
    """Verify Dockerfile exists, sets offline defaults (SAMPLE_MODE=true, USE_ZETARIS=false)."""
    assert os.path.exists("Dockerfile")
    with open("Dockerfile", "r", encoding="utf-8") as f:
        content = f.read()
    assert "SAMPLE_MODE=true" in content
    assert "USE_ZETARIS=false" in content
    assert "PORT=8000" in content


def test_quick_demo_golden_case_execution(tmp_path):
    """
    Priority 0c Item 1 & Backlog Item 1:
    Verifies scripts/quick_demo.py executes the end-to-end golden quarantine case:
    - Target: FAC-CHC-01, MED-001 (Paracetamol 500mg)
    - 400 quarantined units subject to QA hold, 3.7 days usable stock cover
    - Round 1 Skeptic adversarial challenge -> Round 2 Investigator refutation & revision
    - Action plan: PEER_TRANSFER + BATCH_RELEASE
    - Validates tracked logs/golden_trace_FAC-CHC-01_MED-001.jsonl
    - Validates run.py --case golden CLI preset
    """
    import subprocess
    import sys
    import json
    import os

    # 1. Execute quick_demo.py (defaults to golden case, writes trace to isolated tmp_path)
    temp_trace = tmp_path / "test_quick_demo_trace.jsonl"
    res_demo = subprocess.run(
        [sys.executable, "scripts/quick_demo.py", "--case", "golden", "--output-trace", str(temp_trace)],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert res_demo.returncode == 0, f"quick_demo.py failed:\n{res_demo.stderr}\n{res_demo.stdout}"
    assert "MEDTRACE: EXECUTIVE JUDGE DEMONSTRATION" in res_demo.stdout
    assert "FAC-CHC-01" in res_demo.stdout
    assert "paracetamol" in res_demo.stdout.lower()
    assert "QA quarantine hold" in res_demo.stdout
    assert "MULTI-AGENT ADVERSARIAL DEBATE: ROUND 1" in res_demo.stdout
    assert "MULTI-AGENT ADVERSARIAL DEBATE: ROUND 2" in res_demo.stdout
    assert "PEER_TRANSFER" in res_demo.stdout
    assert "BATCH_RELEASE" in res_demo.stdout
    assert os.path.exists(temp_trace)

    # 2. Verify tracked golden trace exists and has valid events
    golden_trace_path = os.path.join("logs", "golden_trace_FAC-CHC-01_MED-001.jsonl")
    assert os.path.exists(golden_trace_path), "golden_trace_FAC-CHC-01_MED-001.jsonl must exist"
    with open(golden_trace_path, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]
    assert len(events) >= 10
    actions = [e["action"] for e in events]
    assert "START_RUN" in actions
    assert "RECONCILE_COMPLETE" in actions
    assert "ROUND_1_START" in actions
    assert "ROUND_1_EVALUATION" in actions
    assert "ROUND_2_START" in actions
    assert "ROUND_2_EVALUATION" in actions
    assert "ACTIONS_RECOMMENDED" in actions
    assert "ACTION_PLAN_AUDITED" in actions

    # 3. Verify CLI --case golden in run.py
    res_cli = subprocess.run(
        [sys.executable, "run.py", "--cli", "--case", "golden", "--sample-mode"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert res_cli.returncode == 0, f"run.py --case golden failed:\n{res_cli.stderr}\n{res_cli.stdout}"
    assert "Preset Case Loaded: GOLDEN CASE" in res_cli.stdout
    assert "Target: Facility FAC-CHC-01 | Medicine MED-001" in res_cli.stdout
    assert "Winning Hypothesis: Batch Quality Assurance Quarantine & Regulatory Recall" in res_cli.stdout
    assert "PEER_TRANSFER" in res_cli.stdout

def test_verdict_flip_card_dynamic_computation_not_hardcoded():
    """
    Hallucination & Anti-Hardcoding Audit Test:
    Verifies build_verdict_flip_card dynamically derives:
    1. Quarantined units and recovered days of cover from varying inputs (not hardcoded to 400 units / 14.2 days).
    2. Physical audit drift units (not hardcoded).
    3. H-MEM cognitive beliefs with arbitrary supplier IDs and reasons (not hardcoded to SUP-001 or Monsoon).
    Would fail if values were magic constants tuned to sample fixtures.
    """
    from scripts.explain_trace import build_verdict_flip_card

    # Scenario A: 180 quarantined units, 12.0 daily consumption -> 15.0 days cover
    events_a = [
        {"action": "START_RUN", "details": {"facility_id": "FAC-TEST-01", "medicine_id": "MED-TEST-01"}},
        {"action": "RECONCILE_COMPLETE", "details": {
            "usable_stock": 24.0,
            "shortfall": 120.0,
            "ledger_stock": 204.0,
            "quarantined_units": 180.0,
            "audit_drift": 0.0,
            "daily_consumption": 12.0,
            "discrepancies": [{"anomaly_type": "QUARANTINED_BATCH", "impact_units": 180.0}]
        }},
        {"action": "CONTEXT_BUILT", "details": {"canon_hash": "hash_a", "entities_present": ["facility", "medicine"]}},
        {"action": "HYPOTHESES_GENERATED", "details": {
            "titles": ["Batch Quality Assurance Quarantine & Regulatory Recall", "Upstream Logistics Transit Delay", "Demand Surge"],
            "likelihoods": {"H1-INTERNAL-AUDIT": 0.92, "H2-SUPPLIER-TRANSIT": 0.40, "H3-EXTERNAL-SURGE": 0.20}
        }},
        {"action": "ROUND_1_EVALUATION", "details": {
            "accepted": True,
            "confidence": 0.92,
            "critique": "Approved winning hypothesis 'Batch Quality Assurance Quarantine & Regulatory Recall'."
        }},
        {"action": "ACTIONS_RECOMMENDED", "details": {"top_action": "PEER_TRANSFER"}}
    ]

    card_a = build_verdict_flip_card(events_a)
    trigger_a = card_a["counterfactual_trigger"]["reversal_condition"]
    action_a = card_a["counterfactual_trigger"]["action_flip"]

    assert "180 quarantined units" in trigger_a
    assert "+180 units" in action_a
    assert "+15.0 days cover" in action_a
    # Must NOT contain the old hardcoded magic numbers from the golden fixture
    assert "400 quarantined units" not in trigger_a
    assert "+14.2 days cover" not in action_a

    # Scenario B: 320 quarantined units, 16.0 daily consumption -> 20.0 days cover
    events_b = [
        {"action": "START_RUN", "details": {"facility_id": "FAC-TEST-02", "medicine_id": "MED-TEST-02"}},
        {"action": "RECONCILE_COMPLETE", "details": {
            "usable_stock": 40.0,
            "shortfall": 200.0,
            "ledger_stock": 360.0,
            "quarantined_units": 320.0,
            "audit_drift": 0.0,
            "daily_consumption": 16.0,
            "discrepancies": [{"anomaly_type": "QUARANTINED_BATCH", "impact_units": 320.0}]
        }},
        {"action": "CONTEXT_BUILT", "details": {"canon_hash": "hash_b", "entities_present": ["facility", "medicine"]}},
        {"action": "HYPOTHESES_GENERATED", "details": {
            "titles": ["Batch Quality Assurance Quarantine & Regulatory Recall"],
            "likelihoods": {"H1-INTERNAL-AUDIT": 0.95}
        }},
        {"action": "ROUND_1_EVALUATION", "details": {
            "accepted": True,
            "confidence": 0.95,
            "critique": "Approved winning hypothesis 'Batch Quality Assurance Quarantine & Regulatory Recall'."
        }},
        {"action": "ACTIONS_RECOMMENDED", "details": {"top_action": "PEER_TRANSFER"}}
    ]

    card_b = build_verdict_flip_card(events_b)
    trigger_b = card_b["counterfactual_trigger"]["reversal_condition"]
    action_b = card_b["counterfactual_trigger"]["action_flip"]

    assert "320 quarantined units" in trigger_b
    assert "+320 units" in action_b
    assert "+20.0 days cover" in action_b

    # Scenario C: Dynamic H-MEM belief with custom supplier ID and reason
    events_c = [
        {"action": "START_RUN", "details": {"facility_id": "FAC-TEST-03", "medicine_id": "MED-TEST-03"}},
        {"action": "RECONCILE_COMPLETE", "details": {"usable_stock": 10.0, "shortfall": 50.0, "discrepancies": []}},
        {"action": "CONTEXT_BUILT", "details": {
            "canon_hash": "hash_c",
            "entities_present": ["facility", "medicine"],
            "hmem_beliefs": {
                "supplier_delays": {
                    "SUP-DYNAMIC-88": {
                        "p90_delay_days": 25.0,
                        "reason": "Landslide blockage on mountain pass"
                    }
                }
            }
        }},
        {"action": "HYPOTHESES_GENERATED", "details": {
            "titles": ["Upstream Logistics Transit Delay"],
            "likelihoods": {"H2-SUPPLIER-TRANSIT": 0.90}
        }},
        {"action": "ROUND_1_EVALUATION", "details": {
            "accepted": True,
            "confidence": 0.90,
            "critique": "Approved winning hypothesis 'Upstream Logistics Transit Delay'."
        }},
        {"action": "ACTIONS_RECOMMENDED", "details": {"top_action": "PEER_TRANSFER"}}
    ]

    card_c = build_verdict_flip_card(events_c)
    memory_facts_c = card_c["cognitive_memory_impact"]["memory_facts"]
    assert len(memory_facts_c) >= 1
    assert "SUP-DYNAMIC-88 +25d delay: Landslide blockage on mountain pass" in memory_facts_c[0]
    # Verify no hardcoded legacy strings leak into dynamic scenario
    assert "SUP-001" not in memory_facts_c[0]
    assert "Monsoon bridge washout" not in memory_facts_c[0]

