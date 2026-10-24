# MedTrace Senior Reviewer Audit & Prioritized Overnight Backlog

**Audit Timestamp**: 2026-10-25 02:05 UTC  
**Reviewer Role**: Senior Staff Engineer & Hackathon Judge Auditor  
**Evaluation Target**: Open Agent Hackathon 2026 — Track 2 (*The Agent That Can Explain Why*)  
**Status**: Application code unchanged in this step. Audit complete; 12 prioritized, concrete items identified below.

---

## 🏛 Executive Audit Summary

MedTrace has built an impressive foundation: deterministic arithmetic is isolated from LLM code paths, 12 essential medicines and empirical supplier slip distributions are collected, Meterless World Model and H-MEM engines are sketched, and the 180-day replay harness measures lead time advantages.

However, a rigorous inspection of **README claims vs real code** reveals 7 critical vulnerabilities and gaps that would severely penalize technical scoring:
1. **Zetaris Query Bridge is Dead Code**: In [`app/adapters/data_store.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/adapters/data_store.py#L44), `_query_zetaris` is defined but **never called anywhere in the codebase**. All methods read local CSVs directly, meaning Zetaris (worth 10 mandatory sponsor tech points) is bypassed even when configured.
2. **The Multi-Agent Debate Loop is a Fixed Chain in Practice**: Across all 80+ trace logs in `logs/`, `ROUND_2` has **never occurred even once**. In [`app/agents/skeptic.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/skeptic.py), review thresholds accept hypotheses on Round 1 in 100% of runs, violating the hackathon requirement for visible critique loops, retries, and revisions.
3. **Ghost Stock Date Synchronization Flaw (Sample 1 & 2 Bug)**: [`run.py --cli --sample-mode --facility FAC-DH-01 --medicine MED-007`](file:///C:/Users/Asus/Desktop/Open Agent/run.py) (the flagship Metformin demo) outputs **0.0 recommended units** because today's ledger (day 180, 6,412 units) is compared directly against an audit count from day 165 (7,219 units) without date alignment, causing `audit_drift` to evaluate to `0.0`.
4. **Hardcoded Facility/Medicine IDs in Benchmark Engine**: In [`app/backtest/engine.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/backtest/engine.py#L243-L359), anomaly detection relies on explicit `if fac == "FAC-DH-01" and med == "MED-007":` blocks rather than evaluating generalizable anomaly detection across all facilities.
5. **Runtime NameError on Type Inspection**: [`app/agents/investigator.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/investigator.py#L19) uses `Optional[str]` without importing `Optional` from `typing`, throwing `NameError` whenever annotations are inspected.
6. **Missing World Model Conflict Tracking & H-MEM Contradiction Resolution**: Execution Plan Phase 4 tests (Test W2: conflict recording; Test H2: contradicting decisions resolving deterministically) are missing from engine implementations.
7. **API Contract Mismatch & Silent Failures**: `output_examples/` schemas diverge from `run.py`'s `POST /run` response format, and invalid facilities/medicines silently hallucinate 90-unit shortfalls instead of returning HTTP 404/422.

---

## 📋 Prioritized Overnight Backlog (Max 12 Concrete Items)

### Item 1: Fix `InvestigatorAgent` Typing Bug (`Optional` NameError) & Schema Enums [DONE]
- **Priority**: P0 (Immediate Stability)
- **Status**: Completed & Verified
- **Files**: [`app/agents/investigator.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/investigator.py#L7), [`app/models/schemas.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/models/schemas.py#L9), [`tests/test_agents.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_agents.py)
- **Problem**: `Optional` is used on line 19 of `investigator.py` but never imported from `typing`, causing runtime `NameError` in Python <3.14 and reflection tools. Furthermore, `AnomalyType` in `schemas.py` only defines 8 anomalies, missing `UNRECORDED_EMERGENCY_TRANSFER` and `COLD_CHAIN_TEMPERATURE_EXCURSION` from the 10 planted simulation anomalies.
- **Action**: Import `Optional` in `investigator.py`. Add the two missing enum values to `AnomalyType` in `schemas.py`. Added regression test `test_investigator_annotations_and_anomaly_types` verifying annotations and that all 10 simulation anomalies in `ground_truth.csv` map to `AnomalyType`.
- **Acceptance Criteria**: `python -c "import app.agents.investigator; print(app.agents.investigator.InvestigatorAgent.investigate.__annotations__)"` executes with exit code 0. All 10 simulation anomalies map cleanly to `AnomalyType`. Tested & 100% passing.

---

### Item 2: Wire Real Zetaris SQL Execution into `DataStore` with Graceful Fallback
- **Priority**: P0 (Sponsor Tech 10 pts)
- **Files**: [`app/adapters/data_store.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/adapters/data_store.py#L44-L140), [`.env.example`](file:///C:/Users/Asus/Desktop/Open Agent/.env.example#L6)
- **Problem**: `_query_zetaris` is dead code. All data reads unconditionally read local CSV files even when `use_zetaris=True`. Additionally, `.env.example` defines `ZETARIS_REST_URL=http://localhost:8888/api/v1.0`, while code and README expect `ZETARIS_BASE_URL=http://localhost:3000`.
- **Action**: Update `DataStore` getters (`get_facilities`, `get_medicines`, `get_batches`, `get_latest_ledger`, `get_purchase_orders`) to query `_query_zetaris()` when `self.use_zetaris=True`, falling back to local files when Zetaris is unreachable. Standardize `.env.example` to `ZETARIS_BASE_URL=http://localhost:3000`.
- **Acceptance Criteria**: With `use_zetaris=True`, getters attempt the Zetaris REST query and fall back gracefully to CSV without crashing. `.env.example` matches `smoke_test.py` and `README.md`.

---

### Item 3: Activate Multi-Agent Adversarial Debate (Skeptic Challenge & Revision Rounds)
- **Priority**: P0 (Track 2 Core Rubric — Innovation & Technical)
- **Files**: [`app/agents/skeptic.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/skeptic.py#L50-L75), [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/orchestrator.py#L90-L123), [`tests/test_agents.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_agents.py)
- **Problem**: In 100% of runs, the Skeptic accepts the hypothesis on Round 1 (`skeptic_rounds: 1`). Across all logs, `ROUND_2` never runs. The system operates as a fixed chain rather than an adversarial debate.
- **Action**: Recalibrate Skeptic review criteria: in Round 1, require explicit secondary corroboration queries for high-impact hypotheses, causing the Skeptic to issue targeted critique notes. Investigator adjusts likelihoods and supplies corroborating data in Round 2 before final Skeptic approval.
- **Acceptance Criteria**: In contested investigations, trace logs record `ROUND_1_EVALUATION` (challenge) followed by `ROUND_2_START` and `HYPOTHESES_GENERATED` with revised likelihoods. `skeptic_rounds >= 2` is verified by a dedicated test in `tests/test_agents.py`.

---

### Item 4: Fix Date-Synchronized Reconciliation for Ghost Stock (Sample 1 & 2 0.0-Unit Bug)
- **Priority**: P1 (Demo & Correctness)
- **Files**: [`app/adapters/data_store.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/adapters/data_store.py#L105-L121), [`app/engine/deterministic.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/engine/deterministic.py#L201-L205)
- **Problem**: When running `python run.py --cli --sample-mode --facility FAC-DH-01 --medicine MED-007`, the system calculates `days_of_cover_trust = 104.75 days` and recommends **0.0 units** because it compares the latest ledger stock (from day 180) against an audit count from day 165. Because stock was consumed over those 15 days, `ledger_stock` < `counted_stock`, calculating `audit_drift = 0.0`.
- **Action**: In `data_store.py` / `deterministic.py`, compare the physical count against the ledger stock *on the audit date* (or account for consumption between the audit date and the current date) to compute true phantom drift.
- **Acceptance Criteria**: Running CLI for `FAC-DH-01` and `MED-007` accurately identifies 50 units of phantom drift, flags `GHOST_STOCK`, calculates trust-adjusted cover gap, and recommends non-zero replenishment units.

---

### Item 5: Eliminate Hardcoded Facility & Medicine IDs in `BacktestEngine`
- **Priority**: P1 (Methodological Rigor & Technical Integrity)
- **Files**: [`app/backtest/engine.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/backtest/engine.py#L240-L360)
- **Problem**: Anomaly detection inside `BacktestEngine.run_backtest()` explicitly checks `fac == "FAC-DH-01" and med == "MED-007"`, `fac == "FAC-PHC-01" and med == "MED-004"`, etc. A judge reading the code will see that anomaly scoring is hardcoded to planted entities rather than evaluating generic multi-agent detection.
- **Action**: Replace entity hardcoding with generalized evaluation logic: scan all `(facility, medicine)` pairs using deterministic variance thresholds (`audit_variance >= 45`), expiry windows (`0 <= days_to_expiry <= 7`), UOM delivery ratios (`rec_qty >= po_qty * 8.0`), and supplier slip thresholds.
- **Acceptance Criteria**: All 10 anomalies are detected generically across any facility and medicine without hardcoded entity string literals. Benchmark numbers remain accurate and reproducible.

---

### Item 6: Implement Meterless World Model Conflict Tracking & Ingest (Test W2)
- **Priority**: P1 (Sponsor Tech & Headless State)
- **Files**: [`app/engines/world_model.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/engines/world_model.py#L12-L55), [`tests/test_world_model.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_world_model.py)
- **Problem**: Execution Plan Phase 4 explicitly specifies Test W2: "all planted conflicts of types 1, 4, 7, 8 are recorded as conflicts." However, `WorldStoreService` only stores entities and edges; conflict ingestion and retrieval are unimplemented.
- **Action**: Add `conflicts: List[Dict[str, Any]]` to `WorldStoreService` with `record_conflict()` and `get_conflicts()` methods. Update `IngestPipelineService` to record discrepancy conflicts during reconciliation.
- **Acceptance Criteria**: Discrepancies found during reconciliation are written to the World Model conflict store. A new test `test_world_model_conflict_recording` passes in `tests/test_world_model.py`.

---

### Item 7: Implement H-MEM Deterministic Contradiction Resolution (Test H2)
- **Priority**: P1 (Sponsor Tech & Cognitive Architecture)
- **Files**: [`app/engines/hmem.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/engines/hmem.py#L43-L83), [`tests/test_world_model.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/test_world_model.py)
- **Problem**: Execution Plan Phase 4 specifies Test H2: "a later contradicting decision resolves the conflict deterministically." Currently, `record_officer_decision()` permanently appends to `rejected_patterns`. If an officer later approves a previously rejected action, the rejection penalty is never cleared.
- **Action**: Update `record_officer_decision()` to resolve contradictions: when an action type is approved for a facility, remove or neutralize conflicting entries in `rejected_patterns` and update preference weightings deterministically.
- **Acceptance Criteria**: A new test `test_hmem_contradiction_resolution` verifies that an approval following a rejection clears the penalty and updates recommendations accordingly.

---

### Item 8: Input Entity Validation & Structured Error Responses in API / CLI
- **Priority**: P1 (Production Quality & API Robustness)
- **Files**: [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/orchestrator.py#L43-L67), [`run.py`](file:///C:/Users/Asus/Desktop/Open Agent/run.py#L33-L63)
- **Problem**: Passing `facility_id="INVALID"` and `medicine_id="INVALID"` silently creates an investigation, invents a 90-unit shortfall, and returns `stockout_prevented=True` with recommended transfers to non-existent facilities.
- **Action**: In `orchestrator.py`, validate that `facility_id` exists in `data_store.get_facilities()` and `medicine_id` in `data_store.get_medicines()`. In `run.py`, raise `HTTPException(status_code=404, detail="...")` for unrecognized entity IDs.
- **Acceptance Criteria**: Requesting an invalid facility or medicine raises HTTP 404 in FastAPI and prints a clean validation error in CLI mode instead of generating false inventory recommendations.

---

### Item 9: Synchronize `output_examples/` with Live API Response Schema
- **Priority**: P2 (Documentation & Contract Integrity)
- **Files**: [`output_examples/*.json`](file:///C:/Users/Asus/Desktop/Open Agent/output_examples/), [`run.py`](file:///C:/Users/Asus/Desktop/Open Agent/run.py#L42-L56)
- **Problem**: `run.py` wraps the action pack inside `{"output": pack.model_dump(), "agents": [...], "execution_time_seconds": ...}`, but the 3 files in `output_examples/` place `ActionPack` fields directly at the root, missing `execution_time_seconds` and `agents`. Automated API tests or judges comparing responses against `output_examples/` will see schema divergence.
- **Action**: Re-generate the 3 sample output JSON files using the exact JSON format returned by `POST /run` (with non-zero shortfall numbers from calibrated Sample 1 and 2).
- **Acceptance Criteria**: `output_examples/` JSON files match the exact schema returned by `POST /run`.

---

### Item 10: Build Automated FastAPI & CLI Test Suite (`tests/test_api.py`)
- **Priority**: P2 (Test Coverage & CI/CD)
- **Files**: [`tests/test_api.py`](file:///C:/Users/Asus/Desktop/Open Agent/tests/)
- **Problem**: There are zero tests for `run.py`, FastAPI endpoints (`GET /health`, `POST /run`), or CLI argument parsing. A regression in the API entry point would not be caught by `pytest`.
- **Action**: Create `tests/test_api.py` using `fastapi.testclient.TestClient`. Test:
  1. `GET /health` returns 200 with status ok and sample_mode.
  2. `POST /run` with valid payload returns 200 and schema-compliant response.
  3. `POST /run` with invalid facility returns 404 error.
  4. CLI execution function runs without exceptions.
- **Acceptance Criteria**: `python -m pytest tests -q` executes all API tests with 100% pass rate.

---

### Item 11: Real Surplus Validation for Peer Transfers in Action Planner
- **Priority**: P2 (Operational Credibility)
- **Files**: [`app/agents/action_planner.py`](file:///C:/Users/Asus/Desktop/Open Agent/app/agents/action_planner.py#L38-L51)
- **Problem**: `ActionPlannerAgent` recommends transferring units from `FAC-WH-01` without checking whether `FAC-WH-01` actually holds usable stock of that medicine.
- **Action**: Query `DataStore` / `WorldModel` for candidate peer facilities holding surplus stock (>30 days cover) of `medicine_id`. If no peer warehouse has surplus, lower transfer feasibility score and promote PO expediting or emergency purchase.
- **Acceptance Criteria**: Transfer recommendations only select source facilities with verified physical surplus.

---

### Item 12: Docker Container Networking & Production Healthcheck
- **Priority**: P2 (Packaging & Judge Portability)
- **Files**: [`Dockerfile`](file:///C:/Users/Asus/Desktop/Open Agent/Dockerfile), [`README.md`](file:///C:/Users/Asus/Desktop/Open Agent/README.md)
- **Problem**: `Dockerfile` lacks a `HEALTHCHECK` directive. Additionally, inside a container, `localhost:3000` or `127.0.0.1:8088` refers to the container itself, preventing connectivity to host Zetaris or Meterless Nightshift without `host.docker.internal`.
- **Action**: Add `HEALTHCHECK` to `Dockerfile`. Document container-to-host networking (`--add-host=host.docker.internal:host-gateway`) in `README.md` for judges evaluating via Docker.
- **Acceptance Criteria**: Container builds cleanly, passes health check, and README clearly explains how containerized MedTrace accesses host sponsor services.

---

## 🎯 Verification Command Baseline
To verify the test suite baseline at any time:
```bash
python -m pytest tests -q
```
Current Status: **11 passed in 1.31s**.
