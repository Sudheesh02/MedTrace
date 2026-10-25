# Zetaris Lightning Registration Guide (MEDTRACE_LH)

How MedTrace's simulated facility data is registered in a local **Zetaris Lightning** stack so the agents can read it with SQL. This is the setup that was actually run and verified for the submission.

## 1. What gets registered

One Lightning database, **`MEDTRACE_LH`**, with one FILESTORE (CSV) table per file in `data/simulated/` plus the curated `medicine_master` from `data/real/`:

| Table | Source file | Rows |
| :--- | :--- | ---: |
| `facilities` | `data/simulated/facilities.csv` | 12 |
| `medicine_master` | `data/real/medicine_master.csv` | 12 |
| `suppliers` | `data/simulated/suppliers.csv` | 4 |
| `batches` | `data/simulated/batches.csv` | 291 |
| `ledger_daily` | `data/simulated/ledger_daily.csv` | 25,920 |
| `consumption_daily` | `data/simulated/consumption_daily.csv` | 25,920 |
| `physical_audit` | `data/simulated/physical_audit.csv` | 432 |
| `purchase_orders` | `data/simulated/purchase_orders.csv` | 1,288 |
| `deliveries` | `data/simulated/deliveries.csv` | 1,236 |
| `transfers` | `data/simulated/transfers.csv` | 1 |

`ground_truth.csv` and `true_stock_daily.csv` are **deliberately not registered**: they are evaluation labels and must not be visible to the agents. The real-world reference files (`openfda_shortages.json`, recalls, WHO, DailyMed, RxNorm, `supplier_slip.csv`) are read from local files, not from Zetaris.

## 2. Prerequisites

1. Zetaris platform installed per the participant guide (docker compose: `ui` on `:3000`, `api`, `driver`, `postgres`). On Windows the stack runs in WSL2 + Docker Desktop. If queries fail, start the driver again from the `zetaris-platform` folder: `docker compose up -d driver`.
2. `.env` has `ZETARIS_BASE_URL`, `ZETARIS_ORG_ID`, `ZETARIS_USERNAME`, `ZETARIS_PASSWORD` (see `.env.example`; never commit real values).
3. The `docker` CLI can reach the driver container (default name `zetaris-driver-1`, override with `ZETARIS_DRIVER_CONTAINER`).

## 3. Register (one command)

```bash
python scripts/register_zetaris_medtrace.py                  # all tables
python scripts/register_zetaris_medtrace.py medicine_master  # only the named table(s)
```

[`scripts/register_zetaris_medtrace.py`](register_zetaris_medtrace.py) copies each CSV into the driver container at `/home/zetaris/customer-data/shared/medtrace/<table>/<table>.csv`, then runs:

```sql
CREATE LIGHTNING DATABASE MEDTRACE_LH DESCRIBE BY "MedTrace simulated supply-chain data" OPTIONS ();
CREATE LIGHTNING FILESTORE TABLE ledger_daily FROM MEDTRACE_LH FORMAT csv
  OPTIONS (path "/home/zetaris/customer-data/shared/medtrace/ledger_daily", header "true");
-- ...one statement per table; the script then prints SELECT COUNT(*) FROM MEDTRACE_LH.<table>
```

## 4. How MedTrace queries it

[`app/adapters/data_store.py`](../app/adapters/data_store.py) logs in (`POST /api/auth/login`) and sends SQL to the UI proxy:

```
POST {ZETARIS_BASE_URL}/api/proxy/sql-editor/sqls/run-query
Authorization: Bearer <token>   X-Org-ID: <org>   X-Request-ID: <uuid>
{"sql": "SELECT * FROM MEDTRACE_LH.ledger_daily WHERE facility_id = 'FAC-DH-01' AND medicine_id = 'MED-007' ORDER BY date DESC LIMIT 1", "limit": 1000}
```

Enable it with `USE_ZETARIS=true` (and `SAMPLE_MODE=false`). If Zetaris is unreachable, `DataStore` falls back to the local CSVs, and the fallback is counted.

## 5. Verify it is really being used

```bash
SAMPLE_MODE=false USE_ZETARIS=true python run.py --cli --facility FAC-WH-01 --medicine MED-006
```

Then open the newest `logs/trace_<run_id>.jsonl` and find the `ZetarisDataLayer` / `DATA_SOURCE_SUMMARY` event: `queries_ok` should equal `queries_attempted` and `queries_fallback_to_csv` should be `0`. A committed example is `logs/live_trace_run-2bceed1c.jsonl` (44 of 44 queries answered by Zetaris).