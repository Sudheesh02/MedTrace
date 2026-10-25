import fs from 'node:fs';
import path from 'node:path';
import { dir, DATA_MODE } from './paths.js';
import { cleanText, hadReasoningLeak } from './text.js';

const SAFE_NAME = /^[A-Za-z0-9._-]+\.jsonl$/;
const MEMORY_FILES = new Set(['trace_without_memory.jsonl', 'trace_with_memory.jsonl']);

const normTs = (ts) => (ts && !/[zZ]|[+-]\d\d:?\d\d$/.test(ts) ? `${ts}Z` : ts);

function readFirstLine(file) {
  const fd = fs.openSync(file, 'r');
  try {
    const buf = Buffer.alloc(8192);
    const n = fs.readSync(fd, buf, 0, buf.length, 0);
    const text = buf.toString('utf8', 0, n);
    const nl = text.indexOf('\n');
    return nl === -1 ? text : text.slice(0, nl);
  } finally {
    fs.closeSync(fd);
  }
}

let indexCache = { at: 0, value: null };

/** Index of every trace file (first line only): file -> {facility, medicine, ts}. Cached 20s. */
export function indexTraces() {
  if (indexCache.value && Date.now() - indexCache.at < 20000) return indexCache.value;
  if (DATA_MODE === 'bundle') {
    // The bundle keeps only the latest trace per pair; the true counts were recorded when it was built.
    try {
      const j = JSON.parse(fs.readFileSync(dir('index.json'), 'utf8'));
      indexCache = { at: Date.now(), value: { entries: Object.values(j.latestByPair || {}), latestByPair: j.latestByPair || {}, countByPair: j.countByPair || {}, total: j.total_traces ?? 0 } };
    } catch {
      indexCache = { at: Date.now(), value: { entries: [], latestByPair: {}, countByPair: {}, total: 0 } };
    }
    return indexCache.value;
  }
  const logs = dir('logs');
  const entries = [];
  let names = [];
  try {
    names = fs.readdirSync(logs).filter((n) => SAFE_NAME.test(n));
  } catch {
    /* logs/ missing */
  }
  for (const name of names) {
    if (MEMORY_FILES.has(name)) continue;
    const full = path.join(logs, name);
    try {
      const first = JSON.parse(readFirstLine(full));
      const d = first.details || {};
      if (!d.facility_id || !d.medicine_id) continue;
      entries.push({
        file: name,
        facility_id: d.facility_id,
        medicine_id: d.medicine_id,
        ts: normTs(first.timestamp) || fs.statSync(full).mtime.toISOString(),
        run_id: first.run_id || null,
      });
    } catch {
      /* skip unreadable / empty trace */
    }
  }
  const latestByPair = {};
  const countByPair = {};
  for (const e of entries) {
    const k = `${e.facility_id}/${e.medicine_id}`;
    countByPair[k] = (countByPair[k] || 0) + 1;
    if (!latestByPair[k] || Date.parse(e.ts) > Date.parse(latestByPair[k].ts)) latestByPair[k] = e;
  }
  indexCache = { at: Date.now(), value: { entries, latestByPair, countByPair, total: names.length } };
  return indexCache.value;
}

export function readTraceEvents(name) {
  if (!SAFE_NAME.test(name)) throw new Error('invalid trace file name');
  const text = fs.readFileSync(dir('logs', name), 'utf8');
  const events = [];
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    try {
      events.push(JSON.parse(line));
    } catch {
      /* ignore partial line */
    }
  }
  return events;
}

function ids(likelihoods, titles) {
  // Titles and likelihood keys are emitted in the same order (H1,H2,H3).
  const keys = Object.keys(likelihoods || {});
  return (titles || []).map((title, i) => ({
    id: keys[i] || `H${i + 1}`,
    title,
    likelihood: keys[i] !== undefined ? likelihoods[keys[i]] : null,
  }));
}

function summarize(ev) {
  const d = ev.details || {};
  switch (ev.action) {
    case 'START_RUN':
      return `Run started for ${d.facility_id} / ${d.medicine_id}`;
    case 'RECONCILE_COMPLETE':
      return `${d.discrepancies_found ?? '?'} discrepancies; usable stock ${d.usable_stock ?? '?'}, shortfall ${d.shortfall ?? '?'}` +
        (d.days_of_cover_trust !== undefined ? `; cover ${d.days_of_cover_trust} d (naive ${d.days_of_cover_naive} d)` : '');
    case 'CONTEXT_BUILT':
      return `World model built (canon ${String(d.canon_hash || '').slice(0, 8)})` + (d.hmem_beliefs ? '; H-MEM beliefs injected' : '');
    case 'HYPOTHESES_GENERATED':
      return `${d.hypotheses_count ?? (d.titles || []).length} hypotheses: ${(d.titles || []).join(' | ')}`;
    case 'ROUND_1_START':
    case 'ROUND_2_START':
    case 'ROUND_3_START':
      return `Investigator round ${d.round}` + (d.previous_critique ? ' (revising after Skeptic critique)' : '');
    case 'ROUND_1_EVALUATION':
    case 'ROUND_2_EVALUATION':
    case 'ROUND_3_EVALUATION':
      return `${d.accepted ? 'ACCEPTED' : 'REJECTED'} (confidence ${d.confidence}); numbers ${d.numbers_valid ? 'valid' : 'INVALID'}`;
    case 'ACTIONS_RECOMMENDED':
      return `${d.recommendations_count} recommendations; top action ${d.top_action}`;
    case 'ACTION_PLAN_AUDITED':
      return `Action plan audit ${d.passed ? 'PASSED' : 'FAILED'} (${d.verified_count} verified)`;
    case 'HUMAN_ESCALATION':
      return 'Escalated to human officer';
    case 'RUN_COMPLETE':
      return `Run ${d.status || 'complete'}`;
    default:
      return ev.action;
  }
}

