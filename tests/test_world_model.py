"""
Tests for Meterless World Model & H-MEM Engines in MedTrace.
"""

import pytest
from app.engines.world_model import WorldStoreService, IngestPipelineService, ContextBuilderService
from app.engines.hmem import HMemEngine

def test_world_model_idempotency_and_stable_ids():
    store = WorldStoreService()
    ingest = IngestPipelineService(store)
    context_builder = ContextBuilderService(store)

    fac = {"facility_id": "FAC-DH-01", "name": "District Hospital"}
    med = {"medicine_id": "MED-001", "generic_name": "Paracetamol"}
    stock = {"ledger_stock": 100, "usable_stock": 70}

    # Ingest twice with same input
    id1 = ingest.ingest_facility_item(fac, med, stock, agent_id="agent1")
    id2 = ingest.ingest_facility_item(fac, med, stock, agent_id="agent2")

    # Idempotent: same entity ID generated
    assert id1 == id2
    assert id1.startswith("ent_inv_")

    ctx = context_builder.build_structured_context("FAC-DH-01", "MED-001")
    assert ctx["facility"]["name"] == "District Hospital"
    assert ctx["medicine"]["generic_name"] == "Paracetamol"
    assert len(ctx["relationships"]) >= 2
    assert "canon_hash" in ctx

def test_hmem_cross_session_memory():
    # In-memory test store
    hmem = HMemEngine(persistence_file="logs/test_hmem.json")
    
    # Record an officer rejection
    hmem.record_officer_decision(
        facility_id="FAC-PHC-01",
        medicine_id="MED-004",
        action_type="PEER_TRANSFER",
        decision="REJECTED",
        reason="Route roads blocked due to flash floods"
    )

    memories = hmem.get_relevant_memories("FAC-PHC-01", "MED-004")
    assert len(memories["past_episodes"]) >= 1
    assert any("PEER_TRANSFER" in p for p in memories["rejected_patterns"])
    assert memories["past_episodes"][0]["decision"] == "REJECTED"


def test_world_model_planted_conflict_recording():
    """
    Test W2 (Execution Plan Phase 4):
    Verifies that all planted conflict types (GHOST_STOCK, PO_DISPATCHED_NOT_RECEIVED,
    UOM_MISMATCH, CHRONIC_SUPPLIER_SLIP) are recorded as conflicts in the World Model
    with entity provenance and timestamp.
    """
    from app.adapters.data_store import DataStore
    from app.agents.reconciler import ReconcilerAgent

    store = WorldStoreService()
    ingest = IngestPipelineService(store)
    
    # Ingest multiple conflict types directly
    conflict_types = [
        ("GHOST_STOCK", "FAC-DH-01", "MED-007", 50.0),
        ("PO_DISPATCHED_NOT_RECEIVED", "FAC-CHC-02", "MED-002", 500.0),
        ("UOM_MISMATCH", "FAC-PHC-03", "MED-008", 900.0),
        ("CHRONIC_SUPPLIER_SLIP", "FAC-DH-01", "MED-010", 12.0)
    ]
    for c_type, fac_id, med_id, mag in conflict_types:
        ingest.record_discrepancy_conflict(
            discrepancy={
                "discrepancy_id": f"DISC_{fac_id}_{med_id}_{c_type}",
                "anomaly_type": c_type,
                "magnitude": mag,
                "description": f"Planted test conflict {c_type}"
            },
            facility_id=fac_id,
            medicine_id=med_id,
            agent_id="reconciler"
        )

    # Verify all conflicts are stored in World Store
    all_conflicts = store.get_conflicts()
    assert len(all_conflicts) == 4
    recorded_types = {c["type"] for c in all_conflicts}
    for c_type, _, _, _ in conflict_types:
        assert c_type in recorded_types

    # Verify entity-level filtering
    dh_conflicts = store.get_conflicts(entity_id="FAC-DH-01")
    assert len(dh_conflicts) == 2
    assert all("FAC-DH-01" in c["entity_ids"] for c in dh_conflicts)

    # Verify end-to-end reconciliation records discrepancy conflicts
    data_store = DataStore(use_zetaris=False)
    reconciler = ReconcilerAgent(data_store, ingest)
    recon = reconciler.reconcile_item("FAC-DH-01", "MED-007")
    
    dh_med7_conflicts = store.get_conflicts(entity_id="MED-007")
    assert len(dh_med7_conflicts) >= 1
    assert any("reconciler" == c["recorded_by"] for c in dh_med7_conflicts)

