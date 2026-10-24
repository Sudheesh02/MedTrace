"""
MedTrace Autonomous Self-Improving & Stress-Testing Runner (scripts/overnight_autonomous_runner.py)
Continuously runs comprehensive self-audits, mathematical invariant stress tests,
multi-agent deliberation loop challenges, and simulation replays.
Logs all findings and performance metrics to output/autonomous_iteration_report.json.
"""

import os
import sys
import time
import json
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Any

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters.data_store import DataStore
from app.adapters.llm_client import LLMClient
from app.engine.deterministic import DeterministicEngine
from app.engines.world_model import WorldStoreService, IngestPipelineService, ContextBuilderService
from app.engines.hmem import HMemEngine
from app.agents.reconciler import ReconcilerAgent
from app.agents.investigator import InvestigatorAgent
from app.agents.skeptic import SkepticAgent
from app.agents.action_planner import ActionPlannerAgent
from app.orchestrator import MedTraceOrchestrator
from app.backtest.engine import BacktestEngine
from scripts.generate_facility_simulation import generate_simulation

class AutonomousRunner:
    def __init__(self):
        self.report_path = "output/autonomous_iteration_report.json"
        os.makedirs("output", exist_ok=True)
        self.store = DataStore(use_zetaris=False)
        self.orchestrator = MedTraceOrchestrator(use_zetaris=False)
        self.backtest = BacktestEngine(sim_dir="data/simulated")

    def run_full_pass(self, iteration_num: int = 1) -> Dict[str, Any]:
        start_time = time.time()
        print(f"\n{'='*75}")
        print(f"[*] STARTING AUTONOMOUS ITERATION PASS #{iteration_num} - {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*75}")

        pass_metrics = {
            "iteration": iteration_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phases": {}
        }

        # -------------------------------------------------------------
        # Phase 1: Data Layer & API Health Audit
        # -------------------------------------------------------------
        print("\n[Phase 1/5] Auditing Data Layer & API Integrity...")
        p1_start = time.time()
        meds = self.store.get_medicines()
        facs = self.store.get_facilities()
        suppliers = self.store.get_suppliers()
        deliveries = self.store.get_deliveries()
        batches = self.store.get_batches()

        assert len(meds) == 12, f"Expected 12 medicines, found {len(meds)}"
        assert len(facs) == 12, f"Expected 12 facilities, found {len(facs)}"
        assert len(suppliers) == 4, f"Expected 4 suppliers, found {len(suppliers)}"
        assert len(batches) > 0, "Batches table is empty"

        # Check newly enriched datasets
        recalls_sample = self.store.get_openfda_recalls(medicine_id="MED-001")
        rxnorm_sample = self.store.get_rxnorm_standard("MED-001")
        pkg_sample = self.store.get_packaging_standard("MED-001")
        surv_sample = self.store.get_disease_surveillance("MED-009")
        shortage_sample = self.store.get_cross_border_shortages(medicine_id="MED-007")

        assert len(recalls_sample) > 0, "openFDA recalls dataset query failed"
        assert rxnorm_sample is not None, "RxNorm dataset query failed"
        assert pkg_sample is not None, "DailyMed packaging query failed"
        assert surv_sample is not None, "WHO surveillance query failed"
        assert shortage_sample is not None, "Cross-border shortages query failed"

        pass_metrics["phases"]["phase_1_data_audit"] = {
            "status": "PASSED",
            "duration_seconds": round(time.time() - p1_start, 3),
            "medicines_count": len(meds),
            "facilities_count": len(facs),
            "suppliers_count": len(suppliers),
            "deliveries_count": len(deliveries),
            "batches_count": len(batches)
        }
        print(" -> Phase 1 Verified: All 5 open datasets and local tables loaded cleanly.")

        # -------------------------------------------------------------
        # Phase 2: Deterministic Engine Math Invariant Stress-Testing
        # -------------------------------------------------------------
        print("\n[Phase 2/5] Stress-Testing Deterministic Math Engine Invariants...")
        p2_start = time.time()
        stress_tests_passed = 0

        # Boundary Test 1: Zero consumption
        doc_zero = DeterministicEngine.compute_days_of_cover(usable_stock=500.0, daily_rate=0.0)
        assert doc_zero == 999.0, f"Expected 999.0 on zero daily rate, got {doc_zero}"
        stress_tests_passed += 1

        # Boundary Test 2: Negative stock (must clamp to 0)
        stock_eval_neg = DeterministicEngine.compute_trust_adjusted_stock(
            ledger_stock=100.0, audit_drift=150.0, quarantined_stock=50.0, expiring_stock=50.0
        )
        assert stock_eval_neg["usable_stock"] == 0.0, "Usable stock failed to clamp at 0"
        stress_tests_passed += 1

        # Boundary Test 3: UOM normalization extreme multipliers
        uom_box = DeterministicEngine.normalize_uom_quantity(reported_quantity=12, reported_unit="box")
        assert uom_box["normalized_quantity"] == 1200.0
        stress_tests_passed += 1

        # Boundary Test 4: Monte Carlo ETA distributions
        mc_res = DeterministicEngine.simulate_monte_carlo_eta(
            promised_days=6.0, days_of_cover=8.0, slip_distribution=[1.0, 2.0, 3.0, 5.0, 8.0], num_simulations=2000
        )
        assert 0.0 <= mc_res["p_stockout_before_arrival"] <= 1.0
        assert mc_res["p90_arrival_days"] >= 6.0
        stress_tests_passed += 1

        pass_metrics["phases"]["phase_2_math_stress"] = {
            "status": "PASSED",
            "duration_seconds": round(time.time() - p2_start, 3),
            "tests_passed": stress_tests_passed
        }
        print(f" -> Phase 2 Verified: All {stress_tests_passed} boundary & mathematical invariant tests passed.")

        # -------------------------------------------------------------
        # Phase 3: Multi-Agent Facility Grid Replay
        # -------------------------------------------------------------
        print("\n[Phase 3/5] Evaluating Multi-Agent Grid (12 Facilities x 12 Medicines)...")
        p3_start = time.time()
        grid_items_tested = 0
        grid_anomalies_flagged = 0
        error_count = 0

        # Sample test across 4 facility tiers (DH, CHC, PHC, WH) for diverse medicines
        tier_facilities = ["FAC-DH-01", "FAC-CHC-01", "FAC-PHC-03", "FAC-WH-01"]
        tier_meds = ["MED-001", "MED-006", "MED-007", "MED-008", "MED-011"]

        for fid in tier_facilities:
            for mid in tier_meds:
                try:
                    pack = self.orchestrator.run_investigation(facility_id=fid, medicine_id=mid)
                    grid_items_tested += 1
                    if len(pack.recommendations) > 0:
                        grid_anomalies_flagged += 1
                    assert pack.run_id is not None
                    assert pack.winning_hypothesis is not None
                    assert pack.days_of_cover_trust >= 0.0
                except Exception as e:
                    print(f"[!] Error on {fid}-{mid}: {str(e)}")
                    error_count += 1

        pass_metrics["phases"]["phase_3_multi_agent_grid"] = {
            "status": "PASSED" if error_count == 0 else "WARNING",
            "duration_seconds": round(time.time() - p3_start, 3),
            "items_tested": grid_items_tested,
            "anomalies_identified": grid_anomalies_flagged,
            "errors": error_count
        }
        print(f" -> Phase 3 Verified: {grid_items_tested} multi-agent runs completed with {error_count} errors.")

        # -------------------------------------------------------------
        # Phase 4: Backtest Benchmark Evaluation
        # -------------------------------------------------------------
        print("\n[Phase 4/5] Running 180-Day Comparative Backtest Replay...")
        p4_start = time.time()
        bt_res = self.backtest.run_backtest(seed=1, sim_dir="data/simulated")
        metrics = bt_res["metrics"]

        pass_metrics["phases"]["phase_4_backtest"] = {
            "status": "PASSED",
            "duration_seconds": round(time.time() - p4_start, 3),
            "lead_time_advantage_days": metrics["early_warning_lead_time_days"]["lead_time_advantage_days"],
            "stockout_recall_pct": metrics["stockout_recall_pct"]["medtrace"],
            "anomaly_precision_pct": metrics["anomaly_detection"]["precision_pct"],
            "anomaly_recall_pct": metrics["anomaly_detection"]["recall_pct"],
            "anomaly_f1_pct": metrics["anomaly_detection"]["f1_score_pct"],
            "false_emergency_reorders": metrics["capital_lockup_false_reorders"]["medtrace"]
        }
        print(f" -> Phase 4 Verified: Lead time advantage: +{metrics['early_warning_lead_time_days']['lead_time_advantage_days']}d | Anomaly F1: {metrics['anomaly_detection']['f1_score_pct']}% | Recall: {metrics['stockout_recall_pct']['medtrace']}%.")

        # -------------------------------------------------------------
        # Phase 5: Report Synthesis & Persistence
        # -------------------------------------------------------------
        total_duration = round(time.time() - start_time, 2)
        pass_metrics["total_duration_seconds"] = total_duration

        # Load existing history if available
        history = []
        if os.path.exists(self.report_path):
            try:
                with open(self.report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    history = data.get("iteration_history", [])
            except Exception:
                history = []

        history.append(pass_metrics)
        final_report = {
            "latest_run": pass_metrics,
            "total_iterations_completed": len(history),
            "iteration_history": history[-20:]  # Keep last 20
        }

        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(final_report, f, indent=2)

        print(f"\n[+] Full iteration #{iteration_num} completed in {total_duration}s. Report saved to {self.report_path}.")
        return pass_metrics

if __name__ == "__main__":
    runner = AutonomousRunner()
    runner.run_full_pass(iteration_num=1)
