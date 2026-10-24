"""
Master Multi-Agent Orchestrator (app/orchestrator.py)
Orchestrates: Reconciler -> World Model -> Investigator <-> Skeptic Loop -> Action Planner -> H-MEM.
Emits structured JSONL execution traces into logs/.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.adapters.data_store import DataStore
from app.adapters.llm_client import LLMClient
from app.engines.world_model import WorldStoreService, IngestPipelineService, ContextBuilderService
from app.engines.hmem import HMemEngine
from app.agents.reconciler import ReconcilerAgent
from app.agents.investigator import InvestigatorAgent
from app.agents.skeptic import SkepticAgent
from app.agents.action_planner import ActionPlannerAgent
from app.models.schemas import ActionPack

class MedTraceOrchestrator:
    def __init__(self, use_zetaris: bool = False, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)

        self.data_store = DataStore(use_zetaris=use_zetaris)
        self.llm_client = LLMClient()
        
        # Meterless Engines
        self.world_store = WorldStoreService()
        self.ingest_service = IngestPipelineService(self.world_store)
        self.context_builder = ContextBuilderService(self.world_store)
        self.hmem = HMemEngine()

        # Agents
        self.reconciler = ReconcilerAgent(self.data_store, self.ingest_service)
        self.investigator = InvestigatorAgent(self.llm_client)
        self.skeptic = SkepticAgent(self.llm_client)
        self.action_planner = ActionPlannerAgent(self.llm_client, self.hmem)

    def run_investigation(
        self,
        facility_id: str = "FAC-DH-01",
        medicine_id: str = "MED-007",
        run_id: Optional[str] = None
    ) -> ActionPack:
        run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        trace_file = os.path.join(self.logs_dir, f"trace_{run_id}.jsonl")
        trace_entries = []

        def log_step(agent: str, action: str, details: Any):
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "agent": agent,
                "action": action,
                "details": details,
                "model": self.llm_client.model
            }
            trace_entries.append(entry)
            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

        log_step("Orchestrator", "START_RUN", {"facility_id": facility_id, "medicine_id": medicine_id})

        # 1. Reconciliation Step
        recon = self.reconciler.reconcile_item(facility_id, medicine_id)
        log_step("ReconcilerAgent", "RECONCILE_COMPLETE", {
            "discrepancies_found": len(recon["discrepancies"]),
            "usable_stock": recon["deterministic_reconciliation"]["stock_evaluation"]["usable_stock"],
            "shortfall": recon["deterministic_reconciliation"]["trust_shortfall"]["shortfall_units"]
        })

        # 2. Build Grounded Context from World Model
        world_context = self.context_builder.build_structured_context(facility_id, medicine_id)
        log_step("WorldModelEngine", "CONTEXT_BUILT", {
            "canon_hash": world_context["canon_hash"],
            "entities_present": list(world_context.keys())
        })

        # 3. Investigator <-> Skeptic Loop (Max 3 rounds)
        winning_hyp = None
        skeptic_review = None
        rounds = 0
        max_rounds = 3
        last_critique = None

        while rounds < max_rounds:
            rounds += 1
            log_step("InvestigatorAgent", f"ROUND_{rounds}_START", {"round": rounds, "previous_critique": last_critique})
            
            hypotheses = self.investigator.investigate(recon, world_context, skeptic_feedback=last_critique)
            log_step("InvestigatorAgent", "HYPOTHESES_GENERATED", {
                "hypotheses_count": len(hypotheses),
                "titles": [h.title for h in hypotheses],
                "likelihoods": {h.hypothesis_id: h.likelihood for h in hypotheses}
            })

            # Skeptic & Number Auditor
            top_hyp, review = self.skeptic.review_and_audit(
                hypotheses=hypotheses,
                deterministic_recon=recon["deterministic_reconciliation"],
                round_number=rounds
            )
            log_step("SkepticAgent", f"ROUND_{rounds}_EVALUATION", {
                "accepted": review.accepted,
                "confidence": review.confidence_score,
                "numbers_valid": review.audited_numbers_valid,
                "critique": review.critique_notes,
                "flagged_inconsistencies": review.flagged_inconsistencies
            })

            if review.accepted:
                winning_hyp = top_hyp
                skeptic_review = review
                break
            else:
                last_critique = review.critique_notes

        if not winning_hyp:
            winning_hyp = hypotheses[0]
            skeptic_review = review

        # 4. Action Planner
        recommendations = self.action_planner.plan_actions(
            facility_id=facility_id,
            medicine_id=medicine_id,
            hypothesis=winning_hyp,
            deterministic_recon=recon["deterministic_reconciliation"]
        )
        log_step("ActionPlannerAgent", "ACTIONS_RECOMMENDED", {
            "recommendations_count": len(recommendations),
            "top_action": recommendations[0].action_type
        })

        det_rec = recon["deterministic_reconciliation"]
        pack = ActionPack(
            run_id=run_id,
            facility_id=facility_id,
            medicine_id=medicine_id,
            stockout_prevented=True,
            days_of_cover_trust=det_rec["trust_cover_days"],
            days_of_cover_naive=det_rec["naive_cover_days"],
            understated_gap_percent=det_rec["understated_gap_percent"],
            investigation_summary=skeptic_review.critique_notes if skeptic_review else "Investigation concluded.",
            winning_hypothesis=winning_hyp,
            recommendations=recommendations,
            skeptic_rounds=rounds,
            trace_file=trace_file
        )

        log_step("Orchestrator", "RUN_COMPLETE", {"run_id": run_id, "status": "SUCCESS"})
        return pack
