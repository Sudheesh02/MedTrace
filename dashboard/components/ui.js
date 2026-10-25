'use client';
import { useCallback, useEffect, useState } from 'react';
import { Info, OctagonAlert, ShieldCheck, TriangleAlert } from 'lucide-react';

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
  <div style={{ padding: 12 }}>{[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="skel" />)}</div>
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

export const pretty = (s) => String(s || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
export const num = (v, d = 1) => (v === null || v === undefined || Number.isNaN(Number(v)) ? '-' : Number(v).toLocaleString(undefined, { maximumFractionDigits: d }));
export const when = (iso) => (iso ? new Date(iso).toLocaleString() : '-');