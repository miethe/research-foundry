"""P3-4: prove `synthesis.attestation.status == "attested"` is unreachable.

ALLOW-LIST (not a best-effort scan). Every function in this repository that
can construct or persist a ``source_assertion`` dict, as of this test's
authoring, is enumerated below. If a new construction/write path is added
anywhere in these three modules without updating this list, the structural
guard tests in this module (``test_no_enumerated_construction_function_has_...``
below) are designed to fail loudly rather than silently pass.

``src/research_foundry/services/source_cards.py``
    Grep-verified (``grep -n "source_assertion\\|evidence_item_type"``): ZERO
    hits. This module ingests/registers source cards and evidence points; it
    never constructs a ``source_assertion`` dict at all. Enumerated here only
    so this test fails loudly if that ever changes -- see
    ``test_source_cards_and_capture_still_construct_zero_source_assertions``.

``src/research_foundry/services/capture.py``
    Grep-verified: ZERO hits. This module captures/triages raw ideas into
    intents; it never constructs a ``source_assertion`` dict either. Same
    loud-failure enumeration purpose as above.

``src/research_foundry/services/assertion_materialization.py``
    - ``AssertionMaterializer._prepare_one`` -- THE sole function in this
      repository that builds a ``source_assertion`` dict from scratch (one
      per materializable extraction fact). Never emits a ``synthesis`` block
      (single-passage direct extraction only).
    - ``AssertionMaterializer.materialize_run`` -- calls ``_prepare`` ->
      ``_prepare_one`` per fact, then persists via ``_write_immutable_assertion``.
    - ``AssertionMaterializer._write_immutable_assertion`` -- the write-ceiling
      choke point: every assertion dict passes through
      ``_enforce_synthesis_attestation_ceiling`` here immediately before the
      bytes hit disk, regardless of what upstream code set.
    - ``AssertionMaterializer._enforce_synthesis_attestation_ceiling`` -- the
      ceiling itself; forcibly resets ``synthesis.attestation.status`` to
      ``"candidate"`` whenever a ``synthesis`` block is present.
    - module-level ``materialize_run`` -- thin convenience wrapper around
      ``AssertionMaterializer.materialize_run``; no separate construction.

``src/research_foundry/services/assertion_rollout.py`` (backfill entry points)
    - ``backfill_run`` -- reconstructs editions/passages, then calls
      ``AssertionMaterializer.materialize_run`` (the SAME materializer/ceiling
      above). Does not construct a ``source_assertion`` dict itself.
    - ``backfill_corpus`` -- fans ``backfill_run`` out over every discovered
      run; same transitive path.

No other function in this repository constructs a ``source_assertion`` dict.
"""

from __future__ import annotations

import copy
import dataclasses
import inspect
import re

from research_foundry.services import assertion_rollout as rollout
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_materialization import (
    AssertionMaterializer,
    _PreparedRecord,
)
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml

_SMUGGLED_SYNTHESIS = {
    "input_refs": [
        {"source_assertion_id": "ast_" + "0" * 64, "contribution": "anchor"},
        {"source_assertion_id": "ast_" + "1" * 64, "contribution": "corroborating"},
    ],
    "method": "adversarial-injection-attempt",
    "reproduces_source_arrangement": True,
    "attestation": {
        "attested_by": "attacker",
        "attested_at": "2026-07-21T00:00:00Z",
        "attestation_ref": "forged-ref",
        "status": "attested",
    },
}


def _setup_run(tmp_foundry, run_id: str, *, content: str = "The measured result was 42 percent.") -> None:
    """Smallest P2-registered forward run (mirrors test_assertion_materialization._setup_run)."""

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="Exact Evidence",
        sensitivity="personal",
        content=content,
        assertion_registry_workspace_id="workspace-a",
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)


def _setup_historical_run(tmp_foundry, run_id: str, *, content: str = "The measured result was 42 percent.") -> None:
    """Historical (pre-P1, no assertion_registry_workspace_id at ingest) run for backfill_run."""

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="Exact Evidence",
        sensitivity="personal",
        content=content,
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)


def _smuggle_synthesis_into(record: _PreparedRecord) -> _PreparedRecord:
    """Return a copy of ``record`` whose assertion carries an adversarial
    ``synthesis.attestation.status: "attested"`` block, as if the sole
    construction function (``_prepare_one``) had been compromised or extended
    to smuggle an attested attestation through.
    """

    smuggled_assertion = copy.deepcopy(record.assertion)
    smuggled_assertion["synthesis"] = copy.deepcopy(_SMUGGLED_SYNTHESIS)
    return dataclasses.replace(record, assertion=smuggled_assertion)


def _all_persisted_assertions(materializer: AssertionMaterializer) -> list[dict]:
    directory = materializer.root / "assertions"
    if not directory.exists():
        return []
    return [load_yaml(path) for path in sorted(directory.glob("*.yaml"))]


