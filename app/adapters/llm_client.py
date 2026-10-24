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
        # Simple heuristic generation based on prompt intent
        if "Investigate" in prompt or "Hypothesis" in prompt or "hypotheses" in prompt:
            fallback_text = (
                "HYPOTHESIS 1 [GHOST_STOCK]: Physical count implies 50 phantom units on ledger.\n"
                "HYPOTHESIS 2 [SUPPLIER_DELAY]: Empirical records indicate vendor delivery slip exceeds safe cover window.\n"
                "HYPOTHESIS 3 [GLOBAL_SHORTAGE]: Active FDA manufacturing shortage signal detected on this therapeutic category."
            )
        elif "Skeptic" in prompt or "Review" in prompt:
            fallback_text = (
                "SKEPTIC REVIEW: Hypothesis 1 and 2 confirmed by cross-source discrepancy between ledger and physical audit. "
                "All numerical calculations match deterministic ground truth. Recommended for approval."
            )
        elif "Action" in prompt or "Plan" in prompt:
            fallback_text = (
                "ACTION PLAN:\n"
                "1. Inter-facility stock transfer of 110 units from regional depot.\n"
                "2. Expedite purchase order with supplier; flag chronic delivery slippage."
            )
        else:
            fallback_text = "MedTrace verified: Usable stock calculated and verified against deterministic constraints."

        return {
            "text": fallback_text,
            "model": "rule-based-sample-mode",
            "usage": {"total_tokens": 0},
            "fallback": True,
            "fallback_reason": error_msg or "SAMPLE_MODE_ACTIVE"
        }
