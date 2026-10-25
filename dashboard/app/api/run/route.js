import fs from 'node:fs';
import path from 'node:path';
import { backendHealth, backendJson } from '../../../lib/backend.js';
import { DATA_MODE, RUN_CACHE_DIR } from '../../../lib/paths.js';
import { resetAlertsCache } from '../../../lib/triage.js';

export const dynamic = 'force-dynamic';

const ID = /^[A-Za-z0-9_-]{1,40}$/;

export async function POST(request) {
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ ok: false, error: 'invalid JSON body' }, { status: 400 });
  }
  const { facility_id, medicine_id, sample_mode } = body || {};
  if (!ID.test(facility_id || '') || !ID.test(medicine_id || '')) {
    return Response.json({ ok: false, error: 'facility_id and medicine_id required' }, { status: 400 });
  }
  if (DATA_MODE === 'bundle') return Response.json({ ok: false, error: 'Run analysis is not available in snapshot mode (stored demo runs only).' }, { status: 503 });
  const health = await backendHealth();
  if (!health.reachable) {
    return Response.json({ ok: false, error: `Backend not reachable at ${health.url} (${health.error}). Start it with "python run.py".` }, { status: 503 });
  }
  try {
    const options = typeof sample_mode === 'boolean' ? { sample_mode } : undefined;
    const res = await backendJson('/run', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ facility_id, medicine_id, options }),
    }, 180000);
    fs.mkdirSync(RUN_CACHE_DIR, { recursive: true });
    const id = String(res.run_id || Date.now()).replace(/[^A-Za-z0-9_-]/g, '');
    fs.writeFileSync(path.join(RUN_CACHE_DIR, `${id}.json`), JSON.stringify(res, null, 2));
    resetAlertsCache();
    return Response.json({ ok: true, run_id: res.run_id, execution_time_seconds: res.execution_time_seconds, trace_file: res.trace_file });
  } catch (e) {
    return Response.json({ ok: false, error: String(e?.message || e) }, { status: 502 });
  }
}