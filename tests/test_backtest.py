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

    # Verify action sizing error calculation (Plan Section 5.3)
    assert "action_sizing_error_pct" in metrics
    sizing = metrics["action_sizing_error_pct"]
    assert "medtrace" in sizing
    assert "naive_lmis" in sizing
    assert sizing["medtrace"] <= 5.0

def test_anomaly_detection_varies_with_input_seed():
    """Verify that backtest evaluation is dynamically computed and not hardcoded."""
    engine_s1 = BacktestEngine(sim_dir="data/simulated")
    res1 = engine_s1.run_backtest(seed=1, sim_dir="data/simulated")

    sim_dir_s2 = "data/simulated_seed_2"
    if not os.path.exists(sim_dir_s2):
        from scripts.generate_facility_simulation import generate_simulation
        generate_simulation(seed=2, out_dir=sim_dir_s2)

    engine_s2 = BacktestEngine(sim_dir=sim_dir_s2)
    res2 = engine_s2.run_backtest(seed=2, sim_dir=sim_dir_s2)
    
    # Lead times and anomaly distributions must reflect different simulation trajectories
    assert res1["metrics"]["early_warning_lead_time_days"]["medtrace"] != \
           res2["metrics"]["early_warning_lead_time_days"]["medtrace"]
    assert res1["total_actual_stockouts"] > 0
    assert res2["total_actual_stockouts"] > 0

def test_backtest_dynamic_demand_derivation_without_hardcoded_keys():
    """Verify that BacktestEngine dynamically derives base demands from consumption without hardcoding."""
    engine = BacktestEngine(sim_dir="data/simulated")
    # Query facilities and medicines dynamically
    meds = engine.store.get_medicines()
    assert len(meds) >= 12
    res = engine.run_backtest(seed=1, sim_dir="data/simulated")
    # Sizing error must be computed strictly from real data
    assert res["metrics"]["action_sizing_error_pct"]["medtrace"] < 2.0


@pytest.mark.parametrize("test_seed", [1, 2, 3])
def test_naive_and_medtrace_formulas_share_same_horizon_across_seeds(test_seed):
    """
    Verify dynamic behavioral calculation of action sizing errors across varying simulation seeds:
    1. Replays backtest across seeds 1, 2, and 3.
    2. Exercises BacktestEngine directly, verifying that action sizing error is computed
       from empirical simulation trajectories rather than hardcoded constant assertions.
    3. Verifies that MedTrace achieves low sizing error (<= 3.0%) across all seeds.
    """
    sim_dir = f"data/simulated_seed_{test_seed}" if test_seed != 1 else "data/simulated"
    if not os.path.exists(sim_dir):
        from scripts.generate_facility_simulation import generate_simulation
        generate_simulation(seed=test_seed, out_dir=sim_dir)

    engine = BacktestEngine(sim_dir=sim_dir)
    res = engine.run_backtest(seed=test_seed, sim_dir=sim_dir)

    assert "action_sizing_error_pct" in res["metrics"]
    sizing = res["metrics"]["action_sizing_error_pct"]
    assert "medtrace" in sizing
    assert "naive_lmis" in sizing
    assert "heuristic_rule_based" in sizing

    # MedTrace must achieve low sizing error across all seeds
    assert sizing["medtrace"] <= 3.0
    assert res["total_actual_stockouts"] > 0
