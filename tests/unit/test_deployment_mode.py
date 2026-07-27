"""Unit tests for ``Config.deployment_mode()`` / ``deployment_mode_validate()``
(public-multiuser-release-activation Phase 1: ACT-101, ACT-102).

Covers:
  - FR-1: ``deployment_mode()`` resolver, default ``single_user``, validation.
  - FR-2: ``single_user`` preset is byte-identical to the pre-feature default
    resolved config (THE #1 acceptance gate for this phase — see
    ``TestFR2ByteIdenticalRegression`` below).
  - FR-3: ``multi_user`` preset defaults RBAC/isolation/rate-limit to
    "enforced"-equivalent values, but an explicit per-knob override always
    wins over the preset.
  - FR-4 (partial, a-c): ``deployment_mode_validate()`` fail-closed gate stub.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from research_foundry.config import (
    AuthRbacEnforcement,
    FoundryConfig,
    WorkspaceIsolationEnforcement,
)
from research_foundry.errors import RFError
from research_foundry.paths import FoundryPaths
from tests.conftest import DI1_AUDIT_TEST_HEAD


def _make_config(tmp_path, foundry_overrides: dict | None = None) -> FoundryConfig:
    """Build a minimal ``FoundryConfig`` backed by a temp workspace.

    ``foundry_overrides`` merges into the top-level ``foundry:`` block of
    ``foundry.yaml`` (e.g. ``{"deployment_mode": "multi_user"}`` or
    ``{"auth": {"provider": "local_static"}}``).
    """
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    foundry_yaml = root / "foundry.yaml"
    lines = ["foundry:", "  owner: Test"]
    if foundry_overrides:
        import yaml  # local import — test-only dependency already used by project

        overrides_yaml = yaml.safe_dump({"foundry": foundry_overrides}, sort_keys=False)
        foundry_yaml.write_text(overrides_yaml, encoding="utf-8")
    else:
        foundry_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return FoundryConfig(paths=FoundryPaths(root=root))


def _di1_accepted_overrides(tmp_path, auth_overrides: dict | None = None) -> dict:
    """Return ``auth`` overrides that satisfy condition (d) in full.

    Writes a throwaway ``status: accepted`` audit artifact under *tmp_path*
    and points ``auth.di1_audit_report_path`` at it (absolute path — the
    override accepts either absolute or distribution-root-relative). Merge
    the result into a test's ``auth`` overrides dict when a test's intent is
    to exercise conditions (a)-(c) in isolation, now that (d) is wired
    (Phase 4 ACT-402).
    """
    audit_path = tmp_path / "di1-audit-accepted.md"
    audit_path.write_text(
        f"---\nstatus: accepted\naudited_head: {DI1_AUDIT_TEST_HEAD}\n---\n\nbody\n",
        encoding="utf-8",
    )
    overrides = dict(auth_overrides or {})
    overrides["di1_audit_acknowledged"] = True
    overrides["di1_audit_report_path"] = str(audit_path)
    return overrides


# ---------------------------------------------------------------------------
# FR-1: deployment_mode() resolver
# ---------------------------------------------------------------------------


class TestDeploymentModeResolver:
    def test_default_is_single_user(self, tmp_path):
        config = _make_config(tmp_path)
        assert config.deployment_mode() == "single_user"

    def test_explicit_single_user(self, tmp_path):
        config = _make_config(tmp_path, {"deployment_mode": "single_user"})
        assert config.deployment_mode() == "single_user"

    def test_explicit_multi_user(self, tmp_path):
        config = _make_config(tmp_path, {"deployment_mode": "multi_user"})
        assert config.deployment_mode() == "multi_user"

    def test_invalid_mode_raises(self, tmp_path):
        config = _make_config(tmp_path, {"deployment_mode": "bogus"})
        with pytest.raises(ValueError, match="deployment_mode"):
            config.deployment_mode()

    def test_case_insensitive(self, tmp_path):
        config = _make_config(tmp_path, {"deployment_mode": "Multi_User"})
        assert config.deployment_mode() == "multi_user"


# ---------------------------------------------------------------------------
# FR-2: single_user byte-identical regression — THE acceptance gate for P1.
# ---------------------------------------------------------------------------


def _resolved_snapshot(config: FoundryConfig) -> dict:
    """Snapshot of every knob touched by the deployment_mode preset composition."""
    provider = config.auth_provider()
    bind_host = config.viewer_bind_host()
    return {
        "auth_provider": provider,
        "auth_rbac_enforcement": config.auth_rbac_enforcement().value,
        "resolve_rbac_enforced": config.resolve_rbac_enforced(provider, bind_host),
        "workspace_isolation_enforcement": config.workspace_isolation_enforcement().value,
        "resolve_workspace_isolation_enforced": config.resolve_workspace_isolation_enforced(
            provider, bind_host
        ),
        "viewer_bind_host": bind_host,
        "auth_rate_limit_enabled": config.auth_rate_limit_enabled(),
    }


class TestFR2ByteIdenticalRegression:
    """``single_user`` (explicit or unset) must resolve identically to the
    pre-feature default — no ``deployment_mode`` key at all.

    This is the #1 acceptance gate for shipping ACT-101 at all (R-P2 guard in
    the phase plan): any future preset-resolver change that causes a
    divergence must fail this test loudly.
    """

    def test_no_deployment_mode_key_matches_explicit_single_user(self, tmp_path):
        baseline = _make_config(tmp_path / "baseline")
        explicit = _make_config(tmp_path / "explicit", {"deployment_mode": "single_user"})

        assert _resolved_snapshot(baseline) == _resolved_snapshot(explicit)

    def test_baseline_resolved_defaults_are_unchanged(self, tmp_path):
        """Pin the literal pre-feature default values (today's shape) so a
        preset-composition regression is caught even if both snapshots
        happened to drift together."""
        config = _make_config(tmp_path)
        snapshot = _resolved_snapshot(config)

        assert snapshot == {
            "auth_provider": "none",
            "auth_rbac_enforcement": "auto",
            "resolve_rbac_enforced": True,
            "workspace_isolation_enforcement": "auto",
            "resolve_workspace_isolation_enforced": False,
            "viewer_bind_host": "127.0.0.1",
            "auth_rate_limit_enabled": True,
        }

    def test_single_user_preset_is_empty(self, tmp_path):
        """Direct assertion on the preset table itself — single_user must
        never map any knob to a non-fallback value."""
        config = _make_config(tmp_path, {"deployment_mode": "single_user"})
        assert config._deployment_mode_preset_default("auth_rbac_enforcement", "auto") == "auto"
        assert (
            config._deployment_mode_preset_default(
                "workspace_isolation_enforcement", "auto"
            )
            == "auto"
        )
        assert config._deployment_mode_preset_default("auth_rate_limit_enabled", True) is True


# ---------------------------------------------------------------------------
# FR-3: multi_user preset defaults + explicit override wins
# ---------------------------------------------------------------------------


class TestMultiUserPreset:
    def test_rbac_enforcement_defaults_to_enabled(self, tmp_path):
        config = _make_config(tmp_path, {"deployment_mode": "multi_user"})
        assert config.auth_rbac_enforcement() == AuthRbacEnforcement.ENABLED

    def test_workspace_isolation_defaults_to_enabled(self, tmp_path):
        config = _make_config(tmp_path, {"deployment_mode": "multi_user"})
        assert (
            config.workspace_isolation_enforcement() == WorkspaceIsolationEnforcement.ENABLED
        )

    def test_rate_limit_defaults_to_enabled(self, tmp_path):
        config = _make_config(tmp_path, {"deployment_mode": "multi_user"})
        assert config.auth_rate_limit_enabled() is True

    def test_explicit_rbac_override_wins_over_preset(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "multi_user",
                "auth": {"provider": "local_static", "rbac_enforcement": "auto"},
            },
        )
        # Explicit "auto" set by the operator must win over the multi_user
        # preset's "enabled" default.
        assert config.auth_rbac_enforcement() == AuthRbacEnforcement.AUTO

    def test_explicit_isolation_override_wins_over_preset(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "multi_user",
                "workspace_isolation_enforcement": "auto",
            },
        )
        assert (
            config.workspace_isolation_enforcement() == WorkspaceIsolationEnforcement.AUTO
        )

    def test_explicit_rate_limit_override_wins_over_preset(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "multi_user",
                "auth": {"rate_limit": {"enabled": False}},
            },
        )
        assert config.auth_rate_limit_enabled() is False

    def test_auth_provider_and_bind_host_untouched_by_preset(self, tmp_path):
        """The preset composes ONLY rbac/isolation/rate-limit — auth.provider
        and viewer.bind_host stay fully operator-controlled (FR-3 note)."""
        config = _make_config(tmp_path, {"deployment_mode": "multi_user"})
        assert config.auth_provider() == "none"
        assert config.viewer_bind_host() == "127.0.0.1"


# ---------------------------------------------------------------------------
# FR-4 (partial, a-c): deployment_mode_validate() startup gate stub
# ---------------------------------------------------------------------------


class TestDeploymentModeValidateStub:
    def test_single_user_never_raises(self, tmp_path):
        """No-op for single_user regardless of how unsafe the other knobs are."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "single_user",
                "auth": {"provider": "none"},
            },
        )
        config.deployment_mode_validate(bind_host="0.0.0.0")  # must not raise

    def test_multi_user_with_provider_none_raises_condition_a(self, tmp_path):
        config = _make_config(tmp_path, {"deployment_mode": "multi_user"})
        with pytest.raises(ValueError, match=r"\(a\)"):
            config.deployment_mode_validate()

    def test_multi_user_with_provider_configured_passes_a_b_c(self, tmp_path):
        """multi_user preset already defaults rbac/isolation to 'enabled', so
        with a real provider configured and (d) separately satisfied
        (Phase 4 ACT-402 — see ``_di1_accepted_overrides``), all four
        conditions are met."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "multi_user",
                "auth": _di1_accepted_overrides(
                    tmp_path, {"provider": "local_static"}
                ),
            },
        )
        config.deployment_mode_validate()  # must not raise

    def test_multi_user_names_every_unmet_condition_not_just_first(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "multi_user",
                "auth": {"provider": "none", "rbac_enforcement": "auto"},
                "workspace_isolation_enforcement": "auto",
            },
        )
        with pytest.raises(ValueError) as excinfo:
            config.deployment_mode_validate()
        message = str(excinfo.value)
        # provider=none -> (a) fails.
        # rbac_enforcement=auto + provider=none -> resolve_rbac_enforced still
        # True (AUTO always returns True per its documented semantics) -> (b) passes.
        # workspace_isolation_enforcement=auto + provider=none -> advisory (False)
        # -> (c) fails.
        # (d) neither di1_audit_acknowledged nor an accepted artifact is
        # configured -> (d) fails too (Phase 4 ACT-402).
        assert "(a)" in message
        assert "(c)" in message
        assert "(d)" in message
        assert "3 unmet condition" in message

    def test_multi_user_disabled_rbac_on_nonloopback_reports_unresolvable(self, tmp_path):
        """resolve_rbac_enforced() itself raises (disabled + non-loopback) —
        the gate must surface that as an unmet (b) condition, not propagate
        the raw ValueError past the "every unmet condition" contract."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "multi_user",
                "auth": {"provider": "local_static", "rbac_enforcement": "disabled"},
            },
        )
        with pytest.raises(ValueError, match=r"\(b\)"):
            config.deployment_mode_validate(bind_host="0.0.0.0")


