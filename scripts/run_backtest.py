"""
Run MedTrace Backtest Across Seeds 1-3 and Held-out Seed 4.
Generates output/backtest_seed_*.json and a summary comparative table.
"""

import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from app.backtest.engine import BacktestEngine
from scripts.generate_facility_simulation import generate_simulation

def main():
    print("="*75)
    print("MEDTRACE 180-DAY BACKTEST & BENCHMARK SUITE")
    print("Evaluating against Naive LMIS and Rule-Based Heuristic")
    print("="*75)

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    seeds = [1, 2, 3, 4]
    all_results = []

    for s in seeds:
        print(f"\n[Running Backtest Seed {s}...]")
        # If seed != 1, generate simulation for this seed into a temporary or direct directory
        sim_dir = f"data/simulated_seed_{s}" if s != 1 else "data/simulated"
        if s != 1:
            generate_simulation(seed=s, out_dir=sim_dir)

        # Temporary engine pointing to that sim dir
        engine = BacktestEngine()
        if s != 1:
            # Point base directory / paths to simulated_seed_{s}
            engine.base_dir = os.path.abspath(".")
            engine.store.base_dir = os.path.abspath(".")
            # Monkeypatch CSV paths for seed
            orig_read_csv = engine.store._read_csv
            def seed_read_csv(path):
                if "data/simulated/" in path:
                    new_path = path.replace("data/simulated/", f"data/simulated_seed_{s}/")
                    return orig_read_csv(new_path)
                return orig_read_csv(path)
            engine.store._read_csv = seed_read_csv
            
            # Monkeypatch engine load paths
            orig_load_gt = engine.load_ground_truth
            def seed_load_gt():
                gt_path = os.path.join(sim_dir, "ground_truth.csv")
                import csv
                if not os.path.exists(gt_path):
                    return []
                with open(gt_path, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))
            engine.load_ground_truth = seed_load_gt

            def seed_load_ts():
                ts_path = os.path.join(sim_dir, "true_stock_daily.csv")
                import csv
                data = {}
                if not os.path.exists(ts_path):
                    return data
                with open(ts_path, "r", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        dt = r["date"]
                        fac = r["facility_id"]
                        med = r["medicine_id"]
                        stk = float(r.get("true_stock", 0))
                        if dt not in data:
                            data[dt] = {}
                        if fac not in data[dt]:
                            data[dt][fac] = {}
                        data[dt][fac][med] = stk
                return data
            engine.load_true_stock = seed_load_ts

        result = engine.run_backtest(seed=s)
        out_file = os.path.join(output_dir, f"backtest_seed_{s}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"-> Saved results to {out_file}")
        all_results.append(result)

    # Print Comparative Summary
    print("\n" + "="*85)
    print("BACKTEST COMPARATIVE SUMMARY TABLE (SEEDS 1-3 & HELD-OUT SEED 4)")
    print("="*85)
    print(f"{'Metric':<32} | {'Naive LMIS':<14} | {'Heuristic':<14} | {'MedTrace':<14} | {'Gain / Target'}")
    print("-" * 85)

    avg_naive_lt = sum(r["metrics"]["early_warning_lead_time_days"]["naive_lmis"] for r in all_results) / len(all_results)
    avg_heur_lt = sum(r["metrics"]["early_warning_lead_time_days"]["heuristic_rule_based"] for r in all_results) / len(all_results)
    avg_med_lt = sum(r["metrics"]["early_warning_lead_time_days"]["medtrace"] for r in all_results) / len(all_results)

    avg_naive_rec = sum(r["metrics"]["stockout_recall_pct"]["naive_lmis"] for r in all_results) / len(all_results)
    avg_heur_rec = sum(r["metrics"]["stockout_recall_pct"]["heuristic_rule_based"] for r in all_results) / len(all_results)
    avg_med_rec = sum(r["metrics"]["stockout_recall_pct"]["medtrace"] for r in all_results) / len(all_results)

    avg_anom_p = sum(r["metrics"]["anomaly_detection"]["precision_pct"] for r in all_results) / len(all_results)
    avg_anom_r = sum(r["metrics"]["anomaly_detection"]["recall_pct"] for r in all_results) / len(all_results)
    avg_anom_f1 = sum(r["metrics"]["anomaly_detection"]["f1_score_pct"] for r in all_results) / len(all_results)

    total_naive_false = sum(r["metrics"]["capital_lockup_false_reorders"]["naive_lmis"] for r in all_results)
    total_heur_false = sum(r["metrics"]["capital_lockup_false_reorders"]["heuristic_rule_based"] for r in all_results)
    total_med_false = sum(r["metrics"]["capital_lockup_false_reorders"]["medtrace"] for r in all_results)

    print(f"{'Early Warning Lead Time':<32} | {avg_naive_lt:>11.1f} d | {avg_heur_lt:>11.1f} d | {avg_med_lt:>11.1f} d | +{avg_med_lt - avg_naive_lt:.1f} days (target >14d)")
    print(f"{'Stockout Recall':<32} | {avg_naive_rec:>11.1f} % | {avg_heur_rec:>11.1f} % | {avg_med_rec:>11.1f} % | +{avg_med_rec - avg_naive_rec:.1f}% (target >90%)")
    print(f"{'Anomaly Precision':<32} | {'0.0 %':>14} | {'0.0 %':>14} | {avg_anom_p:>11.1f} % | High precision")
    print(f"{'Anomaly Recall':<32} | {'0.0 %':>14} | {'0.0 %':>14} | {avg_anom_r:>11.1f} % | Target >85%")
    print(f"{'Anomaly F1 Score':<32} | {'0.0 %':>14} | {'0.0 %':>14} | {avg_anom_f1:>11.1f} % | Target >85%")
    print(f"{'False Emergency Orders':<32} | {total_naive_false:>14} | {total_heur_false:>14} | {total_med_false:>14} | Low capital lockup")
    print("="*85)

if __name__ == "__main__":
    main()
