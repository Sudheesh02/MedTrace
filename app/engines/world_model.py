"""
Meterless World Model Agent Engine (Headless Shared World State)
Adapted from reference architecture in meterless-repo/engines/world-model/
Maintains shared, queryable, idempotent state across multi-agent turns with stable IDs and provenance.
"""

import hashlib
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

class WorldStoreService:
    def __init__(self):
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.snapshots: List[Dict[str, Any]] = []

    @staticmethod
    def derive_stable_id(prefix: str, content: str) -> str:
        """Hash-based stable ID ensures all agents agree on identity without coordination."""
        normalized = content.lower().strip()
        h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{h}"

    def write_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any], agent_id: str = "system") -> Dict[str, Any]:
        existing = self.entities.get(entity_id, {})
        merged = {**existing, **properties}
        merged["id"] = entity_id
        merged["type"] = entity_type
        merged["last_updated_by"] = agent_id
        merged["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.entities[entity_id] = merged
        return merged

    def write_edge(self, from_id: str, to_id: str, relation: str, properties: Optional[Dict[str, Any]] = None, agent_id: str = "system"):
        edge = {
            "from": from_id,
            "to": to_id,
            "relation": relation,
            "properties": properties or {},
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.edges.append(edge)

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self.entities.get(entity_id)

    def get_edges_for(self, entity_id: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        return [
            e for e in self.edges
            if (e["from"] == entity_id or e["to"] == entity_id) and (relation is None or e["relation"] == relation)
        ]

class IngestPipelineService:
    def __init__(self, store: WorldStoreService):
        self.store = store

    def ingest_facility_item(self, facility: Dict[str, Any], medicine: Dict[str, Any], stock_info: Dict[str, Any], agent_id: str = "reconciler") -> str:
        # Stable entity IDs
        fac_id = facility.get("facility_id", "FAC_UNKNOWN")
        med_id = medicine.get("medicine_id", "MED_UNKNOWN")
        inv_id = WorldStoreService.derive_stable_id("ent_inv", f"{fac_id}_{med_id}")

        self.store.write_entity(
            entity_id=fac_id,
            entity_type="Facility",
            properties=facility,
            agent_id=agent_id
        )
        self.store.write_entity(
            entity_id=med_id,
            entity_type="Medicine",
            properties=medicine,
            agent_id=agent_id
        )
        self.store.write_entity(
            entity_id=inv_id,
            entity_type="InventoryState",
            properties={
                "facility_id": fac_id,
                "medicine_id": med_id,
                **stock_info
            },
            agent_id=agent_id
        )

        self.store.write_edge(fac_id, inv_id, "HOLDS_INVENTORY", agent_id=agent_id)
        self.store.write_edge(inv_id, med_id, "FOR_MEDICINE", agent_id=agent_id)
        return inv_id

class ContextBuilderService:
    def __init__(self, store: WorldStoreService):
        self.store = store

    def build_structured_context(self, facility_id: str, medicine_id: str) -> Dict[str, Any]:
        inv_id = WorldStoreService.derive_stable_id("ent_inv", f"{facility_id}_{medicine_id}")
        inv_entity = self.store.get_entity(inv_id) or {}
        fac_entity = self.store.get_entity(facility_id) or {}
        med_entity = self.store.get_entity(medicine_id) or {}
        edges = self.store.get_edges_for(inv_id)

        return {
            "facility": fac_entity,
            "medicine": med_entity,
            "inventory_state": inv_entity,
            "relationships": edges,
            "canon_hash": hashlib.md5(json.dumps(inv_entity, sort_keys=True).encode("utf-8")).hexdigest()
        }
