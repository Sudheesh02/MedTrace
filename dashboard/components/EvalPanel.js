'use client';
import { BookOpen, FlaskConical, ListChecks } from 'lucide-react';
import { ErrorBox, Loading, num } from './ui.js';

const uniq = (arr) => [...new Set(arr)];
const meanOf = (seeds, f) => {
  const v = seeds.map(f);
  return v.length && v.every((x) => typeof x === 'number') ? v.reduce((a, x) => a + x, 0) / v.length : null;
};

function HowToRead({ seeds, d }) {
  const days = uniq(seeds.map((s) => s.evaluation_period_days)).filter(Boolean);
  const planted = seeds.map((s) => s.ground_truth_anomalies).filter((x) => x !== null);
  const leadAdv = seeds.map((s) => s.lead_time?.lead_time_advantage_days);
  const noLeadEdge = leadAdv.length && leadAdv.every((x) => x === 0);
  const sr = seeds.map((s) => s.stockout_recall_pct).filter(Boolean);
  const sameRecall = sr.length && sr.every((x) => x.medtrace === x.naive_lmis && x.medtrace === x.heuristic_rule_based);
  return (
    <div className="eval-card">
      <h3><BookOpen className="ic" />How to read this</h3>
      <ol className="steps">
        <li><b>What is measured.</b> Each seed replays {days.length === 1 ? days[0] : days.join('/')} days of <i>simulated</i> stock movements with {planted.length ? `${Math.min(...planted)}${Math.min(...planted) === Math.max(...planted) ? '' : `-${Math.max(...planted)}`} ` : ''}planted anomalies (ghost stock, quarantine, delayed deliveries, ...). The score is how many planted anomalies were flagged.</li>
        <li><b>Precision / recall / F1.</b> Precision: of the alerts raised, how many were planted anomalies. Recall: of the planted anomalies, how many were raised. F1 is their harmonic mean, so one weak side drags it down.</li>
        <li><b>The two baselines.</b> "Naive LMIS" trusts the ledger and uses a reorder point. "Heuristic" adds simple rules. Both are scored on the same planted set, so the gap between the bars is the lift from reconciling several sources.</li>
        {noLeadEdge ? <li><b>What it does <u>not</u> show.</b> Stockout recall{sameRecall ? ' (100% for all three methods)' : ''} and early-warning lead time are identical for MedTrace and both baselines in every seed (lead-time advantage 0 days). The measurable edge here is anomaly detection, not earlier stockout warning.</li> : null}
        <li><b>Not real-world accuracy.</b> One run per seed on synthetic data; no confidence intervals. {d.curated?.held_out_claim ? `The curated report calls seeds ${d.curated.held_out_claim} held-out, but the seed files carry no tuning/held-out label.` : 'The files do not label seeds as tuning vs held-out.'}</li>
      </ol>
    </div>
  );
}

