"""
MedTrace Clean-Clone & Offline Environment Validator (scripts/validate_clean_clone.py)
Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why
Phase 8.1 / Gate G4: Clean Clone & Offline Self-Contained Verification

Simulates a judge's fresh clone experience:
1. Verifies that sample-mode / offline operations run without requiring external cloud credentials or .env.
2. Runs smoke_test.py (reporting provider credentials or clean zero-hardcoding exit).
3. Executes scripts/quick_demo.py (30-second executive walkthrough).
4. Executes run.py --cli --sample-mode --explain --export-memo (multi-agent audit, explain trace, memo export).
5. Executes scripts/explain_trace.py --latest (debate visualizer fallback & dynamic trace inspection).
6. Runs pytest smoke tests.
"""

import os
import sys
import subprocess
import time

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def run_step(cmd_args, step_name: str, expected_snippet: str = None) -> bool:
    print(f"\n[*] STEP: {step_name}")
    print(f"    Command: {' '.join(cmd_args)}")
    t0 = time.time()
    res = subprocess.run(
        cmd_args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "SAMPLE_MODE": "true", "USE_ZETARIS": "false"}
    )
    elapsed = time.time() - t0
    
    if res.returncode != 0:
        print(f"    [!] FAILED (exit code {res.returncode}) in {elapsed:.2f}s")
        if res.stderr:
            print("    --- Stderr ---")
            print(res.stderr[:500])
        return False

    if expected_snippet and expected_snippet.lower() not in res.stdout.lower():
        print(f"    [!] FAILED: Expected output snippet '{expected_snippet}' not found.")
        print("    --- Stdout ---")
        print(res.stdout[:500])
        return False

    print(f"    [+] PASSED in {elapsed:.2f}s")
    return True


def main():
    print("=" * 80)
    print("MEDTRACE: CLEAN-CLONE & OFFLINE ENVIRONMENT VALIDATION (GATE G4)")
    print("Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why")
    print("=" * 80)

    steps = [
        (
            [sys.executable, "-c", "from app.orchestrator import MedTraceOrchestrator; orch = MedTraceOrchestrator(use_zetaris=False); assert orch.llm_client.sample_mode is True; print('Orchestrator clean init passed')"],
            "Isolated Environment Initialization Check (No Credentials Needed)",
            "Orchestrator clean init passed"
        ),
        (
            [sys.executable, "smoke_test.py"],
            "Pre-Flight Smoke Test (Gate G1 - smoke_test.py)",
            "RUNNING MEDTRACE PRE-FLIGHT SMOKE TEST"
        ),
        (
            [sys.executable, "scripts/quick_demo.py"],
            "30-Second Executive Judge Demo (scripts/quick_demo.py)",
            "EXECUTIVE JUDGE DEMONSTRATION"
        ),
        (
            [sys.executable, "run.py", "--cli", "--sample-mode", "--explain", "--export-memo"],
            "CLI Audit, Multi-Agent Debate, Trace & Memo Export (run.py)",
            "Procurement Memorandum exported to"
        ),
        (
            [sys.executable, "scripts/explain_trace.py", "--latest"],
            "Explain-Why Multi-Agent Debate Visualizer (scripts/explain_trace.py --latest)",
            "MULTI-AGENT REASONING & AUDIT TIMELINE"
        ),
        (
            [sys.executable, "scripts/export_action_pack.py", "--facility", "FAC-DH-01", "--medicine", "MED-007"],
            "Procurement Memorandum Direct Exporter (scripts/export_action_pack.py)",
            "Printable Procurement Memorandum successfully written to"
        ),
        (
            [sys.executable, "-m", "pytest", "tests/test_enriched_data.py", "tests/test_data_store.py", "-q"],
            "Fast Pytest Verification (Enriched Data & DataStore)",
            "passed"
        )
    ]

    all_passed = True
    results = []

    for cmd, name, snippet in steps:
        ok = run_step(cmd, name, snippet)
        results.append((name, ok))
        if not ok:
            all_passed = False

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    for name, ok in results:
        status_str = "[PASS]" if ok else "[FAIL]"
        print(f"  {status_str:<8} | {name}")
    print("=" * 80)

    if all_passed:
        print("[+] SUCCESS: Clean-clone environment and all quickstart entry points verified!")
        sys.exit(0)
    else:
        print("[!] FAILURE: One or more clean-clone validation steps failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
