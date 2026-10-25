'use client';
import { useEffect, useMemo, useState } from 'react';
import { Activity, FlaskConical, GitCompareArrows, LayoutList, OctagonAlert, RefreshCw, ShieldCheck, TriangleAlert, Boxes, History } from 'lucide-react';
import Alerts from './Alerts.js';
import Detail from './Detail.js';
import Why from './Why.js';
import MemoryCard from './MemoryCard.js';
import EvalPanel from './EvalPanel.js';
import { num, useApi } from './ui.js';

const VIEWS = [
  ['triage', 'Triage', LayoutList],
  ['memory', 'Memory flip', GitCompareArrows],
  ['eval', 'Evaluation', FlaskConical],
];

function Kpis({ api, tier, setTier }) {
  const items = api.data?.items || [];
  const counts = api.data?.counts || {};
  const k = useMemo(() => {
    const actionable = items.filter((i) => i.urgency_tier !== 'SECURE');
    return {
      total: items.length,
      facilities: new Set(items.map((i) => i.facility_id)).size,
      medicines: new Set(items.map((i) => i.medicine_id)).size,
      shortfall: actionable.reduce((a, i) => a + (Number(i.shortfall_units) || 0), 0),
      withRuns: items.filter((i) => i.stored_runs > 0).length,
    };
  }, [items]);
  const ready = !!api.data?.ok;
  const v = (x) => (ready ? num(x, 0) : '-');
  const crit = counts.CRITICAL || 0;
  const warn = counts.WARNING || 0;
  const ok = counts.SECURE || 0;
  const pct = (n) => (k.total ? `${(n / k.total) * 100}%` : '0%');
  return (
    <div className="kpis" role="group" aria-label="Alert counts by severity">
      <button className={`kpi crit ${tier === 'CRITICAL' ? 'on' : ''}`} onClick={() => setTier(tier === 'CRITICAL' ? 'ACTIONABLE' : 'CRITICAL')}>
        <div className="kpi-l"><OctagonAlert className="ic" />Critical</div>
        <div className="kpi-v">{v(crit)}</div>
        <div className="kpi-s">facility-medicine pairs, click to filter</div>
      </button>
      <button className={`kpi warn ${tier === 'WARNING' ? 'on' : ''}`} onClick={() => setTier(tier === 'WARNING' ? 'ACTIONABLE' : 'WARNING')}>
        <div className="kpi-l"><TriangleAlert className="ic" />Warning</div>
        <div className="kpi-v">{v(warn)}</div>
        <div className="kpi-s">watch / act soon</div>
      </button>
      <button className={`kpi ok ${tier === 'SECURE' ? 'on' : ''}`} onClick={() => setTier(tier === 'SECURE' ? 'ACTIONABLE' : 'SECURE')}>
        <div className="kpi-l"><ShieldCheck className="ic" />Secure</div>
        <div className="kpi-v">{v(ok)}</div>
        <div className="kpi-s">no action needed</div>
      </button>
      <div className="kpi info">
        <div className="kpi-l"><Boxes className="ic" />Coverage</div>
        <div className="kpi-v">{v(k.total)}</div>
        <div className="kpi-s">{ready ? `${k.facilities} facilities x ${k.medicines} medicines evaluated` : 'loading...'}</div>
        {ready ? (
          <div className="sevbar" title="Critical / Warning / Secure share">
            <i style={{ width: pct(crit), background: 'var(--crit)' }} /><i style={{ width: pct(warn), background: 'var(--warn)' }} /><i style={{ width: pct(ok), background: 'var(--ok)' }} />
          </div>
        ) : null}
      </div>
      <div className="kpi info">
        <div className="kpi-l"><Activity className="ic" />Open shortfall</div>
        <div className="kpi-v">{v(k.shortfall)}</div>
        <div className="kpi-s">units across critical + warning (simulated)</div>
      </div>
      <div className="kpi info">
        <div className="kpi-l"><History className="ic" />Investigated</div>
        <div className="kpi-v">{v(k.withRuns)}</div>
        <div className="kpi-s">pairs with a stored agent run</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const alerts = useApi('/api/alerts');
  const backend = useApi('/api/backend');
  const memory = useApi('/api/memory');
  const evalApi = useApi('/api/eval');
  const [view, setView] = useState('triage');
  const [tier, setTier] = useState('ACTIONABLE');
  const [sel, setSel] = useState(null);
  const detail = useApi(sel ? `/api/detail?facility=${encodeURIComponent(sel.facility_id)}&medicine=${encodeURIComponent(sel.medicine_id)}` : null);
  const be = backend.data;

  // Deep links: /#memory, /#eval and /?facility=FAC-CHC-01&medicine=MED-001
  useEffect(() => {
    const sync = () => {
      const h = window.location.hash.replace('#', '');
      if (VIEWS.some(([k]) => k === h)) setView(h);
    };
    sync();
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, []);
  useEffect(() => {
    if (sel || !alerts.data?.items?.length) return;
    const sp = new URLSearchParams(window.location.search);
    const hit = alerts.data.items.find((i) => i.facility_id === sp.get('facility') && i.medicine_id === sp.get('medicine'));
    if (hit) setSel(hit);
  }, [alerts.data, sel]);

  const go = (k) => {
    setView(k);
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}#${k}`);
  };
  const select = (item) => {
    setSel(item);
    window.history.replaceState(null, '', `?facility=${encodeURIComponent(item.facility_id)}&medicine=${encodeURIComponent(item.medicine_id)}${window.location.hash}`);
  };
  const onRan = () => {
    detail.reload();
    alerts.reload();
    backend.reload();
  };

  return (
    <>
      <header className="topbar">
        <div className="topbar-in">
          <div className="brand">
            <div className="logo"><Activity size={17} strokeWidth={2.6} /></div>
            <div>
              <h1>MedTrace</h1>
              <div className="sub">Stock-integrity triage. Inventory data is simulated.</div>
            </div>
          </div>
          <nav className="nav" aria-label="Views">
            {VIEWS.map(([k, label, Icon]) => (
              <button key={k} className={view === k ? 'on' : ''} onClick={() => go(k)} aria-current={view === k ? 'page' : undefined}><Icon className="ic" />{label}</button>
            ))}
          </nav>
          <div className="top-right">
            <span className={`badge ${be?.reachable ? 'b-ok' : 'b-mute'}`} title={be?.error || ''}>
              <span className={`dot ${be?.reachable ? 'd-ok' : ''}`} style={be?.reachable ? undefined : { background: 'var(--muted)' }} />
              {backend.status === 'loading' && !be ? 'checking backend...' : be?.reachable ? `Backend online${be.sample_mode ? ' (sample mode)' : ''}` : 'Backend offline - stored runs only'}
            </span>
            <button className="ghost" onClick={() => { backend.reload(); alerts.reload(); }} title="Re-check backend and re-read data"><RefreshCw className="ic" />Refresh</button>
          </div>
        </div>
      </header>

      <main className="page">
        {view === 'triage' ? (
          <>
            <Kpis api={alerts} tier={tier} setTier={setTier} />
            <div className="md">
              <Alerts api={alerts} tier={tier} setTier={setTier} selected={sel ? `${sel.facility_id}/${sel.medicine_id}` : null} onSelect={select} />
              <div className="dgrid">
                <Detail item={sel} api={detail} backend={be} onRan={onRan} />
                <Why item={sel} api={detail} backend={be} />
              </div>
            </div>
          </>
        ) : null}
        {view === 'memory' ? <MemoryCard api={memory} /> : null}
        {view === 'eval' ? <EvalPanel api={evalApi} /> : null}
      </main>
    </>
  );
}