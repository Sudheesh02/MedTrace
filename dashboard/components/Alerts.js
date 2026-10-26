'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, CircleDashed, Database, Info, Radio, Search, Sparkles } from 'lucide-react';
import { ErrorBox, ListSkeleton, TIER_CLASS, TierBadge, ago, num, pretty } from './ui.js';

const SUPPLIER = 'supplier_delay_risk';

/** Warning sub-bands are derived from the engine's own fields (cover and the list of detected anomalies). */
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
    { id: 'CRITICAL', tier: 'CRITICAL', label: 'Critical', hint: 'ranked by urgency score' },
    { id: 'W_COVER', tier: 'WARNING', label: 'Warning: low cover', hint: `cover under ${wc} days` },
    { id: 'W_ANOMALY', tier: 'WARNING', label: 'Warning: other anomaly', hint: `cover ${wc}+ days, anomaly beyond supplier delay` },
    { id: 'W_FLAG', tier: 'WARNING', label: 'Warning: supplier-delay flag only', hint: `cover ${wc}+ days, only the supplier-delay flag` },
    { id: 'SECURE', tier: 'SECURE', label: 'Secure', hint: 'no rule triggered' },
  ];
}

export function runChip(i) {
  if (i.pack_live) return { cls: 'b-live', text: 'Live run', title: `Real LLM${i.pack_model ? ` (${i.pack_model})` : ''} + Zetaris live run. Stored action pack with ${i.pack_actions ?? 'several'} recommendation(s)${i.pack_no_action ? ', all with 0 units (no action needed)' : ''}.` };
  if (i.has_pack) return { cls: 'b-ok', text: 'Full plan', title: `Stored action pack with ${i.pack_actions ?? 'several'} recommendation(s)` };
  if (i.latest_run) {
    const lr = i.latest_run;
    return { cls: 'b-info', text: lr.llm_used ? 'LLM run' : 'Sample run', title: `${i.stored_runs} stored trace(s). Latest ${ago(i.latest_run_at)}${lr.models?.length ? `, models: ${lr.models.join(', ')}` : ''}` };
  }
  if (i.stored_runs) return { cls: 'b-info', text: 'Investigated', title: `${i.stored_runs} stored trace(s). Latest ${ago(i.latest_run_at)}` };
  return null;
}

export function orderedItems(items) {
  return [...items].sort((a, b) => (b.urgency_score ?? 0) - (a.urgency_score ?? 0));
}

export function TierLegend({ rules, counts, supplierAll, total }) {
  if (!rules) return <div className="legend-pop small muted">Thresholds unavailable (this data source did not provide the engine rules).</div>;
  return (
    <div className="legend-pop small" role="note">
      <div className="lp-t">How tiers are assigned <span className="muted">(from {rules.source})</span></div>
      <div className="lp-r"><span className="dot d-crit" /><span><b>Critical</b> if trust-adjusted cover &lt; {rules.critical_cover_days} days <i>or</i> shortfall &gt; {rules.critical_shortfall_over} units.</span></div>
      <div className="lp-r"><span className="dot d-warn" /><span><b>Warning</b> if cover &lt; {rules.warning_cover_days} days <i>or</i> any anomaly is detected.</span></div>
      <div className="lp-r"><span className="dot d-ok" /><span><b>Secure</b> otherwise.</span></div>
      <p className="muted">
        Supplier delay counts as an anomaly only when the supplier on the latest purchase order has a p90 delivery slip of {rules.supplier_slip_flag_days ?? 7} days or more ({num(supplierAll, 0)} of {num(total, 0)} pairs). Shorter slips only widen the delivery window used for shortfall. Result: {num(counts.CRITICAL || 0, 0)} Critical, {num(counts.WARNING || 0, 0)} Warning, {num(counts.SECURE || 0, 0)} Secure. We show the engine's tiers unchanged and split Warning into sub-bands only for readability.
      </p>
    </div>
  );
}

