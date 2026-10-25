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
from dotenv import load_dotenv

# Load environment variables prior to package initialization
load_dotenv()

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

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

@app.get("/triage")
def api_triage(facility_id: Optional[str] = None, top_n: int = 10):
    try:
        res = orchestrator.triage_district(facility_id=facility_id, top_n=top_n)
        return {"status": "success", "triage": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run")
def api_run(req: RunRequest):
    start_time = time.time()
    orig_sample_mode = orchestrator.llm_client.sample_mode
    orig_use_zetaris = orchestrator.data_store.use_zetaris
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
        if req.options and req.options.get("sample_mode") is not None:
            orchestrator.llm_client.sample_mode = orig_sample_mode
            orchestrator.data_store.use_zetaris = orig_use_zetaris

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
    parser.add_argument("--triage", action="store_true", help="Execute proactive district-wide inventory triage scan")
    parser.add_argument("--top-n", type=int, default=5, help="Number of urgent items to display in triage")
    parser.add_argument("--explain", action="store_true", help="Render executive multi-agent debate timeline after investigation")
    parser.add_argument("--export-memo", action="store_true", help="Export printable Markdown procurement memorandum to output/")
    args = parser.parse_args()

    if args.sample_mode:
        os.environ["SAMPLE_MODE"] = "true"
        orchestrator.llm_client.sample_mode = True
        orchestrator.data_store.use_zetaris = False

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
        print(f"\nTrace log written to: {pack.trace_file}")
        print("="*60)
        if args.explain:
            from scripts.explain_trace import render_trace
            render_trace(pack.trace_file)
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
