"""
Integration tests for MedTrace Multi-Agent Loop.
"""

import os
import json
import pytest
from app.orchestrator import MedTraceOrchestrator

def test_multi_agent_investigation_loop():
    orchestrator = MedTraceOrchestrator(use_zetaris=False)
    pack = orchestrator.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")

    assert pack.run_id is not None
    assert pack.facility_id == "FAC-DH-01"
    assert pack.medicine_id == "MED-007"
    assert pack.winning_hypothesis is not None
    assert len(pack.recommendations) >= 2
    assert 1 <= pack.skeptic_rounds <= 3
    
    # Verify trace file exists and has valid JSONL entries
    assert os.path.exists(pack.trace_file)
    with open(pack.trace_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 5
        first_entry = json.loads(lines[0])
        assert "run_id" in first_entry
        assert "agent" in first_entry
        assert first_entry["agent"] == "Orchestrator"

def test_number_auditor_provenance():
    """
    Verify that every recommended action carries strict deterministic number provenance:
    - For PEER_TRANSFER, EXPEDITE_PO, EMERGENCY_PURCHASE: recommended_units equals shortfall_units
    - For BATCH_RELEASE: recommended_units equals quarantined_units
    - For INVENTORY_AUDIT_ADJUSTMENT: recommended_units equals audit_drift
    Tested across multiple distinct facilities to ensure behavior is general and not hardcoded to a single fixture.
    """
    from app.models.schemas import ActionType
    orchestrator = MedTraceOrchestrator(use_zetaris=False)

    # Test Case 1: Phantom Stock at District Hospital (audit drift)
    pack_dh = orchestrator.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")
    adj_recs = [r for r in pack_dh.recommendations if r.action_type == ActionType.INVENTORY_AUDIT_ADJUSTMENT]
    assert len(adj_recs) == 1
    assert adj_recs[0].recommended_units == 50.0
    assert adj_recs[0].number_provenance["audit_drift"] == 50.0

    for rec in pack_dh.recommendations:
        if rec.action_type in (ActionType.PEER_TRANSFER, ActionType.EXPEDITE_PO, ActionType.EMERGENCY_PURCHASE):
            assert "shortfall_units" in rec.number_provenance
            assert rec.recommended_units == rec.number_provenance["shortfall_units"]
        elif rec.action_type == ActionType.INVENTORY_AUDIT_ADJUSTMENT:
            assert "audit_drift" in rec.number_provenance
            assert rec.recommended_units == rec.number_provenance["audit_drift"]

    # Test Case 2: Quarantined batch at Community Health Centre (active deficit & batch release)
    pack_chc = orchestrator.run_investigation(facility_id="FAC-CHC-01", medicine_id="MED-001")
    rel_recs = [r for r in pack_chc.recommendations if r.action_type == ActionType.BATCH_RELEASE]
    assert len(rel_recs) == 1
    assert rel_recs[0].recommended_units == 400.0
    assert rel_recs[0].number_provenance["quarantined_units"] == 400.0

    trf_recs = [r for r in pack_chc.recommendations if r.action_type == ActionType.PEER_TRANSFER]
    assert len(trf_recs) == 1
    assert trf_recs[0].recommended_units > 0
    assert trf_recs[0].recommended_units == trf_recs[0].number_provenance["shortfall_units"]

def test_investigator_annotations_and_anomaly_types():
    """Verify InvestigatorAgent method type annotations resolve cleanly and all 10 simulation anomalies map to AnomalyType."""
    import pandas as pd
    from app.agents.investigator import InvestigatorAgent
    from app.models.schemas import AnomalyType

    annotations = InvestigatorAgent.investigate.__annotations__
    assert "skeptic_feedback" in annotations
    assert "reconciliation" in annotations

    gt_df = pd.read_csv("data/simulated/ground_truth.csv")
    simulation_anomaly_types = set(gt_df["type"].unique())
    assert len(simulation_anomaly_types) == 10

    for anomaly_str in simulation_anomaly_types:
        assert anomaly_str in AnomalyType.__members__, f"Simulation anomaly {anomaly_str} missing from AnomalyType enum"
        enum_val = AnomalyType[anomaly_str]
        assert enum_val.value == anomaly_str

def test_skeptic_adversarial_critique_triggers_round_2():
    """
    Verify that when competing hypotheses have close likelihoods (Delta <= 0.15),
    the Skeptic rejects on Round 1 and forces Investigator to perform differential
    elimination in Round 2, resulting in pack.skeptic_rounds >= 2.
    """
    orchestrator = MedTraceOrchestrator(use_zetaris=False)
    pack = orchestrator.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")

    assert pack.skeptic_rounds >= 2
    assert pack.winning_hypothesis is not None
    assert pack.winning_hypothesis.likelihood >= 0.85

    # Verify trace log records the debate loop
    assert os.path.exists(pack.trace_file)
    with open(pack.trace_file, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f]

    actions = [e["action"] for e in events]
    assert "ROUND_1_START" in actions
    assert "ROUND_1_EVALUATION" in actions
    assert "ROUND_2_START" in actions
    assert "ROUND_2_EVALUATION" in actions

    # Verify Round 1 evaluation was a rejection (challenge)
    r1_eval = next(e for e in events if e["action"] == "ROUND_1_EVALUATION")
    assert r1_eval["details"]["accepted"] is False
    assert "challenged" in r1_eval["details"]["critique"].lower()
    assert len(r1_eval["details"]["flagged_inconsistencies"]) >= 1

    # Verify Round 2 start received previous critique
    r2_start = next(e for e in events if e["action"] == "ROUND_2_START")
    assert r2_start["details"]["previous_critique"] is not None
    assert "challenged" in r2_start["details"]["previous_critique"].lower()

    # Verify Round 2 evaluation was accepted with revised differential
    r2_eval = next(e for e in events if e["action"] == "ROUND_2_EVALUATION")
    assert r2_eval["details"]["accepted"] is True
    assert "approved" in r2_eval["details"]["critique"].lower()

def test_skeptic_accepts_uncontested_hypothesis_on_round_1():
    """
    Verify that when hypotheses have clear differential separation (>0.15) and
    valid deterministic numbers, Skeptic accepts directly on Round 1.
    """
    from app.agents.skeptic import SkepticAgent
    from app.adapters.llm_client import LLMClient
    from app.models.schemas import Hypothesis

    skeptic = SkepticAgent(LLMClient())
    hypotheses = [
        Hypothesis(
            hypothesis_id="H1",
            title="Batch Quality Assurance Quarantine",
            cause="Confirmed batch quarantine",
            likelihood=0.92,
            supporting_evidence=["Quality hold active", "Lab test pending"],
            refuting_evidence=[],
            confirming_query="SELECT * FROM batches"
        ),
        Hypothesis(
            hypothesis_id="H2",
            title="Supplier Delay",
            cause="Transit delay",
            likelihood=0.30,
            supporting_evidence=["Routine transit"],
            refuting_evidence=[],
            confirming_query="SELECT * FROM po"
        )
    ]
    deterministic_recon = {
        "stock_evaluation": {
            "ledger_stock": 100.0,
            "usable_stock": 50.0,
            "audit_drift": 0.0,
            "quarantined_stock": 50.0,
            "expiring_stock": 0.0
        },
        "trust_shortfall": {
            "shortfall_units": 40.0,
            "gap_days": 4.0
        }
    }
    top_hyp, review = skeptic.review_and_audit(hypotheses, deterministic_recon, round_number=1)
    assert review.accepted is True
    assert review.confidence_score >= 0.90
    assert top_hyp.hypothesis_id == "H1"
    assert "verified" in review.critique_notes.lower()

def test_skeptic_number_auditor_rejects_arithmetic_inconsistency():
    """
    Verify that if usable stock deviates from deterministic ground truth,
    the Number Auditor rejects regardless of hypothesis likelihood.
    """
    from app.agents.skeptic import SkepticAgent
    from app.adapters.llm_client import LLMClient
    from app.models.schemas import Hypothesis

    skeptic = SkepticAgent(LLMClient())
    hypotheses = [
        Hypothesis(
            hypothesis_id="H1",
            title="Clear Dominant Cause",
            cause="Explanation",
            likelihood=0.95,
            supporting_evidence=["Evidence 1", "Evidence 2"],
            refuting_evidence=[],
            confirming_query="SELECT 1"
        )
    ]
    # Invariant violation: usable_stock != ledger - drift - quar - expiring
    deterministic_recon = {
        "stock_evaluation": {
            "ledger_stock": 100.0,
            "usable_stock": 90.0,  # Expected 100 - 30 = 70.0
            "audit_drift": 30.0,
            "quarantined_stock": 0.0,
            "expiring_stock": 0.0
        },
        "trust_shortfall": {
            "shortfall_units": 10.0,
            "gap_days": 2.0
        }
    }
    top_hyp, review = skeptic.review_and_audit(hypotheses, deterministic_recon, round_number=1)
    assert review.accepted is False
    assert review.audited_numbers_valid is False
    assert any("invariant failed" in inc.lower() for inc in review.flagged_inconsistencies)


def test_action_planner_peer_surplus_validation():
    """
    Verify that ActionPlannerAgent dynamically evaluates peer facilities for usable surplus,
    never self-transfers from the target facility, and identifies BATCH_RELEASE when appropriate.
    """
    from app.agents.action_planner import ActionPlannerAgent
    from app.adapters.data_store import DataStore
    from app.adapters.llm_client import LLMClient
    from app.engines.hmem import HMemEngine
    from app.models.schemas import Hypothesis, ActionType

    ds = DataStore(use_zetaris=False)
    planner = ActionPlannerAgent(LLMClient(), HMemEngine(), data_store=ds)

    hyp = Hypothesis(
        hypothesis_id="H1-QUAR",
        title="Batch Quality Assurance Quarantine & Regulatory Recall",
        cause="Quarantined batch",
        likelihood=0.90,
        supporting_evidence=["400 units quarantined"],
        refuting_evidence=[],
        confirming_query="SELECT 1"
    )
    det_recon = {
        "trust_shortfall": {"shortfall_units": 150.0, "gap_days": 5.0},
        "stock_evaluation": {
            "ledger_stock": 500.0,
            "usable_stock": 100.0,
            "quarantined_stock": 400.0,
            "audit_drift": 0.0,
            "expiring_stock": 0.0
        },
        "trust_cover_days": 3.5
    }

    # Test case 1: Target is FAC-CHC-01
    recs = planner.plan_actions("FAC-CHC-01", "MED-001", hyp, det_recon)
    rec_types = [r.action_type for r in recs]
    assert ActionType.BATCH_RELEASE in rec_types
    assert ActionType.PEER_TRANSFER in rec_types

    trf = next(r for r in recs if r.action_type == ActionType.PEER_TRANSFER)
    assert trf.source_facility_id is not None
    assert trf.source_facility_id != "FAC-CHC-01"  # No self-transfer!
    assert "peer warehouse" in trf.justification

    # Test case 2: Target is the main warehouse FAC-WH-01 itself
    recs_wh = planner.plan_actions("FAC-WH-01", "MED-001", hyp, det_recon)
    trf_wh = next(r for r in recs_wh if r.action_type == ActionType.PEER_TRANSFER)
    assert trf_wh.source_facility_id != "FAC-WH-01"  # Must NOT transfer from itself

def test_orchestrator_input_validation():
    """Verify that orchestrator raises ValueError on unknown facilities or medicines."""
    orch = MedTraceOrchestrator(use_zetaris=False)
    with pytest.raises(ValueError, match="Unrecognized facility_id"):
        orch.run_investigation(facility_id="FAC-DOES-NOT-EXIST", medicine_id="MED-001")

    with pytest.raises(ValueError, match="Unrecognized medicine_id"):
        orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-DOES-NOT-EXIST")

def test_orchestrator_human_escalation_path():
    """
    Verify Execution Plan Phase 3.6:
    When multi-agent debate fails to establish an accepted high-confidence hypothesis,
    the ActionPack is flagged with escalated_to_human=True and escalation_reason populated.
    """
    from unittest.mock import MagicMock
    from app.models.schemas import SkepticReview, Hypothesis

    orch = MedTraceOrchestrator(use_zetaris=False)
    # Mock skeptic to persistently challenge with low confidence
    mock_skeptic = MagicMock()
    mock_skeptic.review_and_audit.return_value = (
        Hypothesis(
            hypothesis_id="H-LOW",
            title="Uncertain Cause",
            cause="Unverified cause",
            likelihood=0.40,
            supporting_evidence=[],
            refuting_evidence=[],
            confirming_query="SELECT 1"
        ),
        SkepticReview(
            accepted=False,
            confidence_score=0.35,
            critique_notes="Persistent ambiguity across all competing hypotheses.",
            audited_numbers_valid=True,
            flagged_inconsistencies=["Conflicting audit logs"]
        )
    )
    orch.skeptic = mock_skeptic

    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")
    assert pack.escalated_to_human is True
    assert pack.escalation_reason is not None
    assert "manual human officer verification" in pack.escalation_reason


def test_action_planner_dynamic_quantities_across_varying_scenarios():
    """
    Parametric multi-scenario test:
    Verifies that ActionPlanner dynamically computes recommended quantities and provenance
    across distinct facility/medicine combinations, proving that outputs are never tuned
    to a single canned fixture.
    """
    from app.models.schemas import ActionType
    orch = MedTraceOrchestrator(use_zetaris=False)

    scenarios = [
        ("FAC-DH-01", "MED-007"),  # District Hospital Metformin (phantom drift 50.0 units, 0 shortfall)
        ("FAC-PHC-01", "MED-004"), # Rural PHC Amoxicillin (expiring batch, ~44 units shortfall)
        ("FAC-CHC-01", "MED-001"), # North Sub-District CHC Paracetamol (quarantined 400 units, ~148 units shortfall)
    ]

    results = []
    for fac_id, med_id in scenarios:
        pack = orch.run_investigation(facility_id=fac_id, medicine_id=med_id)
        assert pack.facility_id == fac_id
        assert pack.medicine_id == med_id
        assert pack.winning_hypothesis is not None
        assert len(pack.recommendations) >= 2

        # Extract quantities per action type
        rec_map = {r.action_type: r.recommended_units for r in pack.recommendations}
        results.append(rec_map)

        # Enforce that numbers are never negative and adhere to provenance
        for rec in pack.recommendations:
            assert rec.recommended_units >= 0.0
            if rec.action_type == ActionType.INVENTORY_AUDIT_ADJUSTMENT:
                assert rec.recommended_units == rec.number_provenance["audit_drift"]
            elif rec.action_type == ActionType.BATCH_RELEASE:
                assert rec.recommended_units == rec.number_provenance["quarantined_units"]
            elif rec.action_type in (ActionType.PEER_TRANSFER, ActionType.EXPEDITE_PO, ActionType.EMERGENCY_PURCHASE):
                assert rec.recommended_units == rec.number_provenance["shortfall_units"]

    # Verify that recommended quantities differ substantially across scenarios (dynamic, non-canned)
    trf_quantities = [r.get(ActionType.PEER_TRANSFER) for r in results]
    assert len(set(trf_quantities)) == 3  # All 3 scenarios must have distinct transfer quantities (0.0, 44.28, 148.3)
    assert trf_quantities[0] == 0.0        # Metformin (adequate cover)
    assert trf_quantities[1] > 0.0         # Amoxicillin (shortfall)
    assert trf_quantities[2] > trf_quantities[1] # Paracetamol (higher shortfall)