function Method({ seeds }) {
  return (
    <div className="eval-card">
      <h3><FlaskConical className="ic" />Method notes <span className="muted small">(read from each seed file)</span></h3>
      <div className="tablewrap">
        <table>
          <thead><tr><th>Seed</th><th className="num">Days</th><th className="num">TP / FP / FN</th><th className="num">Stockouts</th><th className="num">Txns replayed</th><th className="num">Lead time MedTrace / naive (d)</th><th className="num">Detect delay (median d)</th></tr></thead>
          <tbody>
            {seeds.map((s) => (
              <tr key={s.file}>
                <td>{s.seed}</td>
                <td className="num">{s.evaluation_period_days ?? '-'}</td>
                <td className="num">{s.true_positives ?? '-'} / {s.false_positives ?? '-'} / {s.false_negatives ?? '-'}</td>
                <td className="num">{s.total_actual_stockouts ?? '-'}</td>
                <td className="num">{num(s.total_transactions, 0)}{s.replay_seconds ? <span className="muted"> in {num(s.replay_seconds, 1)}s</span> : null}</td>
                <td className="num">{s.lead_time ? `${num(s.lead_time.medtrace, 1)} / ${num(s.lead_time.naive_lmis, 1)}` : '-'}</td>
                <td className="num">{s.timing ? `${num(s.timing.median_detection_delay_days, 1)} (${s.timing.timed_true_positives} timed)` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="small muted" style={{ marginTop: 8 }}>
        Scope: <span className="mono">{seeds[0].scope || 'n/a'}</span>. Lead-time alert threshold: {seeds[0].lead_time?.alert_threshold_days ?? '-'} days of cover.
      </div>
    </div>
  );
}

function Curated({ c }) {
  if (!c) return null;
  return (
    <div className="eval-card">
      <h3><ListChecks className="ic" />Curated rule-coverage suite <span className="badge b-mute">regression test, not accuracy</span></h3>
      <div className="small muted" style={{ marginBottom: 8 }}>{c.file}: {c.scenarios ?? '?'} hand-crafted scenarios, generated {c.generated ?? '?'}.</div>
      {c.declaration ? <div className="note warn small" style={{ marginTop: 0 }}>{c.declaration}</div> : null}
      {c.rows?.length ? (
        <div className="tablewrap">
          <table>
            <thead><tr><th>Metric (as reported in the file)</th><th>Rules-only baseline</th><th>MedTrace loop</th><th>Delta</th></tr></thead>
            <tbody>{c.rows.map((r) => <tr key={r.metric}><td>{r.metric}</td><td>{r.baseline}</td><td><b>{r.medtrace}</b></td><td className={r.delta.startsWith('-') ? 'neg' : ''}>{r.delta}</td></tr>)}</tbody>
          </table>
        </div>
      ) : null}
      {c.rows?.some((r) => r.delta.startsWith('-')) ? <div className="small muted" style={{ marginTop: 6 }}>A negative delta is shown on purpose: on clean cases MedTrace abstains less often than the plain baseline.</div> : null}
    </div>
  );
}

export default function EvalPanel({ api }) {
  const d = api.data;
  const seeds = d?.seeds || [];
  const mean = (k) => meanOf(seeds, (s) => s[k]);
  const f1 = mean('f1_pct');
  const bars = [['MedTrace F1', f1, 'ok'], ['Heuristic F1', mean('heuristic_f1_pct'), 'warn'], ['Naive LMIS F1', mean('naive_lmis_f1_pct'), 'crit']];
  return (
    <section className="panel" aria-label="Evaluation">
      <div className="panel-h">
        <div>
          <h2>Evaluation <span className="badge sim">simulated data</span></h2>
          <div className="sub">Recovery of planted anomalies in a 180-day replay, one run per seed. Not real-world accuracy.</div>
        </div>
      </div>
      <div className="panel-b">
        {api.status === 'loading' && !d ? <Loading what="Reading reports" /> : null}
        {api.status === 'error' && !seeds.length ? <ErrorBox title="No evaluation files found" error={api.error}>Expected output/backtest_seed_*.json.</ErrorBox> : null}
        {seeds.length ? (
          <>
            <div className="two">
              <div className="eval-card">
                <h3>Mean F1 across {seeds.length} seed{seeds.length === 1 ? '' : 's'}</h3>
                <div className="cmp">
                  {bars.map(([label, v, tone]) => (
                    <div key={label} className="cmp-r">
                      <span>{label}</span>
                      <div className={`meter ${tone}`}><i style={{ width: `${Math.max(0, Math.min(100, v || 0))}%` }} /></div>
                      <b>{v === null ? '-' : `${num(v)}%`}</b>
                    </div>
                  ))}
                </div>
                <div className="note small warn" style={{ marginTop: 14 }}>
                  Scope: {seeds[0].scope || 'n/a'}. The files do not label seeds as tuning vs held-out, so none is claimed here.
                </div>
              </div>
              <div className="eval-card">
                <h3>Per seed</h3>
                <div className="tablewrap">
                  <table>
                    <thead><tr><th>Seed</th><th className="num">Planted</th><th className="num">Prec %</th><th className="num">Recall %</th><th className="num">F1 %</th><th className="num">Naive F1 %</th><th className="num">Heur. F1 %</th></tr></thead>
                    <tbody>
                      {seeds.map((s) => (
                        <tr key={s.file}>
                          <td title={s.file}>{s.seed}</td><td className="num">{s.ground_truth_anomalies}</td>
                          <td className="num">{num(s.precision_pct)}</td><td className="num">{num(s.recall_pct)}</td><td className="num"><b>{num(s.f1_pct)}</b></td>
                          <td className="num">{num(s.naive_lmis_f1_pct)}</td><td className="num">{num(s.heuristic_f1_pct)}</td>
                        </tr>
                      ))}
                      <tr><td><i>mean</i></td><td /><td className="num">{num(mean('precision_pct'))}</td><td className="num">{num(mean('recall_pct'))}</td><td className="num"><b>{num(mean('f1_pct'))}</b></td><td className="num">{num(mean('naive_lmis_f1_pct'))}</td><td className="num">{num(mean('heuristic_f1_pct'))}</td></tr>
                    </tbody>
                  </table>
                </div>
                <div className="small muted" style={{ marginTop: 6 }}>Source: {seeds.map((s) => s.file).join(', ')}.</div>
              </div>
            </div>
            <div className="two eq" style={{ marginTop: 14 }}>
              <HowToRead seeds={seeds} d={d} />
              <div className="stack">
                <Method seeds={seeds} />
              </div>
            </div>
            <div style={{ marginTop: 14 }}><Curated c={d.curated} /></div>
          </>
        ) : null}
      </div>
    </section>
  );
}