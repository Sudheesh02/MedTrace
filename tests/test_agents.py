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
    orchestrator = MedTraceOrchestrator(use_zetaris=False)
    pack = orchestrator.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")

    for rec in pack.recommendations:
        assert "shortfall_units" in rec.number_provenance
        assert rec.recommended_units == rec.number_provenance["shortfall_units"]

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
