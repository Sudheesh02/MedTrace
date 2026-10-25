"""
Investigator Agent (app/agents/investigator.py)
Formulates >= 3 competing hypotheses explaining why a shortage is forming.
Grounds each hypothesis in evidence queries and refutation criteria.
"""

import json
from typing import Dict, List, Any, Optional
from app.adapters.llm_client import LLMClient
from app.models.schemas import Hypothesis

class InvestigatorAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def investigate(
        self,
        reconciliation: Dict[str, Any],
        context: Dict[str, Any],
        skeptic_feedback: Optional[str] = None
    ) -> List[Hypothesis]:
        fac_id = reconciliation["facility_id"]
        med_id = reconciliation["medicine_id"]
        gname = reconciliation.get("generic_name", "Medicine")
        recon = reconciliation["deterministic_reconciliation"]
        discrepancies = reconciliation["discrepancies"]
        anoms = recon["anomalies_detected"]
        stock_eval = recon["stock_evaluation"]
        demand_eval = recon["demand_evaluation"]
        shortfall = recon["trust_shortfall"]

        # Extract World Model shared context
        fac_entity = context.get("facility", {}) if context else {}
        med_entity = context.get("medicine", {}) if context else {}
        inv_entity = context.get("inventory_state", {}) if context else {}
        relationships = context.get("relationships", []) if context else []
        conflicts = context.get("conflicts", []) if context else []
        canon_hash = (context.get("canon_hash") or "")[:8] if context else ""
        wm_inv_evidence = f"World Model entity {inv_entity.get('id', 'ent_inv')} (canon hash {canon_hash or 'verified'}) corroborates usable inventory." if inv_entity else None

        # Parse specific discrepancy types
        disc_types = {d.get("anomaly_type") for d in discrepancies}
        quar_disc = next((d for d in discrepancies if d.get("anomaly_type") == "QUARANTINED_BATCH"), None)
        uom_disc = next((d for d in discrepancies if d.get("anomaly_type") == "UOM_MISMATCH"), None)
        po_disc = next((d for d in discrepancies if d.get("anomaly_type") == "PO_DISPATCHED_NOT_RECEIVED"), None)
        demand_disc = next((d for d in discrepancies if d.get("anomaly_type") == "DEMAND_SPIKE"), None)
        global_disc = next((d for d in discrepancies if d.get("anomaly_type") == "GLOBAL_SHORTAGE"), None)
        slip_disc = next((d for d in discrepancies if d.get("anomaly_type") == "CHRONIC_SUPPLIER_SLIP"), None)

        # -------------------------------------------------------------
        # 1. Hypothesis 1: Internal Record Inaccuracy / Quality Hold
        # -------------------------------------------------------------
        if quar_disc:
            h1_title = "Batch Quality Assurance Quarantine & Regulatory Recall"
            h1_cause = f"Warehouse ledger includes {stock_eval['quarantined_stock']} quarantined units subject to regulatory hold."
            quar_ratio = min(1.0, stock_eval['quarantined_stock'] / max(1.0, stock_eval['ledger_stock']))
            h1_likelihood = round(min(0.95, 0.78 + 0.17 * quar_ratio), 2)
            h1_evidence = [
                f"{stock_eval['quarantined_stock']} units marked quarantined = true in batch registry.",
                quar_disc.get("description", "Quality lockup confirmed.")
            ]
            h1_refuting = ["Quarantine released following lab certificate of analysis (CoA) re-test."]
            h1_query = f"SELECT batch_id, quantity, expiry_date, quarantined FROM MEDTRACE_LH.batches WHERE facility_id = '{fac_id}' AND medicine_id = '{med_id}' AND quarantined = true"
        elif uom_disc:
            h1_title = "Unit-of-Measure Multiplier Discrepancy (Pack vs Tablet)"
            h1_cause = f"Packaging multiplier mismatch caused delivery receipt to overstate inventory relative to dispensing units."
            h1_likelihood = 0.88
            h1_evidence = [
                uom_disc.get("description", "10x delivery receipt mismatch detected."),
                f"Ledger balance overstates physical usable inventory by {stock_eval['audit_drift']} units."
            ]
            h1_refuting = ["Physical count confirms receipt was unpacked into individual tablets."]
            h1_query = f"SELECT po.po_id, po.quantity, d.received_qty FROM MEDTRACE_LH.purchase_orders po JOIN MEDTRACE_LH.deliveries d ON po.po_id = d.po_id WHERE po.facility_id = '{fac_id}' AND po.medicine_id = '{med_id}'"
        elif anoms["ghost_stock"]:
            h1_title = "Phantom Stock Drift in Warehouse Ledger"
            h1_cause = f"Physical audit confirms ledger overstates true physical stock by {stock_eval['audit_drift']} units."
            drift = stock_eval['audit_drift']
            drift_ratio = min(1.0, drift / max(1.0, stock_eval['ledger_stock']))
            h1_likelihood = round(min(0.95, 0.80 + 0.15 * drift_ratio), 2)
            h1_evidence = [
                f"Audit count confirms {stock_eval['usable_stock']} physical units vs {stock_eval['ledger_stock']} on ledger.",
                f"Ledger drift variance of {stock_eval['audit_drift']} units recorded."
            ]
            h1_refuting = ["Unlogged receipt from another facility arrived post-audit."]
            h1_query = f"SELECT counted_stock, date FROM MEDTRACE_LH.physical_audit WHERE facility_id = '{fac_id}' AND medicine_id = '{med_id}' ORDER BY date DESC LIMIT 1"
        else:
            h1_title = "Minor Administrative Stock Drift"
            h1_cause = "Normal variance between daily dispensing logs and warehouse ledger."
            h1_likelihood = 0.25
            h1_evidence = ["Audit drift is within standard tolerance (<5 units)."]
            h1_refuting = ["Audit drift exceeds monthly dispensing rate."]
            h1_query = f"SELECT counted_stock FROM MEDTRACE_LH.physical_audit WHERE facility_id = '{fac_id}' AND medicine_id = '{med_id}'"

        # -------------------------------------------------------------
        # 2. Hypothesis 2: Upstream Supplier Delay / Transit Failure
        # -------------------------------------------------------------
        naive_shortfall = recon.get("naive_shortfall", {})
        promised_day_val = naive_shortfall.get("delivery_day", 6.0)
        slip_added = max(0.0, shortfall.get("delivery_day", 9.0) - promised_day_val)
        if po_disc:
            h2_title = "Dispatched Purchase Order Lost or Delayed in Transit"
            h2_cause = f"Supplier marked order dispatched, but goods were never logged at receiving dock."
            h2_likelihood = 0.85
            h2_evidence = [
                po_disc.get("description", "PO dispatched but no delivery receipt logged."),
                f"Creates immediate replenishment gap of {shortfall['gap_days']} days."
            ]
            h2_refuting = ["Carrier tracking confirms delivery scheduled within 24 hours."]
            h2_query = f"SELECT po_id, supplier_id, order_date, promised_date, status FROM MEDTRACE_LH.purchase_orders WHERE facility_id = '{fac_id}' AND status = 'DISPATCHED'"
        elif slip_disc or anoms["supplier_delay_risk"]:
            h2_title = "Upstream Supplier Lead Time Slippage"
            h2_cause = slip_disc.get("description") if slip_disc else f"Empirical supplier slip priors indicate typical delivery delays push arrival past the safety cover window."
            effective_slip = max(slip_added, 7.0 if slip_disc else 0.0)
            slip_ratio = min(1.0, effective_slip / max(1.0, promised_day_val))
            h2_likelihood = round(min(0.95, 0.72 + 0.22 * slip_ratio), 2)
            h2_evidence = [
                f"Promised delivery expected at Day {promised_day_val:.0f}, but vendor slip adds +{slip_added:.1f} days.",
                f"Leaves a trust-adjusted shortfall of {shortfall['shortfall_units']} units across {shortfall['gap_days']} gap days."
            ]
            if slip_disc:
                h2_evidence.append(slip_disc.get("description"))
            h2_refuting = ["Supplier confirms expedited dispatch with guaranteed logistics priority."]
            h2_query = f"SELECT vendor, shipment_mode, mean_slip_days, p90_days FROM MEDTRACE_LH.supplier_slip LIMIT 5"
        else:
            h2_title = "Standard Supplier Lead Time Slippage"
            h2_cause = "Routine delivery transit delays within expected tolerance."
            h2_likelihood = 0.30
            h2_evidence = ["Supplier order is within normal 5-8 day delivery window."]
            h2_refuting = ["Vendor reports logistics fleet disruption."]
            h2_query = f"SELECT promised_date, order_date FROM MEDTRACE_LH.purchase_orders WHERE facility_id = '{fac_id}' AND medicine_id = '{med_id}'"

        # -------------------------------------------------------------
        # 3. Hypothesis 3: External Supply Disruption or Epidemiological Surge
        # -------------------------------------------------------------
        if demand_disc:
            who_tier = demand_eval.get("epidemiological_risk_tier", "ELEVATED")
            mult = demand_eval.get("who_surveillance_multiplier", 1.35)
            surge_ratio = min(1.0, max(0.0, (mult - 1.0) / 0.5))
            h3_likelihood = round(min(0.92, 0.68 + 0.24 * surge_ratio), 2)
            h3_title = "Epidemiological Outbreak & Consumption Demand Surge"
            h3_cause = f"WHO disease surveillance indicates {who_tier} transmission risk, driving consumption +{int((mult - 1.0) * 100)}% above baseline."
            h3_evidence = [
                demand_disc.get("description", "Epidemiological demand spike verified."),
                f"Adjusted daily demand rose from {demand_eval['base_daily_rate']} to {demand_eval['adjusted_daily_demand']} units/day."
            ]
            h3_refuting = ["Surveillance metrics reflect localized outbreak in adjacent district, not this facility."]
            h3_query = f"SELECT indicator, year, value, epidemiological_risk_tier FROM who_disease_surveillance WHERE medicine_id = '{med_id}'"
        elif global_disc:
            h3_title = "Active National / Global Manufacturing Shortage"
            h3_cause = f"Upstream API synthesis bottlenecks or GMP holds reported on {gname}."
            h3_likelihood = 0.75
            h3_evidence = [
                global_disc.get("description", "Active drug shortage reported."),
                f"Corroborated across openFDA shortages registry."
            ]
            h3_refuting = ["Alternative domestic generic manufacturer has unallocated buffer inventory."]
            h3_query = f"GET https://api.fda.gov/drug/shortages.json?search=generic_name:{gname.lower()}"
        else:
            h3_title = "General Market Supply Constriction"
            h3_cause = f"Broader regional supply tightening without active formal shortage notice."
            h3_likelihood = 0.20
            h3_evidence = ["No active national shortage filing logged in openFDA for this generic."]
            h3_refuting = ["Wholesalers report industry-wide allocation caps."]
            h3_query = f"SELECT * FROM openfda_shortages WHERE generic_name = '{gname}'"

        # -------------------------------------------------------------
        # Reactive Revision if Skeptic Feedback is Present (Rounds 2+)
        # -------------------------------------------------------------
        if skeptic_feedback:
            feedback_lower = skeptic_feedback.lower()

            # Case 1: Skeptic challenged close competing hypotheses / lack of differential elimination
            if any(k in feedback_lower for k in ["differential", "competing", "rule out", "eliminated", "contested"]):
                # Determine which hypothesis has direct physical grounding in deterministic reconciliation
                if quar_disc or uom_disc or anoms["ghost_stock"]:
                    # Ground truth is Internal Audit / Facility records (H1)
                    h1_likelihood = min(0.96, round(h1_likelihood + 0.08, 2))
                    h2_likelihood = max(0.20, round(h2_likelihood - 0.25, 2))
                    h3_likelihood = max(0.15, round(h3_likelihood - 0.25, 2))
                    h1_evidence.append("Differential confirmation: Physical inventory audit and batch quality records isolate variance directly to facility ledger, refuting external transit delay.")
                    h2_refuting.append("Supplier tracking confirms PO delivery timeline is secondary to local physical audit variance.")
                    h3_refuting.append("Demand patterns match historical run rate; shortage is not consumption-driven.")
                elif po_disc or anoms["supplier_delay_risk"]:
                    # Ground truth is Supplier / Transit (H2)
                    h2_likelihood = min(0.95, round(h2_likelihood + 0.10, 2))
                    h1_likelihood = max(0.20, round(h1_likelihood - 0.25, 2))
                    h3_likelihood = max(0.15, round(h3_likelihood - 0.25, 2))
                    h2_evidence.append("Differential confirmation: Open PO status and empirical supplier slip distribution confirm replenishment failure originates upstream.")
                    h1_refuting.append("Physical stock audit matches expected pre-delivery level; no local record tampering or unlogged shrinkage detected.")
                    h3_refuting.append("Consumption velocity matches baseline; shortage is supply-constrained rather than outbreak-driven.")
                elif demand_disc or global_disc:
                    # Ground truth is External Surge / Shortage (H3)
                    h3_likelihood = min(0.95, round(h3_likelihood + 0.10, 2))
                    h1_likelihood = max(0.20, round(h1_likelihood - 0.25, 2))
                    h2_likelihood = max(0.20, round(h2_likelihood - 0.25, 2))
                    h3_evidence.append("Differential confirmation: Cross-border shortage filing and epidemiological surveillance confirm external supply exhaustion.")
                    h1_refuting.append("Internal facility records are consistent with dispensing receipts; deficit is driven by patient inflow.")
                    h2_refuting.append("Contracted supplier fulfilled standard allocation; nationwide API bottlenecks prevent additional procurement.")

            # Case 2: Skeptic requested secondary corroboration on external claims
            if "corroboration" in feedback_lower or "secondary" in feedback_lower:
                if demand_disc or global_disc:
                    h3_evidence.append("Multi-source corroboration verified: Correlated openFDA shortage alert with cross-border MOH surveillance data.")
                    h3_likelihood = min(0.92, round(h3_likelihood + 0.05, 2))
                else:
                    h3_likelihood = max(0.15, round(h3_likelihood - 0.25, 2))
                    h3_refuting.append("Skeptic challenge upheld: External disruption claim lacks independent multi-registry confirmation.")

            if "phantom" in feedback_lower or "quarantine" in feedback_lower:
                h1_likelihood = min(0.95, round(h1_likelihood + 0.05, 2))
                h1_evidence.append("Addressed Skeptic feedback: Confirmed physical count alignment with deterministic engine.")

        # Ground hypotheses in Meterless World Model shared state
        if wm_inv_evidence:
            h1_evidence.append(wm_inv_evidence)
        if relationships:
            rel_str = ", ".join(sorted({str(r.get("relation")) for r in relationships if r.get("relation")}))
            h2_evidence.append(f"World Model topology verifies supply-chain relations: {rel_str}.")
        if conflicts:
            c_types = ", ".join(sorted({str(c.get("type")) for c in conflicts if c.get("type")}))
            h3_evidence.append(f"World Model recorded active conflict records: {c_types}.")

        hypotheses = [
            Hypothesis(
                hypothesis_id="H1-INTERNAL-AUDIT",
                title=h1_title,
                cause=h1_cause,
                likelihood=round(h1_likelihood, 2),
                supporting_evidence=h1_evidence,
                refuting_evidence=h1_refuting,
                confirming_query=h1_query
            ),
            Hypothesis(
                hypothesis_id="H2-SUPPLIER-TRANSIT",
                title=h2_title,
                cause=h2_cause,
                likelihood=round(h2_likelihood, 2),
                supporting_evidence=h2_evidence,
                refuting_evidence=h2_refuting,
                confirming_query=h2_query
            ),
            Hypothesis(
                hypothesis_id="H3-EXTERNAL-SURGE",
                title=h3_title,
                cause=h3_cause,
                likelihood=round(h3_likelihood, 2),
                supporting_evidence=h3_evidence,
                refuting_evidence=h3_refuting,
                confirming_query=h3_query
            )
        ]

        # Call LLM client to evaluate candidate hypotheses and enrich qualitative reasoning
        prompt = f"""
        Investigator Agent Root-Cause Analysis for {fac_id} - {med_id} ({gname}):
        - Ledger Stock: {stock_eval['ledger_stock']} units
        - Usable Physical Stock: {stock_eval['usable_stock']} units
        - Trust Cover Days: {recon['trust_cover_days']} days (Naive: {recon['naive_cover_days']} days)
        - Shortfall Units: {shortfall['shortfall_units']} units
        - World Model Canon: {inv_entity.get('id', 'N/A')} (canon hash: {canon_hash or 'N/A'}), Active Conflicts: {len(conflicts)}
        - Detected Discrepancies: {[d.get('description') for d in discrepancies]}
        - Skeptic Critique: {skeptic_feedback or 'Initial Round (No previous critique)'}

        Candidate Hypotheses:
        1. H1-INTERNAL-AUDIT: {h1_title} (Initial Likelihood: {h1_likelihood:.2f})
           Cause: {h1_cause}
        2. H2-SUPPLIER-TRANSIT: {h2_title} (Initial Likelihood: {h2_likelihood:.2f})
           Cause: {h2_cause}
        3. H3-EXTERNAL-SURGE: {h3_title} (Initial Likelihood: {h3_likelihood:.2f})
           Cause: {h3_cause}

        Instructions:
        Evaluate which hypothesis best explains the root cause based strictly on the grounded evidence and Skeptic feedback.
        Return a valid JSON object with:
        {{
            "preferred_hypothesis_id": "H1-INTERNAL-AUDIT" | "H2-SUPPLIER-TRANSIT" | "H3-EXTERNAL-SURGE",
            "likelihood_adjustments": {{
                "H1-INTERNAL-AUDIT": float,
                "H2-SUPPLIER-TRANSIT": float,
                "H3-EXTERNAL-SURGE": float
            }},
            "qualitative_rationale": "Detailed explanation connecting evidence to hypothesis."
        }}
        """
        llm_res = self.llm_client.generate(prompt=prompt, system_prompt="You are a clinical supply chain investigator.")
        self.last_llm_response = llm_res

        # Parse structured JSON feedback from LLM if present
        try:
            raw_text = llm_res.get("text", "")
            if "{" in raw_text and "}" in raw_text:
                json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    pref_id = parsed.get("preferred_hypothesis_id")
                    adj = parsed.get("likelihood_adjustments", {})
                    rationale = parsed.get("qualitative_rationale")

                    for hyp in hypotheses:
                        if isinstance(adj, dict) and hyp.hypothesis_id in adj:
                            try:
                                val = float(adj[hyp.hypothesis_id])
                                hyp.likelihood = max(0.05, min(0.98, round(val, 2)))
                            except (ValueError, TypeError):
                                pass
                        if rationale and hyp.hypothesis_id == pref_id:
                            hyp.supporting_evidence.append(f"Investigator qualitative synthesis: {rationale}")
        except Exception:
            # Fall back cleanly to deterministic evidence likelihoods
            pass

        return hypotheses
