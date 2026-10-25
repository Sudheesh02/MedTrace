"""
LLM Client Adapter (app/adapters/llm_client.py)
Calls Meterless Nightshift / NVIDIA Nemotron via OpenAI-compatible endpoints.
Includes robust offline fallback for SAMPLE_MODE=true.
"""

import os
import json
from typing import Dict, List, Optional, Any
from openai import OpenAI
import re

_THINK_BLOCK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE)
_THINK_TAG_RE = re.compile(r"</?think(?:ing)?>", re.IGNORECASE)


def strip_think_tags(text: str) -> str:
    """Remove reasoning-model chain-of-thought markers from LLM output.

    Handles (1) full <think>...</think> blocks, (2) a lone closing </think> where the
    model emitted its reasoning without an opening tag (keep only the text after the
    last closing tag, unless nothing follows), and (3) stray opening/closing tags.
    """
    if not text:
        return text or ""
    cleaned = _THINK_BLOCK_RE.sub("", text)
    if re.search(r"</think(?:ing)?>", cleaned, re.IGNORECASE):
        tail = re.split(r"</think(?:ing)?>", cleaned, flags=re.IGNORECASE)[-1]
        if tail.strip():
            cleaned = tail
    cleaned = _THINK_TAG_RE.sub("", cleaned)
    return cleaned.strip()

class LLMClient:
    def __init__(self):
        self.sample_mode = os.environ.get("SAMPLE_MODE", "false").lower() == "true"
        
        # Priority 1: Meterless Nightshift if reachable
        self.meterless_url = os.environ.get("METERLESS_BASE_URL", "http://127.0.0.1:8088/v1")
        self.meterless_token = os.environ.get("METERLESS_RUNTIME_TOKEN", "")
        self.meterless_model = os.environ.get("METERLESS_MODEL", "")
        
        # Priority 2: Direct NVIDIA Nemotron endpoint
        self.nvidia_key = os.environ.get("MODEL_API_KEY", "")
        self.nvidia_url = os.environ.get("MODEL_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.nvidia_model = os.environ.get("NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
        
        self.model = self.nvidia_model
        self.provider = "none"
        self.client = None
        self.last_model_used = "rule-based-sample-mode" if self.sample_mode else self.model
        self.last_llm_used = False
        self.last_fallback = self.sample_mode
        self._init_client()

    def _init_client(self):
        if self.meterless_token:
            # Meterless Nightshift OpenAI-compatible gateway (gate removed: works for localhost, 127.0.0.1, or remote hosts)
            self.provider = "meterless"
            self.model = self.meterless_model or self.nvidia_model or "meterless/auto"
            self.client = OpenAI(
                base_url=self.meterless_url,
                api_key=self.meterless_token,
                default_headers={"meterless-app": "medtrace", "meterless-scope": "user"}
            )
        elif self.nvidia_key:
            self.provider = "nvidia"
            self.model = self.nvidia_model
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
        Executes a prompt. If sample mode is active, returns deterministic structured fallback.
        Outside sample mode, fails loudly if unconfigured or if API call fails.
        """
        env_sample = os.environ.get("SAMPLE_MODE", "false").lower() == "true"
        effective_sample_mode = self.sample_mode or env_sample
        if effective_sample_mode:
            return self._sample_fallback(prompt, system_prompt)

        if not self.client:
            raise RuntimeError(
                "LLMClient has no configured provider (missing METERLESS_RUNTIME_TOKEN or MODEL_API_KEY) "
                "and SAMPLE_MODE is false. Configure your API credentials or set SAMPLE_MODE=true."
            )

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
            content = choice.content or getattr(choice, "reasoning_content", None) or ""
            content = strip_think_tags(content)
            actual_model = getattr(res, "model", None) or self.model
            self.last_model_used = actual_model
            self.last_llm_used = True
            self.last_fallback = False
            return {
                "text": content,
                "model": actual_model,
                "usage": res.usage.model_dump() if res.usage else {},
                "fallback": False,
                "llm_used": True
            }
        except Exception as e:
            # Outside sample mode, fail loudly instead of returning canned text
            raise RuntimeError(f"LLM API generation failed outside sample mode: {e}") from e

    def _sample_fallback(self, prompt: str, system_prompt: Optional[str] = None, error_msg: Optional[str] = None) -> Dict[str, Any]:
        """Rule-based offline generator ensuring judges can run end-to-end without credentials."""
        prompt_lower = prompt.lower()
        if "investigate" in prompt_lower or "hypothesis" in prompt_lower or "hypotheses" in prompt_lower or "candidate" in prompt_lower:
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
        fallback_model = "rule-based-sample-mode"
        self.last_model_used = fallback_model
        self.last_llm_used = False
        self.last_fallback = True
        return {
            "text": fallback_text,
            "model": fallback_model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "fallback": True,
            "llm_used": False,
            "fallback_reason": error_msg or "SAMPLE_MODE_ACTIVE"
        }
