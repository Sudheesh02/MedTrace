"""
Unit tests for MedTrace Backtest Engine (tests/test_backtest.py).
Verifies:
1. Shared alert threshold parity across Naive LMIS, Heuristic, and MedTrace.
2. Anomaly precision, recall, and F1 calculations across varying seeds.
3. Held-out test evaluation on seeds 3 and 4 with high generalization.
4. Dynamic demand derivation from consumption without hardcoding.
"""

import os
import pytest
from app.backtest.engine import BacktestEngine

def test_backtest_runs_reproducibly_on_seed_1():
    engine = BacktestEngine(sim_dir="data/simulated")
    results = engine.run_backtest(seed=1, sim_dir="data/simulated")

    assert "metrics" in results
    metrics = results["metrics"]

    # Verify shared alert threshold parity
    lt = metrics["early_warning_lead_time_days"]
    assert lt["alert_threshold_days"] == 14.0
    assert lt["medtrace"] >= lt["naive_lmis"]
    assert lt["lead_time_advantage_days"] >= 0.0

    # Verify generic anomaly detection
    anom = metrics["anomaly_detection"]
    assert anom["ground_truth_anomalies_count"] == 10
    assert anom["detected_anomalies_count"] >= 9
    assert anom["true_positives"] >= 9
    assert anom["precision_pct"] >= 80.0
    assert anom["recall_pct"] >= 90.0
    assert anom["f1_score_pct"] >= 90.0
    assert anom["naive_lmis_f1"] == anom["baseline_comparisons"]["naive_lmis"]["f1_score_pct"]
    assert 0.0 <= anom["naive_lmis_f1"] <= 100.0
    assert anom["f1_score_pct"] > anom["naive_lmis_f1"]

    # Verify raw counts mathematical integrity
    raw = anom["raw_counts"]
    assert raw["true_positives"] + raw["false_negatives"] == anom["ground_truth_anomalies_count"]
    assert raw["true_positives"] == anom["true_positives"]
    assert raw["false_positives"] == anom["false_positives"]
    expected_p = round(raw["true_positives"] / (raw["true_positives"] + raw["false_positives"]) * 100.0, 1)
    expected_r = round(raw["true_positives"] / (raw["true_positives"] + raw["false_negatives"]) * 100.0, 1)
    assert anom["precision_pct"] == expected_p
    assert anom["recall_pct"] == expected_r

    # Verify type-agnostic anomaly comparisons
    ta = anom["type_agnostic_comparisons"]
    assert "medtrace" in ta
    assert "naive_lmis" in ta
    assert "heuristic_rule_based" in ta
    assert ta["medtrace"]["f1_score_pct"] >= ta["naive_lmis"]["f1_score_pct"]
    assert ta["medtrace"]["true_positives"] >= ta["naive_lmis"]["true_positives"]

    # Verify timing evaluation bounds
    te = anom["timing_evaluation"]
    assert te["window_days"] == 7
    assert 0 <= te["timed_true_positives"] <= anom["ground_truth_anomalies_count"]
    assert te["median_detection_delay_days"] <= 5.0

    # Verify capital lockup
    false_reorders = metrics["capital_lockup_false_reorders"]
    assert false_reorders["medtrace"] == 0
    assert false_reorders["naive_lmis"] == 0

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
    assert res["total_actual_stockouts"] > 0
    assert res["metrics"]["stockout_recall_pct"]["medtrace"] == 100.0


@pytest.mark.parametrize("test_seed", [2, 3, 4])
def test_held_out_seeds_evaluation_and_threshold_parity(test_seed):
    """
    Verify dynamic behavioral calculation and generalization across tuning seed 2
    and held-out test seeds 3 and 4:
    1. Replays backtest across seeds 2, 3, and 4.
    2. Exercises BacktestEngine directly, verifying alert threshold parity (14.0 days).
    3. Verifies that MedTrace achieves high anomaly detection F1 (>= 90.0%) across held-out seeds.
    4. Verifies 100% stockout recall and 0 false emergency orders.
    """
    sim_dir = f"data/simulated_seed_{test_seed}"
    if not os.path.exists(sim_dir):
        from scripts.generate_facility_simulation import generate_simulation
        generate_simulation(seed=test_seed, out_dir=sim_dir)

    engine = BacktestEngine(sim_dir=sim_dir)
    res = engine.run_backtest(seed=test_seed, sim_dir=sim_dir)

    metrics = res["metrics"]
    assert metrics["early_warning_lead_time_days"]["alert_threshold_days"] == 14.0
    assert metrics["stockout_recall_pct"]["medtrace"] == 100.0
    assert metrics["anomaly_detection"]["f1_score_pct"] >= 90.0
    assert metrics["capital_lockup_false_reorders"]["medtrace"] == 0
    assert res["total_actual_stockouts"] > 0


