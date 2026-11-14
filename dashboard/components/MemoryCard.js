'use client';
import { ArrowRight, Brain, BrainCircuit, CircleCheck, CircleX, History, ShieldCheck, TriangleAlert } from 'lucide-react';
import { ErrorBox, Loading, RunModeChip, pretty } from './ui.js';

const VERDICT_BADGE = {
  flip: 'badge-ok',
  flip_with_confounders: 'badge-warn',
  no_flip: 'badge-mute',
  changed_without_memory_evidence: 'badge-warn',
  not_comparable: 'badge-mute'
};

const VERDICT_TEXT = {
  flip: 'Verdict flipped on identical inputs',
  flip_with_confounders: 'Verdict flipped, inputs differ',
  no_flip: 'No verdict flip',
  changed_without_memory_evidence: 'Changed, no memory evidence',
  not_comparable: 'Not comparable'
};

const finalRound = (s) => (s.round_detail?.length ? s.round_detail[s.round_detail.length - 1] : null);

const facts = (s) => [
  ['Pair', `${s.facility_id} / ${s.medicine_id}`],
  ['Run ID', s.run_id || '-'],
  ['Debate rounds', String(s.rounds)],
  ['Leading hypothesis', s.leading_hypothesis?.title || '-'],
  ['Escalated to human', s.escalated ? 'yes' : 'no'],
  ['Top recommended action', `${pretty(s.top_action) || '-'} (${s.recommendations ?? '-'} recommendations)`],
];

const CHANGING = new Set(['Run ID']);

