"""
Reconciler Agent (app/agents/reconciler.py)
Audits the numbers first: compares ledger, physical audits, batches, and supplier records.
Ingests grounded state into the Meterless World Model.
"""

from typing import Dict, List, Any
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
        ledger = self.data_store.get_latest_ledger(facility_id, medicine_id)
        audit = self.data_store.get_latest_physical_audit(facility_id, medicine_id)
        batches = self.data_store.get_batches(facility_id, medicine_id)
        recent_cons = self.data_store.get_recent_consumption(facility_id, medicine_id)
        pos = self.data_store.get_purchase_orders(facility_id, medicine_id)

        ledger_stock = ledger["ledger_stock"] if ledger else 0.0
        counted_stock = audit["counted_stock"] if audit else None

        # 2. Compute average daily consumption rate
        if recent_cons:
            daily_rate = sum(c["units_issued"] for c in recent_cons) / len(recent_cons)
        else:
            daily_rate = 10.0  # safe default

        # 3. Expected delivery timeline
        promised_days = 6.0
        if pos:
            latest_po = pos[-1]
            # assume default 6 days if not parsed
            promised_days = 6.0

        # 4. Deterministic reconciliation
        recon_result = DeterministicEngine.audit_reconcile_item(
            ledger_stock=ledger_stock,
            last_counted_audit=counted_stock,
            batches=batches,
            daily_rate=daily_rate,
            promised_delivery_days=promised_days,
            historical_slip_days=3.0
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
            discrepancies.append(Discrepancy(
                discrepancy_id=f"DISC-QUAR-{facility_id}-{medicine_id}",
                anomaly_type=AnomalyType.QUARANTINED_BATCH,
                facility_id=facility_id,
                medicine_id=medicine_id,
                description=f"{q_qty} units under quarantine hold counted as usable in ledger.",
                impact_units=q_qty,
                sources_in_conflict=["batches", "ledger_daily"]
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

        # Check openFDA shortages
        med_records = [m for m in self.data_store.get_medicines() if m["medicine_id"] == medicine_id]
        generic_name = med_records[0]["generic_name"] if med_records else "paracetamol"
        fda_shortages = self.data_store.get_openfda_shortages(generic_name)
        if fda_shortages:
            discrepancies.append(Discrepancy(
                discrepancy_id=f"DISC-FDA-{medicine_id}",
                anomaly_type=AnomalyType.GLOBAL_SHORTAGE,
                facility_id=facility_id,
                medicine_id=medicine_id,
                description=f"Active FDA manufacturing shortage reported on {generic_name} ({len(fda_shortages)} records).",
                impact_units=0.0,
                sources_in_conflict=["openfda_shortages.json"]
            ))

        # 6. Ingest into World Model
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

        return {
            "facility_id": facility_id,
            "medicine_id": medicine_id,
            "generic_name": generic_name,
            "deterministic_reconciliation": recon_result,
            "discrepancies": [d.model_dump() for d in discrepancies]
        }