def test_hmem_contradiction_resolution():
    """
    Test H2 (Execution Plan Phase 4):
    Verifies that a later contradicting decision resolves the conflict deterministically:
    When an officer first rejects an action pattern and subsequently approves it,
    prior rejection penalties are cleared from rejected_patterns and preferences resolve deterministically.
    """
    import os
    test_hmem_file = "logs/test_hmem_contradiction.json"
    if os.path.exists(test_hmem_file):
        os.remove(test_hmem_file)

    hmem = HMemEngine(persistence_file=test_hmem_file)

    # 1. First record an officer rejection
    hmem.record_officer_decision(
        facility_id="FAC-PHC-01",
        medicine_id="MED-004",
        action_type="PEER_TRANSFER",
        decision="REJECTED",
        reason="Route roads blocked due to flash floods"
    )

    memories_v1 = hmem.get_relevant_memories("FAC-PHC-01", "MED-004")
    assert len(memories_v1["past_episodes"]) == 1
    assert any("PEER_TRANSFER on MED-004" in p for p in memories_v1["rejected_patterns"])
    pref_v1 = memories_v1["officer_preferences"].get("FAC-PHC-01_PEER_TRANSFER")
    assert pref_v1["rejected"] == 1
    assert pref_v1["approved"] == 0

    # 2. Later session: officer approves the same action (roads reopened)
    hmem.record_officer_decision(
        facility_id="FAC-PHC-01",
        medicine_id="MED-004",
        action_type="PEER_TRANSFER",
        decision="APPROVED",
        reason="Road repair complete; floodwaters receded"
    )

    memories_v2 = hmem.get_relevant_memories("FAC-PHC-01", "MED-004")
    assert len(memories_v2["past_episodes"]) == 2
    # Contradiction Resolution: rejection pattern must be removed from active memory
    assert not any("PEER_TRANSFER on MED-004" in p for p in memories_v2["rejected_patterns"])
    pref_v2 = memories_v2["officer_preferences"].get("FAC-PHC-01_PEER_TRANSFER")
    assert pref_v2["approved"] == 1
    assert pref_v2["rejected"] == 0  # Rejection penalty decremented deterministically


