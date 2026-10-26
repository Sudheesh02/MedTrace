// Builds dashboard/data-bundle/: a small, secret-scanned snapshot of the REAL repo files the dashboard reads
// (latest stored trace per pair, action packs, backtest reports, memory traces, triage snapshot), so the
// dashboard can be deployed (e.g. on Vercel) without the parent repo. Usage: npm run bundle-data
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

process.env.DATA_SOURCE = 'repo'; // always read from the live repo, never from a previous bundle
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const repo = process.env.MEDTRACE_ROOT ? path.resolve(process.env.MEDTRACE_ROOT) : path.resolve(root, '..');
const out = path.join(root, 'data-bundle');
if (!fs.existsSync(path.join(repo, 'app', 'agents', 'triage_planner.py'))) {
  console.error(`bundle-data: parent repo not found at ${repo} (needs app/agents/triage_planner.py).`);
  process.exit(1);
}

const SECRETS = [
  [/nvapi-[A-Za-z0-9_-]{16,}/, 'NVIDIA key'],
  [/\bsk-[A-Za-z0-9]{20,}/, 'sk- key'],
  [/\bBearer\s+[A-Za-z0-9._-]{20,}/, 'bearer token'],
  [/\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\./, 'JWT'],
  [/"?(api[_-]?key|secret|password|passwd|access[_-]?token|auth[_-]?token)"?\s*[:=]\s*"[^"\s]{8,}"/i, 'credential assignment'],
  [/postgres(ql)?:\/\/[^\s"'/]+:[^\s"'@]+@/i, 'DB connection string with password'],
  [/\bAKIA[0-9A-Z]{16}\b/, 'AWS key'],
];
function scan(label, text) {
  for (const [re, name] of SECRETS) {
    if (re.test(text)) {
      console.error(`bundle-data: ABORT - possible ${name} found in ${label}. Nothing was published.`);
      process.exit(2);
    }
  }
}

fs.rmSync(out, { recursive: true, force: true });
const put = (rel, text) => {
  scan(rel, text);
  const f = path.join(out, rel);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, text);
};
const copy = (from, rel) => put(rel, fs.readFileSync(from, 'utf8'));

// 1. Triage snapshot from the project's own deterministic TriagePlannerAgent
let snap = null;
const cands = process.env.MEDTRACE_PYTHON ? [process.env.MEDTRACE_PYTHON] : ['python', 'py', 'python3'];
for (const c of cands) {
  try {
    snap = JSON.parse(execFileSync(c, [path.join(here, 'triage_snapshot.py')], { cwd: repo, maxBuffer: 128 * 1024 * 1024, timeout: 120000, windowsHide: true, stdio: ['ignore', 'pipe', 'ignore'] }).toString());
    break;
  } catch {
    /* try next */
  }
}
if (!snap) {
  console.error('bundle-data: could not run scripts/triage_snapshot.py (python not found or failed).');
  process.exit(1);
}
if (!snap.rules || !(snap.rules.critical_cover_days > 0)) {
  console.error('bundle-data: the triage snapshot carries no rules (TRIAGE_RULES missing from app/agents/triage_planner.py).');
  process.exit(1);
}
const { indexTraces, traceFileForRun } = await import(pathToFileURL(path.join(root, 'lib', 'traces.js')).href);
const { dir } = await import(pathToFileURL(path.join(root, 'lib', 'paths.js')).href);
put('triage.json', JSON.stringify({ generated_at: new Date().toISOString(), sim_dir: 'data/simulated (synthetic)', facilities: snap.facilities, medicines: snap.medicines, rules: snap.rules, items: snap.items }));

// 2. Traces: latest per pair + the trace of every stored action pack's run + memory A/B traces
const idx = indexTraces();
const want = new Set(Object.values(idx.latestByPair).map((e) => e.file));
const packs = [];
const addPacks = (folder, prefix) => {
  let names = [];
  try { names = fs.readdirSync(folder).filter((n) => n.endsWith('.json')); } catch { /* none */ }
  for (const n of names) {
    try {
      const body = JSON.parse(fs.readFileSync(path.join(folder, n), 'utf8'));
      const o = body.output || body;
      if (!o?.facility_id || !Array.isArray(o?.recommendations)) continue;
      packs.push({ from: path.join(folder, n), rel: `output_examples/${prefix}${n}` });
      const rid = body.run_id || o.run_id;
      const tf = traceFileForRun(rid); // trace_<id>.jsonl or live_trace_<id>.jsonl
      if (tf) want.add(tf);
    } catch { /* skip */ }
  }
};
addPacks(dir('output_examples'), '');
// The dashboard's own saved runs (.cache/runs) are local scratch and are deliberately not bundled.
// Committed memory A/B: the "before" pack lives in output_examples/live_runs/memory_ab/ (the "after" pack is the live_ pack of the same pair).
const abDir = dir('output_examples', 'live_runs', 'memory_ab');
let abFiles = [];
try { abFiles = fs.readdirSync(abDir).filter((n) => n.endsWith('.json')); } catch { /* none */ }
for (const n of abFiles) {
  const body = JSON.parse(fs.readFileSync(path.join(abDir, n), 'utf8'));
  const tf = traceFileForRun(body.run_id || body.output?.run_id);
  if (tf) want.add(tf);
  packs.push({ from: path.join(abDir, n), rel: `output_examples/live_runs/memory_ab/${n}` });
}
for (const m of ['trace_without_memory.jsonl', 'trace_with_memory.jsonl']) if (fs.existsSync(dir('logs', m))) want.add(m);
for (const f of want) copy(dir('logs', f), `logs/${f}`);
for (const p of packs) copy(p.from, p.rel);
if (fs.existsSync(dir('logs', 'hmem_store.json'))) copy(dir('logs', 'hmem_store.json'), 'logs/hmem_store.json');

// 3. Evaluation reports and memos
for (const n of fs.existsSync(dir('output')) ? fs.readdirSync(dir('output')) : []) {
  if (/^backtest_seed_\d+\.json$/.test(n) || n === 'curated_evaluation.md' || /^memo_[A-Za-z0-9_-]+\.md$/.test(n)) copy(dir('output', n), `output/${n}`);
}

// 4. Index (true counts come from the full local log folder; the bundle only ships the latest trace per pair)
put('index.json', JSON.stringify({
  generated_at: new Date().toISOString(),
  note: 'Snapshot of real MedTrace run outputs. Inventory data is simulated.',
  total_traces: idx.total,
  latestByPair: idx.latestByPair,
  countByPair: idx.countByPair,
  packs: packs.map((p) => p.rel),
}));

let bytes = 0;
let files = 0;
const walk = (d) => { for (const n of fs.readdirSync(d)) { const f = path.join(d, n); const s = fs.statSync(f); if (s.isDirectory()) walk(f); else { bytes += s.size; files += 1; } } };
walk(out);
console.log(`bundle-data: wrote ${files} files, ${(bytes / 1024).toFixed(0)} KiB to data-bundle/ (${want.size} traces, ${packs.length} action packs, ${snap.items.length} triage items). Secret scan passed.`);