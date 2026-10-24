"""
Generate 3 input examples and execute them through MedTrace to produce 3 output examples.
Fulfills Technical Execution Requirement: Section 1 (Examples).
"""

import os
import sys
import json
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
        pack = orchestrator.run_investigation(
            facility_id=inp["facility_id"],
            medicine_id=inp["medicine_id"]
        )

        out_data = {
            "run_id": pack.run_id,
            "status": "success",
            "facility_id": pack.facility_id,
            "medicine_id": pack.medicine_id,
            "days_of_cover_trust": pack.days_of_cover_trust,
            "days_of_cover_naive": pack.days_of_cover_naive,
            "understated_gap_percent": pack.understated_gap_percent,
            "winning_hypothesis": pack.winning_hypothesis.model_dump(),
            "recommendations": [r.model_dump() for r in pack.recommendations],
            "skeptic_rounds": pack.skeptic_rounds,
            "trace_file": pack.trace_file
        }

        out_path = os.path.join("output_examples", fname)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"[+] Wrote {out_path}")

if __name__ == "__main__":
    main()
