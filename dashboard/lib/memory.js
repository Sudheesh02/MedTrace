import fs from 'node:fs';
import { dir } from './paths.js';
import { loadRun, traceFileForRun } from './traces.js';
import { findLivePack, readPackFile } from './packs.js';

const safeRun = (name) => {
  try {
    return name && fs.existsSync(dir('logs', name)) ? loadRun(name) : null;
  } catch {
    return null;
  }
};

function snapshot(run) {
  if (!run) return null;
  const last = run.rounds.filter((r) => r.skeptic).slice(-1)[0];
  const r = run.reconcile || {};
  return {
    file: run.file,
    run_id: run.run_id,
    started_at: run.started_at,
    facility_id: run.facility_id,
    medicine_id: run.medicine_id,
    rounds: run.rounds.length,
    final_accepted: last?.skeptic?.accepted ?? null,
    final_confidence: last?.skeptic?.confidence ?? null,
    leading_hypothesis: run.leading_hypothesis,
    escalated: !!run.escalation,
    escalation: run.escalation,
    top_action: run.action?.top ?? null,
    recommendations: run.action?.count ?? null,
    inputs: { discrepancies_found: r.discrepancies_found ?? null, usable_stock: r.usable_stock ?? null, shortfall: r.shortfall ?? null, expiring_units: r.expiring_units ?? null },
    reconcile_json: run.reconcile ? JSON.stringify(run.reconcile) : null,
    context: run.context,
    hmem_beliefs: run.hmem_beliefs,
    models: run.models,
    live: run.live,
    data_source: run.data_source,
    llm_steps: run.llm_steps,
    fallback_steps: run.fallback_steps,
    round_detail: run.rounds.map((x) => ({ round: x.round, accepted: x.skeptic?.accepted ?? null, confidence: x.skeptic?.confidence ?? null })),
  };
}

function beliefsAreEmpty(b) {
  if (!b) return true;
  return !(b.past_episodes?.length || Object.keys(b.officer_preferences || {}).length || b.rejected_patterns?.length || Object.keys(b.supplier_delays || {}).length);
}

/** Keys that differ between two flat objects (values compared as JSON). */
const diffKeys = (a, b) => {
  const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
  return [...keys].filter((k) => JSON.stringify(a?.[k]) !== JSON.stringify(b?.[k]));
};

function compare(without, withMem, extra = {}) {
  const samePair = without.facility_id === withMem.facility_id && without.medicine_id === withMem.medicine_id;
  const changes = [];
  if (without.top_action !== withMem.top_action) changes.push({ field: 'Top recommended action', without: without.top_action, with: withMem.top_action });
  if (without.escalated !== withMem.escalated) changes.push({ field: 'Escalated to human', without: String(without.escalated), with: String(withMem.escalated) });
  if (without.final_accepted !== withMem.final_accepted) changes.push({ field: 'Skeptic final verdict', without: without.final_accepted ? 'accepted' : 'rejected', with: withMem.final_accepted ? 'accepted' : 'rejected' });
  if (without.leading_hypothesis?.title !== withMem.leading_hypothesis?.title) changes.push({ field: 'Leading hypothesis', without: without.leading_hypothesis?.title, with: withMem.leading_hypothesis?.title });
  if (without.rounds !== withMem.rounds) changes.push({ field: 'Debate rounds', without: String(without.rounds), with: String(withMem.rounds) });
  if (without.final_confidence !== withMem.final_confidence) changes.push({ field: 'Skeptic confidence', without: String(without.final_confidence), with: String(withMem.final_confidence) });

  const confounders = [];
  for (const k of ['discrepancies_found', 'usable_stock', 'shortfall']) {
    if (without.inputs[k] !== withMem.inputs[k]) confounders.push(`${k}: ${without.inputs[k]} -> ${withMem.inputs[k]}`);
  }
  // "Same inputs" is only claimed when the complete recorded Reconciler record is byte-identical in both traces.
  const inputsIdentical = !!without.reconcile_json && without.reconcile_json === withMem.reconcile_json;
  const contextDiff = diffKeys(without.context, withMem.context);
  const memoryPresent = !beliefsAreEmpty(withMem.hmem_beliefs);
  const decisionChanged = changes.some((c) => ['Top recommended action', 'Escalated to human', 'Skeptic final verdict', 'Leading hypothesis'].includes(c.field));

  let verdict;
  let headline;
  if (!samePair) {
    verdict = 'not_comparable';
    headline = 'The two traces are for different facility/medicine pairs, so they are not comparable.';
  } else if (!decisionChanged) {
    verdict = 'no_flip';
    headline = 'The stored traces do not show a decision flip.';
  } else if (!memoryPresent) {
    verdict = 'changed_without_memory_evidence';
    headline = 'The decision differs, but the "with memory" trace has no recorded H-MEM beliefs, so memory cannot be credited.';
  } else if (!inputsIdentical || confounders.length) {
    verdict = 'flip_with_confounders';
    headline = 'The decision differs and H-MEM beliefs were injected, but the reconciler inputs also differ between the two runs, so memory is not the only change.';
  } else {
    verdict = 'flip';
    headline = 'The decision differs, H-MEM beliefs were injected, and the recorded reconciler inputs are identical in both runs.';
  }
  return { verdict, headline, same_pair: samePair, changes, confounders, inputs_identical: inputsIdentical, context_diff: contextDiff, memory_present: memoryPresent, without, with: withMem, ...extra };
}

