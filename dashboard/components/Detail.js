'use client';
import { useState } from 'react';
import { ArrowLeft, ArrowRight, CircleCheck, CircleX, Gavel, MousePointerClick, Play, Search, UserRoundCheck, Swords } from 'lucide-react';
import { DetailSkeleton, ErrorBox, TierBadge, num, pretty, when } from './ui.js';

function Metrics({ item }) {
  const cells = [
    ['Trust-adjusted cover (days)', num(item.trust_cover_days, 2)],
    ['Naive LMIS cover (days)', num(item.naive_cover_days, 2)],
    ['Usable / ledger stock', `${num(item.usable_stock, 0)} / ${num(item.ledger_stock, 0)}`],
    ['Quarantined units', num(item.quarantined_stock, 0)],
    ['Audit drift (units)', num(item.audit_drift, 0)],
    ['Shortfall (units)', num(item.shortfall_units, 1), Number(item.shortfall_units) > 0],
    ['Stockout risk', item.p_stockout_risk === null || item.p_stockout_risk === undefined ? '-' : `${num(item.p_stockout_risk * 100, 0)}%`],
  ];
  return <div className="metrics">{cells.map(([l, v, hl]) => <div key={l} className={`metric-c ${hl ? 'hl' : ''}`}><b>{v}</b><span>{l}</span></div>)}</div>;
}

export function Verdicts({ run }) {
  const lastHyp = [...run.rounds].reverse().find((r) => r.hypotheses.length);
  const fs = run.final_skeptic;
  const state = fs ? (fs.accepted ? 'acc' : 'rej') : '';
  const conf = typeof fs?.confidence === 'number' ? fs.confidence : Number(fs?.confidence);
  const debate = run.rounds.filter((r) => r.skeptic);
  return (
    <>
      <div className="vs">
        <div className="vcard inv">
          <div className="who">
            <h4><Search className="ic" />Investigator</h4>
            <span className="badge b-info">{run.rounds.length} round{run.rounds.length === 1 ? '' : 's'}</span>
          </div>
          {run.leading_hypothesis ? (
            <div>
              <div className="sub">Leading hypothesis</div>
              <div style={{ fontWeight: 650, fontSize: 14 }}>{run.leading_hypothesis.title}</div>
              {run.leading_hypothesis.likelihood !== null ? <div className="sub">likelihood {num(run.leading_hypothesis.likelihood * 100, 0)}%</div> : null}
            </div>
          ) : <p className="muted">No hypotheses recorded in this trace.</p>}
          {lastHyp ? lastHyp.hypotheses.map((h) => (
            <div className="hyp" key={h.id}>
              <div className="hl"><span>{h.title}</span><span>{h.likelihood === null ? '-' : `${num(h.likelihood * 100, 0)}%`}</span></div>
              <div className="meter"><i style={{ width: `${Math.round((h.likelihood || 0) * 100)}%` }} /></div>
            </div>
          )) : null}
        </div>

        <div className="vs-mid"><span><Swords size={13} /></span></div>

        <div className={`vcard skep ${state}`}>
          <div className="who">
            <h4><Gavel className="ic" />Skeptic + Number Auditor</h4>
          </div>
          {fs ? (
            <>
              <div className={`verdict-big ${state}`}>{fs.accepted ? <CircleCheck /> : <CircleX />}{fs.accepted ? 'ACCEPTED' : 'REJECTED'}</div>
              <div>
                <div className="row spread small"><span className="muted">Skeptic confidence</span><b>{fs.confidence ?? '-'}</b></div>
                <div className={`meter ${fs.accepted ? 'ok' : 'crit'}`}><i style={{ width: `${Math.round((Number.isFinite(conf) ? conf : 0) * 100)}%` }} /></div>
              </div>
              <div className="row small">
                <span className="muted">Number Auditor</span>
                <span className={`badge ${fs.numbers_valid === null ? 'b-mute' : fs.numbers_valid ? 'b-ok' : 'b-crit'}`}>{fs.numbers_valid === null ? 'n/a' : fs.numbers_valid ? 'numbers valid' : 'numbers INVALID'}</span>
              </div>
              <p className="small" style={{ color: 'var(--ink2)' }}>{fs.critique || <span className="muted">No critique text.</span>}</p>
              {fs.flagged?.length ? <ul className="tight small">{fs.flagged.map((f, i) => <li key={i}>{f}</li>)}</ul> : null}
            </>
          ) : <p className="muted">No Skeptic evaluation recorded in this trace.</p>}
        </div>
      </div>

      {debate.length ? (
        <div className="rounds" aria-label="Debate rounds">
          <span className="sub" style={{ marginRight: 4 }}>Debate</span>
          {debate.map((r, idx) => (
            <span key={r.round} className="row" style={{ gap: 6 }}>
              {idx > 0 ? <ArrowRight className="ic arrow" /> : null}
              <span className={`round ${r.skeptic.accepted ? 'acc' : 'rej'}`}>{r.skeptic.accepted ? <CircleCheck className="ic" /> : <CircleX className="ic" />}R{r.round} {r.skeptic.accepted ? 'accepted' : 'rejected'} <span className="mono">{r.skeptic.confidence}</span></span>
            </span>
          ))}
        </div>
      ) : null}
      {run.escalation ? <div className="note warn small"><b><UserRoundCheck className="ic" /> Escalated to human officer.</b> {run.escalation}</div> : null}
    </>
  );
}

