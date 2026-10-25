# MedTrace Comprehensive Empirical Data Audit (DATA_AUDIT.md)

> **Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why**  
> *Audited on: 2026-10-25 12:15:49 UTC | Strict Empirical Grounding — Zero Invented Numbers*

---

## 📌 1. Master Inventory of Audited Datasets

| Dataset Path | Format | Rows | Columns | File Size | Duplicates | Date Range |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `data/real/cross_border_shortages.json` | JSON | 12 | 8 | 3.9 KB | 0 (0.0%) | N/A |
| `data/real/dailymed_packaging.json` | JSON | 12 | 7 | 6.4 KB | 0 (0.0%) | N/A |
| `data/real/demand_shapes.csv` | CSV | 2,106 | 9 | 115.3 KB | 0 (0.0%) | 2014-01-02 → 2019-12-09 |
| `data/real/medicine_master.csv` | CSV | 12 | 11 | 1.8 KB | 0 (0.0%) | N/A |
| `data/real/openfda_enforcement_recalls.json` | JSON | 3 | 5 | 348.0 KB | 0 (0.0%) | 2026-10-24 → 2026-10-24 |
| `data/real/openfda_shortages.json` | JSON | 1,611 | 14 | 2850.2 KB | 1 (0.06%) | 2012-01-01 → 2026-12-06 |
| `data/real/raw/cleaned_salesdaily.csv` | CSV | 2,106 | 9 | 97.1 KB | 0 (0.0%) | 2014-01-02 → 2019-12-09 |
| `data/real/raw/cleaned_usaid_deliveries.csv` | CSV | 10,324 | 10 | 1280.5 KB | 0 (0.0%) | 2006-05-02 → 2015-12-31 |
| `data/real/raw/salesdaily.csv` | CSV | 2,106 | 13 | 115.1 KB | 0 (0.0%) | 2014-01-02 → 2019-12-09 |
| `data/real/raw/usaid_deliveries.csv` | CSV | 10,324 | 33 | 3697.2 KB | 0 (0.0%) | N/A |
| `data/real/rxnorm_standards.json` | JSON | 12 | 8 | 2.8 KB | 0 (0.0%) | N/A |
| `data/real/supplier_slip.csv` | CSV | 36 | 8 | 1.9 KB | 0 (0.0%) | N/A |
| `data/real/who_disease_surveillance.json` | JSON | 3 | 8 | 2.5 KB | 0 (0.0%) | N/A |
| `data/simulated/batches.csv` | CSV | 291 | 7 | 16.9 KB | 0 (0.0%) | 2026-10-29 → 2028-06-15 |
| `data/simulated/consumption_daily.csv` | CSV | 25,920 | 5 | 1094.5 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated/deliveries.csv` | CSV | 1,236 | 7 | 74.5 KB | 0 (0.0%) | 2026-05-11 → 2026-10-24 |
| `data/simulated/facilities.csv` | CSV | 12 | 5 | 0.7 KB | 0 (0.0%) | N/A |
| `data/simulated/ground_truth.csv` | CSV | 10 | 8 | 1.5 KB | 0 (0.0%) | N/A |
| `data/simulated/ledger_daily.csv` | CSV | 25,920 | 5 | 1139.1 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated/physical_audit.csv` | CSV | 432 | 7 | 36.4 KB | 0 (0.0%) | 2026-06-27 → 2026-10-10 |
| `data/simulated/purchase_orders.csv` | CSV | 1,288 | 9 | 102.9 KB | 0 (0.0%) | 2026-05-05 → 2026-10-24 |
| `data/simulated/suppliers.csv` | CSV | 4 | 7 | 0.4 KB | 0 (0.0%) | N/A |
| `data/simulated/transfers.csv` | CSV | 1 | 9 | 0.2 KB | 0 (0.0%) | 2026-10-15 → 2026-10-15 |
| `data/simulated/true_stock_daily.csv` | CSV | 25,920 | 5 | 1139.1 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_2/batches.csv` | CSV | 291 | 7 | 16.9 KB | 0 (0.0%) | 2026-10-29 → 2028-06-12 |
| `data/simulated_seed_2/consumption_daily.csv` | CSV | 25,920 | 5 | 1094.5 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_2/deliveries.csv` | CSV | 1,281 | 7 | 77.3 KB | 0 (0.0%) | 2026-05-11 → 2026-10-24 |
| `data/simulated_seed_2/facilities.csv` | CSV | 12 | 5 | 0.7 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_2/ground_truth.csv` | CSV | 10 | 8 | 1.5 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_2/ledger_daily.csv` | CSV | 25,920 | 5 | 1138.4 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_2/physical_audit.csv` | CSV | 432 | 7 | 36.4 KB | 0 (0.0%) | 2026-06-27 → 2026-10-10 |
| `data/simulated_seed_2/purchase_orders.csv` | CSV | 1,373 | 9 | 109.7 KB | 0 (0.0%) | 2026-05-05 → 2026-10-24 |
| `data/simulated_seed_2/suppliers.csv` | CSV | 4 | 7 | 0.4 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_2/transfers.csv` | CSV | 1 | 9 | 0.2 KB | 0 (0.0%) | 2026-10-15 → 2026-10-15 |
| `data/simulated_seed_2/true_stock_daily.csv` | CSV | 25,920 | 5 | 1138.4 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_3/batches.csv` | CSV | 291 | 7 | 16.9 KB | 0 (0.0%) | 2026-10-29 → 2028-06-15 |
| `data/simulated_seed_3/consumption_daily.csv` | CSV | 25,920 | 5 | 1094.5 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_3/deliveries.csv` | CSV | 1,220 | 7 | 73.6 KB | 0 (0.0%) | 2026-05-11 → 2026-10-24 |
| `data/simulated_seed_3/facilities.csv` | CSV | 12 | 5 | 0.7 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_3/ground_truth.csv` | CSV | 10 | 8 | 1.5 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_3/ledger_daily.csv` | CSV | 25,920 | 5 | 1139.2 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_3/physical_audit.csv` | CSV | 432 | 7 | 36.4 KB | 0 (0.0%) | 2026-06-27 → 2026-10-10 |
| `data/simulated_seed_3/purchase_orders.csv` | CSV | 1,292 | 9 | 103.2 KB | 0 (0.0%) | 2026-05-05 → 2026-10-24 |
| `data/simulated_seed_3/suppliers.csv` | CSV | 4 | 7 | 0.4 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_3/transfers.csv` | CSV | 1 | 9 | 0.2 KB | 0 (0.0%) | 2026-10-15 → 2026-10-15 |
| `data/simulated_seed_3/true_stock_daily.csv` | CSV | 25,920 | 5 | 1139.2 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_4/batches.csv` | CSV | 291 | 7 | 16.9 KB | 0 (0.0%) | 2026-10-29 → 2028-06-07 |
| `data/simulated_seed_4/consumption_daily.csv` | CSV | 25,920 | 5 | 1094.5 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_4/deliveries.csv` | CSV | 1,249 | 7 | 75.3 KB | 0 (0.0%) | 2026-05-11 → 2026-10-24 |
| `data/simulated_seed_4/facilities.csv` | CSV | 12 | 5 | 0.7 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_4/ground_truth.csv` | CSV | 10 | 8 | 1.5 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_4/ledger_daily.csv` | CSV | 25,920 | 5 | 1138.9 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |
| `data/simulated_seed_4/physical_audit.csv` | CSV | 432 | 7 | 36.4 KB | 0 (0.0%) | 2026-06-27 → 2026-10-10 |
| `data/simulated_seed_4/purchase_orders.csv` | CSV | 1,311 | 9 | 104.7 KB | 0 (0.0%) | 2026-05-05 → 2026-10-24 |
| `data/simulated_seed_4/suppliers.csv` | CSV | 4 | 7 | 0.4 KB | 0 (0.0%) | N/A |
| `data/simulated_seed_4/transfers.csv` | CSV | 1 | 9 | 0.2 KB | 0 (0.0%) | 2026-10-15 → 2026-10-15 |
| `data/simulated_seed_4/true_stock_daily.csv` | CSV | 25,920 | 5 | 1138.9 KB | 0 (0.0%) | 2026-04-28 → 2026-10-24 |

