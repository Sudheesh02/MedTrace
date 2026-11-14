'use client';
import { Bot, Calculator, Database, GitBranch, Gavel, Route, Search, ShieldCheck, Sparkles, Workflow } from 'lucide-react';
import { ErrorBox, Loading, pretty } from './ui.js';

const iconFor = (name) => {
  const n = String(name || '').toLowerCase();
  if (n.includes('investig')) return Search;
  if (n.includes('skeptic')) return Gavel;
  if (n.includes('audit') || n.includes('number')) return Calculator;
  if (n.includes('reconcil')) return GitBranch;
  if (n.includes('zetaris') || n.includes('datalayer')) return Database;
  if (n.includes('plan') || n.includes('action')) return Route;
  if (n.includes('memory') || n.includes('hmem')) return Sparkles;
  if (n.includes('orchestr') || n.includes('supervis')) return Workflow;
  if (n.includes('guard') || n.includes('safety')) return ShieldCheck;
  return Bot;
};

const seconds = (a, b) => {
  const x = Date.parse(a);
  const y = Date.parse(b);
  if (Number.isNaN(x) || Number.isNaN(y)) return null;
  const s = (y - x) / 1000;
  return s < 0 ? null : s;
};

export default function Why({ item, api }) {
  const run = api.data?.run;
  const pack = api.data?.pack;

  if (!item) return null;

  if (api.status === 'loading' && !api.data) {
    return <Loading what="Loading clinical deliberation trace" />;
  }

  if (api.status === 'error') {
    return <ErrorBox title="Deliberation trace unavailable" error={api.error} />;
  }

  if (!run || !run.steps?.length) {
    return (
      <div className="empty-state">
        <p>No decision trace is recorded for this case yet.</p>
      </div>
    );
  }

  return (
    <div className="decision-trace-container">
      <div className="cluster-spread mb-md">
        <div>
          <h3>Clinical Deliberation Trace</h3>
          <p className="muted text-sm">
            Step-by-step record of deliberation between Investigator and Number Auditor.
          </p>
        </div>
        <span className="badge badge-mute">{run.steps.length} steps</span>
      </div>

      {/* Timeline Steps */}
      <div className="timeline">
        {run.steps.map((s, idx) => {
          const Icon = iconFor(s.agent);
          const dt = idx > 0 ? seconds(run.steps[idx - 1].ts, s.ts) : null;
          const isInv = s.agent === 'InvestigatorAgent' && s.action === 'HYPOTHESES_GENERATED' && pack?.winning_hypothesis?.confirming_query;

          return (
            <div key={s.i || idx} className="timeline-step">
              <div className="timeline-node" aria-hidden="true">
                <Icon size={11} />
              </div>

              <div className="timeline-header">
                <strong>{s.i}. {s.agent}</strong>
                <span className="badge badge-mute">{pretty(s.action)}</span>
                {dt !== null ? (
                  <span className="mono muted text-xs">
                    +{dt < 10 ? dt.toFixed(1) : Math.round(dt)}s
                  </span>
                ) : null}
                {s.fallback ? (
                  <span className="badge badge-warn" title="Fallback rule applied">
                    Fallback rule applied
                  </span>
                ) : null}
              </div>

              <p className="mt-xs text-sm">
                {s.summary}
              </p>

              {isInv ? (
                <details className="mt-xs">
                  <summary>Verification query</summary>
                  <pre>{pack.winning_hypothesis.confirming_query}</pre>
                </details>
              ) : null}

              {s.text ? (
                <div className="timeline-text-block">
                  {s.text}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