function Evidence({ pack, run }) {
  const wh = pack?.winning_hypothesis;
  const discs = run?.reconcile?.discrepancies;
  return (
    <>
      <h3>Supporting evidence</h3>
      {wh ? (
        <>
          <p style={{ margin: '0 0 6px' }}><b>{wh.title}</b> - {wh.cause}</p>
          <ul className="tight ev">{(wh.supporting_evidence || []).map((e, i) => <li key={i}>{e}</li>)}</ul>
          {wh.refuting_evidence?.length ? (<><div className="small muted">Refuting / open evidence</div><ul className="tight">{wh.refuting_evidence.map((e, i) => <li key={i}>{e}</li>)}</ul></>) : null}
          {wh.confirming_query ? (<details><summary>Confirming query (Zetaris SQL)</summary><pre>{wh.confirming_query}</pre></details>) : null}
        </>
      ) : discs?.length ? (
        <>
          <div className="small muted">From the Reconciler step of the stored trace (no full action pack stored for this pair).</div>
          <ul className="tight ev">{discs.map((d) => <li key={d.discrepancy_id}><b>{pretty(d.anomaly_type)}</b>: {d.description} <span className="muted">(impact {num(d.impact_units, 1)} units; sources: {(d.sources_in_conflict || []).join(', ')})</span></li>)}</ul>
        </>
      ) : (
        <p className="muted">No detailed evidence is stored for this pair. Older traces only record discrepancy counts. Run the analysis (backend) to produce a full evidence pack.</p>
      )}
    </>
  );
}

