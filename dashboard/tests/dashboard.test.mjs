// Dashboard unit tests (no server): node --test tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkRunToken } from '../lib/runauth.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

test('run route is open when MEDTRACE_RUN_TOKEN is not set', () => {
  assert.equal(checkRunToken({}, {}), null);
  assert.equal(checkRunToken(new Headers(), { MEDTRACE_RUN_TOKEN: '   ' }), null);
});

test('run route requires the token when it is set', () => {
  const env = { MEDTRACE_RUN_TOKEN: 's3cret-token' };
  assert.equal(checkRunToken(new Headers(), env).status, 401);
  assert.equal(checkRunToken(new Headers({ authorization: 'Bearer wrong' }), env).status, 401);
  assert.equal(checkRunToken(new Headers({ 'x-medtrace-token': 'nope' }), env).status, 401);
  assert.equal(checkRunToken(new Headers({ authorization: 'Bearer s3cret-token' }), env), null);
  assert.equal(checkRunToken(new Headers({ 'x-medtrace-token': 's3cret-token' }), env), null);
  assert.equal(checkRunToken({ authorization: 'bearer s3cret-token' }, env), null);
});

test('the rejection message never echoes the token', () => {
  const r = checkRunToken(new Headers(), { MEDTRACE_RUN_TOKEN: 'abc123xyz' });
  assert.ok(!JSON.stringify(r).includes('abc123xyz'));
});

test('lib/triage.js no longer regex-parses the Python source', () => {
  const src = fs.readFileSync(path.join(root, 'lib', 'triage.js'), 'utf8');
  assert.ok(!/readRules/.test(src));
  assert.ok(!/triage_planner\.py/.test(src));
});

test('bundled triage.json ships the engine rules', { skip: !fs.existsSync(path.join(root, 'data-bundle', 'triage.json')) }, () => {
  const snap = JSON.parse(fs.readFileSync(path.join(root, 'data-bundle', 'triage.json'), 'utf8'));
  const r = snap.rules;
  assert.ok(r, 'rules missing in bundle');
  for (const k of ['critical_cover_days', 'critical_shortfall_over', 'warning_cover_days', 'warning_discrepancies_over', 'supplier_slip_flag_days']) {
    assert.equal(typeof r[k], 'number', k);
  }
  assert.ok(r.warning_cover_days > r.critical_cover_days);
  // every tier in the bundle must follow the shipped rules
  for (const it of snap.items) {
    const crit = it.trust_cover_days < r.critical_cover_days || it.shortfall_units > r.critical_shortfall_over;
    const warn = it.trust_cover_days < r.warning_cover_days || it.discrepancies_detected.length > r.warning_discrepancies_over;
    assert.equal(it.urgency_tier, crit ? 'CRITICAL' : warn ? 'WARNING' : 'SECURE', `${it.facility_id}/${it.medicine_id}`);
  }
});
