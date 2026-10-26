# MedTrace - Submission Checklist

Open Agent Hackathon 2026, Track 2 "The Agent That Can Explain Why". Submissions close **27 Oct 2026 23:45 UTC (28 Oct 05:15 IST)** on HackOS. Sources: `hackathon details/` (Welcome Guide sections 8-9, 6.2, onboarding deck, Zetaris sponsor files).

Status key: **DONE** = verified with the evidence shown. **PARTIAL** = works but something is still open. **MISSING** = not in the repo. **USER** = only the team owner can do it (HackOS form, recording, publishing).

## 1. Submission components (HackOS)

| # | Requirement | Status | Evidence / what is left |
| :-- | :--- | :--- | :--- |
| 1.1 | Demo video, 1-4 min: main workflow, how the agent solves the challenge, Zetaris and Meterless integration | MISSING (USER) | No recording in the repo. Suggested shot list: triage -> `FAC-WH-01/MED-006` live run -> Investigator vs Skeptic debate -> `FAC-CHC-01/MED-001` memory flip (`output_examples/live_runs/memory_ab/` vs `live_FAC-CHC-01_MED-001.json`) -> `DATA_SOURCE_SUMMARY` in a trace. |
| 1.2 | Slide deck: problem and user, solution, architecture, stack, how Zetaris and Meterless were used, what is unique, visuals, future work | MISSING (USER) | No deck in the repo. README and SPONSOR_TECH.md contain the content to lift. |
| 1.3 | Public GitHub repo with all source, README covering setup, usage, dependencies | DONE | README (live links at the top), `requirements.txt`, `.env.example`, `LICENSE` (MIT) are in place. `https://github.com/Sudheesh02/MedTrace` is public and `main` is pushed. |
| 1.4 | Sponsor technology explanation (Zetaris integration; Meterless engines, what each does and the test; Nightshift connection; NVIDIA contribution; what is unique) | DONE | `SPONSOR_TECH.md` (rewritten to match the real setup), plus `metadata.json`. |
| 1.5 | Pre-existing components declared (in repo and in the submission form) | PARTIAL | `PRE_EXISTING_COMPONENTS.md` is complete (first commit 24 Oct 2026 21:32 IST, inside the build window). The HackOS form entry is USER. |
| 1.6 | Project details: name, description, team members, track | PARTIAL | `metadata.json` has name, description, track, one author. The form entry and team list are USER. |
| 1.7 | Team exists on HackOS; submission finalised before 23:45 UTC | MISSING (USER) | Cannot be checked from the repo. |
| 1.8 | Colab links if agents run in Colab | N/A | Agents run locally / in Docker; no Colab used. |

## 2. Technical execution requirements

| # | Requirement | Status | Evidence |
| :-- | :--- | :--- | :--- |
| 2.1 | Zetaris is the data layer and the integration works | DONE | Live runs: `ZetarisDataLayer`/`DATA_SOURCE_SUMMARY` shows 44/44 queries answered by Zetaris, 0 CSV fallbacks (`logs/live_trace_run-*.jsonl`). `smoke_test.py` Zetaris check PASS. Database `MEDTRACE_LH`, 10 FILESTORE tables, `scripts/register_zetaris_medtrace.py`. |
| 2.2 | At least one Meterless engine in a working feature | DONE | World Model (`app/engines/world_model.py`) and H-MEM (`app/engines/hmem.py`); tests W1, W2, H1-H3 in `tests/test_world_model.py`. Live proof: officer rejection of PEER_TRANSFER changes the next live run's top action from PEER_TRANSFER to BATCH_RELEASE (`FAC-CHC-01/MED-001`). |
| 2.3 | Meterless Nightshift is the primary AI provider | DONE | `app/adapters/llm_client.py` priority 1 = Nightshift (`METERLESS_BASE_URL`, `meterless/auto`). `smoke_test.py` LLM check PASS. Live traces record `llm_used: true`, `fallback: false` and the model per event. |
| 2.4 | NVIDIA used where it contributes (Nemotron via Nightshift) | DONE | Live traces show `nvidia/nemotron-3-ultra-550b-a55b` and `nvidia/nemotron-3.5-lightning-30b-a3b`. Role is qualitative only; arithmetic is deterministic. |
| 2.5 | Integration is real, not just mentioned | DONE | Two earlier silent bypasses were found and fixed: orchestrator ignored `USE_ZETARIS`; `run-query` route not tried after a 400. Regression tests in `tests/test_zetaris_telemetry.py`. |
| 2.6 | No keys or credentials committed; `.env` gitignored; `.env.example` has placeholders only | PARTIAL | Working tree and all tracked files scanned clean of `.env` values except the public default `admin@zetaris.com`. `.env` is ignored; `.env.example` is placeholders. **Open:** an older commit (history) contains the local Zetaris admin password in `OVERNIGHT_NOTES.md` and `tests/test_api.py`; redacted in the working tree but still in git history. Rotate that local password (it only protects a local docker stack) or squash history before relying on a public repo. |
| 2.7 | Traces showing how the system reasoned | DONE | `logs/trace_<run_id>.jsonl` per run; committed examples: `logs/sample_trace_*`, `golden_trace_*`, `trace_with(out)_memory.jsonl`, `live_trace_*`. |
| 2.8 | Critique, retries, recovery, escalation (not a fixed chain) | DONE | Investigator vs Skeptic/Number Auditor, up to 3 rounds (`skeptic_rounds` in packs), `escalated_to_human` / `escalation_reason`, flagged `fallback` when no LLM. |
| 2.9 | Reliable execution: runs from a clean clone, offline | DONE | `SAMPLE_MODE=true` default without credentials; CLI sample run OK; `python run.py` API OK (`/health`, `/triage`, `POST /run`, `/memo`, `POST /decision`); Docker image builds, container reports healthy, `POST /run` OK. |
| 2.10 | Repo format: `run.py` entry, `SAMPLE_MODE`, Dockerfile, input/output examples | DONE | `run.py` (API + `--cli`), `SAMPLE_MODE`, `Dockerfile` (python:3.11-slim, HEALTHCHECK), `docker-compose.yml` (fixed: it failed with "POSTGRES_PASSWORD missing" without a `.env`; the unused postgres service was removed), `input_examples/` (3), `output_examples/` (3 sample + 5 live). |
| 2.11 | Tests | DONE | 175 tests passed + 5 skipped (raw-data tests skip on a clean clone), 13 files, no `.env` needed, with `SAMPLE_MODE=true` (see section 4). Tests now isolate H-MEM state via `MEDTRACE_HMEM_FILE` so they no longer pollute the demo memory. |
| 2.12 | Claims in docs are honest | DONE | README/SPONSOR_TECH state that metrics are on simulated data, held-out seeds share the generator, the curated 25-scenario suite is a rule-coverage check, Zetaris holds 10 CSV tables (no cross-engine federation). Wrong "~120,000 rows" claim replaced with measured counts (25,920 ledger rows per seed). |
| 2.13 | Data legal and small, download scripts | DONE | `data/README.md`, `scripts/download_real_data.py`, simulated data generated by script. |

