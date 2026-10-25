# CORRECTIVE (monitor, 2026-10-25 10:50 IST) - [ALL COMPLETED & VERIFIED]
- [x] [DONE] The anomaly F1 evaluation was unhardcoded: BacktestEngine now derives evaluation bounds dynamically from ground truth trigger schedules rather than hardcoded 160..178 slice. In README/SPONSOR_TECH, numbers are honestly labeled as planted anomaly detection on synthetic multi-tier simulation data with 10 planted failure modes, avoiding misleading "multi-agent reasoning accuracy" labels.
- [x] [DONE] SPONSOR_TECH.md reworded to transparently state "live cloud connections testable via smoke_test.py with user credentials" and "103/103 automated tests verified".
- [x] [DONE] Priority 0 item 7 complete: tracked sanitized sample trace `logs/sample_trace_FAC-DH-01_MED-007.jsonl` in git via `.gitignore` exception `!logs/sample_trace_*.jsonl`, updated `scripts/explain_trace.py` with automatic clean-clone fallback, and added test in `tests/test_api.py`.

# PRIORITY 0 (from independent blind review, do these before anything else)
1. [x] [DONE] Load .env (python-dotenv) in run.py/app; remove the 127.0.0.1-only gate for Nightshift; actually read METERLESS_MODEL; record the model the API really returned per trace event; add llm_used and fallback flags to every trace line; outside sample mode fail loudly instead of silently returning canned text; test that traced model equals response model.
   - Initialized `python-dotenv` (`load_dotenv()`) in `run.py` and `app/__init__.py`.
   - Removed `127.0.0.1` gate in `LLMClient._init_client()` to support arbitrary Nightshift hostnames/containers.
   - Actively read `METERLESS_MODEL` from env and configure as target model when Meterless is used.
   - Recorded API response model (`getattr(res, "model", None)`) in `actual_model` and logged per trace event.
   - Added boolean `llm_used` and `fallback` flags to 100% of JSONL trace lines and `ActionPack`.
   - Outside sample mode (`SAMPLE_MODE=false`), missing credentials or API exceptions raise `RuntimeError` immediately rather than returning canned text.
   - Added comprehensive automated unit tests in `tests/test_agents.py`: `test_llm_client_reads_meterless_model_and_removes_127_gate`, `test_llm_client_outside_sample_mode_fails_loudly`, and `test_traced_model_equals_response_model_and_flags_in_all_trace_lines`.
2. [x] [DONE] Fix uvicorn.run to "run:app"; POST /run returns 500 on errors; isolate orchestrator state across requests with clean restore.
   - Changed `uvicorn.run("run.py:app", ...)` to `uvicorn.run("run:app", ...)` in `run.py`.
   - Guaranteed `POST /run` cleans up temporary options in `finally` block so overrides do not leak state across sessions.
   - Added automated tests in `tests/test_api.py`: `test_api_run_unhandled_exception_returns_500`.
3. [x] [DONE] Make the LLM matter: investigator ranks hypotheses from evidence pack with structured JSON, skeptic LLM raises challenges, Number Auditor rejects any number not in the evidence pack; added test where debate flips the winner.
   - Updated `InvestigatorAgent` to prompt LLM for structured JSON evaluation and apply likelihood adjustments and qualitative rationale.
   - Enhanced `SkepticAgent` Number Auditor to verify that every quantitative number in candidate hypotheses is grounded in the deterministic evidence pack, rejecting any ungrounded figures.
   - Added automated tests in `tests/test_agents.py`: `test_number_auditor_rejects_hallucinated_numbers_not_in_evidence_pack` and `test_multi_agent_debate_flips_winning_hypothesis`.
4. [x] [DONE] Remove default Zetaris password and raw string SQL vulnerabilities; add identifier sanitization.
   - Eradicated hardcoded `"<REDACTED>"` default password from `DataStore`; requires explicit credentials or falls back cleanly.
   - Implemented `DataStore._sanitize_id` regex validation blocking SQL injection.
   - Added automated tests in `tests/test_data_store.py`: `test_data_store_empty_password_does_not_attempt_zetaris_login` and `test_data_store_sql_identifier_sanitization`.
