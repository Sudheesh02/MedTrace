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