def test_hmem_supplier_delay_belief_changes_decision(tmp_path):
    """
    Test H3 (Priority 0c Item 2 & Backlog Item 2):
    Meterless H-MEM decision-changing feedback loop.
    Demonstrates that seeding a prior supplier-slip fact in H-MEM actively flips
    the downstream decision between with vs without that memory on identical source records.

    Scenario:
    - Facility: FAC-PHC-01 (Rural PHC Block A)
    - Medicine: MED-004 (Amoxicillin)
    - Active PO: SUP-001 (promised delivery within 3 days)

    Run 1 (WITHOUT memory):
      - Default empirical slip (3.0d) leaves inventory adequate.
      - Top action recommendation is MONITOR_BUFFER (0.0 units shortfall, no emergency transfer required).
      - Trace saved to isolated test path (and committed canonical trace logs/trace_without_memory.jsonl exists).

    Seed H-MEM:
      - hmem.record_supplier_delay("SUP-001", 15.0, "Monsoon bridge washout on northern corridor")

    Run 2 (WITH memory):
      - Reconciler queries H-MEM, sees learned +15d delay for SUP-001.
      - Projected delivery slips to 18d; usable stock runs out in ~2.8 to 4 days.
      - Discrepancy flags CHRONIC_SUPPLIER_SLIP with grounded H-MEM explanation.
      - Action Planner eliminates MONITOR_BUFFER and flips top action to urgent PEER_TRANSFER.
      - Trace saved to isolated test path (and committed canonical trace logs/trace_with_memory.jsonl exists).
    """
    import json
    import os
    import shutil
    from app.orchestrator import MedTraceOrchestrator
    from app.engines.hmem import HMemEngine
    from app.models.schemas import ActionType, AnomalyType

    # 1. Setup mock data store wrappers for deterministic scenario isolation
    hmem1 = HMemEngine(persistence_file=str(tmp_path / "hmem1.json"))
    orch1 = MedTraceOrchestrator(use_zetaris=False, hmem=hmem1, logs_dir=str(tmp_path / "logs1"))
    
    orig_pos = orch1.data_store.get_purchase_orders
    orig_batches = orch1.data_store.get_batches
    orig_ledger = orch1.data_store.get_latest_ledger
    orig_audit = orch1.data_store.get_latest_physical_audit
    orig_lod = orch1.data_store.get_ledger_on_date

    def mock_pos(fac, med):
        if fac == "FAC-PHC-01" and med == "MED-004":
            return [{
                "po_id": "PO-ACTIVE-01",
                "supplier_id": "SUP-001",
                "facility_id": "FAC-PHC-01",
                "medicine_id": "MED-004",
                "quantity": "100",
                "order_date": "2026-10-21",
                "promised_date": "2026-10-24",
                "status": "DISPATCHED"
            }]
        return orig_pos(fac, med)

    def mock_batches(fac, med):
        if fac == "FAC-PHC-01" and med == "MED-004":
            return [{
                "batch_id": "BAT-TEST-01",
                "medicine_id": "MED-004",
                "facility_id": "FAC-PHC-01",
                "quantity": 75.0,
                "expiry_date": "2027-04-29",
                "quarantined": False,
                "days_to_expiry": 187
            }]
        return orig_batches(fac, med)

    def mock_ledger(fac, med):
        if fac == "FAC-PHC-01" and med == "MED-004":
            return {"date": "2026-10-24", "facility_id": "FAC-PHC-01", "medicine_id": "MED-004", "ledger_stock": 75.0}
        return orig_ledger(fac, med)

    def mock_audit(fac, med):
        if fac == "FAC-PHC-01" and med == "MED-004":
            return {"date": "2026-10-24", "facility_id": "FAC-PHC-01", "medicine_id": "MED-004", "counted_stock": 75.0}
        return orig_audit(fac, med)

    def mock_lod(fac, med, dt):
        if fac == "FAC-PHC-01" and med == "MED-004":
            return {"date": dt, "facility_id": "FAC-PHC-01", "medicine_id": "MED-004", "ledger_stock": 75.0}
        return orig_lod(fac, med, dt)

    orch1.data_store.get_purchase_orders = mock_pos
    orch1.data_store.get_batches = mock_batches
    orch1.data_store.get_latest_ledger = mock_ledger
    orch1.data_store.get_latest_physical_audit = mock_audit
    orch1.data_store.get_ledger_on_date = mock_lod

    # Execute Run 1 (WITHOUT memory)
    pack1 = orch1.run_investigation("FAC-PHC-01", "MED-004")
    assert pack1.recommendations[0].action_type == ActionType.MONITOR_BUFFER
    assert pack1.recommendations[0].recommended_units == 0.0
    assert pack1.recommendations[0].feasibility_score >= 0.70

    trace1_copy = tmp_path / "trace_without_memory.jsonl"
    shutil.copyfile(pack1.trace_file, trace1_copy)
    assert os.path.exists(trace1_copy)

    # 2. Seed Meterless H-MEM with prior supplier delay belief
    hmem2 = HMemEngine(persistence_file=str(tmp_path / "hmem2.json"))
    hmem2.record_supplier_delay("SUP-001", 15.0, "Monsoon bridge washout on northern corridor")
    assert hmem2.get_supplier_delay("SUP-001") == 15.0

    orch2 = MedTraceOrchestrator(use_zetaris=False, hmem=hmem2, logs_dir=str(tmp_path / "logs2"))
    orch2.data_store.get_purchase_orders = mock_pos
    orch2.data_store.get_batches = mock_batches
    orch2.data_store.get_latest_ledger = mock_ledger
    orch2.data_store.get_latest_physical_audit = mock_audit
    orch2.data_store.get_ledger_on_date = mock_lod

    # Execute Run 2 (WITH memory on identical source records)
    pack2 = orch2.run_investigation("FAC-PHC-01", "MED-004")
    assert pack2.recommendations[0].action_type == ActionType.PEER_TRANSFER
    assert pack2.recommendations[0].recommended_units > 0.0
    assert "H-MEM Grounded Delay" in pack2.recommendations[0].justification
    assert "Monsoon bridge washout" in pack2.recommendations[0].justification

    trace2_copy = tmp_path / "trace_with_memory.jsonl"
    shutil.copyfile(pack2.trace_file, trace2_copy)
    assert os.path.exists(trace2_copy)

    # Verify decision flipped between Run 1 and Run 2
    assert pack1.recommendations[0].action_type != pack2.recommendations[0].action_type

    # 3. Also verify canonical committed traces exist and conform to schema
    canon1 = os.path.join("logs", "trace_without_memory.jsonl")
    canon2 = os.path.join("logs", "trace_with_memory.jsonl")
    assert os.path.exists(canon1), "Canonical trace_without_memory.jsonl must exist"
    assert os.path.exists(canon2), "Canonical trace_with_memory.jsonl must exist"

    with open(canon1, "r", encoding="utf-8") as f:
        events1 = [json.loads(line) for line in f if line.strip()]
    with open(canon2, "r", encoding="utf-8") as f:
        events2 = [json.loads(line) for line in f if line.strip()]

    act1 = next(e for e in events1 if e.get("agent") == "ActionPlannerAgent")
    act2 = next(e for e in events2 if e.get("agent") == "ActionPlannerAgent")
    assert act1["details"]["top_action"] == "MONITOR_BUFFER"
    assert act2["details"]["top_action"] == "PEER_TRANSFER"
