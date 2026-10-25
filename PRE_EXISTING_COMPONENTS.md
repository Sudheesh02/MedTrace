# MedTrace — Declaration of Pre-Existing Components

> **Open Agent Hackathon 2026 — Track 2: The Agent That Can Explain Why**  
> **Submission Deliverable 05: Pre-Existing Components Declaration**  
> **Audit Window: 22 October 2026 00:00 UTC – 27 October 2026 23:45 UTC**

---

## 1. Compliance Statement

In compliance with the **Open Agent Hackathon 2026 Rules** (*Participant Onboarding Deck [16page] Rule 05 & Welcome Guide Section 5*), all participants must explicitly declare any pre-existing code, models, datasets, or libraries created prior to the official hackathon build window (October 22, 2026, 00:00 UTC).

**MedTrace was conceived, architected, implemented, and benchmarked 100% during the hackathon build window.** 

No proprietary pre-existing codebase, commercial supply chain software, or internal company tooling was used. All third-party dependencies are standard, open-source permissive packages, and all raw datasets are from verified public, open-access domain sources.

---

## 2. Pre-Existing Third-Party Open Source Libraries

The following standard Python packages were installed via `pip` and used as underlying runtime infrastructure:

| Package | Version Specified | Licence | Purpose |
| :--- | :--- | :--- | :--- |
| `fastapi` | `>=0.110.0` | MIT | REST API framework for programmatic endpoints (`GET /health`, `POST /run`). |
| `pydantic` | `>=2.6.0` | MIT | Data validation and JSON serialization for Action Pack schemas. |
| `uvicorn` | `>=0.28.0` | BSD-3-Clause | ASGI web server runtime for FastAPI. |
| `requests` | `>=2.31.0` | Apache 2.0 | HTTP client for querying Zetaris REST SQL API and openFDA. |
| `openai` | `>=1.14.0` | Apache 2.0 | Standard client library to interface with NVIDIA Nemotron / Meterless Nightshift endpoints. |
| `pytest` | `>=8.0.0` | MIT | Automated test suite execution harness. |
| `httpx` | `>=0.25.0` | BSD-3-Clause | ASGI test client for FastAPI endpoint verification. |
| `python-dotenv` | `>=1.0.0` | BSD-3-Clause | Safe local environment variable loading (gitignored `.env`). |
| `numpy` | `>=1.26.0` | BSD-3-Clause | Matrix and empirical distribution sampling for Monte Carlo ETA simulations. |

---

## 3. Pre-Existing Public Open Datasets & Reference Sources

All external data referenced by MedTrace originates from public, open-access healthcare repositories:

| Dataset | Authority / Source | Origin Date | Usage in MedTrace & Modeling Assumptions |
| :--- | :--- | :--- | :--- |
| **WHO Model EML & India NLEM 2022** | World Health Organization / Ministry of Health & Family Welfare, India | 2022–2023 | Reference list for 12 essential medicines, ATC classifications, and standard dosing forms. |
| **USAID GHSC-PSM Delivery History & Supplier Slip Priors** | USAID Global Health Supply Chain Program (Data.gov) | 2015–2020 | 10,324 public shipment records used to derive empirical vendor lead-time delay percentiles (`mean`, `p50`, `p90`).<br>*Calibrated Assumption*: Empirical delay percentiles are assigned to simulation suppliers, and Monte Carlo transit slip is modeled via empirical distribution sampling `[0.0, 0.5*p90, 1.0*p90, 1.5*p90]`. |
| **openFDA Shortages & Enforcement Recalls** | US Food & Drug Administration Open Data API (`api.fda.gov`) | Live API / Public Domain | Public shortage alerts and Class I/II recall lot identifiers used as external disruption signals. |
| **NIH RxNorm & DailyMed** | US National Library of Medicine (NLM / NIH) | Public Domain | Standard clinical drug vocabularies and official product listings.<br>*Calibrated Assumption*: Packaging formats (10x10 blister strips) and storage temperatures (2°C–8°C cold chain vs 15°C–30°C room temp) are assigned via rule-based clinical supply heuristics. |
| **WHO GHO Disease Surveillance** | WHO Global Health Observatory Athena OData API | Live API / Public Domain | Real epidemiological indicator time-series (malaria, meningitis, HIV).<br>*Calibrated Assumption*: An assumed +35% (1.35x) surge consumption multiplier is mapped to `ELEVATED` epidemiological risk tiers in `DeterministicEngine`. |
| **Kaggle Pharma Sales Daily** | SaibalPatraDS / Zdravković | CC-BY 4.0 | Time-series sales patterns used to extract normalized seasonal multipliers (mean = 1.0). |

