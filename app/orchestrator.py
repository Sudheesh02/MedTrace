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
from app.agents.triage_planner import TriagePlannerAgent
from app.models.schemas import ActionPack

class MedTraceOrchestrator:
    def __init__(self, use_zetaris: bool = False, logs_dir: str = "logs", hmem: Optional[HMemEngine] = None):
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)

        self.data_store = DataStore(use_zetaris=use_zetaris)
        self.llm_client = LLMClient()
        
        # Meterless Engines
        self.world_store = WorldStoreService()
        self.ingest_service = IngestPipelineService(self.world_store)
        self.context_builder = ContextBuilderService(self.world_store)
        self.hmem = hmem or HMemEngine()

        # Agents (Phase 3.2: 5 agents)
        self.triage_planner = TriagePlannerAgent(self.data_store, self.llm_client)
        self.reconciler = ReconcilerAgent(self.data_store, self.ingest_service, hmem=self.hmem)
        self.investigator = InvestigatorAgent(self.llm_client)
        self.skeptic = SkepticAgent(self.llm_client)
        self.action_planner = ActionPlannerAgent(self.llm_client, self.hmem, self.data_store)

    def run_investigation(
        self,
        facility_id: str = "FAC-DH-01",
        medicine_id: str = "MED-007",
        run_id: Optional[str] = None
    ) -> ActionPack:
        run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        trace_file = os.path.join(self.logs_dir, f"trace_{run_id}.jsonl")
        trace_entries = []

        def log_step(
            agent: str,
            action: str,
            details: Any,
            model: Optional[str] = None,
            llm_used: bool = False,
            fallback: bool = False
        ):
            chosen_model = model or getattr(self.llm_client, "last_model_used", self.llm_client.model)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "agent": agent,
                "action": action,
                "details": details,
                "model": chosen_model,
                "llm_used": bool(llm_used),
                "fallback": bool(fallback)
            }
            trace_entries.append(entry)
            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")

        facility_id = str(facility_id).strip().upper()
        medicine_id = str(medicine_id).strip().upper()

        # Input validation: ensure requested facility and medicine exist
        facility_id = str(facility_id).strip().upper()
        medicine_id = str(medicine_id).strip().upper()

        valid_facs = {f["facility_id"] for f in self.data_store.get_facilities()}
        valid_meds = {m["medicine_id"] for m in self.data_store.get_medicines()}
        if valid_facs and facility_id not in valid_facs:
            raise ValueError(f"Unrecognized facility_id '{facility_id}'. Registered facilities: {sorted(list(valid_facs))}")
        if valid_meds and medicine_id not in valid_meds:
            raise ValueError(f"Unrecognized medicine_id '{medicine_id}'. Registered medicines: {sorted(list(valid_meds))}")

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
            inv_llm = getattr(self.investigator, "last_llm_response", None)
            inv_text = inv_llm.get("text", "") if isinstance(inv_llm, dict) else ""
            inv_usage = inv_llm.get("usage", {}) if isinstance(inv_llm, dict) else {}
            inv_model = inv_llm.get("model", self.llm_client.model) if isinstance(inv_llm, dict) else self.llm_client.model
            inv_used = inv_llm.get("llm_used", False) if isinstance(inv_llm, dict) else False
            inv_fallback = inv_llm.get("fallback", False) if isinstance(inv_llm, dict) else False
            log_step("InvestigatorAgent", "HYPOTHESES_GENERATED", {
                "hypotheses_count": len(hypotheses),
                "titles": [h.title for h in hypotheses],
                "likelihoods": {h.hypothesis_id: h.likelihood for h in hypotheses},
                "llm_reasoning": inv_text,
                "token_usage": inv_usage
            }, model=inv_model, llm_used=inv_used, fallback=inv_fallback)

            # Skeptic & Number Auditor
            top_hyp, review = self.skeptic.review_and_audit(
                hypotheses=hypotheses,
                deterministic_recon=recon["deterministic_reconciliation"],
                round_number=rounds,
                world_context=world_context
            )
            skep_llm = getattr(self.skeptic, "last_llm_response", None)
            skep_text = skep_llm.get("text", "") if isinstance(skep_llm, dict) else ""
            skep_usage = skep_llm.get("usage", {}) if isinstance(skep_llm, dict) else {}
            skep_model = skep_llm.get("model", self.llm_client.model) if isinstance(skep_llm, dict) else self.llm_client.model
            skep_used = skep_llm.get("llm_used", False) if isinstance(skep_llm, dict) else False
            skep_fallback = skep_llm.get("fallback", False) if isinstance(skep_llm, dict) else False
            log_step("SkepticAgent", f"ROUND_{rounds}_EVALUATION", {
                "accepted": review.accepted,
                "confidence": review.confidence_score,
                "numbers_valid": review.audited_numbers_valid,
                "critique": review.critique_notes,
                "flagged_inconsistencies": review.flagged_inconsistencies,
                "llm_reasoning": skep_text,
                "token_usage": skep_usage
            }, model=skep_model, llm_used=skep_used, fallback=skep_fallback)

            if review.accepted:
                winning_hyp = top_hyp
                skeptic_review = review
                break
            else:
                last_critique = review.critique_notes

        if not winning_hyp:
            winning_hyp = hypotheses[0]
            skeptic_review = review

        # Execution Plan Phase 3.6: Escalate to human if debate unconcluded or confidence below threshold
        escalated_to_human = False
        escalation_reason = None
        if not (skeptic_review and skeptic_review.accepted) or (winning_hyp and winning_hyp.likelihood < 0.50):
            escalated_to_human = True
            conf_str = f"{skeptic_review.confidence_score:.2f}" if skeptic_review else "N/A"
            escalation_reason = (
                f"Multi-agent debate unconcluded after {rounds} rounds (Skeptic confidence: {conf_str} < 0.50). "
                f"Action pack requires manual human officer verification."
            )
            log_step("Orchestrator", "HUMAN_ESCALATION", {"reason": escalation_reason}, llm_used=False, fallback=False)

        # 4. Action Planner
        recommendations = self.action_planner.plan_actions(
            facility_id=facility_id,
            medicine_id=medicine_id,
            hypothesis=winning_hyp,
            deterministic_recon=recon["deterministic_reconciliation"],
            escalated_to_human=escalated_to_human
        )
        plan_llm = getattr(self.action_planner, "last_llm_response", None)
        plan_text = plan_llm.get("text", "") if isinstance(plan_llm, dict) else ""
        plan_usage = plan_llm.get("usage", {}) if isinstance(plan_llm, dict) else {}
        plan_model = plan_llm.get("model", self.llm_client.model) if isinstance(plan_llm, dict) else self.llm_client.model
        plan_used = plan_llm.get("llm_used", False) if isinstance(plan_llm, dict) else False
        plan_fallback = plan_llm.get("fallback", False) if isinstance(plan_llm, dict) else False
        log_step("ActionPlannerAgent", "ACTIONS_RECOMMENDED", {
            "recommendations_count": len(recommendations),
            "top_action": recommendations[0].action_type,
            "llm_reasoning": plan_text,
            "token_usage": plan_usage
        }, model=plan_model, llm_used=plan_used, fallback=plan_fallback)

        # 5. Number Auditor Verification of Action Plan
        action_plan_audit = self.skeptic.audit_action_plan(
            recommendations=recommendations,
            deterministic_recon=recon["deterministic_reconciliation"]
        )
        log_step("SkepticAgent", "ACTION_PLAN_AUDITED", {
            "passed": action_plan_audit.passed,
            "verified_count": action_plan_audit.verified_recommendations_count,
            "flagged_inconsistencies": action_plan_audit.flagged_inconsistencies
        }, llm_used=False, fallback=False)

        det_rec = recon["deterministic_reconciliation"]
        # Determine whether early warning intercepted an actual stockout risk
        is_stockout_risk = (
            det_rec["trust_shortfall"]["shortfall_units"] > 0
            or det_rec["trust_shortfall"]["gap_days"] > 0
            or det_rec["understated_gap_percent"] > 0
        )
        p_stockout = det_rec.get("monte_carlo_delivery", {}).get("p_stockout_before_arrival", 0.0)

        overall_model = getattr(self.llm_client, "last_model_used", self.llm_client.model)
        overall_llm_used = getattr(self.llm_client, "last_llm_used", False)
        overall_fallback = getattr(self.llm_client, "last_fallback", False)
        if isinstance(skep_llm, dict) and skep_llm.get("model"):
            overall_model = skep_llm["model"]
            overall_llm_used = skep_llm.get("llm_used", False)
            overall_fallback = skep_llm.get("fallback", False)

        pack = ActionPack(
            run_id=run_id,
            facility_id=facility_id,
            medicine_id=medicine_id,
            stockout_prevented=is_stockout_risk,
            days_of_cover_trust=det_rec["trust_cover_days"],
            days_of_cover_naive=det_rec["naive_cover_days"],
            understated_gap_percent=det_rec["understated_gap_percent"],
            p_stockout_risk=p_stockout,
            investigation_summary=skeptic_review.critique_notes if skeptic_review else "Investigation concluded.",
            winning_hypothesis=winning_hyp,
            recommendations=recommendations,
            skeptic_rounds=rounds,
            trace_file=trace_file,
            action_plan_audit=action_plan_audit,
            escalated_to_human=escalated_to_human,
            escalation_reason=escalation_reason,
            model_used=overall_model,
            llm_used=overall_llm_used,
            fallback=overall_fallback,
            ledger_stock=det_rec["stock_evaluation"]["ledger_stock"],
            usable_stock=det_rec["stock_evaluation"]["usable_stock"],
            quarantined_stock=det_rec["stock_evaluation"].get("quarantined_stock", 0.0),
            audit_drift=det_rec["stock_evaluation"].get("audit_drift", 0.0),
            expiring_stock=det_rec["stock_evaluation"].get("expiring_stock", 0.0)
        )

        log_step("Orchestrator", "RUN_COMPLETE", {"run_id": run_id, "status": "SUCCESS"}, llm_used=False, fallback=False)
        return pack

    def record_decision(
        self,
        facility_id: str,
        medicine_id: str,
        action_type: str,
        decision: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Records an officer's approval or rejection decision into Meterless H-MEM.
        Enforces entity existence validation and updates long-term preferences.
        """
        facility_id = str(facility_id).strip().upper()
        medicine_id = str(medicine_id).strip().upper()

        valid_facs = {f["facility_id"] for f in self.data_store.get_facilities()}
        valid_meds = {m["medicine_id"] for m in self.data_store.get_medicines()}
        if valid_facs and facility_id not in valid_facs:
            raise ValueError(f"Unrecognized facility_id '{facility_id}'. Registered facilities: {sorted(list(valid_facs))}")
        if valid_meds and medicine_id not in valid_meds:
            raise ValueError(f"Unrecognized medicine_id '{medicine_id}'. Registered medicines: {sorted(list(valid_meds))}")

        normalized_decision = decision.strip().upper()
        if normalized_decision not in ("APPROVED", "REJECTED"):
            raise ValueError(f"Invalid decision '{decision}'. Must be 'APPROVED' or 'REJECTED'.")

        action_type_clean = action_type.value if hasattr(action_type, "value") else str(action_type).replace("ActionType.", "").strip().upper()

        self.hmem.record_officer_decision(
            facility_id=facility_id,
            medicine_id=medicine_id,
            action_type=action_type_clean,
            decision=normalized_decision,
            reason=reason
        )

        pref_key = f"{facility_id}_{action_type_clean}"
        return {
            "facility_id": facility_id,
            "medicine_id": medicine_id,
            "action_type": action_type_clean,
            "decision": normalized_decision,
            "reason": reason,
            "preferences": self.hmem.long_term_beliefs["officer_action_preferences"].get(pref_key, {}),
            "all_preferences": self.hmem.long_term_beliefs["officer_action_preferences"],
            "rejected_patterns": self.hmem.long_term_beliefs["rejected_patterns"][-5:]
        }

    def triage_district(self, facility_id: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
        """
        Executes proactive district-wide inventory triage scanning via TriagePlannerAgent.
        """
        if facility_id:
            facility_id = str(facility_id).strip().upper()
        return self.triage_planner.scan_district(facility_id=facility_id, top_n=top_n)
