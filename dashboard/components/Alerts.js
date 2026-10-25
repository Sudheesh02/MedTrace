'use client';
import { useMemo, useState } from 'react';
import { ChevronDown, Search, CircleDashed } from 'lucide-react';
import { ErrorBox, ListSkeleton, TIER_CLASS, TierBadge, num, pretty } from './ui.js';

const BANDS = [['CRITICAL', 'Critical'], ['WARNING', 'Warning'], ['SECURE', 'Secure']];

export default function Alerts({ api, tier, setTier, selected, onSelect }) {
  const [q, setQ] = useState('');
  const [closed, setClosed] = useState({ SECURE: false });
  const items = api.data?.items || [];
  const counts = api.data?.counts || {};

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return items.filter((i) => {
      if (tier === 'ACTIONABLE' && i.urgency_tier === 'SECURE') return false;
      if (['CRITICAL', 'WARNING', 'SECURE'].includes(tier) && i.urgency_tier !== tier) return false;
      if (!needle) return true;
      return `${i.facility_id} ${i.facility_name} ${i.medicine_id} ${i.generic_name} ${(i.discrepancies_detected || []).join(' ')}`.toLowerCase().includes(needle);
    });
  }, [items, tier, q]);

  return (
    <section className="panel listcol" aria-label="Alerts">
      <div className="list-tools">
        <div className="row spread">
          <h2>Alerts</h2>
          <span className="sub">sorted by severity score</span>
        </div>
        <div className="search"><Search className="ic" /><input type="search" placeholder="Filter facility, medicine, anomaly" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter alerts" /></div>
        <div className="seg">
          {[['ACTIONABLE', 'Needs action'], ['CRITICAL', `Critical ${counts.CRITICAL ?? ''}`], ['WARNING', `Warning ${counts.WARNING ?? ''}`], ['SECURE', `Secure ${counts.SECURE ?? ''}`], ['ALL', 'All']].map(([k, label]) => (
            <button key={k} className={tier === k ? 'on' : ''} onClick={() => setTier(k)}>{label.trim()}</button>
          ))}
        </div>
      </div>

      <div className="list-scroll">
        {api.status === 'loading' && !api.data ? <ListSkeleton /> : null}
        {api.status === 'error' && !items.length ? (
          <div style={{ padding: 12 }}>
            <ErrorBox title="Could not load alerts" error={api.error}>
              {(api.data?.attempts || []).map((a) => <div key={a} className="small">{a}</div>)}
            </ErrorBox>
          </div>
        ) : null}
        {api.data?.ok && api.data.source !== 'backend' && api.data.attempts?.length ? (
          <div style={{ padding: '0 12px' }}><div className="note warn small">Backend not used: {api.data.attempts.join('; ')}. Showing the project's own triage engine run on the local data files.</div></div>
        ) : null}

        {api.data?.ok && !shown.length ? <div className="empty"><CircleDashed className="ic" />No alerts match this filter.</div> : null}

        {api.data?.ok ? BANDS.map(([t, label]) => {
          const rows = shown.filter((i) => i.urgency_tier === t);
          if (!rows.length) return null;
          const isClosed = !!closed[t];
          return (
            <div key={t}>
              <button className={`band ${isClosed ? 'closed' : ''}`} onClick={() => setClosed((c) => ({ ...c, [t]: !c[t] }))} aria-expanded={!isClosed}>
                <span className={`dot d-${TIER_CLASS[t]}`} />{label}<span className="ct">{rows.length}</span><ChevronDown className="ic chev" />
              </button>
              {isClosed ? null : rows.map((i) => {
                const key = `${i.facility_id}/${i.medicine_id}`;
                const flagged = i.discrepancies_detected || [];
                return (
                  <div key={key} className={`arow ${TIER_CLASS[i.urgency_tier] || ''} ${selected === key ? 'sel' : ''}`} onClick={() => onSelect(i)} role="button" tabIndex={0} aria-pressed={selected === key} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(i)}>
                    <div className="strip" />
                    <div style={{ minWidth: 0 }}>
                      <div className="t1">{i.generic_name} <span className="mono muted" style={{ fontWeight: 400 }}>{i.medicine_id}</span></div>
                      <div className="t2">{i.facility_name} <span className="mono">{i.facility_id}</span></div>
                      <div className="chips">
                        {flagged.length ? flagged.slice(0, 3).map((d) => <span key={d} className="tag">{pretty(d)}</span>) : <span className="tag" style={{ opacity: .6 }}>none flagged</span>}
                        {flagged.length > 3 ? <span className="tag">+{flagged.length - 3}</span> : null}
                        {i.stored_runs ? <span className="badge b-ok" style={{ lineHeight: '15px' }}>{i.stored_runs} run{i.stored_runs === 1 ? '' : 's'}</span> : null}
                      </div>
                    </div>
                    <div className="metric">
                      <TierBadge tier={i.urgency_tier} />
                      <span className="small muted">cover {num(i.trust_cover_days, 1)}d <span title="naive LMIS cover">(naive {num(i.naive_cover_days, 1)}d)</span></span>
                      <span className="small"><b>{num(i.shortfall_units, 0)}</b> <span className="muted">u short</span></span>
                    </div>
                  </div>
                );
              })}
            </div>
          );
        }) : null}
      </div>
      <div className="list-foot">
        {api.data?.ok ? `${shown.length} of ${items.length} pairs. Source: ${api.data.source_label}${api.data.generated_at ? `, ${new Date(api.data.generated_at).toLocaleTimeString()}` : ''}. Simulated data.` : 'Reading data...'}
      </div>
    </section>
  );
}