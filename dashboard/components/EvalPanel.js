'use client';
import { ErrorBox, Loading, num } from './ui.js';

export default function EvalPanel({ api }) {
  const d = api.data;
  const seeds = d?.seeds || [];
  const mean = (k) => (seeds.length && seeds.every((s) => typeof s[k] === 'number') ? seeds.reduce((a, s) => a + s[k], 0) / seeds.length : null);
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
          <div className="two">
            <div>
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
            <div>
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
        ) : null}
        {d?.curated ? (
          <div className="small muted" style={{ marginTop: 12 }}>
            Also present: {d.curated.file} ({d.curated.scenarios ?? '?'} hand-crafted scenarios, generated {d.curated.generated ?? '?'}), a rule-coverage regression suite, not an accuracy metric.
          </div>
        ) : null}
      </div>
    </section>
  );
}