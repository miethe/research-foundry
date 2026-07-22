"""P5-2: prove the 4 rights-clearance write-ceiling fields are unreachable
to a ``CLEARED_*``/``counsel_approved``/``OWNED``-without-first-party-basis
value from any agent-writable code path.

**Independent of** ``tests/unit/test_synthesis_attestation_write_ceiling.py``
(P3-4). That module proves the *other* half of the §9.10 authorization
boundary (``synthesis.attestation.status`` inside ``assertion_materialization.py``
only). This module proves the remaining 4 named fields (FR-23):

    - ``rights_record.overall_status``
    - ``content_reuse_assessment.decision.status``
    - ``content_reuse_assessment.decision.release_gate``
    - ``rights_extension.clearance_status``

across a DIFFERENT set of write paths, and does not import from, extend, or
rely on that module. Combined, the two modules close both write paths named
in the handoff review's §9.10 finding.

ALLOW-LIST (not a best-effort scan). Grep-verified
(``grep -n '"overall_status"\\|"release_gate"\\|"clearance_status"\\|content_reuse_assessment\\|rights_extension_id'``)
across every module named in this task, as of this test's authoring:

``src/research_foundry/services/rights_backfill.py``
    - ``all_unknown_rights_summary`` -- the ONLY function anywhere in this
      repository that assigns a literal ``"clearance_status": ...`` dict key.
      Hardcoded to the string ``"UNKNOWN"``; takes zero parameters, so there
      is no channel for a caller to substitute any other value.
    - ``_backfill_one`` / ``backfill_rights_summary`` -- persist
      ``all_unknown_rights_summary()`` onto legacy instances that lack a
      ``rights_summary`` entirely; non-clobbering (skip if already present).
      Neither accepts a parameter that could override the mirror's value.
    - Constructs ZERO ``rights_record``, ``content_reuse_assessment``, or
      ``rights_extension`` objects. (The dict key ``"rights_record_ids"`` at
      line 77 is a *list-of-ids* field on the ``rights_summary`` mirror, not
      the ``rights_record`` object itself -- this module has no loader or
      writer for that object at all.)

``src/research_foundry/services/rights_triage.py``
    - ``_classify_capture_rights`` -- always returns
      ``rights_backfill.all_unknown_rights_summary()`` unmodified (no real
      classification signal exists at bare-ingest time; see the module's own
      docstring). Takes zero parameters.
    - ``compute_capture_rights_summary`` -- wraps the above; degrades to the
      same all-``"unknown"`` block (plus a ``rights_triage_failure`` record)
      if the classifier raises. Never raises itself, never accepts an
      override parameter.
    - ``maybe_assess_substitutability`` -- reads ``rights_summary["clearance_status"]``
      to decide whether to *search* for a substitute; never writes
      ``clearance_status``, ``overall_status``, or ``release_gate`` anywhere.
    - Constructs ZERO ``rights_record``/``content_reuse_assessment``/``rights_extension``
      objects (grep-verified: every mention of ``rights_record`` in this
      module is prose in a docstring explaining why no such object exists).

``src/research_foundry/services/rights_substitutability.py``
    - ``is_blocking_clearance_status``, ``assess_substitutability``,
      ``find_substitute_candidates`` -- pure *consumers* of a caller-supplied
      ``clearance_status`` string (used only to decide whether to run a
      keyword search); none of the three ever assigns a value to
      ``clearance_status``, ``overall_status``, ``release_gate``, or
      ``decision.status``, nor constructs a ``rights_record``/
      ``content_reuse_assessment``/``rights_extension`` object. The module's
      own return type (``SubstitutabilityAssessment``: ``searched_at``,
      ``status``, ``candidate_source_ids``, ``coverage_notes``) shares no
      field name with any of the 4 governed fields.

``src/research_foundry/services/rights_validation.py``
    - ``check_rights_divergence`` / ``_check_one`` / ``_compare_mirror_to_record``
      -- READ-ONLY. Compares an already-persisted ``rights_summary`` mirror
      against an already-persisted, caller-supplied ``rights_record`` YAML
      file; never writes to either.
    - ``_load_rights_record`` -- the ONLY function in this module that opens
      a ``rights_record`` file; it is a pure loader (``load_yaml`` only, no
      ``dump_yaml`` call anywhere in this module) and returns ``None`` for
      anything unresolvable.
    - Constructs/persists ZERO ``rights_record``, ``content_reuse_assessment``,
      or ``rights_extension`` objects (this module explicitly documents, in
      its own docstring, that it "has no loader" for ``rights_extension`` at
      all).

``src/research_foundry/services/source_cards.py``
    - ``ingest_source`` -- the sole ``source_card`` construction function.
      Calls ``rights_triage.compute_capture_rights_summary()`` (above) and
      ``rights_triage.maybe_assess_substitutability`` verbatim, with no
      parameter of its own that could set ``rights_summary.clearance_status``,
      let alone any of the 4 governed fields. Constructs ZERO ``rights_record``/
      ``content_reuse_assessment``/``rights_extension`` objects.

``src/research_foundry/services/assertion_materialization.py``
    - ``AssertionMaterializer._prepare_one`` -- same treatment as
      ``ingest_source`` above, for ``source_assertion`` instances: calls the
      SAME two ``rights_triage`` functions verbatim. Constructs ZERO
      ``rights_record``/``content_reuse_assessment``/``rights_extension``
      objects. (This module's own write ceiling for the *other* §9.10 field,
      ``synthesis.attestation.status``, is covered independently by P3-4 --
      not retested here.)

``src/research_foundry/cli_commands.py`` (``rights_app`` sub-app)
    - ``rights_inspect`` / ``rights_list`` / ``rights_validate`` -- READ-ONLY
      display commands; the one ``"clearance_status": ...`` dict-key write
      at line ~2676 builds an in-memory display row from
      ``rights_summary.get("clearance_status", ...)`` for table/JSON output
      -- it is never persisted back to disk.
    - ``rights_backfill`` (the CLI command) -- thin wrapper around
      ``rights_backfill.backfill_rights_summary`` (above); no additional
      write surface.
    - Constructs/persists ZERO ``rights_record``/``content_reuse_assessment``/
      ``rights_extension`` objects.

``src/research_foundry/services/writeback.py`` and
``src/research_foundry/api/routers/writeback.py``
    - CONFUSABLE NAME, UNRELATED FIELD. The one ``"overall_status": ...``
      dict-key write anywhere across the 9 modules named in this task lives
      in ``api/routers/writeback.py`` and sets a
      ``WritebackResult``/response-envelope's batch-outcome field (Literal
      ``"success"``/``"partial"``/``"blocked"``) -- it has nothing to do
      with ``rights_record.overall_status``. Grep-verified: neither file
      contains ``rights_record``, ``content_reuse_assessment``,
      ``rights_extension``, or ``clearance_status`` anywhere.

No other function in any of these 9 modules constructs, mutates, or persists
a ``rights_record``, ``content_reuse_assessment``, or ``rights_extension``
object, or writes ``"release_gate"`` at all. Combined with the governance
guard's rule 7 (``no_agent_cleared_rights_value``, P5-1) covering 3 of the 4
fields by name at the policy layer, this closes the service-layer half of
the FR-23 write ceiling that P5-1 alone cannot prove (a policy rule is only
as good as the callers that invoke it with an accurate ``proposed_field_writes``
tuple -- this module proves the *actual* write paths never produce the
disallowed shape in the first place, independent of whether any caller
remembers to consult the guard).

``content_reuse_assessment.decision.release_gate`` is deliberately NOT one of
the fields enumerated in rule 7's ``_RIGHTS_GOVERNED_FIELDS`` (P5-1's own
scope, matching the implementation plan row: P5-3, a separate later task, is
where a *different* release-gate predicate -- unrelated to this ceiling --
gets added). That non-coverage is safe today for two independent reasons,
both proven below: (1) zero code path anywhere constructs a
``content_reuse_assessment`` object at all, and (2) ``release_gate``'s own
schema enum (``PASS``/``PASS_WITH_CONDITIONS``/``BLOCK``) structurally
excludes ``CLEARED_*``/``counsel_approved`` values regardless.
"""