# ---------------------------------------------------------------------------
# ACT-404: startup fail-closed gate test suite — AC-3 in full.
#
# Covers all four FR-4 conditions INDEPENDENTLY (each unmet condition alone
# triggers refusal, with a specific message naming exactly that condition —
# never silently absorbed into a generic error), the "all four satisfied"
# happy path, and the missing-artifact-file edge case treated identically to
# ``status != "accepted"`` (never "assume passed").
# ---------------------------------------------------------------------------


def _all_conditions_satisfied_overrides(tmp_path) -> dict:
    """``foundry:`` overrides where every one of (a)-(d) independently holds.

    Each test below starts from this baseline and flips exactly one
    condition to unmet, so a failure can only be attributed to that one
    flip — never ambiguous about which condition's logic is under test.
    """
    return {
        "deployment_mode": "multi_user",
        "auth": _di1_accepted_overrides(
            tmp_path,
            {"provider": "local_static", "rbac_enforcement": "enabled"},
        ),
        "workspace_isolation_enforcement": "enabled",
    }


class TestAC3FullFourConditionSuite:
    def test_all_four_satisfied_does_not_raise(self, tmp_path):
        config = _make_config(tmp_path, _all_conditions_satisfied_overrides(tmp_path))
        config.deployment_mode_validate(bind_host="127.0.0.1")  # must not raise

    def test_condition_a_unmet_in_isolation(self, tmp_path):
        overrides = _all_conditions_satisfied_overrides(tmp_path)
        overrides["auth"]["provider"] = "none"
        config = _make_config(tmp_path, overrides)
        with pytest.raises(ValueError) as excinfo:
            config.deployment_mode_validate(bind_host="127.0.0.1")
        message = str(excinfo.value)
        assert "(a)" in message
        assert "(b)" not in message
        assert "(c)" not in message
        assert "(d)" not in message
        assert "1 unmet condition" in message

    def test_condition_b_unmet_in_isolation(self, tmp_path):
        overrides = _all_conditions_satisfied_overrides(tmp_path)
        overrides["auth"]["rbac_enforcement"] = "disabled"
        config = _make_config(tmp_path, overrides)
        with pytest.raises(ValueError) as excinfo:
            # Loopback bind_host: 'disabled' resolves cleanly to False
            # (unmet, not unresolvable) — isolates (b) from the separate
            # "disabled on non-loopback raises" case covered above.
            config.deployment_mode_validate(bind_host="127.0.0.1")
        message = str(excinfo.value)
        assert "(a)" not in message
        assert "(b)" in message
        assert "(c)" not in message
        assert "(d)" not in message
        assert "1 unmet condition" in message

    def test_condition_c_unmet_in_isolation(self, tmp_path):
        overrides = _all_conditions_satisfied_overrides(tmp_path)
        overrides["workspace_isolation_enforcement"] = "disabled"
        config = _make_config(tmp_path, overrides)
        with pytest.raises(ValueError) as excinfo:
            config.deployment_mode_validate(bind_host="127.0.0.1")
        message = str(excinfo.value)
        assert "(a)" not in message
        assert "(b)" not in message
        assert "(c)" in message
        assert "(d)" not in message
        assert "1 unmet condition" in message

    def test_condition_d_unmet_ack_flag_false_in_isolation(self, tmp_path):
        overrides = _all_conditions_satisfied_overrides(tmp_path)
        overrides["auth"]["di1_audit_acknowledged"] = False
        config = _make_config(tmp_path, overrides)
        with pytest.raises(ValueError) as excinfo:
            config.deployment_mode_validate(bind_host="127.0.0.1")
        message = str(excinfo.value)
        assert "(a)" not in message
        assert "(b)" not in message
        assert "(c)" not in message
        assert "(d)" in message
        assert "di1_audit_acknowledged" in message
        assert "1 unmet condition" in message

    def test_condition_d_unmet_artifact_status_not_accepted_in_isolation(self, tmp_path):
        """The ack flag alone must NOT satisfy (d) — a stale/never-updated
        doc with the flag flipped is still an unmet two-part gate."""
        overrides = _all_conditions_satisfied_overrides(tmp_path)
        stale_audit = tmp_path / "stale-audit.md"
        # audited_head matches the pinned test sentinel so this exercises the
        # STATUS check specifically, isolated from the separate G2 freshness
        # check (covered by TestG2AuditFreshnessStaleness below).
        stale_audit.write_text(
            f"---\nstatus: pending-human-signoff\naudited_head: {DI1_AUDIT_TEST_HEAD}\n"
            "---\n\nbody\n",
            encoding="utf-8",
        )
        overrides["auth"]["di1_audit_report_path"] = str(stale_audit)
        config = _make_config(tmp_path, overrides)
        with pytest.raises(ValueError) as excinfo:
            config.deployment_mode_validate(bind_host="127.0.0.1")
        message = str(excinfo.value)
        assert "(a)" not in message
        assert "(b)" not in message
        assert "(c)" not in message
        assert "(d)" in message
        assert "pending-human-signoff" in message
        assert "1 unmet condition" in message

    def test_condition_d_unmet_missing_artifact_file_treated_as_unaccepted(self, tmp_path):
        """The missing-file edge case (AC-3's explicit resilience clause):
        no artifact at all must be treated IDENTICALLY to status != accepted
        — never 'assume passed' because there's nothing to disagree with."""
        overrides = _all_conditions_satisfied_overrides(tmp_path)
        overrides["auth"]["di1_audit_report_path"] = str(tmp_path / "does-not-exist.md")
        config = _make_config(tmp_path, overrides)
        with pytest.raises(ValueError) as excinfo:
            config.deployment_mode_validate(bind_host="127.0.0.1")
        message = str(excinfo.value)
        assert "(d)" in message
        assert "not found" in message
        assert "1 unmet condition" in message

    def test_all_four_unmet_names_all_four(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "multi_user",
                "auth": {"provider": "none", "rbac_enforcement": "disabled"},
                "workspace_isolation_enforcement": "disabled",
            },
        )
        with pytest.raises(ValueError) as excinfo:
            config.deployment_mode_validate(bind_host="127.0.0.1")
        message = str(excinfo.value)
        assert "(a)" in message
        assert "(b)" in message
        assert "(c)" in message
        assert "(d)" in message
        assert "4 unmet condition" in message

    def test_single_user_never_evaluates_condition_d(self, tmp_path):
        """FR-2 regression guard extended to (d): single_user must remain a
        total no-op even with auth.di1_audit_acknowledged unset and no
        artifact on disk at all."""
        config = _make_config(
            tmp_path,
            {"deployment_mode": "single_user", "auth": {"provider": "none"}},
        )
        config.deployment_mode_validate(bind_host="0.0.0.0")  # must not raise

    def test_artifact_status_field_is_read_not_written(self, tmp_path):
        """The gate is read-only against the artifact — validating (then
        failing closed) must never mutate the on-disk file."""
        overrides = _all_conditions_satisfied_overrides(tmp_path)
        overrides["auth"]["di1_audit_acknowledged"] = False
        artifact_path = Path(overrides["auth"]["di1_audit_report_path"])
        before = artifact_path.read_text(encoding="utf-8")
        config = _make_config(tmp_path, overrides)
        with pytest.raises(ValueError):
            config.deployment_mode_validate(bind_host="127.0.0.1")
        assert artifact_path.read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# G1 (DI-1 delta re-audit remediation, 2026-07-26): trusted_single_operator_
