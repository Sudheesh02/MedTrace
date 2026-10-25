import fs from 'node:fs';
import { dir } from './paths.js';

/** Reads output/backtest_seed_*.json (180-day replay on SIMULATED data). Nothing is hardcoded here. */
export function getEval() {
  const out = dir('output');
  let names = [];
  try {
    names = fs.readdirSync(out).filter((n) => /^backtest_seed_\d+\.json$/.test(n)).sort();
  } catch {
    /* none */
  }
  const seeds = [];
  for (const n of names) {
    try {
      const j = JSON.parse(fs.readFileSync(`${out}/${n}`, 'utf8'));
      const a = j.metrics?.anomaly_detection || {};
      seeds.push({
        file: `output/${n}`,
        seed: j.seed,
        evaluation_period_days: j.evaluation_period_days,
        total_actual_stockouts: j.total_actual_stockouts,
        scope: a.evaluation_scope ?? null,
        ground_truth_anomalies: a.ground_truth_anomalies_count ?? null,
        precision_pct: a.precision_pct ?? null,
        recall_pct: a.recall_pct ?? null,
        f1_pct: a.f1_score_pct ?? null,
        naive_lmis_f1_pct: a.naive_lmis_f1 ?? null,
        heuristic_f1_pct: a.heuristic_f1 ?? null,
        true_positives: a.true_positives ?? null,
        false_positives: a.false_positives ?? null,
        false_negatives: a.false_negatives ?? null,
        stockout_recall_pct: j.metrics?.stockout_recall_pct ?? null,
        lead_time: j.metrics?.early_warning_lead_time_days ?? null,
      });
    } catch {
      /* skip malformed */
    }
  }
  const curatedPath = dir('output', 'curated_evaluation.md');
  let curated = null;
  try {
    const head = fs.readFileSync(curatedPath, 'utf8');
    const gen = /\*\*Generated\*\*:\s*(\S+)/.exec(head);
    const count = /\*\*Total Hand-Crafted Clinical Scenarios\*\*:\s*(\d+)/.exec(head);
    curated = { file: 'output/curated_evaluation.md', generated: gen?.[1] ?? null, scenarios: count ? Number(count[1]) : null };
  } catch {
    /* none */
  }
  return { ok: seeds.length > 0, seeds, curated };
}