from __future__ import annotations

import inspect
import os
import re
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import (
    claim_mapping,
    extraction,
    rights_backfill,
    rights_substitutability,
    rights_triage,
    rights_validation,
)
from research_foundry.services import assertion_materialization as materialization
from research_foundry.services import source_cards
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.governance import GuardContext, guard_check
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Disallowed-value vocabulary shared with the governance guard (FR-23).
# ---------------------------------------------------------------------------

_CLEARED_VALUE = "CLEARED_OPEN_LICENSE"
_DISALLOWED_EXACT_VALUES = ("counsel_approved", "attested")
_GOVERNED_OBJECT_NAMES = ("rights_record", "content_reuse_assessment", "rights_extension")


def _recursive_keys(value: Any) -> set[str]:
    """All dict keys anywhere in a nested structure (recursion, for scanning
    a persisted YAML/front-matter payload for a governed object's presence)."""

    keys: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            keys.add(k)
            keys |= _recursive_keys(v)
    elif isinstance(value, list):
        for item in value:
            keys |= _recursive_keys(item)
    return keys


def _source_text(module: Any) -> str:
    return inspect.getsource(module)


def _invoke_cli(args: list[str], cwd: Path):
    """Run the CLI from ``cwd`` so workspace discovery resolves to the tmp
    root (mirrors ``tests/test_cli_rights.py``'s own ``_invoke`` helper --
    duplicated rather than imported, per this module's independence
    requirement)."""

    runner = CliRunner()
    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(prev)