function Side({ kind, title, icon: Icon, s, other }) {
  const fr = finalRound(s);
  const mine = facts(s);
  const theirs = facts(other);

  return (
    <div className={`verdict-card flex-1 ${kind === 'after' ? 'investigator' : ''}`}>
      <div className="verdict-card-header">
        <h3 className="cluster-sm">
          <Icon size={18} color={kind === 'after' ? 'var(--primary)' : 'var(--muted)'} aria-hidden="true" />
          <span>{title}</span>
        </h3>
        <RunModeChip run={s} />
      </div>

      <div className="mono muted text-xs">{s.file}</div>

      {fr ? (
        <div className={`decision-box ${fr.accepted ? 'acc' : 'rej'}`}>
          {fr.accepted ? <CircleCheck size={18} /> : <CircleX size={18} />}
          <div>
            <strong>
              {fr.accepted ? 'Accepted' : 'Rejected'} at confidence {fr.confidence}
            </strong>
            <p className="muted text-xs">
              Final Skeptic result, round {fr.round}{s.escalated ? ', then escalated to a human officer' : ''}
            </p>
          </div>
        </div>
      ) : null}

      <div className="cluster-xs">
        {(s.round_detail || []).map((r, idx) => (
          <span key={r.round} className="cluster-xs text-xs">
            {idx > 0 ? <ArrowRight size={12} color="var(--muted)" /> : null}
            <span className={`badge ${r.accepted ? 'badge-ok' : 'badge-crit'}`}>
              R{r.round} {r.accepted ? 'accepted' : 'rejected'} ({r.confidence})
            </span>
          </span>
        ))}
      </div>

      <div className="stack-xs mt-sm fact-list">
        {mine.map(([k, v], i) => {
          const changed = !CHANGING.has(k) && v !== theirs[i][1];
          return (
            <div key={k} className={`fact-item ${changed ? 'changed' : ''}`}>
              <span className="muted">{k}</span>
              <strong>{v}</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Comparison({ c }) {
  const live = c.kind === 'live';
  const inp = c.without.inputs;

  return (
    <div className="stack-md">
      <div className="case-file-summary-banner">
        <strong>{c.headline}</strong>
      </div>

      <div className="cluster-md">
        <Side kind="before" title={c.before_label} icon={Brain} s={c.without} other={c.with} />
        <div className="pad-sm cluster-sm">
          <ArrowRight size={20} color="var(--primary)" />
        </div>
        <Side kind="after" title={c.after_label} icon={BrainCircuit} s={c.with} other={c.without} />
      </div>

      {c.changes.length ? (
        <div>
          <h3>Summary of changes between runs</h3>
          <div className="table-wrap mt-sm">
            <table>
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Before (No memory)</th>
                  <th>After (Officer rejection remembered)</th>
                </tr>
              </thead>
              <tbody>
                {c.changes.map((x) => (
                  <tr key={x.field}>
                    <td><strong>{x.field}</strong></td>
                    <td className="muted">{pretty(x.without)}</td>
                    <td className="diff-highlight">{pretty(x.with)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {c.inputs_identical ? (
        <div className="note-ok">
          <ShieldCheck size={16} aria-hidden="true" className="icon-inline" />
          <strong>Identical inputs verified:</strong> The complete Reconciler input record is identical in both traces ({inp.discrepancies_found} discrepancies, usable stock {inp.usable_stock}, shortfall {inp.shortfall}). The recorded context differs only in the injected H-MEM beliefs.
        </div>
      ) : c.confounders.length || !c.inputs_identical ? (
        <div className="note-warn">
          <TriangleAlert size={16} aria-hidden="true" className="icon-inline" />
          <strong>Caveat: Reconciler inputs differ between traces</strong> ({c.confounders.join('; ')}). Evidence consistent with memory influencing the decision, not a controlled A/B proof.
        </div>
      ) : null}

      {live ? (
        <p className="muted text-xs">
          <strong>Read with care:</strong> One real-LLM run each. Single before/after pair demonstrates the mechanism working end-to-end, not a statistical estimate.
        </p>
      ) : null}

      <div className="text-sm">
        <strong>H-MEM beliefs injected in the "after" run:</strong>{' '}
        {c.memory_present ? (
          <code className="code-badge">{JSON.stringify(c.with.hmem_beliefs)}</code>
        ) : (
          <span className="muted">none recorded</span>
        )}
      </div>

      <div className="mono muted text-xs">
        Sources: {c.sources.join(', ')}
      </div>
    </div>
  );
}

export default function MemoryCard({ api }) {
  const d = api.data;
  const sec = d?.secondary;

  return (
    <section className="case-file-pane" aria-label="Memory decision flip">
      <div className="case-file-header">
        <div className="case-file-header-top">
          <div>
            <h1>How officer decisions flip AI recommendations</h1>
            <p className="case-file-subtitle">
              Demonstrates Meterless H-MEM cross-session episodic memory adapting to human officer feedback.
            </p>
          </div>
          {d?.ok ? (
            <span className={`badge ${VERDICT_BADGE[d.verdict] || 'badge-mute'}`}>
              {VERDICT_TEXT[d.verdict] || pretty(d.verdict)}
            </span>
          ) : null}
        </div>
      </div>

      <div className="case-tab-content">
        {api.status === 'loading' && !d ? <Loading what="Comparing deliberation traces" /> : null}
        {api.status === 'error' && !d?.without ? <ErrorBox title="Memory comparison unavailable" error={api.error} /> : null}

        {d?.ok ? (
          <>
            <Comparison c={d} />

            {sec ? (
              <details className="mt-lg">
                <summary>
                  <History size={14} className="icon-inline" />
                  Secondary evidence: {sec.title}{' '}
                  <span className={`badge ${VERDICT_BADGE[sec.verdict] || 'badge-mute'} ml-sm`}>
                    {VERDICT_TEXT[sec.verdict] || pretty(sec.verdict)}
                  </span>
                </summary>
                <div className="mt-sm">
                  <Comparison c={sec} />
                </div>
              </details>
            ) : null}

            {d.store ? (
              <details className="mt-sm">
                <summary>Current H-MEM Store ({d.store.episodic_memory?.length ?? 0} officer decision records)</summary>
                <pre>{JSON.stringify(d.store, null, 2)}</pre>
              </details>
            ) : null}
          </>
        ) : null}

        {d && !d.ok ? <div className="note-warn">{d.reason}</div> : null}
      </div>
    </section>
  );
}