# posture escape hatch + bind/auth-based multi_user inference precedence.
# ---------------------------------------------------------------------------


class TestG1DeploymentModeInferenceAndEscapeHatch:
    def test_explicit_multi_user_is_honored_over_inference(self, tmp_path):
        """An explicit deployment_mode always wins -- precedence rule #1,
        unchanged by G1. Verified on a loopback+no-auth config where
        inference would otherwise resolve single_user, so a pass here can
        only be attributed to the explicit value being read first."""
        config = _make_config(tmp_path, {"deployment_mode": "multi_user"})
        assert config.deployment_mode() == "multi_user"

    def test_trusted_single_operator_posture_declared_keeps_single_user(
        self, tmp_path, caplog
    ):
        """A fully-populated posture keeps single_user even though bind +
        a real auth provider alone would otherwise infer multi_user, and
        emits exactly ONE startup warning across multiple deployment_mode()
        calls (idempotence -- deployment_mode() is called many times per
        app-startup via _deployment_mode_preset_default)."""
        config = _make_config(
            tmp_path,
            {
                "viewer": {"bind_host": "0.0.0.0"},
                "auth": {"provider": "local_static"},
                "trusted_single_operator_posture": {
                    "declared": True,
                    "rationale": "Single trusted LAN operator; DI-1 not yet re-accepted.",
                    "declared_at": "2026-07-26",
                    "declared_by": "nick",
                },
            },
        )

        with caplog.at_level(logging.WARNING, logger="research_foundry.config"):
            assert config.deployment_mode() == "single_user"
            assert config.deployment_mode() == "single_user"
            assert config.deployment_mode() == "single_user"

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1, (
            "expected exactly one startup warning across 3 deployment_mode() "
            f"calls, got {len(warnings)}"
        )
        assert "nick" in warnings[0].getMessage()

    def test_declared_true_with_missing_rationale_raises_config_error(self, tmp_path):
        """declared=true with any of rationale/declared_at/declared_by
        missing must fail closed at read-time -- never silently activate
        with a blank field, never silently fall through to inference."""
        config = _make_config(
            tmp_path,
            {
                "trusted_single_operator_posture": {
                    "declared": True,
                    "declared_at": "2026-07-26",
                    "declared_by": "nick",
                    # rationale intentionally omitted
                },
            },
        )
        with pytest.raises(RFError, match="rationale"):
            config.deployment_mode()

    def test_nonloopback_bind_with_real_auth_provider_infers_multi_user(self, tmp_path):
        """No explicit deployment_mode, no posture declared -- a public bind
        with a real auth provider must be INFERRED multi_user so the FR-13
        gate arms, instead of silently running under single_user forever."""
        config = _make_config(
            tmp_path,
            {
                "viewer": {"bind_host": "0.0.0.0"},
                "auth": {"provider": "local_static"},
            },
        )
        assert config.deployment_mode() == "multi_user"

    def test_loopback_bind_never_infers_multi_user(self, tmp_path):
        """The inference is bind-gated -- a loopback bind with a real auth
        provider configured still resolves single_user (unchanged default);
        loopback deployments are not the public-exposure case G1 targets."""
        config = _make_config(
            tmp_path,
            {
                "viewer": {"bind_host": "127.0.0.1"},
                "auth": {"provider": "local_static"},
            },
        )
        assert config.deployment_mode() == "single_user"


