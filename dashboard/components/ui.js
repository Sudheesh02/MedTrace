'use client';
import { useCallback, useEffect, useState } from 'react';
import { Info, OctagonAlert, Radio, ShieldCheck, TriangleAlert } from 'lucide-react';

export function useApi(url, deps = []) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!url) {
      setState({ status: 'idle', data: null, error: null });
      return undefined;
    }
    let dead = false;
    setState((s) => ({ status: 'loading', data: s.data && s.status !== 'idle' ? s.data : null, error: null }));
    fetch(url, { cache: 'no-store' })
      .then(async (r) => {
        let body = null;
        try {
          body = await r.json();
        } catch {
          /* non-json */
        }
        if (dead) return;
        if (!r.ok) setState({ status: 'error', data: body, error: body?.error || body?.reason || `HTTP ${r.status}` });
        else setState({ status: 'ok', data: body, error: null });
      })
      .catch((e) => !dead && setState({ status: 'error', data: null, error: String(e?.message || e) }));
    return () => {
      dead = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, tick, ...deps]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}

export const Loading = ({ what = 'Loading' }) => (
  <div className="empty"><span><span className="spin" />{what}...</span></div>
);

export const ListSkeleton = () => (
  <div style={{ padding: 12 }} aria-busy="true" aria-label="Loading alerts">{[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="skel" />)}</div>
);

export const DetailSkeleton = () => (
  <div className="stack" aria-busy="true" aria-label="Loading detail">
    <div className="panel" style={{ padding: 16 }}><div className="skel line w40" /><div className="skel line w60" /><div className="skel block" /></div>
    <div className="panel" style={{ padding: 16 }}><div className="skel line w40" /><div className="skel block tall" /></div>
  </div>
);

export const ErrorBox = ({ title, error, children }) => (
  <div className="note err"><b>{title}</b>{error ? <div className="small">{String(error)}</div> : null}{children}</div>
);

export const TIER_CLASS = { CRITICAL: 'crit', WARNING: 'warn', SECURE: 'ok' };
const TIER_BADGE = { CRITICAL: 'b-crit', WARNING: 'b-warn', SECURE: 'b-ok' };
const TIER_ICON = { CRITICAL: OctagonAlert, WARNING: TriangleAlert, SECURE: ShieldCheck };
export const TierBadge = ({ tier }) => {
  const Icon = TIER_ICON[tier] || Info;
  return <span className={`badge ${TIER_BADGE[tier] || 'b-mute'}`}><Icon className="ic" aria-hidden="true" />{tier || 'UNKNOWN'}</span>;
};

const modelFamily = (models) => ((models || []).some((m) => /nemotron/i.test(m)) ? 'Nemotron' : 'LLM');

/** What actually produced a run, derived only from the trace: LLM steps, fallback flags and the Zetaris data-source record. */
export function runMode(run) {
  if (!run) return null;
  const ds = run.data_source;
  const llm = (run.llm_steps ?? 0) > 0;
  const fb = (run.fallback_steps ?? 0) > 0;
  const fam = modelFamily(run.models);
  const q = ds && ds.queries_attempted !== null && ds.queries_attempted !== undefined ? `${ds.queries_ok}/${ds.queries_attempted} Zetaris queries succeeded` : null;
  const models = run.models?.length ? `Models: ${run.models.join(', ')}` : null;
  if (run.live) return { cls: 'b-live', live: true, text: `Real LLM (${fam}) + Zetaris live`, title: [models, q, 'No step fell back to a canned answer.'].filter(Boolean).join('. ') };
  if (llm && !fb) return { cls: 'b-info', text: `Real LLM (${fam}), local data files`, title: [models, 'No Zetaris data-source record in this trace.'].filter(Boolean).join('. ') };
  if (llm && fb) return { cls: 'b-warn', text: `LLM run with ${run.fallback_steps} fallback step(s)`, title: models || '' };
  return { cls: 'b-mute', text: 'Sample mode (rule-based, no LLM)', title: 'This trace was produced without an LLM (sample mode).' };
}

export function RunModeChip({ run }) {
  const m = runMode(run);
  if (!m) return null;
  return <span className={`badge ${m.cls}`} title={m.title}>{m.live ? <Radio className="ic" /> : null}{m.text}</span>;
}

export const pretty = (s) => String(s || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
export const num = (v, d = 1) => (v === null || v === undefined || Number.isNaN(Number(v)) ? '-' : Number(v).toLocaleString(undefined, { maximumFractionDigits: d }));
export const ago = (iso) => {
  if (!iso) return 'unknown time';
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (!Number.isFinite(s)) return 'unknown time';
  if (s < 90) return 'just now';
  if (s < 5400) return Math.round(s / 60) + ' min ago';
  if (s < 129600) return Math.round(s / 3600) + ' h ago';
  return Math.round(s / 86400) + ' d ago';
};
export const when = (iso) => (iso ? new Date(iso).toLocaleString() : '-');