'use client';
import { useState } from 'react';
import { ArrowLeft, CheckCircle, CircleCheck, CircleX, Gavel, Search, UserCheck, XCircle } from 'lucide-react';
import { CountUpNum, DetailSkeleton, ErrorBox, TierBadge, num, pretty } from './ui.js';
import Why from './Why.js';

export default function Detail({ item, api, backend, snapshot, onBack }) {
  const [activeTab, setActiveTab] = useState('summary');
  const run = api.data?.run;
  const pack = api.data?.pack;

  if (!item) {
    return (
      <div className="case-file-pane">
        <div className="empty-state">
          <p>Select a medicine from the queue to view its full audit and action plan.</p>
        </div>
      </div>
    );
  }

  if (api.status === 'loading' && !api.data) {
    return (
      <div className="case-file-pane">
        <DetailSkeleton />
      </div>
    );
  }

  if (api.status === 'error') {
    return (
      <div className="case-file-pane pad-lg">
        <ErrorBox title="Case details unavailable" error={api.error} />
      </div>
    );
  }

  // Plain language summary numbers & highlighted pills
  const isSecure = item.urgency_tier === 'SECURE';
  const coverDays = item.trust_cover_days !== null && item.trust_cover_days !== undefined ? num(item.trust_cover_days, 1) : '-';
  const shortfallUnits = Number(item.shortfall_units) > 0 ? num(item.shortfall_units, 0) : '0';

  // Reconciliation numbers comparison
  const r = run?.reconcile;
  const differNote = r && Math.abs((item.usable_stock || 0) - (r.usable_stock || 0)) > 1;

  // Hypotheses
  const hypotheses = run?.rounds?.flatMap((rd) => rd.hypotheses || []) || [];
  const leadingHyp = run?.leading_hypothesis || (hypotheses.length ? hypotheses[0] : null);
  const otherHypotheses = hypotheses.filter((h) => h.id !== leadingHyp?.id);

  // Skeptic verdict
  const finalSkeptic = run?.final_skeptic;
  const skepticAccepted = finalSkeptic?.accepted === true;
  const confPercent = finalSkeptic?.confidence !== null && finalSkeptic?.confidence !== undefined
    ? Math.round(Number(finalSkeptic.confidence) * 100)
    : null;

  // Recommendations
  const recs = pack?.recommendations || [];

  return (
    <article className="case-file-pane" aria-labelledby="case-title">
      {/* Case Header */}
      <div className="case-file-header">
        <div className="case-file-header-top">
          <div className="case-file-title-row">
            {onBack ? (
              <button className="btn btn-ghost" onClick={onBack} aria-label="Back to queue">
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>
            ) : null}
            <h1 id="case-title">{item.generic_name}</h1>
            <TierBadge tier={item.urgency_tier} />
            <span className="badge badge-mute mono">{item.medicine_id}</span>
          </div>
        </div>

        <div className="case-file-subtitle">
          <span>{item.facility_name || item.facility_id}</span>
          <span className="mono muted ml-sm">({item.facility_id})</span>
        </div>

        {/* Executive Summary Banner with Hover-Reactive Inline Stat Pills */}
        <div className="case-file-summary-banner">
          <p>
            <strong>{item.generic_name}</strong> at{' '}
            <span>{item.facility_name || item.facility_id}</span> has about{' '}
            <span className={`stat-pill-highlight ${isSecure ? 'ok' : 'crit'}`}>
              {coverDays} days
            </span>{' '}
            of verified stock
            {isSecure ? (
              '. No immediate clinical action is required.'
            ) : (
              <>
                {' '}left and is about{' '}
                <span className="stat-pill-highlight crit">
                  {shortfallUnits} units short
                </span>{' '}
                before the next scheduled delivery.
              </>
            )}
          </p>
        </div>
      </div>

      {/* Case Tabs */}
      <div className="case-tabs" role="tablist" aria-label="Case file sections">
        <button
          role="tab"
          className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
          aria-selected={activeTab === 'summary'}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
        <button
          role="tab"
          className={`tab-btn ${activeTab === 'evidence' ? 'active' : ''}`}
          aria-selected={activeTab === 'evidence'}
          onClick={() => setActiveTab('evidence')}
        >
          Evidence
        </button>
        <button
          role="tab"
          className={`tab-btn ${activeTab === 'actions' ? 'active' : ''}`}
          aria-selected={activeTab === 'actions'}
          onClick={() => setActiveTab('actions')}
        >
          Action plan ({recs.length})
        </button>
        <button
          role="tab"
          className={`tab-btn ${activeTab === 'trace' ? 'active' : ''}`}
          aria-selected={activeTab === 'trace'}
          onClick={() => setActiveTab('trace')}
        >
          How it was decided
        </button>
      </div>

      {/* Tab 1: Summary */}
      {activeTab === 'summary' ? (
        <div className="case-tab-content">
          {/* Key Numbers Grid with Count-Up Animations */}
          <div className="key-numbers-grid">
            <div className="key-stat-card">
              <span className="key-stat-label">Days of stock left (verified)</span>
              <span className="key-stat-val">
                <CountUpNum value={item.trust_cover_days} decimals={1} unit="d" />
              </span>
            </div>
            <div className="key-stat-card">
              <span className="key-stat-label">Days left according to ledger</span>
              <span className="key-stat-val">
                <CountUpNum value={item.naive_cover_days} decimals={1} unit="d" />
              </span>
            </div>
            <div className="key-stat-card">
              <span className="key-stat-label">Usable stock</span>
              <span className="key-stat-val">
                <CountUpNum value={item.usable_stock} decimals={0} />
              </span>
              <span className="stat-subtext">ledger {num(item.ledger_stock, 0)}</span>
            </div>
            <div className="key-stat-card">
              <span className="key-stat-label">Units on hold</span>
              <span className="key-stat-val">
                <CountUpNum value={item.quarantined_stock} decimals={0} />
              </span>
            </div>
            <div className="key-stat-card">
              <span className="key-stat-label">Count gap</span>
              <span className="key-stat-val">
                <CountUpNum value={item.audit_drift} decimals={0} />
              </span>
            </div>
            <div className={`key-stat-card ${Number(item.shortfall_units) > 0 ? 'highlight' : ''}`}>
              <span className="key-stat-label">Units short before next delivery</span>
              <span className="key-stat-val">
                <CountUpNum value={item.shortfall_units} decimals={0} />
              </span>
            </div>
            <div className="key-stat-card">
              <span className="key-stat-label">Chance of running out first</span>
              <span className="key-stat-val">
                {item.p_stockout_risk !== null && item.p_stockout_risk !== undefined ? (
                  <CountUpNum value={item.p_stockout_risk * 100} decimals={0} unit="%" />
                ) : (
                  '-'
                )}
              </span>
            </div>
          </div>

          {differNote ? (
            <p className="muted text-xs mb-md">
              <strong>Audit Reconciliation:</strong> The overview tiles reflect the district triage preview. Detailed reconciliation confirmed usable stock at {num(r.usable_stock, 0)} units and net shortfall at {num(r.shortfall, 0)} units. Recommendations below reflect this verified balance.
            </p>
          ) : null}

          {/* Verdict Blocks */}
          <div className="verdict-grid">
            {/* Investigator Card */}
            <div className="verdict-card investigator">
              <div className="verdict-card-header">
                <h4>
                  <Search size={15} aria-hidden="true" className="icon-inline" />
                  Investigator: proposed cause
                </h4>
                {run?.rounds ? (
                  <span className="badge badge-mute">
                    {run.rounds.length} round{run.rounds.length === 1 ? '' : 's'}
                  </span>
                ) : null}
              </div>

              {leadingHyp ? (
                <div>
                  <strong className="text-base">{leadingHyp.title}</strong>
                  {leadingHyp.likelihood !== null ? (
                    <div className="mt-sm">
                      <div className="cluster-spread text-xs muted">
                        <span>Confidence</span>
                        <span className="num font-semibold">{num(leadingHyp.likelihood * 100, 0)}%</span>
                      </div>
                      <div className="progress-meter">
                        <div
                          className="progress-meter-fill"
                          style={{ '--meter-w': `${Math.round((leadingHyp.likelihood || 0) * 100)}%` }}
                        />
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="muted">No causal hypotheses recorded for this case.</p>
              )}

              {otherHypotheses.length ? (
                <details className="mt-sm">
                  <summary>Other investigated factors ({otherHypotheses.length})</summary>
                  <ul className="stack-xs mt-sm list-none">
                    {otherHypotheses.map((h) => (
                      <li key={h.id} className="cluster-spread text-sm">
                        <span>{h.title}</span>
                        <span className="num muted">{h.likelihood !== null ? `${num(h.likelihood * 100, 0)}%` : '-'}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </div>

            {/* Skeptic Card */}
            <div className={`verdict-card skeptic ${skepticAccepted ? 'accepted' : 'rejected'}`}>
              <div className="verdict-card-header">
                <h4>
                  <Gavel size={15} aria-hidden="true" className="icon-inline" />
                  Skeptic: mathematical challenge
                </h4>
              </div>

              {finalSkeptic ? (
                <>
                  <div className={`verdict-big-badge ${skepticAccepted ? 'accepted' : 'rejected'}`}>
                    {skepticAccepted ? <CircleCheck size={20} /> : <CircleX size={20} />}
                    <span>{skepticAccepted ? 'ACCEPTED' : 'REJECTED'}</span>
                  </div>

                  <div>
                    <div className="cluster-spread text-xs muted">
                      <span>Verification confidence</span>
                      <span className="num font-semibold">{confPercent !== null ? `${confPercent}%` : '-'}</span>
                    </div>
                    {confPercent !== null ? (
                      <div className="progress-meter">
                        <div
                          className={`progress-meter-fill ${skepticAccepted ? 'ok' : 'crit'}`}
                          style={{ '--meter-w': `${confPercent}%` }}
                        />
                      </div>
                    ) : null}
                  </div>

                  <div className="cluster-sm">
                    <span className="muted text-xs">Number Auditor:</span>
                    <span className={`badge ${finalSkeptic.numbers_valid ? 'badge-ok' : 'badge-crit'}`}>
                      {finalSkeptic.numbers_valid ? 'Calculations verified' : 'Discrepancy flagged'}
                    </span>
                  </div>

                  <p className="text-sm">
                    {finalSkeptic.critique || 'No critique text recorded.'}
                  </p>
                </>
              ) : (
                <p className="muted">No Skeptic challenge recorded for this case.</p>
              )}
            </div>
          </div>

          {/* Escalation note */}
          {run?.escalation ? (
            <div className="note-error mt-md">
              <UserCheck size={16} aria-hidden="true" className="icon-inline" />
              <strong>Escalated to human officer:</strong> {run.escalation}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Tab 2: Evidence */}
      {activeTab === 'evidence' ? (
        <div className="case-tab-content">
          <div className="stack-md">
            <div>
              <h3>Primary Finding</h3>
              <p className="mt-xs text-base font-semibold">
                {pack?.winning_hypothesis?.title || leadingHyp?.title || 'No primary finding recorded.'}
              </p>
              <p className="mt-xs">
                {pack?.winning_hypothesis?.cause || leadingHyp?.cause || ''}
              </p>
            </div>

            {pack?.winning_hypothesis?.supporting_evidence?.length ? (
              <div>
                <h4>Supporting evidence points</h4>
                <ul className="stack-xs mt-xs pl-md">
                  {pack.winning_hypothesis.supporting_evidence.map((pt, i) => (
                    <li key={i}>{pt}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {pack?.winning_hypothesis?.refuting_evidence?.length ? (
              <div>
                <h4>Open or conflicting points</h4>
                <ul className="stack-xs mt-xs pl-md">
                  {pack.winning_hypothesis.refuting_evidence.map((pt, i) => (
                    <li key={i}>{pt}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {pack?.winning_hypothesis?.confirming_query ? (
              <details className="mt-sm">
                <summary>Verification query</summary>
                <pre>{pack.winning_hypothesis.confirming_query}</pre>
              </details>
            ) : null}

            {/* Discrepancies if present */}
            {r?.discrepancies?.length ? (
              <div className="mt-sm">
                <h4>Discrepancies identified</h4>
                <ul className="stack-xs mt-xs pl-md">
                  {r.discrepancies.map((d, i) => (
                    <li key={i}>
                      <strong>{pretty(d.anomaly_type)}:</strong> {d.description}
                      {d.impact_units ? ` (${num(d.impact_units, 0)} units impact)` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Tab 3: Action Plan */}
      {activeTab === 'actions' ? (
        <div className="case-tab-content">
          {pack?.action_plan_audit ? (
            <div className="cluster-sm mb-md">
              <span className={`badge ${pack.action_plan_audit.passed ? 'badge-ok' : 'badge-crit'}`}>
                {pack.action_plan_audit.passed ? <CheckCircle size={13} /> : <XCircle size={13} />}
                <span>
                  {pack.action_plan_audit.passed
                    ? `Audit passed: ${pack.action_plan_audit.verified_recommendations_count || recs.length} actions verified against supply constraints`
                    : 'Audit flagged potential inconsistencies'}
                </span>
              </span>
            </div>
          ) : null}

          {recs.length === 0 ? (
            <div className="empty-state">
              <p>No action recommendations recorded for this item.</p>
            </div>
          ) : (
            <div className="actions-list">
              {recs.map((rec, index) => {
                const actType = rec.action_type?.value || String(rec.action_type || '');
                const cost = rec.estimated_cost_usd !== null && rec.estimated_cost_usd !== undefined
                  ? `$${num(rec.estimated_cost_usd, 2)} USD`
                  : null;
                const feasPercent = Math.round((rec.feasibility_score || 0) * 100);

                return (
                  <div key={rec.action_id || index} className="action-card">
                    <div className="action-card-header">
                      <div className="cluster-sm">
                        <span className="badge badge-info mr-sm">Option {index + 1}</span>
                        <strong className="text-base">{pretty(actType)}</strong>
                      </div>
                      <span className="badge badge-mute">Feasibility: {feasPercent}%</span>
                    </div>

                    <div className="action-card-stats">
                      <div>
                        <div className="key-stat-label">Recommended quantity</div>
                        <strong className="num text-base">{num(rec.recommended_units, 0)} units</strong>
                      </div>
                      {cost ? (
                        <div>
                          <div className="key-stat-label">Estimated cost</div>
                          <strong className="num text-base">{cost}</strong>
                        </div>
                      ) : null}
                      {rec.source_facility_id ? (
                        <div>
                          <div className="key-stat-label">Source facility</div>
                          <strong className="text-sm">{rec.source_facility_id}</strong>
                        </div>
                      ) : null}
                      {rec.supplier_id ? (
                        <div>
                          <div className="key-stat-label">Contracted supplier</div>
                          <strong className="text-sm">{rec.supplier_id}</strong>
                        </div>
                      ) : null}
                    </div>

                    <p>{rec.justification}</p>

                    {rec.number_provenance && Object.keys(rec.number_provenance).length > 0 ? (
                      <details>
                        <summary>Calculation basis (provenance)</summary>
                        <div className="mt-sm">
                          {typeof rec.number_provenance === 'object' ? (
                            <table className="w-full">
                              <tbody>
                                {Object.entries(rec.number_provenance).map(([k, v]) => (
                                  <tr key={k}>
                                    <td className="muted">{pretty(k)}</td>
                                    <td className="num font-semibold">{num(v, 2)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : (
                            <pre>{JSON.stringify(rec.number_provenance, null, 2)}</pre>
                          )}
                        </div>
                      </details>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : null}

      {/* Tab 4: How it was decided */}
      {activeTab === 'trace' ? (
        <div className="case-tab-content">
          <Why item={item} api={api} backend={backend} />
        </div>
      ) : null}
    </article>
  );
}
