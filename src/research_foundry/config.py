"""Workspace + policy configuration loading.

Loads ``foundry.yaml`` and the ``config/*.yaml`` policy files (governance,
model profiles, routing rules, tools, claim policy). Every loader degrades
gracefully to ``{}`` when a file is absent so the package is importable and the
CLI runs before all content files exist.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Optional

from .errors import RFError
from .frontmatter import load_md
from .paths import FoundryPaths, distribution_root
from .yamlio import load_yaml

# Valid values for viewer.auth_mode (OQ-4 resolution).
_VALID_AUTH_MODES = frozenset({"none", "token"})

# Valid values for auth.rbac_enforcement (P5.6 T5).
# "auto"     — enforced when auth.provider != "none"; NOT enforced when provider==none.
# "disabled" — force OFF, BUT ONLY on loopback bind hosts (fail-closed).
# "enabled"  — force ON regardless of provider.


class AuthRbacEnforcement(str, enum.Enum):
    """RBAC enforcement gate configuration (P5.6 T5).

    Controls whether ``require_role`` dependency enforces role checks or
    passes through unconditionally.

    Values
    ------
    auto
        Default.  RBAC is enforced when ``auth.provider != "none"`` and
        NOT enforced when ``auth.provider == "none"`` (the loopback-safe
        default that preserves the existing single-operator behaviour).
    disabled
        Force RBAC **off** regardless of provider.  **FAIL-CLOSED**: only
        honoured when ``viewer.bind_host`` is a loopback address
        (``127.0.0.1``, ``::1``, ``localhost``).  Setting this on a
        non-loopback bind host causes ``create_app`` to refuse startup with
        a ``ValueError``.  You CANNOT disable RBAC on a public bind.
    enabled
        Force RBAC **on** regardless of provider, even when provider is
        ``"none"``.  Useful for hardening loopback deployments where the
        operator still wants role-based access control.
    """

    AUTO = "auto"
    DISABLED = "disabled"
    ENABLED = "enabled"


# Valid values for workspace_isolation_enforcement (WKSP-304 TASK-1.1).
# Orthogonal to auth.rbac_enforcement (independent security gate — see
# WKSP-304 decision log) but structurally mirrors its enum shape exactly.
# "auto"     — enforced when auth.provider != "none"; advisory when provider==none.
# "disabled" — force OFF, BUT ONLY on loopback bind hosts (fail-closed).
# "enabled"  — force ON regardless of provider.


class WorkspaceIsolationEnforcement(str, enum.Enum):
    """Workspace row-level isolation enforcement gate configuration (WKSP-304).

    Controls whether row-level ``workspace_id`` scoping in the catalog,
    builder, and agent-job services is enforced at the query layer or
    remains advisory-only (logs a mismatch but does not deny).  This flag
    is orthogonal to :class:`AuthRbacEnforcement` — isolation and RBAC are
    independent security gates and must not be conflated.

    Values
    ------
    auto
        Default.  Isolation is enforced when ``auth.provider != "none"``
        and advisory-only when ``auth.provider == "none"`` (preserves the
        existing single-operator-trust default behaviour).
    disabled
        Force isolation enforcement **off** regardless of provider.
        **FAIL-CLOSED**: only honoured when ``viewer.bind_host`` is a
        loopback address (``127.0.0.1``, ``::1``, ``localhost``).  Setting
        this on a non-loopback bind host causes startup to refuse with a
        ``ValueError``.  You CANNOT disable isolation enforcement on a
        public bind.
    enabled
        Force isolation enforcement **on** regardless of provider, even
        when provider is ``"none"``.
    """

    AUTO = "auto"
    DISABLED = "disabled"
    ENABLED = "enabled"


@dataclass(frozen=True)
class AssertionLedgerControls:
    """Independent, default-off controls for the reusable assertion ledger.

    These values describe capability authorization only; they do not grant
    private-workspace, production, public-promotion, or writeback authority.
    Automated reuse and canonical claims remain separate opt-ins after ledger
    writes are permitted.
    """

    ledger_write_enabled: bool = False
    automated_reuse_enabled: bool = False
    canonical_claims_enabled: bool = False


@dataclass(frozen=True)
class AssertionLedgerCapabilities:
    """Resolved assertion-ledger capabilities after dependency checks.

    The three controls remain independently configured, but reuse and
    canonical-claim handling cannot run when the ledger itself is not allowed
    to write authoritative records.  The resolver is intentionally local: it
    neither changes a flag nor grants any workspace or rollout authority.
    """

    ledger_write_allowed: bool = False
    automated_reuse_allowed: bool = False
    canonical_claims_allowed: bool = False


def _is_loopback(bind_host: str) -> bool:
    """Return ``True`` if *bind_host* is a loopback address.

    Recognised loopback values: ``"127.0.0.1"``, any ``"127."`` prefix,
    ``"::1"``, and ``"localhost"``.  Everything else (``"0.0.0.0"``,
    LAN IPs, hostnames) is considered non-loopback / public.
    """
    return (
        bind_host in {"127.0.0.1", "::1", "localhost"}
        or bind_host.startswith("127.")
    )


# Valid values for auth.provider (P5.1 canonical auth selector).
# "clerk" is implemented in CLK-4.x with a dark-by-default precondition gate.
# "oidc" is recognised vocabulary but not yet implemented — validated at
# config-read time so deployments that set it fail fast with an actionable
# message rather than silently falling through to the "none" path.  See FU-3.
_VALID_AUTH_PROVIDERS = frozenset({"none", "local_static", "clerk", "oidc"})
_IMPLEMENTED_AUTH_PROVIDERS = frozenset({"none", "local_static", "clerk"})

# Valid values for deployment_mode (FR-1, public-multiuser-release-activation P1).
# "single_user" — default; behaviorally identical to today's un-set default (FR-2).
# "multi_user"  — composes preset *defaults* over the rbac/isolation/rate-limit
#                 knobs (FR-3); an explicit per-knob override in foundry.yaml
#                 always wins over the preset.
_VALID_DEPLOYMENT_MODES = frozenset({"single_user", "multi_user"})

# Preset defaults applied ONLY when the underlying knob is unset (absent) in
# foundry.yaml. ``single_user`` is intentionally empty — this is what makes the
# FR-2 byte-identical regression guarantee hold: with no `deployment_mode` key
# at all, ``deployment_mode()`` resolves to "single_user" and every preset
# lookup below is a no-op, so resolved config is unchanged from pre-feature
# behaviour.
_DEPLOYMENT_MODE_PRESETS: dict[str, dict[str, Any]] = {
    "single_user": {},
    "multi_user": {
        "auth_rbac_enforcement": "enabled",
        "workspace_isolation_enforcement": "enabled",
        "auth_rate_limit_enabled": True,
    },
}

# Config filenames under config/ (spec §5).
GOVERNANCE = "governance.yaml"
MODEL_PROFILES = "model_profiles.yaml"
ROUTING_RULES = "routing_rules.yaml"
TOOLS = "tools.yaml"
CLAIM_POLICY = "claim_policy.yaml"

# DI-1 full-surface audit artifact (FR-13, FR-14, public-multiuser-release-
# activation P4 ACT-401/ACT-402). This is a governance/planning artifact
# that ships with the source checkout -- resolved relative to
# ``distribution_root()`` (see :meth:`FoundryConfig._di1_audit_report_path`),
# never relative to a runtime ``FoundryPaths.root`` (a separate directory in
# split deployments -- see the data-plane-split note in project memory).
_DI1_AUDIT_REPORT_RELATIVE_PATH = (
    "docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md"
)


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

    # --- agents block --------------------------------------------------------

    @property
    def agents(self) -> dict[str, Any]:
        """The ``agents`` block from ``foundry.yaml``.

        Supported keys and defaults
        ---------------------------
        enabled : bool
            Feature flag that gates the entire Phase 4 agent-job surface
            (API routes).  Default ``False`` (opt-in; must be explicitly
            enabled and is only permitted in loopback/single-operator mode
            pre-P5 — P5.2 RBAC + P5.3 workspace isolation are required
            before shared-LAN or public exposure).
        """
        agents = self.foundry.get("agents", {})
        return agents if isinstance(agents, dict) else {}

    def agents_enabled(self) -> bool:
        """Return ``True`` if the agents feature flag is enabled.

        Reads ``foundry.agents.enabled``; defaults to ``False`` when the key
        is absent (opt-in).  To enable the agent-job surface, set::

            foundry:
              agents:
                enabled: false

        in ``foundry.yaml``.  The gate is opt-in: agents are disabled by
        default.  Set ``enabled: true`` in foundry.yaml to enable the
        agent-job surface.  This prevents accidental exposure in shared-LAN
        or static-export deployments before P5 RBAC ships.
        """
        return bool(self.agents.get("enabled", False))

    def agents_default_service_account_id(self) -> Optional[str]:
        """Return ``agents.default_service_account_id``, or ``None`` if unset.

        Consumed by ``agent_job_service.create_job`` (ACT-204, FR-12): when
        ``deployment_mode() == "multi_user"`` AND this key is set, a launched
        agent job's execution identity resolves to this service account
        rather than the triggering caller's identity.  When unset (the
        default) or ``deployment_mode() == "single_user"``, this key is
        never consulted — the pre-feature identity resolution is unchanged
        (AC-5)::

            foundry:
              agents:
                default_service_account_id: svc_researcher_default
        """
        value = self.agents.get("default_service_account_id")
        return str(value) if value else None

    @property
    def assertion_ledger(self) -> dict[str, Any]:
        """Return the assertion-ledger control block with an empty default."""

        ledger = self.foundry.get("assertion_ledger", {})
        return ledger if isinstance(ledger, dict) else {}

    def assertion_ledger_controls(self) -> AssertionLedgerControls:
        """Resolve the three independent assertion-ledger controls.

        All controls default to ``False``.  This resolver intentionally does
        not infer an enabled state from test fixtures, workspace contents, or
        other feature flags.
        """

        ledger = self.assertion_ledger
        return AssertionLedgerControls(
            ledger_write_enabled=ledger.get("ledger_write_enabled") is True,
            automated_reuse_enabled=ledger.get("automated_reuse_enabled") is True,
            canonical_claims_enabled=ledger.get("canonical_claims_enabled") is True,
        )

    def assertion_ledger_capabilities(self) -> AssertionLedgerCapabilities:
        """Resolve fail-closed capability dependencies without changing flags.

        Automated reuse and canonical claims require their own explicit flag
        *and* the ledger-write capability.  This ensures a partial
        configuration cannot make a derived surface available without the
        authoritative ledger being enabled first.
        """

        controls = self.assertion_ledger_controls()
        return AssertionLedgerCapabilities(
            ledger_write_allowed=controls.ledger_write_enabled,
            automated_reuse_allowed=(
                controls.ledger_write_enabled and controls.automated_reuse_enabled
            ),
            canonical_claims_allowed=(
                controls.ledger_write_enabled and controls.canonical_claims_enabled
            ),
        )

    # --- auth block (P5.1 canonical auth provider) ---------------------------

    @property
    def auth(self) -> dict[str, Any]:
        """The ``auth`` block from ``foundry.yaml`` (P5.1 canonical auth config).

        **New canonical auth selector** — supersedes the legacy
        ``viewer.auth_mode`` / ``viewer.auth_token_env`` single-token
        approach.  The legacy fields are preserved for backward compatibility
        until an explicit deprecation pass removes them; new deployments should
        use ``auth.provider`` and ``auth.local_static.tokens`` exclusively.

        Migration guide for ``viewer.auth_mode = "token"`` users
        ---------------------------------------------------------
        Replace::

            foundry:
              viewer:
                auth_mode: token
                auth_token_env: RF_SERVE_TOKEN

        with::

            foundry:
              auth:
                provider: local_static
                local_static:
                  tokens:
                    - token_env: RF_SERVE_TOKEN
                      user_id: <your_user_id>
                      workspace_id: default
                      roles: [owner]
        """
        auth = self.foundry.get("auth", {})
        return auth if isinstance(auth, dict) else {}

    def auth_provider(self) -> str:
        """Return ``auth.provider`` with default ``"none"``; validate on read.

        Valid values: ``none``, ``local_static``, ``clerk``, ``oidc``.

        ``none``
            No auth middleware is added; ``request.state`` never gains an
            ``identity`` attribute.  Safe default for loopback-only mode.

        ``local_static``
            Multi-token Bearer → identity mapping configured via
            ``auth.local_static.tokens`` in ``foundry.yaml``.  Suitable for
            air-gapped, self-hosted, and single-operator LAN deployments.

        ``clerk``
            Clerk.dev JWKS/JWT-based auth (CLK-4.x).  **Dark by default** —
            enabling this provider requires both ``auth.clerk_frontend_api``
            (non-empty) and ``auth.clerk_outbound_internet_enabled: true`` to
            be explicitly set in ``foundry.yaml``.  A missing or incomplete
            configuration raises ``ValueError`` at startup rather than
            silently falling through to the ``none`` path.

        ``oidc``
            Generic OIDC/JWT auth (future: see FU-3).  Recognised vocabulary
            but not yet implemented — raises ``ValueError`` at config-read time.

        Raises:
            ValueError: If the provider is unrecognised, not yet implemented,
                or if ``clerk`` is selected without satisfying its preconditions.
        """
        raw = str(self.auth.get("provider", "none"))
        if raw not in _VALID_AUTH_PROVIDERS:
            raise ValueError(
                f"auth.provider={raw!r} is not a recognised provider. "
                f"Must be one of: {', '.join(sorted(_VALID_AUTH_PROVIDERS))}"
            )
        if raw not in _IMPLEMENTED_AUTH_PROVIDERS:
            raise ValueError(
                f"auth.provider={raw!r} is not yet implemented. "
                f"Supported: none, local_static, clerk. (oidc: see FU-3)"
            )
        # CLK-4.3: Clerk dark-by-default startup gate.
        # Both preconditions must be explicitly set by the operator; we never
        # auto-detect outbound internet or assume a default Clerk URL.
        if raw == "clerk":
            frontend_api = self.auth_clerk_frontend_api()
            outbound = self.auth_clerk_outbound_internet_enabled()
            if not frontend_api or not outbound:
                raise ValueError(
                    "Clerk provider requires auth.clerk_frontend_api and "
                    "auth.clerk_outbound_internet_enabled=true — set these "
                    "explicitly in foundry.yaml before enabling Clerk"
                )
        return raw

    def auth_local_static_tokens(self) -> list[dict]:
        """Return ``auth.local_static.tokens`` with default ``[]``.

        Each entry is a dict with keys:

        ``token_env``
            Name of the environment variable holding the secret token value.
            The token value MUST live in the env var — never inline in
            ``foundry.yaml``.
        ``user_id``
            User identifier returned on a match (e.g. ``"alice"``).
        ``workspace_id``
            Workspace the token grants access to (e.g. ``"default"``).
        ``roles``
            List of role strings for this user in the workspace
            (e.g. ``["owner"]``, ``["researcher"]``).

        Returns an empty list when ``auth.local_static`` or
        ``auth.local_static.tokens`` is absent — the ``LocalStaticAuthProvider``
        will then reject all requests (fail-closed).
        """
        local_static = self.auth.get("local_static", {})
        if not isinstance(local_static, dict):
            return []
        tokens = local_static.get("tokens", [])
        return list(tokens) if isinstance(tokens, list) else []

    def auth_clerk_frontend_api(self) -> str:
        """Return ``auth.clerk_frontend_api`` with default ``""`` (empty string).

        The Clerk Frontend API URL (e.g. ``https://your-app.clerk.accounts.dev``)
        is required when ``auth.provider = "clerk"``.  An empty or absent value
        means the Clerk precondition gate is unmet; ``auth_provider()`` will
        raise and ``ClerkAuthProvider.available()`` will return ``False``.

        The value MUST be a public HTTPS URL reachable by clients — never a
        raw secret.  Clerk API keys live in environment variables, not here.
        """
        raw = self.auth.get("clerk_frontend_api", "")
        return str(raw) if raw else ""

    def auth_clerk_outbound_internet_enabled(self) -> bool:
        """Return ``auth.clerk_outbound_internet_enabled`` with default ``False``.

        This flag is an explicit operator declaration that the deployment has
        outbound internet access to Clerk's JWKS endpoint.  It is **never**
        auto-detected — the operator must set it to ``true`` in ``foundry.yaml``
        to satisfy the Clerk dark-by-default precondition gate (CLK-4.3).

        Default ``False`` means Clerk is disabled unless the operator has
        consciously declared the outbound-internet requirement.
        """
        return bool(self.auth.get("clerk_outbound_internet_enabled", False))

    # --- rate_limit block (P5.6 per-identity+per-route sliding window) ----------

    def auth_rate_limit(self) -> dict[str, Any]:
        """Return the ``auth.rate_limit`` block from ``foundry.yaml``.

        Supported keys and defaults
        ---------------------------
        enabled : bool
            Whether the rate-limit middleware is active.  Default ``True``.
            Set ``false`` to disable rate limiting entirely (not recommended
            for multi-user LAN or public deployments).
        requests_per_window : int
            Maximum requests per ``(user_id, route)`` pair per window.
            Default ``60`` (1 req/sec sustained at the default 60 s window).
        window_seconds : int
            Sliding-window width in seconds.  Default ``60``.

        Deployments with ``auth.provider = none`` (loopback mode) are
        automatically exempt from rate limiting even when ``enabled = true``
        because no identity is available to key on (see
        :class:`~research_foundry.api.middleware.rate_limit.RateLimitMiddleware`).
        """
        rl = self.auth.get("rate_limit", {})
        return rl if isinstance(rl, dict) else {}

    def auth_rate_limit_enabled(self) -> bool:
        """Return ``auth.rate_limit.enabled`` with default ``True``.

        When unset in ``foundry.yaml``, defers to the ``deployment_mode``
        preset default (ACT-101); ``single_user`` preserves the literal
        ``True`` fallback (FR-2), ``multi_user`` also defaults to ``True``
        per FR-3 (rate limiting stays on by default in multi-user mode too).
        """
        rl = self.auth_rate_limit()
        if "enabled" in rl:
            return bool(rl["enabled"])
        return bool(self._deployment_mode_preset_default("auth_rate_limit_enabled", True))

    def auth_rate_limit_requests_per_window(self) -> int:
        """Return ``auth.rate_limit.requests_per_window`` with default ``60``."""
        return int(self.auth_rate_limit().get("requests_per_window", 60))

    def auth_rate_limit_window_seconds(self) -> int:
        """Return ``auth.rate_limit.window_seconds`` with default ``60``."""
        return int(self.auth_rate_limit().get("window_seconds", 60))

    # --- rbac_enforcement block (P5.6 T5 RBAC toggle) -----------------------

    def auth_rbac_enforcement(self) -> AuthRbacEnforcement:
        """Return ``auth.rbac_enforcement`` with default ``auto``.

        Valid values: ``auto``, ``disabled``, ``enabled``.

        ``auto``
            RBAC is enforced when ``auth.provider != "none"`` and skipped
            when provider is ``"none"`` (preserves the single-operator-trust
            default behaviour).

        ``disabled``
            Force RBAC off.  **Fail-closed**: startup refuses if
            ``viewer.bind_host`` is non-loopback.  Never disable RBAC on a
            public bind.

        ``enabled``
            Force RBAC on regardless of provider.

        Raises:
            ValueError: If the raw config value is not a recognised enum member.
        """
        raw = self.auth.get("rbac_enforcement")
        if raw is None:
            # Unset in foundry.yaml — defer to the deployment_mode preset
            # (ACT-101); "auto" is the preset-independent fallback so
            # single_user (the default) is byte-identical to pre-feature
            # behaviour (FR-2).
            raw = self._deployment_mode_preset_default("auth_rbac_enforcement", "auto")
        raw = str(raw).lower()
        try:
            return AuthRbacEnforcement(raw)
        except ValueError:
            valid = ", ".join(e.value for e in AuthRbacEnforcement)
            raise ValueError(
                f"auth.rbac_enforcement={raw!r} is not valid; "
                f"must be one of: {valid}"
            ) from None

    def resolve_rbac_enforced(self, provider: str, bind_host: str) -> bool:
        """Resolve whether RBAC role checks are actively enforced.

        This is called **once** at app-create time and the result is stored
        on ``app.state.rbac_enforced``.  Every subsequent call to
        ``require_role`` reads that flag instead of re-computing.

        Parameters
        ----------
        provider:
            The resolved ``auth.provider`` value (e.g. ``"none"``,
            ``"local_static"``).  Pass ``config.auth_provider()`` unless
            you are writing tests that simulate specific provider states.
        bind_host:
            The ``viewer.bind_host`` value (e.g. ``"127.0.0.1"``,
            ``"0.0.0.0"``).  Used only for the fail-closed
            ``disabled``-on-non-loopback gate.

        Returns
        -------
        bool
            ``True``  — ``require_role`` enforces role checks on every request.
            ``False`` — ``require_role`` passes through unconditionally.

        Raises
        ------
        ValueError
            When ``auth.rbac_enforcement=disabled`` and ``bind_host`` is not a
            loopback address.  The server **must not start** in this state.
        """
        enforcement = self.auth_rbac_enforcement()

        if enforcement == AuthRbacEnforcement.DISABLED:
            if not _is_loopback(bind_host):
                raise ValueError(
                    f"auth.rbac_enforcement=disabled is forbidden when "
                    f"viewer.bind_host={bind_host!r} is a non-loopback address. "
                    "RBAC cannot be disabled on a public bind. "
                    "Either set bind_host to a loopback address (127.0.0.1) or "
                    "use auth.rbac_enforcement=auto (the default)."
                )
            return False

        # AuthRbacEnforcement.AUTO and AuthRbacEnforcement.ENABLED both return True.
        #
        # For AUTO + provider="none": the identity-None passthrough in
        # require_role() already provides the single-operator-trust semantics
        # (no auth middleware → no identity → allow).  We do NOT return False here
        # because that would bypass RBAC even when an identity IS present on the
        # request (e.g. from a custom middleware or test fixture), which would
        # silently break role enforcement for any caller that does inject identity
        # in a provider=none deployment.
        #
        # The rbac_enforced=False sentinel is reserved exclusively for the
        # explicit opt-out case (disabled + loopback) where the operator has
        # consciously decided that ALL requests — including authenticated ones —
        # must pass through unconditionally.
        return True

    # --- workspace_isolation_enforcement block (WKSP-304 TASK-1.1) ----------

    def workspace_isolation_enforcement(self) -> WorkspaceIsolationEnforcement:
        """Return ``workspace_isolation_enforcement`` with default ``auto``.

        Valid values: ``auto``, ``disabled``, ``enabled``.  Structurally
        mirrors :meth:`auth_rbac_enforcement` but is an orthogonal flag —
        it is read from the top-level ``workspace_isolation_enforcement``
        key in ``foundry.yaml`` (a sibling of ``auth:``), not nested under
        the ``auth`` block, because workspace isolation and RBAC are
        independent security gates (see WKSP-304 decision log).

        The parsed value is used by :meth:`resolve_workspace_isolation_enforced`
        to determine whether row-level ``workspace_id`` scoping is actively
        enforced in the catalog, builder, and agent-job services. When
        enforced, :func:`~research_foundry.api.auth.scope.require_workspace_scope`
        denies cross-workspace reads (404), omits unowned rows from list results,
        and rejects mutations on unowned records. Enforcement is gated by
        ``app.state.workspace_isolation_enforced`` and controlled by this flag
        in concert with ``auth.provider`` (see :class:`WorkspaceIsolationEnforcement`
        enum for the full AUTO truth table). Single-operator-trust callers
        (identity ``None``) short-circuit before any enforcement check, so
        ``provider="none"`` deployments stay advisory-only by default.

        Raises:
            ValueError: If the raw config value is not a recognised enum
                member.
        """
        raw = self.foundry.get("workspace_isolation_enforcement")
        if raw is None:
            # Unset in foundry.yaml — defer to the deployment_mode preset
            # (ACT-101); see auth_rbac_enforcement() for the FR-2 rationale.
            raw = self._deployment_mode_preset_default(
                "workspace_isolation_enforcement", "auto"
            )
        raw = str(raw).lower()
        try:
            return WorkspaceIsolationEnforcement(raw)
        except ValueError:
            valid = ", ".join(e.value for e in WorkspaceIsolationEnforcement)
            raise ValueError(
                f"workspace_isolation_enforcement={raw!r} is not valid; "
                f"must be one of: {valid}"
            ) from None

    def resolve_workspace_isolation_enforced(self, provider: str, bind_host: str) -> bool:
        """Resolve whether workspace row-level isolation is actively enforced.

        This is called **once** at app-create time and the result is stored
        on ``app.state.workspace_isolation_enforced``. Every subsequent query
        in the catalog, builder, and agent-job services reads that flag
        (via :func:`~research_foundry.api.auth.scope.resolve_workspace_isolation_active`)
        to determine enforcement mode.

        Structurally mirrors :meth:`resolve_rbac_enforced` (same fail-closed
        gate, same ``_is_loopback`` reuse) but resolves the orthogonal
        ``workspace_isolation_enforcement`` flag instead of
        ``auth.rbac_enforcement`` — see the WKSP-304 decision log for why
        isolation and RBAC are independent security gates.

        Unlike :meth:`resolve_rbac_enforced` (whose ``AUTO`` branch always
        returns ``True`` because RBAC enforcement is additionally gated by
        the identity-None passthrough in ``require_role``), this resolver's
        ``AUTO`` branch returns the literal provider-keyed truth table
        documented on :class:`WorkspaceIsolationEnforcement`: enforcing when
        ``provider != "none"``, advisory when ``provider == "none"``. When
        enforced, :func:`~research_foundry.api.auth.scope.require_workspace_scope`
        denies mismatched or null ``workspace_id`` (404 to the caller). When
        advisory-only (the default for single-operator-trust deployments with
        ``provider="none"``), a mismatch is logged but not denied. The
        identity-None short-circuit in ``require_workspace_scope`` ensures
        single-operator-trust callers (no auth middleware) never pay for,
        and are never affected by, this flag lookup.

        Parameters
        ----------
        provider:
            The resolved ``auth.provider`` value (e.g. ``"none"``,
            ``"local_static"``). Pass ``config.auth_provider()`` unless
            you are writing tests that simulate specific provider states.
        bind_host:
            The ``viewer.bind_host`` value (e.g. ``"127.0.0.1"``,
            ``"0.0.0.0"``). Used only for the fail-closed
            ``disabled``-on-non-loopback gate.

        Returns
        -------
        bool
            ``True``  — isolation is enforced; :func:`~research_foundry.api.auth.scope.require_workspace_scope`
            denies cross-workspace reads and mutations.
            ``False`` — isolation is advisory-only; scope mismatches are logged but allowed.

        Raises
        ------
        ValueError
            When ``workspace_isolation_enforcement=disabled`` and
            ``bind_host`` is not a loopback address. The server **must not
            start** in this state.
        """
        enforcement = self.workspace_isolation_enforcement()

        if enforcement == WorkspaceIsolationEnforcement.DISABLED:
            if not _is_loopback(bind_host):
                raise ValueError(
                    f"workspace_isolation_enforcement=disabled is forbidden when "
                    f"viewer.bind_host={bind_host!r} is a non-loopback address. "
                    "Workspace isolation cannot be disabled on a public bind. "
                    "Either set bind_host to a loopback address (127.0.0.1) or "
                    "use workspace_isolation_enforcement=auto (the default)."
                )
            return False

        if enforcement == WorkspaceIsolationEnforcement.ENABLED:
            return True

        # WorkspaceIsolationEnforcement.AUTO: enforced when provider != "none";
        # advisory-only when provider == "none" (preserves the existing
        # single-operator-trust default behaviour). See docstring above for
        # why this differs from resolve_rbac_enforced's AUTO branch.
        return provider != "none"

    def is_auth_enabled(self) -> bool:
        """Return ``True`` when any auth mechanism is enabled.

        Checks both the canonical ``auth.provider`` block (P5 path) and the
        legacy ``viewer.auth_mode`` field so that non-loopback safety gates
        accept either auth configuration style.

        Returns ``True`` when:
          - ``auth.provider`` is non-``"none"`` (new canonical path), OR
          - ``viewer.auth_mode`` is ``"token"`` (legacy path).

        Returns ``False`` when both are absent or explicitly set to ``"none"``.

        This method never raises — unrecognised or unimplemented provider
        values are treated as ``"none"`` to avoid masking the gate failure.
        Used by the ``rf serve`` pre-bind gate.
        """
        # New canonical path: auth.provider != "none"
        try:
            provider = self.auth_provider()
        except (ValueError, Exception):  # noqa: BLE001 — unrecognised/unimplemented → treat as none
            provider = "none"
        if provider != "none":
            return True
        # Legacy path: viewer.auth_mode == "token"
        try:
            auth_mode = self.viewer_auth_mode()
        except Exception:  # noqa: BLE001
            auth_mode = "none"
        return auth_mode == "token"

    # --- deployment_mode block (FR-1..FR-5: single_user/multi_user presets) --

    def deployment_mode(self) -> str:
        """Return ``deployment_mode`` with default ``"single_user"``; validate.

        Valid values: ``single_user``, ``multi_user``.

        ``single_user``
            Default.  Behaviorally identical to today's un-set default — the
            per-knob resolvers (:meth:`auth_provider`,
            :meth:`auth_rbac_enforcement`, :meth:`workspace_isolation_enforcement`,
            :meth:`viewer_bind_host`, :meth:`auth_rate_limit_enabled`) resolve
            exactly as they did before this method existed (FR-2). This is the
            #1 regression gate for the LAN/NUC deployment.

        ``multi_user``
            Composes preset *defaults* over the RBAC/isolation/rate-limit knobs
            (FR-3): ``auth.rbac_enforcement`` and
            ``workspace_isolation_enforcement`` default to ``"enabled"`` and
            ``auth.rate_limit.enabled`` defaults to ``True`` — but ONLY when the
            operator has not explicitly set that knob in ``foundry.yaml``; an
            explicit per-knob override always wins over the preset.
            ``auth.provider`` and ``viewer.bind_host`` are NOT touched by this
            preset — those remain fully operator-controlled (see
            :meth:`deployment_mode_validate` for the fail-closed startup gate
            that requires a real, non-``"none"`` auth provider).

        Raises:
            ValueError: If the raw config value is not a recognised mode.
        """
        raw = str(self.foundry.get("deployment_mode", "single_user")).lower()
        if raw not in _VALID_DEPLOYMENT_MODES:
            raise ValueError(
                f"deployment_mode={raw!r} is not valid; "
                f"must be one of: {', '.join(sorted(_VALID_DEPLOYMENT_MODES))}"
            )
        return raw

    def _deployment_mode_preset_default(self, knob: str, fallback: Any) -> Any:
        """Return the ``deployment_mode`` preset default for *knob*, else *fallback*.

        Internal composition helper (ACT-101) — callers must only invoke this
        AFTER determining the knob is unset (absent) in ``foundry.yaml``; it
        never overrides an explicit operator-set value. ``single_user`` (the
        default deployment_mode) maps every knob to ``fallback`` unchanged,
        which is what makes the FR-2 byte-identical regression guarantee hold.
        """
        preset = _DEPLOYMENT_MODE_PRESETS.get(self.deployment_mode(), {})
        return preset.get(knob, fallback)

    def di1_audit_acknowledged(self) -> bool:
        """Return ``auth.di1_audit_acknowledged`` (default ``False``).

        The **operator-ack half** of the FR-13 two-part DI-1 gate (Phase 4
        ACT-402) — a human/operator must explicitly set this ``true`` in
        ``foundry.yaml``. On its own this flag satisfies nothing: see
        :meth:`_di1_audit_report_path`/:meth:`_di1_audit_accepted` for the
        other half (the audit artifact's machine-checkable ``status``), and
        :meth:`deployment_mode_validate`'s condition (d) for where both halves
        are required together.
        """
        return bool(self.auth.get("di1_audit_acknowledged", False))

    def _di1_audit_report_path(self) -> Path:
        """Resolve the DI-1 full-surface audit artifact's on-disk path.

        This is a governance/planning document that ships with the source
        checkout (``docs/project_plans/reports/audits/...``) — it is
        resolved relative to :func:`~research_foundry.paths.distribution_root`
        (the installed/checked-out package location), **never** relative to
        :attr:`paths` (``FoundryPaths.root``, the RUNTIME workspace data
        root) — those are two different directories in split deployments
        (see the data-plane-split project note): the runtime root holds
        ``config/``/``schemas/``/``templates/`` copied there by ``rf init``,
        but audits are never copied anywhere. Overridable via
        ``auth.di1_audit_report_path`` in ``foundry.yaml`` (relative to
        ``distribution_root()`` unless given as an absolute path) — mainly
        for tests and non-standard checkouts.
        """
        override = self.auth.get("di1_audit_report_path")
        if override:
            candidate = Path(str(override))
            return candidate if candidate.is_absolute() else distribution_root() / candidate
        return distribution_root() / _DI1_AUDIT_REPORT_RELATIVE_PATH

    def _di1_audit_accepted(self) -> tuple[bool, str]:
        """Resolve the **artifact half** of the FR-13 two-part DI-1 gate.

        Returns ``(accepted, detail)``. ``accepted`` is ``True`` only when
        the artifact at :meth:`_di1_audit_report_path` exists, is readable,
        and its YAML frontmatter's ``status`` field is the literal string
        ``"accepted"`` — set only by an explicit human sign-off (ACT-406;
        Mode D — no agent may set this value itself). A **missing file** is
        treated identically to ``status != "accepted"`` (fail-closed; never
        "assume passed" just because there is nothing to disagree with).
        ``detail`` names the concrete unmet reason for the startup-gate error
        message; empty when ``accepted`` is ``True``.
        """
        path = self._di1_audit_report_path()
        if not path.exists():
            return False, f"DI-1 audit artifact not found at {path}"
        try:
            meta, _ = load_md(path)
        except Exception as exc:  # noqa: BLE001 — malformed file is fail-closed too
            return False, f"DI-1 audit artifact at {path} could not be read: {exc}"
        status = meta.get("status")
        if status != "accepted":
            return False, (
                f"DI-1 audit artifact status is {status!r} (must be 'accepted') at {path}"
            )
        return True, ""

    def _deployment_mode_conditions(
        self, *, bind_host: str | None = None
    ) -> list[dict[str, Any]]:
        """Evaluate the FR-4 multi_user startup-gate conditions (a)-(d) WITHOUT raising.

        Shared introspection helper consumed by both :meth:`deployment_mode_validate`
        (the fail-closed startup gate, which raises when any condition is unmet)
        and :meth:`deployment_mode_status` (the read-only admin-API introspection
        endpoint, Phase 3 ACT-303) — factored out so the two can never drift out
        of sync on what "passing" means for a given condition.

        Returns an empty list when :meth:`deployment_mode` resolves to
        ``"single_user"`` — the gate (and this introspection) is a no-op outside
        multi_user.

        Otherwise returns exactly one dict per condition ``"a"``..``"d"`` with
        keys ``id`` (str), ``passed`` (bool), and ``detail`` (str — empty when
        passed, otherwise the same human-readable reason
        :meth:`deployment_mode_validate` raises with). Never includes secret
        material — every condition here only ever names config keys, resolved
        booleans, or file paths, exactly as :meth:`deployment_mode_validate`
        already does.
        """
        mode = self.deployment_mode()
        if mode != "multi_user":
            return []

        effective_bind_host = bind_host if bind_host is not None else self.viewer_bind_host()
        conditions: list[dict[str, Any]] = []

        try:
            provider = self.auth_provider()
        except ValueError as exc:
            conditions.append({"id": "a", "passed": False, "detail": f"auth.provider is invalid: {exc}"})
            return conditions

        if provider == "none":
            conditions.append(
                {
                    "id": "a",
                    "passed": False,
                    "detail": (
                        "auth.provider must not be 'none' when deployment_mode=multi_user "
                        "— configure auth.provider=local_static or clerk in foundry.yaml."
                    ),
                }
            )
        else:
            conditions.append({"id": "a", "passed": True, "detail": ""})

        try:
            rbac_enforced = self.resolve_rbac_enforced(provider, effective_bind_host)
        except ValueError as exc:
            conditions.append(
                {"id": "b", "passed": False, "detail": f"auth.rbac_enforcement is unresolvable: {exc}"}
            )
        else:
            if rbac_enforced:
                conditions.append({"id": "b", "passed": True, "detail": ""})
            else:
                conditions.append(
                    {
                        "id": "b",
                        "passed": False,
                        "detail": (
                            "auth.rbac_enforcement must resolve to enforced when "
                            "deployment_mode=multi_user — remove rbac_enforcement=disabled "
                            "or set it to 'enabled' in foundry.yaml."
                        ),
                    }
                )

        try:
            isolation_enforced = self.resolve_workspace_isolation_enforced(
                provider, effective_bind_host
            )
        except ValueError as exc:
            conditions.append(
                {"id": "c", "passed": False, "detail": f"workspace_isolation_enforcement is unresolvable: {exc}"}
            )
        else:
            if isolation_enforced:
                conditions.append({"id": "c", "passed": True, "detail": ""})
            else:
                conditions.append(
                    {
                        "id": "c",
                        "passed": False,
                        "detail": (
                            "workspace_isolation_enforcement must resolve to enforced when "
                            "deployment_mode=multi_user — remove workspace_isolation_enforcement="
                            "disabled or set it to 'enabled' in foundry.yaml."
                        ),
                    }
                )

        # Condition (d): FR-13 two-part DI-1 gate (Phase 4 ACT-402). Both halves
        # are evaluated and named independently.
        ack = self.di1_audit_acknowledged()
        audit_accepted, audit_detail = self._di1_audit_accepted()
        if ack and audit_accepted:
            conditions.append({"id": "d", "passed": True, "detail": ""})
        else:
            di1_unmet: list[str] = []
            if not ack:
                di1_unmet.append(
                    "operator has not set auth.di1_audit_acknowledged=true in foundry.yaml"
                )
            if not audit_accepted:
                di1_unmet.append(audit_detail)
            conditions.append(
                {
                    "id": "d",
                    "passed": False,
                    "detail": (
                        "DI-1 full-surface audit two-part gate is incomplete when "
                        "deployment_mode=multi_user — " + "; ".join(di1_unmet) + "."
                    ),
                }
            )

        return conditions

    def deployment_mode_status(self, *, bind_host: str | None = None) -> dict[str, Any]:
        """Read-only introspection over the FR-4 multi_user startup gate (ACT-303).

        Unlike :meth:`deployment_mode_validate` this NEVER raises — it is
        intended for the admin API's ``GET /api/admin/deployment-mode-status``
        endpoint (Phase 3 ACT-303) so operators can see WHY a multi_user
        deployment would refuse to start (or confirm it is clear to start)
        without triggering the fail-closed exception path.

        Returns
        -------
        dict with keys:
            ``deployment_mode``  (str)  — resolved mode ("single_user"/"multi_user")
            ``gate_applicable``  (bool) — False for single_user (gate is a no-op)
            ``gate_passed``      (bool) — True when every applicable condition passes
            ``conditions``       (list[dict]) — one entry per condition (a)-(d),
                each ``{"id": str, "passed": bool, "detail": str}``; empty list
                when ``gate_applicable`` is False.

        Never includes secret material — see :meth:`_deployment_mode_conditions`.
        """
        mode = self.deployment_mode()
        conditions = self._deployment_mode_conditions(bind_host=bind_host)
        gate_applicable = mode == "multi_user"
        gate_passed = (not gate_applicable) or all(c["passed"] for c in conditions)
        return {
            "deployment_mode": mode,
            "gate_applicable": gate_applicable,
            "gate_passed": gate_passed,
            "conditions": conditions,
        }

    def deployment_mode_validate(self, *, bind_host: str | None = None) -> None:
        """Fail-closed startup gate for ``deployment_mode=multi_user`` (FR-4).

        **Full 4-condition suite** (Phase 4 ACT-402 completes the P1 stub,
        which evaluated only (a)-(c)) — see Phase 4 AC-3.

        No-op when :meth:`deployment_mode` resolves to ``"single_user"`` (the
        default) — this gate only ever constrains ``multi_user`` deployments,
        so it can never regress single-user/LAN behaviour.

        Conditions checked (multi_user only)
        -------------------------------------
        (a) ``auth.provider`` must not be ``"none"``.
        (b) ``auth.rbac_enforcement`` must resolve to enforced
            (:meth:`resolve_rbac_enforced`).
        (c) ``workspace_isolation_enforcement`` must resolve to enforced
            (:meth:`resolve_workspace_isolation_enforced`).
        (d) **DI-1 full-surface audit two-part gate** (FR-13, Phase 4
            ACT-401/ACT-402): BOTH halves must independently hold —
            :meth:`di1_audit_acknowledged` (``auth.di1_audit_acknowledged``
            resolves ``True``) AND :meth:`_di1_audit_accepted` (the audit
            artifact at :meth:`_di1_audit_report_path` exists and its
            frontmatter ``status`` is literally ``"accepted"``). Neither a
            stale/never-updated doc with the ack flag flipped, nor an
            accepted doc with the ack flag never set, satisfies this
            condition alone — both are named independently in the raised
            error when either is missing. A missing artifact file is
            treated identically to an unaccepted one (never "assume
            passed"). No agent may set the artifact's ``status`` to
            ``"accepted"`` itself (Mode D, ACT-406) — this method only
            *reads* that field, it never writes it.

        Parameters
        ----------
        bind_host:
            The effective ``viewer.bind_host`` value, forwarded to
            :meth:`resolve_rbac_enforced` / :meth:`resolve_workspace_isolation_enforced`
            for their own fail-closed loopback checks. Defaults to
            :meth:`viewer_bind_host` when omitted.

        Raises
        ------
        ValueError
            Naming EVERY unmet condition (not just the first) when
            ``deployment_mode=multi_user`` and one or more of (a)-(d) fail.
            The server/app **must not start** in this state.
        """
        mode = self.deployment_mode()
        if mode != "multi_user":
            return

        # Phase 3 ACT-303: conditions (a)-(d) are evaluated by the shared
        # non-raising helper so this gate and the admin API's read-only
        # ``deployment_mode_status()`` introspection can never drift out of
        # sync on what "passing" means for a given condition.
        conditions = self._deployment_mode_conditions(bind_host=bind_host)
        unmet = [f"({c['id']}) {c['detail']}" for c in conditions if not c["passed"]]

        if unmet:
            raise ValueError(
                "deployment_mode=multi_user refused to start "
                f"({len(unmet)} unmet condition(s)):\n  - " + "\n  - ".join(unmet)
            )


__all__ = [
    "AssertionLedgerCapabilities",
    "AssertionLedgerControls",
    "AuthRbacEnforcement",
    "FoundryConfig",
    "GOVERNANCE",
    "MODEL_PROFILES",
    "ROUTING_RULES",
    "TOOLS",
    "CLAIM_POLICY",
    "_validate_auth_mode",
    "_is_loopback",
]
