"""
Action Planner Agent (app/agents/action_planner.py)
Formulates ranked, approval-ready action recommendations (Inter-facility Transfer, Expedite PO, Emergency Purchase, Batch Release).
Injects cross-session officer preferences from H-MEM and enforces number provenance.
Dynamically audits peer facilities for usable surplus and queries contracted suppliers.
"""

from typing import Dict, List, Any, Optional
from app.adapters.data_store import DataStore
from app.adapters.llm_client import LLMClient
from app.engines.hmem import HMemEngine
from app.models.schemas import ActionRecommendation, ActionType, Hypothesis

class ActionPlannerAgent:
    def __init__(self, llm_client: LLMClient, hmem: HMemEngine, data_store: Optional[DataStore] = None):
        self.llm_client = llm_client
        self.hmem = hmem
        self.data_store = data_store

    def plan_actions(
        self,
        facility_id: str,
        medicine_id: str,
        hypothesis: Hypothesis,
        deterministic_recon: Dict[str, Any]
    ) -> List[ActionRecommendation]:
        shortfall = deterministic_recon["trust_shortfall"]["shortfall_units"]
        gap_days = deterministic_recon["trust_shortfall"]["gap_days"]
        stock_eval = deterministic_recon.get("stock_evaluation", {})
        quarantined_stock = stock_eval.get("quarantined_stock", 0.0)
        audit_drift = stock_eval.get("audit_drift", 0.0)
        trust_cover = deterministic_recon.get("trust_cover_days", 0.0)

        # Consult H-MEM for past officer decisions
        memories = self.hmem.get_relevant_memories(facility_id, medicine_id)
        rejected_patterns = memories.get("rejected_patterns", [])

        # 1. Identify peer facility with highest usable stock surplus
        best_source_facility: Optional[str] = None
        best_surplus = 0.0
        if self.data_store:
            facilities = self.data_store.get_facilities()
            for fac in facilities:
                peer_id = fac["facility_id"]
                if peer_id == facility_id:
                    continue  # A facility cannot transfer to itself
                peer_ledger = self.data_store.get_latest_ledger(peer_id, medicine_id)
                if peer_ledger:
                    peer_stock = float(peer_ledger.get("ledger_stock", 0.0))
                    # Check if peer stock is locked under quarantine
                    peer_batches = self.data_store.get_batches(peer_id, medicine_id)
                    quar_at_peer = sum(float(b.get("quantity", 0)) for b in peer_batches if str(b.get("quarantined", "")).lower() == "true")
                    # Check if peer facility has physical audit drift (phantom stock)
                    peer_audit = self.data_store.get_latest_physical_audit(peer_id, medicine_id)
                    peer_drift = 0.0
                    if peer_audit:
                        peer_counted = float(peer_audit.get("counted_stock", peer_stock))
                        if peer_stock > peer_counted:
                            peer_drift = peer_stock - peer_counted
                    usable_peer = max(0.0, peer_stock - quar_at_peer - peer_drift)
                    if usable_peer > best_surplus:
                        best_surplus = usable_peer
                        best_source_facility = peer_id

        # 2. Identify contracted supplier from active purchase orders
        contracted_supplier = None
        if self.data_store:
            pos = self.data_store.get_purchase_orders(facility_id, medicine_id)
            if pos:
                contracted_supplier = pos[-1].get("supplier_id")
            if not contracted_supplier:
                suppliers = self.data_store.get_suppliers()
                if suppliers:
                    contracted_supplier = suppliers[0].get("supplier_id")

        recommendations: List[ActionRecommendation] = []

        # Check if quarantined lot is the primary driver of usable deficit
        has_quarantine = (quarantined_stock > 0 and "quarantine" in hypothesis.title.lower())
        if has_quarantine:
            recommendations.append(ActionRecommendation(
                action_id=f"ACT-REL-{facility_id}-{medicine_id}",
                action_type=ActionType.BATCH_RELEASE,
                facility_id=facility_id,
                medicine_id=medicine_id,
                recommended_units=quarantined_stock,
                feasibility_score=0.88,
                justification=f"Fast-track lab Certificate of Analysis (CoA) review for {quarantined_stock:.0f} quarantined units to restore usable balance.",
                number_provenance={
                    "shortfall_units": shortfall,
                    "gap_days": gap_days,
                    "quarantined_units": quarantined_stock
                }
            ))

        # Check if audit drift / phantom stock was identified
        if audit_drift > 0:
            recommendations.append(ActionRecommendation(
                action_id=f"ACT-ADJ-{facility_id}-{medicine_id}",
                action_type=ActionType.INVENTORY_AUDIT_ADJUSTMENT,
                facility_id=facility_id,
                medicine_id=medicine_id,
                recommended_units=audit_drift,
                feasibility_score=0.95,
                justification=f"Reconcile LMIS inventory ledger: Post debit adjustment of {audit_drift:.0f} units to match verified physical shelf count ({stock_eval.get('usable_stock', 0):.0f} units), eliminating phantom ledger drift.",
                number_provenance={
                    "audit_drift": audit_drift,
                    "ledger_stock": stock_eval.get("ledger_stock", 0.0),
                    "usable_stock": stock_eval.get("usable_stock", 0.0)
                }
            ))

        # Check if local inventory is secure (Zero shortfall scenario)
        if shortfall == 0:
            mon_feasibility = 0.98 if audit_drift == 0 else 0.92
            mon_justification = (
                f"Inventory levels are secure ({trust_cover:.1f} days of cover). Routine monitoring active; "
                f"safety buffer intact; emergency transfer and local purchase quotas remain on standby."
                if audit_drift == 0 else
                f"Following {audit_drift:.0f}-unit ledger debit adjustment, verified usable stock covers {trust_cover:.1f} days. "
                f"Routine buffer monitoring active; emergency quotas remain on standby."
            )
            recommendations.append(ActionRecommendation(
                action_id=f"ACT-MON-{facility_id}-{medicine_id}",
                action_type=ActionType.MONITOR_BUFFER,
                facility_id=facility_id,
                medicine_id=medicine_id,
                recommended_units=0.0,
                feasibility_score=mon_feasibility,
                justification=mon_justification,
                number_provenance={
                    "shortfall_units": 0.0,
                    "gap_days": 0.0,
                    "trust_cover_days": trust_cover
                }
            ))

        # Check peer transfer feasibility
        transfer_penalty = 0.20 if any("PEER_TRANSFER" in p for p in rejected_patterns) else 0.0
        can_transfer = (best_source_facility is not None and best_surplus >= max(50.0, shortfall))
        
        if shortfall > 0:
            transfer_feasibility = round(max(0.1, (0.90 if can_transfer else 0.35) - transfer_penalty), 2)
            if can_transfer:
                transfer_justification = f"Transfer {shortfall} units from peer warehouse {best_source_facility} (usable surplus {best_surplus:.0f} units, lead time 24h) to cover {gap_days}-day gap."
            elif best_source_facility:
                transfer_justification = f"Peer warehouse {best_source_facility} holds only {best_surplus:.0f} units; partial transfer possible but insufficient for full {shortfall} unit shortfall."
            else:
                transfer_justification = f"No peer facility holds surplus of {medicine_id}; inter-facility transfer unavailable."
        else:
            transfer_justification = f"No emergency stock transfer required: Facility holds {trust_cover:.1f} days of verified usable cover, exceeding safety threshold. Inter-facility transfer queue on standby."
            transfer_feasibility = 0.20

        recommendations.append(ActionRecommendation(
            action_id=f"ACT-TRF-{facility_id}-{medicine_id}",
            action_type=ActionType.PEER_TRANSFER,
            facility_id=facility_id,
            medicine_id=medicine_id,
            recommended_units=shortfall,
            source_facility_id=best_source_facility if (can_transfer and shortfall > 0) else None,
            feasibility_score=transfer_feasibility,
            justification=transfer_justification,
            number_provenance={
                "shortfall_units": shortfall,
                "gap_days": gap_days,
                "peer_surplus": best_surplus
            }
        ))

        # Secondary: Expedite PO with contracted supplier
        expedite_penalty = 0.20 if any("EXPEDITE_PO" in p for p in rejected_patterns) else 0.0
        if shortfall > 0:
            expedite_justification = f"Issue urgent dispatch escalation to contracted supplier {contracted_supplier or 'SUP-001'} to compress delivery slip and cover {gap_days}-day gap."
            expedite_feasibility = round(max(0.1, 0.75 - expedite_penalty), 2)
        else:
            expedite_justification = f"Standard procurement cycle: No expedited dispatch required; existing inventory covers {trust_cover:.1f} days."
            expedite_feasibility = 0.15

        recommendations.append(ActionRecommendation(
            action_id=f"ACT-EXP-{facility_id}-{medicine_id}",
            action_type=ActionType.EXPEDITE_PO,
            facility_id=facility_id,
            medicine_id=medicine_id,
            recommended_units=shortfall,
            supplier_id=contracted_supplier or "SUP-001",
            feasibility_score=expedite_feasibility,
            justification=expedite_justification,
            number_provenance={
                "shortfall_units": shortfall,
                "gap_days": gap_days
            }
        ))

        # Fallback: Emergency Purchase
        emerg_penalty = 0.20 if any("EMERGENCY_PURCHASE" in p for p in rejected_patterns) else 0.0
        if shortfall > 0:
            emerg_justification = f"Authorise district emergency local procurement quota of {shortfall} units if transfer or supplier dispatch cannot arrive within 48h."
            emerg_feasibility = round(max(0.1, 0.60 - emerg_penalty), 2)
        else:
            emerg_justification = f"Zero emergency procurement required: Local stock is adequate ({trust_cover:.1f} days of cover); emergency quota preserved."
            emerg_feasibility = 0.10

        recommendations.append(ActionRecommendation(
            action_id=f"ACT-EMERG-{facility_id}-{medicine_id}",
            action_type=ActionType.EMERGENCY_PURCHASE,
            facility_id=facility_id,
            medicine_id=medicine_id,
            recommended_units=shortfall,
            feasibility_score=emerg_feasibility,
            justification=emerg_justification,
            number_provenance={
                "shortfall_units": shortfall,
                "gap_days": gap_days
            }
        ))

        # Sort recommendations by feasibility score descending
        recommendations.sort(key=lambda r: r.feasibility_score, reverse=True)

        # Call LLM client to log operational action guidance
        prompt = f"""
        Action Planner Synthesis for {facility_id} - {medicine_id}:
        Winning Hypothesis: {hypothesis.title} (Likelihood: {hypothesis.likelihood})
        Trust Cover: {trust_cover:.1f} days, Shortfall: {shortfall} units across {gap_days} gap days.
        Prioritized Actions: {[f'{r.action_type.value} ({r.recommended_units} units, feasibility {r.feasibility_score})' for r in recommendations]}
        """
        llm_res = self.llm_client.generate(prompt=prompt, system_prompt="You are a clinical supply chain action planner.")
        self.last_llm_response = llm_res

        return recommendations
