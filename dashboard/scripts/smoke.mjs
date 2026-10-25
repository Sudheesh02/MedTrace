// Smoke test: boots the production server (building first if needed) and checks that every
// API route returns non-empty data that matches the real files in the parent repo.
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const repo = path.resolve(root, '..');
const PORT = Number(process.env.SMOKE_PORT || 3199);
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

const server = spawn(process.execPath, [nextBin, 'start', '-p', String(PORT)], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
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

  const be = await getJson('/api/backend');
  check('/api/backend returns a reachability flag', typeof be.body?.reachable === 'boolean', `reachable=${be.body?.reachable}`);

  const al = await getJson('/api/alerts');
  const items = al.body?.items || [];
  check('/api/alerts non-empty', al.status === 200 && items.length > 0, `${items.length} items via ${al.body?.source}`);
  check('alerts sorted by severity score', items.every((x, i) => i === 0 || items[i - 1].urgency_score >= x.urgency_score));
  const facCsv = path.join(repo, 'data', 'simulated', 'facilities.csv');
  if (fs.existsSync(facCsv) && al.body?.source !== 'traces') {
    const rows = fs.readFileSync(facCsv, 'utf8').trim().split(/\r?\n/).length - 1;
    const facs = new Set(items.map((x) => x.facility_id));
    check('alerts cover every facility in data/simulated/facilities.csv', facs.size === rows, `${facs.size} vs ${rows}`);
  }

  const withRun = items.find((x) => x.stored_runs > 0);
  if (withRun) {
    const d = await getJson(`/api/detail?facility=${withRun.facility_id}&medicine=${withRun.medicine_id}`);
    check('/api/detail returns trace steps', d.status === 200 && d.body?.run?.steps?.length > 0, `${withRun.facility_id}/${withRun.medicine_id}, ${d.body?.run?.steps?.length} steps`);
    check('detail has Skeptic verdict', !!d.body?.run?.final_skeptic);
    check('no <think> tags in detail output', !/<\/?think>/i.test(JSON.stringify(d.body)));
  } else {
    check('at least one alert has a stored run', false, 'no trace matched any alert pair');
  }
  const bad = await getJson('/api/detail?facility=..%2F..&medicine=x');
  check('detail rejects bad ids', bad.status === 400);

  const mem = await getJson('/api/memory');
  const memFiles = ['trace_without_memory.jsonl', 'trace_with_memory.jsonl'].every((f) => fs.existsSync(path.join(repo, 'logs', f)));
  check('/api/memory matches presence of trace files', memFiles ? mem.status === 200 && !!mem.body?.verdict : mem.status === 404, `verdict=${mem.body?.verdict}`);

  const ev = await getJson('/api/eval');
  const seedFiles = fs.existsSync(path.join(repo, 'output')) ? fs.readdirSync(path.join(repo, 'output')).filter((n) => /^backtest_seed_\d+\.json$/.test(n)) : [];
  check('/api/eval matches output/backtest_seed_*.json', ev.body?.seeds?.length === seedFiles.length && (seedFiles.length === 0 || ev.status === 200), `${ev.body?.seeds?.length} seeds`);
} catch (e) {
  failures += 1;
  console.error(String(e?.message || e));
} finally {
  stop();
}

console.log(failures ? `\nSMOKE FAILED (${failures})` : '\nSMOKE OK');
process.exit(failures ? 1 : 0);