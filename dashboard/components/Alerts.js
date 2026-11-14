'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, OctagonAlert, Radio, Search, ShieldCheck, TriangleAlert } from 'lucide-react';
import { ErrorBox, ListSkeleton, TierBadge, num } from './ui.js';

const SUPPLIER = 'supplier_delay_risk';

function bandOf(i, rules) {
  if (i.urgency_tier === 'CRITICAL') return 'CRITICAL';
  if (i.urgency_tier === 'SECURE') return 'SECURE';
  const wc = rules?.warning_cover_days ?? 14;
  if (Number(i.trust_cover_days) < wc) return 'W_COVER';
  if ((i.discrepancies_detected || []).some((d) => d !== SUPPLIER)) return 'W_ANOMALY';
  return 'W_FLAG';
}

export function makeBands(rules) {
  const wc = rules?.warning_cover_days ?? 14;
  return [
    { id: 'CRITICAL', tier: 'CRITICAL', label: 'Critical, most urgent first', hint: 'ranked by urgency score' },
    { id: 'W_COVER', tier: 'WARNING', label: 'Warning: low stock', hint: `cover under ${wc} days` },
    { id: 'W_ANOMALY', tier: 'WARNING', label: 'Warning: other problem', hint: `cover ${wc}+ days, anomaly beyond supplier delay` },
    { id: 'W_FLAG', tier: 'WARNING', label: 'Warning: supplier delay only', hint: `cover ${wc}+ days, only the supplier-delay flag` },
    { id: 'SECURE', tier: 'SECURE', label: 'Secure', hint: 'no rule triggered' },
  ];
}

export function runChip(i) {
  if (i.pack_live) return { cls: 'badge-ok', text: 'Live analysis' };
  if (i.has_pack) return { cls: 'badge-info', text: 'Full plan' };
  if (i.latest_run || i.stored_runs) return { cls: 'badge-mute', text: 'Analysed' };
  return null;
}

export function orderedItems(items) {
  return [...items].sort((a, b) => (b.urgency_score ?? 0) - (a.urgency_score ?? 0));
}

export function TierLegend({ rules, counts, supplierAll, total }) {
  if (!rules) return <div className="legend-pop small muted">Thresholds unavailable.</div>;
  return (
    <div className="legend-pop small" role="note">
      <div className="lp-t">How tiers are assigned</div>
      <div className="lp-r"><span><strong>Critical</strong> if days of stock &lt; {rules.critical_cover_days} days or shortfall &gt; {rules.critical_shortfall_over} units.</span></div>
      <div className="lp-r"><span><strong>Warning</strong> if days of stock &lt; {rules.warning_cover_days} days or any anomaly detected.</span></div>
      <div className="lp-r"><span><strong>Secure</strong> otherwise.</span></div>
    </div>
  );
}

