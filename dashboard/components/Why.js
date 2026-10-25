'use client';
import { Bot, Calculator, Cpu, GitBranch, Gavel, Route, Search, ShieldCheck, Sparkles, Workflow } from 'lucide-react';
import { ErrorBox, Loading, pretty, when } from './ui.js';

const PALETTE = ['#5aa7ff', '#b99cff', '#3fd18f', '#f7b035', '#ff8fb1', '#4fd1d9', '#ff9a62'];
const colorFor = (name) => {
  let h = 0;
  for (const c of String(name || '')) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length];
};
const iconFor = (name) => {
  const n = String(name || '').toLowerCase();
  if (n.includes('investig')) return Search;
  if (n.includes('skeptic')) return Gavel;
  if (n.includes('audit') || n.includes('number')) return Calculator;
  if (n.includes('reconcil')) return GitBranch;
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

export default function Why({ item, api, backend }) {
  const run = api.data?.run;
  const pack = api.data?.pack;
  if (!item) return null;
  const agents = run ? [...new Set(run.steps.map((s) => s.agent))] : [];
  return (
    <aside className="panel why" aria-label="Why">
      <div className="panel-h">
        <h2>Why - decision trace</h2>
        {run ? <span className="badge b-mute">{run.steps.length} steps</span> : null}
      </div>
      {api.status === 'loading' && !api.data ? <Loading what="Loading trace" /> : null}
      {api.status === 'error' ? <div style={{ padding: 12 }}><ErrorBox title="Trace unavailable" error={api.error} /></div> : null}
      {api.data?.ok && !run ? <div className="empty">No trace stored for this pair yet.</div> : null}
      {run ? (
        <>
          <div className="legend">
            <span>Models: {run.models.length ? run.models.join(', ') : 'n/a'}</span>
            <span>Data layer: {backend?.reachable ? (backend.zetaris_enabled ? 'Zetaris enabled on backend' : 'Zetaris disabled on backend (local files)') : 'traces do not record which data layer served each query'}</span>
            {run.reasoning_tag_leak_stripped ? <span>Leaked reasoning tags were stripped from displayed text.</span> : null}
            <span className="row" style={{ gap: 10 }}>
              {agents.map((a) => <span key={a} className="row" style={{ gap: 4 }}><span className="dot" style={{ background: colorFor(a) }} />{a}</span>)}
            </span>
          </div>
          <div className="tl">
            {run.steps.map((s, idx) => {
              const Icon = iconFor(s.agent);
              const isInv = s.agent === 'InvestigatorAgent' && s.action === 'HYPOTHESES_GENERATED' && pack?.winning_hypothesis?.confirming_query;
              const dt = idx > 0 ? seconds(run.steps[idx - 1].ts, s.ts) : null;
              return (
                <div key={s.i} className={`tli ${s.fallback ? 'fb' : ''}`} style={{ '--nc': colorFor(s.agent) }}>
                  <div className="node"><Icon className="ic" /></div>
                  <div className="th">
                    <span className="agent">{s.i}. {s.agent}</span>
                    <span className="badge b-mute">{pretty(s.action)}</span>
                    {dt !== null ? <span className="delta" title="time since previous step">+{dt < 10 ? dt.toFixed(1) : Math.round(dt)}s</span> : null}
                  </div>
                  <div className="sm">{s.summary}</div>
                  <div className="meta">
                    <span className="badge b-mute mono" title="model recorded in trace"><Cpu className="ic" />{s.model || 'model n/a'}</span>
                    <span className={`badge ${s.llm_used ? 'b-ok' : 'b-mute'}`}>{s.llm_used === null ? 'llm n/a' : s.llm_used ? 'LLM used' : 'no LLM'}</span>
                    <span className={`badge ${s.fallback ? 'b-warn' : 'b-mute'}`}>{s.fallback === null ? 'fallback n/a' : `fallback: ${s.fallback}`}</span>
                    {s.tokens ? <span className="badge b-mute">{s.tokens} tok</span> : null}
                  </div>
                  {isInv ? <details><summary>tool / Zetaris query (from action pack)</summary><pre>{pack.winning_hypothesis.confirming_query}</pre></details> : null}
                  {s.text ? <div className="txt">{s.text}</div> : null}
                  <div className="sub" style={{ marginTop: 2 }}>{when(s.ts)}</div>
                </div>
              );
            })}
          </div>
        </>
      ) : null}
    </aside>
  );
}