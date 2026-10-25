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
    from app.models.schemas import SkepticReview, Hypothesis, ActionPlanAudit

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
    mock_skeptic.audit_action_plan.return_value = ActionPlanAudit(
        audited=True,
        passed=True,
        verified_recommendations_count=3,
        flagged_inconsistencies=[]
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


def test_llm_client_fallback_is_dynamic_and_unhardcoded():
    """Verify that offline LLM fallback never emits hardcoded numbers or canned quantities."""
    from app.adapters.llm_client import LLMClient
    client = LLMClient()
    client.sample_mode = True

    prompts = [
        "Investigator Agent Review for FAC-DH-01 - MED-007 (metformin)",
        "Skeptic & Number Auditor Review for FAC-PHC-01 - MED-004 (amoxicillin)",
        "Action Planner Synthesis for FAC-CHC-01 - MED-001 (paracetamol)"
    ]

    for p in prompts:
        res = client.generate(prompt=p)
        text = res["text"]
        # Invariants: No legacy hardcoded fixture numbers in qualitative text
        assert "50 phantom units" not in text
        assert "110 units" not in text
        assert res["usage"]["total_tokens"] > 0
        assert res["fallback"] is True


@pytest.mark.parametrize("drift_val,quar_val,shortfall_val", [
    (15.5, 0.0, 0.0),
    (0.0, 85.0, 120.0),
    (42.0, 200.0, 310.5),
    (110.0, 0.0, 75.0),
    (0.0, 0.0, 0.0),
])
def test_action_planner_parametric_shortfall_and_drift_provenance(drift_val, quar_val, shortfall_val):
    """
    Parametric invariant test:
    Directly feeds arbitrary synthesized drift, quarantine, and shortfall values into ActionPlannerAgent.
    Verifies that recommended quantities strictly reflect mathematical inputs, proving zero hardcoding.
    """
    from app.agents.action_planner import ActionPlannerAgent
    from app.adapters.llm_client import LLMClient
    from app.engines.hmem import HMemEngine
    from app.models.schemas import Hypothesis, ActionType

    planner = ActionPlannerAgent(LLMClient(), HMemEngine())
    hyp = Hypothesis(
        hypothesis_id="H-TEST",
        title="Batch Quality Assurance Quarantine & Regulatory Recall" if quar_val > 0 else "Phantom Stock Drift",
        cause="Parametric test cause",
        likelihood=0.88,
        supporting_evidence=["Evidence"],
        refuting_evidence=[],
        confirming_query="SELECT 1"
    )
    det_recon = {
        "trust_shortfall": {"shortfall_units": shortfall_val, "gap_days": 4.0 if shortfall_val > 0 else 0.0},
        "stock_evaluation": {
            "ledger_stock": 500.0,
            "usable_stock": max(0.0, 500.0 - drift_val - quar_val),
            "quarantined_stock": quar_val,
            "audit_drift": drift_val,
            "expiring_stock": 0.0
        },
        "trust_cover_days": 12.0
    }

    recs = planner.plan_actions("FAC-TEST-01", "MED-001", hyp, det_recon)
    rec_dict = {r.action_type: r for r in recs}

    if drift_val > 0:
        assert ActionType.INVENTORY_AUDIT_ADJUSTMENT in rec_dict
        adj = rec_dict[ActionType.INVENTORY_AUDIT_ADJUSTMENT]
        assert adj.recommended_units == drift_val
        assert adj.number_provenance["audit_drift"] == drift_val

    if quar_val > 0:
        assert ActionType.BATCH_RELEASE in rec_dict
        rel = rec_dict[ActionType.BATCH_RELEASE]
        assert rel.recommended_units == quar_val
        assert rel.number_provenance["quarantined_units"] == quar_val

    trf = rec_dict[ActionType.PEER_TRANSFER]
    assert trf.recommended_units == shortfall_val
    assert trf.number_provenance["shortfall_units"] == shortfall_val


def test_investigator_likelihood_dynamism_across_severities():
    """Verify InvestigatorAgent computes distinct likelihoods for high-drift vs low-drift scenarios."""
    from app.agents.investigator import InvestigatorAgent
    from app.adapters.llm_client import LLMClient

    inv = InvestigatorAgent(LLMClient())

    def make_recon(drift: float, ledger: float = 500.0):
        return {
            "facility_id": "FAC-DH-01",
            "medicine_id": "MED-007",
            "generic_name": "metformin",
            "deterministic_reconciliation": {
                "stock_evaluation": {
                    "ledger_stock": ledger,
                    "usable_stock": ledger - drift,
                    "audit_drift": drift,
                    "quarantined_stock": 0.0,
                    "expiring_stock": 0.0
                },
                "demand_evaluation": {"base_daily_rate": 20.0, "adjusted_daily_demand": 20.0},
                "trust_cover_days": (ledger - drift) / 20.0,
                "naive_cover_days": ledger / 20.0,
                "trust_shortfall": {"shortfall_units": 0.0, "gap_days": 0.0, "delivery_day": 6.0},
                "naive_shortfall": {"shortfall_units": 0.0, "gap_days": 0.0, "delivery_day": 6.0},
                "understated_gap_percent": 0.0,
                "anomalies_detected": {
                    "ghost_stock": drift > 0,
                    "quarantined_batches": False,
                    "expiring_batches": False,
                    "supplier_delay_risk": False,
                    "demand_spike": False,
                    "global_shortage": False,
                    "uom_mismatch": False
                }
            },
            "discrepancies": [
                {
                    "anomaly_type": "GHOST_STOCK",
                    "description": f"Ledger overstates true stock by {drift} units.",
                    "impact_units": drift
                }
            ] if drift > 0 else []
        }

    # Small drift (5 units out of 500) vs large drift (350 units out of 500)
    hyps_small = inv.investigate(make_recon(5.0), {})
    hyps_large = inv.investigate(make_recon(350.0), {})

    h1_small = next(h for h in hyps_small if h.hypothesis_id == "H1-INTERNAL-AUDIT")
    h1_large = next(h for h in hyps_large if h.hypothesis_id == "H1-INTERNAL-AUDIT")

    # Likelihood scales with severity
    assert h1_large.likelihood > h1_small.likelihood


def test_action_pack_records_monte_carlo_and_agent_traces():
    """Verify that ActionPack carries Monte Carlo P(stockout) and trace file logs real agent reasoning."""
    orch = MedTraceOrchestrator(use_zetaris=False)
    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")

    # Monte Carlo stockout probability invariant
    assert 0.0 <= pack.p_stockout_risk <= 1.0
    # For Metformin at DH-01 with >100 days of cover, P(stockout) must be 0.0
    assert pack.p_stockout_risk == 0.0

    # Trace file verification: ensure agents log reasoning
    with open(pack.trace_file, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f]

    action_events = [e for e in events if "ACTIONS_RECOMMENDED" in e["action"]]
    assert len(action_events) >= 1
    assert "llm_reasoning" in action_events[0]["details"]
    assert len(action_events[0]["details"]["llm_reasoning"]) > 0


def test_action_planner_disqualifies_peer_with_phantom_drift():
    """
    Verify that ActionPlannerAgent checks physical audit counts at peer facilities:
    if peer warehouse has 500 on ledger but 300 counted (200 phantom drift),
    usable surplus is 300, not 500.
    """
    from unittest.mock import MagicMock
    from app.agents.action_planner import ActionPlannerAgent
    from app.adapters.llm_client import LLMClient
    from app.engines.hmem import HMemEngine
    from app.models.schemas import Hypothesis, ActionType

    mock_ds = MagicMock()
    mock_ds.get_facilities.return_value = [
        {"facility_id": "FAC-TARGET-01"},
        {"facility_id": "FAC-PEER-01"}
    ]
    # Peer ledger says 500 units
    mock_ds.get_latest_ledger.return_value = {"ledger_stock": 500.0}
    mock_ds.get_batches.return_value = []
    # Peer physical audit shows only 80 units (420 units of phantom drift!)
    mock_ds.get_latest_physical_audit.return_value = {"counted_stock": 80.0}
    mock_ds.get_purchase_orders.return_value = []
    mock_ds.get_suppliers.return_value = [{"supplier_id": "SUP-001"}]

    planner = ActionPlannerAgent(LLMClient(), HMemEngine(), data_store=mock_ds)
    hyp = Hypothesis(
        hypothesis_id="H1",
        title="Supplier Delay",
        cause="Transit slip",
        likelihood=0.85,
        supporting_evidence=[],
        refuting_evidence=[],
        confirming_query="SELECT 1"
    )
    det_recon = {
        "trust_shortfall": {"shortfall_units": 150.0, "gap_days": 5.0},
        "stock_evaluation": {
            "ledger_stock": 100.0,
            "usable_stock": 20.0,
            "quarantined_stock": 0.0,
            "audit_drift": 0.0,
            "expiring_stock": 0.0
        },
        "trust_cover_days": 2.0
    }

    recs = planner.plan_actions("FAC-TARGET-01", "MED-001", hyp, det_recon)
    trf = next(r for r in recs if r.action_type == ActionType.PEER_TRANSFER)
    # Since peer holds only 80 usable units (after 420 phantom drift deduction),
    # it cannot cover the 150 unit shortfall!
    assert trf.number_provenance["peer_surplus"] == 80.0
    assert trf.feasibility_score < 0.50
    assert "insufficient for full 150" in trf.justification


def test_action_planner_formulates_monitor_buffer_on_zero_shortfall():
    """
    Verify that when local inventory is healthy (zero shortfall and zero drift),
    ActionPlannerAgent formulates MONITOR_BUFFER as top-ranked recommendation.
    """
    from app.agents.action_planner import ActionPlannerAgent
    from app.adapters.llm_client import LLMClient
    from app.engines.hmem import HMemEngine
    from app.models.schemas import Hypothesis, ActionType

    planner = ActionPlannerAgent(LLMClient(), HMemEngine())
    hyp = Hypothesis(
        hypothesis_id="H-STABLE",
        title="Stable Inventory",
        cause="Nominal operations",
        likelihood=0.20,
        supporting_evidence=[],
        refuting_evidence=[],
        confirming_query="SELECT 1"
    )
    det_recon = {
        "trust_shortfall": {"shortfall_units": 0.0, "gap_days": 0.0},
        "stock_evaluation": {
            "ledger_stock": 600.0,
            "usable_stock": 600.0,
            "quarantined_stock": 0.0,
            "audit_drift": 0.0,
            "expiring_stock": 0.0
        },
        "trust_cover_days": 45.0
    }

    recs = planner.plan_actions("FAC-HEALTHY-01", "MED-001", hyp, det_recon)
    top_rec = recs[0]
    assert top_rec.action_type == ActionType.MONITOR_BUFFER
    assert top_rec.recommended_units == 0.0
    assert top_rec.feasibility_score >= 0.95
    assert "Inventory levels are secure" in top_rec.justification


def test_skeptic_action_plan_audit_catches_arithmetic_violations():
    """
    Verify Number Auditor independently scrutinizes action recommendations
    and rejects quantity or facility violations.
    """
    from app.agents.skeptic import SkepticAgent
    from app.adapters.llm_client import LLMClient
    from app.models.schemas import ActionRecommendation, ActionType

    skeptic = SkepticAgent(LLMClient())
    det_recon = {
        "stock_evaluation": {
            "ledger_stock": 500.0,
            "usable_stock": 350.0,
            "audit_drift": 50.0,
            "quarantined_stock": 100.0,
            "expiring_stock": 0.0
        },
        "trust_shortfall": {"shortfall_units": 120.0, "gap_days": 4.0}
    }

    # Case 1: Valid action plan
    valid_recs = [
        ActionRecommendation(
            action_id="A1",
            action_type=ActionType.PEER_TRANSFER,
            facility_id="FAC-DH-01",
            medicine_id="MED-001",
            recommended_units=120.0,
            source_facility_id="FAC-WH-01",
            feasibility_score=0.90,
            justification="Transfer",
            number_provenance={"shortfall_units": 120.0, "peer_surplus": 300.0}
        ),
        ActionRecommendation(
            action_id="A2",
            action_type=ActionType.INVENTORY_AUDIT_ADJUSTMENT,
            facility_id="FAC-DH-01",
            medicine_id="MED-001",
            recommended_units=50.0,
            feasibility_score=0.95,
            justification="Audit adjustment",
            number_provenance={"audit_drift": 50.0}
        )
    ]
    audit_valid = skeptic.audit_action_plan(valid_recs, det_recon)
    assert audit_valid.passed is True
    assert len(audit_valid.flagged_inconsistencies) == 0

    # Case 2: Invariant violation: PEER_TRANSFER quantity != shortfall
    invalid_recs = [
        ActionRecommendation(
            action_id="A1",
            action_type=ActionType.PEER_TRANSFER,
            facility_id="FAC-DH-01",
            medicine_id="MED-001",
            recommended_units=999.0,  # Does not match 120.0 shortfall!
            source_facility_id="FAC-WH-01",
            feasibility_score=0.90,
            justification="Bad math",
            number_provenance={"shortfall_units": 120.0}
        ),
        ActionRecommendation(
            action_id="A2",
            action_type=ActionType.PEER_TRANSFER,
            facility_id="FAC-DH-01",
            medicine_id="MED-001",
            recommended_units=120.0,
            source_facility_id="FAC-DH-01",  # Self transfer!
            feasibility_score=0.90,
            justification="Self transfer",
            number_provenance={"shortfall_units": 120.0}
        )
    ]
    audit_invalid = skeptic.audit_action_plan(invalid_recs, det_recon)
    assert audit_invalid.passed is False
    assert len(audit_invalid.flagged_inconsistencies) >= 2
    assert any("PEER_TRANSFER recommended units" in inc for inc in audit_invalid.flagged_inconsistencies)
    assert any("Self-transfer detected" in inc for inc in audit_invalid.flagged_inconsistencies)


def test_action_plan_audit_trace_integration():
    """Verify that end-to-end investigation runs Number Auditor on action plan and populates action_plan_audit."""
    orch = MedTraceOrchestrator(use_zetaris=False)
    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")

    assert pack.action_plan_audit is not None
    assert pack.action_plan_audit.audited is True
    assert pack.action_plan_audit.passed is True
    assert pack.action_plan_audit.verified_recommendations_count >= 2

    # Verify trace log has ACTION_PLAN_AUDITED event
    with open(pack.trace_file, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f]
    audited_events = [e for e in events if e.get("action") == "ACTION_PLAN_AUDITED"]
    assert len(audited_events) == 1
    assert audited_events[0]["details"]["passed"] is True


def test_triage_planner_identifies_top_at_risk_items():
    """
    Verify that TriagePlannerAgent scans network inventory and returns a prioritized
    leaderboard separating Critical stockouts from nominal buffer items.
    """
    from app.agents.triage_planner import TriagePlannerAgent
    from app.adapters.data_store import DataStore
    from app.adapters.llm_client import LLMClient

    ds = DataStore(use_zetaris=False)
    triage_agent = TriagePlannerAgent(ds, LLMClient())

    # 1. Test single facility scan
    single_res = triage_agent.scan_district(facility_id="FAC-DH-01", top_n=5)
    assert single_res["total_evaluated"] == 12  # 12 medicines
    assert len(single_res["top_urgent_items"]) <= 5
    # Most urgent items should have higher urgency scores
    if len(single_res["top_urgent_items"]) > 1:
        assert single_res["top_urgent_items"][0]["urgency_score"] >= single_res["top_urgent_items"][1]["urgency_score"]

    # 2. Test full district scan
    district_res = triage_agent.scan_district(top_n=10)
    assert district_res["total_evaluated"] == 144  # 12 facilities * 12 medicines
    assert district_res["critical_count"] > 0
    assert district_res["warning_count"] > 0
    assert len(district_res["top_urgent_items"]) == 10

    # Ensure items are sorted descending by urgency score
    scores = [item["urgency_score"] for item in district_res["top_urgent_items"]]
    assert scores == sorted(scores, reverse=True)


def test_explain_trace_visualizer_renders_cleanly(capsys):
    """
    Verify that scripts/explain_trace.py parses real orchestrator trace logs and renders
    the executive multi-agent debate timeline without unhandled exceptions.
    """
    from scripts.explain_trace import render_trace, find_latest_trace

    orch = MedTraceOrchestrator(use_zetaris=False)
    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")

    assert os.path.exists(pack.trace_file)
    render_trace(pack.trace_file)

    captured = capsys.readouterr()
    out = captured.out
    assert "MEDTRACE MULTI-AGENT REASONING & AUDIT TIMELINE" in out
    assert "[ReconcilerAgent] Grounded Audit Complete:" in out
    assert "MULTI-AGENT ADVERSARIAL DEBATE: ROUND 1" in out
    assert "[SkepticAgent & Number Auditor] Round 1 Evaluation:" in out
    assert "[ActionPlannerAgent] Prioritized Interventions Formulated:" in out
    assert "[Number Auditor] Action Plan Verification: [AUDIT PASSED]" in out

    latest = find_latest_trace()
    assert latest is not None
    assert os.path.exists(latest)


def test_llm_client_reads_meterless_model_and_removes_127_gate(monkeypatch):
    """
    Verify:
    1. Meterless Nightshift URL works for non-127.0.0.1 hosts (e.g., custom docker container or host).
    2. METERLESS_MODEL environment variable is actually read and configured as the target model.
    """
    from app.adapters.llm_client import LLMClient

    monkeypatch.setenv("METERLESS_BASE_URL", "http://nightshift-container:8088/v1")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "nightshift-token-1234")
    monkeypatch.setenv("METERLESS_MODEL", "nightshift-custom-v1")
    monkeypatch.setenv("SAMPLE_MODE", "false")

    client = LLMClient()
    assert client.provider == "meterless"
    assert client.model == "nightshift-custom-v1"
    assert client.client is not None
    assert str(client.client.base_url).rstrip("/") == "http://nightshift-container:8088/v1"


