"""
MedTrace Main Programmatic Entry Point (run.py)
Meets Technical Execution Requirements:
1. CLI entry: python run.py --cli
2. Programmatic API: python run.py (FastAPI on 0.0.0.0:8000, POST /run)
3. Supports SAMPLE_MODE=true for offline judging
4. Bounded execution with internal timeouts and structured JSON output
"""

import os
import sys
import json
import time
import argparse
import re
import threading
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables prior to package initialization
load_dotenv()

# If no LLM credentials are configured and SAMPLE_MODE is not explicitly set, default to sample mode
if not (os.environ.get("MODEL_API_KEY") or os.environ.get("METERLESS_RUNTIME_TOKEN")):
    if "SAMPLE_MODE" not in os.environ:
        os.environ["SAMPLE_MODE"] = "true"

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from app.envutil import env_bool
from app.orchestrator import MedTraceOrchestrator

app = FastAPI(
    title="MedTrace AI Agent API",
    version="1.0.0",
    summary="MedTrace Multi-Agent Inventory Reconciliation & Supply Chain Intelligence Service",
    description=(
        "Autonomous Clinical Supply Chain Intelligence Platform for District Health Logistics.\n\n"
        "**Track 2: The Agent That Can Explain Why** (Open Agent Hackathon 2026)\n\n"
        "- **Zero LLM Arithmetic**: All inventory reconciliation, days-of-cover, and order quantities are 100% deterministic.\n"
        "- **Adversarial Multi-Agent Deliberation**: Reconciler, Investigator, Skeptic Number Auditor, and Action Planner.\n"
        "- **Sponsor Technologies**: Zetaris Lightning SQL, Meterless World Model & H-MEM, NVIDIA Nemotron."
    )
)
orchestrator = MedTraceOrchestrator()

# The orchestrator, its LLM client / data store flags and H-MEM are process-wide shared state, and /run temporarily
# flips them per request. Requests that touch that state are therefore serialised; a waiting request gives up with
# 503 after RUN_LOCK_TIMEOUT_S instead of hanging forever.
_exclusive_lock = threading.Lock()
RUN_LOCK_TIMEOUT_S = float(os.environ.get("MEDTRACE_RUN_LOCK_TIMEOUT_S", "600"))
REPO_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


@contextmanager
def _exclusive():
    if not _exclusive_lock.acquire(timeout=RUN_LOCK_TIMEOUT_S):
        raise HTTPException(status_code=503, detail="MedTrace is busy with another analysis; retry shortly.")
    try:
        yield
    finally:
        _exclusive_lock.release()

class RunRequest(BaseModel):
    facility_id: Optional[str] = Field("FAC-DH-01", description="Target facility identifier (e.g. FAC-DH-01, FAC-CHC-01)")
    medicine_id: Optional[str] = Field("MED-007", description="Target essential medicine identifier (e.g. MED-007, MED-001)")
    options: Optional[Dict[str, Any]] = Field(None, description="Operational overrides, e.g. {'sample_mode': True}")

    model_config = {
        "json_schema_extra": {
            "example": {
                "facility_id": "FAC-DH-01",
                "medicine_id": "MED-007",
                "options": {"sample_mode": True}
            }
        }
    }

