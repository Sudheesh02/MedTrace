"""
Meterless H-MEM Agent Engine (Headless Hierarchical Memory)
Adapted from reference architecture in meterless-repo/engines/hmem/
Persists officer approvals, rejections, overrides, and supplier reliability beliefs across sessions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import logging
import os
import tempfile
import time

logger = logging.getLogger(__name__)

class HMemEngine:
    def __init__(self, persistence_file: Optional[str] = "logs/hmem_store.json"):
        # MEDTRACE_HMEM_FILE lets tests / sandboxes redirect the default store so they never pollute real officer memory.
        if persistence_file == "logs/hmem_store.json" and os.environ.get("MEDTRACE_HMEM_FILE"):
            persistence_file = os.environ["MEDTRACE_HMEM_FILE"]
        self.persistence_file = persistence_file
        self.working_memory: List[Dict[str, Any]] = []
        self.episodic_memory: List[Dict[str, Any]] = []
        self.long_term_beliefs: Dict[str, Any] = {
            "supplier_delays": {},
            "officer_action_preferences": {},
            "rejected_patterns": []
        }
        self._load()

    def _load(self):
        if not (self.persistence_file and os.path.exists(self.persistence_file)):
            return
        try:
            with open(self.persistence_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("H-MEM store root is not a JSON object")
            self.episodic_memory = data.get("episodic_memory", [])
            self.long_term_beliefs = data.get("long_term_beliefs", self.long_term_beliefs)
        except Exception as exc:
            # Never silently discard officer memory: keep the unreadable file for recovery, say so, start empty.
            backup = f"{self.persistence_file}.corrupt-{int(time.time())}"
            try:
                os.replace(self.persistence_file, backup)
                kept = f"preserved as {backup}"
            except OSError:
                kept = "could not be preserved"
            logger.warning("H-MEM store %s is corrupt or unreadable (%s); starting with empty memory; file %s",
                           self.persistence_file, exc, kept)
            self.episodic_memory = []

    def _save(self):
        """Atomic write: dump to a temp file in the same directory, then os.replace over the real store."""
        if not self.persistence_file:
            return
        directory = os.path.dirname(os.path.abspath(self.persistence_file))
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".hmem-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({
                    "episodic_memory": self.episodic_memory[-50:],
                    "long_term_beliefs": self.long_term_beliefs
                }, f, indent=2)
            os.replace(tmp_path, self.persistence_file)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def record_officer_decision(
        self,
        facility_id: str,
        medicine_id: str,
        action_type: str,
        decision: str,  # "APPROVED" or "REJECTED"
        reason: str
    ):
        episode = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "facility_id": facility_id,
            "medicine_id": medicine_id,
            "action_type": action_type,
            "decision": decision,
            "reason": reason
        }
        self.episodic_memory.append(episode)
        
        # Distill into long-term memory with deterministic contradiction resolution
        pref_key = f"{facility_id}_{action_type}"
        prefs = self.long_term_beliefs["officer_action_preferences"].get(pref_key, {"approved": 0, "rejected": 0})
        if decision == "APPROVED":
            prefs["approved"] += 1
            # Contradiction Resolution: Overturn prior rejection penalties for this action
            if prefs.get("rejected", 0) > 0:
                prefs["rejected"] = max(0, prefs["rejected"] - 1)
            # Remove matching rejection patterns from active memory
            pat_prefix = f"{action_type} on {medicine_id}"
            self.long_term_beliefs["rejected_patterns"] = [
                p for p in self.long_term_beliefs["rejected_patterns"]
                if not p.startswith(pat_prefix)
            ]
        else:
            prefs["rejected"] += 1
            self.long_term_beliefs["rejected_patterns"].append(f"{action_type} on {medicine_id}: {reason}")
        self.long_term_beliefs["officer_action_preferences"][pref_key] = prefs
        self._save()

    def record_supplier_delay(
        self,
        supplier_id: str,
        p90_delay_days: float,
        reason: str
    ):
        """
        Records a learned empirical supplier delivery delay prior into long-term beliefs.
        Enables cross-session cognitive memory to adjust downstream reconciliation and action planning.
        """
        self.long_term_beliefs["supplier_delays"][supplier_id] = {
            "p90_delay_days": float(p90_delay_days),
            "reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self._save()

    def get_supplier_delay(self, supplier_id: str) -> Optional[float]:
        """Retrieves learned p90 delay days for a supplier if recorded in long-term beliefs."""
        info = self.long_term_beliefs.get("supplier_delays", {}).get(supplier_id)
        if isinstance(info, dict):
            return info.get("p90_delay_days")
        elif isinstance(info, (int, float)):
            return float(info)
        return None

    def get_supplier_delay_info(self, supplier_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full learned delay belief record (delay, reason, updated_at)."""
        info = self.long_term_beliefs.get("supplier_delays", {}).get(supplier_id)
        if isinstance(info, dict):
            return info
        elif isinstance(info, (int, float)):
            return {"p90_delay_days": float(info), "reason": "Empirical observation"}
        return None

    def get_relevant_memories(self, facility_id: str, medicine_id: str) -> Dict[str, Any]:
        """Retrieves top memories for context injection into Action Planner."""
        relevant_episodes = [
            e for e in reversed(self.episodic_memory)
            if e.get("facility_id") == facility_id or e.get("medicine_id") == medicine_id
        ][:5]

        return {
            "past_episodes": relevant_episodes,
            "officer_preferences": self.long_term_beliefs["officer_action_preferences"],
            "rejected_patterns": self.long_term_beliefs["rejected_patterns"][-5:],
            "supplier_delays": self.long_term_beliefs.get("supplier_delays", {})
        }
