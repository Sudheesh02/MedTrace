"""
Reconciler Agent (app/agents/reconciler.py)
Audits the numbers first: compares ledger, physical audits, batches, and supplier records.
Ingests grounded state into the Meterless World Model.
"""

from typing import Dict, List, Any
from datetime import datetime
from app.adapters.data_store import DataStore
from app.engine.deterministic import DeterministicEngine
from app.engines.world_model import IngestPipelineService
from app.models.schemas import Discrepancy, AnomalyType

class ReconcilerAgent:
    def __init__(self, data_store: DataStore, ingest_service: IngestPipelineService):
        self.data_store = data_store
        self.ingest_service = ingest_service

    def reconcile_item(self, facility_id: str, medicine_id: str) -> Dict[str, Any]:
        # 1. Fetch data
        med_records = [m for m in self.data_store.get_medicines() if m["medicine_id"] == medicine_id]
        generic_name = med_records[0]["generic_name"] if med_records else "paracetamol"

        ledger = self.data_store.get_latest_ledger(facility_id, medicine_id)
        audit = self.data_store.get_latest_physical_audit(facility_id, medicine_id)
        batches = self.data_store.get_batches(facility_id, medicine_id)
        recent_cons = self.data_store.get_recent_consumption(facility_id, medicine_id)
        pos = self.data_store.get_purchase_orders(facility_id, medicine_id)
        deliveries = self.data_store.get_deliveries(facility_id, medicine_id)
        surveillance_data = self.data_store.get_disease_surveillance(medicine_id)
        packaging = self.data_store.get_packaging_standard(medicine_id)
        shortage_signal = self.data_store.get_cross_border_shortages(medicine_id=medicine_id, generic_name=generic_name)

        ledger_stock = ledger["ledger_stock"] if ledger else 0.0
        counted_stock = audit["counted_stock"] if audit else None

        # 2. Compute average daily consumption rate
        if recent_cons:
            daily_rate = sum(c["units_issued"] for c in recent_cons) / len(recent_cons)
        else:
            daily_rate = 10.0  # safe default

        # 3. Expected delivery timeline and empirical supplier slip
        promised_days = 6.0
        historical_slip_days = 3.0
        if pos:
            latest_po = pos[-1]
            try:
                order_dt = datetime.strptime(latest_po["order_date"], "%Y-%m-%d")
                prom_dt = datetime.strptime(latest_po["promised_date"], "%Y-%m-%d")
                lead_days = (prom_dt - order_dt).days
                if lead_days > 0:
                    promised_days = float(lead_days)
            except Exception:
                pass

            # Query empirical vendor slip prior for contracted supplier
            supplier_id = latest_po.get("supplier_id")
            if supplier_id:
                sup_records = [s for s in self.data_store.get_suppliers() if s.get("supplier_id") == supplier_id]
                if sup_records:
                    sup_rec = sup_records[0]
                    raw_slip = sup_rec.get("historical_p90_slip", sup_rec.get("historical_mean_slip", 3.0))
                    try:
                        historical_slip_days = max(0.0, float(raw_slip))
                    except (ValueError, TypeError):
                        historical_slip_days = 3.0

        # Check UOM mismatch between deliveries and POs
        uom_info = None
        uom_mismatch_po = None
        for deliv in deliveries:
            p_id = deliv.get("po_id")
            matching_po = next((p for p in pos if p.get("po_id") == p_id), None)
            if matching_po:
                po_qty = float(matching_po.get("quantity", 0))
                rec_qty = float(deliv.get("received_qty", 0))
                if po_qty > 0 and (rec_qty >= po_qty * 8.0 or po_qty >= rec_qty * 8.0):
                    multiplier = round(rec_qty / po_qty, 1) if rec_qty > po_qty else round(po_qty / rec_qty, 1)
                    uom_info = DeterministicEngine.normalize_uom_quantity(
                        reported_quantity=rec_qty,
                        reported_unit="box" if rec_qty < po_qty else "tablet",
                        dispensing_unit="tablet",
                        pack_size_units=int(multiplier) if multiplier > 1 else 10
                    )
                    uom_mismatch_po = (p_id, po_qty, rec_qty)
                    break

        # 4. Deterministic reconciliation with date-synchronized audit drift
        calculated_drift = None
        if audit and counted_stock is not None:
            audit_dt = audit.get("date")
            ledger_at_audit = self.data_store.get_ledger_on_date(facility_id, medicine_id, audit_dt) if audit_dt else None
            ref_ledger = float(ledger_at_audit["ledger_stock"]) if ledger_at_audit else ledger_stock
            calculated_drift = max(0.0, ref_ledger - counted_stock)

        recon_result = DeterministicEngine.audit_reconcile_item(
            ledger_stock=ledger_stock,
            last_counted_audit=counted_stock,
            batches=batches,
            daily_rate=daily_rate,
            promised_delivery_days=promised_days,
            historical_slip_days=historical_slip_days,
            surveillance_data=surveillance_data,
            shortage_signal=shortage_signal,
            uom_info=uom_info,
            audit_drift=calculated_drift
        )

        # 5. Extract discrepancies
        discrepancies: List[Discrepancy] = []
        anoms = recon_result["anomalies_detected"]
        
        if anoms["ghost_stock"]:
            drift = recon_result["stock_evaluation"]["audit_drift"]
            discrepancies.append(Discrepancy(
                discrepancy_id=f"DISC-GHOST-{facility_id}-{medicine_id}",
                anomaly_type=AnomalyType.GHOST_STOCK,
                facility_id=facility_id,
                medicine_id=medicine_id,
                description=f"Ledger overstates true stock by {drift} units compared to physical count.",
                impact_units=drift,
                sources_in_conflict=["ledger_daily", "physical_audit"]
            ))

        if anoms["quarantined_batches"]:
            q_qty = recon_result["stock_evaluation"]["quarantined_stock"]
            recalls = self.data_store.get_openfda_recalls(medicine_id=medicine_id, generic_name=generic_name)
            recall_note = ""
            conflicts = ["batches", "ledger_daily"]
            if recalls:
                top_r = recalls[0]
                recall_note = f" Cross-referenced FDA {top_r.get('classification', 'Recall')} ({top_r.get('recalling_firm', 'Manufacturer')}): {top_r.get('reason_for_recall', '')[:90]}."
                conflicts.append("openfda_enforcement_recalls.json")
            if packaging and packaging.get("storage_condition"):
                recall_note += f" Storage requirement: {packaging['storage_condition']}."
                conflicts.append("dailymed_packaging.json")
            discrepancies.append(Discrepancy(
                discrepancy_id=f"DISC-QUAR-{facility_id}-{medicine_id}",
                anomaly_type=AnomalyType.QUARANTINED_BATCH,
                facility_id=facility_id,
                medicine_id=medicine_id,
                description=f"{q_qty} units under quarantine hold counted as usable in ledger.{recall_note}",
                impact_units=q_qty,
                sources_in_conflict=conflicts
            ))

        if anoms["expiring_batches"]:
            e_qty = recon_result["stock_evaluation"]["expiring_stock"]
            discrepancies.append(Discrepancy(
                discrepancy_id=f"DISC-EXP-{facility_id}-{medicine_id}",
                anomaly_type=AnomalyType.EXPIRING_BATCH_UNUSABLE,
                facility_id=facility_id,
                medicine_id=medicine_id,
                description=f"{e_qty} units expire before delivery replenishment window.",
                impact_units=e_qty,
                sources_in_conflict=["batches", "purchase_orders"]
            ))

        # Check UOM mismatch discrepancy
        if anoms.get("uom_mismatch") and uom_mismatch_po:
            po_id_ref, p_qty, r_qty = uom_mismatch_po
            discrepancies.append(Discrepancy(
                discrepancy_id=f"DISC-UOM-{facility_id}-{medicine_id}",
                anomaly_type=AnomalyType.UOM_MISMATCH,
                facility_id=facility_id,
                medicine_id=medicine_id,
                description=f"Unit of measure mismatch on {po_id_ref}: PO ordered {p_qty} units, but delivery logged {r_qty} ({uom_info.get('reported_unit')} vs {uom_info.get('dispensing_unit')}).",
                impact_units=abs(r_qty - p_qty),
                sources_in_conflict=["purchase_orders", "deliveries", "dailymed_packaging.json"]
            ))

        # Check epidemiological demand spike discrepancy
        if anoms.get("demand_spike") or (surveillance_data and surveillance_data.get("epidemiological_risk_tier") == "ELEVATED"):
            tier = surveillance_data.get("epidemiological_risk_tier", "ELEVATED") if surveillance_data else "ELEVATED"
            disease = surveillance_data.get("matched_indicator", "WHO GHO surveillance") if surveillance_data else "Seasonal surge"
            ratio = recon_result["demand_evaluation"].get("who_surveillance_multiplier", 1.35)
            discrepancies.append(Discrepancy(
                discrepancy_id=f"DISC-DEMAND-{facility_id}-{medicine_id}",
                anomaly_type=AnomalyType.DEMAND_SPIKE,
                facility_id=facility_id,
                medicine_id=medicine_id,
                description=f"Epidemiological demand spike: WHO surveillance indicates {disease} {tier} risk (+{int((ratio - 1.0) * 100)}% surge).",
                impact_units=round((recon_result["demand_evaluation"]["adjusted_daily_demand"] - daily_rate) * 14.0, 1),
                sources_in_conflict=["who_disease_surveillance.json", "consumption_daily"]
            ))

        # Check PO dispatched but never received
        for po in pos:
            if str(po.get("status", "")).upper() == "DISPATCHED":
                p_id = po.get("po_id")
                po_qty = float(po.get("quantity", 0))
                matching_deliv = next((d for d in deliveries if d.get("po_id") == p_id), None)
                if not matching_deliv:
                    discrepancies.append(Discrepancy(
                        discrepancy_id=f"DISC-PO-DISP-{p_id}",
                        anomaly_type=AnomalyType.PO_DISPATCHED_NOT_RECEIVED,
                        facility_id=facility_id,
                        medicine_id=medicine_id,
                        description=f"Purchase order {p_id} ({po_qty} units) marked DISPATCHED on {po.get('order_date')} but no delivery receipt logged.",
                        impact_units=po_qty,
                        sources_in_conflict=["purchase_orders", "deliveries"]
                    ))

        # Check openFDA shortages & cross-border shortages
        fda_shortages = self.data_store.get_openfda_shortages(generic_name)
        if fda_shortages or shortage_signal:
            shortage_cause = shortage_signal.get("root_cause_classification", "Active manufacturing disruption") if shortage_signal else "Active FDA manufacturing shortage"
            rec_count = len(fda_shortages) if fda_shortages else 1
            discrepancies.append(Discrepancy(
                discrepancy_id=f"DISC-FDA-{medicine_id}",
                anomaly_type=AnomalyType.GLOBAL_SHORTAGE,
                facility_id=facility_id,
                medicine_id=medicine_id,
                description=f"Global/upstream drug shortage: {generic_name} subject to {shortage_cause} ({rec_count} records).",
                impact_units=0.0,
                sources_in_conflict=["openfda_shortages.json", "cross_border_shortages.json"]
            ))

        # 6. Ingest into World Model & Conflict Store
        self.ingest_service.ingest_facility_item(
            facility={"facility_id": facility_id},
            medicine={"medicine_id": medicine_id, "generic_name": generic_name},
            stock_info={
                "ledger_stock": ledger_stock,
                "usable_stock": recon_result["stock_evaluation"]["usable_stock"],
                "trust_cover_days": recon_result["trust_cover_days"],
                "daily_rate": round(daily_rate, 2),
                "discrepancies_count": len(discrepancies)
            },
            agent_id="reconciler"
        )

        for disc in discrepancies:
            self.ingest_service.record_discrepancy_conflict(
                discrepancy=disc.model_dump(),
                facility_id=facility_id,
                medicine_id=medicine_id,
                agent_id="reconciler"
            )

        return {
            "facility_id": facility_id,
            "medicine_id": medicine_id,
            "generic_name": generic_name,
            "deterministic_reconciliation": recon_result,
            "discrepancies": [d.model_dump() for d in discrepancies]
        }
