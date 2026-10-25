'use client';
import { ErrorBox, Loading, pretty, when } from './ui.js';

const VERDICT_BADGE = { flip: 'b-ok', flip_with_confounders: 'b-warn', no_flip: 'b-mute', changed_without_memory_evidence: 'b-warn', not_comparable: 'b-mute' };

function Side({ title, s }) {
  return (
    <div className="card">
      <h4>{title}</h4>
      <div className="small mono muted">{s.file}</div>
      <ul className="tight small">
        <li>Pair: {s.facility_id} / {s.medicine_id}</li>
        <li>Debate: {s.rounds} round(s) - {s.round_detail.map((r) => `R${r.round} ${r.accepted ? 'accepted' : 'rejected'} (${r.confidence})`).join(', ')}</li>
        <li>Leading hypothesis: <b>{s.leading_hypothesis?.title || '-'}</b></li>
        <li>Escalated to human: <b>{s.escalated ? 'yes' : 'no'}</b></li>
        <li>Top action: <b>{pretty(s.top_action) || '-'}</b> ({s.recommendations ?? '-'} recommendations)</li>
      </ul>
    </div>
  );
}

export default function MemoryCard({ api }) {
  const d = api.data;
  return (
    <section className="panel" aria-label="Memory decision flip">
      <header>
        <h2>Memory "decision flip" - without vs with H-MEM</h2>
        <span className="badge b-mute">logs/trace_without_memory.jsonl vs logs/trace_with_memory.jsonl</span>
      </header>
      {api.status === 'loading' && !d ? <Loading what="Comparing traces" /> : null}
      {api.status === 'error' && !d?.without ? <ErrorBox title="Memory comparison unavailable" error={api.error} /> : null}
      {d?.ok ? (
        <>
          <div className="note"><span className={`badge ${VERDICT_BADGE[d.verdict] || 'b-mute'}`}>{pretty(d.verdict)}</span> {d.headline}</div>
          <div className="flip">
            <Side title="Without memory" s={d.without} />
            <Side title="With H-MEM" s={d.with} />
          </div>
          {d.changes.length ? (
            <table className="diff" style={{ marginTop: 8 }}>
              <thead><tr><th>What changed</th><th>Without</th><th>With</th></tr></thead>
              <tbody>{d.changes.map((c) => <tr key={c.field} style={{ cursor: 'default' }}><td>{c.field}</td><td>{c.without}</td><td>{c.with}</td></tr>)}</tbody>
            </table>
          ) : null}
          {d.confounders.length ? (
            <div className="note warn small"><b>Caveat - reconciler inputs differ between the two traces</b> ({d.confounders.join('; ')}). The two runs were not on identical inputs, so this is evidence consistent with memory influencing the decision, not a controlled A/B proof.</div>
          ) : null}
          <div className="small" style={{ marginTop: 8 }}>
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
    </section>
  );
}