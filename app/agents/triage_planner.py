"""
Triage Planner Agent (app/agents/triage_planner.py)
Phase 3.2 Multi-Agent Architecture: Proactive district-wide inventory scanning & prioritization.
Scans all facility-medicine pairs across the network, audits trust-adjusted availability,
detects latent discrepancies, and ranks items by stockout urgency (Critical, Warning, Secure).
"""

from typing import Dict, List, Optional, Any
from app.adapters.data_store import DataStore
from app.adapters.llm_client import LLMClient
from app.engine.deterministic import DeterministicEngine

class TriagePlannerAgent:
    def __init__(self, data_store: DataStore, llm_client: Optional[LLMClient] = None):
        self.data_store = data_store
        self.llm_client = llm_client

    def triage_pair(self, facility_id: str, medicine_id: str, fac_meta: Optional[Dict[str, Any]] = None, med_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fast deterministic audit of a single facility-medicine pair.
        Computes trust-adjusted stock, days of cover, shortfall, and discrepancy indicators.
        """
        ledger = self.data_store.get_latest_ledger(facility_id, medicine_id)
        ledger_stock = float(ledger.get("ledger_stock", 0.0)) if ledger else 0.0

        audit = self.data_store.get_latest_physical_audit(facility_id, medicine_id)
        counted_stock = float(audit.get("counted_stock", ledger_stock)) if audit else None

        batches = self.data_store.get_batches(facility_id, medicine_id)
        recent_cons = self.data_store.get_recent_consumption(facility_id, medicine_id, days=7)
        daily_rate = sum(c.get("units_issued", 0.0) for c in recent_cons) / len(recent_cons) if recent_cons else 15.0

        pos = self.data_store.get_purchase_orders(facility_id, medicine_id)
        promised_days = 6.0
        historical_slip_days = 3.0
        if pos:
            latest_po = pos[-1]
            try:
                from datetime import datetime
                order_dt = datetime.strptime(latest_po["order_date"], "%Y-%m-%d")
                prom_dt = datetime.strptime(latest_po["promised_date"], "%Y-%m-%d")
                lead_days = (prom_dt - order_dt).days
                if lead_days > 0:
                    promised_days = float(lead_days)
            except Exception:
                pass

        # Calculate date-synchronized audit drift
        calculated_drift = None
        if audit and counted_stock is not None:
            audit_dt = audit.get("date")
            ledger_at_audit = self.data_store.get_ledger_on_date(facility_id, medicine_id, audit_dt) if audit_dt else None
            ref_ledger = float(ledger_at_audit["ledger_stock"]) if ledger_at_audit else ledger_stock
            calculated_drift = max(0.0, ref_ledger - counted_stock)

        recon = DeterministicEngine.audit_reconcile_item(
            ledger_stock=ledger_stock,
            last_counted_audit=counted_stock,
            batches=batches,
            daily_rate=daily_rate,
            promised_delivery_days=promised_days,
            historical_slip_days=historical_slip_days,
            audit_drift=calculated_drift
        )

        stock_eval = recon["stock_evaluation"]
        shortfall = recon["trust_shortfall"]
        anoms = recon["anomalies_detected"]

        # Classification based on trust cover and discrepancies
        trust_cover = recon["trust_cover_days"]
        shortfall_units = shortfall["shortfall_units"]
        discrepancy_count = sum(1 for v in anoms.values() if v)

        if trust_cover < 7.0 or shortfall_units > 0:
            urgency_tier = "CRITICAL"
            urgency_score = 100.0 - min(90.0, trust_cover * 5.0) + min(30.0, shortfall_units * 0.1)
        elif trust_cover < 14.0 or discrepancy_count > 0:
            urgency_tier = "WARNING"
            urgency_score = 50.0 - min(30.0, trust_cover * 2.0) + (discrepancy_count * 10.0)
        else:
            urgency_tier = "SECURE"
            urgency_score = max(0.0, 20.0 - trust_cover * 0.5)

        fac_name = fac_meta.get("name", facility_id) if fac_meta else facility_id
        med_name = med_meta.get("generic_name", medicine_id) if med_meta else medicine_id

        return {
            "facility_id": facility_id,
            "facility_name": fac_name,
            "medicine_id": medicine_id,
            "generic_name": med_name,
            "ledger_stock": stock_eval["ledger_stock"],
            "usable_stock": stock_eval["usable_stock"],
            "audit_drift": stock_eval["audit_drift"],
            "quarantined_stock": stock_eval["quarantined_stock"],
            "daily_rate": round(daily_rate, 1),
            "trust_cover_days": trust_cover,
            "naive_cover_days": recon["naive_cover_days"],
            "shortfall_units": shortfall_units,
            "gap_days": shortfall["gap_days"],
            "p_stockout_risk": recon.get("monte_carlo_delivery", {}).get("p_stockout_before_arrival", 0.0),
            "discrepancies_detected": [k for k, v in anoms.items() if v],
            "urgency_tier": urgency_tier,
            "urgency_score": round(urgency_score, 1)
        }

    def scan_district(self, facility_id: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
        """
        Scans all facilities (or a specific facility) across all registered medicines.
        Returns a sorted portfolio ranked by stockout urgency.
        """
        facilities = self.data_store.get_facilities()
        medicines = self.data_store.get_medicines()

        fac_map = {f["facility_id"]: f for f in facilities}
        med_map = {m["medicine_id"]: m for m in medicines}

        target_facs = [fac_map[facility_id]] if facility_id and facility_id in fac_map else facilities

        scanned_items = []
        for fac in target_facs:
            f_id = fac["facility_id"]
            for med in medicines:
                m_id = med["medicine_id"]
                item = self.triage_pair(f_id, m_id, fac_meta=fac, med_meta=med)
                scanned_items.append(item)

        # Sort by urgency score descending (most critical first), then trust cover ascending
        scanned_items.sort(key=lambda x: (x["urgency_score"], -x["trust_cover_days"]), reverse=True)

        critical_count = sum(1 for x in scanned_items if x["urgency_tier"] == "CRITICAL")
        warning_count = sum(1 for x in scanned_items if x["urgency_tier"] == "WARNING")
        secure_count = sum(1 for x in scanned_items if x["urgency_tier"] == "SECURE")

        top_critical = scanned_items[:top_n]

        # Call LLM client for qualitative triage synthesis if available
        qualitative_synthesis = None
        if self.llm_client:
            prompt = f"""
            Triage District Portfolio Summary:
            Total Evaluated: {len(scanned_items)} facility-medicine items.
            Critical Items: {critical_count}, Warnings: {warning_count}, Secure: {secure_count}.
            Top 3 Critical Bottlenecks:
            {[f"{x['facility_name']} - {x['generic_name']} (Cover: {x['trust_cover_days']}d, Shortfall: {x['shortfall_units']} units, Risk: {x['urgency_tier']})" for x in top_critical[:3]]}
            """
            llm_res = self.llm_client.generate(prompt=prompt, system_prompt="You are a clinical supply chain triage officer.")
            qualitative_synthesis = llm_res.get("text")

        return {
            "total_evaluated": len(scanned_items),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "secure_count": secure_count,
            "top_urgent_items": top_critical,
            "qualitative_synthesis": qualitative_synthesis
        }
