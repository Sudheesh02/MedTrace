# MedTrace - Demo Video Script (Open Agent Hackathon, Track 2: The Agent That Can Explain Why)

Speaker: Sudheesh Singh. Target length: **3:00** (rules: demo video must be 1-4 minutes, showing the main workflow, how the agent solves the challenge, key features, and how Zetaris and Meterless are integrated - Welcome Guide section 12). A **90-second cut** is in Part 3. Optional Hinglish intro/outro is in Part 4.

How to use this file: Part 1 is the main script, beat by beat. Say the lines under **SAY** more or less as written, in your own rhythm. Light edits are fine, but do not add new claims or numbers. If you want to add a number, check it against the "Fact sources" table in Part 7 first.

> **Which dashboard to record:** the live site (https://medtrace-dashboard.vercel.app) is in **snapshot mode**: it serves stored real runs (Nemotron + Zetaris) bundled with the app, so the "Run analysis" button is not available there. The laptop dashboard on http://localhost:3001, with the backend running (`python run.py`), supports **Run analysis** for a fresh live run. Record Beat 3 (live terminal run) and any Run-analysis click on the laptop; use either one for the rest.

Speaking pace used for timing: about 145 words per minute, with pauses for clicks. The main script is about 430 spoken words, which is roughly 2:55 to 3:05 at that pace. Running a little over (up to about 3:30) is fine; the hard limit is 4:00.

Why the script is shaped this way (from `hackathon details/`): judges score Impact 30, Technical 20, Innovation 15, Demo 15, Product and UX 10, Sponsor Tech 10. They reward agents that critique and revise each other, traces that show which model did what, and honesty about limits. They discount hardcoded demo paths and unsupported claims of value. For the NVIDIA prize the submission must "show which model handled the request" - so Beat 5 zooms on the model badge.

---

## Part 1 - Main script (3:00)

### Timing at a glance

| Time | Beat | Screen | Judging criteria it serves |
| :-- | :-- | :-- | :-- |
| 0:00-0:22 | 1. Hook | Title card or dashboard Triage page | Impact |
| 0:22-0:42 | 2. What it is, and the one strict rule | Dashboard, "How MedTrace decides" strip | Innovation, Technical |
| 0:42-0:55 | 3. Live run in the terminal (sped up) | Terminal: `python run.py --cli` | Demo, Technical |
| 0:55-1:35 | 4. Investigator vs Skeptic, result, action plan | Dashboard, FAC-WH-02 / MED-007 | Impact, Product and UX, Technical |
| 1:35-2:00 | 5. The "Why" trace, Zetaris, Nemotron via Nightshift | Why panel and telemetry box | Sponsor Tech, Technical |
| 2:00-2:30 | 6. Memory flip (H-MEM) | Memory flip page, FAC-CHC-01 / MED-001 | Innovation, Sponsor Tech |
| 2:30-2:50 | 7. Honesty: simulated data, what the benchmark is and is not | Evaluation page | Technical (trust), Demo |
| 2:50-3:00 | 8. What's next and close | README on GitHub, then end card | Impact |

---

### Beat 1 | 0:00-0:22 | Hook

**ON SCREEN**
- Start on the dashboard Triage page (`http://localhost:3001`) so the first frame already shows a product, or a plain title card: "MedTrace - the agent that explains why a clinic is about to run out".
- Do not click anything yet. Face-cam is optional; if used, small corner only.

**SAY**
> Okay so, a clinic runs out of metformin, and the patient just gets sent home. One study of public facilities in Punjab found essential medicines were available only about 45 percent of the time. WHO's benchmark is 80. Part of it, honestly, is that stock records don't match what's on the shelf. So I built MedTrace.

(About 52 words. Source of the 45% / 80% figures: a PGIMER study of Punjab public facilities as reported in news coverage - it is a secondhand source, which is why the line says "one study" and not more.)

---

### Beat 2 | 0:22-0:42 | What it is, and the one strict rule

**ON SCREEN**
- Point the cursor at the **"How MedTrace decides"** strip at the top of the Triage page. It reads: numbers by deterministic code, reasoning by agents, decisions by people. Steps: Triage Planner -> Reconciler -> Investigator and Skeptic + Number Auditor -> Action Planner.
- Slowly sweep the cursor along the five steps while talking. Briefly hover the chips (Zetaris, Meterless H-MEM, NVIDIA Nemotron).
- The Zetaris chip now reads "Zetaris Lightning SQL (MEDTRACE_LH)" (fixed). Still do not call it a "federation": it is one Lightning database over CSV tables.

**SAY**
> MedTrace is for a district drug warehouse officer. It checks whether the ledger can be believed, works out why a shortage is forming, and gives the officer an action to approve. One strict rule: the LLM never does arithmetic. Cover, shortfall, order size, all plain code. The models only reason and explain, and a Number Auditor re-checks the figures they quote.

(About 55 words.)

---

### Beat 3 | 0:42-0:55 | Live run in the terminal (sped up)

**ON SCREEN**
- Terminal in the repo folder (`C:\Users\Asus\Desktop\Open Agent`), already running or pre-recorded:
  `python run.py --cli --facility FAC-WH-02 --medicine MED-007`
- Show the start of the run, then cut or speed up (4x to 8x) to the finished **MEDTRACE ACTION PACK SUMMARY**. Put a small on-screen label "sped up" while it is fast-forwarded.
- Freeze for 2 seconds on the lines: Winning Hypothesis, Skeptic Rounds, Top Recommended Action.
- Why sped up: the stored live run of this pair took 124 seconds (`output_examples/live_FAC-WH-02_MED-007.json`, `execution_time_seconds`).

**SAY**
> This is a real run, sped up. Live Zetaris queries, live Nemotron through Meterless. It takes about two minutes, so bas, I'm not making you watch all of it.

(About 26 words.)

---

### Beat 4 | 0:55-1:35 | Investigator vs Skeptic, the result, the action plan

**ON SCREEN**
1. Switch to the browser, **Triage** page. The first load already selects **FAC-WH-02 / MED-007** (metformin, Regional Medical Depot). If it did not, click it in the Critical band. The chip should say **Live run**.
2. KPI strip: just a glance (do not read numbers from the tiles - see the tile/stored-run note below).
3. Detail pane. Scroll to **Investigator vs Skeptic** (two cards side by side). Show the debate-rounds row: R1 rejected 0.65 -> R2 accepted 0.95. Point at "numbers valid" on the Number Auditor badge.
4. Scroll to **Supporting evidence** and show the PO-1272 line: 7,500 units marked DISPATCHED on 2026-10-22, no delivery receipt.
5. Scroll to **Action plan**: Peer transfer 5,180 units from FAC-WH-01 (est. cost $46.62, feasibility 0.9), then Expedite PO ($341.88) and Emergency purchase ($777.00) as alternatives. Open **number provenance** on the first row for one second. Point at "Action-plan audit: passed".

**SAY**
> Here's the result. About four and a half days of cover, and 5,180 units short. The cause is a purchase order marked dispatched with no delivery receipt. Round one, the Investigator says "lost in transit." The Skeptic rejects it, confidence 0.65, because a global shortage was too close to rule out. Round two, more evidence, accepted at 0.95. Then the plan: transfer 5,180 units from the other warehouse, about 47 dollars. The auditor verified all three recommendations.

(About 83 words.)

**Tile vs stored-run note (read before recording).** The tiles in the detail pane come from the quick triage preview, which for this pair shows slightly different figures (cover 4.43 days, shortfall about 2,021 units in `dashboard/data-bundle/triage.json`) than the stored live run (cover 4.58 days, shortfall 5,180.01 units, gap 17.42 days). The dashboard shows an amber note "Stored run vs triage preview" when they differ. Speak only the stored-run numbers (as in the lines above). If the amber note is on screen, optionally add this honest line (about 5 seconds): "That amber note is the dashboard telling you the quick preview and the stored run differ a bit. I left it in on purpose."

---

### Beat 5 | 1:35-2:00 | The "Why" trace, Zetaris, Nemotron via Nightshift

**ON SCREEN**
1. Open the **Why - decision trace** side panel (same pair). Scroll slowly down the timeline: Reconciler, World Model context, Investigator round 1, Skeptic round 1, Investigator round 2, Skeptic round 2, Action Planner, action-plan audit, Zetaris data layer.
2. **Zoom in (browser zoom 150% or a screen-recorder zoom) on a model badge** on an LLM step: `nvidia/nemotron-3-ultra-550b-a55b`. Hold 2 seconds. This is the "show which model handled the request" requirement.
3. Show the **Data source telemetry** box: **44 queries, 44 succeeded, 0 CSV fallback**, with the per-table chips (ledger_daily x13, physical_audit x12, batches x12, ...). Hold 2 seconds.
4. Optional (2 seconds): open "tool / Zetaris query" under the Investigator step to show the `SELECT ... FROM MEDTRACE_LH.purchase_orders ...` confirming query.

**SAY**
> The Why panel shows every step: which agent, which model, how long. Here it's Nemotron 3 Ultra, through Meterless Nightshift. And this box is Zetaris: forty-four queries against my MEDTRACE_LH database, forty-four answered, zero CSV fallbacks. Earlier, yaar, my runs were quietly reading local CSVs. I caught it, fixed it, and now every run counts it.

(About 58 words. Sources: `logs/live_trace_run-81de2396.jsonl` DATA_SOURCE_SUMMARY; SPONSOR_TECH.md section 2.3 "An honest bug record".)

---

### Beat 6 | 2:00-2:30 | Memory flip (Meterless H-MEM)

**ON SCREEN**
1. Click the **Memory flip** tab (or open `http://localhost:3001/#memory`).
2. The primary example is the live before/after pair for **FAC-CHC-01 / MED-001** (paracetamol, a quarantined batch). Left card (before): top action **Peer transfer**. Right card (after): top action **Batch release**. The "What changed" table highlights the changed fields.
3. Point at the green note "Same inputs, checked in the data" - the complete Reconciler record is identical in both traces.
4. Point at "H-MEM beliefs injected in the 'after' run": the recorded officer rejection (PEER_TRANSFER on MED-001: "Neighbouring facilities are also short; officer will not approve a peer transfer.").
5. Point at the amber "Read with care: one real-LLM run each" note.

**SAY**
> Memory. Same clinic, same stock record: a quarantined paracetamol batch. Before, the plan is a peer transfer. The officer rejects it, because the neighbours are short too. H-MEM remembers that. Rerun, identical inputs, and now the top action is releasing the quarantined batch; the transfer drops to third. One real run on each side, so this shows the mechanism working, not a statistic.

(About 63 words. Sources: `output_examples/live_runs/memory_ab/before_FAC-CHC-01_MED-001.json` run-fa05aba2 and `output_examples/live_FAC-CHC-01_MED-001.json` run-781d2661; the rejection is the episode inside the "after" trace's CONTEXT_BUILT `hmem_beliefs`; before: PEER_TRANSFER feasibility 0.9 ranked first; after: BATCH_RELEASE first, PEER_TRANSFER feasibility 0.7 ranked third.)

---

### Beat 7 | 2:30-2:50 | Honesty: simulated data and what the benchmark is

**ON SCREEN**
1. Click the **Evaluation** tab. Hold on the **"simulated data"** badge in the title.
2. Show the per-seed table: seeds 3 and 4 (held-out) F1 94.7% each, naive F1 26.7% and 20.0%.
3. Show the "Not real-world accuracy" bullet in "How to read this", and the Curated rule-coverage suite panel with the negative delta (abstention on clean controls 75.0% vs 87.5%).
4. (Cut back to Triage for one second) Show the Warning band count and the legend info button, to back up the last sentence.

**SAY**
> Quick honesty. All the inventory data is simulated. On the held-out seeds, F1 is 94.7 percent against about 23 for a naive baseline, but I wrote the rules knowing the ten anomaly types, so that's a rule-coverage check, not real-world accuracy. And almost everything shows as Warning, because the supplier-delay flag trips on every pair. That band is coarse.

(About 59 words. Sources in Part 7.)

---

### Beat 8 | 2:50-3:00 | What's next and close

**ON SCREEN**
- Cut to the GitHub repo page (README top, then scroll a little so the architecture diagram shows), then the end card with both URLs in large text: `https://github.com/Sudheesh02/MedTrace` and `https://medtrace-dashboard.vercel.app`.

**SAY**
> Next: real LMIS exports, and an approve button right in the dashboard. Repo is `https://github.com/Sudheesh02/MedTrace`, live dashboard is `https://medtrace-dashboard.vercel.app`. The hosted one shows stored real runs; the agent runs from the repo. Thanks.

(About 33 words - say the URLs slowly, or say "links are on screen" and let the end card carry them. Replace the placeholders before recording.)

---

## Part 2 - Pre-recording checklist

Check these in this order. Laptop is memory-tight (about 2 GB free earlier), so close things first.

**Machine**
- [ ] Close Chrome tabs you do not need (Chrome was the biggest memory user, about 2.7 GB). Close Edge webview, Slack, Discord, Spotify. Keep: Docker Desktop, one browser window, terminal, recorder.
- [ ] Plug in the charger. Windows: Focus Assist / Do Not Disturb ON (no notification pop-ups). Turn off screen savers and sleep.
- [ ] Set display to 1920x1080, 100% scaling if possible (or note the scale and record at 1080p output).
- [ ] Do not restart the laptop between steps: Docker, Zetaris and the dashboard server all have to come back up.

**Backend stack**
- [ ] Start Docker Desktop and the Zetaris stack (UI on `:3000`). If the Zetaris driver exited, restart it (it ran via WSL earlier). Confirm database `MEDTRACE_LH` still has its 10 tables (if not: `python scripts/register_zetaris_medtrace.py`).
- [ ] Meterless Nightshift gateway is running on `:8088` and the NVIDIA key is set in Nightshift's Providers/Setup. `.env` should have `SAMPLE_MODE=false` and `USE_ZETARIS=true` for the live run.
- [ ] Run `python smoke_test.py` - both checks (LLM provider and Zetaris REST SQL) must PASS before you record the live run.
- [ ] Start the backend: `python run.py` (FastAPI on `:8000`). The dashboard header should say "Backend online". (The "Run analysis" button there defaults to sample mode with no LLM; the live run you show comes from the terminal.)
- [ ] Do NOT run `python run.py --record-decision ...` while rehearsing: it writes to `logs/hmem_store.json` (the demo memory). The Memory flip page reads stored traces, so it needs no live action.

**Dashboard**
- [ ] `cd dashboard`, then `npm run build`, then `npm start` (serves on `http://localhost:3001`). Port 3000 belongs to Zetaris.
- [ ] Open `http://localhost:3001` in one clean window. Check: header shows the default pair FAC-WH-02 / MED-007 selected with the **Live run** chip; the "How MedTrace decides" strip is expanded (it remembers collapsed state in local storage - click it open if shut); `/#memory` and `/#eval` load.
- [ ] Check today's triage counts yourself and only say numbers you see. The bundle snapshot (regenerated 2026-10-26 after the supplier-delay rule change) shows 144 pairs: 16 Critical, 53 Warning, 75 Secure. The script does not quote these counts, so a different number on screen will not break a line.
- [ ] Browser zoom 110-125% so text is readable at 1080p. Hide bookmarks bar. Dark theme is the dashboard's own.

**Terminal**
- [ ] PowerShell, large font (Ctrl + mouse wheel, about 18 pt), dark background, cd to `C:\Users\Asus\Desktop\Open Agent`. Clear the screen.
- [ ] Pre-record the live run (it takes about two minutes) as its own clip, then speed it up in editing. Command: `python run.py --cli --facility FAC-WH-02 --medicine MED-007`. A new run writes a new trace file in `logs/`: that is fine, but tell whoever is committing/pushing.
- [ ] Optional second terminal shot for 1 second: `python run.py --cli --triage --top-n 5` (the leaderboard print) - only if time allows.

**Recorder (OBS Studio or Xbox Game Bar Win+G)**
- [ ] Output 1920x1080, 30 fps, MP4 (H.264), around 8-12 Mbps. Record the desktop display, not a single window, if you plan to cut between terminal and browser.
- [ ] Capture mic only (no system audio), unless you want to capture sounds. Record at 48 kHz.
- [ ] Do one 15-second test recording: check audio level, that the cursor is visible, and that text is sharp.
- [ ] Record each beat as a separate take. If the laptop lags, you can stitch takes without redoing everything. Leave 1 second of silence at the start and end of each take.

**Mic and voice**
- [ ] Use a headset or earphone mic if you have one; sit close, about a hand-span from the mic. A quiet room, fan and AC off if possible. Soft surface behind you.
- [ ] Peaks around -12 to -6 dB. If peaks hit 0, turn the mic gain down.
- [ ] Read the script out loud twice first. Speak like you are explaining it to a friend who is smart but not in healthcare. Smile on the hook; it changes your voice.
- [ ] Pause for a breath at each beat break - those are your cut points.
- [ ] The end card should show both links in large text: https://github.com/Sudheesh02/MedTrace and https://medtrace-dashboard.vercel.app (already filled in below).

**After recording**
- [ ] Check final length is between 1:00 and 4:00 and aim for 2:50-3:10. Watch it once at normal speed with sound off: can you still follow the story from the captions/labels alone? If not, add on-screen text labels for the key numbers.
- [ ] Add captions (English). Export MP4 and upload to the place HackOS asks for; put the link in the submission form.

---

## Part 2b - If something breaks live (fallbacks)

| What breaks | What to do instead (all honest) |
| :-- | :-- |
| Dashboard server will not start | Run `npm run build` again, or use `npm run dev` (also :3001). If the repo-mode data is missing, bundle mode works with no parent repo files: it ships real stored runs in `dashboard/data-bundle/` (`npm run smoke:bundle` verifies it). The UI then says "Stored demo runs (snapshot)" and hides "Run analysis" - say so out loud in one sentence. |
| Port 3001 busy | `npx next dev -p 3002` (or any free port). Do not use 3000 (Zetaris). |
| Zetaris is down or the driver exited | Do not fake it. Show the stored live trace evidence instead: the Why panel's telemetry for the stored run (44/44) and `logs/live_trace_run-81de2396.jsonl`. Say: "Zetaris is not running on this laptop right now, so this is the stored live run from earlier." The code also falls back to local CSV automatically and counts it as a fallback, so a live run still works and the trace will say so. |
| Nightshift/Nemotron fails (401, `no_provider_configured`, or timeout) | Check Nightshift is up on :8088 and the NVIDIA key is in its Providers tab. If it will not recover, show the stored live packs (`output_examples/live_*.json`) and the Why panel from the stored run. If you run offline, use `python run.py --cli --sample-mode` and say clearly that sample mode is deterministic text with no LLM (traces then say `fallback: true`). |
| Terminal live run too slow or errors | Use the pre-recorded clip of the run (record it first, and keep it). The live-run line only says "a real run, sped up", so a recording is consistent with the script. |
| Memory flip page shows "not comparable" or a different pair | Open `http://localhost:3001/#memory` after a hard refresh. The primary example is read from `output_examples/live_runs/memory_ab/` and `output_examples/live_FAC-CHC-01_MED-001.json`; if the files are missing, say the sample-mode pair is "secondary evidence" and read it with its caveat (the dashboard says "evidence consistent with memory influencing the decision, not a controlled A/B proof"). Do not claim a flip the page does not show. |
| Default pair is not FAC-WH-02 / MED-007 | Search for "metformin" in the alert filter and click the FAC-WH-02 row. |
| Laptop lags badly | Stop recording, close apps, record beats separately and stitch. Do the terminal clip last when nothing else is running. |
| You flub a line | Do not stop; pause 2 seconds, then say the line again cleanly. Cut the bad take in editing. |

---

## Part 3 - 90-second cut (about 165 spoken words, roughly 70 seconds of speech plus click pauses)

Use this if you want a tighter version (for a social post, or if the 3:00 reads too fast). Same screens as Part 1, fewer words, no terminal beat (or a 3-second flash of it).

| Time | On screen | SAY |
| :-- | :-- | :-- |
| 0:00-0:13 | Triage page | "Clinics run out of metformin and patients get sent home. In one study, public facilities in Punjab had essential medicines about 45 percent of the time. I built MedTrace to catch it early." |
| 0:13-0:26 | "How MedTrace decides" strip | "It's for a district warehouse officer. Every number is plain code, never the LLM. Agents debate why, and the officer decides." |
| 0:26-0:52 | FAC-WH-02 / MED-007: Investigator vs Skeptic cards, then Action plan | "Metformin, 5,180 units short, because a purchase order was marked dispatched but never received. The Investigator says lost in transit. The Skeptic rejects it at 0.65, because a global shortage wasn't ruled out. Round two, accepted at 0.95. The plan: a peer transfer, about 47 dollars." |
| 0:52-1:07 | Why panel, model badge, telemetry box | "Every step is traced with its model, here Nemotron 3 Ultra through Meterless Nightshift. And Zetaris: 44 queries, 44 answered, no CSV fallback." |
| 1:07-1:21 | Memory flip page | "Officer rejects a transfer, H-MEM remembers it. Same inputs, next run recommends releasing the quarantined batch instead. One real run each side." |
| 1:21-1:30 | Evaluation page, then end card | "All data is simulated, and the benchmark is a rule-coverage check, not real-world accuracy. Repo is `https://github.com/Sudheesh02/MedTrace`, dashboard is `https://medtrace-dashboard.vercel.app`." |

---

## Part 4 - Optional Hinglish alt-version (intro + outro only)

Use these instead of Beat 1 and Beat 8's spoken lines if you prefer to speak that way. Keep the middle beats in English because judges read English. If you use Hinglish, add English captions so judges can follow. Keep the hook claim exactly as is (about 45 percent, one study).

**Alt intro (replaces Beat 1, about 20 seconds)**
> Dekho, ek clinic mein metformin khatam ho jaati hai aur patient ko ghar bhej dete hain. Punjab ke public facilities ki ek study mein zaroori dawaiyan sirf lagbhag 45 percent time available thi. WHO ka benchmark 80 hai. Ledger mein stock dikhta hai, par shelf pe hota nahi. Isliye maine MedTrace banaya.

**Alt outro (replaces Beat 8, about 12 seconds)**
> Aage ka plan: real LMIS exports aur dashboard mein approve button. Sab data simulated hai, aur benchmark sirf rule-coverage check hai, real-world accuracy nahi. Repo aur live dashboard ke links screen pe hain. Thanks!

---

## Part 5 - Delivery notes (your voice)

- Honest and a little self-deprecating works. Good places: "bas, I'm not making you watch all of it" (Beat 3) and "my runs were quietly reading local CSVs. I caught it" (Beat 5). Do not add jokes about the sponsors.
- Keep Hinglish to what is written: "bas" and "yaar" in the main script, nothing else.
- Do not say "zero hallucination", "proven", "generalizes", "99%", "production-ready", or "federated". None of those is supported by the repo (see Part 7).
- If a judge only watches the first 30 seconds, they should know: the real problem, the user, the "LLM never does arithmetic" rule, and that this is a working agent. Beats 1-3 do that.
- The word "Skeptic" always goes with "Number Auditor" on first use in Beat 4 (it is "Skeptic + Number Auditor" in the UI). The script says "the auditor" later.

---

## Part 6 - What each Beat shows vs the judging rubric

| Rubric item (Welcome Guide s.13) | Where it shows up in the video |
| :-- | :-- |
| Impact (30): real problem, clear user | Beat 1 (hook), Beat 2 (district drug warehouse officer), Beat 4 (action plan the officer can approve) |
| Technical (20): build, reliability, architecture | Beat 2 (deterministic engine rule), Beat 3 (live CLI run), Beat 5 (trace and telemetry), Beat 7 (honest evaluation) |
| Innovation (15) | Beat 4 (Skeptic rejects, Investigator revises), Beat 6 (memory changes the decision) |
| Demo (15) | The whole video: one pair end to end, then memory, then evaluation |
| Product and UX (10) | Beat 2 and Beat 4 (dashboard, alert list, side-by-side verdicts) |
| Sponsor Tech (10) | Beat 3 and Beat 5 (Zetaris live SQL, Nightshift, Nemotron model badge), Beat 6 (H-MEM) |
| "Agents that challenge and improve each other" | Beat 4 (round 1 rejected at 0.65, round 2 accepted at 0.95) |
| "Clear logs and traceability", "which model handled each request" | Beat 5 |

---

## Part 7 - Fact sources (every claim in the script, and where to verify it)

All paths are relative to `C:\Users\Asus\Desktop\Open Agent`. "Verified" means I read the value from the file when writing this script.

| Claim in the script | Value | Source file |
| :-- | :-- | :-- |
| Punjab public facilities: essential-medicine availability about 45 percent vs WHO benchmark 80 | 45.2% vs 80% | `docs/internal/MedTrace_Research_and_Execution_Plan.md` section 2.1 (S1: PGIMER study, via Medical Dialogues news report; secondhand) |
| Video length rule | 1 to 4 minutes | `hackathon details/Welcome Guide FINAL.md` section 12; onboarding deck `16page.md` ("One to four minutes, agent in action") |
| NVIDIA prize: show which model handled the request | required | `hackathon details/Welcome Guide FINAL.md` (prizes section) |
| Live run time about two minutes | 124.24 s (WH-02/MED-007), 119.86 s and 170.19 s (CHC-01/MED-001 after / before) | `output_examples/live_FAC-WH-02_MED-007.json`, `output_examples/live_FAC-CHC-01_MED-001.json`, `output_examples/live_runs/memory_ab/before_FAC-CHC-01_MED-001.json` |
| WH-02 / MED-007 stored live run: cover 4.58 days, shortfall 5,180.01 units, gap 17.42 days, usable stock 1,363 | as stated | `output_examples/live_FAC-WH-02_MED-007.json` (run-81de2396), also `RECONCILE_COMPLETE` in `logs/live_trace_run-81de2396.jsonl` |
| Cause: PO-1272 (7,500 units) marked DISPATCHED 2026-10-22, no delivery receipt | as stated | same file, `winning_hypothesis.supporting_evidence` |
| Debate: round 1 rejected at confidence 0.65 (top hypothesis 0.85 vs 0.75 for global shortage, delta 0.10 within the 0.15 threshold); round 2 accepted at 0.95 (delta 0.45); `skeptic_rounds` 2 | as stated | `SkepticAgent ROUND_1_EVALUATION` and `ROUND_2_EVALUATION` in `logs/live_trace_run-81de2396.jsonl` |
| Action plan: peer transfer 5,180.01 units from FAC-WH-01, est. $46.62, feasibility 0.9; expedite PO $341.88; emergency purchase $777.00; audit passed with 3 verified | as stated | `output_examples/live_FAC-WH-02_MED-007.json` (`recommendations`, `action_plan_audit`) |
| Model on LLM steps: nvidia/nemotron-3-ultra-550b-a55b, `llm_used` true, `fallback` false | as stated | `output_examples/live_FAC-WH-02_MED-007.json`; per-step in `logs/live_trace_run-81de2396.jsonl` |
| Nemotron reached through Meterless Nightshift, model `meterless/auto` | as stated | `README.md` technology table, `SPONSOR_TECH.md` section 4.1 |
| Zetaris telemetry: database MEDTRACE_LH, 44 queries attempted, 44 ok, 0 CSV fallbacks (9 tables queried in this run; 10 tables registered) | as stated | `DATA_SOURCE_SUMMARY` in `logs/live_trace_run-81de2396.jsonl`; `SPONSOR_TECH.md` section 2.1 and 2.3 |
| Honest bug: earlier runs silently read local CSV; fixed and counted, with regression tests | as stated | `SPONSOR_TECH.md` section 2.3 ("An honest bug record"), `tests/test_zetaris_telemetry.py` |
| Zetaris scope is one Lightning database over CSV filestore tables (no federation claim) | as stated | `SPONSOR_TECH.md` section 2.1 |
| LLM never does arithmetic; all numbers from the deterministic engine; Number Auditor re-checks quoted figures | as stated | `README.md` section 4.2 / Executive Summary, `app/engine/deterministic.py`, dashboard `components/HowItWorks.js` |
| Memory flip: CHC-01 / MED-001 before (run-fa05aba2): top action PEER_TRANSFER (feasibility 0.9); after officer rejection (run-781d2661): top action BATCH_RELEASE, PEER_TRANSFER feasibility 0.7, ranked third | as stated | `output_examples/live_runs/memory_ab/before_FAC-CHC-01_MED-001.json`, `output_examples/live_FAC-CHC-01_MED-001.json` |
| Officer rejection: PEER_TRANSFER on MED-001, "Neighbouring facilities are also short; officer will not approve a peer transfer." | as stated | `hmem_beliefs` in `CONTEXT_BUILT` of `logs/live_trace_run-781d2661.jsonl` |
| Identical inputs: the complete Reconciler record is identical in both traces (I compared the two `RECONCILE_COMPLETE` events: identical) | verified | `logs/live_trace_run-fa05aba2.jsonl` vs `logs/live_trace_run-781d2661.jsonl` |
| Memory flip is one real-LLM run each side, so mechanism, not statistics | as stated | dashboard `components/MemoryCard.js` ("Read with care" note) |
| H-MEM: implemented in the repo, adapted from Meterless's reference design | as stated | `app/engines/hmem.py` header ("Adapted from reference architecture in meterless-repo/engines/hmem/"); `SPONSOR_TECH.md` section 3.2; tests H1-H3 in `tests/test_world_model.py` |
| Held-out seeds 3 and 4: F1 94.7% each; naive baseline F1 26.7% (seed 3) and 20.0% (seed 4), "about 23" = README's 23.4% held-out naive figure; seeds 1 and 2 (tuning) are 94.7% and 90.0% | as stated | `output/backtest_seed_1.json` to `backtest_seed_4.json` (`metrics.anomaly_detection`), `README.md` benchmark table |
| 10 planted anomaly types; the rules were written knowing them; same generator for tuning and held-out seeds; rule-coverage check, not real-world accuracy | as stated | `README.md` "Honest scope" note under the benchmark table |
| Data is simulated (12 facilities x 12 medicines = 144 pairs, 180 days, 25,920 ledger rows per seed) | as stated | `README.md`, `output/backtest_seed_*.json` (`total_transactions_evaluated` 25,920), `dashboard/data-bundle/triage.json` (144 items) |
| Curated 25-scenario suite: abstention on clean controls 75.0% (6/8) vs rules baseline 87.5% (7/8) | as stated | `output/curated_evaluation.md`, `README.md` |
| Stockout recall (100%) and lead time (74.2 days clean) are the same for MedTrace and the baselines, i.e. no earlier-warning advantage claimed | as stated | `output/backtest_summary.md`, `output/backtest_seed_*.json` |
| Triage snapshot: 16 Critical, 53 Warning, 75 Secure of 144; supplier delay flags a pair only when the supplier's p90 slip is 7+ days | as stated | `dashboard/README.md` ("Triage tiers"), `dashboard/data-bundle/triage.json` (generated 2026-10-26, re-check at recording time) |
| Dashboard views: Triage, Memory flip, Evaluation; deep links `/#memory`, `/#eval`; port 3001 | as stated | `dashboard/components/Dashboard.js`, `dashboard/package.json`, `dashboard/README.md` |
| Hosted dashboard is stored real runs (bundle mode); the agent runs from the repo | as stated | `dashboard/README.md` ("Deploying without the parent repo (Vercel)") |
| "Next" items (real LMIS exports, an approve button in the dashboard) | plans, not features | `data/lmis_export_contract.md` exists for the export format; the dashboard has no approve button today (officer decisions go through `POST /decision` or `python run.py --record-decision`) |

**Wording to avoid (found while reading the repo - do not repeat in the video):**
- (FIXED) The dashboard chip used to say "Zetaris federated SQL data layer"; it now says "Zetaris Lightning SQL (MEDTRACE_LH)", matching `SPONSOR_TECH.md` (one Lightning database over CSV tables, not a federation). Keep saying "Zetaris Lightning SQL" or "Zetaris as the data layer".
- (FIXED) `output/backtest_summary.md` used to say "94.7% F1 generalization on unseen facility networks"; it now says 94.7% F1 on simulated planted anomalies, not a generalization claim. Do not say "generalization" in the video.
- The README's executive text uses some strong phrases ("zero hallucinated math", "zero capital lockup"). In the video only say what is backed by the files: numbers come from deterministic code, and on the 25 curated scenarios no ungrounded number claims got through (a regression check by the same author as the rules).
- NVIDIA models: the live traces use Nemotron 3 Ultra (550B) for the pair shown. The README also lists Nemotron 3.5 Lightning 30B, which appears on other runs and on non-LLM steps' labels. Only name the model that is on screen.

**Still open for the submission (not for the video):** slide deck and the HackOS form are yours, per `SUBMISSION_CHECKLIST.md`. The video must be uploaded where HackOS asks. The repo and dashboard links in Beat 8 and the 90-second cut are already filled in.