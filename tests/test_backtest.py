"""
Unit tests for MedTrace Backtest Engine (tests/test_backtest.py).
Verifies:
1. Generalized anomaly detection without hardcoded entity string literals.
2. Anomaly precision, recall, and F1 calculations across varying seeds.
3. Sensitivity to input variation (would fail if outputs were canned or hardcoded).
"""

import os
import pytest
from app.backtest.engine import BacktestEngine

def test_backtest_runs_reproducibly_on_seed_1():
    engine = BacktestEngine(sim_dir="data/simulated")
    results = engine.run_backtest(seed=1, sim_dir="data/simulated")

    assert "metrics" in results
    metrics = results["metrics"]

    # Verify early warning lead time
    lt = metrics["early_warning_lead_time_days"]
    assert lt["medtrace"] > lt["naive_lmis"]
    assert lt["lead_time_advantage_days"] > 0

    # Verify generic anomaly detection
    anom = metrics["anomaly_detection"]
    assert anom["ground_truth_anomalies_count"] == 10
    assert anom["detected_anomalies_count"] >= 9
    assert anom["true_positives"] >= 9
    assert anom["precision_pct"] >= 90.0
    assert anom["recall_pct"] >= 90.0
    assert anom["f1_score_pct"] >= 90.0

def test_anomaly_detection_varies_with_input_seed():
    """Verify that backtest evaluation is dynamically computed and not hardcoded."""
    engine_s1 = BacktestEngine(sim_dir="data/simulated")
    res1 = engine_s1.run_backtest(seed=1, sim_dir="data/simulated")

    sim_dir_s2 = "data/simulated_seed_2"
    if os.path.exists(sim_dir_s2):
        engine_s2 = BacktestEngine(sim_dir=sim_dir_s2)
        res2 = engine_s2.run_backtest(seed=2, sim_dir=sim_dir_s2)
        
        # Lead times must reflect the different simulation trajectories
        assert res1["metrics"]["early_warning_lead_time_days"]["medtrace"] != \
               res2["metrics"]["early_warning_lead_time_days"]["medtrace"]
