# MedTrace 180-Day Simulation Replay & Benchmark Summary Report

> **Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why**  
> *Empirical comparative evaluation against baseline logistics management models across 180 simulated days.*

---

## 📊 1. Overall Comparative Benchmark (Seeds 1–4)

All models evaluated under identical **14.0-day replenishment alert horizon** (`consumption * 14.0 days`), eliminating threshold bias:

| Evaluation Metric | Naive LMIS | Heuristic Rule-Based | MedTrace | Gain / Advantage |
| :--- | :---: | :---: | :---: | :---: |
| **Shared Alert Horizon** | 14.0 days | 14.0 days | **14.0 days** | Identical baseline parity |
| **Clean Stock Lead Time** | 58.4 days | 58.4 days | **58.5 days** | Baseline parity on uncorrupted stock |
| **Stockout Recall** | 100.0% | 100.0% | **100.0%** | 100% intercept across all true stockouts |
| **Ground-Truth Anomaly Precision** | 100.0% | 100.0% | **93.5%** | Planted failure mode precision |
| **Ground-Truth Anomaly Recall** | 10.0% | 10.0% | **95.0%** | Planted failure mode recall (>85% target) |
| **Ground-Truth Anomaly F1 Score** | 18.2% | 18.2% | **93.9%** | Planted failure mode F1 (>85% target) |
| **Held-Out Test F1 (Seeds 3–4)** | 18.2% | 18.2% | **95.0%** | Unseen simulation generalization |
| **False Emergency Reorders** | 0 | 0 | **0** | Zero capital lockup across 180 days |

---

## 🔬 2. Seed-by-Seed Empirical Breakdown

| Simulation Seed | Evaluation Role | Total Actual Stockouts | Anomaly Precision | Anomaly Recall | Anomaly F1 Score |
| :---: | :--- | :---: | :---: | :---: | :---: |
| Seed 1 | Tuning / Development | 30 | 83.3% | 100.0% | **90.9%** |
| Seed 2 | Tuning / Development | 25 | 100.0% | 90.0% | **94.7%** |
| Seed 3 | Held-Out Test | 27 | 100.0% | 90.0% | **94.7%** |
| Seed 4 | Held-Out Test | 16 | 90.9% | 100.0% | **95.2%** |

---

## ⚡ 3. Computational Performance & Throughput

Evaluation engine computational throughput measured across 180 simulated days (~25,920 transaction records per seed):

| Simulation Seed | Transactions Replayed | Replay Duration | Processing Throughput |
| :---: | :---: | :---: | :---: |
| Seed 1 | 25,920 | 3.28s | 7,899.7 events/sec |
| Seed 2 | 25,920 | 3.26s | 7,955.5 events/sec |
| Seed 3 | 25,920 | 3.13s | 8,289.2 events/sec |
| Seed 4 | 25,920 | 3.22s | 8,055.0 events/sec |

---

## ⚖️ 4. Evaluation Methodology & Invariant Principles

1. **Parity Alert Threshold**: All three models trigger reorder alerts at exactly `consumption * 14.0 days`. Naive LMIS and Heuristic are not artificially penalized with higher or lower thresholds.
2. **Zero LLM Arithmetic**: All stock reconciliations, Monte Carlo ETA simulations, and order quantities are computed with deterministic symbolic algorithms (`DeterministicEngine`).
3. **Held-Out Generalization**: Algorithm parameters were tuned exclusively on Seeds 1–2 and evaluated without modification on held-out Seeds 3–4, demonstrating **95.0% F1 generalization** on unseen facility networks.
