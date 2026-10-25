'use client';
import { ArrowRight, Brain, BrainCircuit, CircleCheck, CircleX, TriangleAlert } from 'lucide-react';
import { ErrorBox, Loading, pretty } from './ui.js';

const VERDICT_BADGE = { flip: 'b-ok', flip_with_confounders: 'b-warn', no_flip: 'b-mute', changed_without_memory_evidence: 'b-warn', not_comparable: 'b-mute' };

const finalRound = (s) => (s.round_detail?.length ? s.round_detail[s.round_detail.length - 1] : null);
const facts = (s) => [
  ['Pair', `${s.facility_id} / ${s.medicine_id}`],
  ['Debate rounds', String(s.rounds)],
  ['Leading hypothesis', s.leading_hypothesis?.title || '-'],
  ['Escalated to human', s.escalated ? 'yes' : 'no'],
  ['Top action', `${pretty(s.top_action) || '-'} (${s.recommendations ?? '-'} rec.)`],
];

function Side({ kind, title, icon: Icon, s, other }) {
  const fr = finalRound(s);
  const mine = facts(s);
  const theirs = facts(other);
  return (
    <div className={`side ${kind}`}>
      <div className="stitle"><Icon className="ic" style={{ width: 18, height: 18, color: kind === 'after' ? 'var(--accent)' : 'var(--muted)' }} />{title}</div>
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
          <div key={k} className={`fact ${v !== theirs[i][1] ? 'chg' : ''}`}><span>{k}</span><b>{v}</b></div>
        ))}
      </div>
    </div>
  );
}

export default function MemoryCard({ api }) {
  const d = api.data;
  return (
    <section className="panel" aria-label="Memory decision flip">
      <div className="panel-h">
        <div>
          <h2>Memory decision flip: without vs with H-MEM</h2>
          <div className="sub">Compares logs/trace_without_memory.jsonl against logs/trace_with_memory.jsonl. Highlighted values changed.</div>
        </div>
        {d?.ok ? <span className={`badge ${VERDICT_BADGE[d.verdict] || 'b-mute'}`}>{pretty(d.verdict)}</span> : null}
      </div>
      <div className="panel-b">
        {api.status === 'loading' && !d ? <Loading what="Comparing traces" /> : null}
        {api.status === 'error' && !d?.without ? <ErrorBox title="Memory comparison unavailable" error={api.error} /> : null}
        {d?.ok ? (
          <>
            <div className="note" style={{ marginTop: 0 }}>{d.headline}</div>
            <div className="flipwrap">
              <Side kind="before" title="Without memory" icon={Brain} s={d.without} other={d.with} />
              <div className="flipmid"><ArrowRight className="ic" /></div>
              <Side kind="after" title="With H-MEM" icon={BrainCircuit} s={d.with} other={d.without} />
            </div>
            {d.changes.length ? (
              <>
                <h3 style={{ marginTop: 16 }}>What changed</h3>
                <div className="tablewrap">
                  <table>
                    <thead><tr><th>Field</th><th>Without</th><th>With</th></tr></thead>
                    <tbody>{d.changes.map((c) => <tr key={c.field}><td>{c.field}</td><td className="muted" style={{ wordBreak: 'break-word' }}>{c.without}</td><td style={{ wordBreak: 'break-word' }}>{c.with}</td></tr>)}</tbody>
                  </table>
                </div>
              </>
            ) : null}
            {d.confounders.length ? (
              <div className="note warn"><b><TriangleAlert className="ic" /> Caveat: reconciler inputs differ between the two traces</b> ({d.confounders.join('; ')}). The two runs were not on identical inputs, so this is evidence consistent with memory influencing the decision, not a controlled A/B proof.</div>
            ) : null}
            <div className="small" style={{ marginTop: 10 }}>
              <b>H-MEM beliefs injected in the "with memory" run:</b>{' '}
              {d.memory_present ? <code className="mono">{JSON.stringify(d.with.hmem_beliefs)}</code> : <span className="muted">none recorded</span>}
            </div>
            {d.store ? (
              <details style={{ marginTop: 6 }}>
                <summary>Current H-MEM store (logs/hmem_store.json): {d.store.episodic_memory?.length ?? 0} officer decision(s) recorded</summary>
                <pre>{JSON.stringify(d.store, null, 2)}</pre>
              </details>
            ) : null}
          </>
        ) : null}
        {d && !d.ok ? <div className="note warn">{d.reason}</div> : null}
      </div>
    </section>
  );
}