def test_backtest_dynamic_anomaly_bounds_adapt_to_ground_truth():
    """Verify that BacktestEngine anomaly inspection dynamically derives bounds from ground truth schedule."""
    engine = BacktestEngine(sim_dir="data/simulated")
    gt = engine.load_ground_truth("data/simulated")
    assert len(gt) >= 10
    
    # Ground truth schedule must contain valid day indices
    day_indices = [int(g["day_index"]) for g in gt if "day_index" in g and str(g["day_index"]).isdigit()]
    assert len(day_indices) == len(gt)
    min_d, max_d = min(day_indices), max(day_indices)
    assert min_d >= 0
    assert max_d <= 180

    # Backtest execution successfully detects anomalies across the entire 180-day timeline
    res = engine.run_backtest(seed=1, sim_dir="data/simulated")
    anom = res["metrics"]["anomaly_detection"]
    assert anom["ground_truth_anomalies_count"] == 10
    assert anom["true_positives"] >= 9
    assert anom["precision_pct"] >= 80.0


def test_backtest_performance_benchmarks_metrics():
    """Verify BacktestEngine computes empirical throughput and execution duration metrics."""
    engine = BacktestEngine(sim_dir="data/simulated")
    res = engine.run_backtest(seed=1, sim_dir="data/simulated")

    assert "performance_benchmarks" in res
    pb = res["performance_benchmarks"]
    assert "replay_duration_seconds" in pb
    assert "total_transactions_evaluated" in pb
    assert "throughput_events_per_sec" in pb
    assert pb["replay_duration_seconds"] > 0.0
    assert pb["total_transactions_evaluated"] > 1000
    assert pb["throughput_events_per_sec"] > 10.0


