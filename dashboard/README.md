# MedTrace Dashboard

A small, read-only Next.js dashboard over MedTrace's real run outputs. It shows:

1. **Alerts** for every facility x medicine pair, sorted by severity.
2. **Detail** for the selected alert: Investigator vs Skeptic + Number Auditor verdicts, evidence, and the action plan.
3. **Why** panel: step-by-step trace (agent, step, model, LLM used, fallback).
4. **Memory "decision flip"** card: `trace_without_memory.jsonl` vs `trace_with_memory.jsonl`, with caveats when the runs are not like-for-like.
5. **Evaluation** panel, labelled *simulated data*.

Nothing is hardcoded in the UI; everything is read at request time.

## Run it

```powershell
cd dashboard
npm install
npm run dev        # http://localhost:3001
```

Port note: `3000` is commonly taken by the local Zetaris container (`ZETARIS_BASE_URL=http://localhost:3000`), so the dashboard uses **3001**. To use another port: `npx next dev -p 3000`.

Other commands: `npm run build`, `npm start` (production, port 3001), `npm run smoke` (boots the production server on port 3199 and checks every API route against the real files).

Optional env vars: `MEDTRACE_API` (default `http://localhost:8000`), `MEDTRACE_ROOT` (default: parent folder), `MEDTRACE_PYTHON` (python executable for the triage helper).

## Where each panel gets its data

| Panel | Source (in priority order) |
| --- | --- |
| Alerts | FastAPI `GET /triage` if `python run.py` is reachable; otherwise `scripts/triage_snapshot.py`, which runs the project's own `TriagePlannerAgent.triage_pair()` over `data/simulated` (no LLM, no network, read-only); last resort: latest stored traces. |
| Detail / verdicts | Latest `logs/trace_*.jsonl` for the pair (or the trace of the stored action pack's run). |
| Evidence / action plan | Action pack JSON: `.cache/runs/*.json` (saved by "Run analysis") or `output_examples/*.json`; `output/memo_<facility>_<medicine>.md` if present. If no pack exists the UI says so and shows only what the trace records. |
| Why | Same trace, every event. `<think>` reasoning leaks are stripped before display. |
| Memory card | `logs/trace_without_memory.jsonl`, `logs/trace_with_memory.jsonl`, `logs/hmem_store.json`. |
| Evaluation | `output/backtest_seed_*.json` (simulated 180-day replay) and a pointer to `output/curated_evaluation.md`. |

## "Run analysis"

The button appears only when the backend answers `GET /health`. Start it with `python run.py` (FastAPI on :8000). The dashboard sends `POST /run` (sample mode is ticked by default, so no LLM calls) and stores the response under `dashboard/.cache/runs/` so the full action pack can be re-opened. When the backend is offline the dashboard shows the most recent stored runs.

## Honesty notes

- Inventory data and all evaluation numbers are **simulated**; the UI labels them so.
- `logs/*.jsonl` (except the tracked sample/golden/memory traces) are git-ignored, so a fresh clone has far fewer stored runs than a working copy. Pairs without a stored run say so.
- Traces record only the count and top action of the Action Planner; full order quantities come from an action pack.
- The memory card reports "no flip" or "not comparable" when the files do not support a flip, and flags differing reconciler inputs.
## UI

The UI is a dark, Linear/Datadog-style triage layout: KPI strip (counts by severity, from the live alert data), severity-banded alert list (master), detail pane with side-by-side Investigator vs Skeptic cards, a vertical decision-trace timeline, and separate Memory flip and Evaluation views (deep links: `/#memory`, `/#eval`). Icons: lucide-react. Screenshots are in `dashboard/screenshots/`.

## Triage tiers

Tiers come unchanged from `app/agents/triage_planner.py`. The thresholds live in its `TRIAGE_RULES` dict (the code uses the same dict), the engine returns them with the triage result, and the dashboard shows what it receives (backend `/triage`, `scripts/triage_snapshot.py`, or the `rules` field in `data-bundle/triage.json`). Nothing parses Python source any more, so the legend cannot drift: **Critical** if trust-adjusted cover < 7 days or shortfall > 0; **Warning** if cover < 14 days or any anomaly is detected; otherwise **Secure**.

Supplier delay is evidence-based: the Planner takes the p90 delivery slip of the supplier on the pair's latest purchase order (`data/simulated/suppliers.csv`, the same source the Reconciler uses) and counts `supplier_delay_risk` as an anomaly only when that slip is 7 days or more (the Reconciler's chronic-slip threshold). Shorter slips still widen the delivery window used for the shortfall and Monte Carlo, they just do not flag the pair. Pairs with no purchase order have no supplier evidence and are not flagged. Earlier versions applied a fixed 3-day slip and flagged every pair, which made every pair at least Warning (11 Critical / 133 Warning / 0 Secure); the current snapshot is 16 Critical / 53 Warning / 75 Secure (16 Critical rather than 11 because suppliers with a 14-day p90 slip now widen the shortfall window, exactly as in the deep investigation). The UI splits Warning into sub-bands for readability: low cover, other anomaly, supplier-delay flag only. The Warning band is collapsed by default; Critical is ranked by the engine's urgency score. The first load selects FAC-WH-02 / MED-007 (the live real-LLM run) when it exists, otherwise the top critical pair with a stored full action pack. Keyboard: up/down (or j/k) moves through the list; on mobile the list drills into the detail with a back button.

