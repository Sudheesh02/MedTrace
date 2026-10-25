# MedTrace Curated Multi-Agent Benchmark Evaluation Report

**Evaluation Target**: Open Agent Hackathon 2026 - Track 2 (*The Agent That Can Explain Why*)  
**Generated**: 2026-10-25T20:14:38.088169  
**Total Hand-Crafted Clinical Scenarios**: 20  
**Evaluation Scope**: Multi-agent adversarial deliberation loop, Number Auditor zero-hallucination guardrail, and clinical action formulation against rules-only baseline.

> [!NOTE]
> **Synthetic Benchmark Declaration**: This evaluation consists of 20 hand-crafted clinical scenarios representing real-world hospital/clinic supply failure modes (5 Clean Controls, 4 Phantom Drift, 3 Quarantined Batches, 3 Chronic Supplier Slips, 3 PO Transit Losses, 2 Unit-of-Measure Mismatches). All input records and numbers are explicitly grounded and audited.

---

## 1. Executive Comparative Benchmark Summary

| Metric | Rules-Only Baseline (Standard LMIS) | MedTrace Multi-Agent Loop | Advantage / Delta | Grounding Method |
| :--- | :---: | :---: | :---: | :--- |
| **Anomaly Detection Precision** | **60.0%** (3/5) | **100.0%** (15/15) | **+40.0%** | 0 false alarms on clean stock |
| **Anomaly Detection Recall** | **20.0%** (3/15) | **100.0%** (15/15) | **+80.0%** | Multi-source audit intercepts hidden risks |
| **Anomaly F1 Score** | **30.0%** | **100.0%** | **+70.0%** | Harmonic balance of precision & recall |
| **Correct Abstention Rate (Clean Cases)** | **100.0%** (5/5) | **100.0%** (5/5) | **Parity (100%)** | Zero false emergency reorders on healthy stock |
| **Unsupported Number Claim Rate** | Unenforced / Ungrounded | **0.0%** (0/20) | **100% Mathematically Grounded** | Enforced by Skeptic Number Auditor |

---

## 2. Category-Wise Failure Mode Breakdown

| Clinical Category | Scenario Count | Rules Baseline Detected | MedTrace Detected | Clinical Consequence of Baseline Failure |
| :--- | :---: | :---: | :---: | :--- |
| `CLEAN_STOCK` | 5 | 5/5 (100%) | **5/5 (100%)** | Both systems abstain from ordering unnecessary emergency stock. |
| `PHANTOM_DRIFT` | 4 | 3/4 (75%) | **4/4 (100%)** | Baseline misses sub-threshold drift; undetected physical stockout occurs. |
| `QUARANTINED_BATCH` | 3 | 0/3 (0%) | **3/3 (100%)** | Baseline counts quarantined drugs as usable; patients receive recalled lot or stockout occurs. |
| `CHRONIC_SUPPLIER_SLIP` | 3 | 0/3 (0%) | **3/3 (100%)** | Baseline assumes on-time delivery; chronic vendor delay causes unintercepted stockout. |
| `PO_TRANSIT_LOSS` | 3 | 0/3 (0%) | **3/3 (100%)** | Baseline assumes dispatched PO will arrive; lost shipment is never expedited. |
| `UOM_MISMATCH` | 2 | 0/2 (0%) | **2/2 (100%)** | 10x blister pack error leads to 10-fold inventory miscalculation and emergency ordering. |

---

## 3. Scenario-by-Scenario Deliberation & Audit Table

