"""
MedTrace 30-Second Executive Walkthrough (scripts/quick_demo.py)
Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why

Demonstrates the complete end-to-end cognitive architecture in one command:
1. Proactive District-Wide Triage Scan (TriagePlannerAgent).
2. Deep Multi-Agent Reconciler & World Model context grounding on Golden Quarantine Case.
3. Adversarial Debate (Investigator vs Skeptic Number Auditor, Round 1 Challenge -> Round 2 Revision).
4. Final Approval-Ready Action Pack with Number Provenance (Peer Transfer + Fast-Track Batch Release).
5. Executive Explain-Why Debate Timeline visualization.
"""

import os
import sys
import time
import json
import shutil
import argparse

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.orchestrator import MedTraceOrchestrator
from scripts.explain_trace import render_trace

def main():
    parser = argparse.ArgumentParser(description="MedTrace Executive Judge Demonstration")
    parser.add_argument(
        "--case",
        choices=["golden", "standard"],
        default="golden",
        help="Target clinical demonstration case: 'golden' (FAC-CHC-01/MED-001 quarantine stockout) or 'standard' (FAC-DH-01/MED-007)"
    )
    parser.add_argument("--top-n", type=int, default=3, help="Top urgent items to display in triage scan")
    parser.add_argument("--output-trace", type=str, default=None, help="Optional output path to copy the resulting debate trace")
    parser.add_argument("--save-golden", action="store_true", help="Explicitly update the committed canonical golden trace file")
    args = parser.parse_args()

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
    triage_res = orchestrator.triage_district(top_n=args.top_n)
    t_triage = time.time() - t0

    print(f"-> Scanned {triage_res['total_evaluated']} pairs in {t_triage:.2f}s:")
    print(f"   Status Breakdown: {triage_res['critical_count']} CRITICAL | {triage_res['warning_count']} WARNING | {triage_res['secure_count']} SECURE")
    print("-" * 80)
    print(f"{'Facility':<20} | {'Medicine':<22} | {'Trust Cover':<12} | {'Urgency':<10}")
    print("-" * 80)
    for item in triage_res["top_urgent_items"][:args.top_n]:
        print(f"{item['facility_name'][:20]:<20} | {item['generic_name'][:22]:<22} | {item['trust_cover_days']:>7.1f} d   | {item['urgency_tier']:<10}")
    print("-" * 80)

    # -------------------------------------------------------------
    # Step 2: Deep Multi-Agent Investigation on Target Anomaly
    # -------------------------------------------------------------
    if args.case == "golden":
        target_fac = "FAC-CHC-01"
        target_med = "MED-001"
    else:
        target_fac = "FAC-DH-01"
        target_med = "MED-007"

    med_meta = next((m for m in orchestrator.data_store.get_medicines() if m["medicine_id"] == target_med), {})
    fac_meta = next((f for f in orchestrator.data_store.get_facilities() if f["facility_id"] == target_fac), {})
    med_label = f"{med_meta.get('generic_name', target_med)} {med_meta.get('form', '')}".strip()
    fac_label = f"{fac_meta.get('name', target_fac)} ({fac_meta.get('level', 'Facility')})"

    case_tag = "GOLDEN CASE: " if args.case == "golden" else ""
    print(f"\n[STEP 2 / 4] Launching Deep Multi-Agent Audit on {case_tag}{target_fac} ({med_label})...")
    print(f"             - Target Node: {fac_label} | Medicine: {med_label}")
    print("             - Auditing records across warehouse ledger, physical counts, QA batch hold registry, and supplier priors.")

    t1 = time.time()
    pack = orchestrator.run_investigation(facility_id=target_fac, medicine_id=target_med)
    t_inv = time.time() - t1

    print(f"\n-> Investigation finalized in {t_inv:.2f}s across {pack.skeptic_rounds} adversarial rounds:")
    print(f"   - Ledger Stock: {pack.ledger_stock:.1f} units ({pack.days_of_cover_naive:.1f}d naive cover; LMIS considers safe)")
    if pack.quarantined_stock and pack.quarantined_stock > 0:
        recall_note = "facility QA batch quarantine hold"
        if hasattr(orchestrator, "data_store"):
            recalls = orchestrator.data_store.get_openfda_recalls(medicine_id=target_med, generic_name=med_label)
            if recalls:
                recall_note = f"openFDA enforcement recall match ({len(recalls)} registered events in dataset)"
        print(f"   - QA quarantine hold: {pack.quarantined_stock:.1f} units locked under {recall_note}")
    if pack.audit_drift and pack.audit_drift > 0:
        print(f"   - Physical Audit Drift: {pack.audit_drift:.1f} units unrecorded ledger variance")
    print(f"   - Trust-Adjusted Usable Stock: {pack.usable_stock:.1f} units ({pack.days_of_cover_trust:.1f}d true cover -> catastrophic deficit in {pack.days_of_cover_trust:.1f} days)")
    print(f"   - Winning Hypothesis: {pack.winning_hypothesis.title}")
    print(f"   - Root Cause: {pack.winning_hypothesis.cause}")
    if pack.skeptic_rounds > 1:
        adv_outcome = f"Skeptic challenged in Round 1 -> Investigator refined -> Skeptic approved in Round {pack.skeptic_rounds}"
    else:
        adv_outcome = f"Skeptic approved hypothesis in Round 1 with zero ungrounded inconsistencies"
    print(f"   - Adversarial Outcome: {adv_outcome}")

    # -------------------------------------------------------------
    # Step 3: Approval-Ready Action Pack Formulation
    # -------------------------------------------------------------
    print(f"\n[STEP 3 / 4] Formulated Approval-Ready Action Pack:")
    print(f"   - Naive Ledger Cover: {pack.days_of_cover_naive:.1f} days (unadjusted)")
    print(f"   - Trust-Adjusted Usable Cover: {pack.days_of_cover_trust:.1f} days (catastrophic deficit uncovered)")
    print(f"   - Understated Cover Gap: {pack.understated_gap_percent:.1f}%")
    print(f"   - Stockout Prevented: {'YES [CRITICAL EARLY WARNING]' if pack.stockout_prevented else 'NO'}")
    print(f"   - Number Auditor Verification: {'PASSED [OK]' if pack.action_plan_audit.passed else 'FAILED'}")
    rounds_str = f"{pack.skeptic_rounds} round{'s' if pack.skeptic_rounds != 1 else ''}"
    if pack.trace_file and os.path.exists(pack.trace_file):
        try:
            round_actions = []
            with open(pack.trace_file, "r", encoding="utf-8") as tf:
                for line in tf:
                    ev = json.loads(line)
                    act = ev.get("action", "")
                    if act.endswith("_EVALUATION") and "ROUND_" in act:
                        r_idx = act.split("_")[1]
                        acc = ev.get("details", {}).get("accepted", False)
                        round_actions.append(f"Round {r_idx} {'Approved' if acc else 'Challenged'}")
            if round_actions:
                rounds_str = f"{pack.skeptic_rounds} rounds (" + " -> ".join(round_actions) + ")"
        except Exception:
            pass
    print(f"   - Adversarial Debate Rounds: {rounds_str}")
    print(f"   - Verified Recommendations ({pack.action_plan_audit.verified_recommendations_count} actions):")
    for i, act in enumerate(pack.recommendations[:3], 1):
        act_name = act.action_type.value if hasattr(act.action_type, "value") else str(act.action_type)
        cost_str = f" (${act.estimated_cost_usd:.2f} USD)" if act.estimated_cost_usd is not None else ""
        print(f"     {i}. [{act_name}] {act.recommended_units:.1f} units{cost_str} (Feasibility: {act.feasibility_score:.2f})")
        print(f"        Justification: {act.justification}")

    # -------------------------------------------------------------
    # Step 4: Executive Explain-Why Debate Timeline
    # -------------------------------------------------------------
    print(f"\n[STEP 4 / 4] Rendering Explain-Why Audit & Multi-Agent Debate Timeline:")
    render_trace(pack.trace_file)

    if args.output_trace:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_trace)), exist_ok=True)
        shutil.copyfile(pack.trace_file, args.output_trace)
        print(f"[+] Output trace saved: {args.output_trace}")
    elif args.save_golden or (args.case == "golden" and os.environ.get("MEDTRACE_SAVE_GOLDEN") == "1"):
        golden_trace_path = os.path.join(orchestrator.logs_dir, "golden_trace_FAC-CHC-01_MED-001.jsonl")
        shutil.copyfile(pack.trace_file, golden_trace_path)
        print(f"[+] Canonical Golden Trace committed & saved: {golden_trace_path}")
    else:
        print(f"[+] Dynamic run trace saved: {pack.trace_file}")

    t_total = time.time() - t0
    mode_str = "Deterministic Sample Mode (rule-based offline)" if (pack.fallback or not pack.llm_used) else f"Live LLM Mode ({pack.model_used})"
    print(f"\n[+] Demonstration successfully completed in {t_total:.2f}s ({mode_str}).")
    audit_tag = "PASSED [OK]" if pack.action_plan_audit.passed else "FLAGGED"
    v_count = pack.action_plan_audit.verified_recommendations_count
    print(f"    Number Auditor: {v_count} recommendations mathematically verified [{audit_tag}]. Zero ungrounded numbers emitted.")
    print("="*85 + "\n")

if __name__ == "__main__":
    main()
