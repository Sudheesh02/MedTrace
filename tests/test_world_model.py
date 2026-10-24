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
