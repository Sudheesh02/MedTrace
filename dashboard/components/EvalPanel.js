'use client';
import { BookOpen, FlaskConical, ListChecks } from 'lucide-react';
import { ErrorBox, Loading, num } from './ui.js';

const uniq = (arr) => [...new Set(arr)];
const meanOf = (seeds, f) => {
  const v = seeds.map(f);
  return v.length && v.every((x) => typeof x === 'number') ? v.reduce((a, x) => a + x, 0) / v.length : null;
};

function HowToRead({ seeds }) {
  const days = uniq(seeds.map((s) => s.evaluation_period_days)).filter(Boolean);
  const planted = seeds.map((s) => s.ground_truth_anomalies).filter((x) => x !== null);

  return (
    <div className="action-card">
      <h3 className="cluster-sm">
        <BookOpen size={16} aria-hidden="true" className="icon-inline" />
        <span>How to read this evaluation</span>
      </h3>
      <ol className="stack-sm mt-sm pl-md text-sm">
        <li>
          <strong>What is measured:</strong> Each seed replays {days.length === 1 ? days[0] : days.join('/')} days of <em>simulated</em> stock movements with {planted.length ? `${Math.min(...planted)}` : '10'} planted anomalies (phantom drift, quarantine holds, supplier slips).
        </li>
        <li>
          <strong>Precision / Recall / F1:</strong> Precision measures what share of flagged alerts were real planted anomalies; Recall measures what share of planted anomalies were intercepted. F1 is their harmonic mean.
        </li>
        <li>
          <strong>The baselines:</strong> Traditional LMIS trusts ledger numbers and applies simple reorder thresholds. The performance gap represents the lift gained by multi-source data reconciliation.
        </li>
        <li>
          <strong>Scope & honesty:</strong> Evaluated on synthetic facility data with planted anomalies; not a claim of real-world epidemiological generalization.
        </li>
      </ol>
    </div>
  );
}

