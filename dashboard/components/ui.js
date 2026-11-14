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
        if (!r.ok) {
          setState({ status: 'error', data: body, error: body?.error || body?.reason || `HTTP ${r.status}` });
        } else {
          setState({ status: 'ok', data: body, error: null });
        }
      })
      .catch((e) => !dead && setState({ status: 'error', data: null, error: String(e?.message || e) }));
    return () => {
      dead = true;
    };
  }, [url, tick, ...deps]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}

/**
 * useCountUp: Smooth 650ms count-up animation for hero metrics
 */
export function useCountUp(targetVal, duration = 650, decimals = 1) {
  const target = Number(targetVal);
  const isValid = targetVal !== null && targetVal !== undefined && !Number.isNaN(target);
  const [current, setCurrent] = useState(isValid ? target : 0);

  useEffect(() => {
    if (!isValid) return;
    const startVal = current;
    const diff = target - startVal;
    if (Math.abs(diff) < 0.0001) return;

    let startTime = null;
    let animFrame = null;

    const step = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      // easeOutCubic curve
      const ease = 1 - Math.pow(1 - progress, 3);
      setCurrent(startVal + diff * ease);

      if (progress < 1) {
        animFrame = requestAnimationFrame(step);
      } else {
        setCurrent(target);
      }
    };

    animFrame = requestAnimationFrame(step);
    return () => {
      if (animFrame) cancelAnimationFrame(animFrame);
    };
  }, [targetVal, duration, isValid]);

  if (!isValid) return '-';
  return current.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function CountUpNum({ value, decimals = 1, unit = '' }) {
  const animated = useCountUp(value, 650, decimals);
  return (
    <span className="count-up-number">
      {animated}
      {unit ? <span className="stat-unit"> {unit}</span> : null}
    </span>
  );
}

export const Loading = ({ what = 'Loading' }) => (
  <div className="empty-state">
    <span className="loading-spinner" aria-hidden="true" />
    <span>{what}...</span>
  </div>
);

export const ListSkeleton = () => (
  <div className="skeleton-list" aria-busy="true" aria-label="Loading queue">
    {[0, 1, 2, 3, 4, 5].map((i) => (
      <div key={i} className="skeleton-row" />
    ))}
  </div>
);

export const DetailSkeleton = () => (
  <div className="skeleton-detail" aria-busy="true" aria-label="Loading case details">
    <div className="skeleton-card" />
    <div className="skeleton-card" />
  </div>
);

export const ErrorBox = ({ title, error, children }) => (
  <div className="note-error" role="alert">
    <strong>{title}</strong>
    {error ? <div className="note-error-detail">{String(error)}</div> : null}
    {children}
  </div>
);

export const TIER_CLASS = { CRITICAL: 'crit', WARNING: 'warn', SECURE: 'ok' };
export const TIER_ICON = { CRITICAL: OctagonAlert, WARNING: TriangleAlert, SECURE: ShieldCheck };

export const TierBadge = ({ tier }) => {
  const norm = String(tier || '').toUpperCase();
  const cls = TIER_CLASS[norm] || 'mute';
  const Icon = TIER_ICON[norm] || Info;
  return (
    <span className={`badge badge-${cls}`}>
      <Icon size={13} aria-hidden="true" />
      <span>{pretty(tier || 'Unknown')}</span>
    </span>
  );
};

export function runMode(run) {
  if (!run) return null;
  if (run.live) {
    return { cls: 'badge-ok', live: true, text: 'Live audit' };
  }
  if (run.llm_steps > 0) {
    return { cls: 'badge-info', text: 'Multi-agent audit' };
  }
  return { cls: 'badge-mute', text: 'Audit replay' };
}

export function RunModeChip({ run }) {
  const m = runMode(run);
  if (!m) return null;
  return (
    <span className={`badge ${m.cls}`}>
      {m.live ? <Radio size={12} aria-hidden="true" /> : null}
      <span>{m.text}</span>
    </span>
  );
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
