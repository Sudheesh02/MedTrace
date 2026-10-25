"""
Explain Trace Visualizer (scripts/explain_trace.py)
Renders multi-agent debate transcripts from JSONL trace logs into an executive, judge-ready timeline.
Demonstrates adversarial debate, Number Auditor verification, and reactive recovery.
"""

import os
import sys
import json
import glob
import argparse
from typing import List, Dict, Any, Optional

def find_latest_trace(logs_dir: str = "logs") -> Optional[str]:
    files = glob.glob(os.path.join(logs_dir, "trace_*.jsonl"))
    if files:
        files.sort(key=os.path.getmtime, reverse=True)
        return files[0]
    
    # On clean clones prior to dynamic runs, fall back to tracked judge sample trace
    sample_trace = os.path.join(logs_dir, "sample_trace_FAC-DH-01_MED-007.jsonl")
    if os.path.exists(sample_trace):
        print(f"[i] No dynamic trace logs found; rendering tracked sample trace ({os.path.basename(sample_trace)}) for judge evaluation.")
        return sample_trace
    return None

def render_trace(trace_path: str):
    if not os.path.exists(trace_path):
        print(f"[!] Error: Trace file not found: {trace_path}")
        sys.exit(1)

    print("\n" + "="*85)
    print("MEDTRACE MULTI-AGENT REASONING & AUDIT TIMELINE")
    print(f"Source: {os.path.basename(trace_path)}")
    print("="*85)

    with open(trace_path, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    start_event = next((e for e in events if e.get("action") == "START_RUN"), None)
    if start_event:
        details = start_event.get("details", {})
        print(f"\n[TARGET] Facility: {details.get('facility_id')} | Medicine: {details.get('medicine_id')} | Run ID: {start_event.get('run_id')}")

    for e in events:
        agent = e.get("agent")
        action = e.get("action")
        details = e.get("details", {})
        ts = e.get("timestamp", "").split("T")[-1][:8]

        if action == "RECONCILE_COMPLETE":
            print(f"\n[{ts}] [ReconcilerAgent] Grounded Audit Complete:")
            print(f"  - Discrepancies Detected: {details.get('discrepancies_found')}")
            print(f"  - Usable Physical Stock: {details.get('usable_stock')} units")
            print(f"  - Shortfall to Delivery: {details.get('shortfall')} units")

        elif action == "CONTEXT_BUILT":
            print(f"\n[{ts}] [WorldModelEngine] Canonical Context Grounded:")
            print(f"  - Canonical State Hash: {details.get('canon_hash')}")
            print(f"  - Grounded Entities: {', '.join(details.get('entities_present', []))}")

        elif action == "ROUND_1_START":
            print(f"\n" + "-"*65)
            print(f"[{ts}] --- MULTI-AGENT ADVERSARIAL DEBATE: ROUND 1 ---")
            print("-" * 65)

        elif action == "HYPOTHESES_GENERATED" and "ROUND_1" in str(events[events.index(e)-1].get("action")):
            print(f"[{ts}] [InvestigatorAgent] Generated {details.get('hypotheses_count')} Competing Hypotheses:")
            for hid, lk in details.get("likelihoods", {}).items():
                print(f"    * {hid}: Likelihood = {lk:.2f}")

        elif action == "ROUND_1_EVALUATION":
            acc = details.get("accepted")
            icon = "[PASS]" if acc else "[CHALLENGE]"
            print(f"\n[{ts}] [SkepticAgent & Number Auditor] Round 1 Evaluation: {icon}")
            print(f"  - Numbers Validated Against Math Invariants: {details.get('numbers_valid')}")
            print(f"  - Critique: {details.get('critique')}")
            if details.get("flagged_inconsistencies"):
                print(f"  - Flagged Ambiguities: {'; '.join(details.get('flagged_inconsistencies'))}")

        elif action == "ROUND_2_START":
            print(f"\n" + "-"*65)
            print(f"[{ts}] --- MULTI-AGENT ADVERSARIAL DEBATE: ROUND 2 (REVISION & REFUTATION) ---")
            print("-" * 65)

        elif action == "HYPOTHESES_GENERATED" and "ROUND_2" in str(events[events.index(e)-1].get("action")):
            print(f"[{ts}] [InvestigatorAgent] Revised Hypotheses after Skeptic Challenge:")
            for hid, lk in details.get("likelihoods", {}).items():
                print(f"    * {hid}: Revised Likelihood = {lk:.2f}")

        elif action == "ROUND_2_EVALUATION":
            acc = details.get("accepted")
            icon = "[APPROVED]" if acc else "[REJECTED]"
            print(f"\n[{ts}] [SkepticAgent & Number Auditor] Round 2 Evaluation: {icon}")
            print(f"  - Confidence: {details.get('confidence'):.2f}")
            print(f"  - Critique: {details.get('critique')}")

        elif action == "ACTIONS_RECOMMENDED":
            print(f"\n[{ts}] [ActionPlannerAgent] Prioritized Interventions Formulated:")
            print(f"  - Recommendations Count: {details.get('recommendations_count')}")
            print(f"  - Primary Selected Action: {details.get('top_action')}")

        elif action == "ACTION_PLAN_AUDITED":
            passed = details.get("passed")
            icon = "[AUDIT PASSED]" if passed else "[AUDIT FAILED]"
            print(f"\n[{ts}] [Number Auditor] Action Plan Verification: {icon}")
            print(f"  - Verified Actions: {details.get('verified_count')} items checked against deterministic equations.")
            if details.get("flagged_inconsistencies"):
                print(f"  - Inconsistencies: {'; '.join(details.get('flagged_inconsistencies'))}")

        elif action == "HUMAN_ESCALATION":
            print(f"\n[{ts}] [HUMAN ESCALATION] Alert: {details.get('reason')}")

        elif action == "RUN_COMPLETE":
            print(f"\n[{ts}] [Orchestrator] Run Finalized: Status = {details.get('status')}")

    print("="*85 + "\n")

def main():
    parser = argparse.ArgumentParser(description="MedTrace Trace Visualizer")
    parser.add_argument("--file", help="Path to specific trace JSONL file")
    parser.add_argument("--latest", action="store_true", help="Visualize latest trace file in logs/")
    args = parser.parse_args()

    trace_file = args.file
    if args.latest or not trace_file:
        trace_file = find_latest_trace()

    if not trace_file:
        print("[!] No trace files found in logs/.")
        sys.exit(1)

    render_trace(trace_file)

if __name__ == "__main__":
    main()
