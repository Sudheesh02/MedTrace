'use client';
import { ErrorBox, Loading, num } from './ui.js';

export default function EvalPanel({ api }) {
  const d = api.data;
  const seeds = d?.seeds || [];
  const mean = (k) => (seeds.length && seeds.every((s) => typeof s[k] === 'number') ? seeds.reduce((a, s) => a + s[k], 0) / seeds.length : null);
  return (
    <section className="panel" aria-label="Evaluation">
      <header>
        <h2>Evaluation <span className="badge sim">simulated data</span></h2>
      </header>
      {api.status === 'loading' && !d ? <Loading what="Reading reports" /> : null}
      {api.status === 'error' && !seeds.length ? <ErrorBox title="No evaluation files found" error={api.error}>Expected output/backtest_seed_*.json.</ErrorBox> : null}
      {seeds.length ? (
        <>
          <div className="note small">
            180-day replay on <b>simulated</b> facility networks, one run per seed. Anomaly scores measure recovery of <i>planted</i> anomalies (scope: {seeds[0].scope || 'n/a'}); they are not real-world accuracy.
          </div>
          <div className="tablewrap">
            <table>
              <thead><tr><th>Seed</th><th className="num">Planted</th><th className="num">Precision %</th><th className="num">Recall %</th><th className="num">F1 %</th><th className="num">Naive LMIS F1 %</th><th className="num">Heuristic F1 %</th></tr></thead>
              <tbody>
                {seeds.map((s) => (
                  <tr key={s.file} style={{ cursor: 'default' }}>
                    <td title={s.file}>{s.seed}</td><td className="num">{s.ground_truth_anomalies}</td>
                    <td className="num">{num(s.precision_pct)}</td><td className="num">{num(s.recall_pct)}</td><td className="num"><b>{num(s.f1_pct)}</b></td>
                    <td className="num">{num(s.naive_lmis_f1_pct)}</td><td className="num">{num(s.heuristic_f1_pct)}</td>
                  </tr>
                ))}
                <tr style={{ cursor: 'default' }}><td><i>mean</i></td><td /><td className="num">{num(mean('precision_pct'))}</td><td className="num">{num(mean('recall_pct'))}</td><td className="num"><b>{num(mean('f1_pct'))}</b></td><td className="num">{num(mean('naive_lmis_f1_pct'))}</td><td className="num">{num(mean('heuristic_f1_pct'))}</td></tr>
              </tbody>
            </table>
          </div>
          <div className="small muted" style={{ marginTop: 6 }}>Source: {seeds.map((s) => s.file).join(', ')}. The files do not label seeds as tuning vs held-out, so none is claimed here.</div>
        </>
      ) : null}
      {d?.curated ? (
        <div className="small muted" style={{ marginTop: 6 }}>
          Also present: {d.curated.file} ({d.curated.scenarios ?? '?'} hand-crafted scenarios, generated {d.curated.generated ?? '?'}) - a rule-coverage regression suite, not an accuracy metric.
        </div>
      ) : null}
    </section>
  );
}