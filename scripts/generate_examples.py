"""
Generate 3 input examples and execute them through MedTrace to produce 3 output examples.
Fulfills Technical Execution Requirement: Section 1 (Examples).
Synchronized with FastAPI POST /run response contract.
"""

import os
import sys
import json
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.orchestrator import MedTraceOrchestrator

SAMPLES = [
    {
        "filename": "sample_1_district_hospital_metformin.json",
        "input": {
            "facility_id": "FAC-DH-01",
            "medicine_id": "MED-007",
            "description": "District Hospital Metformin stock check: Ledger shows healthy balance, but physical audits indicate phantom stock."
        }
    },
    {
        "filename": "sample_2_phc_amoxicillin_expiring.json",
        "input": {
            "facility_id": "FAC-PHC-01",
            "medicine_id": "MED-004",
            "description": "Primary Health Centre Amoxicillin: Active batch expiring within lead time window."
        }
    },
    {
        "filename": "sample_3_chc_paracetamol_quarantine.json",
        "input": {
            "facility_id": "FAC-CHC-01",
            "medicine_id": "MED-001",
            "description": "Community Health Centre Paracetamol: Batch flagged under quality control quarantine hold."
        }
    }
]

def main():
    os.makedirs("input_examples", exist_ok=True)
    os.makedirs("output_examples", exist_ok=True)

    orchestrator = MedTraceOrchestrator(use_zetaris=False)

    for item in SAMPLES:
        fname = item["filename"]
        inp = item["input"]
        
        # Write input example
        in_path = os.path.join("input_examples", fname)
        with open(in_path, "w", encoding="utf-8") as f:
            json.dump(inp, f, indent=2)
        print(f"[+] Wrote {in_path}")

        # Execute investigation
        start_time = time.time()
        pack = orchestrator.run_investigation(
            facility_id=inp["facility_id"],
            medicine_id=inp["medicine_id"]
        )
        duration = round(time.time() - start_time, 2)

        out_data = {
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

        out_path = os.path.join("output_examples", fname)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"[+] Wrote {out_path}")

if __name__ == "__main__":
    main()