# ---------------------------------------------------------------------------
# Structural guards: grep-equivalent, fail loudly if the allow-list above
# goes stale (mirrors test_synthesis_attestation_write_ceiling.py's pattern).
# ---------------------------------------------------------------------------

_ENUMERATED_MODULES = (
    rights_backfill,
    rights_triage,
    rights_substitutability,
    rights_validation,
    source_cards,
    materialization,
)
_ENUMERATED_MODULE_PATHS = (
    "src/research_foundry/cli_commands.py",
    "src/research_foundry/api/routers/writeback.py",
    "src/research_foundry/services/writeback.py",
)


def test_content_reuse_assessment_object_never_constructed_in_any_enumerated_module() -> None:
    """Zero-hit claim: ``content_reuse_assessment`` (the object that carries
    2 of the 4 governed fields -- ``decision.status``/``decision.release_gate``)
    is never referenced -- let alone constructed -- anywhere across the 6
    importable service modules named in this task. If this ever becomes
    nonzero, the allow-list above and this test module both need updating
    with real adversarial coverage for the new construction path.
    """

    offenders = [m.__name__ for m in _ENUMERATED_MODULES if "content_reuse_assessment" in _source_text(m)]
    assert offenders == [], f"content_reuse_assessment now referenced in: {offenders}"

    repo_root = Path(__file__).resolve().parents[2]
    for rel_path in _ENUMERATED_MODULE_PATHS:
        text = (repo_root / rel_path).read_text(encoding="utf-8")
        assert "content_reuse_assessment" not in text, rel_path


def test_rights_extension_object_never_constructed_in_any_enumerated_module() -> None:
    """Zero-hit claim for the object carrying the 4th governed field
    (``rights_extension.clearance_status``): no module ever constructs a
    ``rights_extension_id`` (the object's own identity field -- a stricter,
    unambiguous proxy for "this code builds a rights_extension instance"
    than the bare substring ``rights_extension``, which also appears in
    explanatory docstring prose across several of these modules).
    """

    offenders = [m.__name__ for m in _ENUMERATED_MODULES if "rights_extension_id" in _source_text(m)]
    assert offenders == [], f"rights_extension_id now referenced in: {offenders}"

    repo_root = Path(__file__).resolve().parents[2]
    for rel_path in _ENUMERATED_MODULE_PATHS:
        text = (repo_root / rel_path).read_text(encoding="utf-8")
        assert "rights_extension_id" not in text, rel_path