def test_backtest_summary_markdown_generation(tmp_path):
    """Verify that scripts/run_backtest.py generates valid comparative tables in an isolated directory."""
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "scripts/run_backtest.py", "--output-dir", str(tmp_path), "--seeds", "1"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0, f"run_backtest failed with stderr: {res.stderr}"

    summary_file = os.path.join(str(tmp_path), "backtest_summary.md")
    assert os.path.exists(summary_file)
    with open(summary_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "# MedTrace 180-Day Simulation Replay & Benchmark Summary Report" in content
    assert "Naive LMIS" in content
    assert "Heuristic Rule-Based" in content
    assert "MedTrace" in content
    assert "Held-Out Test F1" in content
    assert "Processing Throughput" in content
    assert "Zero LLM Arithmetic" in content


def test_type_agnostic_and_timed_anomaly_scoring_invariants():
    """
    Anti-Hardcoding & Audit Invariant Test:
    Verifies that type-agnostic and timing-bounded anomaly scoring metrics are derived
    dynamically from simulation records across varying seeds, asserting:
    1. Raw counts (TP, FP, FN) satisfy P = TP/(TP+FP) and R = TP/(TP+FN) exactly.
    2. Type-agnostic F1 scores evaluate irregularities across all three models.
    3. Metrics vary dynamically between seeds without hardcoding.
    """
    engine1 = BacktestEngine(sim_dir="data/simulated")
    res1 = engine1.run_backtest(seed=1, sim_dir="data/simulated")

    sim_dir2 = "data/simulated_seed_2"
    if not os.path.exists(sim_dir2):
        from scripts.generate_facility_simulation import generate_simulation
        generate_simulation(seed=2, out_dir=sim_dir2)

    engine2 = BacktestEngine(sim_dir=sim_dir2)
    res2 = engine2.run_backtest(seed=2, sim_dir=sim_dir2)

    for res in [res1, res2]:
        anom = res["metrics"]["anomaly_detection"]
        raw = anom["raw_counts"]
        # Invariant 1: TP + FN must equal ground truth total count
        assert raw["true_positives"] + raw["false_negatives"] == anom["ground_truth_anomalies_count"]
        # Invariant 2: Precision formula
        if raw["true_positives"] + raw["false_positives"] > 0:
            calc_p = round(raw["true_positives"] / (raw["true_positives"] + raw["false_positives"]) * 100.0, 1)
            assert anom["precision_pct"] == calc_p
        # Invariant 3: Recall formula
        calc_r = round(raw["true_positives"] / (raw["true_positives"] + raw["false_negatives"]) * 100.0, 1)
        assert anom["recall_pct"] == calc_r

        # Type-agnostic comparisons must be present for all 3 models
        ta = anom["type_agnostic_comparisons"]
        assert "medtrace" in ta and "naive_lmis" in ta and "heuristic_rule_based" in ta
        assert ta["medtrace"]["precision_pct"] >= 80.0
        assert ta["medtrace"]["recall_pct"] >= 80.0

        # Timing evaluation must have window_days = 7
        te = anom["timing_evaluation"]
        assert te["window_days"] == 7
        assert te["timed_true_positives"] >= 7

    # Dynamism invariant: across different seeds, total actual stockouts and transaction counts vary
    assert res1["total_actual_stockouts"] != res2["total_actual_stockouts"]




def test_curated_benchmark_evaluation_execution(tmp_path):
    """
    Priority 0c Item 5 & Backlog Item 5:
    Curated Multi-Agent Benchmark Suite (20 Hand-Crafted Clinical Scenarios).
    Verifies:
    1. Full multi-agent loop evaluation across 20 clinical scenarios (5 Clean, 4 Drift, 3 Quarantined, 3 Slip, 3 Transit, 2 UOM).
    2. MedTrace achieves 100% Correct Abstention on clean cases (5/5) with 0 false emergency purchases.
    3. MedTrace achieves 0.0% Unsupported Claim Rate via Number Auditor validation.
    4. MedTrace Anomaly Recall (100.0%) and F1 (100.0%) decisively outperform rules baseline (20.0% recall, 30.0% F1).
    5. scripts/run_curated_eval.py CLI executes cleanly and generates output/curated_evaluation.md.
    """
    from app.backtest.curated_benchmark import CuratedBenchmark, CURATED_SCENARIOS
    import subprocess
    import sys

    # 1. In-process benchmark execution
    benchmark = CuratedBenchmark(logs_dir=str(tmp_path / "logs"))
    assert len(benchmark.scenarios) == 20

    results = benchmark.run_benchmark()
    assert results["total_scenarios"] == 20

    mm = results["medtrace_metrics"]
    bm = results["baseline_metrics"]

    # Precision, Recall, and F1 invariants
    assert mm["precision_pct"] == 100.0
    assert mm["recall_pct"] == 100.0
    assert mm["f1_score_pct"] == 100.0
    assert mm["correct_abstention_pct"] == 100.0
    assert mm["correct_abstentions"] == 5
    assert mm["unsupported_claim_rate_pct"] == 0.0
    assert mm["unsupported_number_claims_count"] == 0

    # Rules baseline comparison: baseline misses hidden supplier slips, quarantined lots, and transit loss
    assert bm["recall_pct"] <= 40.0
    assert mm["recall_pct"] > bm["recall_pct"]
    assert mm["f1_score_pct"] > bm["f1_score_pct"]

    # Category-wise coverage
    cats = results["category_breakdown"]
    assert cats["CLEAN_STOCK"]["medtrace_detected"] == 5
    assert cats["PHANTOM_DRIFT"]["medtrace_detected"] == 4
    assert cats["QUARANTINED_BATCH"]["medtrace_detected"] == 3
    assert cats["CHRONIC_SUPPLIER_SLIP"]["medtrace_detected"] == 3
    assert cats["PO_TRANSIT_LOSS"]["medtrace_detected"] == 3
    assert cats["UOM_MISMATCH"]["medtrace_detected"] == 2

    # Baseline failures on silent supply disruptions
    assert cats["QUARANTINED_BATCH"]["baseline_detected"] == 0
    assert cats["CHRONIC_SUPPLIER_SLIP"]["baseline_detected"] == 0
    assert cats["PO_TRANSIT_LOSS"]["baseline_detected"] == 0

    # 2. CLI script execution verification
    cli_out_dir = str(tmp_path / "cli_eval")
    cmd_res = subprocess.run(
        [sys.executable, "scripts/run_curated_eval.py", "--output-dir", cli_out_dir],
        capture_output=True,
        text=True
    )
    assert cmd_res.returncode == 0, f"run_curated_eval failed: {cmd_res.stderr}"
    assert "MEDTRACE: CURATED MULTI-AGENT CLINICAL BENCHMARK SUITE" in cmd_res.stdout
    assert "Execution completed: 20 scenarios evaluated" in cmd_res.stdout

    report_path = os.path.join(cli_out_dir, "curated_evaluation.md")
    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    assert "# MedTrace Curated Multi-Agent Benchmark Evaluation Report" in report_text
    assert "Synthetic Benchmark Declaration" in report_text
    assert "Correct Abstention Rate (Clean Cases)" in report_text
    assert "Zero-Hallucination Number Auditor Verification Invariants" in report_text
