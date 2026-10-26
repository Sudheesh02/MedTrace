import crypto from 'node:crypto';

/**
 * Optional guard for POST /api/run. When MEDTRACE_RUN_TOKEN is set, the request must carry the same value as
 * "Authorization: Bearer <token>" or "x-medtrace-token: <token>". When it is not set the route stays open (local use).
 * Returns null when allowed, or { status, error } when the request must be rejected.
 */
export function checkRunToken(headers, env = process.env) {
  const expected = (env.MEDTRACE_RUN_TOKEN || '').trim();
  if (!expected) return null;
  const get = (n) => (typeof headers?.get === 'function' ? headers.get(n) : headers?.[n]) || '';
  const auth = String(get('authorization'));
  const bearer = /^Bearer\s+(.+)$/i.exec(auth);
  const given = (bearer ? bearer[1] : String(get('x-medtrace-token'))).trim();
  const a = crypto.createHash('sha256').update(given).digest();
  const b = crypto.createHash('sha256').update(expected).digest();
  if (given && crypto.timingSafeEqual(a, b)) return null;
  return { status: 401, error: 'Run token required or invalid (this server sets MEDTRACE_RUN_TOKEN).' };
}
