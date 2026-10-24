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
