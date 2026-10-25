// Smoke test: boots the production server (building first if needed) and checks that every
// API route returns non-empty data that matches the real files.
//   node scripts/smoke.mjs             -> reads the live parent repo (default)
//   node scripts/smoke.mjs --isolated  -> copies the built app + data-bundle to a temp dir OUTSIDE the repo
//                                         (no parent files, no DATA_SOURCE hint) so auto-detect must serve the
//                                         bundle. This simulates a Vercel-style deployment without the repo.
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const repo = path.resolve(root, '..');
const ISOLATED = process.argv.includes('--isolated') || process.env.SMOKE_MODE === 'isolated';
const PORT = Number(process.env.SMOKE_PORT || (ISOLATED ? 3198 : 3199));
const base = `http://localhost:${PORT}`;
const nextBin = path.join(root, 'node_modules', 'next', 'dist', 'bin', 'next');

let failures = 0;
const check = (name, cond, extra = '') => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? `  (${extra})` : ''}`);
  if (!cond) failures += 1;
};
const getJson = async (p) => {
  const r = await fetch(base + p);
  let body = null;
  try { body = await r.json(); } catch { /* ignore */ }
  return { status: r.status, body };
};

if (!fs.existsSync(path.join(root, '.next', 'BUILD_ID'))) {
  console.log('No production build found; running next build...');
  const b = spawnSync(process.execPath, [nextBin, 'build'], { cwd: root, stdio: 'inherit' });
  if (b.status !== 0) { console.error('build failed'); process.exit(1); }
}

let appDir = root;
let isoDir = null;
if (ISOLATED) {
  if (!fs.existsSync(path.join(root, 'data-bundle', 'index.json'))) { console.error('no data-bundle; run npm run bundle-data first'); process.exit(1); }
  isoDir = fs.mkdtempSync(path.join(os.tmpdir(), 'medtrace-iso-'));
  for (const n of ['.next', 'package.json', 'next.config.mjs', 'data-bundle']) fs.cpSync(path.join(root, n), path.join(isoDir, n), { recursive: true });
  fs.symlinkSync(path.join(root, 'node_modules'), path.join(isoDir, 'node_modules'), 'junction');
  appDir = isoDir;
  const parentHasEngine = fs.existsSync(path.join(path.dirname(isoDir), 'app', 'agents', 'triage_planner.py'));
  console.log(`isolated copy at ${isoDir}; parent repo files visible: ${parentHasEngine}`);
}

const env = { ...process.env };
if (ISOLATED) { delete env.DATA_SOURCE; delete env.MEDTRACE_ROOT; }
const server = spawn(process.execPath, [nextBin, 'start', '-p', String(PORT)], { cwd: appDir, stdio: ['ignore', 'pipe', 'pipe'], env });
let serverLog = '';
server.stdout.on('data', (d) => (serverLog += d));
server.stderr.on('data', (d) => (serverLog += d));
const stop = () => {
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(server.pid), '/T', '/F'], { stdio: 'ignore' });
  else server.kill('SIGTERM');
};

try {
  let up = false;
  for (let i = 0; i < 60 && !up; i++) {
    try { up = (await fetch(`${base}/api/backend`)).ok; } catch { await new Promise((r) => setTimeout(r, 1000)); }
  }
  check('server starts', up);
  if (!up) throw new Error(`server did not start\n${serverLog}`);

  const page = await fetch(base + '/');
  const html = await page.text();
  check('GET / renders', page.status === 200 && html.includes('MedTrace'));
  check('page has a title and icon metadata', /<title>MedTrace/.test(html) && /rel="icon"/.test(html));
  const ico = await fetch(base + '/icon.svg');
  check('favicon /icon.svg is served', ico.status === 200 && /svg/.test(ico.headers.get('content-type') || ''));

  const be = await getJson('/api/backend');
  check('/api/backend returns a reachability flag', typeof be.body?.reachable === 'boolean', `reachable=${be.body?.reachable}`);

  const al = await getJson('/api/alerts');
  const items = al.body?.items || [];
  check('/api/alerts non-empty', al.status === 200 && items.length > 0, `${items.length} items via ${al.body?.source}`);
  check('alerts sorted by severity score', items.every((x, i) => i === 0 || items[i - 1].urgency_score >= x.urgency_score));
  const r = al.body?.rules;
  check('tier thresholds come from the engine source', !!r && r.critical_cover_days > 0 && r.warning_cover_days > r.critical_cover_days, JSON.stringify(r));
  check('every alert carries run info', items.every((x) => typeof x.stored_runs === 'number' && typeof x.has_pack === 'boolean'));
  const counts = al.body?.counts || {};
  check('severity counts add up', (counts.CRITICAL || 0) + (counts.WARNING || 0) + (counts.SECURE || 0) === items.length, JSON.stringify(counts));
  const defaultPick = items.filter((x) => x.urgency_tier === 'CRITICAL' && x.has_pack);
  check('a critical pair with a stored action pack exists (auto-select target)', defaultPick.length > 0, defaultPick[0] ? `${defaultPick[0].facility_id}/${defaultPick[0].medicine_id}` : '');

  if (!ISOLATED) {
    const facCsv = path.join(repo, 'data', 'simulated', 'facilities.csv');
    if (fs.existsSync(facCsv) && al.body?.source !== 'traces') {
      const rows = fs.readFileSync(facCsv, 'utf8').trim().split(/\r?\n/).length - 1;
      const facs = new Set(items.map((x) => x.facility_id));
      check('alerts cover every facility in data/simulated/facilities.csv', facs.size === rows, `${facs.size} vs ${rows}`);
    }
  } else {
    check('isolated: served from the bundle', al.body?.mode === 'bundle' && al.body?.source === 'bundle', `${al.body?.mode}/${al.body?.source}`);
    check('isolated: label is "Stored demo runs (snapshot)"', al.body?.source_label === 'Stored demo runs (snapshot)');
    check('isolated: backend reported unreachable', be.body?.reachable === false);
    const run = await fetch(base + '/api/run', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ facility_id: 'x', medicine_id: 'y' }) });
    const rb = await run.json().catch(() => ({}));
    check('isolated: run analysis declines gracefully', run.status === 503 && /snapshot/i.test(rb.error || ''), rb.error);
    const idx = JSON.parse(fs.readFileSync(path.join(appDir, 'data-bundle', 'index.json'), 'utf8'));
    check('isolated: stored-run counts match the bundle index', items.every((x) => (x.stored_runs || 0) === (idx.countByPair[`${x.facility_id}/${x.medicine_id}`] || 0)));
  }

  const withRun = defaultPick[0] || items.find((x) => x.stored_runs > 0);
  if (withRun) {
    const d = await getJson(`/api/detail?facility=${withRun.facility_id}&medicine=${withRun.medicine_id}`);
    check('/api/detail returns trace steps', d.status === 200 && d.body?.run?.steps?.length > 0, `${withRun.facility_id}/${withRun.medicine_id}, ${d.body?.run?.steps?.length} steps`);
    check('detail has Skeptic verdict', !!d.body?.run?.final_skeptic);
    if (defaultPick[0]) check('detail carries the stored action pack', Array.isArray(d.body?.pack?.recommendations) && d.body.pack.recommendations.length > 0);
    check('no <think> tags in detail output', !/<\/?think>/i.test(JSON.stringify(d.body)));
  } else {
    check('at least one alert has a stored run', false, 'no trace matched any alert pair');
  }
  const bad = await getJson('/api/detail?facility=..%2F..&medicine=x');
  check('detail rejects bad ids', bad.status === 400);

  const dataRoot = ISOLATED ? path.join(appDir, 'data-bundle') : repo;
  const mem = await getJson('/api/memory');
  const memFiles = ['trace_without_memory.jsonl', 'trace_with_memory.jsonl'].every((f) => fs.existsSync(path.join(dataRoot, 'logs', f)));
  check('/api/memory matches presence of trace files', memFiles ? mem.status === 200 && !!mem.body?.verdict : mem.status === 404, `verdict=${mem.body?.verdict}`);

  const ev = await getJson('/api/eval');
  const seedFiles = fs.existsSync(path.join(dataRoot, 'output')) ? fs.readdirSync(path.join(dataRoot, 'output')).filter((n) => /^backtest_seed_\d+\.json$/.test(n)) : [];
  check('/api/eval matches output/backtest_seed_*.json', ev.body?.seeds?.length === seedFiles.length && (seedFiles.length === 0 || ev.status === 200), `${ev.body?.seeds?.length} seeds`);
} catch (e) {
  failures += 1;
  console.error(String(e?.message || e));
} finally {
  stop();
  if (isoDir) { try { fs.rmSync(isoDir, { recursive: true, force: true }); } catch { /* ignore */ } }
}

if (!ISOLATED && fs.existsSync(path.join(root, 'data-bundle'))) {
  const stack = [path.join(root, 'data-bundle')];
  const envs = [];
  while (stack.length) {
    const d = stack.pop();
    for (const n of fs.readdirSync(d)) {
      const f = path.join(d, n);
      if (fs.statSync(f).isDirectory()) stack.push(f);
      else if (/^\.env/.test(n)) envs.push(f);
    }
  }
  check('data-bundle contains no .env files', envs.length === 0, envs.join(', '));
}

console.log(failures ? `\nSMOKE FAILED (${failures})` : '\nSMOKE OK');
process.exit(failures ? 1 : 0);
