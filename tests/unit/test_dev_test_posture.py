"""Unit tests for ``FoundryConfig.dev_test_posture_live_fetch_enabled()``
(clearance-gates M3, half A: ``foundry.dev_test_posture.live_fetch_enabled``)
and the paired audit-trail wiring at its startup emission site.

Mirrors ``tests/unit/test_deployment_mode.py``'s
``trusted_single_operator_posture`` coverage exactly, applied to the sibling
``dev_test_posture`` block:

  - Default is ``False`` when the block is absent.
  - Explicit, fully-populated opt-in resolves ``True``.
  - A half-declared block (``live_fetch_enabled: true`` with a required
    field missing) raises :class:`RFError` (fail-closed).
  - The startup warning fires exactly once per :class:`FoundryConfig`
    instance across repeated calls.
  - The paired audit event (``dev_test_posture_activated``) is emitted from
    the startup site OUTSIDE ``config.py`` — ``api.app.create_app`` — never
    from ``config.py`` itself (that import would be circular).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.errors import RFError
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services import audit_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _posture_overrides(
    *,
    declared_by: str = "nick",
    rationale: str = "local dev/test only; no license/ToS posture asserted",
    declared_at: str = "2026-08-05",
) -> dict[str, Any]:
    return {
        "live_fetch_enabled": True,
        "rationale": rationale,
        "declared_at": declared_at,
        "declared_by": declared_by,
    }


def _make_config(tmp_path: Path, foundry_overrides: dict | None = None) -> FoundryConfig:
    """Build a minimal ``FoundryConfig`` backed by a temp workspace.

    ``foundry_overrides`` merges into the top-level ``foundry:`` block of
    ``foundry.yaml``. Lightweight — does NOT copy the canonical distribution,
    so this is only suitable for calling ``FoundryConfig`` accessors
    directly, never ``create_app()`` (see ``_make_full_config`` below for
    that).
    """
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    foundry_yaml = root / "foundry.yaml"
    if foundry_overrides:
        overrides_yaml = yaml.safe_dump({"foundry": foundry_overrides}, sort_keys=False)
        foundry_yaml.write_text(overrides_yaml, encoding="utf-8")
    else:
        foundry_yaml.write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    return FoundryConfig(paths=FoundryPaths(root=root))


def _make_full_config(tmp_path: Path, foundry_overrides: dict | None = None) -> FoundryConfig:
    """Build a full temp workspace (schemas/config/templates copied) so
    ``create_app()`` can fully wire routers — mirrors
    ``tests/test_config_workspace_enforcement.py::_make_config``.

    Defaults to a loopback bind with ``auth.provider=none``, which resolves
    ``deployment_mode=single_user`` with no further declarations required
    (no ``trusted_single_operator_posture`` needed for this file's matrix).
    """
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    foundry_src = dist / "foundry.yaml"
    if foundry_src.exists():
        shutil.copyfile(foundry_src, root / "foundry.yaml")
    else:
        (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    for d in ("runs", "inbox/raw_ideas", "intents/active"):
        (root / d).mkdir(parents=True, exist_ok=True)

    foundry_yaml_path = root / "foundry.yaml"
    from research_foundry.yamlio import dump_yaml, load_yaml

    existing = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    existing["foundry"]["viewer"] = {
        **(existing["foundry"].get("viewer") or {}),
        "auth_mode": "none",
        "bind_host": "127.0.0.1",
    }
    existing["foundry"]["auth"] = {
        **(existing["foundry"].get("auth") or {}),
        "provider": "none",
    }
    if foundry_overrides:
        existing["foundry"].update(foundry_overrides)
    dump_yaml(existing, foundry_yaml_path)
    return FoundryConfig(paths=FoundryPaths(root=root))


# ---------------------------------------------------------------------------
# Default / opt-in / half-declared
# ---------------------------------------------------------------------------


class TestDevTestPostureResolver:
    def test_default_is_false(self, tmp_path):
        """No dev_test_posture block at all -> False, no raise."""
        config = _make_config(tmp_path)
        assert config.dev_test_posture_live_fetch_enabled() is False

    def test_absent_live_fetch_enabled_key_is_false(self, tmp_path):
        """Block present but live_fetch_enabled unset -> False."""
        config = _make_config(
            tmp_path,
            {"dev_test_posture": {"rationale": "no-op, key missing"}},
        )
        assert config.dev_test_posture_live_fetch_enabled() is False

    def test_live_fetch_enabled_false_is_false(self, tmp_path):
        config = _make_config(
            tmp_path,
            {"dev_test_posture": {"live_fetch_enabled": False}},
        )
        assert config.dev_test_posture_live_fetch_enabled() is False

    def test_explicit_full_opt_in_resolves_true(self, tmp_path):
        """A fully-populated posture activates live fetch."""
        config = _make_config(
            tmp_path,
            {"dev_test_posture": _posture_overrides()},
        )
        assert config.dev_test_posture_live_fetch_enabled() is True

    def test_half_declared_missing_rationale_raises(self, tmp_path):
        """live_fetch_enabled=true with rationale missing -> RFError (fail-closed)."""
        overrides = _posture_overrides()
        del overrides["rationale"]
        config = _make_config(tmp_path, {"dev_test_posture": overrides})
        with pytest.raises(RFError, match="rationale"):
            config.dev_test_posture_live_fetch_enabled()

    def test_half_declared_missing_declared_by_raises(self, tmp_path):
        overrides = _posture_overrides()
        del overrides["declared_by"]
        config = _make_config(tmp_path, {"dev_test_posture": overrides})
        with pytest.raises(RFError, match="declared_by"):
            config.dev_test_posture_live_fetch_enabled()

    def test_half_declared_empty_string_field_raises(self, tmp_path):
        """An empty-string field is treated as missing, not "declared but blank"."""
        overrides = _posture_overrides(declared_at="")
        config = _make_config(tmp_path, {"dev_test_posture": overrides})
        with pytest.raises(RFError, match="declared_at"):
            config.dev_test_posture_live_fetch_enabled()

    def test_never_opens_acquisition(self, tmp_path):
        """The posture's raw accessor never carries an acquisition-scope key
        -- this is a documentation-enforced invariant (M3 scope), not a
        machine-checkable one, so the test only asserts the fixture itself
        stays within the declared vocabulary."""
        config = _make_config(tmp_path, {"dev_test_posture": _posture_overrides()})
        posture = config.dev_test_posture()
        assert "acquisition" not in str(posture)


# ---------------------------------------------------------------------------
# Once-only startup warning
# ---------------------------------------------------------------------------


class TestDevTestPostureWarningDedup:
    def test_warning_fires_exactly_once_across_repeated_calls(self, tmp_path, caplog):
        config = _make_config(tmp_path, {"dev_test_posture": _posture_overrides()})

        with caplog.at_level(logging.WARNING, logger="research_foundry.config"):
            assert config.dev_test_posture_live_fetch_enabled() is True
            assert config.dev_test_posture_live_fetch_enabled() is True
            assert config.dev_test_posture_live_fetch_enabled() is True

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1, (
            "expected exactly one startup warning across 3 "
            f"dev_test_posture_live_fetch_enabled() calls, got {len(warnings)}"
        )
        assert "nick" in warnings[0].getMessage()

    def test_no_warning_when_not_declared(self, tmp_path, caplog):
        config = _make_config(tmp_path)
        with caplog.at_level(logging.WARNING, logger="research_foundry.config"):
            assert config.dev_test_posture_live_fetch_enabled() is False
        assert not [r for r in caplog.records if r.levelno == logging.WARNING]


# ---------------------------------------------------------------------------
# Audit event emitted at the startup site (api.app.create_app)
# ---------------------------------------------------------------------------


class TestDevTestPostureAuditEvent:
    def test_new_mutation_type_is_registered(self):
        assert "dev_test_posture_activated" in audit_service.MUTATION_TYPES

    def test_create_app_emits_audit_event_when_posture_declared(self, tmp_path):
        config = _make_full_config(
            tmp_path,
            {"dev_test_posture": _posture_overrides(declared_by="nick-startup-test")},
        )

        create_app(config)

        result = audit_service.list_events(
            config.paths, mutation_type="dev_test_posture_activated"
        )
        items = result["items"]
        assert len(items) == 1, (
            f"expected exactly one dev_test_posture_activated audit row, got {items}"
        )
        row = items[0]
        assert row["mutation_type"] == "dev_test_posture_activated"
        assert row["action"] == "dev_test_posture.live_fetch_enabled"
        assert row["policy_snapshot"]["declared_by"] == "nick-startup-test"

    def test_create_app_emits_no_audit_event_when_posture_not_declared(self, tmp_path):
        """Negative control: create_app() must not fabricate an activation
        event when the posture was never declared -- this is what makes the
        positive-control test above a real signal, not a tautology."""
        config = _make_full_config(tmp_path)

        create_app(config)

        result = audit_service.list_events(
            config.paths, mutation_type="dev_test_posture_activated"
        )
        assert result["items"] == []

    def test_config_module_does_not_import_audit_service(self):
        """The single most important structural constraint in this task:
        config.py must never import audit_service (audit_service -> ...
        -> config would be circular). Asserted directly against the
        imported module's namespace rather than via source-text grepping,
        so a refactor that renames the import can't silently defeat this
        check."""
        import research_foundry.config as config_module

        assert "audit_service" not in vars(config_module)