## Deploying without the parent repo (Vercel)

```powershell
npm run bundle-data   # needs the parent repo + python; writes dashboard/data-bundle/ (about 500 KiB)
npm run build
npm run smoke         # live repo mode
npm run smoke:e2e     # repo mode + combined e2e: starts the backend (python run.py, sample mode, Zetaris off) on :8000, checks Backend online + alerts from /triage, runs an analysis through POST /api/run, checks the new pack, stops the backend, checks offline mode, then removes the files it created
npm test               # node --test tests/ (run-token guard, rules shipped in the bundle, no source parsing)
npm run smoke:bundle  # copies the build + bundle to a temp dir with NO parent files and checks bundle mode
```

`bundle-data` copies real files only: the triage snapshot (run through the project's own engine), the latest stored trace per pair plus the traces behind stored action packs and the memory A/B traces, `output_examples/` and run-cache packs, `backtest_seed_*.json`, `curated_evaluation.md` and memos. It never copies `.env`, aborts if its secret scan (API-key, bearer, JWT, DB-URL patterns) matches anything, and `dashboard/.gitignore` un-ignores the bundle's `*.jsonl`. The app uses the bundle when `DATA_SOURCE=bundle`, or automatically when the parent repo's engine is not next to `dashboard/`. In that mode the UI says **Stored demo runs (snapshot)**, "Run analysis" is hidden and `POST /api/run` answers 503. Stored-run counts come from the real log folder at bundle time (`index.json`); only the latest trace per pair ships.

## Live runs (real LLM + Zetaris)

A trace counts as **live** only if the trace itself shows it: an LLM step ran, no step has `fallback: true`, and its `DATA_SOURCE_SUMMARY` event has `use_zetaris: true` with `queries_ok > 0`. Packs written to `output_examples/live_*.json` with `llm_used: true` and `fallback: false` get the **Live run** chip; the Why panel shows the Zetaris query telemetry from that event. Traces are read from `logs/live_trace_<run_id>.jsonl` (falling back to `trace_<run_id>.jsonl`). The Memory view's primary example is the live before/after pair under `output_examples/live_runs/memory_ab/`; "same inputs" is only claimed when the full Reconciler record is identical in both traces (the app compares it). The older sample-mode pair stays as secondary evidence with its caveat. Run analysis resets the alert/pack/trace caches so the new pack shows up immediately.

## Protecting "Run analysis" (optional)

Set `MEDTRACE_RUN_TOKEN` in the dashboard's environment to require `Authorization: Bearer <token>` (or `x-medtrace-token`) on `POST /api/run`; without it the route is open, which is the local default. The UI asks for the token once per browser tab when the server answers 401. In snapshot mode (hosted bundle) the route already answers 503.