def test_release_gate_key_never_written_in_any_enumerated_module() -> None:
    """``"release_gate"`` (the literal dict key) has zero write sites across
    every module named in this task -- grep-verified before this test was
    authored. This is a total-absence claim, not a value-level one: since no
    code writes the key at all, it cannot carry a disallowed value.
    """

    pattern = re.compile(r'"release_gate"\s*:')
    offenders = [m.__name__ for m in _ENUMERATED_MODULES if pattern.search(_source_text(m))]
    assert offenders == [], f'"release_gate": now written in: {offenders}'

    repo_root = Path(__file__).resolve().parents[2]
    for rel_path in _ENUMERATED_MODULE_PATHS:
        text = (repo_root / rel_path).read_text(encoding="utf-8")
        assert not pattern.search(text), rel_path


def test_overall_status_key_write_site_is_exactly_the_unrelated_writeback_receipt() -> None:
    """The literal ``"overall_status": ...`` dict-key write occurs at exactly
    ONE site across every module named in this task, and it is the
    confusably-named, semantically-unrelated ``WritebackResult`` batch-outcome
    field in ``api/routers/writeback.py`` -- never ``rights_record.overall_status``.
    A second write site appearing anywhere (including inside
    ``services/writeback.py``, which today has zero) must fail this test
    loudly rather than silently pass, since that would be exactly the shape
    of a new, unreviewed write path to the governed field.
    """

    pattern = re.compile(r'"overall_status"\s*:')
    hits_in_enumerated = [m.__name__ for m in _ENUMERATED_MODULES if pattern.search(_source_text(m))]
    assert hits_in_enumerated == [], f'"overall_status": found in enumerated modules: {hits_in_enumerated}'

    repo_root = Path(__file__).resolve().parents[2]
    hit_paths = [rel for rel in _ENUMERATED_MODULE_PATHS if pattern.search((repo_root / rel).read_text(encoding="utf-8"))]
    assert hit_paths == ["src/research_foundry/api/routers/writeback.py"], hit_paths

    # Sanity: the ONE hit is on a Literal["success", "partial"] field of a
    # response model, not anything that could hold "CLEARED_..."/"OWNED".
    writeback_router_text = (repo_root / "src/research_foundry/api/routers/writeback.py").read_text(encoding="utf-8")
    assert 'overall_status: Literal["success", "partial"]' in writeback_router_text


def test_clearance_status_key_write_sites_are_exactly_the_two_known_safe_ones() -> None:
    """The literal ``"clearance_status": ...`` dict-key write occurs at
    exactly 2 sites: the hardcoded ``"UNKNOWN"`` default in
    ``rights_backfill.all_unknown_rights_summary``, and an in-memory,
    read-then-display row in ``cli_commands.py``'s ``rights_list`` (never
    persisted). Both are on the ``rights_summary`` MIRROR, not the
    authoritative ``rights_extension`` object this task's 4th field names --
    this module contains zero writers for that object at all (see the two
    tests above). A third site appearing anywhere is a new write path this
    allow-list has not reviewed.
    """

    pattern = re.compile(r'"clearance_status"\s*:')

    service_hits = [m.__name__ for m in _ENUMERATED_MODULES if pattern.search(_source_text(m))]
    assert service_hits == ["research_foundry.services.rights_backfill"], service_hits

    repo_root = Path(__file__).resolve().parents[2]
    hit_paths = [rel for rel in _ENUMERATED_MODULE_PATHS if pattern.search((repo_root / rel).read_text(encoding="utf-8"))]
    assert hit_paths == ["src/research_foundry/cli_commands.py"], hit_paths


