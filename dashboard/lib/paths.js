import path from 'node:path';

// The dashboard lives in <repo>/dashboard and reads outputs from the parent repo.
export const REPO_ROOT = process.env.MEDTRACE_ROOT
  ? path.resolve(process.env.MEDTRACE_ROOT)
  : path.resolve(process.cwd(), '..');

export const API_BASE = (process.env.MEDTRACE_API || 'http://localhost:8000').replace(/\/$/, '');

// Where "Run analysis" responses are stored so the full action pack can be re-opened later.
export const RUN_CACHE_DIR = path.join(process.cwd(), '.cache', 'runs');

export const dir = (...p) => path.join(REPO_ROOT, ...p);