| Case ID | Facility | Medicine | Category | Expected Ground Truth | Rules Baseline | MedTrace Verdict | Number Audit | Top Action Recommended |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **CASE-01** | `FAC-DH-01` | `MED-004` | `CLEAN_STOCK` | CLEAN (Adequate Stock) | NO_ALERT (0 units) | **CLEAN (Buffer Intact)** | [PASS] | `MONITOR_BUFFER` (0 units) |
| **CASE-02** | `FAC-CHC-01` | `MED-009` | `CLEAN_STOCK` | CLEAN (Adequate Stock) | NO_ALERT (0 units) | **CLEAN (Buffer Intact)** | [PASS] | `MONITOR_BUFFER` (0 units) |
| **CASE-03** | `FAC-PHC-01` | `MED-001` | `CLEAN_STOCK` | CLEAN (Adequate Stock) | NO_ALERT (0 units) | **CLEAN (Buffer Intact)** | [PASS] | `MONITOR_BUFFER` (0 units) |
| **CASE-04** | `FAC-DH-01` | `MED-007` | `CLEAN_STOCK` | CLEAN (Adequate Stock) | NO_ALERT (0 units) | **CLEAN (Buffer Intact)** | [PASS] | `MONITOR_BUFFER` (0 units) |
| **CASE-05** | `FAC-CHC-02` | `MED-008` | `CLEAN_STOCK` | CLEAN (Adequate Stock) | NO_ALERT (0 units) | **CLEAN (Buffer Intact)** | [PASS] | `MONITOR_BUFFER` (0 units) |
| **CASE-06** | `FAC-DH-01` | `MED-003` | `PHANTOM_DRIFT` | GHOST_STOCK | GHOST_STOCK | **GHOST_STOCK** | [PASS] | `INVENTORY_AUDIT_ADJUSTMENT` (220 units) |
| **CASE-07** | `FAC-CHC-01` | `MED-002` | `PHANTOM_DRIFT` | GHOST_STOCK | GHOST_STOCK | **GHOST_STOCK** | [PASS] | `INVENTORY_AUDIT_ADJUSTMENT` (230 units) |
| **CASE-08** | `FAC-PHC-01` | `MED-005` | `PHANTOM_DRIFT` | GHOST_STOCK | GHOST_STOCK | **GHOST_STOCK** | [PASS] | `INVENTORY_AUDIT_ADJUSTMENT` (250 units) |
| **CASE-09** | `FAC-PHC-02` | `MED-001` | `PHANTOM_DRIFT` | GHOST_STOCK | NO_ALERT (0 units) | **GHOST_STOCK** | [PASS] | `INVENTORY_AUDIT_ADJUSTMENT` (120 units) |
| **CASE-10** | `FAC-DH-01` | `MED-001` | `QUARANTINED_BATCH` | QUARANTINED_BATCH | NO_ALERT (0 units) | **QUARANTINED_BATCH** | [PASS] | `PEER_TRANSFER` (149 units) |
| **CASE-11** | `FAC-CHC-01` | `MED-004` | `QUARANTINED_BATCH` | QUARANTINED_BATCH | NO_ALERT (0 units) | **QUARANTINED_BATCH** | [PASS] | `PEER_TRANSFER` (30 units) |
| **CASE-12** | `FAC-PHC-01` | `MED-006` | `QUARANTINED_BATCH` | QUARANTINED_BATCH | NO_ALERT (0 units) | **QUARANTINED_BATCH** | [PASS] | `MONITOR_BUFFER` (0 units) |
| **CASE-13** | `FAC-DH-01` | `MED-010` | `CHRONIC_SUPPLIER_SLIP` | CHRONIC_SUPPLIER_SLIP | NO_ALERT (0 units) | **CHRONIC_SUPPLIER_SLIP** | [PASS] | `PEER_TRANSFER` (105 units) |
| **CASE-14** | `FAC-CHC-01` | `MED-006` | `CHRONIC_SUPPLIER_SLIP` | CHRONIC_SUPPLIER_SLIP | NO_ALERT (0 units) | **CHRONIC_SUPPLIER_SLIP** | [PASS] | `PEER_TRANSFER` (90 units) |
| **CASE-15** | `FAC-PHC-01` | `MED-011` | `CHRONIC_SUPPLIER_SLIP` | CHRONIC_SUPPLIER_SLIP | NO_ALERT (0 units) | **CHRONIC_SUPPLIER_SLIP** | [PASS] | `PEER_TRANSFER` (132 units) |
| **CASE-16** | `FAC-DH-01` | `MED-009` | `PO_TRANSIT_LOSS` | PO_DISPATCHED_NOT_RECEIVED | NO_ALERT (0 units) | **PO_DISPATCHED_NOT_RECEIVED** | [PASS] | `PEER_TRANSFER` (30 units) |
| **CASE-17** | `FAC-CHC-02` | `MED-004` | `PO_TRANSIT_LOSS` | PO_DISPATCHED_NOT_RECEIVED | NO_ALERT (0 units) | **PO_DISPATCHED_NOT_RECEIVED** | [PASS] | `PEER_TRANSFER` (48 units) |
| **CASE-18** | `FAC-PHC-02` | `MED-007` | `PO_TRANSIT_LOSS` | PO_DISPATCHED_NOT_RECEIVED | NO_ALERT (0 units) | **PO_DISPATCHED_NOT_RECEIVED** | [PASS] | `PEER_TRANSFER` (60 units) |
| **CASE-19** | `FAC-DH-01` | `MED-004` | `UOM_MISMATCH` | UOM_MISMATCH | STOCK_DEFICIT | **UOM_MISMATCH** | [PASS] | `PEER_TRANSFER` (125 units) |
| **CASE-20** | `FAC-CHC-01` | `MED-001` | `UOM_MISMATCH` | UOM_MISMATCH | STOCK_DEFICIT | **UOM_MISMATCH** | [PASS] | `PEER_TRANSFER` (140 units) |

---

## 4. Zero-Hallucination Number Auditor Verification Invariants
Across all 20 clinical scenarios, the MedTrace multi-agent loop enforced 4 deterministic mathematical invariants:
1. **Non-Negative Inventory**: $\text{usable\_stock} \ge 0$ and $\text{shortfall\_units} \ge 0$ validated across 100% of cases.
2. **Trust-Adjusted Stock Identity**: $\text{usable\_stock} = \max(0, \text{ledger\_stock} - \text{drift} - \text{quarantined} - \text{expired})$ checked within 0.01 tolerance.
3. **Claim Grounding Guardrail**: Every numerical quantity cited in Investigator hypotheses and Skeptic critiques is checked against the deterministic reconciliation evidence set.
4. **Action Plan Invariant Audit**: Recommended transfer units match exact shortfall; peer facility surplus is strictly respected; healthy stock cases formulate `MONITOR_BUFFER` with 0.0 units.

**Result**: **0 unsupported claims** detected (0.0% rate across 20 runs).