# ---------------------------------------------------------------------------
# Phase 5 "G1-precedence" hardening (2026-07-27, Codex gpt-5.6-sol
# adversarial finding): an operator could previously write an explicit
# ``deployment_mode: single_user`` on a non-loopback, auth-enabled bind and
# dodge the G1 inference above without ever declaring
# ``trusted_single_operator_posture`` -- defeating the whole point of the
# posture being the ONLY way to keep single_user semantics on a public+auth
# bind. These tests cover the five scenarios named in the remediation plan.
# ---------------------------------------------------------------------------


def _posture_overrides(*, declared_by: str = "nick") -> dict:
    return {
        "declared": True,
        "rationale": "Single trusted LAN operator; DI-1 not yet re-accepted.",
        "declared_at": "2026-07-27",
        "declared_by": declared_by,
    }


class TestG1PrecedenceExplicitSingleUserGate:
    def test_a_explicit_single_user_nonloopback_auth_no_posture_raises(self, tmp_path):
        """(a) Explicit single_user + non-loopback + auth-enabled + NO
        posture -> config error at load. This is the exact dodge the
        Phase-5 gate closes: without it, the config below would silently
        resolve to single_user despite being a public+authenticated bind."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "single_user",
                "viewer": {"bind_host": "0.0.0.0"},
                "auth": {"provider": "local_static"},
            },
        )
        with pytest.raises(RFError, match="trusted_single_operator_posture"):
            config.deployment_mode()

    def test_b_explicit_single_user_nonloopback_auth_with_posture_allowed(
        self, tmp_path, caplog
    ):
        """(b) Explicit single_user + non-loopback + auth-enabled + posture
        declared -> allowed, warning emitted once, single_user returned."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "single_user",
                "viewer": {"bind_host": "0.0.0.0"},
                "auth": {"provider": "local_static"},
                "trusted_single_operator_posture": _posture_overrides(),
            },
        )

        with caplog.at_level(logging.WARNING, logger="research_foundry.config"):
            assert config.deployment_mode() == "single_user"
            assert config.deployment_mode() == "single_user"

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1, (
            f"expected exactly one startup warning across 2 deployment_mode() calls, "
            f"got {len(warnings)}"
        )
        assert "nick" in warnings[0].getMessage()

    def test_c_explicit_single_user_loopback_auth_no_posture_allowed(self, tmp_path):
        """(c) Explicit single_user + loopback + auth-enabled + no posture
        -> allowed, single_user returned (no error -- loopback is safe)."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "single_user",
                "viewer": {"bind_host": "127.0.0.1"},
                "auth": {"provider": "local_static"},
            },
        )
        assert config.deployment_mode() == "single_user"

    def test_d_explicit_single_user_nonloopback_no_auth_unaffected_by_new_gate(
        self, tmp_path
    ):
        """(d) Explicit single_user + non-loopback + no auth
        (auth.provider=none) -> deployment_mode() itself must NOT raise;
        this combination is refused by the separate ``_bind_gate`` invariant
        at ``create_app()`` time (F1(2)), not by this resolver. Verifies the
        Phase-5 gate is bind+auth-enabled-scoped, not bind-only."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "single_user",
                "viewer": {"bind_host": "0.0.0.0"},
                "auth": {"provider": "none"},
            },
        )
        assert config.deployment_mode() == "single_user"

    def test_legacy_auth_mode_token_also_gated(self, tmp_path):
        """The gate uses ``is_auth_enabled()`` (covers the legacy
        ``viewer.auth_mode=="token"`` path too, not only ``auth.provider``)
        -- a deliberately broader net than the canonical-path-only
        inference it guards. No posture declared -> still raises."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "single_user",
                "viewer": {"bind_host": "0.0.0.0", "auth_mode": "token"},
                "auth": {"provider": "none"},
            },
        )
        with pytest.raises(RFError, match="trusted_single_operator_posture"):
            config.deployment_mode()

    def test_explicit_multi_user_always_honored_regardless_of_posture(self, tmp_path):
        """Step 1 (explicit multi_user always wins) is untouched by the new
        gate -- no posture required, no error, even on a public+auth bind."""
        config = _make_config(
            tmp_path,
            {
                "deployment_mode": "multi_user",
                "viewer": {"bind_host": "0.0.0.0"},
                "auth": {"provider": "local_static"},
            },
        )
        assert config.deployment_mode() == "multi_user"


# ---------------------------------------------------------------------------
# G2 (DI-1 delta re-audit remediation, 2026-07-26): _di1_audit_accepted()
# staleness detection -- audited_head vs. the current source-tree HEAD.
# ---------------------------------------------------------------------------


class TestG2AuditFreshnessStaleness:
    def test_audited_head_matches_current_head_and_status_accepted_passes(self, tmp_path):
        audit_path = tmp_path / "audit.md"
        audit_path.write_text(
            f"---\nstatus: accepted\naudited_head: {DI1_AUDIT_TEST_HEAD}\n---\n\nbody\n",
            encoding="utf-8",
        )
        config = _make_config(tmp_path, {"auth": {"di1_audit_report_path": str(audit_path)}})

        accepted, detail = config._di1_audit_accepted()

        assert accepted is True
        assert detail == ""

    def test_audited_head_mismatch_fails_with_staleness_message(self, tmp_path):
        audit_path = tmp_path / "audit.md"
        # A hex-lettered SHA (not all-digit) -- an all-digit dummy like
        # "0000...0" is parsed by PyYAML's YAML-1.1 octal resolver as the
        # integer 0, not the string "0000...0", which would spuriously hit
        # the "audited_head not declared" branch instead of the staleness
        # branch this test targets.
        audit_path.write_text(
            "---\nstatus: accepted\n"
            "audited_head: ffffffffffffffffffffffffffffffffffffffff\n"
            "---\n\nbody\n",
            encoding="utf-8",
        )
        config = _make_config(tmp_path, {"auth": {"di1_audit_report_path": str(audit_path)}})

        accepted, detail = config._di1_audit_accepted()

        assert accepted is False
        assert "stale" in detail
        assert "audited_head" in detail
        assert "HEAD" in detail

    def test_missing_audited_head_fails_with_cannot_verify_message(self, tmp_path):
        audit_path = tmp_path / "audit.md"
        audit_path.write_text("---\nstatus: accepted\n---\n\nbody\n", encoding="utf-8")
        config = _make_config(tmp_path, {"auth": {"di1_audit_report_path": str(audit_path)}})

        accepted, detail = config._di1_audit_accepted()

        assert accepted is False
        assert "audited_head" in detail
        assert "cannot verify" in detail
