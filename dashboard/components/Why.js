'use client';
import { ErrorBox, Loading, pretty, when } from './ui.js';

export default function Why({ item, api, backend }) {
  const run = api.data?.run;
  const pack = api.data?.pack;
  return (
    <aside className="panel" aria-label="Why">
      <header>
        <h2>Why - step-by-step trace</h2>
        {run ? <span className="badge b-mute">{run.steps.length} steps</span> : null}
      </header>
      {!item ? <div className="empty">Select an alert to see its trace.</div> : null}
      {item && api.status === 'loading' && !api.data ? <Loading what="Loading trace" /> : null}
      {item && api.status === 'error' ? <ErrorBox title="Trace unavailable" error={api.error} /> : null}
      {item && api.data?.ok && !run ? <div className="empty">No trace stored for this pair yet.</div> : null}
      {run ? (
        <>
          <div className="small muted" style={{ marginBottom: 6 }}>
            Models in this run: {run.models.length ? run.models.join(', ') : 'n/a'}.{' '}
            Data layer: {backend?.reachable ? (backend.zetaris_enabled ? 'Zetaris enabled on backend' : 'Zetaris disabled on backend (local files)') : 'traces do not record which data layer served each query'}.
            {run.reasoning_tag_leak_stripped ? ' Leaked <think> reasoning was stripped from displayed text.' : ''}
          </div>
          <div className="steps">
            {run.steps.map((s) => {
              const isInv = s.agent === 'InvestigatorAgent' && s.action === 'HYPOTHESES_GENERATED' && pack?.winning_hypothesis?.confirming_query;
              return (
                <div key={s.i} className={`step ${s.fallback ? 'fb' : s.llm_used ? 'llm' : ''}`}>
                  <div className="meta">
                    <b className="small">{s.i}. {s.agent}</b>
                    <span className="badge b-info">{pretty(s.action)}</span>
                    <span className="badge b-mute mono" title="model recorded in trace">{s.model || 'model n/a'}</span>
                    <span className={`badge ${s.llm_used ? 'b-ok' : 'b-mute'}`}>{s.llm_used === null ? 'llm n/a' : s.llm_used ? 'LLM used' : 'no LLM'}</span>
                    <span className={`badge ${s.fallback ? 'b-warn' : 'b-mute'}`}>{s.fallback === null ? 'fallback n/a' : `fallback: ${s.fallback}`}</span>
                  </div>
                  <div className="small">{s.summary}</div>
                  {isInv ? <details><summary>tool / Zetaris query (from action pack)</summary><pre>{pack.winning_hypothesis.confirming_query}</pre></details> : null}
                  {s.text ? <div className="txt">{s.text}</div> : null}
                  <div className="sub">{when(s.ts)}{s.tokens ? ` | ${s.tokens} tokens` : ''}</div>
                </div>
              );
            })}
          </div>
        </>
      ) : null}
    </aside>
  );
}