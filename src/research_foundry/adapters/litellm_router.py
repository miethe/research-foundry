"""LiteLLM router adapter — model-profile routing (spec §13, §8.2).

Exposes :meth:`route` which maps a model-profile name (e.g. ``rf_extract_cheap``)
to a concrete ``{provider, model, ...}`` decision by reading
``config/model_profiles.yaml`` and the environment. In the default environment
``litellm`` is not installed and no provider keys are present, so:

* :meth:`available` is False, and
* :meth:`route` deterministically returns the profile's first ``preferred``
  entry (degraded, no live completion).

Real mode (when ``litellm`` is importable) would additionally honour env-based
key availability to pick the first reachable provider; we keep the default
deterministic so routing never depends on network or secrets.
"""

from __future__ import annotations

import os
from typing import Any

from ..config import FoundryConfig
from ..paths import FoundryPaths
from .base import AdapterResult, BaseAdapter, register

# Mapping from a profile's preferred ``provider`` to the env var that would make
# it live. Used only to *prefer* a reachable provider when keys exist; absence
# never fails routing (we fall back to the first preferred entry).
_PROVIDER_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": None,  # local; no key required
}


class LiteLLMRouterAdapter(BaseAdapter):
    """Routes model profiles to concrete (provider, model) decisions."""

    id = "litellm_router"
    requires = ("litellm",)

    def route(
        self,
        model_profile: str,
        *,
        paths: FoundryPaths | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Resolve ``model_profile`` to a concrete routing decision.

        Reads ``config/model_profiles.yaml`` for the profile's ``preferred``
        list and returns the first entry whose provider key is present in the
        environment; if none are reachable (the default offline case), returns
        the first preferred entry with ``degraded=True``.
        """

        paths = paths or FoundryPaths.discover()
        env = env if env is not None else dict(os.environ)
        cfg = FoundryConfig(paths=paths)
        profiles = cfg.model_profiles.get("model_profiles", {})
        profile = profiles.get(model_profile) if isinstance(profiles, dict) else None

        if not isinstance(profile, dict):
            return {
                "model_profile": model_profile,
                "provider": None,
                "model": None,
                "degraded": True,
                "reason": "unknown_profile",
            }

        preferred = [p for p in (profile.get("preferred") or []) if isinstance(p, dict)]
        if not preferred:
            return {
                "model_profile": model_profile,
                "provider": None,
                "model": None,
                "degraded": True,
                "reason": "no_preferred_entries",
            }

        chosen = preferred[0]
        reachable = None
        if self.available():
            for entry in preferred:
                provider = str(entry.get("provider") or "")
                key_var = _PROVIDER_KEYS.get(provider)
                if key_var is None or env.get(key_var):  # local provider or key present
                    reachable = entry
                    break

        live = reachable is not None
        selected = reachable or chosen
        return {
            "model_profile": model_profile,
            "provider": selected.get("provider"),
            "model": selected.get("model"),
            "tier": profile.get("tier"),
            "temperature": profile.get("temperature"),
            "max_tokens": profile.get("max_tokens"),
            "preferred": preferred,
            "degraded": not live,
            "reason": "reachable_provider" if live else "preferred_fallback",
        }

    def run(self, request: dict[str, Any]) -> AdapterResult:
        model_profile = str(request.get("model_profile") or "rf_extract_cheap")
        paths = request.get("paths")
        decision = self.route(
            model_profile,
            paths=paths if isinstance(paths, FoundryPaths) else None,
        )
        degraded = bool(decision.get("degraded", True))
        notes = [
            f"routed {model_profile} -> {decision.get('provider')}:{decision.get('model')}"
        ]
        if degraded:
            notes.append("litellm unavailable or no provider key: returned preferred fallback")
        return AdapterResult(
            adapter=self.id,
            degraded=degraded,
            artifacts={"routing_decision": _yaml(decision)},
            notes=notes,
        )


def _yaml(obj: dict[str, Any]) -> str:
    from ..yamlio import dumps_yaml

    return dumps_yaml(obj)


register(LiteLLMRouterAdapter())

__all__ = ["LiteLLMRouterAdapter"]
