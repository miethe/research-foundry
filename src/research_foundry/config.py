"""Workspace + policy configuration loading.

Loads ``foundry.yaml`` and the ``config/*.yaml`` policy files (governance,
model profiles, routing rules, tools, claim policy). Every loader degrades
gracefully to ``{}`` when a file is absent so the package is importable and the
CLI runs before all content files exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from .paths import FoundryPaths
from .yamlio import load_yaml

# Config filenames under config/ (spec §5).
GOVERNANCE = "governance.yaml"
MODEL_PROFILES = "model_profiles.yaml"
ROUTING_RULES = "routing_rules.yaml"
TOOLS = "tools.yaml"
CLAIM_POLICY = "claim_policy.yaml"


def _safe_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = load_yaml(path)
    return data if isinstance(data, dict) else {}


@dataclass
class FoundryConfig:
    """Lazily-loaded view over a foundry workspace's configuration."""

    paths: FoundryPaths
    _cache: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, start: str | Path | None = None) -> FoundryConfig:
        return cls(paths=FoundryPaths.discover(start))

    @cached_property
    def foundry(self) -> dict[str, Any]:
        data = _safe_load(self.paths.foundry_yaml)
        return data.get("foundry", data) if data else {}

    def _config(self, name: str) -> dict[str, Any]:
        if name not in self._cache:
            self._cache[name] = _safe_load(self.paths.config / name)
        return self._cache[name]

    @property
    def governance(self) -> dict[str, Any]:
        return self._config(GOVERNANCE)

    @property
    def model_profiles(self) -> dict[str, Any]:
        return self._config(MODEL_PROFILES)

    @property
    def routing_rules(self) -> dict[str, Any]:
        return self._config(ROUTING_RULES)

    @property
    def tools(self) -> dict[str, Any]:
        return self._config(TOOLS)

    @property
    def claim_policy(self) -> dict[str, Any]:
        return self._config(CLAIM_POLICY)

    # --- convenience accessors -------------------------------------------
    @property
    def owner(self) -> str:
        return str(self.foundry.get("owner") or "Nick Miethe")

    @property
    def default_profile(self) -> str:
        return str(self.foundry.get("default_profile") or "personal")

    @property
    def timezone(self) -> str:
        return str(self.foundry.get("timezone") or "America/New_York")

    def key_profiles(self) -> dict[str, Any]:
        """The ``key_profiles`` map from governance config (spec §7.1)."""

        gov = self.governance
        return gov.get("key_profiles", {}) if isinstance(gov, dict) else {}

    def policy_rules(self) -> list[dict[str, Any]]:
        """The ``policy_rules`` list from governance config (spec §7.2)."""

        gov = self.governance
        rules = gov.get("policy_rules", []) if isinstance(gov, dict) else []
        return rules if isinstance(rules, list) else []


__all__ = [
    "FoundryConfig",
    "GOVERNANCE",
    "MODEL_PROFILES",
    "ROUTING_RULES",
    "TOOLS",
    "CLAIM_POLICY",
]