/** Turn raw JSONL events into a structured run for the UI. */
export function parseRun(events, file) {
  const start = events.find((e) => e.action === 'START_RUN');
  const rounds = new Map();
  const getRound = (n) => {
    if (!rounds.has(n)) rounds.set(n, { round: n, hypotheses: [], skeptic: null, previous_critique: null });
    return rounds.get(n);
  };
  let currentRound = 1;
  let reconcile = null;
  let hmemBeliefs = null;
  let escalation = null;
  let action = null;
  let audit = null;
  let complete = false;
  let leak = false;

  const steps = events.map((ev, i) => {
    const d = ev.details || {};
    let text = '';
    const rawText = d.llm_reasoning ?? null;
    if (rawText) {
      if (hadReasoningLeak(rawText)) leak = true;
      text = cleanText(rawText);
    }
    const roundMatch = /^ROUND_(\d)_(START|EVALUATION)$/.exec(ev.action || '');
    if (roundMatch) currentRound = Number(roundMatch[1]);
    if (ev.action === 'RECONCILE_COMPLETE') reconcile = d;
    if (ev.action === 'CONTEXT_BUILT' && d.hmem_beliefs) hmemBeliefs = d.hmem_beliefs;
    if (ev.action && /^ROUND_\d_START$/.test(ev.action)) getRound(currentRound).previous_critique = d.previous_critique ? cleanText(d.previous_critique) : null;
    if (ev.action === 'HYPOTHESES_GENERATED') getRound(currentRound).hypotheses = ids(d.likelihoods, d.titles);
    if (roundMatch && roundMatch[2] === 'EVALUATION') {
      getRound(currentRound).skeptic = {
        accepted: !!d.accepted,
        confidence: d.confidence ?? null,
        numbers_valid: d.numbers_valid ?? null,
        critique: cleanText(d.critique),
        flagged: (d.flagged_inconsistencies || []).map(cleanText),
        reasoning: text,
      };
    }
    if (ev.action === 'HUMAN_ESCALATION') escalation = cleanText(d.reason);
    if (ev.action === 'ACTIONS_RECOMMENDED') action = { count: d.recommendations_count, top: d.top_action, reasoning: text };
    if (ev.action === 'ACTION_PLAN_AUDITED') audit = { passed: !!d.passed, verified: d.verified_count, flagged: (d.flagged_inconsistencies || []).map(cleanText) };
    if (ev.action === 'RUN_COMPLETE') complete = true;
    const critique = d.critique ? cleanText(d.critique) : '';
    return {
      i: i + 1,
      ts: normTs(ev.timestamp),
      agent: ev.agent,
      action: ev.action,
      model: ev.model ?? null,
      llm_used: ev.llm_used ?? null,
      fallback: ev.fallback ?? null,
      summary: summarize(ev),
      text: text || critique || '',
      tokens: d.token_usage?.total_tokens ?? null,
    };
  });

  const roundList = [...rounds.values()].sort((a, b) => a.round - b.round);
  const lastWithHyp = [...roundList].reverse().find((r) => r.hypotheses.length);
  const leading = lastWithHyp
    ? [...lastWithHyp.hypotheses].sort((a, b) => (b.likelihood ?? 0) - (a.likelihood ?? 0))[0]
    : null;
  const lastEval = [...roundList].reverse().find((r) => r.skeptic)?.skeptic ?? null;

  return {
    file,
    run_id: start?.run_id || events[0]?.run_id || null,
    facility_id: start?.details?.facility_id ?? null,
    medicine_id: start?.details?.medicine_id ?? null,
    started_at: normTs(start?.timestamp),
    complete,
    reasoning_tag_leak_stripped: leak,
    rounds: roundList,
    leading_hypothesis: leading,
    final_skeptic: lastEval,
    escalation,
    reconcile,
    hmem_beliefs: hmemBeliefs,
    action,
    audit,
    steps,
    models: [...new Set(steps.map((s) => s.model).filter(Boolean))],
  };
}

export function loadRun(file) {
  return parseRun(readTraceEvents(file), file);
}
const summaryCache = new Map();
/** Compact facts about one stored trace (for list badges): models, whether an LLM answered, Skeptic outcome. */
export function summarizeTrace(file) {
  if (summaryCache.has(file)) return summaryCache.get(file);
  let s = null;
  try {
    const run = loadRun(file);
    s = {
      models: run.models,
      llm_used: run.steps.some((x) => x.llm_used === true),
      accepted: run.final_skeptic ? !!run.final_skeptic.accepted : null,
      confidence: run.final_skeptic?.confidence ?? null,
      rounds: run.rounds.length,
      escalated: !!run.escalation,
      complete: !!run.complete,
    };
  } catch {
    s = null;
  }
  summaryCache.set(file, s);
  return s;
}