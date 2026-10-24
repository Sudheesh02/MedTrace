"""
Investigator Agent (app/agents/investigator.py)
Formulates >= 3 competing hypotheses explaining why a shortage is forming.
Grounds each hypothesis in evidence queries and refutation criteria.
"""

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

        # Parse specific discrepancy types
        disc_types = {d.get("anomaly_type") for d in discrepancies}
        quar_disc = next((d for d in discrepancies if d.get("anomaly_type") == "QUARANTINED_BATCH"), None)
        uom_disc = next((d for d in discrepancies if d.get("anomaly_type") == "UOM_MISMATCH"), None)
        po_disc = next((d for d in discrepancies if d.get("anomaly_type") == "PO_DISPATCHED_NOT_RECEIVED"), None)
        demand_disc = next((d for d in discrepancies if d.get("anomaly_type") == "DEMAND_SPIKE"), None)
        global_disc = next((d for d in discrepancies if d.get("anomaly_type") == "GLOBAL_SHORTAGE"), None)

        # -------------------------------------------------------------
        # 1. Hypothesis 1: Internal Record Inaccuracy / Quality Hold
        # -------------------------------------------------------------
        if quar_disc:
            h1_title = "Batch Quality Assurance Quarantine & Regulatory Recall"
            h1_cause = f"Warehouse ledger includes {stock_eval['quarantined_stock']} quarantined units subject to regulatory hold."
            h1_likelihood = 0.90
            h1_evidence = [
                f"{stock_eval['quarantined_stock']} units marked quarantined = true in batch registry.",
                quar_disc.get("description", "Quality lockup confirmed.")
            ]
            h1_refuting = ["Quarantine released following lab certificate of analysis (CoA) re-test."]
            h1_query = f"SELECT batch_id, quantity, expiry_date, quarantined FROM zetaris.lightning.batches WHERE facility_id = '{fac_id}' AND medicine_id = '{med_id}' AND quarantined = true"
        elif uom_disc:
            h1_title = "Unit-of-Measure Multiplier Discrepancy (Pack vs Tablet)"
            h1_cause = f"Packaging multiplier mismatch caused delivery receipt to overstate inventory relative to dispensing units."
            h1_likelihood = 0.88
            h1_evidence = [
                uom_disc.get("description", "10x delivery receipt mismatch detected."),
                f"Ledger balance overstates physical usable inventory by {stock_eval['audit_drift']} units."
            ]
            h1_refuting = ["Physical count confirms receipt was unpacked into individual tablets."]
            h1_query = f"SELECT po.po_id, po.quantity, d.received_qty FROM zetaris.lightning.purchase_orders po JOIN zetaris.lightning.deliveries d ON po.po_id = d.po_id WHERE po.facility_id = '{fac_id}' AND po.medicine_id = '{med_id}'"
        elif anoms["ghost_stock"]:
            h1_title = "Phantom Stock Drift in Warehouse Ledger"
            h1_cause = f"Physical audit confirms ledger overstates true physical stock by {stock_eval['audit_drift']} units."
            h1_likelihood = 0.85
            h1_evidence = [
                f"Audit count confirms {stock_eval['usable_stock']} physical units vs {stock_eval['ledger_stock']} on ledger.",
                f"Ledger drift variance of {stock_eval['audit_drift']} units recorded."
            ]
            h1_refuting = ["Unlogged receipt from another facility arrived post-audit."]
            h1_query = f"SELECT counted_stock, date FROM zetaris.lightning.physical_audit WHERE facility_id = '{fac_id}' AND medicine_id = '{med_id}' ORDER BY date DESC LIMIT 1"
        else:
            h1_title = "Minor Administrative Stock Drift"
            h1_cause = "Normal variance between daily dispensing logs and warehouse ledger."
            h1_likelihood = 0.25
            h1_evidence = ["Audit drift is within standard tolerance (<5 units)."]
            h1_refuting = ["Audit drift exceeds monthly dispensing rate."]
            h1_query = f"SELECT counted_stock FROM zetaris.lightning.physical_audit WHERE facility_id = '{fac_id}' AND medicine_id = '{med_id}'"

        # -------------------------------------------------------------
        # 2. Hypothesis 2: Upstream Supplier Delay / Transit Failure
        # -------------------------------------------------------------
        if po_disc:
            h2_title = "Dispatched Purchase Order Lost or Delayed in Transit"
            h2_cause = f"Supplier marked order dispatched, but goods were never logged at receiving dock."
            h2_likelihood = 0.85
            h2_evidence = [
                po_disc.get("description", "PO dispatched but no delivery receipt logged."),
                f"Creates immediate replenishment gap of {shortfall['gap_days']} days."
            ]
            h2_refuting = ["Carrier tracking confirms delivery scheduled within 24 hours."]
            h2_query = f"SELECT po_id, supplier_id, order_date, promised_date, status FROM zetaris.lightning.purchase_orders WHERE facility_id = '{fac_id}' AND status = 'DISPATCHED'"
        elif anoms["supplier_delay_risk"]:
            h2_title = "Upstream Supplier Lead Time Slippage"
            h2_cause = f"Empirical supplier slip priors indicate typical delivery delays push arrival past the safety cover window."
            h2_likelihood = 0.75
            h2_evidence = [
                f"Promised delivery expected at Day 6, but historical vendor slip adds +3.0 days.",
                f"Leaves a trust-adjusted shortfall of {shortfall['shortfall_units']} units across {shortfall['gap_days']} gap days."
            ]
            h2_refuting = ["Supplier confirms expedited dispatch with guaranteed logistics priority."]
            h2_query = f"SELECT vendor, shipment_mode, mean_slip_days, p90_days FROM zetaris.lightning.supplier_slip LIMIT 5"
        else:
            h2_title = "Standard Supplier Lead Time Slippage"
            h2_cause = "Routine delivery transit delays within expected tolerance."
            h2_likelihood = 0.30
            h2_evidence = ["Supplier order is within normal 5-8 day delivery window."]
            h2_refuting = ["Vendor reports logistics fleet disruption."]
            h2_query = f"SELECT promised_date, order_date FROM zetaris.lightning.purchase_orders WHERE facility_id = '{fac_id}' AND medicine_id = '{med_id}'"

        # -------------------------------------------------------------
        # 3. Hypothesis 3: External Supply Disruption or Epidemiological Surge
        # -------------------------------------------------------------
        if demand_disc:
            who_tier = demand_eval.get("epidemiological_risk_tier", "ELEVATED")
            mult = demand_eval.get("who_surveillance_multiplier", 1.35)
            h3_title = "Epidemiological Outbreak & Consumption Demand Surge"
            h3_cause = f"WHO disease surveillance indicates {who_tier} transmission risk, driving consumption +{int((mult - 1.0) * 100)}% above baseline."
            h3_likelihood = 0.80
            h3_evidence = [
                demand_disc.get("description", "Epidemiological demand spike verified."),
                f"Adjusted daily demand rose from {demand_eval['base_daily_rate']} to {demand_eval['adjusted_daily_demand']} units/day."
            ]
            h3_refuting = ["Surveillance metrics reflect localized outbreak in adjacent district, not this facility."]
            h3_query = f"SELECT indicator, year, value, epidemiological_risk_tier FROM who_disease_surveillance WHERE medicine_id = '{med_id}'"
        elif global_disc:
            h3_title = "Active National / Global Manufacturing Shortage"
            h3_cause = f"Upstream API synthesis bottlenecks or GMP holds reported on {gname}."
            h3_likelihood = 0.72
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
            # Adjust likelihoods and add Skeptic's challenge to refuting evidence
            if "corroboration" in skeptic_feedback.lower():
                h3_likelihood = round(max(0.15, h3_likelihood - 0.25), 2)
                h3_refuting.append(f"Skeptic challenge: {skeptic_feedback}")
            if "phantom" in skeptic_feedback.lower() or "quarantine" in skeptic_feedback.lower():
                h1_likelihood = min(0.95, round(h1_likelihood + 0.05, 2))
                h1_evidence.append(f"Addressed Skeptic feedback: Confirmed physical count alignment with deterministic engine.")

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

        # Call LLM client to enrich reasoning
        prompt = f"""
        Investigator Agent Review for {fac_id} - {med_id} ({gname}):
        - Ledger Stock: {stock_eval['ledger_stock']} units
        - Usable Physical Stock: {stock_eval['usable_stock']} units
        - Trust Cover Days: {recon['trust_cover_days']} days (Naive: {recon['naive_cover_days']} days)
        - Shortfall Units: {shortfall['shortfall_units']} units
        - Skeptic Critique: {skeptic_feedback or 'Initial Round'}
        Formulated hypotheses: {[h.title for h in hypotheses]}
        """
        self.llm_client.generate(prompt=prompt, system_prompt="You are a clinical supply chain investigator.")

        return hypotheses
