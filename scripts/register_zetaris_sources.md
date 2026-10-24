# Zetaris Lightning Data Source Registration Guide

This document defines the exact commands, endpoints, and SQL statements used to register heterogeneous clinical supply chain datasets into **Zetaris Lightning Federated SQL** for MedTrace.

---

## 🏛 1. Architecture Overview

MedTrace utilizes Zetaris as its federated data layer to query across:
1. **Warehouse & Facility Ledgers** (`data/simulated/ledger_daily.csv`, `consumption_daily.csv`)
2. **Batch & Quarantine Registries** (`data/simulated/batches.csv`)
3. **Physical Shelf Audits** (`data/simulated/physical_audit.csv`)
4. **Logistics & Supplier Deliveries** (`data/simulated/purchase_orders.csv`, `deliveries.csv`)
5. **Real-World Global Registries** (`data/real/supplier_slip.csv`, `openfda_shortages.json`, `cross_border_shortages.json`)

---

## 🔑 2. Authentication & Session Setup

### Login via Zetaris REST API
```bash
curl -X POST "http://localhost:3000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@zetaris.com", "password": "YourPassword"}'
```
Response:
```json
{
  "idToken": "eyJhbGciOiJIUzI1NiIsIn...",
  "orgId": "1",
  "expiresIn": 86400
}
```

---

## 📊 3. Registering Local CSV / Parquet Data Sources

### Option A: Via Zetaris Web UI
1. Navigate to `http://localhost:3000/datasources`
2. Click **Add New Data Source**
3. Select **File System / Mounted Volume**
4. Set path: `/data/simulated`
5. Click **Discover Tables & Schemas**
6. Save as `zetaris.lightning`

### Option B: Via Zetaris Lightning DDL
Execute via the SQL Query API:
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS zetaris.lightning.facilities (
    facility_id VARCHAR(32),
    name VARCHAR(128),
    level VARCHAR(16),
    parent_facility_id VARCHAR(32),
    lead_time_days FLOAT
)
USING CSV
OPTIONS (path '/data/simulated/facilities.csv', header 'true');

CREATE EXTERNAL TABLE IF NOT EXISTS zetaris.lightning.ledger_daily (
    date VARCHAR(16),
    facility_id VARCHAR(32),
    medicine_id VARCHAR(32),
    ledger_stock FLOAT,
    source VARCHAR(32)
)
USING CSV
OPTIONS (path '/data/simulated/ledger_daily.csv', header 'true');

CREATE EXTERNAL TABLE IF NOT EXISTS zetaris.lightning.batches (
    batch_id VARCHAR(32),
    facility_id VARCHAR(32),
    medicine_id VARCHAR(32),
    quantity FLOAT,
    expiry_date VARCHAR(16),
    quarantined BOOLEAN,
    source VARCHAR(32)
)
USING CSV
OPTIONS (path '/data/simulated/batches.csv', header 'true');

CREATE EXTERNAL TABLE IF NOT EXISTS zetaris.lightning.physical_audit (
    audit_id VARCHAR(32),
    date VARCHAR(16),
    facility_id VARCHAR(32),
    medicine_id VARCHAR(32),
    counted_stock FLOAT,
    auditor_notes VARCHAR(256),
    source VARCHAR(32)
)
USING CSV
OPTIONS (path '/data/simulated/physical_audit.csv', header 'true');
```

---

## ⚡ 4. Executing Federated Queries via Python Adapter

MedTrace's [`app/adapters/data_store.py`](../app/adapters/data_store.py) automatically authenticates and routes queries to Zetaris via:
```python
POST http://localhost:3000/api/proxy/sql-editor/sqls/run-query
Headers:
  Authorization: Bearer <TOKEN>
  X-Org-ID: 1
  X-Request-ID: <UUID>
Body:
  {"sql": "SELECT ledger_stock FROM zetaris.lightning.ledger_daily WHERE facility_id = 'FAC-DH-01' AND medicine_id = 'MED-007' ORDER BY date DESC LIMIT 1"}
```

If Zetaris is offline or unreachable, `DataStore` seamlessly falls back to local CSV files without application interruption.