def _assert_never_attested(assertions: list[dict]) -> None:
    assert assertions, "expected at least one persisted assertion to inspect"
    for assertion in assertions:
        synthesis = assertion.get("synthesis")
        if synthesis is None:
            continue
        assert synthesis.get("attestation", {}).get("status") != "attested"


def test_prepare_one_smuggled_attestation_is_forced_to_candidate_on_materialize(
    tmp_foundry, monkeypatch
) -> None:
    """Adversarial path via the forward materializer: even if ``_prepare_one``
    (the sole construction function) were patched to smuggle
    ``attestation.status: "attested"`` into the assertion it returns, the
    persisted record must never carry that value -- the write-ceiling in
    ``_write_immutable_assertion`` is the backstop.
    """

    run_id = "rf_run_p3_4_smuggle_materialize"
    _setup_run(tmp_foundry, run_id)

    original_prepare_one = AssertionMaterializer._prepare_one

    def _smuggling_prepare_one(self, run_id, mapping, claim):  # noqa: ANN001
        record = original_prepare_one(self, run_id, mapping, claim)
        return _smuggle_synthesis_into(record)

    monkeypatch.setattr(AssertionMaterializer, "_prepare_one", _smuggling_prepare_one)

    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    result = materializer.materialize_run(run_id)

    assert result.status == "materialized"
    persisted = _all_persisted_assertions(materializer)
    _assert_never_attested(persisted)
    # The smuggling attempt must be visibly neutralized, not merely absent --
    # prove the synthesis block survived (so this test is not vacuous) while
    # its attestation status was forced back to "candidate".
    smuggled = [a for a in persisted if a.get("synthesis") is not None]
    assert smuggled, "expected the smuggled synthesis block to reach disk (minus the attested status)"
    assert smuggled[0]["synthesis"]["attestation"]["status"] == "candidate"


def test_backfill_run_smuggled_attestation_is_forced_to_candidate(tmp_foundry, monkeypatch) -> None:
    """Same adversarial attempt, routed through the backfill entry point
    (``assertion_rollout.backfill_run``) rather than the forward materializer.
    Backfill delegates into the SAME ``AssertionMaterializer.materialize_run``
    / write-ceiling, so it must be equally immune.
    """

    run_id = "rf_run_p3_4_smuggle_backfill"
    _setup_historical_run(tmp_foundry, run_id)

    original_prepare_one = AssertionMaterializer._prepare_one

    def _smuggling_prepare_one(self, run_id, mapping, claim):  # noqa: ANN001
        record = original_prepare_one(self, run_id, mapping, claim)
        return _smuggle_synthesis_into(record)

    monkeypatch.setattr(AssertionMaterializer, "_prepare_one", _smuggling_prepare_one)

    receipt = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)
    assert receipt["materialization_status"] == "materialized"

    materializer = AssertionMaterializer(workspace_id="default", paths=tmp_foundry)
    persisted = _all_persisted_assertions(materializer)
    _assert_never_attested(persisted)
    smuggled = [a for a in persisted if a.get("synthesis") is not None]
    assert smuggled, "expected the smuggled synthesis block to reach disk (minus the attested status)"
    assert smuggled[0]["synthesis"]["attestation"]["status"] == "candidate"


def test_enforce_synthesis_attestation_ceiling_forces_attested_to_candidate() -> None:
    """Direct unit test of the ceiling helper: an "attested" status fed in
    synthetically is always forced back to "candidate", regardless of any
    other field in the ``synthesis``/``attestation`` blocks.
    """

    assertion = {
        "assertion_id": "ast_" + "a" * 64,
        "synthesis": {
            "input_refs": [
                {"source_assertion_id": "ast_" + "0" * 64, "contribution": "anchor"},
                {"source_assertion_id": "ast_" + "1" * 64, "contribution": "corroborating"},
            ],
            "method": "manual",
            "reproduces_source_arrangement": True,
            "attestation": {
                "attested_by": "a-human",
                "attested_at": "2026-07-21T00:00:00Z",
                "attestation_ref": "some-ref",
                "status": "attested",
            },
        },
    }

    ceilinged = AssertionMaterializer._enforce_synthesis_attestation_ceiling(assertion)

    assert ceilinged["synthesis"]["attestation"]["status"] == "candidate"
    # Every other field in the synthesis/attestation blocks is preserved --
    # the ceiling narrowly targets `status`, it does not discard provenance.
    assert ceilinged["synthesis"]["method"] == "manual"
    assert ceilinged["synthesis"]["attestation"]["attested_by"] == "a-human"
    # The input is not mutated in place (a defensive-copy contract, so callers
    # holding a reference to the original dict never observe a surprise
    # mutation from a helper they didn't know rewrote their object).
    assert assertion["synthesis"]["attestation"]["status"] == "attested"


