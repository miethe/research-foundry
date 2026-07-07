"""Unit tests for make_key_fingerprint (FR-14 — salted HMAC fingerprint)."""

from __future__ import annotations

import logging
import re

import pytest

from research_foundry.services.telemetry import _INTERIM_PEPPER, make_key_fingerprint
from research_foundry.services.governance import scan_secrets

# Synthetic key used throughout (never a real credential)
_SYNTHETIC_KEY = "sk-test-0000000000000000000000000000000000000000000000"
_HEX_RE = re.compile(r"^[0-9a-f]{12}$")


def test_fingerprint_is_12_hex():
    """Fingerprint must be exactly 12 lowercase hex characters."""
    fp = make_key_fingerprint(_SYNTHETIC_KEY)
    assert len(fp) == 12, f"expected 12 chars, got {len(fp)}: {fp!r}"
    assert _HEX_RE.match(fp), f"not 12 lowercase hex chars: {fp!r}"


def test_fingerprint_is_deterministic():
    """Same raw_key + same pepper produces the same fingerprint every time."""
    fp1 = make_key_fingerprint(_SYNTHETIC_KEY, pepper="test-pepper")
    fp2 = make_key_fingerprint(_SYNTHETIC_KEY, pepper="test-pepper")
    assert fp1 == fp2


def test_fingerprint_different_keys():
    """Different raw keys must produce different fingerprints."""
    fp1 = make_key_fingerprint("key-alpha-111111111111111111111111111111111111111")
    fp2 = make_key_fingerprint("key-beta--222222222222222222222222222222222222222")
    assert fp1 != fp2, "distinct keys produced the same fingerprint (collision)"


def test_fingerprint_not_reversible_prefix():
    """Fingerprint must not be a raw truncation of the key."""
    fp = make_key_fingerprint(_SYNTHETIC_KEY)
    assert fp != _SYNTHETIC_KEY[:12], (
        "fingerprint equals raw key prefix — no HMAC was applied"
    )


def test_fingerprint_not_flagged_by_governance():
    """The HMAC fingerprint must not trigger any secret-scan violation."""
    fp = make_key_fingerprint(_SYNTHETIC_KEY)
    violations = scan_secrets(fp)
    assert violations == [], (
        f"fingerprint {fp!r} triggered governance violations: {violations}"
    )


def test_interim_pepper_warning_emitted(caplog, monkeypatch):
    """When no pepper kwarg and RF_KEY_PROFILE_PEPPER not set, a SECURITY warning is emitted."""
    monkeypatch.delenv("RF_KEY_PROFILE_PEPPER", raising=False)
    with caplog.at_level(logging.WARNING, logger="research_foundry.services.telemetry"):
        make_key_fingerprint(_SYNTHETIC_KEY)
    assert any(
        "SECURITY" in msg and "RF_KEY_PROFILE_PEPPER" in msg
        for msg in caplog.messages
    ), f"Expected SECURITY warning about missing pepper, got: {caplog.messages!r}"


def test_env_pepper_no_warning(caplog, monkeypatch):
    """When RF_KEY_PROFILE_PEPPER is set, no SECURITY warning is emitted and the
    fingerprint matches explicit-kwarg result with that same pepper value."""
    env_pepper = "test-env-pepper-xyzzy"
    monkeypatch.setenv("RF_KEY_PROFILE_PEPPER", env_pepper)
    with caplog.at_level(logging.WARNING, logger="research_foundry.services.telemetry"):
        fp = make_key_fingerprint(_SYNTHETIC_KEY)
    security_warnings = [m for m in caplog.messages if "SECURITY" in m and "RF_KEY_PROFILE_PEPPER" in m]
    assert not security_warnings, (
        f"Expected NO SECURITY warning when env pepper is set, got: {security_warnings!r}"
    )
    # Fingerprint must match the explicit-kwarg computation and differ from interim.
    fp_expected = make_key_fingerprint(_SYNTHETIC_KEY, pepper=env_pepper)
    assert fp == fp_expected, "Fingerprint with env pepper must equal explicit-kwarg fingerprint"
    fp_interim = make_key_fingerprint(_SYNTHETIC_KEY, pepper=_INTERIM_PEPPER)
    assert fp != fp_interim, "Env pepper fingerprint must differ from interim pepper fingerprint"
