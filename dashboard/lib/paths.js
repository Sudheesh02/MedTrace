import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// Data source resolution.
//  - "repo":   the dashboard lives in <repo>/dashboard and reads the parent repo's logs/, output/, ...
//  - "bundle": reads dashboard/data-bundle/ (a snapshot of the same files made by `npm run bundle-data`).
// DATA_SOURCE=repo|bundle forces a mode; otherwise the parent repo is auto-detected and the bundle is the fallback.
const PARENT = process.env.MEDTRACE_ROOT ? path.resolve(process.env.MEDTRACE_ROOT) : path.resolve(process.cwd(), '..');

function findBundle() {
  const cands = [process.env.DATA_BUNDLE_DIR, path.join(process.cwd(), 'data-bundle'), path.join(process.cwd(), 'dashboard', 'data-bundle')].filter(Boolean);
  return cands.map((c) => path.resolve(c)).find((c) => fs.existsSync(path.join(c, 'index.json'))) || null;
}

const forced = (process.env.DATA_SOURCE || '').toLowerCase();
const bundleDir = findBundle();
const repoPresent = fs.existsSync(path.join(PARENT, 'app', 'agents', 'triage_planner.py'));

export const DATA_MODE = forced === 'bundle' ? 'bundle' : forced === 'repo' ? 'repo' : repoPresent || !bundleDir ? 'repo' : 'bundle';
export const BUNDLE_DIR = bundleDir;
export const REPO_ROOT = DATA_MODE === 'bundle' ? bundleDir || path.join(process.cwd(), 'data-bundle') : PARENT;

export const API_BASE = (process.env.MEDTRACE_API || 'http://localhost:8000').replace(/\/$/, '');

// Where "Run analysis" responses are stored so the full action pack can be re-opened later.
export const RUN_CACHE_DIR = DATA_MODE === 'bundle' ? path.join(os.tmpdir(), 'medtrace-runs') : path.join(process.cwd(), '.cache', 'runs');

export const dir = (...p) => path.join(REPO_ROOT, ...p);