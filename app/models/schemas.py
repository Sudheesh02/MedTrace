"""
Data Schemas for MedTrace Multi-Agent Architecture (app/models/schemas.py)
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class AnomalyType(str, Enum):
    GHOST_STOCK = "GHOST_STOCK"
    EXPIRING_BATCH_UNUSABLE = "EXPIRING_BATCH_UNUSABLE"
    QUARANTINED_BATCH = "QUARANTINED_BATCH"
    PO_DISPATCHED_NOT_RECEIVED = "PO_DISPATCHED_NOT_RECEIVED"
    CHRONIC_SUPPLIER_SLIP = "CHRONIC_SUPPLIER_SLIP"
    DEMAND_SPIKE = "DEMAND_SPIKE"
    UOM_MISMATCH = "UOM_MISMATCH"
    GLOBAL_SHORTAGE = "GLOBAL_SHORTAGE"
    UNRECORDED_EMERGENCY_TRANSFER = "UNRECORDED_EMERGENCY_TRANSFER"
    COLD_CHAIN_TEMPERATURE_EXCURSION = "COLD_CHAIN_TEMPERATURE_EXCURSION"

class Discrepancy(BaseModel):
    discrepancy_id: str
    anomaly_type: AnomalyType
    facility_id: str
    medicine_id: str
    description: str
    impact_units: float
    sources_in_conflict: List[str]
    provenance: Dict[str, Any] = Field(default_factory=dict)

class Hypothesis(BaseModel):
    hypothesis_id: str
    title: str
    cause: str
    likelihood: float = Field(ge=0.0, le=1.0)
    supporting_evidence: List[str]
    refuting_evidence: List[str]
    confirming_query: str

class SkepticReview(BaseModel):
    accepted: bool
    confidence_score: float
    critique_notes: str
    audited_numbers_valid: bool
    flagged_inconsistencies: List[str] = Field(default_factory=list)

class ActionType(str, Enum):
    PEER_TRANSFER = "PEER_TRANSFER"
    EXPEDITE_PO = "EXPEDITE_PO"
    EMERGENCY_PURCHASE = "EMERGENCY_PURCHASE"
    BATCH_RELEASE = "BATCH_RELEASE"

class ActionRecommendation(BaseModel):
    action_id: str
    action_type: ActionType
    facility_id: str
    medicine_id: str
    recommended_units: float
    source_facility_id: Optional[str] = None
    supplier_id: Optional[str] = None
    feasibility_score: float
    justification: str
    number_provenance: Dict[str, float]

class ActionPack(BaseModel):
    run_id: str
    facility_id: str
    medicine_id: str
    stockout_prevented: bool
    days_of_cover_trust: float
    days_of_cover_naive: float
    understated_gap_percent: float
    investigation_summary: str
    winning_hypothesis: Hypothesis
    recommendations: List[ActionRecommendation]
    skeptic_rounds: int
    trace_file: str