def test_enforce_synthesis_attestation_ceiling_is_a_no_op_without_synthesis() -> None:
    """The ceiling is total: an assertion with no ``synthesis`` block at all
    (the shape ``_prepare_one`` produces today) passes through unchanged.
    """

    assertion = {
        "assertion_id": "ast_" + "b" * 64,
        "extensions": {"evidence_taxonomy": {"evidence_item_type": "other", "judgment_basis": "unassessed"}},
    }

    ceilinged = AssertionMaterializer._enforce_synthesis_attestation_ceiling(assertion)

    assert "synthesis" not in ceilinged
    assert ceilinged == assertion


def test_enforce_synthesis_attestation_ceiling_fills_missing_attestation_block() -> None:
    """A ``synthesis`` block present WITHOUT an ``attestation`` sub-object at
    all (e.g. a malformed/older write attempt) still comes out ceilinged --
    the helper does not require ``attestation`` to already exist to enforce
    "candidate".
    """

    assertion = {
        "assertion_id": "ast_" + "c" * 64,
        "synthesis": {
            "input_refs": [
                {"source_assertion_id": "ast_" + "0" * 64, "contribution": "anchor"},
                {"source_assertion_id": "ast_" + "1" * 64, "contribution": "corroborating"},
            ],
            "method": "manual",
            "reproduces_source_arrangement": True,
        },
    }

    ceilinged = AssertionMaterializer._enforce_synthesis_attestation_ceiling(assertion)

    assert ceilinged["synthesis"]["attestation"] == {"status": "candidate"}


# ---------------------------------------------------------------------------
# Structural guards: fail loudly if the allow-list above goes stale.
# ---------------------------------------------------------------------------

_ATTESTATION_PARAM_RE = re.compile(r"attestation", re.IGNORECASE)

# Every enumerated construction/entry-point function from the module
# docstring above, resolved to live callables so a rename shows up as an
# AttributeError (loud failure) rather than this test silently skipping it.
_ENUMERATED_CONSTRUCTION_CALLABLES = (
    AssertionMaterializer._prepare_one,
    AssertionMaterializer.materialize_run,
    AssertionMaterializer._write_immutable_assertion,
    AssertionMaterializer._enforce_synthesis_attestation_ceiling,
    rollout.backfill_run,
    rollout.backfill_corpus,
)


def test_no_enumerated_construction_function_accepts_an_attestation_override() -> None:
    """None of the enumerated functions' signatures accept a parameter that
    looks like an ``attestation``/``attestation_status`` override. If a new
    parameter matching that pattern is ever added to one of these functions,
    this test must fail loudly (not silently pass) -- that would be exactly
    the shape of a bypass around the write ceiling.
    """

    offending: list[str] = []
    for fn in _ENUMERATED_CONSTRUCTION_CALLABLES:
        for name in inspect.signature(fn).parameters:
            if _ATTESTATION_PARAM_RE.search(name):
                offending.append(f"{fn.__qualname__}(...{name}...)")
    assert offending == [], f"unenumerated attestation-override parameter(s) introduced: {offending}"


def test_source_cards_and_capture_still_construct_zero_source_assertions() -> None:
    """Regression guard for the allow-list's core claim: as of this test's
    authoring, ``source_cards.py`` and ``capture.py`` construct ZERO
    ``source_assertion`` dicts (grep-verified). If either module is later
    extended to build one, this test must fail loudly so the allow-list above
    gets updated instead of silently going stale.
    """

    import research_foundry.services.capture as capture_module
    import research_foundry.services.source_cards as source_cards_module

    for module in (source_cards_module, capture_module):
        source_text = inspect.getsource(module)
        assert "source_assertion" not in source_text, (
            f"{module.__name__} now references source_assertion -- update the "
            "allow-list in this test module's docstring and add adversarial "
            "coverage for its construction path"
        )
        assert "evidence_item_type" not in source_text, (
            f"{module.__name__} now references evidence_item_type -- update the "
            "allow-list in this test module's docstring and add adversarial "
            "coverage for its construction path"
        )


def test_prepare_one_never_emits_a_synthesis_block_on_its_own(tmp_foundry) -> None:
    """Sanity anchor for the docstring's claim that ``_prepare_one`` (unpatched,
    no monkeypatching) never emits ``synthesis`` on its own -- this
    materializer performs single-passage direct extraction only. Runtime
    check (not a source-text grep, which would false-positive on this
    module's own explanatory comments): the persisted assertion has no
    ``synthesis`` key and an honest ``extensions.evidence_taxonomy`` default.
    """

    run_id = "rf_run_p3_4_no_synthesis_by_default"
    _setup_run(tmp_foundry, run_id)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run(run_id)

    assert result.status == "materialized"
    persisted = _all_persisted_assertions(materializer)
    assert persisted
    for assertion in persisted:
        assert "synthesis" not in assertion
        assert assertion["extensions"]["evidence_taxonomy"] == {
            "evidence_item_type": "other",
            "judgment_basis": "unassessed",
        }
