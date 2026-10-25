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
| **DC-1c** | DailyMed Packaging & Cold Chain | `data/real/dailymed_packaging.json` | **CURATED / RULE-ASSIGNED** | NIH / US FDA Structured Product Labeling (SPL) | 12 | Official product names with rule-assigned storage conditions ($2\text{--}8^\circ\text{C}$ cold chain vs $15\text{--}30^\circ\text{C}$) and packaging norms |
| **DC-1d** | WHO Disease Surveillance | `data/real/who_disease_surveillance.json` | **REAL (live API)** | WHO Global Health Observatory (GHO) Athena OData API | 3 indicators | Epidemiological risk indicators (malaria, meningitis, HIV) mapped to essential medicines |
| **DC-5** | Pharma Sales Daily | `data/real/raw/salesdaily.csv` & `data/real/demand_shapes.csv` | **REAL** | Kaggle Pharma Sales Daily (Zdravković / SaibalPatraDS) | 2,106 | Real daily seasonality, spikes, and consumption multiplier curves across 8 ATC groups |
| **DC-7** | Facility Simulation Layer | `data/simulated/*.csv` | **SIMULATED** | Calibrated Python simulator (`scripts/generate_facility_simulation.py`) | ~122,000 | 180 days of facility stock, audits, batches, POs, deliveries, and 10 planted discrepancy anomalies |

---

## 2. Explicit Modeling Assumptions

To preserve total transparency, all synthetic modeling assumptions, heuristic parameters, and rule assignments in MedTrace are explicitly declared below:

1. **WHO Disease Surveillance Demand Multipliers**:
   - *Real Input*: Real disease incidence rates queried from the WHO Global Health Observatory Athena OData API (`who_disease_surveillance.json`).
   - *Calibrated Assumption*: When an indicator is flagged as `ELEVATED` risk tier (e.g. seasonal malaria surge or meningitis epidemic), `DeterministicEngine` applies a calibrated +35% demand multiplier (`who_surveillance_multiplier = 1.35`) to adjust required replenishment buffer.

2. **DailyMed Packaging & Cold Chain Storage**:
   - *Real Input*: Product descriptions and commercial drug names queried from the NIH DailyMed API (`dailymed_packaging.json`).
   - *Calibrated Assumption*: Cold chain requirements ($2^\circ\text{C}$ to $8^\circ\text{C}$) are rule-assigned based on drug classification (e.g., vaccines, insulin), while other oral medications default to controlled room temperature ($15^\circ\text{C}$ to $30^\circ\text{C}$). Packaging formats default to standard 10x10 blister packs (100 units/box) for tablets and capsules.

3. **USAID Supplier Slip Priors & Monte Carlo Transit Delays**:
   - *Real Input*: Empirical delivery delay distributions computed from 10,324 historical USAID GHSC-PSM shipments (`supplier_slip.csv`), grouping by vendor and logistics transit mode (`mean`, `p50`, `p90`, `min`, `max`).
   - *Calibrated Assumption*: Real vendor slip percentiles are mapped to simulated suppliers, and delivery arrival uncertainty is modeled in `DeterministicEngine` via Monte Carlo sampling across empirical slip bounds $[0.0, 0.5 \times p90, 1.0 \times p90, 1.5 \times p90]$.

4. **Empirical Direct Purchase Order Lead-Time Distribution Calibration**:
   - *Real Input*: Direct purchase orders shipped from manufacturers to client facilities (`Fulfill Via = 'Direct Drop'`) in USAID delivery history (`usaid_deliveries.csv`), comprising 4,920 consignments (47.7% of all procurement records) and 4,587 valid order-to-delivery date pairs.
   - *Empirical Quantiles*: Order-to-Delivery Lead Time has Median (P50) = 92.0 days, Interquartile Range (IQR) = 93.0 days (P25: 50.0d → P75: 143.0d), Mean = 105.80 days (Std: 79.28d), P90 = 208.0 days, P95 = 270.7 days, Range: [0 .. 616] days. Scheduled delivery date slip has Mean = +0.78 days, Median = 0.0 days, IQR = 0.0 days (P90 = 0.0d, P95 = 1.0d, Range: [-57 .. 150] days).

---

## 3. Table Schemas & Labeling

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

## 4. How to Regenerate

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