# ---------------------------------------------------------------------------
# Signature-scan guard: none of the construction/persistence functions
# accept a parameter shaped like a governed-field override.
# ---------------------------------------------------------------------------

_OVERRIDE_PARAM_RE = re.compile(r"overall_status|release_gate|decision_status|rights_extension", re.IGNORECASE)

_ENUMERATED_CONSTRUCTION_CALLABLES = (
    rights_backfill.all_unknown_rights_summary,
    rights_backfill.backfill_rights_summary,
    rights_backfill._backfill_one,
    rights_triage._classify_capture_rights,
    rights_triage.compute_capture_rights_summary,
    rights_validation.check_rights_divergence,
    rights_validation._check_one,
    rights_validation._load_rights_record,
    rights_validation._compare_mirror_to_record,
    ingest_source,
    AssertionMaterializer._prepare_one,
)


def test_no_enumerated_construction_function_accepts_a_governed_field_override() -> None:
    """None of the enumerated construction/persistence functions' signatures
    accept a parameter that looks like an override for
    ``overall_status``/``release_gate``/``decision.status``/``rights_extension``.
    (``clearance_status`` itself is deliberately excluded from this regex --
    several *consumer* functions elsewhere, e.g.
    ``rights_substitutability.is_blocking_clearance_status``, legitimately
    accept it as a read-only input to decide whether to search for a
    substitute; that is not a write-override and is covered by the
    structural guards above instead.) If a new parameter matching this
    pattern is ever added to one of these functions, this test must fail
    loudly.
    """

    offending: list[str] = []
    for fn in _ENUMERATED_CONSTRUCTION_CALLABLES:
        for name in inspect.signature(fn).parameters:
            if _OVERRIDE_PARAM_RE.search(name):
                offending.append(f"{fn.__qualname__}(...{name}...)")
    assert offending == [], f"unenumerated governed-field override parameter(s) introduced: {offending}"


def test_all_unknown_rights_summary_and_classify_capture_rights_take_zero_parameters() -> None:
    """The two functions that actually hardcode ``clearance_status: "UNKNOWN"``
    take literally zero parameters -- there is no channel, adversarial or
    otherwise, for a caller to substitute a different value through them.
    """

    assert inspect.signature(rights_backfill.all_unknown_rights_summary).parameters == {}
    assert inspect.signature(rights_triage._classify_capture_rights).parameters == {}
    assert inspect.signature(rights_triage.compute_capture_rights_summary).parameters == {}


# ---------------------------------------------------------------------------
# Behavioral tests: the real write paths, exercised end-to-end.
# ---------------------------------------------------------------------------


def test_all_unknown_rights_summary_clearance_status_is_unknown() -> None:
    summary = rights_backfill.all_unknown_rights_summary()
    assert summary["clearance_status"] == "UNKNOWN"
    assert not _recursive_keys(summary) & set(_GOVERNED_OBJECT_NAMES)


def test_compute_capture_rights_summary_clearance_status_is_unknown() -> None:
    summary = rights_triage.compute_capture_rights_summary()
    assert summary["clearance_status"] == "UNKNOWN"
    assert not _recursive_keys(summary) & set(_GOVERNED_OBJECT_NAMES)


