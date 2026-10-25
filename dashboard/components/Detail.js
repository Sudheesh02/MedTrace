'use client';
import { useState } from 'react';
import { ErrorBox, Loading, TierBadge, num, pretty, when } from './ui.js';

function Metrics({ item }) {
  const cells = [
    ['Trust-adjusted cover (d)', num(item.trust_cover_days, 2)],
    ['Naive LMIS cover (d)', num(item.naive_cover_days, 2)],
    ['Usable / ledger stock', `${num(item.usable_stock, 0)} / ${num(item.ledger_stock, 0)}`],
    ['Quarantined units', num(item.quarantined_stock, 0)],
    ['Audit drift (units)', num(item.audit_drift, 0)],
    ['Shortfall (units)', num(item.shortfall_units, 1)],
    ['Stockout risk', item.p_stockout_risk === null || item.p_stockout_risk === undefined ? '-' : `${num(item.p_stockout_risk * 100, 0)}%`],
  ];
  return <div className="kv">{cells.map(([l, v]) => <div key={l}><b>{v}</b><span>{l}</span></div>)}</div>;
}

function Verdicts({ run }) {
  const lastHyp = [...run.rounds].reverse().find((r) => r.hypotheses.length);
  const fs = run.final_skeptic;
  return (
    <>
      <div className="split">
        <div className="card">
          <h4>Investigator <span className="badge b-info">{run.rounds.length} round{run.rounds.length === 1 ? '' : 's'}</span></h4>
          {run.leading_hypothesis ? (
            <p style={{ margin: '0 0 8px' }}>Concluded: <b>{run.leading_hypothesis.title}</b>{run.leading_hypothesis.likelihood !== null ? <> (likelihood {num(run.leading_hypothesis.likelihood * 100, 0)}%)</> : null}</p>
          ) : <p className="muted">No hypotheses recorded in this trace.</p>}
          {lastHyp ? lastHyp.hypotheses.map((h) => (
            <div key={h.id}>
              <div className="small">{h.title} <span className="muted">- {h.likelihood === null ? '-' : `${num(h.likelihood * 100, 0)}%`}</span></div>
              <div className="bar"><i style={{ width: `${Math.round((h.likelihood || 0) * 100)}%` }} /></div>
            </div>
          )) : null}
        </div>
        <div className="card">
          <h4>Skeptic + Number Auditor {fs ? <span className={`badge ${fs.accepted ? 'b-ok' : 'b-crit'}`}>{fs.accepted ? 'ACCEPTED' : 'REJECTED'}</span> : null}</h4>
          {fs ? (
            <>
              <p style={{ margin: '0 0 6px' }} className="small">
                Confidence {fs.confidence ?? '-'} | Number Auditor: <span className={`badge ${fs.numbers_valid ? 'b-ok' : 'b-crit'}`}>{fs.numbers_valid === null ? 'n/a' : fs.numbers_valid ? 'numbers valid' : 'numbers INVALID'}</span>
              </p>
              <p style={{ margin: '0 0 6px' }} className="small">{fs.critique || <span className="muted">No critique text.</span>}</p>
              {fs.flagged?.length ? <ul className="tight small">{fs.flagged.map((f, i) => <li key={i}>{f}</li>)}</ul> : null}
            </>
          ) : <p className="muted">No Skeptic evaluation recorded in this trace.</p>}
        </div>
      </div>
      <div className="small" style={{ marginTop: 8 }}>
        <b>Debate:</b>{' '}
        {run.rounds.filter((r) => r.skeptic).map((r) => (
          <span key={r.round} className={`badge ${r.skeptic.accepted ? 'b-ok' : 'b-crit'}`} style={{ marginRight: 6 }}>R{r.round}: {r.skeptic.accepted ? 'accepted' : 'rejected'} ({r.skeptic.confidence})</span>
        ))}
      </div>
      {run.escalation ? <div className="note warn small"><b>Escalated to human officer.</b> {run.escalation}</div> : null}
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
          <ul className="tight">{(wh.supporting_evidence || []).map((e, i) => <li key={i}>{e}</li>)}</ul>
          {wh.refuting_evidence?.length ? (<><div className="small muted">Refuting / open evidence</div><ul className="tight">{wh.refuting_evidence.map((e, i) => <li key={i}>{e}</li>)}</ul></>) : null}
          {wh.confirming_query ? (<details><summary>Confirming query (Zetaris SQL)</summary><pre>{wh.confirming_query}</pre></details>) : null}
        </>
      ) : discs?.length ? (
        <>
          <div className="small muted">From the Reconciler step of the stored trace (no full action pack stored for this pair).</div>
          <ul className="tight">{discs.map((d) => <li key={d.discrepancy_id}><b>{pretty(d.anomaly_type)}</b>: {d.description} <span className="muted">(impact {num(d.impact_units, 1)} units; sources: {(d.sources_in_conflict || []).join(', ')})</span></li>)}</ul>
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
          <div className="tablewrap" style={{ marginTop: 6 }}>
            <table>
              <thead><tr><th>Action</th><th className="num">Units</th><th className="num">Est. cost (USD)</th><th>Source / supplier</th><th className="num">Feasibility</th></tr></thead>
              <tbody>
                {pack.recommendations.map((r) => (
                  <tr key={r.action_id} style={{ cursor: 'default' }}>
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
          {pack.action_plan_audit ? <div className="small" style={{ marginTop: 6 }}>Action-plan audit: <span className={`badge ${pack.action_plan_audit.passed ? 'b-ok' : 'b-crit'}`}>{pack.action_plan_audit.passed ? 'PASSED' : 'FAILED'}</span> ({pack.action_plan_audit.verified_recommendations_count} verified)</div> : null}
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

export default function Detail({ item, api, backend, onRan }) {
  const [running, setRunning] = useState(false);
  const [sample, setSample] = useState(true);
  const [msg, setMsg] = useState(null);

  if (!item) return <section className="panel"><div className="empty">Select an alert above to see the Investigator vs Skeptic verdict, evidence and action plan.</div></section>;

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
    <section className="panel" aria-label="Detail">
      <header>
        <div>
          <h2>{item.facility_name} - {item.generic_name} <TierBadge tier={item.urgency_tier} /></h2>
          <div className="sub mono">{item.facility_id} / {item.medicine_id}</div>
        </div>
        <div className="chips">
          {backend?.reachable ? (
            <>
              <label className="small"><input type="checkbox" checked={sample} onChange={(e) => setSample(e.target.checked)} /> sample mode (offline, no LLM calls)</label>
              <button className="primary" onClick={run} disabled={running}>{running ? 'Running...' : 'Run analysis'}</button>
            </>
          ) : (
            <span className="badge b-mute" title={backend?.error || ''}>Backend offline - showing stored runs only</span>
          )}
        </div>
      </header>
      {msg ? <div className={`note small ${msg.err ? 'err' : ''}`}>{msg.text}</div> : null}
      <Metrics item={item} />
      <div className="small muted">Figures above: deterministic engine over the local data files (simulated).</div>

      {api.status === 'loading' && !d ? <Loading what="Loading run" /> : null}
      {api.status === 'error' ? <ErrorBox title="Could not load run details" error={api.error} /> : null}
      {d?.ok ? (
        <>
          {run_ ? (
            <>
              <div className="small muted" style={{ margin: '6px 0' }}>
                Trace <span className="mono">{run_.file}</span> (run {run_.run_id}, {when(run_.started_at)}; {d.stored_runs} stored run(s) for this pair). {d.trace_note}
              </div>
              <h3>Investigator vs Skeptic</h3>
              <Verdicts run={run_} />
            </>
          ) : (
            <div className="note small">No stored run for this pair. {backend?.reachable ? 'Click "Run analysis" to create one.' : 'Start the backend (python run.py) to run an analysis.'}</div>
          )}
          <Evidence pack={d.pack} run={run_} />
          <ActionPlan pack={d.pack} run={run_} item={item} memo={d.memo} />
        </>
      ) : null}
    </section>
  );
}