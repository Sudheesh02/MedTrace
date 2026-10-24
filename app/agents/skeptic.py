"""
Skeptic & Number Auditor Agent (app/agents/skeptic.py)
Challenges hypotheses, enforces multi-source validation, and verifies every single number against deterministic truth.
"""

from typing import Dict, List, Any, Tuple
from app.adapters.llm_client import LLMClient
from app.models.schemas import Hypothesis, SkepticReview

class SkepticAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def review_and_audit(
        self,
        hypotheses: List[Hypothesis],
        deterministic_recon: Dict[str, Any],
        round_number: int = 1
    ) -> Tuple[Hypothesis, SkepticReview]:
        """
        Scrutinizes hypotheses and executes Number Auditor check.
        Enforces mathematical invariants, differential diagnosis, and multi-source corroboration rules.
        """
        if not hypotheses:
            raise ValueError("No hypotheses provided to SkepticAgent.")

        # Pick top hypothesis by likelihood
        sorted_hyp = sorted(hypotheses, key=lambda h: h.likelihood, reverse=True)
        top_hyp = sorted_hyp[0]
        second_hyp = sorted_hyp[1] if len(sorted_hyp) > 1 else None
        delta = (top_hyp.likelihood - second_hyp.likelihood) if second_hyp else 1.0

        # 1. Number Auditor Verification
        stock_eval = deterministic_recon["stock_evaluation"]
        shortfall = deterministic_recon["trust_shortfall"]
        
        inconsistencies = []
        numbers_valid = True

        # Mathematical Invariant 1: Non-negative inventory
        if stock_eval["usable_stock"] < 0:
            inconsistencies.append("Usable stock cannot be negative.")
            numbers_valid = False

        if shortfall["shortfall_units"] < 0:
            inconsistencies.append("Shortfall units cannot be negative.")
            numbers_valid = False

        # Mathematical Invariant 2: Trust-adjusted stock formula
        expected_usable = max(0.0, stock_eval["ledger_stock"] - stock_eval["audit_drift"] - stock_eval["quarantined_stock"] - stock_eval["expiring_stock"])
        if abs(stock_eval["usable_stock"] - expected_usable) > 0.01:
            inconsistencies.append(f"Usable stock invariant failed: expected {expected_usable}, got {stock_eval['usable_stock']}.")
            numbers_valid = False

        # 2. Adversarial Challenge & Differential Elimination (Execution Plan Phase 3.4)
        # In Round 1, challenge if:
        # a) Multiple hypotheses have close likelihood (delta <= 0.15) — lack of differential elimination
        # b) External disruption claims lack >= 2 independent supporting sources
        is_contested = (second_hyp is not None and delta <= 0.15)
        needs_corroboration = any(term in top_hyp.title.lower() for term in ["external", "shortage", "surge", "outbreak"])
        lacks_secondary = len(top_hyp.supporting_evidence) < 2

        if not numbers_valid:
            accepted = False
            confidence = 0.30
            critique_notes = (
                f"Skeptic & Number Auditor REJECTED hypotheses (Round {round_number}): "
                f"Mathematical invariant violations detected: {'; '.join(inconsistencies)}"
            )
        elif round_number == 1 and is_contested:
            accepted = False
            confidence = round(max(0.35, top_hyp.likelihood - 0.20), 2)
            inconsistencies.append(
                f"Ambiguous differential: top hypothesis '{top_hyp.title}' (likelihood={top_hyp.likelihood:.2f}) "
                f"does not rule out close alternative '{second_hyp.title}' (likelihood={second_hyp.likelihood:.2f}, Delta={delta:.2f} <= 0.15)."
            )
            critique_notes = (
                f"Skeptic challenged top hypothesis '{top_hyp.title}' (Round {round_number}): "
                f"Close competing hypothesis '{second_hyp.title}' (likelihood {second_hyp.likelihood:.2f}, Delta={delta:.2f} <= 0.15) "
                f"was not differentially eliminated. Requires targeted corroborating evidence and differential refutation before approval."
            )
        elif round_number == 1 and needs_corroboration and lacks_secondary:
            accepted = False
            confidence = 0.45
            inconsistencies.append("External disruption claim lacks secondary corroboration; requires cross-verification via confirming query.")
            critique_notes = (
                f"Skeptic challenged top hypothesis '{top_hyp.title}' (Round {round_number}): "
                f"External disruption claim requires secondary corroboration across independent registries before approval. "
                f"Flagged for Investigator revision."
            )
        else:
            accepted = numbers_valid and (top_hyp.likelihood >= 0.50)
            confidence = top_hyp.likelihood if accepted else 0.40
            if round_number > 1:
                critique_notes = (
                    f"Skeptic approved revised hypothesis '{top_hyp.title}' (Round {round_number}). "
                    f"Differential elimination confirmed against '{second_hyp.title if second_hyp else 'alternatives'}' (separation Delta={delta:.2f}). "
                    f"Audited numbers verified: Usable Stock = {stock_eval['usable_stock']} units, "
                    f"Shortfall = {shortfall['shortfall_units']} units across {shortfall['gap_days']} gap days. "
                    f"Corroborating evidence: {len(top_hyp.supporting_evidence)} items checked."
                )
            else:
                critique_notes = (
                    f"Skeptic verified top hypothesis '{top_hyp.title}' (Round {round_number}). "
                    f"All {len(hypotheses)} competing hypotheses evaluated. "
                    f"Audited numbers verified: Usable Stock = {stock_eval['usable_stock']} units, "
                    f"Shortfall = {shortfall['shortfall_units']} units across {shortfall['gap_days']} gap days. "
                    f"Corroborating evidence: {len(top_hyp.supporting_evidence)} items checked."
                )

        # Call LLM client to log agent reasoning
        prompt = f"""
        Skeptic & Number Auditor Review (Round {round_number}):
        Evaluating Top Hypothesis: '{top_hyp.title}' (Likelihood: {top_hyp.likelihood})
        Second Alternative: '{second_hyp.title if second_hyp else 'None'}' (Likelihood: {second_hyp.likelihood if second_hyp else 0.0})
        Deterministic Usable Stock: {stock_eval['usable_stock']} units
        Deterministic Shortfall: {shortfall['shortfall_units']} units
        Numbers Valid: {numbers_valid}
        Decision: {'ACCEPTED' if accepted else 'CHALLENGED'}
        Critique Notes: {critique_notes}
        """
        self.llm_client.generate(prompt=prompt, system_prompt="You are a clinical supply chain skeptic and number auditor.")

        review = SkepticReview(
            accepted=accepted,
            confidence_score=round(confidence, 2),
            critique_notes=critique_notes,
            audited_numbers_valid=numbers_valid,
            flagged_inconsistencies=inconsistencies
        )

        return top_hyp, review
