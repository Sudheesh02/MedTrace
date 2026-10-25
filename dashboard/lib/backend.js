import { API_BASE, DATA_MODE } from './paths.js';

async function timedFetch(url, opts = {}, ms = 1500) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  try {
    return await fetch(url, { ...opts, signal: ctl.signal, cache: 'no-store' });
  } finally {
    clearTimeout(t);
  }
}

/** Is the FastAPI backend (python run.py) reachable? Returns its /health payload or {reachable:false}. */
export async function backendHealth() {
  if (DATA_MODE === 'bundle') return { reachable: false, url: null, mode: 'bundle', error: 'snapshot mode (no backend)' };
  try {
    const res = await timedFetch(`${API_BASE}/health`, {}, 1500);
    if (!res.ok) return { reachable: false, url: API_BASE, error: `HTTP ${res.status}` };
    const body = await res.json();
    return { reachable: true, url: API_BASE, ...body };
  } catch (e) {
    return { reachable: false, url: API_BASE, error: e?.name === 'AbortError' ? 'timeout' : 'connection refused / unreachable' };
  }
}

export async function backendJson(pathname, opts = {}, ms = 20000) {
  const res = await timedFetch(`${API_BASE}${pathname}`, opts, ms);
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text.slice(0, 500) };
  }
  if (!res.ok) throw new Error(body?.detail ? String(body.detail) : `backend HTTP ${res.status}`);
  return body;
}