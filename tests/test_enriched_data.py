"""
Unit and Integration Tests for Enriched Data & Multi-Agent Loop (tests/test_enriched_data.py)
Validates:
1. DataStore accessors for newly ingested public health datasets.
2. DeterministicEngine UOM normalization and WHO GHO demand multipliers.
3. Reconciler discrepancy generation for UOM mismatch and FDA recalls.
4. Investigator and Skeptic adversarial review loop.
"""

import pytest
from app.adapters.data_store import DataStore
from app.engine.deterministic import DeterministicEngine
from app.engines.world_model import WorldStoreService, IngestPipelineService
from app.agents.reconciler import ReconcilerAgent
from app.agents.investigator import InvestigatorAgent
from app.agents.skeptic import SkepticAgent
from app.adapters.llm_client import LLMClient

@pytest.fixture
def store():
    return DataStore(use_zetaris=False)

def test_datastore_enriched_accessors(store):
    # Test openFDA enforcement recalls
    recalls = store.get_openfda_recalls(medicine_id="MED-001")
    assert isinstance(recalls, list)
    assert len(recalls) > 0
    assert "reason_for_recall" in recalls[0]

    # Test RxNorm standards
    rxnorm = store.get_rxnorm_standard("MED-001")
    assert rxnorm is not None
    assert rxnorm["rxcui"] == "161"
    assert "acetaminophen" in rxnorm["rxnorm_name"].lower()

    # Test DailyMed packaging standards
    pkg = store.get_packaging_standard("MED-001")
    assert pkg is not None
    assert "storage_condition" in pkg

    # Test WHO disease surveillance
    surv = store.get_disease_surveillance("MED-009")
    assert surv is not None
    assert surv["epidemiological_risk_tier"] == "ELEVATED"

    # Test cross-border shortages
    shortage = store.get_cross_border_shortages(medicine_id="MED-007")
    assert shortage is not None
    assert "root_cause_classification" in shortage

    # Test deliveries
    deliveries = store.get_deliveries()
    assert isinstance(deliveries, list)
    assert len(deliveries) > 0

def test_deterministic_uom_normalization():
    # Box of 100 tablets vs individual tablet
    res = DeterministicEngine.normalize_uom_quantity(
        reported_quantity=5,
        reported_unit="box",
        dispensing_unit="tablet"
    )
    assert res["uom_mismatch_detected"] is True
    assert res["pack_multiplier"] == 100.0
    assert res["normalized_quantity"] == 500.0

    # Custom pack size multiplier
    res_custom = DeterministicEngine.normalize_uom_quantity(
        reported_quantity=10,
        reported_unit="strip",
        dispensing_unit="tablet",
        pack_size_units=10
    )
    assert res_custom["uom_mismatch_detected"] is True
    assert res_custom["normalized_quantity"] == 100.0

def test_deterministic_epidemiological_multiplier():
    # Standard risk tier
    res_std = DeterministicEngine.compute_epidemiological_demand_multiplier(
        base_rate=20.0,
        surveillance_data={"epidemiological_risk_tier": "STANDARD"}
    )
    assert res_std["who_surveillance_multiplier"] == 1.0
    assert res_std["adjusted_daily_demand"] == 20.0
    assert res_std["demand_spike_detected"] is False

    # Elevated risk tier (outbreak surge)
    res_elevated = DeterministicEngine.compute_epidemiological_demand_multiplier(
        base_rate=20.0,
        atc_seasonal_multiplier=1.1,
        surveillance_data={"epidemiological_risk_tier": "ELEVATED"}
    )
    assert res_elevated["who_surveillance_multiplier"] == 1.35
    assert res_elevated["combined_multiplier"] >= 1.40
    assert res_elevated["demand_spike_detected"] is True
    assert res_elevated["adjusted_daily_demand"] > 25.0

def test_reconciler_and_skeptic_loop(store):
    world_store = WorldStoreService()
    ingest = IngestPipelineService(world_store)
    reconciler = ReconcilerAgent(store, ingest)
    llm = LLMClient()
    investigator = InvestigatorAgent(llm)
    skeptic = SkepticAgent(llm)

    # Reconcile quarantined item
    recon = reconciler.reconcile_item("FAC-CHC-01", "MED-001")
    assert recon["facility_id"] == "FAC-CHC-01"
    assert recon["medicine_id"] == "MED-001"
    discs = recon["discrepancies"]
    assert any(d["anomaly_type"] == "QUARANTINED_BATCH" for d in discs)

    # Investigator generates hypotheses
    hypotheses = investigator.investigate(recon, context={})
    assert len(hypotheses) == 3

    # Skeptic reviews and audits numbers
    top_hyp, review = skeptic.review_and_audit(
        hypotheses=hypotheses,
        deterministic_recon=recon["deterministic_reconciliation"],
        round_number=1
    )
    assert review.audited_numbers_valid is True
    assert review.confidence_score > 0.0

def test_datastore_uom_pack_multiplier_grounding(store):
    """
    Validates that DataStore derives packaging multipliers directly from
    DailyMed and RxNorm standards without hardcoding.
    """
    # Dispensing unit for MED-001 is tablet, MED-004 is capsule
    assert store.get_uom_pack_multiplier("MED-001", "tablet") == 1.0
    assert store.get_uom_pack_multiplier("MED-001", "strip") == 10.0
    assert store.get_uom_pack_multiplier("MED-001", "box") == 100.0
    assert store.get_uom_pack_multiplier("MED-001", "carton") == 100.0

    assert store.get_uom_pack_multiplier("MED-004", "capsule") == 1.0
    assert store.get_uom_pack_multiplier("MED-004", "blister") == 10.0
    assert store.get_uom_pack_multiplier("MED-004", "box of 100") == 100.0

def test_reconciler_uom_mismatch_uses_packaging_standards(store):
    """
    Validates that ReconcilerAgent extracts dispensing unit and packaging spec
    from DailyMed / RxNorm data when reconciling PO vs delivery quantities.
    """
    world_store = WorldStoreService()
    ingest = IngestPipelineService(world_store)
    reconciler = ReconcilerAgent(store, ingest)

    # Mock deliveries with a 10x pack mismatch
    mock_deliveries = [{
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-004",
        "po_id": "PO-TEST-001",
        "received_qty": 50.0,
        "delivery_date": "2026-03-01"
    }]
    mock_pos = [{
        "facility_id": "FAC-DH-01",
        "medicine_id": "MED-004",
        "po_id": "PO-TEST-001",
        "quantity": 500.0,
        "status": "DELIVERED"
    }]

    # Temporarily monkeypatch get_deliveries and get_purchase_orders
    orig_deliv = store.get_deliveries
    orig_pos = store.get_purchase_orders
    try:
        store.get_deliveries = lambda fac, med: mock_deliveries
        store.get_purchase_orders = lambda fac, med: mock_pos

        recon = reconciler.reconcile_item("FAC-DH-01", "MED-004")
        uom_disc = next((d for d in recon["discrepancies"] if d["anomaly_type"] == "UOM_MISMATCH"), None)
        assert uom_disc is not None
        # MED-004 dispensing unit is capsule from DailyMed / RxNorm
        assert "capsule" in uom_disc["description"].lower()
    finally:
        store.get_deliveries = orig_deliv
        store.get_purchase_orders = orig_pos

