"""
Central AI routing layer for AIOS/Pulse.

All AI calls in the system go through AIRouter. Never call Ollama, Kimi K2,
or Claude directly — always use this class.

Sensitive tasks (grievances, member data, negotiation strategy) are ALWAYS
routed to Ollama locally. A last-resort sanitizer blocks PII patterns from
ever reaching external APIs.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

import anthropic
import httpx
import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII / sensitive-data patterns — used by the sanitizer as a last-resort
# safety net before any external API call.
# ---------------------------------------------------------------------------
_SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\d{3}-\d{2}-\d{4}"),                          # SSN
    re.compile(r"#\d{2}-\d{3,4}"),                              # Grievance case numbers (##-###)
    re.compile(r"\bGRV[-/]\d{4,}", re.IGNORECASE),              # Alternate grievance ID formats
    re.compile(r"member[_\s]?id[:\s]+\w+", re.IGNORECASE),     # Member IDs
    re.compile(r"\bBAD\d{5,}\b"),                               # Badge/employee numbers
    re.compile(r"dues[_\s]?account[:\s]+\w+", re.IGNORECASE),  # Dues account references
    re.compile(                                                  # Phone numbers
        r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"
    ),
    re.compile(                                                  # Email + grievance/discipline keywords
        r"[\w.-]+@[\w.-]+\.\w+"                                 # email address
        r"(?=[\s\S]{0,200}"                                     # lookahead within 200 chars
        r"(?:grievance|discipline|termination|arbitration"       # sensitive keywords
        r"|negotiation|dues|bargaining|executive.session))",
        re.IGNORECASE,
    ),
]


class AIResponse(BaseModel):
    """Structured response returned by every AIRouter.complete() call."""

    text: str
    model_used: str
    task_type: str
    routed_to: str          # "ollama" | "kimi_k2" | "claude"
    fallback_used: bool = False


class AIRouter:
    """
    Central AI routing layer. All AI calls in the system go through here.
    Never call Ollama, Kimi, or Claude directly — always use this class.
    """

    def __init__(self, config_path: str = "config/ai-routing.yaml"):
        path = Path(config_path)
        if not path.is_absolute():
            # Resolve relative to project root (one level up from integrations/)
            path = Path(__file__).resolve().parents[2] / config_path
        with open(path) as f:
            self.config = yaml.safe_load(f)
        self._resolve_env_vars()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self,
        task: str,
        prompt: str,
        context: Optional[dict] = None,
        force_local: bool = False,
    ) -> AIResponse:
        """
        Route a completion request to the appropriate model.

        Args:
            task: Task type key from ai-routing.yaml routing table.
            prompt: The full prompt to send.
            context: Optional additional context (logged but not sent to
                     external APIs if sensitive).
            force_local: Override routing and force Ollama regardless of config.

        Raises:
            ValueError: If task type is unknown.
            RuntimeError: If sensitive task has no available local model, or
                          if no model is available after fallback attempts.
        """
        routing = self._get_routing(task)
        sensitive = routing["sensitive"]
        preferred_model = routing["model"]
        fallback_model = routing.get("fallback")
        fallback_used = False

        # Decide target model ------------------------------------------------
        if force_local or sensitive:
            target = "ollama"
        else:
            target = preferred_model

        # Check preferred model availability ----------------------------------
        if not self._model_available(target):
            if sensitive or force_local:
                raise RuntimeError(
                    f"Task '{task}' contains sensitive data and cannot be "
                    f"routed externally. Ollama must be running. "
                    f"Check: curl localhost:11434/api/version"
                )
            if fallback_model and self._model_available(fallback_model):
                target = fallback_model
                fallback_used = True
            else:
                raise RuntimeError(
                    f"No available model for task '{task}'. "
                    f"Preferred model '{preferred_model}' is unavailable "
                    f"and fallback '{fallback_model}' is also unavailable."
                )

        # Sanitizer — last-resort safety net before external calls ------------
        if target != "ollama" and self._contains_sensitive_data(prompt):
            logger.warning(
                "Sanitizer triggered: task=%s target=%s — "
                "overriding to ollama (sensitive data detected in prompt)",
                task,
                target,
            )
            if not self._model_available("ollama"):
                raise RuntimeError(
                    f"Sanitizer detected sensitive data in prompt for task "
                    f"'{task}' but Ollama is unavailable. Cannot route "
                    f"externally. Check: curl localhost:11434/api/version"
                )
            target = "ollama"
            fallback_used = True

        # Log routing decision (never log prompt content) ---------------------
        logger.info(
            "AI routing: task=%s model=%s sensitive=%s fallback=%s",
            task,
            target,
            sensitive,
            fallback_used,
        )

        # Dispatch to model ---------------------------------------------------
        dispatch = {
            "ollama": self._call_ollama,
            "kimi_k2": self._call_kimi_k2,
            "claude": self._call_claude,
        }
        caller = dispatch.get(target)
        if caller is None:
            raise RuntimeError(f"Unknown model target: {target}")

        t0 = time.monotonic()
        try:
            text = await caller(prompt, task)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "AI call succeeded: task=%s routed_to=%s duration_ms=%d fallback=%s",
                task,
                target,
                elapsed_ms,
                fallback_used,
            )
        except Exception:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            logger.error(
                "AI call failed: task=%s routed_to=%s duration_ms=%d",
                task,
                target,
                elapsed_ms,
            )
            raise

        model_name = self.config["models"][target].get("model", target)

        return AIResponse(
            text=text,
            model_used=model_name,
            task_type=task,
            routed_to=target,
            fallback_used=fallback_used,
        )

    async def health(self) -> dict[str, str]:
        """
        Check status of each configured model endpoint.

        Returns dict like:
            {"ollama": "ok|error", "kimi_k2": "ok|disabled|error", ...}
        """
        statuses: dict[str, str] = {}

        # Ollama — always expected to be enabled
        ollama_cfg = self.config["models"]["ollama"]
        base_url = ollama_cfg.get("base_url") or "http://localhost:11434"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{base_url}/api/version")
                statuses["ollama"] = "ok" if resp.status_code == 200 else "error"
        except Exception:
            statuses["ollama"] = "error"

        # Kimi K2
        kimi_cfg = self.config["models"]["kimi_k2"]
        if not kimi_cfg.get("enabled", False):
            statuses["kimi_k2"] = "disabled"
        else:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        kimi_cfg["base_url"] + "/models",
                        headers={"Authorization": f"Bearer {kimi_cfg.get('api_key', '')}"},
                    )
                    statuses["kimi_k2"] = "ok" if resp.status_code == 200 else "error"
            except Exception:
                statuses["kimi_k2"] = "error"

        # Claude
        claude_cfg = self.config["models"]["claude"]
        if not claude_cfg.get("enabled", False):
            statuses["claude"] = "disabled"
        else:
            try:
                client = anthropic.Anthropic(api_key=claude_cfg.get("api_key", ""))
                # Lightweight call to validate credentials
                client.models.list(limit=1)
                statuses["claude"] = "ok"
            except Exception:
                statuses["claude"] = "error"

        return statuses

    # ------------------------------------------------------------------
    # Model callers
    # ------------------------------------------------------------------

    async def _call_ollama(self, prompt: str, task: str) -> str:
        """POST to Ollama /api/generate, return response text."""
        cfg = self.config["models"]["ollama"]
        base_url = cfg.get("base_url") or "http://localhost:11434"
        model = cfg.get("model") or "llama3.1:8b"
        timeout = cfg.get("timeout_seconds") or 120

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json()["response"]

    async def _call_kimi_k2(self, prompt: str, task: str) -> str:
        """POST to NVIDIA NIM API with Kimi K2 model, return response text."""
        cfg = self.config["models"]["kimi_k2"]
        base_url = cfg["base_url"]
        model = cfg["model"]
        api_key = cfg.get("api_key", "")
        timeout = cfg.get("timeout_seconds", 60)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def _call_claude(self, prompt: str, task: str) -> str:
        """Call Anthropic Claude API, return response text."""
        cfg = self.config["models"]["claude"]
        api_key = cfg.get("api_key") or ""
        model = cfg.get("model") or "claude-sonnet-4-6"
        timeout = cfg.get("timeout_seconds") or 60

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
        )
        return message.content[0].text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_sensitive(self, task: str) -> bool:
        """Return True if task must never leave local processing."""
        routing = self._get_routing(task)
        return routing["sensitive"]

    def _get_routing(self, task: str) -> dict:
        """Return routing config for a task, raise ValueError if unknown."""
        routing_table = self.config.get("routing", {})
        if task not in routing_table:
            raise ValueError(
                f"Unknown task type: '{task}'. "
                f"Valid task types: {', '.join(sorted(routing_table.keys()))}"
            )
        return routing_table[task]

    def _model_available(self, model_name: str) -> bool:
        """Check if a model is configured and enabled."""
        model_cfg = self.config.get("models", {}).get(model_name)
        if model_cfg is None:
            return False
        if not model_cfg.get("enabled", False):
            return False
        # For API-key-gated models, key must be present
        if "api_key" in model_cfg and not model_cfg["api_key"]:
            return False
        return True

    def _contains_sensitive_data(self, text: str) -> bool:
        """Scan text for PII/sensitive patterns. Last-resort safety net."""
        for pattern in _SENSITIVE_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _resolve_env_vars(self) -> None:
        """Replace ${VAR} placeholders in config with actual env values."""
        self.config = self._resolve_node(self.config)

    def _resolve_node(self, node: Any) -> Any:
        """Recursively resolve ${VAR} placeholders in config values."""
        if isinstance(node, str):
            return self._resolve_string(node)
        if isinstance(node, dict):
            return {k: self._resolve_node(v) for k, v in node.items()}
        if isinstance(node, list):
            return [self._resolve_node(item) for item in node]
        return node

    @staticmethod
    def _resolve_string(value: str) -> Any:
        """
        Resolve a single string value containing ${VAR} placeholders.

        - If the entire string is a single ${VAR}, return the resolved value
          with type coercion (booleans). Unset variables resolve to an empty
          string so string-typed config fields remain valid.
        - If ${VAR} is embedded in a larger string, substitute in-place.
        """
        pattern = re.compile(r"\$\{([^}]+)\}")

        # Full-string match — apply type coercion
        full_match = pattern.fullmatch(value)
        if full_match:
            env_val = os.environ.get(full_match.group(1), "")
            if env_val == "":
                return ""
            if env_val.lower() in ("true", "1", "yes"):
                return True
            if env_val.lower() in ("false", "0", "no"):
                return False
            return env_val

        # Partial substitution — keep as string
        def _replace(m: re.Match) -> str:
            return os.environ.get(m.group(1), "")

        return pattern.sub(_replace, value)