---

## 🔬 2. Real-World Datasets (`data/real/`) Detailed Column Profiles

### Dataset: `data/real/cross_border_shortages.json`
- **Total Records**: 12 rows | **Total Columns**: 8 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `generic_name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `primary_search_term` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `active_shortage_flag` | integer | 0 (0.0%) | 91.67% | 1 (8.33%) | 1 (8.33%) | [0.0 .. 1.0], med=0.0 |
| `root_cause_classification` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `regulatory_records_found` | integer | 0 (0.0%) | 66.67% | 1 (8.33%) | 0 (0.0%) | [0.0 .. 6.0], med=0.0 |
| `reported_reasons` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `multi_country_impact` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `_id` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |

### Dataset: `data/real/dailymed_packaging.json`
- **Total Records**: 12 rows | **Total Columns**: 7 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `generic_name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `daily_med_records_found` | integer | 0 (0.0%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [1.0 .. 100.0], med=26.0 |
| `sample_commercial_products` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `storage_condition` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `standard_packaging` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `dispensing_unit` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `_id` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |

### Dataset: `data/real/demand_shapes.csv`
- **Total Records**: 2,106 rows | **Total Columns**: 9 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `datum` | date | 0 (0.0%) | N/A | N/A | N/A | 2014-01-02 .. 2019-12-09 |
| `M01AB_multiplier` | float | 0 (0.0%) | 1.9% | 26 (1.23%) | 17 (0.81%) | [0.0 .. 3.445], med=0.99 |
| `M01AE_multiplier` | float | 0 (0.0%) | 1.71% | 40 (1.9%) | 25 (1.19%) | [0.0 .. 3.712], med=0.94 |
| `N02BA_multiplier` | float | 0 (0.0%) | 3.7% | 31 (1.47%) | 20 (0.95%) | [0.0 .. 4.123], med=0.9 |
| `N02BE_multiplier` | float | 0 (0.0%) | 1.23% | 48 (2.28%) | 22 (1.04%) | [0.0 .. 5.382], med=0.9 |
| `N05B_multiplier` | float | 0 (0.0%) | 2.04% | 48 (2.28%) | 25 (1.19%) | [0.0 .. 6.193], med=0.9 |
| `N05C_multiplier` | float | 0 (0.0%) | 67.9% | 160 (7.6%) | 46 (2.18%) | [0.0 .. 15.164], med=0.0 |
| `R03_multiplier` | float | 0 (0.0%) | 22.98% | 124 (5.89%) | 43 (2.04%) | [0.0 .. 8.164], med=0.73 |
| `R06_multiplier` | float | 0 (0.0%) | 12.16% | 83 (3.94%) | 26 (1.23%) | [0.0 .. 5.172], med=0.69 |

### Dataset: `data/real/medicine_master.csv`
- **Total Records**: 12 rows | **Total Columns**: 11 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `medicine_id` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `generic_name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `rxcui` | integer | 0 (0.0%) | 0.0% | 2 (16.67%) | 1 (8.33%) | [161.0 .. 195085.0], med=6591.0 |
| `strength` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `form` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `atc_code` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `level_min` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `shelf_life_months` | integer | 0 (0.0%) | 0.0% | 3 (25.0%) | 0 (0.0%) | [24.0 .. 36.0], med=36.0 |
| `demand_group` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `supply_group` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `source_url` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |

### Dataset: `data/real/openfda_enforcement_recalls.json`
- **Total Records**: 3 rows | **Total Columns**: 5 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `source` | string | 2 (66.67%) | N/A | N/A | N/A | N/A |
| `total_curated_records` | integer | 2 (66.67%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [189.0 .. 189.0], med=189.0 |
| `generated_at` | date | 2 (66.67%) | N/A | N/A | N/A | 2026-10-24 .. 2026-10-24 |
| `medicines_covered` | integer | 2 (66.67%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [12.0 .. 12.0], med=12.0 |
| `_id` | string | 1 (33.33%) | N/A | N/A | N/A | N/A |

### Dataset: `data/real/openfda_shortages.json`
- **Total Records**: 1,611 rows | **Total Columns**: 14 | **Duplicate Rows**: 1 (0.06%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `update_type` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `initial_posting_date` | date | 0 (0.0%) | N/A | N/A | N/A | 2012-01-01 .. 2026-12-06 |
| `package_ndc` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `generic_name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `contact_info` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `availability` | string | 469 (29.11%) | N/A | N/A | N/A | N/A |
| `related_info` | string | 501 (31.1%) | N/A | N/A | N/A | N/A |
| `openfda` | string | 301 (18.68%) | N/A | N/A | N/A | N/A |
| `update_date` | date | 0 (0.0%) | N/A | N/A | N/A | 2023-04-28 .. 2026-12-05 |
| `therapeutic_category` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `dosage_form` | string | 10 (0.62%) | N/A | N/A | N/A | N/A |
| `presentation` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `company_name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `status` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |

### Dataset: `data/real/raw/cleaned_salesdaily.csv`
- **Total Records**: 2,106 rows | **Total Columns**: 9 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `datum` | date | 0 (0.0%) | N/A | N/A | N/A | 2014-01-02 .. 2019-12-09 |
| `M01AB` | float | 0 (0.0%) | 1.9% | 26 (1.23%) | 17 (0.81%) | [0.0 .. 17.34], med=4.99 |
| `M01AE` | float | 0 (0.0%) | 1.71% | 40 (1.9%) | 25 (1.19%) | [0.0 .. 14.463], med=3.67 |
| `N02BA` | float | 0 (0.0%) | 3.7% | 31 (1.47%) | 20 (0.95%) | [0.0 .. 16.0], med=3.5 |
| `N02BE` | float | 0 (0.0%) | 1.23% | 48 (2.28%) | 22 (1.04%) | [0.0 .. 161.0], med=26.9 |
| `N05B` | float | 0 (0.0%) | 2.04% | 48 (2.28%) | 25 (1.19%) | [0.0 .. 54.83333333], med=8.0 |
| `N05C` | float | 0 (0.0%) | 67.9% | 160 (7.6%) | 46 (2.18%) | [0.0 .. 9.0], med=0.0 |
| `R03` | float | 0 (0.0%) | 22.98% | 124 (5.89%) | 43 (2.04%) | [0.0 .. 45.0], med=4.0 |
| `R06` | float | 0 (0.0%) | 12.16% | 81 (3.85%) | 26 (1.23%) | [0.0 .. 15.0], med=2.0 |

### Dataset: `data/real/raw/cleaned_usaid_deliveries.csv`
- **Total Records**: 10,324 rows | **Total Columns**: 10 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `line_id` | integer | 0 (0.0%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [1.0 .. 86823.0], med=57540.5 |
| `po_id` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `vendor` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `shipment_mode` | string | 360 (3.49%) | N/A | N/A | N/A | N/A |
| `item_description` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `line_quantity` | integer | 0 (0.0%) | 0.0% | 1371 (13.28%) | 217 (2.1%) | [1.0 .. 619999.0], med=3000.0 |
| `scheduled_date` | date | 0 (0.0%) | N/A | N/A | N/A | 2006-05-02 .. 2015-12-31 |
| `delivered_date` | date | 0 (0.0%) | N/A | N/A | N/A | 2006-05-02 .. 2015-09-14 |
| `raw_slip_days` | integer | 0 (0.0%) | 61.26% | 3127 (30.29%) | 284 (2.75%) | [-372.0 .. 192.0], med=0.0 |
| `clamped_slip_days` | integer | 0 (0.0%) | 61.26% | 3127 (30.29%) | 105 (1.02%) | [-60.0 .. 180.0], med=0.0 |

### Dataset: `data/real/raw/salesdaily.csv`
- **Total Records**: 2,106 rows | **Total Columns**: 13 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `datum` | date | 0 (0.0%) | N/A | N/A | N/A | 2014-01-02 .. 2019-12-09 |
| `M01AB` | float | 0 (0.0%) | 1.9% | 26 (1.23%) | 17 (0.81%) | [0.0 .. 17.34], med=4.99 |
| `M01AE` | float | 0 (0.0%) | 1.71% | 40 (1.9%) | 25 (1.19%) | [0.0 .. 14.463], med=3.67 |
| `N02BA` | float | 0 (0.0%) | 3.7% | 31 (1.47%) | 20 (0.95%) | [0.0 .. 16.0], med=3.5 |
| `N02BE` | float | 0 (0.0%) | 1.23% | 48 (2.28%) | 22 (1.04%) | [0.0 .. 161.0], med=26.9 |
| `N05B` | float | 0 (0.0%) | 2.04% | 48 (2.28%) | 25 (1.19%) | [0.0 .. 54.83333333], med=8.0 |
| `N05C` | float | 0 (0.0%) | 67.9% | 160 (7.6%) | 46 (2.18%) | [0.0 .. 9.0], med=0.0 |
| `R03` | float | 0 (0.0%) | 22.98% | 124 (5.89%) | 43 (2.04%) | [0.0 .. 45.0], med=4.0 |
| `R06` | float | 0 (0.0%) | 12.16% | 81 (3.85%) | 26 (1.23%) | [0.0 .. 15.0], med=2.0 |
| `Year` | integer | 0 (0.0%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [2014.0 .. 2019.0], med=2016.0 |
| `Month` | integer | 0 (0.0%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [1.0 .. 12.0], med=6.0 |
| `Hour` | integer | 0 (0.0%) | 0.0% | 2 (0.09%) | 2 (0.09%) | [190.0 .. 276.0], med=276.0 |
| `Weekday Name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |

### Dataset: `data/real/raw/usaid_deliveries.csv`
- **Total Records**: 10,324 rows | **Total Columns**: 33 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `﻿ID` | integer | 0 (0.0%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [1.0 .. 86823.0], med=57540.5 |
| `Project Code` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `PQ #` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `PO / SO #` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `ASN/DN #` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Country` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Managed By` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Fulfill Via` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Vendor INCO Term` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Shipment Mode` | string | 360 (3.49%) | N/A | N/A | N/A | N/A |
| `PQ First Sent to Client Date` | string | 205 (1.99%) | N/A | N/A | N/A | N/A |
| `PO Sent to Vendor Date` | string | 328 (3.18%) | N/A | N/A | N/A | N/A |
| `Scheduled Delivery Date` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Delivered to Client Date` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Delivery Recorded Date` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Product Group` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Sub Classification` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Vendor` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Item Description` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Molecule/Test Type` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Brand` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Dosage` | string | 1736 (16.82%) | N/A | N/A | N/A | N/A |
| `Dosage Form` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Unit of Measure (Per Pack)` | integer | 0 (0.0%) | 0.0% | 1023 (9.91%) | 67 (0.65%) | [1.0 .. 1000.0], med=60.0 |
| `Line Item Quantity` | integer | 0 (0.0%) | 0.0% | 1371 (13.28%) | 217 (2.1%) | [1.0 .. 619999.0], med=3000.0 |
| `Line Item Value` | float | 0 (0.0%) | 0.16% | 1127 (10.92%) | 193 (1.87%) | [0.0 .. 5951990.4], med=30471.47 |
| `Pack Price` | float | 0 (0.0%) | 0.17% | 1160 (11.24%) | 80 (0.77%) | [0.0 .. 1345.64], med=9.3 |
| `Unit Price` | float | 0 (0.0%) | 1.0% | 880 (8.52%) | 90 (0.87%) | [0.0 .. 238.65], med=0.16 |
| `Manufacturing Site` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `First Line Designation` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Weight (Kilograms)` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Freight Cost (USD)` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `Line Item Insurance (USD)` | float | 287 (2.78%) | 0.54% | 1116 (11.12%) | 214 (2.13%) | [0.0 .. 7708.44], med=47.04 |

### Dataset: `data/real/rxnorm_standards.json`
- **Total Records**: 12 rows | **Total Columns**: 8 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `medicine_id` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `generic_name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `rxcui` | integer | 0 (0.0%) | 0.0% | 2 (16.67%) | 1 (8.33%) | [161.0 .. 195085.0], med=6591.0 |
| `rxnorm_name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `standard_form` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `strength` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `atc_code` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `_id` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |

### Dataset: `data/real/supplier_slip.csv`
- **Total Records**: 36 rows | **Total Columns**: 8 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `vendor` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `shipment_mode` | string | 2 (5.56%) | N/A | N/A | N/A | N/A |
| `n_records` | integer | 0 (0.0%) | 0.0% | 3 (8.33%) | 1 (2.78%) | [17.0 .. 10324.0], med=84.0 |
| `mean_slip_days` | float | 0 (0.0%) | 22.22% | 8 (22.22%) | 1 (2.78%) | [-56.09 .. 9.17], med=0.0 |
| `median_p50_days` | integer | 0 (0.0%) | 91.67% | 3 (8.33%) | 1 (2.78%) | [-60.0 .. 0.0], med=0.0 |
| `p90_days` | integer | 0 (0.0%) | 75.0% | 9 (25.0%) | 2 (5.56%) | [-60.0 .. 43.0], med=0.0 |
| `min_days` | integer | 0 (0.0%) | 33.33% | 0 (0.0%) | 0 (0.0%) | [-60.0 .. 0.0], med=-11.5 |
| `max_days` | integer | 0 (0.0%) | 25.0% | 0 (0.0%) | 0 (0.0%) | [0.0 .. 180.0], med=35.5 |

### Dataset: `data/real/who_disease_surveillance.json`
- **Total Records**: 3 rows | **Total Columns**: 8 | **Duplicate Rows**: 0 (0.0%)

| Column Name | Inferred Type | Nulls (%) | Zero % | Outliers (IQR) | Outliers (|z|>3) | Min / Max / Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `indicator_code` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `indicator_name` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `records_analyzed` | integer | 0 (0.0%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [97.0 .. 100.0], med=100.0 |
| `sample_recent_records` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `average_metric` | integer | 0 (0.0%) | 0.0% | 0 (0.0%) | 0 (0.0%) | [66.634 .. 1425609.5], med=1095.0 |
| `epidemiological_risk_tier` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `demand_multiplier_impact` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |
| `_id` | string | 0 (0.0%) | N/A | N/A | N/A | N/A |

---

## 🏥 3. Simulated Multi-Tier Network Profiles (`data/simulated/`)

Summary of facility ledger, consumption, physical audit, and order records across the 180-day baseline simulation:

#### `batches.csv` (291 rows, 7 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `batch_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `quantity` | integer | 0 | 7.0 | 79.0 | 5520.0 | 0.0% |
| `expiry_date` | date | 0 | 2026-10-29 | N/A | 2028-06-15 | N/A |
| `quarantined` | boolean | 0 | N/A | N/A | N/A | N/A |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `consumption_daily.csv` (25,920 rows, 5 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `date` | date | 0 | 2026-04-28 | N/A | 2026-10-24 | N/A |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `units_issued` | integer | 0 | 0.0 | 7.0 | 459.0 | 2.02% |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `deliveries.csv` (1,236 rows, 7 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `delivery_id` | string | 0 | N/A | N/A | N/A | N/A |
| `po_id` | string | 0 | N/A | N/A | N/A | N/A |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `received_date` | date | 0 | 2026-05-11 | N/A | 2026-10-24 | N/A |
| `received_qty` | integer | 0 | 18.0 | 184.0 | 11600.0 | 0.0% |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `facilities.csv` (12 rows, 5 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `name` | string | 0 | N/A | N/A | N/A | N/A |
| `level` | string | 0 | N/A | N/A | N/A | N/A |
| `catchment_scale` | float | 0 | 0.12 | 0.23 | 5.0 | 0.0% |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `ground_truth.csv` (10 rows, 8 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `anomaly_id` | string | 0 | N/A | N/A | N/A | N/A |
| `type` | string | 0 | N/A | N/A | N/A | N/A |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `day_index` | integer | 0 | 160.0 | 169.5 | 175.0 | 0.0% |
| `description` | string | 0 | N/A | N/A | N/A | N/A |
| `magnitude` | integer | 0 | 0.0 | 150.0 | 900.0 | 10.0% |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `ledger_daily.csv` (25,920 rows, 5 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `date` | date | 0 | 2026-04-28 | N/A | 2026-10-24 | N/A |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `ledger_stock` | integer | 0 | 0.0 | 487.0 | 57617.0 | 0.11% |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `physical_audit.csv` (432 rows, 7 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `audit_id` | string | 0 | N/A | N/A | N/A | N/A |
| `date` | date | 0 | 2026-06-27 | N/A | 2026-10-10 | N/A |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `counted_stock` | integer | 0 | 0.0 | 515.0 | 54368.0 | 0.23% |
| `auditor_notes` | string | 0 | N/A | N/A | N/A | N/A |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `purchase_orders.csv` (1,288 rows, 9 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `po_id` | string | 0 | N/A | N/A | N/A | N/A |
| `supplier_id` | string | 0 | N/A | N/A | N/A | N/A |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `quantity` | integer | 0 | 18.0 | 184.0 | 11600.0 | 0.0% |
| `order_date` | date | 0 | 2026-05-05 | N/A | 2026-10-24 | N/A |
| `promised_date` | date | 0 | 2026-05-11 | N/A | 2026-11-01 | N/A |
| `status` | string | 0 | N/A | N/A | N/A | N/A |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `suppliers.csv` (4 rows, 7 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `supplier_id` | string | 0 | N/A | N/A | N/A | N/A |
| `supplier_name` | string | 0 | N/A | N/A | N/A | N/A |
| `real_vendor_ref` | string | 0 | N/A | N/A | N/A | N/A |
| `shipment_mode` | string | 0 | N/A | N/A | N/A | N/A |
| `historical_mean_slip` | float | 0 | -16.55 | -6.13 | 0.94 | 0.0% |
| `historical_p90_slip` | integer | 0 | 3.0 | 6.5 | 14.0 | 0.0% |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `transfers.csv` (1 rows, 9 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `transfer_id` | string | 0 | N/A | N/A | N/A | N/A |
| `from_facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `to_facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `quantity` | integer | 0 | 120.0 | 120.0 | 120.0 | 0.0% |
| `transfer_date` | date | 0 | 2026-10-15 | N/A | 2026-10-15 | N/A |
| `lead_days` | integer | 0 | 1.0 | 1.0 | 1.0 | 0.0% |
| `status` | string | 0 | N/A | N/A | N/A | N/A |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

#### `true_stock_daily.csv` (25,920 rows, 5 columns)
| Column | Type | Null Count | Min | Median | Max | Zero Inflation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `date` | date | 0 | 2026-04-28 | N/A | 2026-10-24 | N/A |
| `facility_id` | string | 0 | N/A | N/A | N/A | N/A |
| `medicine_id` | string | 0 | N/A | N/A | N/A | N/A |
| `true_stock` | integer | 0 | 0.0 | 487.0 | 57617.0 | 0.11% |
| `source` | string | 0 | N/A | N/A | N/A | N/A |

---

## 🛡️ 4. Data Hygiene Findings & Invariant Principles

1. **Deterministic Arithmetic**: All statistics, percentiles, IQR bounds, and z-score thresholds are computed directly via NumPy and standard Python libraries without LLM intermediate translation.
2. **Zero Fabrication**: All counts match physical disk contents exactly as verified by `scripts/data_audit.py`.
3. **Transparent Outliers**: Delivery slip delays and demand surges are empirically quantified to ground probabilistic ETA Monte Carlo sampling in real-world distributor behavior.

---

## 🔬 5. USAID Delivery Deduplication Key Rationale & Multi-Line PO Audit

In the initial data cleaning iteration, an overly coarse deduplication key based strictly on `(PO, Scheduled Date, Delivered Date, Vendor, Mode)` discarded 3,732 rows (36.1% of the dataset) as apparent 'duplicates'.

However, a column-level audit confirms that `usaid_deliveries.csv` has **0 exact duplicate rows** across its 33 columns. The 3,732 collapsed rows represent distinct medicine line items shipped together in the same purchase order consignments on the same delivery dates:

### Concrete Raw Examples of Collapsed Multi-Line Consignments:
1. **PO `SCMS-19800` (Delivered 2006-06-02)**:
   - Line `ID=422`: *Saquinavir 200mg [Invirase], capsules, 120 Caps* | Qty: 6 | Value: $80.64
   - Line `ID=423`: *Stavudine 1mg/ml [Zerit], powder for oral solution, 200 ml* | Qty: 600 | Value: $2,838.00
   - *Audit Finding*: Distinct antiretroviral medicines with completely different molecule types, quantities, and price structures sharing a single multi-item shipping manifest.
2. **PO `SCMS-23500` (Delivered 2006-08-27)**:
   - Line `ID=532`: *Didanosine EC 250mg [Videx EC], delayed-release capsules, 30 Caps* | Qty: 100 | Value: $1,634.00
   - Line `ID=533`: *Stavudine 1mg/ml [Zerit], powder for oral solution, 200 ml* | Qty: 670 | Value: $3,169.10
   - *Audit Finding*: Separate clinical formulations packaged in one physical pallet delivery.
3. **PO `SCMS-33320` (Delivered 2006-11-24)**:
   - Line `ID=835`: *Tenofovir Disoproxil Fumarate 300mg, tablets, 30 Tabs* | Qty: 80 | Value: $1,656.00
   - Line `ID=837`: *Stavudine 1mg/ml [Zerit], powder for oral solution, 200 ml* | Qty: 600 | Value: $2,838.00
   - *Audit Finding*: Completely distinct chemical entities delivered together under USAID PEPFAR procurement.

### Corrected Line-Item Deduplication Key
The deduplication key in `scripts/process_real_data.py` was updated to incorporate the unique line item ID, Item Description, and Line Item Quantity:
$$\text{Dedup Key} = (\text{line\_id}, \text{po\_id}, d_{\text{sched}}, d_{\text{deliv}}, \text{item\_description}, \text{line\_quantity}, \text{vendor}, \text{mode})$$

With this grounded line-item deduplication key:
- Total Raw Rows: **10,324**
- Dropped Missing Dates: **0** (100% of rows have valid parseable scheduled and delivery dates)
- True Duplicate Rows: **0** (0.0%)
- Cleaned Valid Rows: **10,324** (100% preserved)
- Extreme Slip Clamping ([-60, +180] days): **441 rows** winsorized
- Verified Vendor-Mode Empirical Distributions: **36 distinct priors** generated with pooled fallback
