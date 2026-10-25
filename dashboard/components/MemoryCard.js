'use client';
import { ArrowRight, Brain, BrainCircuit, CircleCheck, CircleX, History, ShieldCheck, TriangleAlert } from 'lucide-react';
import { ErrorBox, Loading, RunModeChip, pretty } from './ui.js';

const VERDICT_BADGE = { flip: 'b-ok', flip_with_confounders: 'b-warn', no_flip: 'b-mute', changed_without_memory_evidence: 'b-warn', not_comparable: 'b-mute' };
const VERDICT_TEXT = { flip: 'Flip, identical inputs', flip_with_confounders: 'Flip, inputs differ', no_flip: 'No flip', changed_without_memory_evidence: 'Changed, no memory evidence', not_comparable: 'Not comparable' };

const finalRound = (s) => (s.round_detail?.length ? s.round_detail[s.round_detail.length - 1] : null);
const facts = (s) => [
  ['Pair', `${s.facility_id} / ${s.medicine_id}`],
  ['Run', s.run_id || '-'],
  ['Debate rounds', String(s.rounds)],
  ['Leading hypothesis', s.leading_hypothesis?.title || '-'],
  ['Escalated to human', s.escalated ? 'yes' : 'no'],
  ['Top action', `${pretty(s.top_action) || '-'} (${s.recommendations ?? '-'} rec.)`],
];
const CHANGING = new Set(['Run']);

function Side({ kind, title, icon: Icon, s, other }) {
  const fr = finalRound(s);
  const mine = facts(s);
  const theirs = facts(other);
  return (
    <div className={`side ${kind}`}>
      <div className="stitle"><Icon className="ic" style={{ width: 18, height: 18, color: kind === 'after' ? 'var(--accent)' : 'var(--muted)' }} />{title}</div>
      <div className="chiprow" style={{ marginTop: 0 }}><RunModeChip run={s} /></div>
      <div className="small mono muted">{s.file}</div>
      {fr ? (
        <div className={`decision ${fr.accepted ? 'acc' : 'rej'}`}>
          {fr.accepted ? <CircleCheck /> : <CircleX />}
          <div>
            <b>{fr.accepted ? 'Accepted' : 'Rejected'} at confidence {fr.confidence}</b>
            <span>Final Skeptic result, round {fr.round}{s.escalated ? ', then escalated to a human' : ''}</span>
          </div>
        </div>
      ) : null}
      <div className="rounds" style={{ marginTop: 0 }}>
        {(s.round_detail || []).map((r, idx) => (
          <span key={r.round} className="row" style={{ gap: 6 }}>
            {idx > 0 ? <ArrowRight className="ic arrow" /> : null}
            <span className={`round ${r.accepted ? 'acc' : 'rej'}`}>R{r.round} {r.accepted ? 'accepted' : 'rejected'} <span className="mono">{r.confidence}</span></span>
          </span>
        ))}
      </div>
      <div>
        {mine.map(([k, v], i) => (
          <div key={k} className={`fact ${!CHANGING.has(k) && v !== theirs[i][1] ? 'chg' : ''}`}><span>{k}</span><b>{v}</b></div>
        ))}
      </div>
    </div>
  );
}