def test_backfill_rights_summary_writes_only_unknown_clearance_status(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy_source.md"
    dump_md({"source_card_id": "src_legacy_001", "type": "source_card"}, "# Legacy\n", legacy)

    results = rights_backfill.backfill_rights_summary([legacy])

    assert results[0].action == rights_backfill.ACTION_BACKFILLED
    metadata, _body = load_md(legacy)
    assert metadata["rights_summary"]["clearance_status"] == "UNKNOWN"
    assert not _recursive_keys(metadata) & set(_GOVERNED_OBJECT_NAMES)


def test_backfill_rights_summary_never_clobbers_an_existing_mirror(tmp_path: Path) -> None:
    """Non-clobbering-by-construction: an instance already carrying a
    ``rights_summary`` (even an adversarially-authored one that some OTHER,
    unreviewed writer set) is left byte-for-byte untouched -- backfill never
    elevates, never rewrites, never "fixes" an existing value either way.
    """

    already_present = tmp_path / "already_present.md"
    adversarial_summary = rights_backfill.all_unknown_rights_summary()
    adversarial_summary["clearance_status"] = _CLEARED_VALUE
    dump_md(
        {"source_card_id": "src_present_001", "type": "source_card", "rights_summary": adversarial_summary},
        "# Present\n",
        already_present,
    )
    before = already_present.read_text(encoding="utf-8")

    results = rights_backfill.backfill_rights_summary([already_present])

    assert results[0].action == rights_backfill.ACTION_SKIPPED_PRESENT
    assert already_present.read_text(encoding="utf-8") == before


def test_ingest_source_persisted_rights_summary_is_unknown_with_no_governed_object(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_p5_2_ingest"
    tmp_foundry.run_paths(run_id).ensure_scaffold()

    result = ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="P5-2 Evidence",
        sensitivity="personal",
        content="The measured result was 42 percent.",
        paths=tmp_foundry,
    )

    metadata, _body = load_md(Path(result.path))
    assert metadata["rights_summary"]["clearance_status"] == "UNKNOWN"
    assert not _recursive_keys(metadata) & set(_GOVERNED_OBJECT_NAMES)


def _setup_run_for_materialization(tmp_foundry: FoundryPaths, run_id: str) -> None:
    """Minimal forward run so ``AssertionMaterializer.materialize_run`` has a
    claim to work with. Deliberately NOT imported from
    ``test_synthesis_attestation_write_ceiling.py`` -- this module's
    independence requirement extends to its fixtures, not just its
    assertions.
    """

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="P5-2 Materialization Evidence",
        sensitivity="personal",
        content="The measured result was 42 percent.",
        assertion_registry_workspace_id="workspace-p5-2",
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)