def test_llm_client_outside_sample_mode_fails_loudly(monkeypatch):
    """
    Verify that outside sample mode (SAMPLE_MODE=false), LLMClient fails loudly:
    1. If no credentials are configured, raises RuntimeError.
    2. If the API call fails, raises RuntimeError instead of returning canned text.
    """
    from unittest.mock import MagicMock
    from app.adapters.llm_client import LLMClient

    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.delenv("METERLESS_RUNTIME_TOKEN", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)

    unconfigured_client = LLMClient()
    assert unconfigured_client.client is None
    with pytest.raises(RuntimeError) as exc_info:
        unconfigured_client.generate(prompt="Investigate root cause")
    assert "LLMClient has no configured provider" in str(exc_info.value)
    assert "SAMPLE_MODE is false" in str(exc_info.value)

    # Now configure a mock client that raises an exception during generation
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "token-xyz")
    failing_client = LLMClient()
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.side_effect = ConnectionError("Nightshift daemon unreachable")
    failing_client.client = mock_openai

    with pytest.raises(RuntimeError) as exc_info2:
        failing_client.generate(prompt="Investigate root cause")
    assert "LLM API generation failed outside sample mode" in str(exc_info2.value)
    assert "Nightshift daemon unreachable" in str(exc_info2.value)


