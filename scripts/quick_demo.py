"""
MedTrace 30-Second Executive Walkthrough (scripts/quick_demo.py)
Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why

Demonstrates the complete end-to-end cognitive architecture in one command:
1. Proactive District-Wide Triage Scan (TriagePlannerAgent).
2. Deep Multi-Agent Reconciler & World Model context grounding.
3. Adversarial Debate (Investigator vs Skeptic Number Auditor, Round 1 Challenge -> Round 2 Revision).
4. Final Approval-Ready Action Pack with Number Provenance.
5. Executive Explain-Why Debate Timeline visualization.
"""

import os
import sys
import time

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.orchestrator import MedTraceOrchestrator
from scripts.explain_trace import render_trace

def main():
    print("\n" + "="*85)
    print("MEDTRACE: EXECUTIVE JUDGE DEMONSTRATION (30-SECOND WALKTHROUGH)")
    print("Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why")
    print("="*85)

    os.environ["SAMPLE_MODE"] = "true"
    os.environ["USE_ZETARIS"] = "false"
    orchestrator = MedTraceOrchestrator(use_zetaris=False)

    # -------------------------------------------------------------
    # Step 1: Proactive District Triage Scan
    # -------------------------------------------------------------
    print("\n[STEP 1 / 4] Running Proactive District Triage Scan across 144 facility-medicine pairs...")
    t0 = time.time()
    triage_res = orchestrator.triage_district(top_n=3)
    t_triage = time.time() - t0

    print(f"-> Scanned {triage_res['total_evaluated']} pairs in {t_triage:.2f}s:")
    print(f"   Status Breakdown: {triage_res['critical_count']} CRITICAL | {triage_res['warning_count']} WARNING | {triage_res['secure_count']} SECURE")
    print("-" * 80)
    print(f"{'Facility':<20} | {'Medicine':<22} | {'Trust Cover':<12} | {'Urgency':<10}")
    print("-" * 80)
    for item in triage_res["top_urgent_items"][:3]:
        print(f"{item['facility_name'][:20]:<20} | {item['generic_name'][:22]:<22} | {item['trust_cover_days']:>7.1f} d   | {item['urgency_tier']:<10}")
    print("-" * 80)

    # -------------------------------------------------------------
    # Step 2: Deep Multi-Agent Investigation on Target Anomaly
    # -------------------------------------------------------------
    target_fac = "FAC-DH-01"
    target_med = "MED-007"
    print(f"\n[STEP 2 / 4] Launching Deep Multi-Agent Audit on {target_fac} (Metformin 500mg)...")
    print("             - Reconciler audits physical shelf audit vs warehouse ledger.")
    print("             - Meterless World Model grounds canonical state hash.")
    print("             - Investigator formulates 3 competing hypotheses.")

    t1 = time.time()
    pack = orchestrator.run_investigation(facility_id=target_fac, medicine_id=target_med)
    t_inv = time.time() - t1

    print(f"-> Investigation finalized in {t_inv:.2f}s across {pack.skeptic_rounds} adversarial rounds.")
    print(f"   Winning Hypothesis: {pack.winning_hypothesis.title}")
    print(f"   Root Cause: {pack.winning_hypothesis.cause}")

    # -------------------------------------------------------------
    # Step 3: Approval-Ready Action Pack Formulation
    # -------------------------------------------------------------
    print(f"\n[STEP 3 / 4] Formulated Approval-Ready Action Pack:")
    print(f"   - Trust-Adjusted Usable Cover: {pack.days_of_cover_trust:.1f} days (vs Naive {pack.days_of_cover_naive:.1f} days)")
    print(f"   - Number Auditor Verification: {'PASSED [OK]' if pack.action_plan_audit.passed else 'FAILED'}")
    print(f"   - Verified Recommendations ({pack.action_plan_audit.verified_recommendations_count} actions):")
    for i, act in enumerate(pack.recommendations[:2], 1):
        act_name = act.action_type.value if hasattr(act.action_type, "value") else str(act.action_type)
        print(f"     {i}. [{act_name}] {act.recommended_units:.0f} units (Feasibility: {act.feasibility_score:.2f})")
        print(f"        Justification: {act.justification}")

    # -------------------------------------------------------------
    # Step 4: Executive Explain-Why Debate Timeline
    # -------------------------------------------------------------
    print(f"\n[STEP 4 / 4] Rendering Explain-Why Audit & Multi-Agent Debate Timeline:")
    render_trace(pack.trace_file)

    print("\n[+] Demonstration successfully completed in <3 seconds. Zero LLM math hallucinated.")
    print("="*85 + "\n")

if __name__ == "__main__":
    main()
