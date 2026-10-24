# MedTrace Senior Reviewer Comprehensive Audit & Prioritized Overnight Backlog

**Audit Timestamp**: 2026-10-25 04:15 UTC  
**Reviewer Role**: Senior Staff AI Reviewer & Hackathon Judge Auditor  
**Evaluation Target**: Open Agent Hackathon 2026 — Track 2 (*The Agent That Can Explain Why*)  
**Status**: Application code unchanged in this step. Audit complete; 12 prioritized, concrete, small items established below.

---

## 🏛 Executive Audit Summary: README Claims vs. Real Code

A rigorous audit of [README.md](file:///C:/Users/Asus/Desktop/Open Agent/README.md), [MedTrace_Research_and_Execution_Plan.md](file:///C:/Users/Asus/Desktop/Open Agent/MedTrace_Research_and_Execution_Plan.md), the hackathon guidelines in `hackathon details/` ([16page.md](file:///C:/Users/Asus/Desktop/Open Agent/hackathon details/16page.md), [How to Win Hackathons!.md](file:///C:/Users/Asus/Desktop/Open Agent/hackathon details/How to Win Hackathons!.md), [Meterless_ Overview.md](file:///C:/Users/Asus/Desktop/Open Agent/hackathon details/Meterless_ Overview.md), [participant-setup-guide.md](file:///C:/Users/Asus/Desktop/Open Agent/hackathon details/participant-setup-guide.md)), and the active codebase reveals significant strengths along with 8 critical vulnerabilities and gaps against the 100-point judging rubric:

### Strengths Identified:
1. **Zero LLM Hallucinated Math**: The core design principle—isolating deterministic arithmetic to [`DeterministicEngine`](file:///C:/Users/Asus/Desktop/Open Agent/app/engine/deterministic.py)—is strictly maintained. Days of cover, trust-adjusted usable stock, and Monte Carlo ETA are computed mathematically with zero LLM generation of quantities.
2. **Real World Datasets**: 12 curated medicines, 10,324 real USAID shipment records, empirical supplier slip priors, openFDA shortages, FDA recall events, RxNorm clinical codes, and DailyMed cold-chain labels are collected with clear provenance in [`data/README.md`](file:///C:/Users/Asus/Desktop/Open Agent/data/README.md).
3. **Zetaris Federated SQL DataStore Integration**: [`DataStore`](file:///C:/Users/Asus/Desktop/Open Agent/app/adapters/data_store.py) connects dynamically to Zetaris Lightning REST SQL proxy (`/api/proxy/sql-editor/sqls/run-query`) with automatic JWT authentication and clean offline fallback.
4. **180-Day Facility Simulation Replay**: [`BacktestEngine`](file:///C:/Users/Asus/Desktop/Open Agent/app/backtest/engine.py) simulates 12 facilities over 180 days across seeds 1–3 and held-out seed 4, measuring real early warning lead times against naive LMIS.

---

### Critical Gaps & Vulnerabilities Uncovered:

| # | Subsystem | README Claim / Plan Requirement | Real Code Reality | Judging Impact |
|---|---|---|---|---|
| 1 | **Multi-Agent Loop** | "Adversarial critique & verification loop between Investigator and Skeptic" | In 100% of runs, the Skeptic accepts on Round 1 (`skeptic_rounds: 1`). `ROUND_2` never runs. The system operates as a fixed linear chain, penalized under Hackathon Rubric Technical & Innovation criteria. | **-10 pts** (Innovation & Technical) |
| 2 | **Meterless World Model & H-MEM** | "Execution Plan Phase 4: Test W2 (conflict recording) and Test H2 (contradiction resolution)" | While conflict recording and contradiction logic were sketched in engine files, neither is verified by automated tests in [`tests/test_world_model.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_world_model.py). | **-5 pts** (Sponsor Tech) |
| 3 | **Benchmark Metrics** | README Table: Early Warning `+14.4 d`, Recall `99.1%`, Precision `100.0%`, False Orders `4` | Real backtest execution (`scripts/run_backtest.py`) measures: Early Warning `+13.1 d` (64.1d vs 51.0d), Recall `100.0%`, Precision `97.7%`, Recall `92.5%`, F1 `94.8%`, False Orders `0`. Violates rule: *"Only claim numbers that the backtest actually measures."* | **-5 pts** (Credibility & Rigor) |
| 4 | **API Error Handling** | "Production-grade REST API (`POST /run`)" | Passing invalid facility or medicine IDs silently proceeds, assumes defaults (10 units/day), and hallucinates a 90-unit shortfall for non-existent entities, returning HTTP 200 rather than HTTP 404/422. | **-3 pts** (Product & UX) |
| 5 | **Action Planner** | "Ranks transfers with constraint checks (expiry-after-arrival, surplus)" | [`ActionPlannerAgent`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/action_planner.py) hardcodes `source_facility_id="FAC-WH-01"` without checking whether `FAC-WH-01` has usable surplus of `medicine_id` or if `FAC-WH-01` is itself the target. | **-4 pts** (Technical & Product) |
| 6 | **Human Escalation** | "Skeptic low confidence -> Escalate to human (Phase 3.6)" | When hypotheses fail Skeptic thresholds or have low confidence, Orchestrator still assigns `hypotheses[0]` and marks `stockout_prevented=True` without flagging human escalation. | **-3 pts** (Responsible AI) |
| 7 | **Examples & Schema** | `output_examples/*.json` represent API contract | `scripts/generate_examples.py` flattens output JSON, omitting `execution_time_seconds` and `agents` metadata present in `POST /run`. Sample 1 and 2 output examples contain stale `0.0` values. | **-3 pts** (Product & UX) |
| 8 | **Packaging & Docker** | Production Docker container spec | Missing `.dockerignore` causes git history, caches, and large archives to be copied into the build context. `Dockerfile` lacks `HEALTHCHECK`. Missing `httpx` in `requirements.txt`. | **-2 pts** (Technical) |

---

## 📋 Previously Completed Items (Verified in Git History)

- **Item A [DONE in Commit `316ab68`]**: Fixed `InvestigatorAgent` typing bug (`Optional` import missing) and mapped all 10 simulation anomalies to `AnomalyType` enum.
- **Item B [DONE in Commit `3b44a9e`]**: Wired live Zetaris Lightning REST SQL execution into `DataStore` with auto-discovery from `USE_ZETARIS` and graceful offline fallback; added 5 unit tests in `tests/test_data_store.py`.
- **Item C [DONE in Commit `45d86f7`]**: Eliminated hardcoded entity strings (`FAC-DH-01`, `MED-007`) in `BacktestEngine.run_backtest()`; added automated test suite in `tests/test_backtest.py`.

---

## 🚀 Prioritized Overnight Backlog (Exactly 12 Concrete, Small Items)

### Item 1: Activate Multi-Agent Adversarial Debate (Skeptic Challenge & Round 2 Revision)
- **Priority**: P0 (Track 2 Core Rubric — Innovation 15 pts & Technical 20 pts)
- **Status**: Ready for Implementation
- **Files**: [`app/agents/skeptic.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/skeptic.py), [`app/agents/investigator.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/investigator.py), [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/orchestrator.py), [`tests/test_agents.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_agents.py)
- **Problem**: In 100% of runs, the Skeptic accepts the hypothesis on Round 1 (`skeptic_rounds: 1`). Across all 80+ trace logs, `ROUND_2` never runs. The system operates as a fixed linear chain rather than an adversarial debate, directly violating the hackathon rubric requirement for critique, retries, and revision loops.
- **Action**:
  1. In `skeptic.py`, recalibrate Round 1 acceptance criteria: when multiple competing hypotheses have close likelihood scores ($\Delta \le 0.15$) or when an external disruption claim lacks multiple independent source corroborations, set `accepted=False` with explicit critique notes challenging the lack of differential elimination.
  2. In `investigator.py`, on receiving `skeptic_feedback` in Round 2, adjust hypothesis likelihoods, append targeted corroborating evidence queries, and refute the challenged counter-hypotheses.
  3. Add test `test_skeptic_adversarial_critique_triggers_round_2` in `tests/test_agents.py` asserting `pack.skeptic_rounds >= 2` on contested cases.
- **Acceptance Criteria**: Contested investigations trigger `ROUND_1_EVALUATION` (challenge) followed by `ROUND_2_START` with revised likelihoods in trace logs. `tests/test_agents.py` passes with an explicit assertion verifying multi-round debate.

---

### Item 2: Test & Finalize World Model Conflict Tracking & Ingest (Test W2)
- **Priority**: P0 (Sponsor Tech 10 pts & Execution Plan Phase 4.3)
- **Status**: Ready for Implementation
- **Files**: [`app/engines/world_model.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/engines/world_model.py), [`tests/test_world_model.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_world_model.py)
- **Problem**: Execution Plan Phase 4 explicitly specifies Test W2: "all planted conflicts of types 1, 4, 7, 8 are recorded as conflicts." Although `record_conflict` and `get_conflicts` methods were added to `WorldStoreService`, automated test coverage in `tests/test_world_model.py` is missing, leaving Meterless World Model conflict ingestion unverified.
- **Action**:
  1. Add `test_world_model_planted_conflict_recording` to `tests/test_world_model.py`.
  2. Verify that discrepancies identified during reconciliation (Ghost Stock, PO Dispatched Not Received, UOM Mismatch, Chronic Supplier Slip) are written to `world_store.conflicts` with entity IDs and timestamped provenance.
  3. Verify conflict query filtering via `world_store.get_conflicts(entity_id)`.
- **Acceptance Criteria**: `test_world_model_planted_conflict_recording` executes and passes in `tests/test_world_model.py`, verifying Phase 4 Test W2 compliance.

---

### Item 3: Test & Finalize H-MEM Deterministic Contradiction Resolution (Test H2)
- **Priority**: P0 (Sponsor Tech 10 pts & Execution Plan Phase 4.6)
- **Status**: Ready for Implementation
- **Files**: [`app/engines/hmem.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/engines/hmem.py), [`tests/test_world_model.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_world_model.py)
- **Problem**: Execution Plan Phase 4 specifies Test H2: "a later contradicting decision resolves the conflict deterministically." Contradiction resolution logic in `HMemEngine.record_officer_decision` lacks an automated unit test.
- **Action**:
  1. Add `test_hmem_contradiction_resolution` in `tests/test_world_model.py`.
  2. Verify that when an officer rejects an action (e.g. `PEER_TRANSFER` on `MED-004`) and subsequently approves it in a later session, the prior rejection penalty is cleared from `rejected_patterns` and preference weightings resolve deterministically.
- **Acceptance Criteria**: `test_hmem_contradiction_resolution` executes and passes in `tests/test_world_model.py`, verifying Phase 4 Test H2 compliance.

---

### Item 4: Input Entity Validation & Structured Error Responses in API / CLI
- **Priority**: P1 (Production Quality & API Robustness)
- **Status**: Ready for Implementation
- **Files**: [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/orchestrator.py), [`run.py`](file:///C:/Users/Asus/Desktop/Open Agent/run.py), [`tests/test_api.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/)
- **Problem**: Passing `facility_id="INVALID"` and `medicine_id="INVALID"` silently creates an investigation, defaults missing ledger/consumption to 10.0 units/day, invents a 90-unit shortfall, and returns `stockout_prevented=True` with recommended transfers to non-existent facilities.
- **Action**:
  1. In `orchestrator.py`, validate `facility_id` against `data_store.get_facilities()` and `medicine_id` against `data_store.get_medicines()`.
  2. If an entity is unrecognized, raise `ValueError(f"Unrecognized entity: {facility_id}")`.
  3. In `run.py`, catch `ValueError` and raise `HTTPException(status_code=404, detail=str(e))` instead of returning HTTP 200 with `status: error`. In CLI mode, print a clean validation error and exit with code 1.
- **Acceptance Criteria**: Requesting an invalid facility or medicine raises HTTP 404 in FastAPI and prints a clean validation error in CLI mode instead of generating false inventory recommendations.

---

### Item 5: Real Surplus & Expiry Validation for Peer Transfers in Action Planner
- **Priority**: P1 (Operational Credibility & Execution Plan Section 2.2 / 4.2)
- **Status**: Ready for Implementation
- **Files**: [`app/agents/action_planner.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/action_planner.py), [`tests/test_agents.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_agents.py)
- **Problem**: `ActionPlannerAgent` always hardcodes `source_facility_id="FAC-WH-01"` without checking: (a) whether the target facility IS `FAC-WH-01`, (b) whether `FAC-WH-01` actually holds usable stock of that medicine, or (c) whether batches at `FAC-WH-01` expire before arrival.
- **Action**:
  1. Inject `DataStore` into `ActionPlannerAgent`.
  2. Dynamically scan candidate peer facilities (`data_store.get_facilities()`) to identify peers holding usable stock with $>30$ days of cover for `medicine_id` (excluding the target facility itself).
  3. If no peer facility has surplus or if peer stock is near expiry, reduce peer transfer feasibility from 0.90 to 0.20 and promote `EXPEDITE_PO` or `EMERGENCY_PURCHASE`.
  4. Add unit test `test_action_planner_peer_surplus_validation` in `tests/test_agents.py`.
- **Acceptance Criteria**: Transfer recommendations only select source facilities with verified physical surplus, avoiding self-transfers or transfers from depleted warehouses.

---

### Item 6: Low-Confidence Human Escalation Path (Execution Plan Phase 3.6 / 4.2)
- **Priority**: P1 (Responsible AI & Hackathon Rubric)
- **Status**: Ready for Implementation
- **Files**: [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/orchestrator.py), [`app/models/schemas.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/models/schemas.py), [`run.py`](file:///C:/Users/Asus/Desktop/Open Agent/run.py)
- **Problem**: Execution Plan Section 4.2 specifies `Skeptic -> "low confidence" -> Escalate to human`. Currently, if Skeptic confidence remains below threshold after 3 rounds, `Orchestrator` still assigns `winning_hyp = hypotheses[0]` and outputs `stockout_prevented=True` without flagging human escalation.
- **Action**:
  1. Add `escalated_to_human: bool = False` and `escalation_reason: Optional[str] = None` to `ActionPack` schema in `schemas.py`.
  2. In `orchestrator.py`, if `winning_hyp` confidence $< 0.50$ after max rounds, set `escalated_to_human=True` and assign top action to `ActionType.EMERGENCY_PURCHASE` with human verification flag.
  3. Log step `Orchestrator.HUMAN_ESCALATION` in the trace log.
- **Acceptance Criteria**: Investigations with unverified or contested hypotheses trigger human escalation flag in the `ActionPack` output and trace log.

---

### Item 7: Eliminate Remaining Entity & Supplier String Literals in `BacktestEngine`
- **Priority**: P1 (Methodological Rigor & Technical Integrity)
- **Status**: Ready for Implementation
- **Files**: [`app/backtest/engine.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/backtest/engine.py), [`tests/test_backtest.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_backtest.py)
- **Problem**: In `app/backtest/engine.py`: line 361 hardcodes `if med == "MED-009" and len(open_pos) >= 2 and fac_meta.get("level") == "CHC":`, line 316 checks `opo.get("supplier_id") == "SUP-004"`, and line 324 checks `opo.get("supplier_id") == "SUP-001"`.
- **Action**:
  1. Replace `med == "MED-009"` with a generic lookup against `data_store.get_cross_border_shortages(medicine_id=med)` or `openfda_shortages.json`.
  2. Replace hardcoded supplier IDs with empirical delay thresholds: check whether `opo.get("status") == "DISPATCHED"` has zero matching delivery row in `delivs_by_fac_med` past promised date (for `PO_DISPATCHED_NOT_RECEIVED`), and check whether vendor mean slip $> 5.0$ days in `supplier_slip` (for `CHRONIC_SUPPLIER_SLIP`).
- **Acceptance Criteria**: Zero facility IDs, medicine IDs, or supplier IDs remain hardcoded in `BacktestEngine`. `python -m pytest tests/test_backtest.py` passes 100%.

---

### Item 8: Synchronize README Evaluation Table with Measured Backtest Output
- **Priority**: P1 (Documentation Integrity & Zero-Fluff Rule)
- **Status**: Ready for Implementation
- **Files**: [`README.md`](file:///C:/Users/Asus/Desktop/Open Agent/README.md)
- **Problem**: `README.md` lines 62-69 claim `Early Warning Lead Time: +14.4 days`, `Recall: 99.1%`, `Precision: 100.0%`, and `False Reorders: 4`. However, `scripts/run_backtest.py` across seeds 1–4 actually measures: `Early Warning Lead Time: +13.1 days (64.1d vs 51.0d)`, `Stockout Recall: 100.0%`, `Anomaly Precision: 97.7%`, `Anomaly Recall: 92.5%`, `Anomaly F1 Score: 94.8%`, and `False Emergency Orders: 0`.
- **Action**:
  1. Update `README.md` Table to report the exact figures measured by `scripts/run_backtest.py`.
  2. Add an explicit footnote explaining seed-averaged results across seeds 1–3 and held-out seed 4, adhering strictly to the "Only claim numbers that the backtest actually measures" rule.
- **Acceptance Criteria**: Every metric in `README.md` precisely matches the measured output of `python scripts/run_backtest.py`.

---

### Item 9: Synchronize `output_examples/` with API Response Schema
- **Priority**: P2 (Documentation & Contract Integrity)
- **Status**: Ready for Implementation
- **Files**: [`output_examples/*.json`](file:///C:/Users/Asus/Desktop/Open Agent/output_examples/), [`scripts/generate_examples.py`](file:///C:/Users/Asus/Desktop/Open Agent/scripts/generate_examples.py)
- **Problem**: `scripts/generate_examples.py` constructs a flattened dictionary for `output_examples/*.json`, omitting `execution_time_seconds` and `agents` metadata, while `run.py`'s `POST /run` wraps the pack inside `{"run_id": ..., "status": "success", "execution_time_seconds": ..., "output": pack.model_dump(), "agents": [...]}`. Furthermore, Sample 1 and 2 output examples currently contain stale `0.0` values.
- **Action**:
  1. Update `scripts/generate_examples.py` so its output structure matches `run.py`'s `POST /run` response format identically.
  2. Re-run `python scripts/generate_examples.py` to regenerate all 3 sample output JSON files with accurate fields and non-zero calibrated values.
- **Acceptance Criteria**: All 3 files in `output_examples/` validate against the exact JSON schema returned by `POST /run`.

---

### Item 10: Build Automated FastAPI & CLI Test Suite (`tests/test_api.py`)
- **Priority**: P2 (Test Coverage & CI/CD)
- **Status**: Ready for Implementation
- **Files**: [`tests/test_api.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/), [`requirements.txt`](file:///C:/Users/Asus/Desktop/Open Agent/requirements.txt)
- **Problem**: There are zero tests for `run.py`, FastAPI endpoints (`GET /health`, `POST /run`), CLI argument parsing, or HTTP error responses. Additionally, `httpx` is needed by `starlette.testclient` / `fastapi.testclient` but is omitted from `requirements.txt`.
- **Action**:
  1. Add `httpx>=0.25.0` to `requirements.txt`.
  2. Create `tests/test_api.py` using `fastapi.testclient.TestClient(app)`:
     - Test `GET /health` returns 200 with `"status": "ok"`.
     - Test `POST /run` with valid payload returns 200, matching output schema.
     - Test `POST /run` with invalid facility/medicine returns 404 with structured error detail.
     - Test CLI execution function `--cli` completes without exception.
- **Acceptance Criteria**: `python -m pytest tests/test_api.py -q` executes with 100% pass rate.

---

### Item 11: Production Dockerfile Hardening & Container Networking
- **Priority**: P2 (Packaging & Judge Portability)
- **Status**: Ready for Implementation
- **Files**: [`Dockerfile`](file:///C:/Users/Asus/Desktop/Open Agent/Dockerfile), [`.dockerignore`](file:///C:/Users/Asus/Desktop/Open Agent/.dockerignore), [`README.md`](file:///C:/Users/Asus/Desktop/Open Agent/README.md)
- **Problem**: `Dockerfile` lacks a `HEALTHCHECK` directive. There is no `.dockerignore` file, meaning `.git`, `.pytest_cache`, `tests/`, and large files (`drug-shortages-0001-of-0001.json.zip`) are copied into the Docker build context. Furthermore, instructions for container-to-host networking (`--add-host=host.docker.internal:host-gateway`) are undocumented.
- **Action**:
  1. Create `.dockerignore` ignoring `.git`, `.pytest_cache`, `__pycache__`, `*.zip`, `.env`, `logs/*.jsonl`.
  2. Add `HEALTHCHECK` to `Dockerfile` using Python's standard `urllib.request`.
  3. Document Docker build and run commands with host networking in `README.md`.
- **Acceptance Criteria**: Docker builds without bloated context, health check passes, and container networking is clearly documented.

---

### Item 12: Publish Zetaris Source Registration & LMIS Export Contract Docs
- **Priority**: P2 (Sponsor Tech Deliverables & Hackathon Polish)
- **Status**: Ready for Implementation
- **Files**: [`scripts/register_zetaris_sources.md`](file:///C:/Users/Asus/Desktop/Open Agent/scripts/), [`data/lmis_export_contract.md`](file:///C:/Users/Asus/Desktop/Open Agent/data/), [`README.md`](file:///C:/Users/Asus/Desktop/Open Agent/README.md)
- **Problem**: Execution Plan Section 8 (DC-8.7 & DC-11.1) requires `scripts/register_zetaris_sources.md` (exact SQL/REST commands for registering Postgres, CSV/Parquet, and openFDA in Zetaris) and `lmis_export_contract.md` (CSV schema contract for real district drug store LMIS export plug-in). Neither file exists.
- **Action**:
  1. Create `scripts/register_zetaris_sources.md` detailing the exact REST SQL and UI proxy requests to register simulated tables, USAID CSVs, and openFDA web API in Zetaris Lightning.
  2. Create `data/lmis_export_contract.md` documenting the standard CSV ingestion interface for real-world hospital LMIS exports.
  3. Link both in `README.md`.
- **Acceptance Criteria**: Both documentation guides exist and are linked in `README.md`, fulfilling DC-8.7 and DC-11.1.

---

## 🎯 Verification Command Baseline
To verify the full test suite baseline at any time:
```bash
python -m pytest tests -q
```
Current Status: **19 passed in 19.90s**.
