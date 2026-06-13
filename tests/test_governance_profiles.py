"""Tests for the governance guard service (contract §8).

Proves the non-negotiable policy rules fire deterministically:
* personal-allowed intent run under a ``work_approved`` profile -> BLOCK (exit 3)
* mixed personal + work_sensitive sources in a bundle -> BLOCK (exit 3)
* secret strings (sk-ant-…, ghp_…) detected by the scanner
* work_sensitive writeback to personal MeatyWiki -> require_approval (exit 7)
* a clean personal run -> pass (exit 0)
"""

from __future__ import annotations

from research_foundry.config import FoundryConfig
from research_foundry.services.governance import (
    GuardContext,
    Violation,
    guard_check,
    preflight,
    scan_paths,
    scan_secrets,
)


def _ids(result) -> set[str]:
    return {v.rule_id for v in result.violations}


# --- no_work_keys_for_personal_runs ----------------------------------------


def test_personal_intent_with_work_profile_blocks(tmp_foundry):
    ctx = GuardContext(
        profile="work_approved",
        intent_key_profile_allowed="personal",
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.passed is False
    assert result.exit_code == 3
    assert "no_work_keys_for_personal_runs" in _ids(result)


def test_preflight_personal_intent_work_profile_blocks(tmp_foundry):
    intent = {"governance": {"key_profile_allowed": "personal"}, "sensitivity": "personal"}
    result = preflight(intent, {}, {}, profile="work_approved", paths=tmp_foundry)
    assert result.exit_code == 3
    assert "no_work_keys_for_personal_runs" in _ids(result)


# --- no_mixed_personal_work_bundle -----------------------------------------


def test_mixed_personal_work_bundle_blocks(tmp_foundry):
    ctx = GuardContext(
        profile="work_approved",
        source_sensitivities=("personal", "work_sensitive"),
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.passed is False
    assert result.exit_code == 3
    assert "no_mixed_personal_work_bundle" in _ids(result)


# --- no_secret_in_markdown -------------------------------------------------


def test_scan_secrets_detects_anthropic_key(tmp_foundry):
    cfg = FoundryConfig(paths=tmp_foundry)
    text = "here is a leaked key sk-ant-abcdefghijklmnopqrstuvwxyz0123 in the doc"
    hits = scan_secrets(text, config=cfg)
    assert hits, "expected the sk-ant- key to be detected"


def test_scan_secrets_detects_github_pat(tmp_foundry):
    cfg = FoundryConfig(paths=tmp_foundry)
    text = "token: ghp_" + "a" * 36
    hits = scan_secrets(text, config=cfg)
    assert hits, "expected the ghp_ token to be detected"


def test_scan_secrets_clean_text_returns_empty(tmp_foundry):
    cfg = FoundryConfig(paths=tmp_foundry)
    hits = scan_secrets("a perfectly normal research note about evidence bundles", config=cfg)
    assert hits == []


def test_scan_paths_flags_secret_file_and_guard_blocks(tmp_foundry):
    cfg = FoundryConfig(paths=tmp_foundry)
    leaky = tmp_foundry.root / "leaky.md"
    leaky.write_text("key sk-ant-abcdefghijklmnopqrstuvwxyz0123\n", encoding="utf-8")
    violations = scan_paths([leaky], config=cfg)
    assert any(v.rule_id == "no_secret_in_markdown" for v in violations)
    assert all(isinstance(v, Violation) for v in violations)

    ctx = GuardContext(profile="personal", artifact_paths=(leaky,))
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.exit_code == 3
    assert "no_secret_in_markdown" in _ids(result)


# --- work_writeback_requires_review (require_approval -> exit 7) -------------


def test_work_sensitive_writeback_to_personal_meatywiki_requires_review(tmp_foundry):
    ctx = GuardContext(
        profile="work_approved",
        sensitivity="work_sensitive",
        source_sensitivities=("work_sensitive",),
        writeback_targets=("meatywiki",),
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.passed is False
    assert result.exit_code == 7
    assert "work_writeback_requires_review" in _ids(result)


def test_block_outranks_require_approval(tmp_foundry):
    # Mixed bundle (block) + work writeback (require_approval) -> block wins.
    ctx = GuardContext(
        profile="work_approved",
        sensitivity="work_sensitive",
        source_sensitivities=("personal", "work_sensitive"),
        writeback_targets=("meatywiki",),
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.exit_code == 3
    ids = _ids(result)
    assert "no_mixed_personal_work_bundle" in ids
    assert "work_writeback_requires_review" in ids


# --- no_work_sensitive_to_unapproved_provider ------------------------------


def test_work_sensitive_to_unapproved_provider_blocks(tmp_foundry):
    ctx = GuardContext(
        profile="work_approved",
        sensitivity="work_sensitive",
        source_sensitivities=("work_sensitive",),
        model_provider="some_public_endpoint",
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.exit_code == 3
    assert "no_work_sensitive_to_unapproved_provider" in _ids(result)


# --- material_claims_must_be_mapped ----------------------------------------


def test_unmapped_material_claims_block(tmp_foundry):
    ctx = GuardContext(profile="personal", unmapped_material_claims=2)
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.exit_code == 3
    assert "material_claims_must_be_mapped" in _ids(result)


# --- clean personal run -> pass --------------------------------------------


def test_clean_personal_run_passes(tmp_foundry):
    clean = tmp_foundry.root / "note.md"
    clean.write_text("A clean personal research note with no secrets.\n", encoding="utf-8")
    ctx = GuardContext(
        profile="personal",
        sensitivity="personal",
        source_sensitivities=("personal", "public"),
        intent_key_profile_allowed="personal",
        writeback_targets=("meatywiki",),
        artifact_paths=(clean,),
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.passed is True
    assert result.exit_code == 0
    assert result.violations == []


def test_clean_preflight_passes(tmp_foundry):
    intent = {
        "governance": {
            "key_profile_allowed": "personal",
            "allowed_writebacks": ["meatywiki_personal"],
        },
        "sensitivity": "personal",
    }
    result = preflight(intent, {}, {"model_provider": "local"}, profile="personal", paths=tmp_foundry)
    assert result.exit_code == 0
    assert result.passed is True


# --- hook entrypoints (safe no-ops) ----------------------------------------


def test_hook_entrypoints_noop_without_stdin():
    from research_foundry.validators import (
        emit_ccdash_event,
        guard_pretool,
        scan_artifact,
    )

    # No stdin / tty -> allow, never raise. (pytest captures stdin -> not a tty;
    # _read_stdin reads empty -> {} -> allow.)
    assert guard_pretool.main([]) == 0
    assert scan_artifact.main([]) == 0
    assert emit_ccdash_event.main([]) == 0
