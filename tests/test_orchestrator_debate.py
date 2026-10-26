"""Orchestrator debate loop: winner selection when the Skeptic never accepts, and escalation reasons."""
from unittest.mock import MagicMock

import pytest

from app.models.schemas import ActionPlanAudit, Hypothesis, SkepticReview
from app.orchestrator import MedTraceOrchestrator


def _hyp(hid, likelihood):
    return Hypothesis(
        hypothesis_id=hid, title=f"Title {hid}", cause=f"Cause {hid}", likelihood=likelihood,
        supporting_evidence=[], refuting_evidence=[], confirming_query="SELECT 1",
    )


def _review(accepted, confidence=0.8):
    return SkepticReview(
        accepted=accepted, confidence_score=confidence, critique_notes="notes",
        audited_numbers_valid=True, flagged_inconsistencies=[],
    )


def _orch(hypotheses, skeptic_results, logs_dir):
    orch = MedTraceOrchestrator(use_zetaris=False, logs_dir=str(logs_dir))
    orch.investigator = MagicMock()
    orch.investigator.investigate.return_value = hypotheses
    skeptic = MagicMock()
    skeptic.review_and_audit.side_effect = skeptic_results
    skeptic.audit_action_plan.return_value = ActionPlanAudit(
        audited=True, passed=True, verified_recommendations_count=1, flagged_inconsistencies=[]
    )
    orch.skeptic = skeptic
    return orch


def test_unconcluded_debate_falls_back_to_skeptic_top_hypothesis_not_first_listed(tmp_path):
    """Regression: after 3 rejected rounds the winner used to be hypotheses[0] (investigator's listing order)."""
    weak, strong = _hyp("H-WEAK", 0.30), _hyp("H-STRONG", 0.65)
    # Investigator lists the weak one first; the Skeptic ranks the strong one on top but never accepts.
    orch = _orch([weak, strong], [(strong, _review(False, 0.6))] * 3, tmp_path)
    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")
    assert pack.skeptic_rounds == 3
    assert pack.winning_hypothesis.hypothesis_id == "H-STRONG"
    assert pack.escalated_to_human is True


def test_escalation_reason_for_unconcluded_debate_reports_rounds_and_real_confidence(tmp_path):
    top = _hyp("H-A", 0.80)
    orch = _orch([top], [(top, _review(False, 0.72))] * 3, tmp_path)
    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")
    reason = pack.escalation_reason
    assert "unconcluded after 3 rounds" in reason
    assert "0.72" in reason                      # the actual confidence, not a hard-coded "< 0.50"
    assert "< 0.50" not in reason
    assert "manual human officer verification" in reason


def test_escalation_reason_for_low_likelihood_after_accepted_review_does_not_claim_unconcluded(tmp_path):
    """Regression: an accepted review with a low-likelihood winner was reported as 'debate unconcluded'."""
    top = _hyp("H-LOW", 0.40)
    orch = _orch([top], [(top, _review(True, 0.90))], tmp_path)
    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")
    assert pack.skeptic_rounds == 1
    assert pack.escalated_to_human is True
    reason = pack.escalation_reason
    assert "unconcluded" not in reason
    assert "0.40" in reason and "0.50" in reason
    assert "manual human officer verification" in reason


def test_no_escalation_when_accepted_with_adequate_likelihood(tmp_path):
    top = _hyp("H-OK", 0.75)
    orch = _orch([top], [(top, _review(True, 0.90))], tmp_path)
    pack = orch.run_investigation(facility_id="FAC-DH-01", medicine_id="MED-007")
    assert pack.escalated_to_human is False
    assert pack.escalation_reason is None
    assert pack.winning_hypothesis.hypothesis_id == "H-OK"
