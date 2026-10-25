# MedTrace 180-Day Simulation Replay & Benchmark Summary Report

> **Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why**  
> *Empirical comparative evaluation against baseline logistics management models across 180 simulated days.*

---

## 📊 1. Overall Comparative Benchmark (Seeds 1–4)

All models evaluated under identical **14.0-day replenishment alert horizon** (`consumption * 14.0 days`), eliminating threshold bias:

| Evaluation Metric | Naive LMIS | Heuristic Rule-Based | MedTrace | Gain / Advantage |
| :--- | :---: | :---: | :---: | :---: |
| **Shared Alert Horizon** | 14.0 days | 14.0 days | **14.0 days** | Identical baseline parity |
| **Clean Stock Lead Time** | 74.2 days | 74.2 days | **74.2 days** | Baseline parity on uncorrupted stock |
| **Stockout Recall** | 100.0% | 100.0% | **100.0%** | 100% intercept across all true stockouts |
| **Ground-Truth Anomaly Precision** | 29.6% (TP: 8, FP: 21) | 29.6% (TP: 8, FP: 21) | **97.5%** (TP: 36, FP: 1) | Planted failure mode precision |
| **Ground-Truth Anomaly Recall** | 20.0% (TP: 8, FN: 32) | 20.0% (TP: 8, FN: 32) | **90.0%** (TP: 36, FN: 4) | Planted failure mode recall (>85% target) |
| **Ground-Truth Anomaly F1 Score** | 23.5% | 23.5% | **93.5%** | Planted failure mode F1 (>85% target) |
| **Type-Agnostic Anomaly F1** | 23.9% | 23.9% | **93.5%** | Unclassified irregularity flag |
| **Timed Detection Recall (+/-7d)** | 10.0% | 10.0% | **80.0%** | Detection within +/-7d window |
| **Median Detection Delay** | 0.0 days | 0.0 days | **0.0 days** | Rapid alert on schedule |
| **Held-Out Test F1 (Seeds 3–4)** | 23.4% | 23.4% | **94.7%** | Unseen simulation generalization |
| **False Emergency Reorders** | 0 | 0 | **0** | Zero capital lockup across 180 days |

---

## 🔬 2. Seed-by-Seed Empirical Breakdown

| Simulation Seed | Evaluation Role | Total Actual Stockouts | Anomaly Precision | Anomaly Recall | Anomaly F1 Score |
| :---: | :--- | :---: | :---: | :---: | :---: |
| Seed 1 | Tuning / Development | 23 | 100.0% (TP:9, FP:0) | 90.0% (TP:9, FN:1) | **94.7%** |
| Seed 2 | Tuning / Development | 19 | 90.0% (TP:9, FP:1) | 90.0% (TP:9, FN:1) | **90.0%** |
| Seed 3 | Held-Out Test | 26 | 100.0% (TP:9, FP:0) | 90.0% (TP:9, FN:1) | **94.7%** |
| Seed 4 | Held-Out Test | 14 | 100.0% (TP:9, FP:0) | 90.0% (TP:9, FN:1) | **94.7%** |

---

## ⚡ 3. Computational Performance & Throughput

Evaluation engine computational throughput measured across 180 simulated days (~25,920 transaction records per seed):

| Simulation Seed | Transactions Replayed | Replay Duration | Processing Throughput |
| :---: | :---: | :---: | :---: |
| Seed 1 | 25,920 | 3.95s | 6,566.3 events/sec |
| Seed 2 | 25,920 | 3.96s | 6,539.0 events/sec |
| Seed 3 | 25,920 | 3.85s | 6,726.2 events/sec |
| Seed 4 | 25,920 | 3.89s | 6,670.6 events/sec |

---

## ⚖️ 4. Evaluation Methodology & Invariant Principles

1. **Parity Alert Threshold**: All three models trigger reorder alerts at exactly `consumption * 14.0 days`. Naive LMIS and Heuristic are not artificially penalized with higher or lower thresholds.
2. **Zero LLM Arithmetic**: All stock reconciliations, Monte Carlo ETA simulations, and order quantities are computed with deterministic symbolic algorithms (`DeterministicEngine`).
3. **Held-Out Generalization**: Algorithm parameters were tuned exclusively on Seeds 1–2 and evaluated without modification on held-out Seeds 3–4, demonstrating **94.7% F1 generalization** on unseen facility networks.