function Method({ seeds }) {
  return (
    <div className="action-card">
      <h3 className="cluster-sm">
        <FlaskConical size={16} aria-hidden="true" className="icon-inline" />
        <span>Simulation Replay Methodology</span>
      </h3>
      <div className="table-wrap mt-sm">
        <table>
          <thead>
            <tr>
              <th>Seed</th>
              <th>Days</th>
              <th>TP / FP / FN</th>
              <th>Actual Stockouts</th>
              <th>Txns Replayed</th>
              <th>Lead time MedTrace / Naive</th>
            </tr>
          </thead>
          <tbody>
            {seeds.map((s) => (
              <tr key={s.file}>
                <td><strong>{s.seed}</strong></td>
                <td className="num">{s.evaluation_period_days ?? '-'}</td>
                <td className="num">{s.true_positives ?? '-'} / {s.false_positives ?? '-'} / {s.false_negatives ?? '-'}</td>
                <td className="num">{s.total_actual_stockouts ?? '-'}</td>
                <td className="num">{num(s.total_transactions, 0)}</td>
                <td className="num">{s.lead_time ? `${num(s.lead_time.medtrace, 1)}d / ${num(s.lead_time.naive_lmis, 1)}d` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="muted text-xs mt-xs">
        Scope: {seeds[0]?.scope || 'Multi-facility deterministic audit replay'}. Alert threshold: {seeds[0]?.lead_time?.alert_threshold_days ?? 14} days of cover.
      </div>
    </div>
  );
}

function Curated({ c }) {
  if (!c) return null;
  return (
    <div className="action-card mt-md">
      <h3 className="cluster-sm">
        <ListChecks size={16} aria-hidden="true" className="icon-inline" />
        <span>Curated Clinical Scenarios Suite</span>
      </h3>
      <p className="muted text-sm mt-xs">
        {c.file}: {c.scenarios ?? '25'} hand-crafted scenarios testing edge cases (cold-chain, UOM mismatch, QA recall).
      </p>

      {c.declaration ? (
        <div className="case-file-summary-banner mt-sm">
          {c.declaration}
        </div>
      ) : null}

      {c.rows?.length ? (
        <div className="table-wrap mt-sm">
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Rules-only baseline</th>
                <th>MedTrace Multi-Agent Loop</th>
                <th>Advantage (Delta)</th>
              </tr>
            </thead>
            <tbody>
              {c.rows.map((r) => (
                <tr key={r.metric}>
                  <td><strong>{r.metric}</strong></td>
                  <td className="num">{r.baseline}</td>
                  <td className="num diff-highlight">{r.medtrace}</td>
                  <td className="num">{r.delta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

export default function EvalPanel({ api }) {
  const d = api.data;
  const seeds = d?.seeds || [];
  const mean = (k) => meanOf(seeds, (s) => s[k]);
  const f1 = mean('f1_pct');

  const bars = [
    { label: 'MedTrace Multi-Source Audit', val: f1, cls: 'ok', toneClass: 'text-ok' },
    { label: 'Heuristic Rule-Based', val: mean('heuristic_f1_pct'), cls: 'warn', toneClass: 'text-warn' },
    { label: 'Naive LMIS Baseline', val: mean('naive_lmis_f1_pct'), cls: 'crit', toneClass: 'text-crit' },
  ];

  return (
    <section className="case-file-pane" aria-label="Evaluation">
      <div className="case-file-header">
        <div className="case-file-header-top">
          <div>
            <h1>Algorithmic Evaluation & Benchmarks</h1>
            <p className="case-file-subtitle">
              Measured across 180-day simulated inventory replay (12 facilities × 12 essential medicines).
            </p>
          </div>
          <span className="badge badge-warn">Simulated Data</span>
        </div>
      </div>

      <div className="case-tab-content">
        {api.status === 'loading' && !d ? <Loading what="Reading evaluation reports" /> : null}
        {api.status === 'error' && !seeds.length ? (
          <ErrorBox title="No evaluation reports found" error={api.error}>
            Expected output/backtest_seed_*.json.
          </ErrorBox>
        ) : null}

        {seeds.length ? (
          <div className="stack-md">
            {/* Top comparison cards */}
            <div className="grid-2col">
              {/* Mean F1 Bars */}
              <div className="action-card">
                <h3>Mean F1 Score across {seeds.length} seeds</h3>
                <div className="stack-sm mt-md">
                  {bars.map(({ label, val, cls, toneClass }) => (
                    <div key={label}>
                      <div className="cluster-spread text-sm">
                        <span>{label}</span>
                        <strong className={`num ${toneClass}`}>{val === null ? '-' : `${num(val, 1)}%`}</strong>
                      </div>
                      <div className="progress-meter">
                        <div
                          className={`progress-meter-fill ${cls}`}
                          style={{ '--meter-w': `${Math.max(0, Math.min(100, val || 0))}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <p className="muted text-xs mt-sm">
                  Evaluated with identical 14.0-day replenishment alert threshold across all three models.
                </p>
              </div>

              {/* Per seed breakdown table */}
              <div className="action-card">
                <h3>Per-Seed Anomaly Detection</h3>
                <div className="table-wrap mt-sm">
                  <table>
                    <thead>
                      <tr>
                        <th>Seed</th>
                        <th>Planted</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>MedTrace F1</th>
                        <th>Baseline F1</th>
                      </tr>
                    </thead>
                    <tbody>
                      {seeds.map((s) => (
                        <tr key={s.file}>
                          <td><strong>{s.seed}</strong></td>
                          <td className="num">{s.ground_truth_anomalies}</td>
                          <td className="num">{num(s.precision_pct, 1)}%</td>
                          <td className="num">{num(s.recall_pct, 1)}%</td>
                          <td className="num diff-highlight">{num(s.f1_pct, 1)}%</td>
                          <td className="num muted">{num(s.naive_lmis_f1_pct, 1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="grid-2col">
              <HowToRead seeds={seeds} d={d} />
              <Method seeds={seeds} />
            </div>

            <Curated c={d.curated} />
          </div>
        ) : null}
      </div>
    </section>
  );
}
