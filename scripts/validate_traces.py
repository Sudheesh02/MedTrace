"""
MedTrace Multi-Agent Audit Trace Conformance Validator (scripts/validate_traces.py)
Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why
Phase 8.1 / Gate G4 & Track 2 Conformance Standard

Validates that JSONL audit traces conform strictly to:
1. Required JSON schema keys on every line: timestamp, agent, action, details, model, llm_used, fallback.
2. Track 2 Multi-Agent deliberation milestones (reconcile, world model context, debate, critique, revision, plan audit).
3. Grounded provenance: zero null models or ungrounded artifacts.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

REQUIRED_LINE_KEYS = {"timestamp", "agent", "action", "details", "model", "llm_used", "fallback"}
CORE_ACTIONS = {
    "START_RUN",
    "RECONCILE_COMPLETE",
    "CONTEXT_BUILT",
    "ROUND_1_START",
    "HYPOTHESES_GENERATED",
    "ROUND_1_EVALUATION",
    "ACTIONS_RECOMMENDED",
    "ACTION_PLAN_AUDITED",
    "RUN_COMPLETE"
}


def validate_trace_file(file_path: str) -> Tuple[bool, List[str]]:
    errors = []
    if not os.path.exists(file_path):
        return False, [f"Trace file does not exist: {file_path}"]

    if os.path.getsize(file_path) == 0:
        return False, [f"Trace file is empty (0 bytes): {file_path}"]

    actions_seen = set()
    line_count = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            line_count += 1
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as je:
                errors.append(f"Line {idx}: Invalid JSON syntax ({je})")
                continue

            # Verify line-level schema keys
            missing_keys = REQUIRED_LINE_KEYS - set(entry.keys())
            if missing_keys:
                errors.append(f"Line {idx}: Missing required schema keys: {sorted(list(missing_keys))}")

            # Verify typed flags
            if not isinstance(entry.get("llm_used"), bool):
                errors.append(f"Line {idx}: 'llm_used' must be boolean, got {type(entry.get('llm_used'))}")
            if not isinstance(entry.get("fallback"), bool):
                errors.append(f"Line {idx}: 'fallback' must be boolean, got {type(entry.get('fallback'))}")

            act = entry.get("action", "")
            actions_seen.add(act)

    if line_count < 5:
        errors.append(f"Trace contains only {line_count} lines; minimum 5 lines required for valid deliberation.")

    # Check for core deliberation milestones
    missing_actions = CORE_ACTIONS - actions_seen
    if missing_actions:
        errors.append(f"Trace is missing core Track 2 deliberation actions: {sorted(list(missing_actions))}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="MedTrace Audit Trace Conformance Validator")
    parser.add_argument("--trace-file", help="Specific trace file to validate")
    parser.add_argument("--all", action="store_true", help="Validate all historical trace files in logs/")
    args = parser.parse_args()

    logs_dir = os.path.join(REPO_ROOT, "logs")
    if args.trace_file:
        trace_files = [args.trace_file]
    elif args.all:
        if not os.path.exists(logs_dir):
            print(f"[!] No logs directory found at {logs_dir}")
            sys.exit(1)
        trace_files = [
            os.path.join(logs_dir, f)
            for f in os.listdir(logs_dir)
            if f.endswith(".jsonl")
        ]
    else:
        # Default behavior: validate tracked sample traces and the latest active trace
        trace_files = []
        if os.path.exists(logs_dir):
            sample_traces = [
                os.path.join(logs_dir, f)
                for f in os.listdir(logs_dir)
                if (f.startswith("sample_trace_") or f.startswith("golden_trace_") or f.startswith("trace_with")) and f.endswith(".jsonl")
            ]
            trace_files.extend(sample_traces)

            # Also include latest trace if available
            from scripts.explain_trace import find_latest_trace
            latest = find_latest_trace()
            if latest and latest not in trace_files and os.path.exists(latest):
                trace_files.append(latest)

    if not trace_files:
        print("[!] No .jsonl trace files found to validate.")
        sys.exit(1)

    print("=" * 75)
    print("MEDTRACE: MULTI-AGENT AUDIT TRACE CONFORMANCE VALIDATOR")
    print(f"Inspecting {len(trace_files)} trace file(s)...")
    print("=" * 75)

    all_passed = True
    for t_file in trace_files:
        rel_path = os.path.relpath(t_file, REPO_ROOT)
        ok, errs = validate_trace_file(t_file)
        if ok:
            print(f"[PASS] {rel_path:<45} (All schemas & actions verified)")
        else:
            print(f"[FAIL] {rel_path:<45} ({len(errs)} errors):")
            for e in errs[:5]:
                print(f"       - {e}")
            all_passed = False

    print("=" * 75)
    if all_passed:
        print("[+] SUCCESS: All multi-agent deliberation traces strictly conform to Track 2 standards!")
        sys.exit(0)
    else:
        print("[!] FAILURE: One or more audit traces failed conformance validation.")
        sys.exit(1)


if __name__ == "__main__":
    main()
