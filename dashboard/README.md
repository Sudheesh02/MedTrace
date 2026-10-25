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