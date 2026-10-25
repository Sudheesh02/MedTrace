import { execFile } from 'node:child_process';
import path from 'node:path';
import { REPO_ROOT } from './paths.js';
import { backendHealth, backendJson } from './backend.js';
import { indexTraces, loadRun } from './traces.js';

let cache = { at: 0, value: null };

function viaPython() {
  const script = path.join(process.cwd(), 'scripts', 'triage_snapshot.py');
  const candidates = process.env.MEDTRACE_PYTHON ? [process.env.MEDTRACE_PYTHON] : ['python', 'py', 'python3'];
  return new Promise((resolve, reject) => {
    const tryNext = (i, lastErr) => {
      if (i >= candidates.length) return reject(lastErr || new Error('python not found'));
      execFile(candidates[i], [script], { cwd: REPO_ROOT, maxBuffer: 64 * 1024 * 1024, timeout: 90000, windowsHide: true }, (err, stdout, stderr) => {
        if (err) return tryNext(i + 1, new Error((stderr || err.message || '').toString().split('\n').slice(-4).join(' ').trim()));
        try {
          resolve(JSON.parse(stdout));
        } catch (e) {
          tryNext(i + 1, new Error('python helper returned invalid JSON'));
        }
      });
    };
    tryNext(0);
  });
}

/** Last-resort: derive a (partial) alert list from stored traces that carry reconcile details. */
function viaTraces() {
  const idx = indexTraces();
  const items = [];
  for (const e of Object.values(idx.latestByPair)) {
    try {
      const run = loadRun(e.file);
      const r = run.reconcile;
      if (!r || r.days_of_cover_trust === undefined) continue;
      const cover = r.days_of_cover_trust;
      const shortfall = r.shortfall || 0;
      items.push({
        facility_id: e.facility_id,
        facility_name: e.facility_id,
        medicine_id: e.medicine_id,
        generic_name: e.medicine_id,
        ledger_stock: r.ledger_stock,
        usable_stock: r.usable_stock,
        audit_drift: r.audit_drift,
        quarantined_stock: r.quarantined_units,
        daily_rate: r.daily_consumption,
        trust_cover_days: cover,
        naive_cover_days: r.days_of_cover_naive,
        shortfall_units: shortfall,
        gap_days: null,
        p_stockout_risk: null,
        discrepancies_detected: (r.discrepancies || []).map((d) => String(d.anomaly_type || '').toLowerCase()),
        urgency_tier: cover < 7 || shortfall > 0 ? 'CRITICAL' : cover < 14 ? 'WARNING' : 'SECURE',
        urgency_score: 100 - Math.min(90, cover * 5),
      });
    } catch {
      /* skip */
    }
  }
  items.sort((a, b) => b.urgency_score - a.urgency_score);
  return { items };
}

function decorate(items) {
  const idx = indexTraces();
  return items.map((it) => {
    const k = `${it.facility_id}/${it.medicine_id}`;
    const latest = idx.latestByPair[k];
    return { ...it, stored_runs: idx.countByPair[k] || 0, latest_run_at: latest?.ts ?? null };
  });
}

export async function getAlerts({ force = false } = {}) {
  if (!force && cache.value && Date.now() - cache.at < 30000) return cache.value;
  const attempts = [];
  const health = await backendHealth();
  let result = null;

  if (health.reachable) {
    try {
      const body = await backendJson('/triage?top_n=1000', {}, 30000);
      const t = body.triage || {};
      result = {
        source: 'backend',
        source_label: `FastAPI backend ${health.url}/triage`,
        items: t.top_urgent_items || [],
        total_evaluated: t.total_evaluated,
      };
    } catch (e) {
      attempts.push(`backend /triage failed: ${e.message}`);
    }
  } else {
    attempts.push(`backend not reachable (${health.error})`);
  }

  if (!result) {
    try {
      const snap = await viaPython();
      result = {
        source: 'python-snapshot',
        source_label: `TriagePlannerAgent over local ${snap.sim_dir} (${snap.facilities} facilities x ${snap.medicines} medicines)`,
        items: snap.items,
        total_evaluated: snap.items.length,
      };
    } catch (e) {
      attempts.push(`python snapshot failed: ${e.message}`);
    }
  }

  if (!result) {
    const t = viaTraces();
    if (t.items.length) {
      result = {
        source: 'traces',
        source_label: 'Latest stored traces only (partial: backend and python snapshot unavailable)',
        items: t.items,
        total_evaluated: t.items.length,
      };
    }
  }

  if (!result) {
    return { ok: false, error: 'No alert source available.', attempts, items: [], backend: health };
  }
  const items = decorate(result.items);
  const counts = items.reduce((a, i) => ((a[i.urgency_tier] = (a[i.urgency_tier] || 0) + 1), a), {});
  const value = { ok: true, ...result, items, counts, attempts, backend: health, generated_at: new Date().toISOString() };
  cache = { at: Date.now(), value };
  return value;
}