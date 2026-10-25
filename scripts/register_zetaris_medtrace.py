"""Register MedTrace simulated CSVs in a local Zetaris stack as Lightning database MEDTRACE_LH.
Usage (stack already running via zetaris-platform docker compose):
    python scripts/register_zetaris_medtrace.py              # register all tables
    python scripts/register_zetaris_medtrace.py medicine_master   # register only the named table(s)
Copies data/simulated/*.csv into the driver container's shared filesystem root and creates
one FILESTORE table per CSV. ground_truth.csv and true_stock_daily.csv are deliberately NOT
registered (they are evaluation labels, not agent inputs)."""
import os, subprocess, sys, uuid
import requests
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.adapters.data_store import DataStore

TABLES = ["ledger_daily", "facilities", "batches", "physical_audit", "consumption_daily",
          "purchase_orders", "deliveries", "suppliers", "transfers", "medicine_master"]
# Source folder per table (everything is simulated except the curated medicine master).
SRC_DIRS = {"medicine_master": os.path.join("data", "real")}
CONTAINER = os.environ.get("ZETARIS_DRIVER_CONTAINER", "zetaris-driver-1")
ROOT = "/home/zetaris/customer-data/shared/medtrace"
SRC = os.path.join("data", "simulated")

def sh(*a):
    subprocess.run(["docker", "exec", "-u", "root", CONTAINER, "sh", "-c", " ".join(a)], check=True)

def main():
    tables = [t for t in TABLES if t in sys.argv[1:]] if len(sys.argv) > 1 else TABLES
    for t in tables:
        sh(f"mkdir -p {ROOT}/{t}")
        subprocess.run(["docker", "cp", os.path.join(SRC_DIRS.get(t, SRC), f"{t}.csv"), f"{CONTAINER}:{ROOT}/{t}/{t}.csv"], check=True)
    sh(f"chmod -R a+rwX {ROOT} && chgrp -R zetaris {ROOT}")
    ds = DataStore(use_zetaris=True)
    token = ds._get_token()
    if not token:
        sys.exit("Zetaris login failed - check ZETARIS_* in .env")
    url = ds.base_url + "/api/proxy/sql-editor/sqls/run-query"
    hdr = {"Authorization": f"Bearer {token}", "X-Org-ID": str(ds.zetaris_org), "X-Request-ID": str(uuid.uuid4())}
    def q(sql):
        return requests.post(url, headers=hdr, json={"sql": sql, "limit": 5}, timeout=180)
    q('CREATE LIGHTNING DATABASE MEDTRACE_LH DESCRIBE BY "MedTrace simulated supply-chain data" OPTIONS ()')
    for t in tables:
        q(f'CREATE LIGHTNING FILESTORE TABLE {t} FROM MEDTRACE_LH FORMAT csv OPTIONS (path "{ROOT}/{t}", header "true")')
        r = q(f"SELECT COUNT(*) AS n FROM MEDTRACE_LH.{t}")
        print(t, r.status_code, r.json().get("data") if r.ok else r.text[:100])

if __name__ == "__main__":
    main()