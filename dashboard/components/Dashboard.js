'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, FlaskConical, GitCompareArrows, LayoutList, OctagonAlert, RefreshCw, ShieldCheck, TriangleAlert, Boxes, History, Clock } from 'lucide-react';
import Alerts, { orderedItems } from './Alerts.js';
import Detail from './Detail.js';
import Why from './Why.js';
import MemoryCard from './MemoryCard.js';
import EvalPanel from './EvalPanel.js';
import HowItWorks from './HowItWorks.js';
import { ago, num, useApi } from './ui.js';

const VIEWS = [
  ['triage', 'Triage', LayoutList],
  ['memory', 'Memory flip', GitCompareArrows],
  ['eval', 'Evaluation', FlaskConical],
];
const SUPPLIER = 'supplier_delay_risk';

function sourcePill(data) {
  if (!data) return null;
  if (data.mode === 'bundle' || data.source === 'bundle') return { text: 'Stored demo runs (snapshot)', cls: 'snap', title: 'A snapshot of real MedTrace outputs shipped with this deployment. Inventory data is simulated. Run analysis is disabled here.' };
  if (data.source === 'backend') return { text: 'Source: live FastAPI backend', cls: 'live', title: data.source_label };
  if (data.source === 'python-snapshot') return { text: 'Source: local triage engine snapshot', cls: '', title: 'The project\'s own TriagePlannerAgent run over the local simulated data files (no backend needed).' };
  return { text: 'Source: stored traces only (partial)', cls: 'warn', title: data.source_label };
}

function Kpis({ api, tier, setTier }) {
  const items = api.data?.items || [];
  const counts = api.data?.counts || {};
  const rules = api.data?.rules;
  const k = useMemo(() => {
    const actionable = items.filter((i) => i.urgency_tier !== 'SECURE');
    const wc = rules?.warning_cover_days ?? 14;
    const warn = items.filter((i) => i.urgency_tier === 'WARNING');
    return {
      total: items.length,
      facilities: new Set(items.map((i) => i.facility_id)).size,
      medicines: new Set(items.map((i) => i.medicine_id)).size,
      shortfall: actionable.reduce((a, i) => a + (Number(i.shortfall_units) || 0), 0),
      withRuns: items.filter((i) => i.stored_runs > 0).length,
      withPack: items.filter((i) => i.has_pack).length,
      live: items.filter((i) => i.pack_live).length,
      warnLow: warn.filter((i) => Number(i.trust_cover_days) < wc).length,
      supplierAll: items.filter((i) => (i.discrepancies_detected || []).includes(SUPPLIER)).length,
    };
  }, [items, rules]);
  const ready = !!api.data?.ok;
  const v = (x) => (ready ? num(x, 0) : <span className="skel inline" aria-label="loading" />);
  const crit = counts.CRITICAL || 0;
  const warn = counts.WARNING || 0;
  const ok = counts.SECURE || 0;
  const pct = (n) => (k.total ? `${(n / k.total) * 100}%` : '0%');
  return (
    <div className="kpis" role="group" aria-label="Alert counts by severity">
      <button className={`kpi crit ${tier === 'CRITICAL' ? 'on' : ''}`} onClick={() => setTier(tier === 'CRITICAL' ? 'ACTIONABLE' : 'CRITICAL')} aria-pressed={tier === 'CRITICAL'}>
        <div className="kpi-l"><OctagonAlert className="ic" />Critical</div>
        <div className="kpi-v">{v(crit)}</div>
        <div className="kpi-s">{rules ? `cover < ${rules.critical_cover_days}d or shortfall > ${rules.critical_shortfall_over}` : 'pairs needing action first'}</div>
      </button>
      <button className={`kpi warn ${tier === 'WARNING' ? 'on' : ''}`} onClick={() => setTier(tier === 'WARNING' ? 'ACTIONABLE' : 'WARNING')} aria-pressed={tier === 'WARNING'}>
        <div className="kpi-l"><TriangleAlert className="ic" />Warning</div>
        <div className="kpi-v">{v(warn)}</div>
        <div className="kpi-s">{ready ? `${k.warnLow} with cover < ${rules?.warning_cover_days ?? 14}d; rest anomaly-flagged` : 'watch / act soon'}</div>
      </button>
      <button className={`kpi ok ${tier === 'SECURE' ? 'on' : ''}`} onClick={() => setTier(tier === 'SECURE' ? 'ACTIONABLE' : 'SECURE')} aria-pressed={tier === 'SECURE'}>
        <div className="kpi-l"><ShieldCheck className="ic" />Secure</div>
        <div className="kpi-v">{v(ok)}</div>
        <div className="kpi-s">{ready && ok === 0 ? `engine flags ${SUPPLIER.replace(/_/g, ' ')} on ${k.supplierAll}/${k.total}` : 'no rule triggered'}</div>
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
        <div className="kpi-s">pairs with a stored run, {ready ? k.withPack : '-'} with a full action plan{ready && k.live ? `, ${k.live} live (real LLM + Zetaris)` : ''}</div>
      </div>
    </div>
  );
}