def test_prepare_one_persisted_rights_summary_is_unknown_with_no_governed_object(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_p5_2_materialize"
    _setup_run_for_materialization(tmp_foundry, run_id)

    materializer = AssertionMaterializer(workspace_id="workspace-p5-2", paths=tmp_foundry)
    result = materializer.materialize_run(run_id)
    assert result.status == "materialized"

    directory = materializer.root / "assertions"
    persisted = [load_yaml(p) for p in sorted(directory.glob("*.yaml"))]
    assert persisted, "expected at least one persisted assertion to inspect"
    for assertion in persisted:
        assert assertion["rights_summary"]["clearance_status"] == "UNKNOWN"
        assert not _recursive_keys(assertion) & set(_GOVERNED_OBJECT_NAMES)


def test_check_rights_divergence_never_writes_the_crafted_authoritative_record(tmp_path: Path) -> None:
    """Adversarial input via the ONE read path that ever opens a
    ``rights_record`` file at all (``rights_validation._load_rights_record``):
    even when the on-disk authoritative record already carries a disallowed
    ``overall_status`` (as if some OTHER, out-of-scope system had written it
    -- this module has no writer of its own to test adversarial mutation
    against), ``check_rights_divergence`` never rewrites that file, never
    copies the disallowed value onto the mirror it's checking, and never
    constructs a ``content_reuse_assessment``/``rights_extension`` object as
    a side effect.
    """

    records_dir = tmp_path / "rights_records"
    records_dir.mkdir(parents=True)
    record_path = records_dir / "rr_p5_2_crafted.yaml"
    dump_yaml(
        {
            "schema_version": "1.0",
            "rights_record_id": "rr_p5_2_crafted",
            "source_id": "src_demo",
            "record_scope": "source",
            "jurisdictions": ["US"],
            "access": {"basis": "public_web"},
            "copyright": {"status": "copyrighted"},
            "component_decisions": [],
            "overall_status": _CLEARED_VALUE,
            "review": {"reviewed_at": "2026-07-21T12:00:00Z", "review_status": "agent_triage_only"},
        },
        record_path,
    )
    before = record_path.read_text(encoding="utf-8")

    card = tmp_path / "src_p5_2_crafted.md"
    mirror = rights_backfill.all_unknown_rights_summary()
    mirror["rights_record_ids"] = ["rr_p5_2_crafted"]
    mirror["access_basis"] = "public_web"
    dump_md({"source_card_id": "src_p5_2_crafted", "type": "source_card", "rights_summary": mirror}, "# X\n", card)

    results = rights_validation.check_rights_divergence(
        [card], as_of="2026-07-21", rights_records_dir=records_dir
    )

    # The authoritative record file is never rewritten by the check.
    assert record_path.read_text(encoding="utf-8") == before
    # The mirror's own clearance_status is unaffected -- still "UNKNOWN".
    metadata, _body = load_md(card)
    assert metadata["rights_summary"]["clearance_status"] == "UNKNOWN"
    assert not _recursive_keys(metadata) & set(_GOVERNED_OBJECT_NAMES)
    # No new files were created anywhere under tmp_path as a side effect.
    assert sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == sorted(
        p.name for p in [record_path, card]
    )
    assert results  # sanity: the check actually ran


def test_cli_rights_inspect_never_writes_back_a_crafted_cleared_record(tmp_foundry: FoundryPaths) -> None:
    """Same adversarial shape as the test above, routed through the full
    ``rf rights inspect`` CLI surface rather than calling the service
    function directly -- proving the CLI layer (``cli_commands.py``) adds no
    write path of its own on top of the read-only service function it calls.
    """

    run_id = "run_p5_2_cli"
    card_path = tmp_foundry.runs / run_id / "source_cards" / "src_p5_2_cli.md"
    mirror = rights_backfill.all_unknown_rights_summary()
    mirror["rights_record_ids"] = ["rr_p5_2_cli_crafted"]
    dump_md(
        {"source_card_id": "src_p5_2_cli", "type": "source_card", "rights_summary": mirror},
        "# X\n",
        card_path,
    )
    before_card = card_path.read_text(encoding="utf-8")

    records_dir = tmp_foundry.root / "rights_records"
    records_dir.mkdir(parents=True, exist_ok=True)
    record_path = records_dir / "rr_p5_2_cli_crafted.yaml"
    dump_yaml(
        {
            "schema_version": "1.0",
            "rights_record_id": "rr_p5_2_cli_crafted",
            "source_id": "src_demo",
            "record_scope": "source",
            "jurisdictions": ["US"],
            "access": {"basis": "public_web"},
            "copyright": {"status": "copyrighted"},
            "component_decisions": [],
            "overall_status": _CLEARED_VALUE,
            "review": {"reviewed_at": "2026-07-21T12:00:00Z", "review_status": "agent_triage_only"},
        },
        record_path,
    )
    before_record = record_path.read_text(encoding="utf-8")

    result = _invoke_cli(["rights", "inspect", "src_p5_2_cli"], tmp_foundry.root)

    assert result.exit_code == 0, result.output
    # The CLI is free to DISPLAY the crafted record's overall_status (it's
    # read-only rights-posture output) -- what it must never do is write it
    # anywhere. Both on-disk files are untouched.
    assert card_path.read_text(encoding="utf-8") == before_card
    assert record_path.read_text(encoding="utf-8") == before_record
    metadata, _body = load_md(card_path)
    assert metadata["rights_summary"]["clearance_status"] == "UNKNOWN"
    assert not _recursive_keys(metadata) & set(_GOVERNED_OBJECT_NAMES)


def test_cli_rights_backfill_writes_only_unknown_clearance_status(tmp_foundry: FoundryPaths) -> None:
    run_id = "run_p5_2_cli_backfill"
    card_path = tmp_foundry.runs / run_id / "source_cards" / "src_p5_2_backfill.md"
    dump_md({"source_card_id": "src_p5_2_backfill", "type": "source_card"}, "# X\n", card_path)

    result = _invoke_cli(["rights", "backfill", str(card_path)], tmp_foundry.root)

    assert result.exit_code == 0, result.output
    metadata, _body = load_md(card_path)
    assert metadata["rights_summary"]["clearance_status"] == "UNKNOWN"
    assert not _recursive_keys(metadata) & set(_GOVERNED_OBJECT_NAMES)


# ---------------------------------------------------------------------------
# Layered defense: the governance guard (P5-1) as ONE enforcement layer
# alongside (not instead of) the service-layer proofs above.
# ---------------------------------------------------------------------------


def test_governance_guard_blocks_disallowed_values_on_the_3_covered_fields() -> None:
    for field_name in (
        "rights_record.overall_status",
        "content_reuse_assessment.decision.status",
        "rights_extension.clearance_status",
    ):
        for bad_value in (_CLEARED_VALUE, *_DISALLOWED_EXACT_VALUES):
            result = guard_check(GuardContext(proposed_field_writes=((field_name, bad_value),)))
            assert result.exit_code == 3, (field_name, bad_value)
            assert "no_agent_cleared_rights_value" in {v.rule_id for v in result.violations}


def test_release_gate_is_safe_despite_governance_non_coverage() -> None:
    """``content_reuse_assessment.decision.release_gate`` is NOT one of rule
    7's named fields (documented in this module's docstring and in the
    implementation plan: P5-1 deliberately scoped to the 4 fields excluding
    this one; a different release-gate predicate is P5-3's separate concern).
    This test proves that non-coverage is currently safe for two independent
    reasons, so it is not the reachable gap this task's Mode C instructions
    would require escalating:

    1. The governance guard indeed does not block it by name (documented,
       not a false claim).
    2. No code path anywhere constructs the containing
       ``content_reuse_assessment`` object at all (re-asserted here for
       proximity to the governance-non-coverage fact above), and the field's
       own schema enum (PASS/PASS_WITH_CONDITIONS/BLOCK) cannot represent a
       ``CLEARED_*``/``counsel_approved`` value even if a writer existed.
    """

    result = guard_check(
        GuardContext(proposed_field_writes=(("content_reuse_assessment.decision.release_gate", _CLEARED_VALUE),))
    )
    assert result.exit_code == 0
    assert "no_agent_cleared_rights_value" not in {v.rule_id for v in result.violations}

    for m in _ENUMERATED_MODULES:
        assert "content_reuse_assessment" not in _source_text(m), m.__name__


def test_owned_without_first_party_basis_has_zero_construction_paths() -> None:
    """The 3rd disallowed shape this task names -- ``OWNED`` set on a record
    that lacks a first-party basis (schema §9.5: ``overall_status: OWNED``
    is only valid when ``record_scope: first_party``) -- requires a writer
    that can set ``overall_status``/``decision.status`` at all. Since
    ``test_overall_status_key_write_site_is_exactly_the_unrelated_writeback_receipt``
    and ``test_content_reuse_assessment_object_never_constructed_in_any_enumerated_module``
    together prove zero such writers exist across every module named in this
    task, the combination is unreachable a fortiori -- there is no
    ``record_scope``-blind writer to interrogate for a missing basis check
    in the first place. This test re-asserts the "OWNED" string itself is
    never assigned to ``overall_status``/``clearance_status`` anywhere, as a
    direct, literal check.
    """

    pattern = re.compile(r'"(overall_status|clearance_status|status)"\s*:\s*"OWNED"')
    offenders = [m.__name__ for m in _ENUMERATED_MODULES if pattern.search(_source_text(m))]
    assert offenders == [], f'"OWNED" assigned to a governed field in: {offenders}'
