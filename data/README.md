# MedTrace — Data Provenance & Inventory (DC-10)

This directory contains real, curated, and calibrated simulated datasets used by the MedTrace agent system for stockout prevention, discrepancy reconciliation, and root-cause explanation.

---

## 1. Data Origin Summary

| Dataset ID | Dataset Name | File Path | Origin Type | Source / Authority | Row Count | Purpose in MedTrace |
|---|---|---|---|---|---|---|
| **DC-1** | Medicine Master | `data/real/medicine_master.csv` | **CURATED** | WHO Model List of Essential Medicines (EML) & India NLEM | 12 | Standardizes 12 essential medicines (OPD staples + programme commodities), dosages, ATC codes, care levels |
| **DC-2** | USAID Delivery History | `data/real/raw/usaid_deliveries.csv` | **REAL** | USAID GHSC-PSM Commodity Delivery Dataset | 10,324 | Ground truth empirical delivery dates vs scheduled dates, real vendors, logistics modes |
| **DC-3** | Supplier Slip Priors | `data/real/supplier_slip.csv` | **DERIVED** | Computed from DC-2 grouped by vendor & shipment mode | 34 | Informs Monte Carlo lead time and delay probability calculations |
| **DC-4** | openFDA Drug Shortages | `data/real/openfda_shortages.json` | **REAL (live API)** | US FDA Open Data API (`api.fda.gov/drug/shortages.json`) | 1,611 | External global supply disruption signal and manufacturer shortage status |
| **DC-4b** | openFDA Enforcement Recalls | `data/real/openfda_enforcement_recalls.json` | **REAL (live API)** | US FDA Recall Enterprise System (RES) via openFDA API | 189 | Real Class I, II, III recalls and lot numbers directly explaining `QUARANTINED_BATCH` holds |
| **DC-1b** | NIH RxNorm Standards | `data/real/rxnorm_standards.json` | **REAL** | US National Library of Medicine (NLM / NIH) | 12 | Standard clinical identifiers (RxCUIs) and UOM dose forms preventing `UOM_MISMATCH` |
| **DC-1c** | DailyMed Packaging & Cold Chain | `data/real/dailymed_packaging.json` | **REAL** | NIH / US FDA Structured Product Labeling (SPL) | 12 | Official temperature storage requirements ($2\text{--}8^\circ\text{C}$ cold chain vs $15\text{--}30^\circ\text{C}$) and packaging norms |
| **DC-5** | Pharma Sales Daily | `data/real/raw/salesdaily.csv` & `data/real/demand_shapes.csv` | **REAL** | Kaggle Pharma Sales Daily (Zdravković / SaibalPatraDS) | 2,106 | Real daily seasonality, spikes, and consumption multiplier curves across 8 ATC groups |
| **DC-7** | Facility Simulation Layer | `data/simulated/*.csv` | **SIMULATED** | Calibrated Python simulator (`scripts/generate_facility_simulation.py`) | ~122,000 | 180 days of facility stock, audits, batches, POs, deliveries, and 10 planted discrepancy anomalies |

---

## 2. Table Schemas & Labeling

### Honesty & Labeling Rule
- Every simulated row explicitly carries `source = 'SIMULATED'`.
- `true_stock_daily.csv` and `ground_truth.csv` are read **only** by the backtest evaluation harness and are **never** exposed to LLM agents or Zetaris queries.

### Key Simulated Tables (`data/simulated/`):
- `facilities.csv`: 1 District Hospital, 3 CHCs, 6 PHCs, 2 Warehouses.
- `suppliers.csv`: 4 Suppliers linked to top real vendors from DC-3.
- `batches.csv`: Batch numbers, expiry dates, quarantine flags.
- `ledger_daily.csv`: Ledger recorded stock levels across 180 days.
- `physical_audit.csv`: Periodic physical stock count audits.
- `consumption_daily.csv`: Daily units dispensed per facility and medicine.
- `purchase_orders.csv`: Purchase orders, promised dates, and statuses.
- `deliveries.csv`: Actual delivery receipts and quantities.
- `ground_truth.csv`: Benchmark record of planted anomalies.
- `true_stock_daily.csv`: Actual ground truth physical stock (isolated from agents).

---

## 3. How to Regenerate

```bash
# 1. Download real datasets (openFDA, USAID, Pharma Sales)
python scripts/download_real_data.py

# 2. Build Curated Medicine Master (DC-1)
python scripts/build_medicine_master.py

# 3. Process Supplier Slip Priors (DC-3) & Demand Shapes (DC-5)
python scripts/process_real_data.py

# 4. Fetch Enriched Real Data (openFDA Recalls, NIH RxNorm, DailyMed)
python scripts/fetch_enriched_real_data.py

# 5. Generate Calibrated Simulated Facility Layer (DC-7)
python scripts/generate_facility_simulation.py
```
