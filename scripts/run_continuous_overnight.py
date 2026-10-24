"""
MedTrace Continuous Overnight Autonomous Daemon (scripts/run_continuous_overnight.py)
Executes non-stop calibration passes, mathematical audits, and backtest benchmarks throughout the night.
Heartbeat is written to logs/overnight_heartbeat.log.
Detailed metrics are appended to output/autonomous_iteration_report.json.
"""

import os
import sys
import time
from datetime import datetime, timezone

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.overnight_autonomous_runner import AutonomousRunner

def run_overnight_loop(interval_seconds: int = 300, max_iterations: int = 100):
    os.makedirs("logs", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    heartbeat_path = "logs/overnight_heartbeat.log"

    print("="*75)
    print("MEDTRACE NON-STOP OVERNIGHT AUTONOMOUS AGENT RUNNER")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print(f"Cycle interval: {interval_seconds} seconds (~{interval_seconds//60} min)")
    print("="*75)

    runner = AutonomousRunner()
    iteration = 1

    while iteration <= max_iterations:
        iter_start = datetime.now(timezone.utc).isoformat()
        log_msg = f"[{iter_start}] Starting Overnight Autonomous Iteration #{iteration}...\n"
        print(log_msg.strip())
        with open(heartbeat_path, "a", encoding="utf-8") as f:
            f.write(log_msg)

        try:
            metrics = runner.run_full_pass(iteration_num=iteration)
            summary = (
                f"[{datetime.now(timezone.utc).isoformat()}] SUCCESS Iteration #{iteration}: "
                f"Duration={metrics.get('total_duration_seconds')}s | "
                f"LeadTimeAdvantage={metrics['phases']['phase_4_backtest']['lead_time_advantage_days']}d | "
                f"AnomalyF1={metrics['phases']['phase_4_backtest']['anomaly_f1_pct']}%\n"
            )
            print(summary.strip())
            with open(heartbeat_path, "a", encoding="utf-8") as f:
                f.write(summary)
        except Exception as e:
            err_msg = f"[{datetime.now(timezone.utc).isoformat()}] ERROR in Iteration #{iteration}: {str(e)}\n"
            print(err_msg.strip())
            with open(heartbeat_path, "a", encoding="utf-8") as f:
                f.write(err_msg)

        iteration += 1
        print(f"Sleeping for {interval_seconds}s before next autonomous iteration pass...\n")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    # 5-minute interval between full audit passes
    run_overnight_loop(interval_seconds=300, max_iterations=120)