/** Pick the most useful first selection: a critical pair that has a stored full action pack. */
const PREFERRED_DEFAULT = 'FAC-WH-02/MED-007'; // critical metformin: live real-LLM + Zetaris run with a full pack (a UI preference only)
export function pickDefault(items) {
  const crit = orderedItems(items.filter((i) => i.urgency_tier === 'CRITICAL'));
  const liveCrit = crit.filter((i) => i.pack_live && i.pack_real_llm);
  const pref = liveCrit.find((i) => `${i.facility_id}/${i.medicine_id}` === PREFERRED_DEFAULT);
  if (pref) return pref;
  const rank = (i) => (i.pack_live ? 4 : 0) + (i.has_pack ? 2 : 0) + (i.latest_run?.llm_used ? 1 : 0) + (i.latest_run ? 0.5 : 0);
  const best = [...crit].sort((a, b) => rank(b) - rank(a))[0];
  if (best && rank(best) > 0) return best;
  return crit[0] || orderedItems(items.filter((i) => i.has_pack))[0] || orderedItems(items)[0] || null;
}

export default function Dashboard() {
  const alerts = useApi('/api/alerts');
  const backend = useApi('/api/backend');
  const memory = useApi('/api/memory');
  const evalApi = useApi('/api/eval');
  const [view, setView] = useState('triage');
  const [tier, setTier] = useState('ACTIONABLE');
  const [sel, setSel] = useState(null);
  const [drill, setDrill] = useState(false);
  const detail = useApi(sel ? `/api/detail?facility=${encodeURIComponent(sel.facility_id)}&medicine=${encodeURIComponent(sel.medicine_id)}` : null);
  const be = backend.data;
  const snapshot = alerts.data?.mode === 'bundle';
  const pill = sourcePill(alerts.data);

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
    if (hit) {
      setSel(hit);
      if (window.matchMedia('(max-width: 960px)').matches) setDrill(true);
      return;
    }
    // Never open empty on desktop; on mobile stay on the list until the user drills in.
    if (!window.matchMedia('(max-width: 960px)').matches) setSel(pickDefault(alerts.data.items));
  }, [alerts.data, sel]);

  const go = (k) => {
    setView(k);
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}#${k}`);
  };
  const select = useCallback((item) => {
    setSel(item);
    setDrill(true);
    window.history.replaceState(null, '', `?facility=${encodeURIComponent(item.facility_id)}&medicine=${encodeURIComponent(item.medicine_id)}${window.location.hash}`);
  }, []);
  const onRan = () => {
    detail.reload();
    alerts.reload();
    backend.reload();
  };

  const last = useMemo(() => {
    const withRun = (alerts.data?.items || []).filter((i) => i.latest_run_at);
    if (!withRun.length) return null;
    // Prefer the pairs that have a stored live (real LLM + Zetaris) pack, so the header does not report an incidental sample-mode test run.
    const live = withRun.filter((i) => i.pack_live);
    const pool = live.length ? live : withRun;
    return pool.reduce((a, b) => (new Date(b.latest_run_at) > new Date(a.latest_run_at) ? b : a));
  }, [alerts.data]);
  const lastChip = last
    ? (alerts.data?.mode === 'bundle'
      ? `Stored ${last.pack_live ? 'live' : 'demo'} run \u00b7 ${new Date(last.latest_run_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}`
      : `Latest run ${ago(last.latest_run_at)} \u00b7 ${last.latest_run?.llm_used ? 'LLM pipeline' : 'sample mode'}${last.latest_run?.accepted === true ? ' \u00b7 accepted' : last.latest_run?.accepted === false ? ' \u00b7 rejected' : ''}`)
    : null;

  return (
    <>
      <header className="topbar">
        <div className="topbar-in">
          <div className="brand">
            <div className="logo"><Activity size={17} strokeWidth={2.6} /></div>
            <div>
              <h1>MedTrace</h1>
              <div className="sub">Stock-integrity triage <span className="hide-s">· inventory data is simulated</span></div>
            </div>
          </div>
          <nav className="nav" aria-label="Views">
            {VIEWS.map(([k, label, Icon]) => (
              <button key={k} className={view === k ? 'on' : ''} onClick={() => go(k)} aria-current={view === k ? 'page' : undefined}><Icon className="ic" /><span>{label}</span></button>
            ))}
          </nav>
          <div className="top-right">
            {lastChip ? <span className="badge b-mute hide-s" title={`${last.generic_name} at ${last.facility_name}. Timestamp of the newest stored trace.`}><Clock className="ic" />{lastChip}</span> : null}
            {snapshot ? (
              <span className="badge b-info" title="No backend in this deployment"><span className="dot" style={{ background: 'var(--accent)' }} />Snapshot mode</span>
            ) : (
              <span className={`badge ${be?.reachable ? 'b-ok' : 'b-mute'}`} title={be?.error || ''}>
                <span className={`dot ${be?.reachable ? 'd-ok' : ''}`} style={be?.reachable ? undefined : { background: 'var(--muted)' }} />
                {backend.status === 'loading' && !be ? 'checking backend...' : be?.reachable ? `Backend online${be.sample_mode ? ' (sample mode)' : ''}` : 'Backend offline'}
              </span>
            )}
            <button className="ghost" onClick={() => { backend.reload(); alerts.reload(); }} title="Re-check backend and re-read data" aria-label="Refresh"><RefreshCw className="ic" /><span className="hide-s">Refresh</span></button>
          </div>
        </div>
      </header>

      <main className={`page ${drill ? 'drill' : ''}`}>
        {view === 'triage' ? (
          <>
            <div className="above"><Kpis api={alerts} tier={tier} setTier={setTier} /></div>
            <div className="above"><HowItWorks /></div>
            <div className={`md ${drill ? 'drill' : ''}`}>
              <Alerts api={alerts} tier={tier} setTier={setTier} selected={sel ? `${sel.facility_id}/${sel.medicine_id}` : null} onSelect={select} source={pill} />
              <div className="dgrid">
                <Detail item={sel} api={detail} backend={be} snapshot={snapshot} onRan={onRan} onBack={() => setDrill(false)} />
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