/** Committed live A/B: output_examples/live_runs/memory_ab/before_<pair>.json is the run before an officer rejection was stored; the live pack of the same pair is the run after. */
function liveComparison() {
  let names = [];
  try {
    names = fs.readdirSync(dir('output_examples', 'live_runs', 'memory_ab')).filter((n) => /^before_.+\.json$/.test(n));
  } catch {
    return null;
  }
  for (const n of names) {
    const before = readPackFile('live_runs', 'memory_ab', n);
    if (!before?.pack?.facility_id) continue;
    const after = findLivePack(before.pack.facility_id, before.pack.medicine_id);
    if (!before.run_id || !after?.run_id) continue;
    const w = snapshot(safeRun(traceFileForRun(before.run_id)));
    const m = snapshot(safeRun(traceFileForRun(after.run_id)));
    if (!w || !m) continue;
    return compare(w, m, {
      kind: 'live',
      title: 'Live A/B on real LLM + Zetaris: before vs after an officer rejection',
      before_label: 'Before: no officer feedback in H-MEM',
      after_label: 'After: officer rejection stored in H-MEM',
      sources: [`output_examples/live_runs/memory_ab/${n}`, after.source, w.file && `logs/${w.file}`, m.file && `logs/${m.file}`].filter(Boolean),
    });
  }
  return null;
}

function legacyComparison() {
  const without = snapshot(safeRun('trace_without_memory.jsonl'));
  const withMem = snapshot(safeRun('trace_with_memory.jsonl'));
  if (!without || !withMem) return null;
  return compare(without, withMem, {
    kind: 'legacy',
    title: 'Earlier stored pair: trace_without_memory vs trace_with_memory',
    before_label: 'Without memory',
    after_label: 'With H-MEM',
    sources: ['logs/trace_without_memory.jsonl', 'logs/trace_with_memory.jsonl'],
  });
}

export function getMemoryComparison() {
  let store = null;
  try {
    store = JSON.parse(fs.readFileSync(dir('logs', 'hmem_store.json'), 'utf8'));
  } catch {
    /* no store file (it is created at run time and is not committed) */
  }
  const live = liveComparison();
  const legacy = legacyComparison();
  const primary = live || legacy;
  if (!primary) {
    return { ok: false, reason: 'No before/after trace pair found (looked for output_examples/live_runs/memory_ab/ and logs/trace_without_memory.jsonl + trace_with_memory.jsonl).', store };
  }
  return { ok: true, ...primary, secondary: live ? legacy : null, store };
}