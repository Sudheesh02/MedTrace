'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, FlaskConical, GitCompareArrows, HelpCircle, LayoutList, Moon, OctagonAlert, RefreshCw, ShieldCheck, Sun, TriangleAlert } from 'lucide-react';
import Alerts, { orderedItems } from './Alerts.js';
import Detail from './Detail.js';
import MemoryCard from './MemoryCard.js';
import EvalPanel from './EvalPanel.js';
import HowItWorks from './HowItWorks.js';
import MedTraceLogo from './MedTraceLogo.js';
import { num, useApi } from './ui.js';

const VIEWS = [
  ['triage', 'Triage', LayoutList],
  ['memory', 'Memory flip', GitCompareArrows],
  ['eval', 'Evaluation', FlaskConical],
];

const PREFERRED_DEFAULT = 'FAC-WH-02/MED-007';

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
  const [howOpen, setHowOpen] = useState(false);
  const [theme, setTheme] = useState('dark');

  const detail = useApi(sel ? `/api/detail?facility=${encodeURIComponent(sel.facility_id)}&medicine=${encodeURIComponent(sel.medicine_id)}` : null);
  const be = backend.data;
  const snapshot = alerts.data?.mode === 'bundle' || alerts.data?.source === 'bundle';

  // Ambient Cursor Spotlight tracking
  useEffect(() => {
    const handleMouseMove = (e) => {
      document.documentElement.style.setProperty('--mouse-x', `${e.clientX}px`);
      document.documentElement.style.setProperty('--mouse-y', `${e.clientY}px`);
    };
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Synchronize deep links: /#memory, /#eval and /?facility=...&medicine=...
  useEffect(() => {
    const sync = () => {
      const h = window.location.hash.replace('#', '');
      if (VIEWS.some(([k]) => k === h)) setView(h);
    };
    sync();
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, []);

  // Initialize theme (default to Obsidian Dark)
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem('medtrace-theme');
      if (saved) {
        setTheme(saved);
        document.documentElement.setAttribute('data-theme', saved);
      } else {
        setTheme('dark');
        document.documentElement.setAttribute('data-theme', 'dark');
      }
    } catch {
      /* ignore */
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    try {
      window.localStorage.setItem('medtrace-theme', nextTheme);
      document.documentElement.setAttribute('data-theme', nextTheme);
    } catch {
      /* ignore */
    }
  };

  // Auto-pick selection on load
  useEffect(() => {
    if (sel || !alerts.data?.items?.length) return;
    const sp = new URLSearchParams(window.location.search);
    const hit = alerts.data.items.find((i) => i.facility_id === sp.get('facility') && i.medicine_id === sp.get('medicine'));
    if (hit) {
      setSel(hit);
      if (window.matchMedia('(max-width: 960px)').matches) setDrill(true);
      return;
    }
    if (!window.matchMedia('(max-width: 960px)').matches) {
      setSel(pickDefault(alerts.data.items));
    }
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

  // Metrics for summary strip
  const items = alerts.data?.items || [];
  const counts = alerts.data?.counts || {};
  const totalShortfall = useMemo(() => {
    const actionable = items.filter((i) => i.urgency_tier !== 'SECURE');
    return actionable.reduce((a, i) => a + (Number(i.shortfall_units) || 0), 0);
  }, [items]);

  return (
    <>
      {/* Edge-to-Edge Sticky Header */}
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-section">
            <MedTraceLogo />
          </div>

          <nav className="view-nav" aria-label="Views">
            {VIEWS.map(([k, label, Icon]) => (
              <button
                key={k}
                className={`nav-item ${view === k ? 'active' : ''}`}
                onClick={() => go(k)}
                aria-current={view === k ? 'page' : undefined}
              >
                <Icon size={15} aria-hidden="true" />
                <span>{label}</span>
              </button>
            ))}
          </nav>

          <div className="header-actions">
            <button className="btn btn-ghost" onClick={() => setHowOpen(true)}>
              <HelpCircle size={15} aria-hidden="true" />
              <span>How it works</span>
            </button>

            <button className="btn btn-ghost" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
              {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
            </button>

            {/* Single Officer-Focused Status Chip */}
            <div className="badge badge-mute" title="Inventory dataset is simulated for triage demonstration">
              <span className="status-dot ok" />
              <span>Simulated data</span>
            </div>

            <button
              className="btn btn-ghost"
              onClick={() => {
                backend.reload();
                alerts.reload();
                detail.reload();
              }}
              title="Refresh data"
              aria-label="Refresh data"
            >
              <RefreshCw size={15} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="app-container">
        {view === 'triage' ? (
          <>
            {/* One-Row Summary Strip */}
            <div className="summary-strip" role="group" aria-label="District triage metrics">
              <div className="summary-filters">
                <button
                  className={`summary-filter-btn crit ${tier === 'CRITICAL' ? 'active' : ''}`}
                  onClick={() => setTier(tier === 'CRITICAL' ? 'ACTIONABLE' : 'CRITICAL')}
                  aria-pressed={tier === 'CRITICAL'}
                >
                  <OctagonAlert size={15} color="var(--crit)" aria-hidden="true" />
                  <span><strong>{num(counts.CRITICAL || 0, 0)}</strong> Critical</span>
                </button>

                <button
                  className={`summary-filter-btn warn ${tier === 'WARNING' ? 'active' : ''}`}
                  onClick={() => setTier(tier === 'WARNING' ? 'ACTIONABLE' : 'WARNING')}
                  aria-pressed={tier === 'WARNING'}
                >
                  <TriangleAlert size={15} color="var(--warn)" aria-hidden="true" />
                  <span><strong>{num(counts.WARNING || 0, 0)}</strong> Warning</span>
                </button>

                <button
                  className={`summary-filter-btn ok ${tier === 'SECURE' ? 'active' : ''}`}
                  onClick={() => setTier(tier === 'SECURE' ? 'ACTIONABLE' : 'SECURE')}
                  aria-pressed={tier === 'SECURE'}
                >
                  <ShieldCheck size={15} color="var(--ok)" aria-hidden="true" />
                  <span><strong>{num(counts.SECURE || 0, 0)}</strong> Secure</span>
                </button>
              </div>

              <div className="summary-stat-box">
                <Activity size={15} aria-hidden="true" />
                <span>
                  <strong>{num(totalShortfall, 0)}</strong> units short in total (simulated)
                </span>
              </div>
            </div>

            {/* Two-Pane Triage Layout */}
            <div className={`triage-layout ${drill ? 'drilled' : ''}`}>
              <Alerts
                api={alerts}
                tier={tier}
                setTier={setTier}
                selected={sel ? `${sel.facility_id}/${sel.medicine_id}` : null}
                onSelect={select}
              />

              <Detail
                item={sel}
                api={detail}
                backend={be}
                snapshot={snapshot}
                onRan={onRan}
                onBack={() => setDrill(false)}
              />
            </div>
          </>
        ) : null}

        {view === 'memory' ? <MemoryCard api={memory} /> : null}
        {view === 'eval' ? <EvalPanel api={evalApi} /> : null}
      </main>

      {/* How It Works Native Dialog */}
      <HowItWorks isOpen={howOpen} onClose={() => setHowOpen(false)} />
    </>
  );
}
