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

const isLiveName = (f) => path.basename(f).startsWith('live_');

/** Every stored action pack (top level of the dashboard run cache and output_examples/). */
function scanPacks() {
  const candidates = [
    ...jsonFiles(RUN_CACHE_DIR).map((f) => ({ f, cache: true, origin: 'dashboard run cache (.cache/runs)/' })),
    ...jsonFiles(dir('output_examples')).map((f) => ({ f, cache: false, origin: 'output_examples/' })),
  ];
  const out = [];
  for (const c of candidates) {
    try {
      const body = JSON.parse(fs.readFileSync(c.f, 'utf8'));
      const pack = body.output || body;
      if (!pack?.facility_id || !pack?.medicine_id || !Array.isArray(pack?.recommendations)) continue;
      const real_llm = pack.llm_used === true && pack.fallback === false;
      out.push({
        key: `${pack.facility_id}/${pack.medicine_id}`,
        // The committed live packs are named live_<facility>_<medicine>.json and must be a real LLM answer with no fallback.
        live: !c.cache && isLiveName(c.f) && real_llm,
        real_llm,
        model: pack.model_used ?? null,
        cache: c.cache,
        // A dashboard-run pack wins over a stored one only if it is newer; stored live packs beat other stored packs.
        rank: fs.statSync(c.f).mtimeMs - (!c.cache && !isLiveName(c.f) ? 1e13 : 0),
        pack,
        run_id: body.run_id || pack.run_id || null,
        execution_time_seconds: body.execution_time_seconds ?? null,
        source: `${c.origin}${path.basename(c.f)}`,
      });
    } catch {
      /* skip */
    }
  }
  return out;
}

const best = (list) => list.reduce((a, b) => (!a || b.rank > a.rank ? b : a), null);

/** Pick the pack to show for a pair. */
export function findPack(facility, medicine) {
  return best(scanPacks().filter((p) => p.key === `${facility}/${medicine}`));
}

/** Best committed live pack (live_*.json) for a pair, ignoring dashboard-run packs. */
export function findLivePack(facility, medicine) {
  return best(scanPacks().filter((p) => p.key === `${facility}/${medicine}` && p.live));
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
export function resetPackCache() {
  packIdx = { at: 0, value: null };
}

/** Pairs that have a stored full action pack. key -> {run_id, actions, escalated, live, real_llm, model} */
export function packPairs() {
  if (packIdx.value && Date.now() - packIdx.at < 20000) return packIdx.value;
  const map = {};
  const byKey = {};
  for (const p of scanPacks()) (byKey[p.key] ||= []).push(p);
  for (const [k, list] of Object.entries(byKey)) {
    const b = best(list);
    map[k] = { run_id: b.run_id, actions: b.pack.recommendations.length, escalated: !!b.pack.escalated_to_human, live: b.live, real_llm: b.real_llm, model: b.model, no_action: b.pack.recommendations.every((r) => !Number(r.recommended_units)) };
  }
  packIdx = { at: Date.now(), value: map };
  return map;
}

/** A pack by explicit file under output_examples/ (used for the committed memory A/B "before" pack). */
export function readPackFile(...rel) {
  try {
    const body = JSON.parse(fs.readFileSync(dir('output_examples', ...rel), 'utf8'));
    return { run_id: body.run_id || body.output?.run_id || null, pack: body.output || body };
  } catch {
    return null;
  }
}