5. [x] [DONE] Redo the benchmark honestly: naive baseline at the SAME alert threshold, tune on seeds 1-2 and test on 3-4; drop the lead-time headline; report audit accuracy and root-cause accuracy.
   - Unified alert threshold in `BacktestEngine` to 14.0 days across Naive LMIS, Heuristic, and MedTrace.
   - Tuned on seeds 1–2 and verified on held-out seeds 3–4 (94.7% F1 on held-out seeds 3–4; 94.8% F1 overall).
   - Dropped artificial lead-time headline; documented baseline parity on uncorrupted stock and 94.8% root-cause accuracy in `README.md`, `scripts/run_backtest.py`, and `output/backtest_seed_*.json`.
   - Verified 103 unit and integration tests passing cleanly.
6. [x] [DONE] Truth pass on SPONSOR_TECH.md, PRE_EXISTING_COMPONENTS.md, metadata.json, README: correct test counts, remove tests that do not exist, remove claims such as 100% verified or via NVIDIA NIM unless true, label rule-assigned DailyMed fields and invented WHO multipliers / Monte Carlo slip as assumptions, declare the Gemini overnight automation.
   - Completed: `SPONSOR_TECH.md` updated to 103 tests and qualified status badges; `metadata.json` updated to NVIDIA API / Meterless; `data/README.md` and `PRE_EXISTING_COMPONENTS.md` annotate assumptions; Gemini overnight harness declared.
   - Completed verification: `PRE_EXISTING_COMPONENTS.md` line 84 updated to 103 automated tests across 7 test suites; verified by `test_metadata_json_and_docs_integrity` in `tests/test_api.py`.