*Note: All data samples in the repository are lightweight, legal to use, accompanied by automated download and extraction scripts in `scripts/download_real_data.py`, and all heuristic or synthetic parameters are explicitly declared above.*

---

## 4. Components Built Wholly During the Hackathon (Oct 22–27, 2026)

The entirety of MedTrace's domain logic, reasoning loops, evaluation harnesses, and testing infrastructure was engineered from scratch during the hackathon:

1. **Deterministic Arithmetic Engine ([`app/engine/deterministic.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/engine/deterministic.py))**:
   - Trust-adjusted usable stock algorithm ($usable = ledger - drift - quarantined - expiring$).
   - Parametric days-of-cover and inventory shortfall calculator.
   - Monte Carlo probabilistic lead-time arrival simulator with empirical vendor delay distributions.
   - Dynamic Unit-of-Measure (UOM) converter (pack size multiplier).

2. **Adversarial Multi-Agent Deliberation Architecture ([`app/agents/`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/agents/))**:
   - `TriagePlannerAgent`: Proactively scans district facility-medicine portfolios and prioritizes critical stockout risks.
   - `ReconcilerAgent`: Multi-source anomaly detection across ledgers, audits, and open POs.
   - `InvestigatorAgent`: Generates $\ge 3$ competing differential hypotheses with evidentiary verification tests.
   - `SkepticAgent`: Number Auditor that independently verifies mathematical invariants, rejects hallucinated numbers, and executes adversarial challenge loops.
   - `ActionPlannerAgent`: Dynamic peer warehouse surplus routing, lead-time feasibility scoring, and emergency order formulation.
   - `MedTraceOrchestrator` ([`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/orchestrator.py)): Central state machine with structured JSONL audit trace logging (`logs/trace_*.jsonl`).

3. **Sponsor Technology Implementations**:
   - **Meterless World Model Service** ([`app/engines/world_model.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/engines/world_model.py)): Grounded entity state graph, provenance tracking, content hash idempotency (Test W1), and planted conflict recording (Test W2).
   - **Meterless H-MEM Service** ([`app/engines/hmem.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/engines/hmem.py)): Episodic memory store recording officer override decisions (Test H1) and deterministic contradiction resolution (Test H2).
   - **Zetaris Federated SQL Adapter** ([`app/adapters/data_store.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/adapters/data_store.py)): REST SQL proxy querying, JWT authentication caching, dynamic SQL generation, and offline fallback.

4. **180-Day Facility Simulation & Comparative Backtest Harness**:
   - Simulation Generator ([`scripts/generate_facility_simulation.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/scripts/generate_facility_simulation.py)): Multi-tier facility transaction generator across 12 facilities and 180 days with 10 planted anomalies across seeds 1–4.
   - Backtest Replay Engine ([`app/backtest/engine.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/backtest/engine.py), [`scripts/run_backtest.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/scripts/run_backtest.py)): Measures early warning lead times, anomaly precision/recall, and false reorders comparing MedTrace against Naive LMIS and Heuristic Rule systems.

5. **API, Packaging, Documentation & Test Suite**:
   - Unified API & CLI runner ([`run.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/run.py)).
   - Hardened `Dockerfile` with container healthcheck and `.dockerignore`.
   - Comprehensive test suite in [`tests/`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/) (116 automated tests passing with 100% success rate across all 7 test suites).
   - All documentation: `README.md`, `SPONSOR_TECH.md`, `scripts/register_zetaris_sources.md`, `data/lmis_export_contract.md`.

6. **Autonomous Development & Agent Harness**:
   - **Gemini Autonomous Coding Assistant & Harness**: Continuous architecture auditing, test generation, benchmark standardization, and iterative overnight refinement executed through the Google Antigravity / Gemini autonomous agent harness under developer direction during the hackathon window.
