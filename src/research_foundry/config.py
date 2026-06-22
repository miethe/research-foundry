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

from .errors import RFError
from .paths import FoundryPaths
from .yamlio import load_yaml

# Valid values for viewer.auth_mode (OQ-4 resolution).
_VALID_AUTH_MODES = frozenset({"none", "token"})

# Config filenames under config/ (spec §5).
GOVERNANCE = "governance.yaml"
MODEL_PROFILES = "model_profiles.yaml"
ROUTING_RULES = "routing_rules.yaml"
TOOLS = "tools.yaml"
CLAIM_POLICY = "claim_policy.yaml"


def _validate_auth_mode(value: str) -> None:
    """Raise :class:`RFError` if *value* is not a recognised auth mode."""
    if value not in _VALID_AUTH_MODES:
        raise RFError(
            f"viewer.auth_mode {value!r} is not valid; "
            f"must be one of: {', '.join(sorted(_VALID_AUTH_MODES))}"
        )


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

    @property
    def viewer(self) -> dict[str, Any]:
        """The ``viewer`` block from ``foundry.yaml`` (runs-frontend export).

        Holds read-only viewer settings for both the static export pipeline and
        the live loopback API (``rf serve``).

        Supported keys and defaults
        ---------------------------
        sensitivity_threshold : str
            Redaction threshold for the export service (default ``"public"``).
        bind_host : str
            Host address ``rf serve`` binds to (default ``"127.0.0.1"``).
        serve_port : int
            TCP port for ``rf serve``.  Default ``7432`` — chosen to avoid
            collision with MeatyWiki API at ``8765`` (see SERVICES.md).
        auth_mode : str
            Authentication mode for ``rf serve``: ``"none"`` or ``"token"``.
            Default ``"none"`` (loopback-safe).  Must be ``"token"`` when
            ``bind_host`` is ``0.0.0.0`` (enforced in P4 fail-closed check).
        auth_token_env : str
            Name of the environment variable that holds the shared-secret
            token for ``auth_mode=token``.  Default ``"RF_SERVE_TOKEN"``.
            The token value MUST live in the env var — never inline in
            foundry.yaml.
        allowlist : list[str]
            Optional IP allowlist.  When non-empty, only listed IPs may reach
            ``rf serve`` endpoints (enforced in P4 IP allowlist middleware).
            Default ``[]`` (no restriction).
        cors_origins : list[str]
            CORS allowed origins passed to the FastAPI CORS middleware.
            Default ``["*"]`` (suitable for loopback mode); restrict to
            specific origins when binding on LAN.
        """

        viewer = self.foundry.get("viewer", {})
        return viewer if isinstance(viewer, dict) else {}

    def viewer_serve_port(self) -> int:
        """Return ``viewer.serve_port`` with default ``7432``.

        Port ``7432`` deconflicts from MeatyWiki Portal API (``8765``),
        IntentTree API (``8032``), SkillMeat API (``8080``), and all other
        known services on the agentic-nuc node (see SERVICES.md port table).
        """
        return int(self.viewer.get("serve_port", 7432))

    def viewer_bind_host(self) -> str:
        """Return ``viewer.bind_host`` with default ``"127.0.0.1"``."""
        return str(self.viewer.get("bind_host", "127.0.0.1"))

    def viewer_auth_mode(self) -> str:
        """Return ``viewer.auth_mode`` with default ``"none"``; validate on read."""
        raw = str(self.viewer.get("auth_mode", "none"))
        _validate_auth_mode(raw)
        return raw

    def viewer_auth_token_env(self) -> str:
        """Return ``viewer.auth_token_env`` with default ``"RF_SERVE_TOKEN"``."""
        return str(self.viewer.get("auth_token_env", "RF_SERVE_TOKEN"))

    def viewer_allowlist(self) -> list[str]:
        """Return ``viewer.allowlist`` with default ``[]``; validate list-of-strings."""
        raw = self.viewer.get("allowlist", [])
        if not isinstance(raw, list):
            raise RFError(
                "viewer.allowlist must be a list of strings, got "
                f"{type(raw).__name__!r}"
            )
        for item in raw:
            if not isinstance(item, str):
                raise RFError(
                    f"viewer.allowlist entries must be strings, got {item!r}"
                )
        return list(raw)

    def viewer_cors_origins(self) -> list[str]:
        """Return ``viewer.cors_origins`` with default ``["*"]``."""
        raw = self.viewer.get("cors_origins", ["*"])
        if not isinstance(raw, list):
            return ["*"]
        return [str(o) for o in raw]

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
    "_validate_auth_mode",
]
