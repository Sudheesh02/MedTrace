# MedTrace Hospital & Warehouse LMIS Ingestion Contract

This document defines the standard tabular data exchange format for integrating real-world Logistics Management Information Systems (LMIS) — such as OpenLMIS, DHIS2 Tracker, mSupply, or district ERPs — into MedTrace.

---

## 📋 1. Core Ingestion Tables

To perform audit reconciliation and multi-agent shortage investigation, an external LMIS exports 5 standardized CSV extracts:

### 1.1 `ledger_daily.csv` (Daily Closing Balance)
Records closing physical balances reported by the warehouse ledger.
| Column | Type | Nullable | Description / Standard |
| :--- | :--- | :---: | :--- |
| `date` | `YYYY-MM-DD` | No | Date of closing stock balance |
| `facility_id` | `VARCHAR(32)` | No | Unique facility identifier (e.g. `FAC-DH-01`) |
| `medicine_id` | `VARCHAR(32)` | No | Curated essential medicine ID (e.g. `MED-007`) |
| `ledger_stock` | `FLOAT` | No | Recorded quantity in basic dispensing units |
| `source` | `VARCHAR(32)` | Yes | System of record (`LMIS_EXPORT`, `DHIS2`) |

### 1.2 `physical_audit.csv` (Physical Shelf Counts)
Periodic physical cycle counts and stocktaking audits.
| Column | Type | Nullable | Description / Standard |
| :--- | :--- | :---: | :--- |
| `audit_id` | `VARCHAR(32)` | No | Unique audit record identifier |
| `date` | `YYYY-MM-DD` | No | Date physical count was conducted |
| `facility_id` | `VARCHAR(32)` | No | Facility where audit occurred |
| `medicine_id` | `VARCHAR(32)` | No | Medicine counted |
| `counted_stock` | `FLOAT` | No | Verified physical shelf count |
| `auditor_notes` | `VARCHAR(256)` | Yes | Inspector commentary or shrinkage flags |

### 1.3 `batches.csv` (Batch & Quality Status)
Tracks individual lots, shelf-life expiry dates, and QA quarantine holds.
| Column | Type | Nullable | Description / Standard |
| :--- | :--- | :---: | :--- |
| `batch_id` | `VARCHAR(32)` | No | Manufacturer lot / batch number |
| `facility_id` | `VARCHAR(32)` | No | Facility holding the batch |
| `medicine_id` | `VARCHAR(32)` | No | Medicine identifier |
| `quantity` | `FLOAT` | No | Quantity in this specific lot |
| `expiry_date` | `YYYY-MM-DD` | No | Manufacturer expiration date |
| `quarantined` | `BOOLEAN` | No | `true` if under QA hold / recall |

### 1.4 `purchase_orders.csv` (Procurement Pipeline)
Purchase orders placed with contracted vendors.
| Column | Type | Nullable | Description / Standard |
| :--- | :--- | :---: | :--- |
| `po_id` | `VARCHAR(32)` | No | Order reference number |
| `supplier_id` | `VARCHAR(32)` | No | Contracted supplier code |
| `facility_id` | `VARCHAR(32)` | No | Receiving destination |
| `medicine_id` | `VARCHAR(32)` | No | Medicine ordered |
| `quantity` | `FLOAT` | No | Ordered quantity |
| `order_date` | `YYYY-MM-DD` | No | Date order was placed |
| `promised_date` | `YYYY-MM-DD` | No | Vendor contract SLA delivery date |
| `status` | `VARCHAR(16)` | No | `PLACED`, `DISPATCHED`, `DELIVERED`, `CANCELLED` |

### 1.5 `deliveries.csv` (Receiving Dock Inbound)
Goods receipt notes (GRN) logged at warehouse receiving docks.
| Column | Type | Nullable | Description / Standard |
| :--- | :--- | :---: | :--- |
| `delivery_id` | `VARCHAR(32)` | No | Goods receipt voucher identifier |
| `po_id` | `VARCHAR(32)` | No | Matching purchase order reference |
| `facility_id` | `VARCHAR(32)` | No | Receiving facility |
| `medicine_id` | `VARCHAR(32)` | No | Medicine received |
| `received_date` | `YYYY-MM-DD` | No | Physical receipt date |
| `received_qty` | `FLOAT` | No | Quantity received at dock |

---

## 🔒 2. Validation & Ingestion Rules
1. **Dispensing Unit Uniformity**: All quantities must represent single dispensing units (tablets, capsules, vials) as normalized via RxNorm standards.
2. **Date Synchronization**: When physical audit dates diverge from ledger closing dates, MedTrace synchronizes ledger stock on the audit date to compute exact phantom drift.
3. **Data Protection**: Ingestion pipelines strictly validate that files do not contain patient-identifiable health information (zero PHI).