function ActionPlan({ pack, run, item, memo }) {
  return (
    <>
      <h3>Action plan</h3>
      {pack ? (
        <>
          <div className="small muted">Pack {pack.run_id}, from {pack._source}. Quantities are computed by the deterministic engine, not by an LLM.</div>
          <div className="tablewrap" style={{ marginTop: 8 }}>
            <table>
              <thead><tr><th>Action</th><th className="num">Units</th><th className="num">Est. cost (USD)</th><th>Source / supplier</th><th className="num">Feasibility</th></tr></thead>
              <tbody>
                {pack.recommendations.map((r) => (
                  <tr key={r.action_id}>
                    <td><b>{pretty(r.action_type)}</b><div className="small muted">{r.justification}</div>
                      {r.number_provenance ? <details><summary>number provenance</summary><pre>{JSON.stringify(r.number_provenance, null, 1)}</pre></details> : null}</td>
                    <td className="num">{num(r.recommended_units, 1)}</td>
                    <td className="num">{r.estimated_cost_usd === null || r.estimated_cost_usd === undefined ? '-' : num(r.estimated_cost_usd, 2)}</td>
                    <td>{r.source_facility_id || r.supplier_id || '-'}</td>
                    <td className="num">{num(r.feasibility_score, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {pack.action_plan_audit ? <div className="small" style={{ marginTop: 8 }}>Action-plan audit: <span className={`badge ${pack.action_plan_audit.passed ? 'b-ok' : 'b-crit'}`}>{pack.action_plan_audit.passed ? 'PASSED' : 'FAILED'}</span> ({pack.action_plan_audit.verified_recommendations_count} verified)</div> : null}
          {pack.escalated_to_human ? <div className="note warn small">Escalated to officer: {pack.escalation_reason}</div> : null}
        </>
      ) : (
        <div className="note small">
          No full action pack (with order quantities) is stored for this pair.
          {run?.action ? <> The stored trace records only that the Action Planner produced <b>{run.action.count}</b> recommendation(s) with top action <b>{pretty(run.action.top)}</b>{run.audit ? <>, audit {run.audit.passed ? 'passed' : 'failed'} ({run.audit.verified} verified)</> : null}.</> : null}
          {' '}Deterministic shortfall for this pair is <b>{num(item.shortfall_units, 1)} units</b> over a {num(item.gap_days, 2)}-day gap. Use "Run analysis" (needs the backend) to generate the full plan.
        </div>
      )}
      {memo ? <details style={{ marginTop: 8 }}><summary>Procurement memo ({memo.path}, {when(memo.mtime)})</summary><pre>{memo.text}</pre></details> : null}
    </>
  );
}

export default function Detail({ item, api, backend, snapshot, onRan, onBack }) {
  const [running, setRunning] = useState(false);
  const [sample, setSample] = useState(true);
  const [msg, setMsg] = useState(null);

  if (!item) {
    return (
      <section className="panel" style={{ gridColumn: '1 / -1' }} aria-label="Detail">
        <div className="empty" style={{ padding: '80px 16px' }}>
          <MousePointerClick className="ic" />
          <b style={{ color: 'var(--ink2)' }}>Select an alert</b>
          <span>See the Investigator vs Skeptic verdict, evidence, action plan and the step-by-step trace.</span>
        </div>
      </section>
    );
  }

  async function run() {
    setRunning(true);
    setMsg(null);
    try {
      const r = await fetch('/api/run', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ facility_id: item.facility_id, medicine_id: item.medicine_id, sample_mode: sample }) });
      const body = await r.json();
      if (!r.ok || !body.ok) setMsg({ err: true, text: body.error || `HTTP ${r.status}` });
      else {
        setMsg({ err: false, text: `Run ${body.run_id} finished in ${body.execution_time_seconds}s.` });
        onRan();
      }
    } catch (e) {
      setMsg({ err: true, text: String(e.message || e) });
    } finally {
      setRunning(false);
    }
  }

  const d = api.data;
  const run_ = d?.run;
  return (
    <div className="stack">
      <section className="panel" aria-label="Detail">
        <div className="dhead">
          <div>
            <button className="ghost backbtn" onClick={onBack}><ArrowLeft className="ic" />All alerts</button>
            <h2>{item.generic_name} <TierBadge tier={item.urgency_tier} /></h2>
            <div className="sub" style={{ marginTop: 3 }}>{item.facility_name} <span className="mono">{item.facility_id} / {item.medicine_id}</span></div>
          </div>
          <div className="row">
            {snapshot ? (
              <span className="badge b-info" title="This deployment ships stored runs only; the analysis backend is not part of it.">Stored demo runs (snapshot)</span>
            ) : backend?.reachable ? (
              <>
                <label className="small row" style={{ gap: 5 }}><input type="checkbox" checked={sample} onChange={(e) => setSample(e.target.checked)} /> sample mode (no LLM)</label>
                <button className="primary" onClick={run} disabled={running}><Play className="ic" />{running ? 'Running...' : 'Run analysis'}</button>
              </>
            ) : (
              <span className="badge b-mute" title={backend?.error || ''}>Backend offline: showing stored runs</span>
            )}
          </div>
        </div>
        <div className="sec">
          {msg ? <div className={`note small ${msg.err ? 'err' : ''}`} style={{ marginTop: 0 }}>{msg.text}</div> : null}
          <Metrics item={item} />
          <div className="small muted" style={{ marginTop: 8 }}>Deterministic engine over the local data files (simulated).</div>
        </div>
      </section>

      {api.status === 'loading' && !d ? <DetailSkeleton /> : null}
      {api.status === 'error' ? <ErrorBox title="Could not load run details" error={api.error} /> : null}
      {d?.ok ? (
        <>
          <section className="panel">
            <div className="sec">
              <h3>Investigator vs Skeptic</h3>
              {run_ ? (
                <>
                  <div className="small muted" style={{ marginBottom: 10 }}>
                    Showing the latest stored trace <span className="mono">{run_.file}</span> (run {run_.run_id}, {when(run_.started_at)}). {d.stored_runs > 1 ? `${num(d.stored_runs, 0)} traces are stored for this pair; older ones are not shown.` : ""} {d.trace_note && !/^Latest stored trace/.test(d.trace_note) ? d.trace_note : null}
                  </div>
                  <Verdicts run={run_} />
                </>
              ) : (
                <div className="note small" style={{ marginTop: 0 }}>No stored run for this pair. {snapshot ? 'The snapshot ships the latest stored run per investigated pair only.' : backend?.reachable ? 'Click "Run analysis" to create one.' : 'Start the backend (python run.py) to run an analysis.'}</div>
              )}
            </div>
          </section>
          <section className="panel"><div className="sec"><Evidence pack={d.pack} run={run_} /></div></section>
          <section className="panel"><div className="sec"><ActionPlan pack={d.pack} run={run_} item={item} memo={d.memo} /></div></section>
        </>
      ) : null}
    </div>
  );
}