function Comparison({ c }) {
  const live = c.kind === 'live';
  const inp = c.without.inputs;
  return (
    <>
      <div className="note" style={{ marginTop: 0 }}>{c.headline}</div>
      <div className="flipwrap">
        <Side kind="before" title={c.before_label} icon={Brain} s={c.without} other={c.with} />
        <div className="flipmid"><ArrowRight className="ic" /></div>
        <Side kind="after" title={c.after_label} icon={BrainCircuit} s={c.with} other={c.without} />
      </div>
      {c.changes.length ? (
        <>
          <h3 style={{ marginTop: 16 }}>What changed</h3>
          <div className="tablewrap">
            <table>
              <thead><tr><th>Field</th><th>Before</th><th>After</th></tr></thead>
              <tbody>{c.changes.map((x) => <tr key={x.field}><td>{x.field}</td><td className="muted" style={{ wordBreak: 'break-word' }}>{pretty(x.without)}</td><td style={{ wordBreak: 'break-word' }}><b>{pretty(x.with)}</b></td></tr>)}</tbody>
            </table>
          </div>
        </>
      ) : null}
      {c.inputs_identical ? (
        <div className="note small" style={{ borderLeftColor: 'var(--ok)', borderColor: 'var(--ok-line)', background: 'var(--ok-bg)' }}>
          <b><ShieldCheck className="ic" /> Same inputs, checked in the data:</b> the complete Reconciler record is identical in both traces ({inp.discrepancies_found} discrepancies, usable stock {inp.usable_stock}, shortfall {inp.shortfall}). The recorded world-model context differs only in <span className="mono">{c.context_diff.join(', ') || 'nothing'}</span> (the injected H-MEM beliefs and the hash that includes them).
        </div>
      ) : c.confounders.length || !c.inputs_identical ? (
        <div className="note warn small"><b><TriangleAlert className="ic" /> Caveat: reconciler inputs differ between the two traces</b>{c.confounders.length ? ` (${c.confounders.join('; ')})` : ''}. The two runs were not on identical inputs, so this is evidence consistent with memory influencing the decision, not a controlled A/B proof.</div>
      ) : null}
      {live ? <div className="note warn small" style={{ marginTop: 8 }}><b>Read with care:</b> one real-LLM run each. LLM output is not deterministic, so a single before/after pair shows the mechanism working end to end, not a statistical estimate.{c.changes.some((x) => /^Skeptic/.test(x.field)) ? '' : ' The Skeptic verdict and confidence are the same in both runs; only the fields listed above changed.'}</div> : null}
      <div className="small" style={{ marginTop: 10 }}>
        <b>H-MEM beliefs injected in the "after" run:</b>{' '}
        {c.memory_present ? <code className="mono">{JSON.stringify(c.with.hmem_beliefs)}</code> : <span className="muted">none recorded</span>}
      </div>
      <div className="small muted" style={{ marginTop: 6 }}>Sources: {c.sources.join(', ')}.</div>
    </>
  );
}

export default function MemoryCard({ api }) {
  const d = api.data;
  const sec = d?.secondary;
  return (
    <section className="panel" aria-label="Memory decision flip">
      <div className="panel-h">
        <div>
          <h2>Memory decision flip: before vs after H-MEM</h2>
          <div className="sub">{d?.ok ? d.title : 'Compares stored traces with and without remembered officer feedback. Highlighted values changed.'}</div>
        </div>
        {d?.ok ? <span className={`badge ${VERDICT_BADGE[d.verdict] || 'b-mute'}`}>{VERDICT_TEXT[d.verdict] || pretty(d.verdict)}</span> : null}
      </div>
      <div className="panel-b">
        {api.status === 'loading' && !d ? <Loading what="Comparing traces" /> : null}
        {api.status === 'error' && !d?.without ? <ErrorBox title="Memory comparison unavailable" error={api.error} /> : null}
        {d?.ok ? (
          <>
            <Comparison c={d} />
            {sec ? (
              <details className="secondary" style={{ marginTop: 18 }}>
                <summary><History className="ic" style={{ width: 13, height: 13, verticalAlign: -2, marginRight: 6 }} />Secondary evidence: {sec.title} <span className={`badge ${VERDICT_BADGE[sec.verdict] || 'b-mute'}`} style={{ marginLeft: 6 }}>{VERDICT_TEXT[sec.verdict] || pretty(sec.verdict)}</span></summary>
                <div style={{ marginTop: 10 }}><Comparison c={sec} /></div>
              </details>
            ) : null}
            {d.store ? (
              <details style={{ marginTop: 10 }}>
                <summary>Current H-MEM store (logs/hmem_store.json): {d.store.episodic_memory?.length ?? 0} officer decision(s) recorded</summary>
                <pre>{JSON.stringify(d.store, null, 2)}</pre>
              </details>
            ) : <div className="small muted" style={{ marginTop: 10 }}>No logs/hmem_store.json in this checkout (the store is created at run time); the beliefs above are the ones recorded in the trace itself.</div>}
          </>
        ) : null}
        {d && !d.ok ? <div className="note warn">{d.reason}</div> : null}
      </div>
    </section>
  );
}