class DecisionRequest(BaseModel):
    facility_id: str = Field(..., description="Target facility identifier (e.g. FAC-CHC-01)")
    medicine_id: str = Field(..., description="Target essential medicine identifier (e.g. MED-001)")
    action_type: str = Field(..., description="Action recommendation type (e.g. PEER_TRANSFER, EXPEDITED_PO)")
    decision: str = Field(..., description="Officer decision: APPROVED or REJECTED")
    reason: Optional[str] = Field("", description="Officer clinical or logistics reasoning")

    model_config = {
        "json_schema_extra": {
            "example": {
                "facility_id": "FAC-CHC-01",
                "medicine_id": "MED-001",
                "action_type": "PEER_TRANSFER",
                "decision": "APPROVED",
                "reason": "Route roads clear; vehicle available"
            }
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "MedTrace",
        "sample_mode": orchestrator.llm_client.sample_mode,
        "zetaris_enabled": orchestrator.data_store.use_zetaris
    }

@app.post("/decision")
def api_record_decision(req: DecisionRequest):
    try:
        with _exclusive():
            res = orchestrator.record_decision(
                facility_id=req.facility_id,
                medicine_id=req.medicine_id,
                action_type=req.action_type,
                decision=req.decision,
                reason=req.reason or ""
            )
        return {
            "status": "success",
            "message": f"Officer decision '{req.decision.upper()}' recorded for {req.facility_id} {req.action_type}",
            "memory_state": res
        }
    except HTTPException:
        raise
    except ValueError as ve:
        status_code = 400 if "Invalid decision" in str(ve) else 404
        raise HTTPException(status_code=status_code, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/triage")
def api_triage(facility_id: Optional[str] = None, top_n: int = 10):
    try:
        res = orchestrator.triage_district(facility_id=facility_id, top_n=top_n)
        return {"status": "success", "triage": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run")
def api_run(req: RunRequest):
    with _exclusive():
        return _run_locked(req)


def _run_locked(req: RunRequest):
    start_time = time.time()
    orig_env_sample = os.environ.get("SAMPLE_MODE")
    orig_sample_mode = orchestrator.llm_client.sample_mode
    orig_use_zetaris = orchestrator.data_store.use_zetaris
    if req.options and req.options.get("sample_mode") is not None:
        force_sample = bool(req.options.get("sample_mode"))
        orchestrator.llm_client.sample_mode = force_sample
        os.environ["SAMPLE_MODE"] = "true" if force_sample else "false"
        if force_sample:
            orchestrator.data_store.use_zetaris = False
    elif not (os.environ.get("MODEL_API_KEY") or os.environ.get("METERLESS_RUNTIME_TOKEN")):
        orchestrator.llm_client.sample_mode = True
        orchestrator.data_store.use_zetaris = False
    try:
        pack = orchestrator.run_investigation(
            facility_id=req.facility_id or "FAC-DH-01",
            medicine_id=req.medicine_id or "MED-007"
        )
        duration = round(time.time() - start_time, 2)
        return {
            "run_id": pack.run_id,
            "status": "success",
            "execution_time_seconds": duration,
            "output": pack.model_dump(),
            "agents": [
                {"name": "TriagePlanner", "role": "Scans district portfolio and prioritizes at-risk facilities & medicines"},
                {"name": "Reconciler", "role": "Audits ledger vs physical audit vs batch expiry"},
                {"name": "WorldModel", "role": "Maintains shared canonical grounded entities & relations"},
                {"name": "Investigator", "role": "Generates >= 3 competing hypotheses with evidence queries"},
                {"name": "Skeptic & Number Auditor", "role": "Challenging assertions & verifying deterministic arithmetic"},
                {"name": "ActionPlanner", "role": "Ranks transfers, PO expedites, and emergency orders"},
                {"name": "HMEM", "role": "Cross-session memory of officer approvals/overrides"}
            ],
            "trace_file": pack.trace_file
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        orchestrator.llm_client.sample_mode = orig_sample_mode
        orchestrator.data_store.use_zetaris = orig_use_zetaris
        if req.options and req.options.get("sample_mode") is not None:
            if orig_env_sample is not None:
                os.environ["SAMPLE_MODE"] = orig_env_sample
            else:
                os.environ.pop("SAMPLE_MODE", None)

def _memo_candidates(facility_id: str, medicine_id: str):
    name = f"memo_{facility_id}_{medicine_id}.md"
    dirs = [d for d in (os.environ.get("MEDTRACE_OUTPUT_DIR"), REPO_OUTPUT_DIR) if d]
    return [os.path.join(d, name) for d in dirs]


def _clean_ids(facility_id: str, medicine_id: str):
    fac, med = str(facility_id).strip().upper(), str(medicine_id).strip().upper()
    if not (_SAFE_ID.match(fac) and _SAFE_ID.match(med)):
        raise HTTPException(status_code=400, detail="Invalid facility_id or medicine_id.")
    return fac, med


@app.get("/memo/{facility_id}/{medicine_id}", response_class=PlainTextResponse)
def api_get_memo(facility_id: str, medicine_id: str):
    """Read-only: returns the stored procurement memorandum (Markdown) for a pair. Generate one with POST."""
    fac, med = _clean_ids(facility_id, medicine_id)
    for path in _memo_candidates(fac, med):
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return PlainTextResponse(content=f.read(), media_type="text/markdown")
    raise HTTPException(
        status_code=404,
        detail=f"No stored memo for {fac}/{med}. Generate one with POST /memo/{fac}/{med} (runs a new investigation).",
    )


@app.post("/memo/{facility_id}/{medicine_id}", response_class=PlainTextResponse)
def api_create_memo(facility_id: str, medicine_id: str):
    """Runs a new investigation, stores the memorandum under output/ and returns it as Markdown."""
    fac, med = _clean_ids(facility_id, medicine_id)
    try:
        from scripts.export_action_pack import generate_memorandum
        with _exclusive():
            pack = orchestrator.run_investigation(facility_id=fac, medicine_id=med)
        path = generate_memorandum(pack)
        with open(path, "r", encoding="utf-8") as f:
            return PlainTextResponse(content=f.read(), media_type="text/markdown")
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trace/latest")
def api_get_latest_trace():
    """Retrieves the latest multi-agent deliberation trace as structured events."""
    try:
        import json
        from scripts.explain_trace import find_latest_trace, build_verdict_flip_card
        trace_path = find_latest_trace()
        if not trace_path or not os.path.exists(trace_path):
            raise HTTPException(status_code=404, detail="No trace files found in logs/")
        events = []
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        card = build_verdict_flip_card(events)
        return {
            "status": "success",
            "trace_file": trace_path,
            "events_count": len(events),
            "verdict_flip_card": card,
            "events": events
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trace/verdict-flip")
def api_get_trace_verdict_flip():
    """Retrieves the executive Verdict-Flip Card and counterfactual dissent log for the latest deliberation trace."""
    try:
        import json
        from scripts.explain_trace import find_latest_trace, build_verdict_flip_card
        trace_path = find_latest_trace()
        if not trace_path or not os.path.exists(trace_path):
            raise HTTPException(status_code=404, detail="No trace files found in logs/")
        events = []
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        card = build_verdict_flip_card(events)
        return {
            "status": "success",
            "trace_file": trace_path,
            "verdict_flip_card": card
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def main():
    parser = argparse.ArgumentParser(description="MedTrace Agent Runner")
    parser.add_argument("--cli", action="store_true", help="Run single investigation in CLI mode")
    parser.add_argument("--facility", default="FAC-DH-01", help="Target facility ID")
    parser.add_argument("--medicine", default="MED-007", help="Target medicine ID")
    parser.add_argument("--case", choices=["golden", "standard"], default=None, help="Preset clinical scenario: 'golden' (FAC-CHC-01/MED-001 quarantine stockout) or 'standard' (FAC-DH-01/MED-007)")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    parser.add_argument("--sample-mode", action="store_true", help="Force sample mode offline execution")
    parser.add_argument("--record-decision", action="store_true", help="Record an officer approval/rejection decision into H-MEM")
    parser.add_argument("--action-type", default="PEER_TRANSFER", help="Action type to decide on (e.g. PEER_TRANSFER, EXPEDITE_PO)")
    parser.add_argument("--decision", choices=["APPROVED", "REJECTED", "approved", "rejected"], default="APPROVED", help="Decision (APPROVED or REJECTED)")
    parser.add_argument("--reason", default="Manual officer judgment", help="Reason for decision")
    parser.add_argument("--triage", action="store_true", help="Execute proactive district-wide inventory triage scan")
    parser.add_argument("--auto-triage", action="store_true", help="Proactively scan district and immediately audit top urgent bottleneck")
    parser.add_argument("--top-n", type=int, default=5, help="Number of urgent items to display in triage")
    parser.add_argument("--explain", action="store_true", help="Render executive multi-agent debate timeline after investigation")
    parser.add_argument("--verdict-flip", action="store_true", help="Render executive verdict-flip and counterfactual card after investigation")
    parser.add_argument("--export-memo", action="store_true", help="Export printable Markdown procurement memorandum to output/")
    parser.add_argument("--save-golden", action="store_true", help="Explicitly update the committed canonical golden trace file")
    args = parser.parse_args()

    if not (os.environ.get("MODEL_API_KEY") or os.environ.get("METERLESS_RUNTIME_TOKEN")):
        if "SAMPLE_MODE" not in os.environ or env_bool("SAMPLE_MODE"):
            args.sample_mode = True

    if args.sample_mode:
        os.environ["SAMPLE_MODE"] = "true"
        orchestrator.llm_client.sample_mode = True
        orchestrator.data_store.use_zetaris = False

    if args.case == "golden":
        args.facility = "FAC-CHC-01"
        args.medicine = "MED-001"
        args.cli = True
        print("[*] Preset Case Loaded: GOLDEN CASE (FAC-CHC-01 / MED-001 Paracetamol 500mg QA Quarantine Hold)")
    elif args.case == "standard":
        args.facility = "FAC-DH-01"
        args.medicine = "MED-007"
        args.cli = True
        print("[*] Preset Case Loaded: STANDARD CASE (FAC-DH-01 / MED-007 Metformin 500mg)")

    if args.auto_triage:
        print("[*] Proactive District Triage Scan initiated via TriagePlannerAgent...")
        triage_res = orchestrator.triage_district(top_n=5)
        top_items = triage_res.get("top_urgent_items", [])
        if not top_items:
            print("[!] No urgent bottlenecks identified in district.")
            return
        urgent_target = top_items[0]
        args.facility = urgent_target["facility_id"]
        args.medicine = urgent_target["medicine_id"]
        args.cli = True
        print(f"[+] Proactive Triage routed investigation to highest bottleneck:")
        print(f"    Facility: {args.facility} | Medicine: {args.medicine} ({urgent_target['generic_name']})")
        print(f"    Urgency Tier: {urgent_target['urgency_tier']} | Days of Cover: {urgent_target['trust_cover_days']} d | Shortfall: {urgent_target['shortfall_units']} units\n")

    if args.triage:
        print("[*] Running MedTrace Proactive District Triage Scan...")
        res = orchestrator.triage_district(facility_id=args.facility if args.facility != "FAC-DH-01" else None, top_n=args.top_n)
        print("\n" + "="*80)
        print("MEDTRACE PROACTIVE DISTRICT TRIAGE LEADERBOARD")
        print("="*80)
        print(f"Total Evaluated: {res['total_evaluated']} facility-medicine pairs")
        print(f"Status: {res['critical_count']} CRITICAL | {res['warning_count']} WARNING | {res['secure_count']} SECURE")
        print("-" * 80)
        print(f"{'Facility':<18} | {'Medicine':<16} | {'Cover':<8} | {'Shortfall':<10} | {'Status':<10}")
        print("-" * 80)
        for item in res["top_urgent_items"]:
            print(f"{item['facility_id']:<18} | {item['generic_name'][:16]:<16} | {item['trust_cover_days']:>5.1f} d | {item['shortfall_units']:>6.1f} u | {item['urgency_tier']:<10}")
        print("="*80)
        if res.get("qualitative_synthesis"):
            print(f"Executive Synthesis:\n{res['qualitative_synthesis']}\n")
        return

    if args.record_decision:
        print(f"[*] Recording Officer Decision in H-MEM: Facility={args.facility}, Medicine={args.medicine}, Action={args.action_type}, Decision={args.decision.upper()}...")
        try:
            res = orchestrator.record_decision(
                facility_id=args.facility,
                medicine_id=args.medicine,
                action_type=args.action_type,
                decision=args.decision.upper(),
                reason=args.reason
            )
            print("[+] Successfully recorded officer decision in H-MEM.")
            print(f"    Preference State for {args.facility}_{res['action_type']}: {res['preferences']}")
            print(f"    Active Rejected Patterns: {res['rejected_patterns']}")
        except ValueError as ve:
            print(f"[!] Validation Error: {ve}")
            sys.exit(1)
        return

    if args.cli:
        print(f"[*] Starting MedTrace CLI Investigation: Facility={args.facility}, Medicine={args.medicine}...")
        try:
            pack = orchestrator.run_investigation(facility_id=args.facility, medicine_id=args.medicine)
        except ValueError as ve:
            print(f"[!] Validation Error: {ve}")
            sys.exit(1)
        print("\n" + "="*60)
        print("MEDTRACE ACTION PACK SUMMARY")
        print("="*60)
        print(f"Run ID: {pack.run_id}")
        print(f"Target: Facility {pack.facility_id} | Medicine {pack.medicine_id}")
        print(f"Trust-Adjusted Days of Cover: {pack.days_of_cover_trust} days (Naive was {pack.days_of_cover_naive} days)")
        print(f"Understated Gap: {pack.understated_gap_percent}%")
        print(f"Monte Carlo Stockout Risk: {pack.p_stockout_risk * 100:.1f}%")
        print(f"Winning Hypothesis: {pack.winning_hypothesis.title}")
        print(f"Cause: {pack.winning_hypothesis.cause}")
        print(f"Skeptic Rounds: {pack.skeptic_rounds}")
        print(f"Escalated to Officer: {'YES - ' + (pack.escalation_reason or 'Unresolved multi-agent debate') if pack.escalated_to_human else 'NO (Autonomous Approval)'}")
        print("\nTop Recommended Action:")
        top_act = pack.recommendations[0]
        act_type_str = top_act.action_type.value if hasattr(top_act.action_type, 'value') else str(top_act.action_type)
        print(f"- Type: {act_type_str}")
        print(f"- Recommended Quantity: {top_act.recommended_units} units")
        if top_act.estimated_cost_usd is not None:
            print(f"- Estimated Financial Cost: ${top_act.estimated_cost_usd:.2f} USD")
        print(f"- Justification: {top_act.justification}")
        if len(pack.recommendations) > 1:
            print("\nAlternative Actions:")
            for alt_act in pack.recommendations[1:]:
                alt_type_str = alt_act.action_type.value if hasattr(alt_act.action_type, 'value') else str(alt_act.action_type)
                print(f"- [{alt_type_str}] {alt_act.recommended_units} units: {alt_act.justification}")
        print(f"\nTrace log written to: {pack.trace_file}")
        if getattr(args, "case", None) == "golden" and (getattr(args, "save_golden", False) or os.environ.get("MEDTRACE_SAVE_GOLDEN") == "1"):
            import shutil
            golden_trace_path = os.path.join(orchestrator.logs_dir, "golden_trace_FAC-CHC-01_MED-001.jsonl")
            shutil.copyfile(pack.trace_file, golden_trace_path)
            print(f"[+] Canonical Golden Trace saved: {golden_trace_path}")
        print("="*60)
        if args.explain:
            from scripts.explain_trace import render_trace
            render_trace(pack.trace_file)
        elif getattr(args, "verdict_flip", False):
            from scripts.explain_trace import render_verdict_flip_card
            with open(pack.trace_file, "r", encoding="utf-8") as f:
                trace_events = [json.loads(line) for line in f if line.strip()]
            render_verdict_flip_card(trace_events)
        if args.export_memo:
            from scripts.export_action_pack import generate_memorandum
            memo_path = generate_memorandum(pack)
            print(f"\n[+] Procurement Memorandum exported to: {memo_path}")
    else:
        port = int(os.getenv("PORT", args.port))
        print(f"[*] Starting MedTrace HTTP Server on 0.0.0.0:{port}...")
        uvicorn.run("run:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
