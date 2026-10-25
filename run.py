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
import time
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.orchestrator import MedTraceOrchestrator

app = FastAPI(title="MedTrace AI Agent API", version="1.0.0")
orchestrator = MedTraceOrchestrator()

class RunRequest(BaseModel):
    facility_id: Optional[str] = "FAC-DH-01"
    medicine_id: Optional[str] = "MED-007"
    options: Optional[Dict[str, Any]] = None

class DecisionRequest(BaseModel):
    facility_id: str
    medicine_id: str
    action_type: str
    decision: str
    reason: Optional[str] = ""

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
    except ValueError as ve:
        status_code = 400 if "Invalid decision" in str(ve) else 404
        raise HTTPException(status_code=status_code, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run")
def api_run(req: RunRequest):
    start_time = time.time()
    if req.options and req.options.get("sample_mode") is not None:
        force_sample = bool(req.options.get("sample_mode"))
        orchestrator.llm_client.sample_mode = force_sample
        if force_sample:
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
        duration = round(time.time() - start_time, 2)
        return {
            "status": "error",
            "execution_time_seconds": duration,
            "error": {"type": type(e).__name__, "message": str(e)}
        }

def main():
    parser = argparse.ArgumentParser(description="MedTrace Agent Runner")
    parser.add_argument("--cli", action="store_true", help="Run single investigation in CLI mode")
    parser.add_argument("--facility", default="FAC-DH-01", help="Target facility ID")
    parser.add_argument("--medicine", default="MED-007", help="Target medicine ID")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    parser.add_argument("--sample-mode", action="store_true", help="Force sample mode offline execution")
    parser.add_argument("--record-decision", action="store_true", help="Record an officer approval/rejection decision into H-MEM")
    parser.add_argument("--action-type", default="PEER_TRANSFER", help="Action type to decide on (e.g. PEER_TRANSFER, EXPEDITE_PO)")
    parser.add_argument("--decision", choices=["APPROVED", "REJECTED", "approved", "rejected"], default="APPROVED", help="Decision (APPROVED or REJECTED)")
    parser.add_argument("--reason", default="Manual officer judgment", help="Reason for decision")
    args = parser.parse_args()

    if args.sample_mode:
        os.environ["SAMPLE_MODE"] = "true"
        orchestrator.llm_client.sample_mode = True
        orchestrator.data_store.use_zetaris = False

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
        print("\nTop Recommended Action:")
        top_act = pack.recommendations[0]
        act_type_str = top_act.action_type.value if hasattr(top_act.action_type, 'value') else str(top_act.action_type)
        print(f"- Type: {act_type_str}")
        print(f"- Recommended Quantity: {top_act.recommended_units} units")
        print(f"- Justification: {top_act.justification}")
        print(f"\nTrace log written to: {pack.trace_file}")
        print("="*60)
    else:
        port = int(os.getenv("PORT", args.port))
        print(f"[*] Starting MedTrace HTTP Server on 0.0.0.0:{port}...")
        uvicorn.run("run.py:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
