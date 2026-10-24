"""
Action Planner Agent (app/agents/action_planner.py)
Formulates ranked, approval-ready action recommendations (Inter-facility Transfer, Expedite PO, Emergency Purchase).
Injects cross-session officer preferences from H-MEM and enforces number provenance.
"""

from typing import Dict, List, Any
from app.adapters.llm_client import LLMClient
from app.engines.hmem import HMemEngine
from app.models.schemas import ActionRecommendation, ActionType, Hypothesis

class ActionPlannerAgent:
    def __init__(self, llm_client: LLMClient, hmem: HMemEngine):
        self.llm_client = llm_client
        self.hmem = hmem

    def plan_actions(
        self,
        facility_id: str,
        medicine_id: str,
        hypothesis: Hypothesis,
        deterministic_recon: Dict[str, Any]
    ) -> List[ActionRecommendation]:
        shortfall = deterministic_recon["trust_shortfall"]["shortfall_units"]
        gap_days = deterministic_recon["trust_shortfall"]["gap_days"]

        # Consult H-MEM for past officer decisions
        memories = self.hmem.get_relevant_memories(facility_id, medicine_id)
        rejected_patterns = memories.get("rejected_patterns", [])

        recommendations: List[ActionRecommendation] = []

        # 1. Primary Recommendation: Peer Transfer
        transfer_penalty = 0.0
        if any("PEER_TRANSFER" in p for p in rejected_patterns):
            transfer_penalty = 0.20

        recommendations.append(ActionRecommendation(
            action_id=f"ACT-TRF-{facility_id}-{medicine_id}",
            action_type=ActionType.PEER_TRANSFER,
            facility_id=facility_id,
            medicine_id=medicine_id,
            recommended_units=shortfall,
            source_facility_id="FAC-WH-01",  # District Drug Warehouse
            feasibility_score=round(max(0.1, 0.90 - transfer_penalty), 2),
            justification=f"Transfer {shortfall} units from District Central Store (lead time 24h) to cover {gap_days}-day gap.",
            number_provenance={
                "shortfall_units": shortfall,
                "gap_days": gap_days
            }
        ))

        # 2. Secondary Recommendation: Expedite Purchase Order
        recommendations.append(ActionRecommendation(
            action_id=f"ACT-EXP-{facility_id}-{medicine_id}",
            action_type=ActionType.EXPEDITE_PO,
            facility_id=facility_id,
            medicine_id=medicine_id,
            recommended_units=shortfall,
            supplier_id="SUP-001",
            feasibility_score=0.75,
            justification=f"Issue urgent dispatch escalation to contracted supplier to compress historical delivery slip.",
            number_provenance={
                "shortfall_units": shortfall,
                "gap_days": gap_days
            }
        ))

        # 3. Fallback: Emergency Local Purchase
        recommendations.append(ActionRecommendation(
            action_id=f"ACT-EMERG-{facility_id}-{medicine_id}",
            action_type=ActionType.EMERGENCY_PURCHASE,
            facility_id=facility_id,
            medicine_id=medicine_id,
            recommended_units=shortfall,
            feasibility_score=0.60,
            justification=f"Authorise district emergency local procurement quota if transfer cannot be dispatched within 48h.",
            number_provenance={
                "shortfall_units": shortfall,
                "gap_days": gap_days
            }
        ))

        return recommendations
