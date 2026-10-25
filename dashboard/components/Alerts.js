'use client';
import { useMemo, useState } from 'react';
import { ErrorBox, Loading, TierBadge, num, pretty } from './ui.js';

export default function Alerts({ api, selected, onSelect }) {
  const [tier, setTier] = useState('ACTIONABLE');
  const [q, setQ] = useState('');
  const items = api.data?.items || [];

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return items.filter((i) => {
      if (tier === 'ACTIONABLE' && i.urgency_tier === 'SECURE') return false;
      if (['CRITICAL', 'WARNING', 'SECURE'].includes(tier) && i.urgency_tier !== tier) return false;
      if (!needle) return true;
      return `${i.facility_id} ${i.facility_name} ${i.medicine_id} ${i.generic_name} ${(i.discrepancies_detected || []).join(' ')}`.toLowerCase().includes(needle);
    });
  }, [items, tier, q]);

  const counts = api.data?.counts || {};
  return (
    <section className="panel" aria-label="Alerts">
      <header>
        <div>
          <h2>Alerts - all facilities, by severity</h2>
          {api.data?.ok ? (
            <div className="sub">
              Source: {api.data.source_label}. {items.length} facility-medicine pairs evaluated
              {api.data.generated_at ? `, at ${new Date(api.data.generated_at).toLocaleTimeString()}` : ''}. Underlying inventory data is SIMULATED.
            </div>
          ) : null}
        </div>
        <div className="chips">
          {[['ACTIONABLE', 'Critical + Warning'], ['CRITICAL', `Critical (${counts.CRITICAL || 0})`], ['WARNING', `Warning (${counts.WARNING || 0})`], ['SECURE', `Secure (${counts.SECURE || 0})`], ['ALL', 'All']].map(([k, label]) => (
            <button key={k} className={`chip ${tier === k ? 'on' : ''}`} onClick={() => setTier(k)}>{label}</button>
          ))}
          <input type="search" placeholder="Filter facility / medicine" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter alerts" />
          <button onClick={api.reload} title="Re-read data">Refresh</button>
        </div>
      </header>

      {api.status === 'loading' && !api.data ? <Loading what="Scanning facilities (first load runs the triage engine, a few seconds)" /> : null}
      {api.status === 'error' && !items.length ? (
        <ErrorBox title="Could not load alerts" error={api.error}>
          {(api.data?.attempts || []).map((a) => <div key={a} className="small">{a}</div>)}
        </ErrorBox>
      ) : null}
      {api.data?.ok && api.data.source !== 'backend' && api.data.attempts?.length ? (
        <div className="note small">Backend not used: {api.data.attempts.join('; ')}. Showing the project's own triage engine run on the local data files instead.</div>
      ) : null}

      {api.data?.ok ? (
        shown.length ? (
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Status</th><th>Facility</th><th>Medicine</th><th>Alert type</th>
                  <th className="num">Cover (trust / naive d)</th><th className="num">Shortfall (units)</th><th className="num">Drift / quarantine</th><th>Stored runs</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((i) => {
                  const key = `${i.facility_id}/${i.medicine_id}`;
                  return (
                    <tr key={key} className={selected === key ? 'sel' : ''} onClick={() => onSelect(i)} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onSelect(i)}>
                      <td><TierBadge tier={i.urgency_tier} /></td>
                      <td>{i.facility_name}<div className="sub mono">{i.facility_id}</div></td>
                      <td>{i.generic_name}<div className="sub mono">{i.medicine_id}</div></td>
                      <td>{(i.discrepancies_detected || []).length ? i.discrepancies_detected.map((d) => <span key={d} className="badge b-info" style={{ marginRight: 4 }}>{pretty(d)}</span>) : <span className="muted">none flagged</span>}</td>
                      <td className="num">{num(i.trust_cover_days, 2)} / {num(i.naive_cover_days, 2)}</td>
                      <td className="num">{num(i.shortfall_units, 1)}</td>
                      <td className="num">{num(i.audit_drift, 0)} / {num(i.quarantined_stock, 0)}</td>
                      <td>{i.stored_runs ? <span className="badge b-ok">{i.stored_runs}</span> : <span className="badge b-mute">none</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">No alerts match this filter.</div>
        )
      ) : null}
    </section>
  );
}