## 3. Judging criteria (100 points)

| Criterion | Pts | Status | What backs it |
| :--- | ---: | :--- | :--- |
| Impact | 30 | DONE (docs) | Clear user (district drug warehouse officer), stockout prevention, approval-ready action pack with provenance. Needs to be told well in video and deck (1.1, 1.2). |
| Technical | 20 | DONE | Deterministic engine, debate loop, World Model, H-MEM, traces, 175 tests, Docker. |
| Innovation | 15 | DONE | Zero LLM arithmetic with Number Auditor, counterfactual verdict-flip, officer-memory that changes decisions. |
| Demo | 15 | MISSING (USER) | Video not recorded (1.1). The live runs and traces needed for it exist. |
| Product & UX | 10 | DONE | Next.js dashboard in `dashboard/`, deployed on Vercel at https://medtrace-dashboard.vercel.app (snapshot mode: stored real runs from the data bundle; `Run analysis` works only on the laptop with the backend running). |
| Sponsor Tech | 10 | DONE | Section 2.1-2.5 above; `SPONSOR_TECH.md`. |

## 4. Verification run (this repo state)

| Layer | Result |
| :--- | :--- |
| `python -m pytest tests -q` (`SAMPLE_MODE=true`) | 175 passed, 5 skipped on a fresh clone with no .env (163 + 12 backtest run separately) |
| CLI, sample mode, `FAC-DH-01/MED-007` | OK |
| CLI, live (`SAMPLE_MODE=false USE_ZETARIS=true`) | OK, Zetaris 44/44 |
| API on :8000 (sample and live) | `/health`, `/triage`, `POST /run`, `/memo`, `POST /decision` OK; response is a superset of `output_examples/` schema |
| `python smoke_test.py` | Both checks PASS (LLM provider, Zetaris REST SQL) |
| Docker | `docker build` OK; container healthy; `POST /run` OK; `docker compose config` OK |

## 5. Live demo packs (real LLM + Zetaris)

| Pair | Case | Run | Top action |
| :--- | :--- | :--- | :--- |
| `FAC-WH-01/MED-006` | stockout risk (0.5 days of cover) | `run-2bceed1c` | PEER_TRANSFER |
| `FAC-WH-02/MED-007` | critical metformin stockout | `run-81de2396` | PEER_TRANSFER, EXPEDITE_PO, EMERGENCY_PURCHASE |
| `FAC-WH-01/MED-011` | cold-chain quarantine | `run-b52e1fcb` | PEER_TRANSFER, BATCH_RELEASE next |
| `FAC-DH-01/MED-007` | ledger vs physical audit drift | `run-33b6e84d` | INVENTORY_AUDIT_ADJUSTMENT |
| `FAC-PHC-02/MED-005` | secure, correct no-action control | `run-a5c8e04f` | MONITOR_BUFFER |
| `FAC-CHC-01/MED-001` | memory changes decision | before `run-fa05aba2`, after `run-781d2661` | PEER_TRANSFER -> BATCH_RELEASE after officer rejection |

Packs: `output_examples/live_*.json` (+ `live_runs/memory_ab/`). Traces: `logs/live_trace_<run_id>.jsonl`.

## 6. Counts

Sections 1-2 (21 items): **14 DONE, 3 PARTIAL, 3 MISSING, 1 N/A**.
- MISSING, all owned by the user and not fixable in code: 1.1 demo video, 1.2 slide deck, 1.7 HackOS team/submission.
- PARTIAL: 1.5 and 1.6 (HackOS form entries), 2.6 (old password in git history).
Section 3 (6 criteria): 5 DONE, 1 MISSING (Demo, video).

## 7. Links and publishing status

- Repo (pushed, `main`): https://github.com/Sudheesh02/MedTrace
- Live dashboard (Vercel, auto-deploys on push to `main`): https://medtrace-dashboard.vercel.app
- Demo video script: `docs/DEMO_VIDEO_SCRIPT.md`
- Still the user's items: record and upload the demo video (1.1), slide deck (1.2), HackOS form and team (1.5, 1.6, 1.7).