export default function Alerts({ api, tier, setTier, selected, onSelect }) {
  const [q, setQ] = useState('');
  const [filterMode, setFilterMode] = useState('ACTIONABLE'); // 'ACTIONABLE' or 'ALL'
  const [closed, setClosed] = useState({ W_COVER: true, W_ANOMALY: true, W_FLAG: true, SECURE: true });
  const scroller = useRef(null);

  const items = api.data?.items || [];
  const rules = api.data?.rules || null;
  const bands = useMemo(() => makeBands(rules), [rules]);
  const searching = q.trim().length > 0;

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return orderedItems(items).filter((i) => {
      if (filterMode === 'ACTIONABLE' && i.urgency_tier === 'SECURE') return false;
      if (['CRITICAL', 'WARNING', 'SECURE'].includes(tier) && i.urgency_tier !== tier) return false;
      if (!needle) return true;
      return `${i.facility_id} ${i.facility_name} ${i.medicine_id} ${i.generic_name} ${(i.discrepancies_detected || []).join(' ')}`.toLowerCase().includes(needle);
    });
  }, [items, tier, filterMode, q]);

  const grouped = useMemo(() => {
    return bands
      .map((b) => ({ ...b, rows: shown.filter((i) => bandOf(i, rules) === b.id) }))
      .filter((b) => b.rows.length);
  }, [bands, shown, rules]);

  const isClosed = (id) => (searching || tier === 'WARNING' ? false : !!closed[id]);
  const toggleBand = (id) => setClosed((c) => ({ ...c, [id]: !c[id] }));

  const keyOf = (i) => `${i.facility_id}/${i.medicine_id}`;

  // Keep selected item visible if inside a closed band
  useEffect(() => {
    if (!selected) return;
    const it = items.find((i) => keyOf(i) === selected);
    if (it) {
      const b = bandOf(it, rules);
      if (closed[b]) {
        setClosed((c) => ({ ...c, [b]: false }));
      }
    }
  }, [selected, items, rules, closed]);

  // Scroll active item into view
  useEffect(() => {
    if (!selected || !scroller.current) return;
    const el = scroller.current.querySelector(`[data-key="${CSS.escape(selected)}"]`);
    el?.scrollIntoView?.({ block: 'nearest' });
  }, [selected]);

  // Keyboard navigation: j/k and arrow up/down
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['input', 'textarea'].includes(e.target.tagName.toLowerCase())) return;
      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault();
        const allVisible = grouped.flatMap((b) => (isClosed(b.id) ? [] : b.rows));
        if (!allVisible.length) return;
        const currIndex = allVisible.findIndex((i) => keyOf(i) === selected);
        const nextIndex = currIndex < allVisible.length - 1 ? currIndex + 1 : 0;
        onSelect(allVisible[nextIndex]);
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault();
        const allVisible = grouped.flatMap((b) => (isClosed(b.id) ? [] : b.rows));
        if (!allVisible.length) return;
        const currIndex = allVisible.findIndex((i) => keyOf(i) === selected);
        const prevIndex = currIndex > 0 ? currIndex - 1 : allVisible.length - 1;
        onSelect(allVisible[prevIndex]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [grouped, selected, onSelect, closed, searching, tier]);

  return (
    <aside className="queue-pane" aria-label="Action queue">
      <div className="queue-header">
        <input
          type="search"
          className="queue-search-input"
          placeholder="Search medicine, facility..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Filter queue"
        />
        <div className="queue-filter-row">
          <div className="queue-filter-chips">
            <button
              className={`queue-pill-btn ${filterMode === 'ACTIONABLE' ? 'active' : ''}`}
              onClick={() => {
                setFilterMode('ACTIONABLE');
                if (tier === 'SECURE') setTier('ACTIONABLE');
              }}
            >
              Needs action
            </button>
            <button
              className={`queue-pill-btn ${filterMode === 'ALL' ? 'active' : ''}`}
              onClick={() => setFilterMode('ALL')}
            >
              All items
            </button>
          </div>
          <span className="mono muted text-xs">
            {shown.length} items
          </span>
        </div>
      </div>

      <div className="queue-list-scroll" ref={scroller}>
        {api.status === 'loading' && !api.data ? <ListSkeleton /> : null}
        {api.status === 'error' ? <ErrorBox title="Queue unavailable" error={api.error} /> : null}
        {api.data?.ok && !shown.length ? (
          <div className="empty-state">
            <p>No medicines match your filter.</p>
          </div>
        ) : null}

        {grouped.map((band) => {
          const shut = isClosed(band.id);
          const isCritical = band.tier === 'CRITICAL';
          return (
            <div key={band.id} className="band-section">
              <button
                className="band-toggle"
                onClick={() => toggleBand(band.id)}
                aria-expanded={!shut}
              >
                <span>
                  <strong>{band.label}</strong> ({band.rows.length})
                </span>
                {shut ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
              </button>

              {!shut ? (
                <ul className="queue-list">
                  {band.rows.map((item) => {
                    const key = keyOf(item);
                    const isSel = key === selected;
                    const chip = runChip(item);
                    const tierCls = item.urgency_tier === 'CRITICAL' ? 'crit' : item.urgency_tier === 'WARNING' ? 'warn' : 'ok';
                    const cover = item.trust_cover_days !== null && item.trust_cover_days !== undefined ? `${num(item.trust_cover_days, 1)}d left` : '-';
                    const shortfall = Number(item.shortfall_units) > 0 ? `${num(item.shortfall_units, 0)} units short` : 'No shortfall';

                    return (
                      <li key={key} className="queue-item-wrap">
                        <button
                          type="button"
                          className={`queue-item ${tierCls} ${isSel ? 'active' : ''}`}
                          onClick={() => onSelect(item)}
                          aria-current={isSel ? 'true' : undefined}
                          data-key={key}
                        >
                          <span className="queue-item-line-1">
                            <span className="queue-item-name">{item.generic_name}</span>
                            <span className="queue-item-cover mono">{cover}</span>
                          </span>
                          <span className="queue-item-line-2">
                            <span className="queue-item-facility">{item.facility_name || item.facility_id}</span>
                            <span className="queue-item-shortfall mono">{shortfall}</span>
                          </span>
                          {chip ? (
                            <span className="queue-item-line-3">
                              <span className={`badge ${chip.cls}`}>{chip.text}</span>
                            </span>
                          ) : null}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
