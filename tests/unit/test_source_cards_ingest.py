"""P3 forward write driver (phase-3-4-forward-and-reuse.md): `rf ingest` CLI
wiring of `assertion_registry_workspace_id` into `source_cards.ingest_source`.

P3-01 threads the single-operator workspace id ("default", per P1-01's
resolution rule in `assertion_workspace.py`) through P1's fail-closed
`resolve_or_deny` gate into `ingest_source` -- this module proves that wiring
via the real `rf ingest` Typer command (`CliRunner`), not by calling
`ingest_source()` directly with an explicit `assertion_registry_workspace_id`
kwarg the way P1.5-03's own AC-8/AC-9 tests do
(`tests/unit/test_assertion_materialization.py`). Per the P2-01 SPIKE finding
this phase's entry-point wiring only pays off once P1.5's contract fix is in
place (verbatim-quote binding + per-quote passage segmentation); this module
proves it pays off *through the CLI*, the only call site real runs use.

* P3-02 -- flag-off regression: `ledger_write_enabled=false` must produce
  byte-identical artifacts to the pre-feature baseline (mirrors the AAR's A2
  fix approach: assert the flag actually reaches its runtime consumer,
  don't assume the inverse of flag-on).
* P3-03 -- forward-write integration: `ledger_write_enabled=true` must
  increase the workspace ledger's assertion count with >=1 assertion bound
  to a verbatim quote, reusing P1-03's shared dual-workspace isolation
  fixture to also prove the CLI's forward write stays workspace-confined.
"""

from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

# P1-03 shared isolation fixture (phase-1-foundation.md): reuse rather than
# re-derive an equivalent two-workspace AssertionRegistry pair.
from tests.unit.test_assertion_workspace_isolation import (
    dual_workspace_registries,  # noqa: F401  (pytest fixture injection by name)
)
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.paths import FoundryPaths
from research_foundry.services import claim_mapping, extraction, source_cards
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.yamlio import dump_yaml, load_yaml

runner = CliRunner()

# The CLI hardcodes this literal per P1-01's single-operator resolution rule
# (assertion_workspace.py) -- not exposed as a new CLI argument.
DEFAULT_WORKSPACE_ID = "default"


def _invoke(args: list[str], cwd: Path):
    """Run `rf` from `cwd` so `FoundryPaths.discover()` resolves the tmp workspace."""

    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args)
    finally:
        os.chdir(prev)