export default function Alerts({ api, tier, setTier, selected, onSelect, source }) {
  const [q, setQ] = useState('');
  const [closed, setClosed] = useState({ W_COVER: true, W_ANOMALY: true, W_FLAG: true });
  const [legend, setLegend] = useState(false);
  const scroller = useRef(null);
  const items = api.data?.items || [];
  const counts = api.data?.counts || {};
  const rules = api.data?.rules || null;
  const bands = useMemo(() => makeBands(rules), [rules]);
  const searching = q.trim().length > 0;

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return orderedItems(items).filter((i) => {
      if (tier === 'ACTIONABLE' && i.urgency_tier === 'SECURE') return false;
      if (['CRITICAL', 'WARNING', 'SECURE'].includes(tier) && i.urgency_tier !== tier) return false;
      if (!needle) return true;
      return `${i.facility_id} ${i.facility_name} ${i.medicine_id} ${i.generic_name} ${(i.discrepancies_detected || []).join(' ')}`.toLowerCase().includes(needle);
    });
  }, [items, tier, q]);

  const supplierAll = useMemo(() => items.filter((i) => (i.discrepancies_detected || []).includes(SUPPLIER)).length, [items]);
  const grouped = useMemo(() => bands.map((b) => ({ ...b, rows: shown.filter((i) => bandOf(i, rules) === b.id) })).filter((b) => b.rows.length), [bands, shown, rules]);
  const isClosed = (id) => (searching || tier === 'WARNING' ? false : !!closed[id]);
  const visible = useMemo(() => grouped.flatMap((b) => (isClosed(b.id) ? [] : b.rows)), [grouped, closed, searching, tier]); // eslint-disable-line react-hooks/exhaustive-deps
  const keyOf = (i) => `${i.facility_id}/${i.medicine_id}`;

  // Opening the Warning band on first selection of a warning pair keeps the selection visible.
  useEffect(() => {
    if (!selected) return;
    const it = items.find((i) => keyOf(i) === selected);
    if (it && it.urgency_tier === 'WARNING') {
      const b = bandOf(it, rules);
      setClosed((c) => (c[b] ? { ...c, [b]: false } : c));
    }
  }, [selected, items, rules]);

  useEffect(() => {
    if (!selected || !scroller.current) return;
    const el = scroller.current.querySelector(`[data-key="${CSS.escape(selected)}"]`);
    el?.scrollIntoView?.({ block: 'nearest' });
  }, [selected]);

  function onKeyDown(e) {
    if (!['ArrowDown', 'ArrowUp', 'j', 'k', 'Home', 'End'].includes(e.key)) return;
    if (e.target?.tagName === 'INPUT') {
      if (e.key !== 'ArrowDown') return;
    }
    if (!visible.length) return;
    e.preventDefault();
    const cur = visible.findIndex((i) => keyOf(i) === selected);
    let next = cur;
    if (e.key === 'ArrowDown' || e.key === 'j') next = Math.min(visible.length - 1, cur + 1);
    else if (e.key === 'ArrowUp' || e.key === 'k') next = Math.max(0, cur === -1 ? 0 : cur - 1);
    else if (e.key === 'Home') next = 0;
    else next = visible.length - 1;
    const it = visible[next];
    onSelect(it);
    requestAnimationFrame(() => scroller.current?.querySelector(`[data-key="${CSS.escape(keyOf(it))}"]`)?.focus({ preventScroll: true }));
  }

  const pill = source || {};
  return (
    <section className="panel listcol" aria-label="Alerts" onKeyDown={onKeyDown}>
      <div className="list-tools">
        <div className="row spread">
          <h2>Alerts</h2>
          <div className="row" style={{ gap: 6 }}>
            <span className={`pill ${pill.cls || ''}`} title={pill.title || ''}><Database className="ic" />{pill.text || 'Reading data...'}</span>
            <button className={`ghost icon ${legend ? 'on' : ''}`} onClick={() => setLegend((v) => !v)} aria-expanded={legend} aria-label="How tiers are assigned" title="How tiers are assigned"><Info className="ic" /></button>
          </div>
        </div>
        {legend ? <TierLegend rules={rules} counts={counts} supplierAll={supplierAll} total={items.length} /> : null}
        <div className="search"><Search className="ic" /><input type="search" placeholder="Filter facility, medicine, anomaly" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter alerts" /></div>
        <div className="seg" role="group" aria-label="Severity filter">
          {[['ACTIONABLE', 'Needs action'], ['CRITICAL', `Critical ${counts.CRITICAL ?? ''}`], ['WARNING', `Warning ${counts.WARNING ?? ''}`], ['SECURE', `Secure ${counts.SECURE ?? ''}`], ['ALL', 'All']].map(([k, label]) => (
            <button key={k} className={tier === k ? 'on' : ''} onClick={() => setTier(k)} aria-pressed={tier === k}>{label.trim()}</button>
          ))}
        </div>
      </div>

      <div className="list-scroll" ref={scroller}>
        {api.status === 'loading' && !api.data ? <ListSkeleton /> : null}
        {api.status === 'error' && !items.length ? (
          <div style={{ padding: 12 }}>
            <ErrorBox title="Could not load alerts" error={api.error}>
              {(api.data?.attempts || []).map((a) => <div key={a} className="small">{a}</div>)}
            </ErrorBox>
          </div>
        ) : null}

        {api.data?.ok && !shown.length ? <div className="empty"><CircleDashed className="ic" />No alerts match this filter.</div> : null}

        {api.data?.ok ? grouped.map((b) => {
          const closedNow = isClosed(b.id);
          const sub = b.tier === 'WARNING';
          return (
            <div key={b.id} className={sub ? 'subband' : ''}>
              <button className={`band ${closedNow ? 'closed' : ''}`} onClick={() => setClosed((c) => ({ ...c, [b.id]: !c[b.id] }))} aria-expanded={!closedNow}>
                <span className={`dot d-${TIER_CLASS[b.tier]}`} />{b.label}<span className="ct">{b.rows.length}</span>
                <span className="bhint">{b.hint}</span>
                <ChevronDown className="ic chev" />
              </button>
              {closedNow ? null : b.rows.map((i, n) => {
                const key = keyOf(i);
                const flagged = i.discrepancies_detected || [];
                const chip = runChip(i);
                return (
                  <button type="button" key={key} data-key={key} className={`arow ${TIER_CLASS[i.urgency_tier] || ''} ${selected === key ? 'sel' : ''}`} onClick={() => onSelect(i)} tabIndex={selected === key || (!selected && n === 0 && b === grouped[0]) ? 0 : -1} aria-pressed={selected === key}>
                    <div className="strip" />
                    <div style={{ minWidth: 0 }}>
                      <div className="t1">{b.id === 'CRITICAL' ? <span className="rank">#{n + 1}</span> : null}{i.generic_name} <span className="mono muted" style={{ fontWeight: 400 }}>{i.medicine_id}</span></div>
                      <div className="t2">{i.facility_name} <span className="mono">{i.facility_id}</span></div>
                      <div className="chips">
                        {chip ? <span className={`badge ${chip.cls}`} title={chip.title}>{chip.text === 'Full plan' ? <Sparkles className="ic" /> : chip.text === 'Live run' ? <Radio className="ic" /> : null}{chip.text}</span> : null}
                        {flagged.length ? flagged.slice(0, 2).map((d) => <span key={d} className={`tag ${d === SUPPLIER ? 'dim' : ''}`} title={d === SUPPLIER ? 'Supplier p90 delivery slip is chronic (see the tier legend for the threshold)' : undefined}>{pretty(d)}</span>) : <span className="tag" style={{ opacity: .6 }}>none flagged</span>}
                        {flagged.length > 2 ? <span className="tag">+{flagged.length - 2}</span> : null}
                      </div>
                    </div>
                    <div className="metric">
                      <TierBadge tier={i.urgency_tier} />
                      <span className="small muted">cover {num(i.trust_cover_days, 1)}d <span title="naive LMIS cover">(naive {num(i.naive_cover_days, 1)}d)</span></span>
                      <span className="small"><b>{num(i.shortfall_units, 0)}</b> <span className="muted">u short</span></span>
                    </div>
                  </button>
                );
              })}
            </div>
          );
        }) : null}
      </div>
      <div className="list-foot">
        {api.data?.ok ? <>{shown.length} of {items.length} pairs. Simulated data. <span className="kbd">↑</span><span className="kbd">↓</span> to move.</> : 'Reading data...'}
      </div>
    </section>
  );
}