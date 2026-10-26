// Smoke test: boots the production server (building first if needed) and checks that every
// API route returns non-empty data that matches the real files.
//   node scripts/smoke.mjs             -> reads the live parent repo (default)
//   node scripts/smoke.mjs --isolated  -> copies the built app + data-bundle to a temp dir OUTSIDE the repo
//                                         (no parent files, no DATA_SOURCE hint) so auto-detect must serve the
//                                         bundle. This simulates a Vercel-style deployment without the repo.
//   node scripts/smoke.mjs --e2e       -> repo mode PLUS a combined end-to-end test: starts the backend (python run.py,
//                                         SAMPLE_MODE=true, Zetaris off) on :8000, checks "Backend online" + alerts from
//                                         backend /triage, runs an analysis through POST /api/run, checks the new pack in
//                                         /api/detail, stops the backend and checks graceful offline mode. Files the test
//                                         created in logs/, output/ and output_examples/ are removed again.
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const repo = path.resolve(root, '..');
const ISOLATED = process.argv.includes('--isolated') || process.env.SMOKE_MODE === 'isolated';
const E2E = process.argv.includes('--e2e');
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
let backend = null;
const stopBackend = () => {
  if (!backend) return;
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(backend.pid), '/T', '/F'], { stdio: 'ignore' });
  else backend.kill('SIGTERM');
  backend = null;
};
const stop = () => {
  stopBackend();
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
  check('tier thresholds are shipped by the engine (TRIAGE_RULES), not parsed from source', !!r && r.critical_cover_days > 0 && r.warning_cover_days > r.critical_cover_days && r.supplier_slip_flag_days > 0, JSON.stringify(r));
  check('every alert carries run info', items.every((x) => typeof x.stored_runs === 'number' && typeof x.has_pack === 'boolean'));
  const counts = al.body?.counts || {};
  check('tiers follow the shipped rules', !!r && items.every((x) => { const c = x.trust_cover_days < r.critical_cover_days || x.shortfall_units > r.critical_shortfall_over; const w = x.trust_cover_days < r.warning_cover_days || (x.discrepancies_detected || []).length > r.warning_discrepancies_over; return x.urgency_tier === (c ? 'CRITICAL' : w ? 'WARNING' : 'SECURE'); }));
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

  // Live (real LLM + Zetaris) packs committed in output_examples/live_*.json
  const liveFiles = fs.existsSync(path.join(ISOLATED ? path.join(appDir, 'data-bundle') : repo, 'output_examples'))
    ? fs.readdirSync(path.join(ISOLATED ? path.join(appDir, 'data-bundle') : repo, 'output_examples')).filter((n) => /^live_.+\.json$/.test(n))
    : [];
  const livePairs = items.filter((x) => x.pack_live);
  check('live packs are recognised (one live pair per live_*.json)', livePairs.length === liveFiles.length && liveFiles.length > 0, `${livePairs.length} live pairs, ${liveFiles.length} files`);
  const dflt = items.find((x) => x.facility_id === 'FAC-WH-02' && x.medicine_id === 'MED-007');
  if (dflt) {
    const dd = await getJson('/api/detail?facility=FAC-WH-02&medicine=MED-007');
    check('default pair FAC-WH-02/MED-007 is live: real LLM, no fallback, Zetaris telemetry', dflt.pack_live && dd.body?.run?.live === true && dd.body.run.fallback_steps === 0 && dd.body.run.data_source?.queries_ok > 0, `${dd.body?.run?.file}, ${dd.body?.run?.data_source?.queries_ok}/${dd.body?.run?.data_source?.queries_attempted} queries`);
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
  const abDir = path.join(dataRoot, 'output_examples', 'live_runs', 'memory_ab');
  const hasAb = fs.existsSync(abDir) && fs.readdirSync(abDir).some((n) => /^before_.+\.json$/.test(n));
  check('/api/memory matches presence of trace files', memFiles || hasAb ? mem.status === 200 && !!mem.body?.verdict : mem.status === 404, `kind=${mem.body?.kind} verdict=${mem.body?.verdict}`);
  if (hasAb) {
    check('memory flip: live before/after pair is primary and same-input claim is computed from the data', mem.body?.kind === 'live' && typeof mem.body?.inputs_identical === 'boolean' && (mem.body.verdict !== 'flip' || mem.body.inputs_identical === true), `inputs_identical=${mem.body?.inputs_identical}, secondary=${mem.body?.secondary?.kind || 'none'}`);
  }

  const ev = await getJson('/api/eval');
  const seedFiles = fs.existsSync(path.join(dataRoot, 'output')) ? fs.readdirSync(path.join(dataRoot, 'output')).filter((n) => /^backtest_seed_\d+\.json$/.test(n)) : [];
  check('/api/eval matches output/backtest_seed_*.json', ev.body?.seeds?.length === seedFiles.length && (seedFiles.length === 0 || ev.status === 200), `${ev.body?.seeds?.length} seeds`);

  if (E2E && !ISOLATED) {
    const walk = (d, acc = []) => {
      if (!fs.existsSync(d)) return acc;
      for (const n of fs.readdirSync(d)) {
        const f = path.join(d, n);
        if (fs.statSync(f).isDirectory()) walk(f, acc); else acc.push(path.relative(repo, f));
      }
      return acc;
    };
    const scan = () => ['logs', 'output', 'output_examples'].flatMap((d) => walk(path.join(repo, d)));
    const before = new Set(scan());
    const cacheCreated = [];
    const up8000 = async () => { try { return (await fetch('http://localhost:8000/health')).ok; } catch { return false; } };
    try {
      check('e2e: nothing is listening on :8000 before the test', !(await up8000()));
      const py = process.env.MEDTRACE_PYTHON || 'python';
      backend = spawn(py, ['run.py'], { cwd: repo, stdio: 'ignore', windowsHide: true, env: { ...process.env, SAMPLE_MODE: 'true', USE_ZETARIS: 'false', PYTHONIOENCODING: 'utf-8' } });
      let on = false;
      for (let i = 0; i < 60 && !on; i++) { on = await up8000(); if (!on) await new Promise((r) => setTimeout(r, 1000)); }
      check('e2e: backend (python run.py, sample mode) comes up', on);
      if (!on) throw new Error('backend did not start');
      const be2 = await getJson('/api/backend');
      check('e2e: dashboard reports Backend online (sample mode)', be2.body?.reachable === true && be2.body?.sample_mode === true, JSON.stringify({ reachable: be2.body?.reachable, sample: be2.body?.sample_mode }));
      const al2 = await getJson('/api/alerts?refresh=1');
      const it2 = al2.body?.items || [];
      check('e2e: alerts now come from backend /triage', al2.body?.source === 'backend' && it2.length === items.length && it2.length > 0, `${al2.body?.source}, ${it2.length} items`);
      check('e2e: live chips survive the backend source', it2.filter((x) => x.pack_live).length === livePairs.length);
      const target = it2.find((x) => x.urgency_tier === 'CRITICAL' && !x.has_pack) || it2.find((x) => !x.has_pack && !x.pack_live) || it2.find((x) => !x.pack_live);
      check('e2e: found a pair to analyse', !!target, target ? `${target.facility_id}/${target.medicine_id}` : '');
      const runRes = await fetch(base + '/api/run', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ facility_id: target.facility_id, medicine_id: target.medicine_id, sample_mode: true }) });
      const rb2 = await runRes.json().catch(() => ({}));
      check('e2e: POST /api/run through the dashboard succeeds', runRes.status === 200 && rb2.ok === true && !!rb2.run_id, `run_id=${rb2.run_id}, ${rb2.execution_time_seconds}s`);
      if (rb2.run_id) cacheCreated.push(path.join(root, '.cache', 'runs', `${String(rb2.run_id).replace(/[^A-Za-z0-9_-]/g, '')}.json`));
      const d2 = await getJson(`/api/detail?facility=${target.facility_id}&medicine=${target.medicine_id}`);
      check('e2e: the new pack appears in the detail view', d2.body?.pack?.run_id === rb2.run_id && d2.body?.run?.run_id === rb2.run_id && Array.isArray(d2.body?.pack?.recommendations), `pack ${d2.body?.pack?._source}`);
      const al3 = await getJson('/api/alerts');
      check('e2e: the alert row now shows a stored plan without a manual refresh', !!(al3.body?.items || []).find((x) => x.facility_id === target.facility_id && x.medicine_id === target.medicine_id)?.has_pack);

      stopBackend();
      let down = false;
      for (let i = 0; i < 20 && !down; i++) { down = !(await up8000()); if (!down) await new Promise((r) => setTimeout(r, 500)); }
      check('e2e: backend stopped', down);
      const be3 = await getJson('/api/backend');
      check('e2e: dashboard reports the backend offline', be3.body?.reachable === false, be3.body?.error);
      const al4 = await getJson('/api/alerts?refresh=1');
      check('e2e: offline mode still serves all alerts from the local engine', al4.status === 200 && al4.body?.source !== 'backend' && (al4.body?.items || []).length === items.length, `${al4.body?.source_label}`);
      const d4 = await getJson(`/api/detail?facility=${target.facility_id}&medicine=${target.medicine_id}`);
      check('e2e: offline mode still shows the stored run and pack', d4.status === 200 && !!d4.body?.pack && !!d4.body?.run);
      const run4 = await fetch(base + '/api/run', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ facility_id: target.facility_id, medicine_id: target.medicine_id }) });
      const rb4 = await run4.json().catch(() => ({}));
      check('e2e: Run analysis declines gracefully when offline (503 with a hint)', run4.status === 503 && /python run\.py/i.test(rb4.error || ''), rb4.error);
    } finally {
      stopBackend();
      await new Promise((r) => setTimeout(r, 800));
      let removed = 0;
      for (const rel of scan()) if (!before.has(rel)) { try { fs.rmSync(path.join(repo, rel), { force: true }); removed += 1; } catch { /* ignore */ } }
      for (const f of cacheCreated) { try { fs.rmSync(f, { force: true }); } catch { /* ignore */ } }
      console.log(`e2e cleanup: removed ${removed} file(s) the test created in logs/, output/, output_examples/ and ${cacheCreated.length} dashboard cache pack(s).`);
    }
  }
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
