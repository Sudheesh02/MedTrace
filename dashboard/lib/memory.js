import fs from 'node:fs';
import { dir } from './paths.js';
import { loadRun } from './traces.js';

const safeRun = (name) => {
  try {
    return fs.existsSync(dir('logs', name)) ? loadRun(name) : null;
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
    hmem_beliefs: run.hmem_beliefs,
    round_detail: run.rounds.map((x) => ({ round: x.round, accepted: x.skeptic?.accepted ?? null, confidence: x.skeptic?.confidence ?? null })),
  };
}

function beliefsAreEmpty(b) {
  if (!b) return true;
  return !(b.past_episodes?.length || Object.keys(b.officer_preferences || {}).length || b.rejected_patterns?.length || Object.keys(b.supplier_delays || {}).length);
}

export function getMemoryComparison() {
  const without = snapshot(safeRun('trace_without_memory.jsonl'));
  const withMem = snapshot(safeRun('trace_with_memory.jsonl'));
  let store = null;
  try {
    store = JSON.parse(fs.readFileSync(dir('logs', 'hmem_store.json'), 'utf8'));
  } catch {
    /* no store */
  }
  if (!without || !withMem) {
    return { ok: false, reason: 'trace_without_memory.jsonl and/or trace_with_memory.jsonl not found in logs/.', without, with: withMem, store };
  }

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
  } else if (confounders.length) {
    verdict = 'flip_with_confounders';
    headline = 'The decision differs and H-MEM beliefs were injected, but the reconciler inputs also differ between the two runs, so memory is not the only change.';
  } else {
    verdict = 'flip';
    headline = 'The decision differs, H-MEM beliefs were injected, and reconciler inputs match.';
  }
  return { ok: true, verdict, headline, same_pair: samePair, changes, confounders, memory_present: memoryPresent, without, with: withMem, store };
}