7. [x] [DONE] Track a sample trace (un-ignore one sanitized logs/*.jsonl) and commit scripts/explain_trace.py wired to --explain.
   - Tracked `logs/sample_trace_FAC-DH-01_MED-007.jsonl` in git with `.gitignore` exception `!logs/sample_trace_*.jsonl`.
   - Wired `scripts/explain_trace.py` `find_latest_trace()` to automatically fall back to the tracked sample trace on fresh clones.
   - Added automated test in `tests/test_api.py`: `test_explain_trace_sample_trace_fallback`.

---

# COMPLETED VERIFIED BASELINE ARCHITECTURE
- [x] [DONE] In-Memory CSV caching and indexed pair lookups in `DataStore` (dropped scan time from 21.2s to 0.04s; full test suite from 85s to 39s).
- [x] [DONE] Synchronized `output_examples/*.json` and `scripts/generate_examples.py` with `action_plan_audit`, `TriagePlannerAgent`, and `MONITOR_BUFFER`.
- [x] [DONE] Integrated `scripts/explain_trace.py` with CLI flag `--explain` in `run.py` and documented in `README.md`.
- [x] [DONE] Unified replenishment horizon in BacktestEngine to 14.0 days across all methods and dropped circular `action_sizing_error_pct` metric.
- [x] [DONE] Created pytest `conftest.py` setting `SAMPLE_MODE=true` and `USE_ZETARIS=false` for clean environment isolation.
- [x] [DONE] Added regression test `test_explain_trace_visualizer_renders_cleanly` in `tests/test_agents.py`.
- [x] [DONE] Standardized HTTP 500 error handling in `run.py` `/run` endpoint.
- [x] [DONE] Subprocess CLI integration tests in `tests/test_api.py` covering `--cli`, `--triage`, and `--record-decision`.
- [x] [DONE] Derived baseline medicine demand dynamically in `BacktestEngine` from catchment-normalized consumption.
- [x] [DONE] Dedicated 30-second judge walkthrough script (`scripts/quick_demo.py`).
- [x] [DONE] Zetaris 4-way federated SQL join test in `tests/test_data_store.py`.
- [x] [DONE] Deterministic budget and financial impact computation in `ActionPlannerAgent` with Number Auditor validation.
- [x] [DONE] Automated clean-clone validation harness (`scripts/validate_clean_clone.py`) passing all 7 gates.
- [x] [DONE] Printable officer procurement memorandum exporter in Markdown (`scripts/export_action_pack.py` and `--export-memo`).
- [x] [DONE] Lightweight `docker-compose.yml` with backend and optional profiled Postgres service.
- [x] [DONE] RxNorm standard packaging multiplier dynamic lookup in `DataStore` and `ReconcilerAgent`.

---

# MedTrace Senior Reviewer Comprehensive Audit & Prioritized Overnight Backlog

**Audit Timestamp**: 2026-10-25 11:45 UTC  
**Reviewer Role**: Senior Staff AI Reviewer & Hackathon Judge Auditor  
**Evaluation Target**: Open Agent Hackathon 2026 — Track 2 (*The Agent That Can Explain Why*)  
**Scope**: README Claims vs. Real Code, Multi-Agent Deliberation Loop, Data Layer, Backtest Engine, Test Suite, FastAPI/CLI App, Dockerfile, Docs, and Hackathon Alignment.  
**Baseline Test Suite**: **103 passed, 1 warning in 114.73s** (100% passing rate across all 7 test suites).  
**Status**: Application code untouched in this audit step. Exactly 12 prioritized, concrete, small items formulated below replacing completed/stale entries.

---

## 🏛 Executive Audit Findings Summary

| Area | Current Code State | Identified Gap / Risk | Judging Impact | Priority |
| :--- | :--- | :--- | :--- | :---: |
| **Docs & Provenance** | 103 tests pass; README, SPONSOR_TECH & PRE_EXISTING_COMPONENTS updated. | Synchronized with 103-test reality across all files; zero stale references. | **Verified** | **DONE** |
| **Sponsor Integration** | `DataStore` queries Zetaris via REST SQL. | Participant Setup Guide lines 786-804 & 1620-1623 & 1799-1808 specify `ZETARIS_REST_URL` (`http://localhost:8888/api/v1.0`) and `POST /sql-editor/sqls/run`. `DataStore` only reads `ZETARIS_BASE_URL` (`http://localhost:3000`) and hits `/api/proxy/sql-editor/sqls/run-query`. | **-4 pts** (Sponsor Tech 10 pts) | **P1** |
| **Multi-Agent Shared State** | World Model builds context; passes to Investigator. | `InvestigatorAgent.investigate()` declares `context: Dict[str, Any]` but never references it in the method body! Skeptic also does not inspect World Model conflicts. | **-4 pts** (Innovation 15 pts / Technical) | **P1** |
| **Output Examples** | 3 input and 3 output samples present. | `ActionRecommendation` in `output_examples/*.json` was not regenerated after financial costs were implemented (`estimated_cost_usd` missing in sample JSONs). | **-2 pts** (Demo 15 pts / Submission Specs) | **P1** |
| **API Ergonomics** | Strict case checking on facility and medicine IDs. | Passing `fac-dh-01` or `med-007` or trailing whitespace raises uncaught 404 `ValueError`. Needs case-insensitive `.strip().upper()` normalization. | **-2 pts** (Product & UX 10 pts) | **P1** |
| **Human Escalation** | Orchestrator sets `escalated_to_human = True`. | `ActionPlannerAgent` is unaware of escalation; formulates autonomous transfer recommendations with high feasibility instead of requiring human authorization. | **-2 pts** (Responsible AI / Technical) | **P1** |
| **FastAPI Document Routes** | CLI exports Markdown memo and renders trace. | FastAPI Swagger UI lacks endpoints to retrieve generated procurement memorandum (`GET /memo/{fac}/{med}`) or latest debate trace (`GET /trace/latest`). | **-2 pts** (Product & UX 10 pts) | **P2** |
| **Backtest Reporting** | Backtest saves JSON and logs to stdout. | Lacks an automated, judge-ready Markdown summary report (`output/backtest_summary.md`) comparing seeds 1–4 side by side with Markdown tables. | **-2 pts** (Technical Depth 20 pts) | **P2** |
| **Triage CLI Flow** | `run.py --triage` scans district portfolio. | Plan §4.2 specifies Triage Planner feeds at-risk items to Reconciler. CLI lacks `--auto-triage` flag to automatically audit the top #1 urgent bottleneck. | **-1 pt** (Technical / Multi-Agent) | **P2** |
| **Dockerfile Defaults** | `SAMPLE_MODE=true` set in Dockerfile ENV. | `Dockerfile` omits explicit `ENV USE_ZETARIS=false`. When running `docker run` directly without compose, explicit ENV prevents confusion. | **-1 pt** (Deployment / Technical) | **P2** |
| **Backtest Performance** | Lead time and anomaly metrics computed. | Backtest engine does not record execution throughput (events/sec, latency, memory delta) valued by sponsors (Meterless & NVIDIA). | **-1 pt** (Sponsor Tech / Technical) | **P2** |
| **Trace Conformance** | Traces emitted in `logs/trace_*.jsonl`. | Lacks an automated conformance validator (`scripts/validate_traces.py`) verifying all JSONL trace lines adhere to Track 2 debate/audit requirements. | **-1 pt** (Test Rigor / Track 2) | **P2** |

---

## 🚀 Prioritized Overnight Backlog (Exactly 12 Concrete, Small Items)

### Item 1: Complete Priority 0 Item 6 — Update Stale Test Count in `PRE_EXISTING_COMPONENTS.md`
- **Priority**: P0 (Docs Integrity, Hackathon Compliance)
- **Status**: [x] [DONE]
- **Files**: [`PRE_EXISTING_COMPONENTS.md`](file:///C:/Users/Asus/Desktop/Open%20Agent/PRE_EXISTING_COMPONENTS.md), [`tests/test_api.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_api.py)
- **Problem**: In `PRE_EXISTING_COMPONENTS.md` line 84, the text states `Comprehensive test suite in tests/ (88 automated tests passing with 100% success rate)`. The test suite has grown to 103 tests across 7 test suites. Leaving "88" violates Priority 0 Item 6 ("truth pass on PRE_EXISTING_COMPONENTS.md... correct test counts").
- **Action**:
  1. In `PRE_EXISTING_COMPONENTS.md` line 84, update "88 automated tests" to "103 automated tests passing with 100% success rate across all 7 test suites".
  2. In `tests/test_api.py` `test_metadata_json_and_docs_integrity`, add assertion verifying `PRE_EXISTING_COMPONENTS.md` references the verified test count (103 tests) and contains zero stale "88 automated tests" references.
- **Acceptance Criteria**: `PRE_EXISTING_COMPONENTS.md` reflects 103 passing tests; verified by `test_metadata_json_and_docs_integrity`.

---

### Item 2: Official Zetaris `ZETARIS_REST_URL` & Dual-Endpoint Compatibility in `DataStore` and `smoke_test.py`
- **Priority**: P1 (Sponsor Tech 10 pts, Participant Guide Compliance)
- **Status**: [ ] [PENDING]
- **Files**: [`app/adapters/data_store.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/adapters/data_store.py), [`smoke_test.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/smoke_test.py), [`.env.example`](file:///C:/Users/Asus/Desktop/Open%20Agent/.env.example), [`tests/test_data_store.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_data_store.py)
- **Problem**: The official Participant Setup Guide (lines 786-804 & 1620-1623 & 1799-1808) defines `ZETARIS_REST_URL=http://localhost:8888/api/v1.0` and `POST /sql-editor/sqls/run`. Currently `DataStore` and `smoke_test.py` only read `ZETARIS_BASE_URL` (defaulting to `http://localhost:3000`) and hit `/api/proxy/sql-editor/sqls/run-query`. If a judge configures `ZETARIS_REST_URL` per the guide, connectivity fails.
- **Action**:
  1. In `DataStore.__init__` and `smoke_test.py`, inspect `ZETARIS_REST_URL` first, falling back to `ZETARIS_BASE_URL`.
  2. In `_query_zetaris`, if the base URL contains `/api/v1.0` or port 8888, target `/sql-editor/sqls/run`. Otherwise fall back to `/api/proxy/sql-editor/sqls/run-query` or try direct `/sql-editor/sqls/run` upon 404.
  3. In `.env.example`, document both `ZETARIS_REST_URL=http://localhost:8888/api/v1.0` and `ZETARIS_BASE_URL=http://localhost:3000`.
  4. Add unit test in `tests/test_data_store.py` verifying that `ZETARIS_REST_URL` is parsed and queries `/sql-editor/sqls/run`.
- **Acceptance Criteria**: Live Zetaris queries succeed whether configured with `ZETARIS_REST_URL` (port 8888 `/sql-editor/sqls/run`) or `ZETARIS_BASE_URL` (port 3000 UI proxy).

---

### Item 3: Wire World Model Shared Context & Conflicts into `InvestigatorAgent` and `SkepticAgent`
- **Priority**: P1 (Innovation 15 pts, Sponsor Tech 10 pts, Reasoning Architecture)
- **Status**: [ ] [PENDING]
- **Files**: [`app/agents/investigator.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/agents/investigator.py), [`app/agents/skeptic.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/agents/skeptic.py), [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/orchestrator.py), [`tests/test_agents.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_agents.py)
- **Problem**: `orchestrator.py` builds `world_context = self.context_builder.build_structured_context(facility_id, medicine_id)` and passes it to `investigator.investigate(recon, world_context, ...)`. However, in `investigator.py` line 19, `context` is completely unreferenced and unused! Furthermore, `SkepticAgent` does not inspect `world_context` or `world_store.get_conflicts(facility_id)`.
- **Action**:
  1. In `InvestigatorAgent.investigate()`, actively extract `facility` metadata (level, catchment), `relationships` (edges like `HOLDS_INVENTORY`), `canon_hash`, and any recorded conflicts from `world_context`. Incorporate them into hypothesis supporting evidence and the LLM prompt.
  2. In `orchestrator.py`, pass `world_context` into `SkepticAgent.review_and_audit()`.
  3. In `SkepticAgent`, verify that candidate hypotheses correlate with recorded World Model conflict entities.
  4. Add automated unit test in `tests/test_agents.py`: `test_investigator_and_skeptic_grounded_in_world_model_context`.
- **Acceptance Criteria**: `context` is actively consumed; hypotheses cite World Model canonical entity IDs (`ent_inv_*`) and canon hashes.

---

### Item 4: Synchronize `output_examples/*.json` via `scripts/generate_examples.py` for Financial Cost Schemas
- **Priority**: P1 (Deliverable Compliance, Technical Execution)
- **Status**: [ ] [PENDING]
- **Files**: [`scripts/generate_examples.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/scripts/generate_examples.py), `output_examples/*.json`, [`tests/test_api.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_api.py)
- **Problem**: In Item 4, `ActionRecommendation` and `ActionPlannerAgent` were updated to compute deterministic financial outlays (`estimated_cost_usd`). However, `output_examples/*.json` was not regenerated, leaving existing sample output files missing `estimated_cost_usd` and differing from the live API response.
- **Action**:
  1. Re-execute `python scripts/generate_examples.py` to regenerate all 3 sample output JSON files.
  2. Verify that each recommendation in `output_examples/*.json` includes valid `estimated_cost_usd` values ($0.00 for monitoring/adjustments, non-zero for transfers/POs).
  3. Add regression test in `tests/test_api.py`: `test_output_examples_schema_and_financial_costs_conformance`.
- **Acceptance Criteria**: 100% of sample output files in `output_examples/` contain valid `estimated_cost_usd` matching the live API output schema.

---

### Item 5: Case-Insensitive & Whitespace-Tolerant Identifier Normalization in Orchestrator and API
- **Priority**: P1 (Product & UX 10 pts, Judge Ergonomics)
- **Status**: [ ] [PENDING]
- **Files**: [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/orchestrator.py), [`run.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/run.py), [`tests/test_agents.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_agents.py)
- **Problem**: When a user runs `python run.py --cli --facility fac-dh-01 --medicine med-007` (lowercase) or provides input with trailing whitespace, `orchestrator.run_investigation` raises an unhandled 404 `ValueError` because facility and medicine ID lookup is strictly case-sensitive.
- **Action**:
  1. In `app/orchestrator.py`, normalize input identifiers: `facility_id = facility_id.strip().upper()` and `medicine_id = medicine_id.strip().upper()`.
  2. In `run.py`, ensure `RunRequest` and `DecisionRequest` strip whitespace and normalize case before delegating to orchestrator.
  3. Add unit test in `tests/test_agents.py`: `test_orchestrator_case_insensitive_and_whitespace_normalization`.
- **Acceptance Criteria**: Inputs like `"fac-dh-01 "` and `"med-007"` resolve cleanly to canonical records without 404 errors.

---

### Item 6: Escalation-Aware Action Recommendation Feasibility and Officer Counter-Signature Annotation
- **Priority**: P1 (Responsible AI, Technical Depth 20 pts)
- **Status**: [ ] [PENDING]
- **Files**: [`app/agents/action_planner.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/agents/action_planner.py), [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/orchestrator.py), [`app/models/schemas.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/models/schemas.py), [`tests/test_agents.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_agents.py)
- **Problem**: When multi-agent debate fails to achieve consensus or confidence falls below 0.50, `orchestrator` correctly sets `escalated_to_human = True`. However, `ActionPlannerAgent` is completely unaware of escalation, generating standard peer transfer recommendations with high feasibility scores rather than noting that human counter-signature is mandatory.
- **Action**:
  1. Pass `escalated_to_human: bool` into `ActionPlannerAgent.plan_actions()`.
  2. When True, reduce autonomous feasibility scores by 0.25 (reflecting unresolved debate) and annotate justifications: `"[ESCALATED TO CONTROLLER] Requires manual clinical review before dispatch authorization"`.
  3. Add automated test in `tests/test_agents.py`: `test_action_planner_adapts_to_human_escalation`.
- **Acceptance Criteria**: Action plans for escalated runs explicitly reflect escalation status in justifications and feasibility scoring.

---

### Item 7: Expose Printable Memorandum & Trace Endpoints on FastAPI (`GET /memo` and `GET /trace/latest`)
- **Priority**: P2 (Product & UX 10 pts, Demo 15 pts)
- **Status**: [ ] [PENDING]
- **Files**: [`run.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/run.py), [`tests/test_api.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_api.py)
- **Problem**: While `run.py --export-memo` generates Markdown procurement memoranda and `explain_trace.py` visualizes debate traces in terminal, judges interacting with the FastAPI web service (`/docs`) have no endpoints to read the generated memorandum or retrieve the latest debate event timeline via HTTP.
- **Action**:
  1. In `run.py`, add `GET /memo/{facility_id}/{medicine_id}` generating and returning the official GitHub-Flavored Markdown procurement memorandum as `text/markdown`.
  2. In `run.py`, add `GET /trace/latest` returning the latest JSONL debate event list structured for frontend or inspection.
  3. Add regression tests in `tests/test_api.py`: `test_api_get_memo_endpoint` and `test_api_get_trace_latest_endpoint`.
- **Acceptance Criteria**: Navigating to `/memo/FAC-DH-01/MED-007` or `/trace/latest` in Swagger UI returns formatted memorandum text and trace events.

---

### Item 8: Automated Comparative Backtest Markdown Summary Exporter (`output/backtest_summary.md`)
- **Priority**: P2 (Impact 30 pts, Evaluation Rigor)
- **Status**: [ ] [PENDING]
- **Files**: [`app/backtest/engine.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/backtest/engine.py), [`scripts/run_backtest.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/scripts/run_backtest.py), [`tests/test_backtest.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_backtest.py)
- **Problem**: `scripts/run_backtest.py` saves JSON results to `output/backtest_seed_N.json` and prints terminal stdout, but lacks an automated, human-readable Markdown summary report (`output/backtest_summary.md`) that judges can immediately view on GitHub.
- **Action**:
  1. In `scripts/run_backtest.py`, format aggregated multi-seed metrics into `output/backtest_summary.md`.
  2. Include comparison table (Naive LMIS vs Heuristic vs MedTrace across lead time, recall, precision, F1, and capital lockup), seed-by-seed breakdown (seeds 1–2 tuning, seeds 3–4 held-out test), and honest methodology notes.
  3. Add automated test in `tests/test_backtest.py`: `test_backtest_summary_markdown_generation`.
- **Acceptance Criteria**: Running `python scripts/run_backtest.py` generates `output/backtest_summary.md` with complete comparative Markdown tables.

---

### Item 9: Triage Planner Integration into Default CLI & Investigation Pipeline (Plan §4.2)
- **Priority**: P2 (Technical 20 pts, Multi-Agent Coordination)
- **Status**: [ ] [PENDING]
- **Files**: [`run.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/run.py), [`app/orchestrator.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/orchestrator.py), [`tests/test_agents.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_agents.py)
- **Problem**: In Execution Plan §4.2, Triage Planner is the upstream agent that proactively scans the district and identifies at-risk targets. Currently, running `python run.py --cli` requires manual `--facility` and `--medicine` arguments (defaulting to FAC-DH-01 / MED-007).
- **Action**:
  1. In `run.py`, add CLI flag `--auto-triage`. When specified, the system runs a proactive district triage scan, selects the #1 highest urgency bottleneck, and seamlessly launches the deep multi-agent audit on that item without manual ID entry.
  2. Add unit test in `tests/test_agents.py`: `test_auto_triage_delegation_flow`.
- **Acceptance Criteria**: `python run.py --cli --auto-triage --sample-mode` scans the district and investigates the top urgent bottleneck in a single pass.

---

### Item 10: Explicit `ENV USE_ZETARIS=false` in `Dockerfile` for Non-Compose Container Execution
- **Priority**: P2 (Technical Deployment, Docker Packaging)
- **Status**: [ ] [PENDING]
- **Files**: [`Dockerfile`](file:///C:/Users/Asus/Desktop/Open%20Agent/Dockerfile), [`tests/test_api.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_api.py)
- **Problem**: `Dockerfile` defines `ENV SAMPLE_MODE=true` and `ENV PORT=8000`, but omits `ENV USE_ZETARIS=false`. When a judge executes `docker run -p 8000:8000 <image>` directly rather than using Docker Compose, declaring `ENV USE_ZETARIS=false` in the image guarantees offline isolation without relying on code fallbacks.
- **Action**:
  1. In `Dockerfile`, add `ENV USE_ZETARIS=false`.
  2. In `tests/test_api.py`, add assertions in `test_docker_compose_configuration` or a dedicated test verifying `Dockerfile` environment variables.
- **Acceptance Criteria**: Dockerfile explicitly sets `ENV USE_ZETARIS=false`.

---

### Item 11: Benchmark Throughput & Resource Metrics in Backtest Engine
- **Priority**: P2 (Technical Depth 20 pts, Sponsor Tech)
- **Status**: [ ] [PENDING]
- **Files**: [`app/backtest/engine.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/app/backtest/engine.py), [`tests/test_backtest.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_backtest.py)
- **Problem**: `BacktestEngine` records statistical accuracy metrics (lead time, recall, F1), but omits computational throughput metrics (replay duration, daily transaction processing rate in events/sec), which sponsor technologies (Meterless & NVIDIA) evaluate for runtime efficiency.
- **Action**:
  1. In `BacktestEngine.run_backtest()`, measure total replay duration, daily transaction throughput (`total_transactions / duration`), and include under a `"performance_benchmarks"` dictionary in the returned results.
  2. Add test in `tests/test_backtest.py`: `test_backtest_performance_benchmarks_metrics`.
- **Acceptance Criteria**: Backtest results include execution duration and transaction throughput metrics.

---

### Item 12: Multi-Agent Audit Trace Conformance Validator Script (`scripts/validate_traces.py`)
- **Priority**: P2 (Reliable Execution, Track 2 "Explain Why")
- **Status**: [ ] [PENDING]
- **Files**: `scripts/validate_traces.py`, [`tests/test_api.py`](file:///C:/Users/Asus/Desktop/Open%20Agent/tests/test_api.py)
- **Problem**: Track 2 judges evaluate audit traces to verify that agents act, critique, and revise outputs rather than running fixed prompt wrappers. There is currently no standalone validator that inspects all generated JSONL traces in `logs/` and asserts Track 2 conformance.
- **Action**:
  1. Author `scripts/validate_traces.py` that validates all traces in `logs/` against schema rules:
     - 100% of lines contain valid `timestamp`, `agent`, `action`, `details`, `model`, `llm_used`, and `fallback` keys.
     - Contains at least 1 `RECONCILE_COMPLETE`, 1 `CONTEXT_BUILT`, 1 `ROUND_1_START`, 1 `ROUND_1_EVALUATION` with critique, 1 `ROUND_2_START` revision, and 1 `ACTION_PLAN_AUDITED`.
     - Zero ungrounded numbers in agent reasoning.
  2. Add unit test in `tests/test_api.py`: `test_trace_conformance_validator_execution`.
- **Acceptance Criteria**: `python scripts/validate_traces.py` validates all logs in `logs/` and exits 0.

---

## 🎯 Verification Command Baseline
To verify the full test suite baseline at any time:
```bash
python -m pytest tests -q
```
Current Baseline Status: **103 passed, 1 warning in ~114s** (100% passing rate across all 7 test suites).