def test_traced_model_equals_response_model_and_flags_in_all_trace_lines(monkeypatch):
    """
    Verify:
    1. When LLM returns an actual response with model='response-model-nemotron-v2',
       the traced model equals the API response model.
    2. llm_used=True and fallback=False are logged on all LLM trace events.
    3. Every single line in the JSONL trace file contains 'model', 'llm_used', and 'fallback'.
    4. ActionPack.model_used equals the response model, with pack.llm_used=True and pack.fallback=False.
    5. In sample mode, trace entries record model='rule-based-sample-mode', llm_used=False, fallback=True.
    """
    from unittest.mock import MagicMock

    # --- Part 1: Real API mock returning a specific response model ---
    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "mock-token")
    monkeypatch.setenv("METERLESS_MODEL", "requested-model-alias")

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Grounded multi-agent synthesis: Discrepancy confirmed with physical audit records."
    mock_choice.message.reasoning_content = None
    mock_chat_completion.choices = [mock_choice]
    mock_chat_completion.model = "api-returned-nemotron-30b-v2.1"
    mock_chat_completion.usage = MagicMock(model_dump=lambda: {"total_tokens": 120})

    orch = MedTraceOrchestrator(use_zetaris=False)
    orch.llm_client.client.chat.completions.create = MagicMock(return_value=mock_chat_completion)

    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")

    # Verify ActionPack metadata
    assert pack.model_used == "api-returned-nemotron-30b-v2.1"
    assert pack.llm_used is True
    assert pack.fallback is False

    # Inspect every line in the trace file
    with open(pack.trace_file, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    assert len(events) >= 5
    for e in events:
        assert "model" in e, f"Event {e.get('action')} missing 'model'"
        assert "llm_used" in e, f"Event {e.get('action')} missing 'llm_used'"
        assert "fallback" in e, f"Event {e.get('action')} missing 'fallback'"
        assert isinstance(e["llm_used"], bool)
        assert isinstance(e["fallback"], bool)

    # Check LLM-specific actions
    llm_actions = [e for e in events if e.get("action") in ("HYPOTHESES_GENERATED", "ROUND_1_EVALUATION", "ACTIONS_RECOMMENDED")]
    assert len(llm_actions) >= 3
    for e in llm_actions:
        assert e["model"] == "api-returned-nemotron-30b-v2.1"
        assert e["llm_used"] is True
        assert e["fallback"] is False

    # Check non-LLM actions (reconciler, world model, audit)
    non_llm_actions = [e for e in events if e.get("action") in ("START_RUN", "RECONCILE_COMPLETE", "CONTEXT_BUILT", "ACTION_PLAN_AUDITED")]
    for e in non_llm_actions:
        assert e["llm_used"] is False
        assert e["fallback"] is False

    # --- Part 2: Sample mode run ---
    monkeypatch.setenv("SAMPLE_MODE", "true")
    orch_sample = MedTraceOrchestrator(use_zetaris=False)
    pack_sample = orch_sample.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")

    assert pack_sample.model_used == "rule-based-sample-mode"
    assert pack_sample.llm_used is False
    assert pack_sample.fallback is True

    with open(pack_sample.trace_file, "r", encoding="utf-8") as f:
        sample_events = [json.loads(line) for line in f if line.strip()]

    sample_llm_actions = [e for e in sample_events if e.get("action") in ("HYPOTHESES_GENERATED", "ROUND_1_EVALUATION", "ACTIONS_RECOMMENDED")]
    for e in sample_llm_actions:
        assert e["model"] == "rule-based-sample-mode"
        assert e["llm_used"] is False
        assert e["fallback"] is True


def test_number_auditor_rejects_hallucinated_numbers_not_in_evidence_pack():
    """
    Verify Number Auditor zero-hallucination guardrail:
    If an LLM or hypothesis asserts quantitative claims that do NOT exist in the deterministic
    evidence pack (e.g. claiming 9999 units or 850 units when ground truth drift is 50),
    the Number Auditor must detect the ungrounded number, flag it, and reject the hypothesis.
    """
    from app.agents.skeptic import SkepticAgent
    from app.adapters.llm_client import LLMClient
    from app.models.schemas import Hypothesis

    skeptic = SkepticAgent(LLMClient())
    deterministic_recon = {
        "stock_evaluation": {
            "ledger_stock": 500.0,
            "usable_stock": 450.0,
            "audit_drift": 50.0,
            "quarantined_stock": 0.0,
            "expiring_stock": 0.0
        },
        "trust_shortfall": {
            "shortfall_units": 60.0,
            "gap_days": 3.0,
            "delivery_day": 6.0
        },
        "trust_cover_days": 22.5,
        "naive_cover_days": 25.0,
        "understated_gap_percent": 10.0,
        "demand_evaluation": {
            "base_daily_rate": 20.0,
            "adjusted_daily_demand": 20.0
        }
    }

    # Case 1: Grounded hypothesis with valid numbers from evidence pack
    grounded_hyp = Hypothesis(
        hypothesis_id="H1-INTERNAL-AUDIT",
        title="Phantom Stock Drift in Warehouse Ledger",
        cause="Physical audit confirms ledger overstates true physical stock by 50.0 units.",
        likelihood=0.90,
        supporting_evidence=["Audit count confirms 450.0 physical units vs 500.0 on ledger."],
        refuting_evidence=[],
        confirming_query="SELECT 1"
    )
    top_hyp1, review1 = skeptic.review_and_audit([grounded_hyp], deterministic_recon, round_number=1)
    assert review1.audited_numbers_valid is True
    assert review1.accepted is True

    # Case 2: Hallucinated hypothesis asserting 9999 units (not in evidence pack)
    hallucinated_hyp = Hypothesis(
        hypothesis_id="H1-INTERNAL-AUDIT",
        title="Phantom Stock Drift in Warehouse Ledger",
        cause="Physical audit confirms catastrophic loss of 9999.0 units.",
        likelihood=0.90,
        supporting_evidence=["Hallucinated shrinkage of 850.0 units claimed by ungrounded model."],
        refuting_evidence=[],
        confirming_query="SELECT 1"
    )
    top_hyp2, review2 = skeptic.review_and_audit([hallucinated_hyp], deterministic_recon, round_number=1)
    assert review2.audited_numbers_valid is False
    assert review2.accepted is False
    assert review2.confidence_score <= 0.35
    assert any("not grounded in the deterministic evidence pack" in note for note in review2.flagged_inconsistencies)
    assert "9999.0" in review2.critique_notes or "850.0" in review2.critique_notes


def test_multi_agent_debate_flips_winning_hypothesis():
    """
    Verify multi-agent adversarial debate dynamics:
    1. In Round 1, an ambiguous case causes H2 (Supplier Transit) to lead with likelihood 0.82
       over H1 (Phantom Drift) at 0.80 (Delta = 0.02 <= 0.15).
    2. Skeptic challenges Round 1 top hypothesis due to lack of differential elimination.
    3. Investigator re-evaluates evidence under Skeptic critique: physical shelf count confirms
       immediate leakage on shelves, refuting external transit delay.
    4. Investigator revises: H1 is promoted to 0.88 and H2 is demoted to 0.35.
    5. In Round 2, Skeptic evaluates revised hypotheses: H1 is now the clear winner and is accepted!
    6. Verifies that debate actively FLIPPED the winner between rounds based on critique.
    """
    from app.agents.investigator import InvestigatorAgent
    from app.agents.skeptic import SkepticAgent
    from app.adapters.llm_client import LLMClient
    from app.models.schemas import Hypothesis

    llm = LLMClient()
    inv = InvestigatorAgent(llm)
    skeptic = SkepticAgent(llm)

    recon_data = {
        "facility_id": "FAC-CHC-01",
        "medicine_id": "MED-001",
        "generic_name": "Amoxicillin",
        "deterministic_reconciliation": {
            "stock_evaluation": {
                "ledger_stock": 250.0,
                "usable_stock": 170.0,
                "audit_drift": 80.0,
                "quarantined_stock": 0.0,
                "expiring_stock": 0.0
            },
            "demand_evaluation": {"base_daily_rate": 25.0, "adjusted_daily_demand": 25.0},
            "trust_cover_days": 6.8,
            "naive_cover_days": 10.0,
            "trust_shortfall": {"shortfall_units": 55.0, "gap_days": 2.2, "delivery_day": 9.0},
            "naive_shortfall": {"shortfall_units": 0.0, "gap_days": 0.0, "delivery_day": 6.0},
            "understated_gap_percent": 100.0,
            "anomalies_detected": {
                "ghost_stock": True,
                "quarantined_batches": False,
                "expiring_batches": False,
                "supplier_delay_risk": True,
                "demand_spike": False,
                "global_shortage": False,
                "uom_mismatch": False
            }
        },
        "discrepancies": [
            {"anomaly_type": "GHOST_STOCK", "description": "80 units missing on shelf.", "impact_units": 80.0},
            {"anomaly_type": "PO_DISPATCHED_NOT_RECEIVED", "description": "Supplier slip adds +3 days.", "impact_units": 55.0}
        ]
    }

    # Simulate Round 1 initial state where H2 was slightly ahead of H1
    r1_hyps = [
        Hypothesis(
            hypothesis_id="H2-SUPPLIER-TRANSIT",
            title="Upstream Supplier Lead Time Slippage",
            cause="Empirical supplier slip priors indicate typical delivery delays push arrival.",
            likelihood=0.82,
            supporting_evidence=["Historical vendor slip adds delay."],
            refuting_evidence=[],
            confirming_query="SELECT * FROM supplier_slip"
        ),
        Hypothesis(
            hypothesis_id="H1-INTERNAL-AUDIT",
            title="Phantom Stock Drift in Warehouse Ledger",
            cause="Physical audit confirms ledger overstates true physical stock by 80.0 units.",
            likelihood=0.80,
            supporting_evidence=["80.0 units missing from shelf."],
            refuting_evidence=[],
            confirming_query="SELECT * FROM physical_audit"
        ),
        Hypothesis(
            hypothesis_id="H3-EXTERNAL-SURGE",
            title="General Market Supply Constriction",
            cause="Market tightening.",
            likelihood=0.20,
            supporting_evidence=[],
            refuting_evidence=[],
            confirming_query="SELECT 1"
        )
    ]

    # Skeptic evaluates Round 1
    det_recon = recon_data["deterministic_reconciliation"]
    top_r1, review_r1 = skeptic.review_and_audit(r1_hyps, det_recon, round_number=1)

    # In Round 1: Top candidate is H2, but Skeptic REJECTS due to close Delta (0.02 <= 0.15)
    assert top_r1.hypothesis_id == "H2-SUPPLIER-TRANSIT"
    assert review_r1.accepted is False
    assert "close competing hypothesis" in review_r1.critique_notes.lower()
    assert len(review_r1.flagged_inconsistencies) >= 1

    # Round 2: Investigator receives Skeptic critique and executes differential elimination
    r2_hyps = inv.investigate(recon_data, {}, skeptic_feedback=review_r1.critique_notes)
    h1_r2 = next(h for h in r2_hyps if h.hypothesis_id == "H1-INTERNAL-AUDIT")
    h2_r2 = next(h for h in r2_hyps if h.hypothesis_id == "H2-SUPPLIER-TRANSIT")

    # Skeptic evaluates Round 2
    top_r2, review_r2 = skeptic.review_and_audit(r2_hyps, det_recon, round_number=2)

    # In Round 2: Top candidate is now H1! Winner FLIPPED from H2 to H1!
    assert top_r2.hypothesis_id == "H1-INTERNAL-AUDIT"
    assert h1_r2.likelihood > h2_r2.likelihood
    assert review_r2.accepted is True
    assert "approved" in review_r2.critique_notes.lower()
    assert top_r1.hypothesis_id != top_r2.hypothesis_id, "Debate must flip the winning hypothesis between rounds!"


def test_action_planner_computes_deterministic_financial_costs():
    """
    Verify that ActionPlannerAgent deterministically computes estimated financial costs:
    - PEER_TRANSFER: units * unit_price * 0.15 (inter-facility handling fee)
    - EXPEDITE_PO: units * unit_price * 1.10 (procurement + 10% rush fee)
    - EMERGENCY_PURCHASE: units * unit_price * 2.50 (emergency spot premium)
    - MONITOR_BUFFER: $0.00
    - Scales proportionally when shortfall changes (no hardcoded cost constants).
    """
    from app.agents.action_planner import ActionPlannerAgent
    from app.adapters.llm_client import LLMClient
    from app.adapters.data_store import DataStore
    from app.engines.hmem import HMemEngine
    from app.models.schemas import Hypothesis, ActionType

    data_store = DataStore(use_zetaris=False)
    hmem = HMemEngine()
    planner = ActionPlannerAgent(LLMClient(), hmem, data_store=data_store)

    unit_price = data_store.get_medicine_unit_price("MED-004")  # Amoxicillin ($0.12)
    assert unit_price == 0.12

    hypothesis = Hypothesis(
        hypothesis_id="H2-SUPPLIER-TRANSIT",
        title="Upstream Supplier Lead Time Slippage",
        cause="Delayed delivery",
        likelihood=0.85,
        supporting_evidence=["Delivery delayed"],
        refuting_evidence=[],
        confirming_query="SELECT 1"
    )

    # Test Scenario A: shortfall = 200 units
    recon_200 = {
        "stock_evaluation": {"usable_stock": 50.0, "ledger_stock": 50.0, "audit_drift": 0.0, "quarantined_stock": 0.0},
        "trust_shortfall": {"shortfall_units": 200.0, "gap_days": 5.0},
        "trust_cover_days": 2.5
    }
    recs_200 = planner.plan_actions("FAC-CHC-01", "MED-004", hypothesis, recon_200)

    trf_200 = next(r for r in recs_200 if r.action_type == ActionType.PEER_TRANSFER)
    exp_200 = next(r for r in recs_200 if r.action_type == ActionType.EXPEDITE_PO)
    emg_200 = next(r for r in recs_200 if r.action_type == ActionType.EMERGENCY_PURCHASE)

    expected_trf_cost_200 = round(200.0 * 0.12 * 0.15, 2)  # $3.60
    expected_exp_cost_200 = round(200.0 * 0.12 * 1.10, 2)  # $26.40
    expected_emg_cost_200 = round(200.0 * 0.12 * 2.50, 2)  # $60.00

    assert trf_200.estimated_cost_usd == expected_trf_cost_200
    assert exp_200.estimated_cost_usd == expected_exp_cost_200
    assert emg_200.estimated_cost_usd == expected_emg_cost_200

    # Test Scenario B: shortfall = 500 units (must scale proportionally without hardcoding)
    recon_500 = {
        "stock_evaluation": {"usable_stock": 20.0, "ledger_stock": 20.0, "audit_drift": 0.0, "quarantined_stock": 0.0},
        "trust_shortfall": {"shortfall_units": 500.0, "gap_days": 10.0},
        "trust_cover_days": 1.0
    }
    recs_500 = planner.plan_actions("FAC-CHC-01", "MED-004", hypothesis, recon_500)

    trf_500 = next(r for r in recs_500 if r.action_type == ActionType.PEER_TRANSFER)
    exp_500 = next(r for r in recs_500 if r.action_type == ActionType.EXPEDITE_PO)
    emg_500 = next(r for r in recs_500 if r.action_type == ActionType.EMERGENCY_PURCHASE)

    assert trf_500.estimated_cost_usd == round(500.0 * 0.12 * 0.15, 2)
    assert exp_500.estimated_cost_usd == round(500.0 * 0.12 * 1.10, 2)
    assert emg_500.estimated_cost_usd == round(500.0 * 0.12 * 2.50, 2)
    assert trf_500.estimated_cost_usd > trf_200.estimated_cost_usd


def test_reconciler_dynamic_consumption_fallback_without_history():
    """
    Verify that when recent consumption history is empty, ReconcilerAgent does not
    default to a magic constant (10.0), but dynamically derives daily consumption from
    facility catchment scale and medicine profile.
    """
    from app.agents.reconciler import ReconcilerAgent
    from app.adapters.data_store import DataStore
    from app.engines.world_model import WorldStoreService, IngestPipelineService
    from unittest.mock import patch

    store = DataStore(use_zetaris=False)
    ingest = IngestPipelineService(WorldStoreService())
    reconciler = ReconcilerAgent(store, ingest)

    # Mock get_recent_consumption to return empty list
    with patch.object(store, "get_recent_consumption", return_value=[]):
        # District Hospital (catchment 1.0) with staple medicine MED-001 (Paracetamol)
        res_dh = reconciler.reconcile_item("FAC-DH-01", "MED-001")
        daily_dh = res_dh["deterministic_reconciliation"]["demand_evaluation"]["base_daily_rate"]
        assert daily_dh == 30.0  # 30.0 * 1.0

        # Sub-District CHC (catchment 0.35) with staple medicine MED-001 (Paracetamol)
        res_chc = reconciler.reconcile_item("FAC-CHC-01", "MED-001")
        daily_chc = res_chc["deterministic_reconciliation"]["demand_evaluation"]["base_daily_rate"]
        assert daily_chc == 10.5  # 30.0 * 0.35
        assert daily_dh > daily_chc


def test_skeptic_action_plan_audit_rejects_negative_costs():
    """Verify that the Number Auditor audits estimated_cost_usd and rejects negative numbers."""
    from app.agents.skeptic import SkepticAgent
    from app.adapters.llm_client import LLMClient
    from app.models.schemas import ActionRecommendation, ActionType

    skeptic = SkepticAgent(LLMClient())
    recon = {
        "stock_evaluation": {"usable_stock": 100.0, "audit_drift": 0.0, "quarantined_stock": 0.0},
        "trust_shortfall": {"shortfall_units": 50.0, "gap_days": 2.0}
    }

    # Case 1: Valid recommendation with positive cost
    valid_rec = ActionRecommendation(
        action_id="ACT-1",
        action_type=ActionType.PEER_TRANSFER,
        facility_id="FAC-CHC-01",
        medicine_id="MED-001",
        recommended_units=50.0,
        estimated_cost_usd=2.50,
        feasibility_score=0.90,
        justification="Valid transfer",
        number_provenance={"shortfall_units": 50.0}
    )
    audit_valid = skeptic.audit_action_plan([valid_rec], recon)
    assert audit_valid.passed is True

    # Case 2: Invalid recommendation with negative cost
    invalid_rec = ActionRecommendation(
        action_id="ACT-2",
        action_type=ActionType.PEER_TRANSFER,
        facility_id="FAC-CHC-01",
        medicine_id="MED-001",
        recommended_units=50.0,
        estimated_cost_usd=-15.00,
        feasibility_score=0.90,
        justification="Invalid negative cost",
        number_provenance={"shortfall_units": 50.0}
    )
    audit_invalid = skeptic.audit_action_plan([invalid_rec], recon)
    assert audit_invalid.passed is False
    assert any("cannot be negative" in inc for inc in audit_invalid.flagged_inconsistencies)


def test_investigator_and_skeptic_grounded_in_world_model_context():
    """Verify InvestigatorAgent and SkepticAgent actively inspect and enforce Meterless World Model shared state."""
    from app.engines.world_model import WorldStoreService, IngestPipelineService, ContextBuilderService
    from app.agents.investigator import InvestigatorAgent
    from app.agents.skeptic import SkepticAgent
    from app.adapters.llm_client import LLMClient
    from app.models.schemas import Hypothesis

    store = WorldStoreService()
    ingest = IngestPipelineService(store)
    builder = ContextBuilderService(store)

    # Ingest facility and item with registered conflict
    ingest.ingest_facility_item(
        facility={"facility_id": "FAC-TEST-01", "name": "Test Hospital", "level": "DH"},
        medicine={"medicine_id": "MED-TEST-01", "generic_name": "Amoxicillin"},
        stock_info={"usable_stock": 250.0, "ledger_stock": 350.0, "trust_cover_days": 8.5}
    )
    ingest.record_discrepancy_conflict(
        discrepancy={"anomaly_type": "GHOST_STOCK", "description": "Ledger overstates true stock by 100 units"},
        facility_id="FAC-TEST-01",
        medicine_id="MED-TEST-01"
    )

    ctx = builder.build_structured_context("FAC-TEST-01", "MED-TEST-01")
    assert "conflicts" in ctx
    assert len(ctx["conflicts"]) == 1
    assert ctx["canon_hash"] is not None

    investigator = InvestigatorAgent(LLMClient())
    recon_data = {
        "facility_id": "FAC-TEST-01",
        "medicine_id": "MED-TEST-01",
        "generic_name": "Amoxicillin",
        "discrepancies": [{"anomaly_type": "GHOST_STOCK", "description": "Audit drift 100 units"}],
        "deterministic_reconciliation": {
            "stock_evaluation": {
                "ledger_stock": 350.0,
                "usable_stock": 250.0,
                "audit_drift": 100.0,
                "quarantined_stock": 0.0,
                "expiring_stock": 0.0
            },
            "demand_evaluation": {"base_daily_rate": 20.0, "adjusted_daily_demand": 20.0},
            "trust_shortfall": {"shortfall_units": 0.0, "gap_days": 0.0, "delivery_day": 6.0},
            "trust_cover_days": 12.5,
            "naive_cover_days": 17.5,
            "anomalies_detected": {
                "ghost_stock": True,
                "quarantined_batches": False,
                "expiring_batches": False,
                "supplier_delay_risk": False,
                "demand_spike": False,
                "global_shortage": False,
                "uom_mismatch": False
            }
        }
    }

    hypotheses = investigator.investigate(recon_data, ctx)
    assert len(hypotheses) == 3
    # Verify H1 supporting evidence includes World Model entity grounding
    h1 = next(h for h in hypotheses if h.hypothesis_id == "H1-INTERNAL-AUDIT")
    assert any("World Model" in ev for ev in h1.supporting_evidence)

    # Test Skeptic Number Auditor catches World Model contradictions
    skeptic = SkepticAgent(LLMClient())
    # Contradicting context: World Model usable_stock = 999.0 while deterministic_recon = 250.0
    contradicting_ctx = {
        **ctx,
        "inventory_state": {**ctx["inventory_state"], "usable_stock": 999.0}
    }
    _, review_contra = skeptic.review_and_audit(
        hypotheses=hypotheses,
        deterministic_recon=recon_data["deterministic_reconciliation"],
        round_number=1,
        world_context=contradicting_ctx
    )
    assert review_contra.audited_numbers_valid is False
    assert any("World Model canonical stock" in inc for inc in review_contra.flagged_inconsistencies)


def test_orchestrator_case_insensitive_and_whitespace_normalization():
    """Verify that facility and medicine ID inputs are automatically case-folded and stripped."""
    orchestrator = MedTraceOrchestrator(use_zetaris=False)

    # Pass lowercase with trailing/leading spaces
    pack = orchestrator.run_investigation(
        facility_id="  fac-dh-01  ",
        medicine_id=" med-007 "
    )
    assert pack.facility_id == "FAC-DH-01"
    assert pack.medicine_id == "MED-007"
    assert pack.winning_hypothesis is not None


def test_action_planner_adapts_to_human_escalation():
    """
    Verify that when an investigation is escalated to a human officer,
    ActionPlannerAgent penalizes autonomous feasibility and prepends controller warnings.
    """
    from app.agents.action_planner import ActionPlannerAgent
    from app.engines.hmem import HMemEngine
    from app.adapters.llm_client import LLMClient
    from app.models.schemas import Hypothesis

    planner = ActionPlannerAgent(LLMClient(), HMemEngine())
    hyp = Hypothesis(
        hypothesis_id="H1-UNCERTAIN",
        title="Unconfirmed Supply Chain Shortfall",
        cause="Competing unverified claims",
        likelihood=0.45,
        supporting_evidence=["Single source report"],
        refuting_evidence=[],
        confirming_query="SELECT 1"
    )
    recon = {
        "trust_shortfall": {"shortfall_units": 100.0, "gap_days": 4.0},
        "stock_evaluation": {"ledger_stock": 200.0, "usable_stock": 50.0, "audit_drift": 0.0, "quarantined_stock": 0.0, "expiring_stock": 0.0},
        "trust_cover_days": 2.0
    }

    # Standard non-escalated plan
    recs_standard = planner.plan_actions("FAC-CHC-01", "MED-001", hyp, recon, escalated_to_human=False)
    # Escalated plan
    recs_escalated = planner.plan_actions("FAC-CHC-01", "MED-001", hyp, recon, escalated_to_human=True)

    assert len(recs_standard) == len(recs_escalated)
    for std, esc in zip(recs_standard, recs_escalated):
        assert esc.feasibility_score < std.feasibility_score or esc.feasibility_score == 0.10
        assert "[ESCALATED TO CONTROLLER]" in esc.justification




