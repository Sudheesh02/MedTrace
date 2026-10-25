"""
Read-only helper for the MedTrace dashboard.
Runs the project's own deterministic TriagePlannerAgent.triage_pair() over every
facility x medicine pair using the local data files (data/simulated). No LLM, no network,
no writes. Prints a JSON document to stdout.
"""
import os, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.environ["SAMPLE_MODE"] = "true"
os.environ["USE_ZETARIS"] = "false"

from app.adapters.data_store import DataStore  # noqa: E402
from app.agents.triage_planner import TriagePlannerAgent  # noqa: E402

ds = DataStore(use_zetaris=False)
planner = TriagePlannerAgent(ds, None)
facilities = ds.get_facilities()
medicines = ds.get_medicines()
items = []
for fac in facilities:
    for med in medicines:
        items.append(planner.triage_pair(fac["facility_id"], med["medicine_id"], fac_meta=fac, med_meta=med))
items.sort(key=lambda x: (x["urgency_score"], -x["trust_cover_days"]), reverse=True)
print(json.dumps({
    "sim_dir": ds.sim_dir,
    "facilities": len(facilities),
    "medicines": len(medicines),
    "items": items,
}))
