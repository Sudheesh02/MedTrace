import fs from 'node:fs';
import path from 'node:path';
import { dir, RUN_CACHE_DIR } from './paths.js';

function jsonFiles(folder) {
  try {
    return fs.readdirSync(folder).filter((n) => n.endsWith('.json')).map((n) => path.join(folder, n));
  } catch {
    return [];
  }
}

/** Find the most recent stored action pack for a pair: dashboard-run cache first, then output_examples/. */
export function findPack(facility, medicine) {
  const candidates = [
    ...jsonFiles(RUN_CACHE_DIR).map((f) => ({ f, origin: 'dashboard run cache (.cache/runs)' })),
    ...jsonFiles(dir('output_examples')).map((f) => ({ f, origin: 'output_examples/' })),
  ];
  let best = null;
  for (const c of candidates) {
    try {
      const body = JSON.parse(fs.readFileSync(c.f, 'utf8'));
      const out = body.output || body;
      if (out?.facility_id !== facility || out?.medicine_id !== medicine || !Array.isArray(out?.recommendations)) continue;
      const mtime = fs.statSync(c.f).mtimeMs;
      if (!best || mtime > best.mtime) {
        best = { mtime, pack: out, run_id: body.run_id || out.run_id, execution_time_seconds: body.execution_time_seconds ?? null, source: `${c.origin}${path.basename(c.f)}` };
      }
    } catch {
      /* skip */
    }
  }
  return best;
}

export function findMemo(facility, medicine) {
  const f = dir('output', `memo_${facility}_${medicine}.md`);
  try {
    return { path: `output/memo_${facility}_${medicine}.md`, text: fs.readFileSync(f, 'utf8'), mtime: fs.statSync(f).mtime.toISOString() };
  } catch {
    return null;
  }
}
let packIdx = { at: 0, value: null };
/** Pairs that have a stored full action pack (dashboard run cache or output_examples/). key -> {run_id, source} */
export function packPairs() {
  if (packIdx.value && Date.now() - packIdx.at < 20000) return packIdx.value;
  const map = {};
  const candidates = [...jsonFiles(RUN_CACHE_DIR), ...jsonFiles(dir('output_examples'))];
  for (const f of candidates) {
    try {
      const body = JSON.parse(fs.readFileSync(f, 'utf8'));
      const out = body.output || body;
      if (!out?.facility_id || !out?.medicine_id || !Array.isArray(out?.recommendations)) continue;
      const k = `${out.facility_id}/${out.medicine_id}`;
      const mtime = fs.statSync(f).mtimeMs;
      if (!map[k] || mtime > map[k].mtime) map[k] = { mtime, run_id: body.run_id || out.run_id || null, actions: out.recommendations.length, escalated: !!out.escalated_to_human };
    } catch {
      /* skip */
    }
  }
  packIdx = { at: Date.now(), value: map };
  return map;
}