def _set_ledger_write_enabled(paths: FoundryPaths, enabled: bool) -> None:
    foundry = load_yaml(paths.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": enabled}
    dump_yaml(foundry, paths.foundry_yaml)


def _write_source_file(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# P3-02: flag-off regression -- byte-identical to the pre-feature baseline.
# ---------------------------------------------------------------------------


def test_rf_ingest_flag_off_is_byte_identical_to_pre_feature_baseline(
    tmp_foundry: FoundryPaths, tmp_path: Path
) -> None:
    """Mirrors the AAR's A2 fix approach (per phase-3-4 plan): assert the
    ``ledger_write_enabled=false`` flag actually reaches ``ingest_source``'s
    runtime consumer *through the real CLI entry point*, rather than assuming
    the inverse of the flag-on test. "Pre-feature baseline" is simulated by
    calling ``ingest_source()`` directly with no
    ``assertion_registry_workspace_id`` at all -- the exact shape the CLI
    used to call it before P3-01's wiring -- against the SAME run/locator/
    title, then re-running the identical inputs through the now-wired CLI
    (flag off) and diffing every produced artifact byte-for-byte. Every id
    involved (source_card_id, claim ledger id) is content-derived and every
    timestamp is pinned by the suite's autouse fixed-clock fixture, so a
    second identical write is expected to be byte-for-byte idempotent -- any
    divergence would mean the CLI's new workspace-id wiring leaked into the
    artifact despite the flag being off.
    """

    _set_ledger_write_enabled(tmp_foundry, False)
    run_id = "rf_run_p3_flagoff_regression"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    content = "The average research task takes around 3 minutes to complete."
    source_file = _write_source_file(tmp_path, "evidence.txt", content)

    # (1) "Pre-feature" baseline: ingest_source() called exactly as the CLI
    # called it before P3-01 (no assertion_registry_workspace_id kwarg).
    baseline = source_cards.ingest_source(
        str(source_file),
        run_id=run_id,
        title="Flag Off Regression",
        sensitivity="personal",
        source_type="other",
        paths=tmp_foundry,
    )
    assert not (tmp_foundry.root / "assertion_ledger").exists()
    baseline_card_bytes = baseline.path.read_bytes()
    baseline_index_bytes = (tmp_foundry.registries / "source_index.yaml").read_bytes()

    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    baseline_ledger_bytes = tmp_foundry.run_paths(run_id).claim_ledger.read_bytes()

    # (2) Post-P3-01 CLI, same run/locator/title, flag still off. The CLI now
    # resolves a real (non-None) workspace_id ("default") and passes it to
    # ingest_source -- proving that alone does not change any artifact while
    # ledger_write_enabled=false.
    result = _invoke(
        [
            "ingest",
            str(source_file),
            "--run",
            run_id,
            "--title",
            "Flag Off Regression",
            "--sensitivity",
            "personal",
            "--source-type",
            "other",
        ],
        tmp_foundry.root,
    )
    assert result.exit_code == 0, result.output
    assert not (tmp_foundry.root / "assertion_ledger").exists()

    assert baseline.path.read_bytes() == baseline_card_bytes
    assert (tmp_foundry.registries / "source_index.yaml").read_bytes() == baseline_index_bytes

    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    assert tmp_foundry.run_paths(run_id).claim_ledger.read_bytes() == baseline_ledger_bytes


# ---------------------------------------------------------------------------
# P3-03: forward-write integration -- flag on increases the ledger's
# assertion count with >=1 verbatim-quote-bound assertion.
# ---------------------------------------------------------------------------


def test_rf_ingest_flag_on_forward_writes_verbatim_quote_bound_assertion(
    tmp_foundry: FoundryPaths,
    tmp_path: Path,
    dual_workspace_registries,  # noqa: F811 (pytest fixture injection by name)
) -> None:
    """Proves P3-01's *CLI* wiring -- not just ``ingest_source()`` called
    directly with an explicit ``workspace_id`` the way P1.5-03's own AC-8
    proof does -- reaches the real forward-write entry point. A fresh run's
    ``rf ingest`` (flag on) resolves the single-operator workspace id
    ("default") through P1's ``resolve_or_deny`` gate, threading it into
    ``ingest_source`` so the run's verbatim quote is segmented into the
    ``AssertionRegistry`` as a passage; running the rest of the (unmodified)
    forward pipeline then materializes >=1 assertion bound to that exact
    quote -- the workspace ledger's assertion count goes from 0 to >=1.
    """

    _set_ledger_write_enabled(tmp_foundry, True)
    run_id = "rf_run_p3_forward_write"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    quote = "The measured result was 42 percent."
    source_file = _write_source_file(tmp_path, "evidence.txt", quote)

    materializer = AssertionMaterializer(workspace_id=DEFAULT_WORKSPACE_ID, paths=tmp_foundry)
    assert not (materializer.root / "assertions").exists()  # before: zero assertions

    result = _invoke(
        [
            "ingest",
            str(source_file),
            "--run",
            run_id,
            "--title",
            "Forward Write Evidence",
            "--sensitivity",
            "personal",
            "--source-type",
            "other",
        ],
        tmp_foundry.root,
    )
    assert result.exit_code == 0, result.output

    source_path = next(tmp_foundry.run_paths(run_id).sources.glob("*.md"))
    source_card_id = source_path.stem

    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)

    materialization = materializer.materialize_run(run_id)

    assert materialization.status == "materialized"
    assert len(materialization.assertion_ids) >= 1

    # Independent proof, not merely inferred from materialize_run()'s success
    # (mirrors P1.5-03's AC-8 methodology, test_assertion_materialization.py
    # ::test_ac8_verbatim_quote_forward_yield_proof_end_to_end): a direct
    # find_exact_passages() call confirms the CLI-driven ingest actually
    # segmented and bound the verbatim quote in the registry.
    matches = materializer.registry.find_exact_passages(source_card_id, quote)
    assert len(matches) >= 1

    assertion = load_yaml(materializer._assertion_path(materialization.assertion_ids[0]))
    assert assertion["assertion_text"] == quote
    assert assertion["assertion_text_sha256"] == sha256(quote.encode("utf-8")).hexdigest()

    # The workspace ledger's assertion count: 0 -> >=1.
    assertions_dir = materializer.root / "assertions"
    assert assertions_dir.exists()
    assert len(list(assertions_dir.glob("*.yaml"))) >= 1

    # Reuse P1-03's shared isolation fixture (test_assertion_workspace_isolation
    # .py): the CLI's forward write is confined to the "default" workspace it
    # resolved -- a differently keyed workspace registry (P1-03's alpha/bravo
    # pair) must show zero presence of this quote, proving the CLI wiring
    # does not break cross-workspace isolation.
    cross_workspace_matches = dual_workspace_registries.alpha.find_exact_passages(source_card_id, quote)
    assert cross_workspace_matches == ()
    assert dual_workspace_registries.alpha.root.exists() is False


# ---------------------------------------------------------------------------
# P6 DI-1 F1: ingest_source() self-gates resolve_or_deny rather than trusting
# an already-checked caller (e.g. the CLI, which resolves "default" before
# calling in). A direct caller passing an unchecked, whitespace-only
# workspace id must be denied by ingest_source() itself.
# ---------------------------------------------------------------------------


def test_ingest_source_whitespace_only_workspace_id_skips_ledger_write_without_raising(
    tmp_foundry: FoundryPaths, tmp_path: Path
) -> None:
    """A whitespace-only ``assertion_registry_workspace_id`` passed directly to
    ``ingest_source()`` (bypassing the CLI's own ``resolve_or_deny("default")``
    call) must deny exactly like ``None`` -- zero ledger writes, no exception
    -- while ``ledger_write_enabled=True`` (so the denial is provably due to
    the blank workspace id, not the flag), and the source-card markdown is
    still written normally.
    """

    _set_ledger_write_enabled(tmp_foundry, True)
    run_id = "rf_run_p6_di1_f1_whitespace_workspace"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    content = "The measured result was 42 percent."
    source_file = _write_source_file(tmp_path, "evidence.txt", content)

    result = source_cards.ingest_source(
        str(source_file),
        run_id=run_id,
        title="Whitespace Workspace",
        sensitivity="personal",
        source_type="other",
        assertion_registry_workspace_id="   ",
        paths=tmp_foundry,
    )

    assert result.degraded is False
    assert result.path.is_file()
    assert not (tmp_foundry.root / "assertion_ledger").exists()
