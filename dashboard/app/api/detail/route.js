import fs from 'node:fs';
import { dir } from '../../../lib/paths.js';
import { indexTraces, loadRun, traceFileForRun } from '../../../lib/traces.js';
import { findPack, findMemo } from '../../../lib/packs.js';
import { cleanText } from '../../../lib/text.js';

export const dynamic = 'force-dynamic';

const ID = /^[A-Za-z0-9_-]{1,40}$/;

function deepClean(v) {
  if (typeof v === 'string') return cleanText(v);
  if (Array.isArray(v)) return v.map(deepClean);
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, deepClean(x)]));
  return v;
}

export async function GET(request) {
  const sp = new URL(request.url).searchParams;
  const facility = sp.get('facility') || '';
  const medicine = sp.get('medicine') || '';
  if (!ID.test(facility) || !ID.test(medicine)) {
    return Response.json({ ok: false, error: 'facility and medicine query parameters are required' }, { status: 400 });
  }
  try {
    const found = findPack(facility, medicine);
    const idx = indexTraces();
    let traceFile = null;
    let traceNote = null;
    const packTrace = found?.run_id ? traceFileForRun(found.run_id) : null;
    if (packTrace) {
      traceFile = packTrace;
      traceNote = 'Trace of the same run as the action pack shown.';
    } else {
      const latest = idx.latestByPair[`${facility}/${medicine}`];
      if (latest) {
        traceFile = latest.file;
        traceNote = found
          ? 'The action pack and this trace may come from different runs (the pack run\'s trace file is not on disk); the latest stored trace for this pair is shown.'
          : 'Latest stored trace for this pair.';
      }
    }
    const run = traceFile ? loadRun(traceFile) : null;
    return Response.json({
      ok: true,
      facility_id: facility,
      medicine_id: medicine,
      stored_runs: idx.countByPair[`${facility}/${medicine}`] || 0,
      trace_note: traceNote,
      run,
      pack: found ? { ...deepClean(found.pack), _source: found.source, _execution_time_seconds: found.execution_time_seconds, _live: found.live } : null,
      memo: findMemo(facility, medicine),
    });
  } catch (e) {
    return Response.json({ ok: false, error: String(e?.message || e) }, { status: 500 });
  }
}