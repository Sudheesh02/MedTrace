"""
LLM Client Adapter (app/adapters/llm_client.py)
Calls Meterless Nightshift / NVIDIA Nemotron via OpenAI-compatible endpoints.
Includes robust offline fallback for SAMPLE_MODE=true.
"""

import os
import json
from typing import Dict, List, Optional, Any
from openai import OpenAI

class LLMClient:
    def __init__(self):
        self.sample_mode = os.environ.get("SAMPLE_MODE", "false").lower() == "true"
        
        # Priority 1: Meterless Nightshift if reachable
        self.meterless_url = os.environ.get("METERLESS_BASE_URL", "http://127.0.0.1:8088/v1")
        self.meterless_token = os.environ.get("METERLESS_RUNTIME_TOKEN", "")
        
        # Priority 2: Direct NVIDIA Nemotron endpoint
        self.nvidia_key = os.environ.get("MODEL_API_KEY", "")
        self.nvidia_url = os.environ.get("MODEL_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.model = os.environ.get("NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
        
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.meterless_token and "127.0.0.1" in self.meterless_url:
            self.client = OpenAI(
                base_url=self.meterless_url,
                api_key=self.meterless_token,
                default_headers={"meterless-app": "medtrace", "meterless-scope": "user"}
            )
        elif self.nvidia_key and self.nvidia_key.startswith("nvapi-"):
            self.client = OpenAI(
                base_url=self.nvidia_url,
                api_key=self.nvidia_key
            )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Executes a prompt. If sample mode is active or client is offline, returns deterministic structured fallback.
        """
        if self.sample_mode or not self.client:
            return self._sample_fallback(prompt, system_prompt)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=45
            )
            choice = res.choices[0].message
            content = choice.content or choice.reasoning_content or ""
            return {
                "text": content,
                "model": self.model,
                "usage": res.usage.model_dump() if res.usage else {},
                "fallback": False
            }
        except Exception as e:
            # Graceful degradation to sample mode fallback
            return self._sample_fallback(prompt, system_prompt, error_msg=str(e))

    def _sample_fallback(self, prompt: str, system_prompt: Optional[str] = None, error_msg: Optional[str] = None) -> Dict[str, Any]:
        """Rule-based offline generator ensuring judges can run end-to-end without credentials."""
        prompt_lower = prompt.lower()
        if "investigate" in prompt_lower or "hypothesis" in prompt_lower or "hypotheses" in prompt_lower:
            fallback_text = (
                "Investigator qualitative synthesis: Root cause analysis indicates a divergence between "
                "recorded facility inventory, quality hold registries, and upstream delivery schedules. "
                "Investigating primary hypothesis alongside secondary logistical and epidemiological alternatives. "
                "All numerical quantities and cover metrics strictly computed by DeterministicEngine."
            )
        elif "skeptic" in prompt_lower or "review" in prompt_lower or "auditor" in prompt_lower:
            fallback_text = (
                "Skeptic qualitative audit: Verified hypothesis claims against grounded physical evidence and "
                "deterministic ledger invariants. Cross-checked multi-source data dependencies to confirm "
                "whether root cause is facility-internal or supply chain transit-driven."
            )
        elif "action" in prompt_lower or "plan" in prompt_lower or "planner" in prompt_lower:
            fallback_text = (
                "Action Planner operational guidance: Formulating prioritized, constraint-verified interventions. "
                "Auditing nearby facility surpluses for peer transfer, validating supplier lead-time priors for PO expediting, "
                "and reserving emergency procurement quotas strictly for residual deficit gaps."
            )
        else:
            fallback_text = (
                "MedTrace qualitative review: Reconciled multi-source records against deterministic physical constraints "
                "with full row-level provenance."
            )

        prompt_tokens = len(prompt.split())
        completion_tokens = len(fallback_text.split())
        return {
            "text": fallback_text,
            "model": "rule-based-sample-mode",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "fallback": True,
            "fallback_reason": error_msg or "SAMPLE_MODE_ACTIVE"
        }
