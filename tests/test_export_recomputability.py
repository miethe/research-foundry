"""Export recomputability (source-metadata-propagation-v1, SMP-1.5, AC-M1-3).

The read path stays dumb: every derived value must be reconstructible by
re-running :func:`export_service.export_run` over unchanged files -- no
persisted derived state, no cached judgment, no wall-clock read.

Proves this by calling ``export_run()`` **twice, in-process**, over an
unchanged run and asserting the two outputs are equal once the telemetry
``timeline`` is ``del``'d from both and both dicts are canonical-sorted.

Two named-risk traps this test must not fall into (plan "Named risks"):

* ``rf verify`` must NOT be used to "prove" hydration -- ``verification.py``
  only imports helpers from ``export_service`` and never calls
  ``export_run()``, so any AC exercised through ``rf verify`` is vacuous.
  This test calls ``svc.export_run()`` directly.
* Each ``rf verify`` invocation appends a timestamped event to
  ``telemetry/run_trace.jsonl``, which ``_timeline()`` folds into the
  export -- so a naive byte-for-byte comparison of two exports could never
  pass if anything had appended to the trace between calls. The
  ``timeline`` key is explicitly ``del``'d from both outputs before
  comparison, regardless of whether this particular test happens to
  trigger that growth, so the test stays correct if a future change adds
  an intermediate trace-appending call between the two ``export_run()``
  calls.

The test is anchored on SMP-1.2/SMP-1.3/SMP-1.4's hydrated fields
(``authors``/``doi``/``publisher``/``version``/``trust.source_rank``) so it
FAILS on the pre-M1 shape where those fields were hardcoded empty/unknown at
the ingest boundary and dropped (never hydrated) at export time -- a test
that would pass against an unimplemented feature is itself a defect
(plan's "AC -> command -> evidence" preamble).
"""

from __future__ import annotations

from typing import Any

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import export_service as svc
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml

RUN_ID = "rf_run_export_recomputability"


def _canonical_sort(value: Any) -> Any:
    """Recursively canonicalize ``value`` for order-insensitive comparison.

    Dict keys are sorted by construction when compared via ``==`` in Python
    (dict equality is order-insensitive already), but *list* order is not --
    and the plan's monotone-rollup decision requires set-union values to be
    canonically sorted before serialization. Sort every list of orderable
    (str/number) leaves so accidental non-determinism in list order (e.g. a
    filesystem glob) cannot produce a false failure OR mask a false pass.
    Lists of dicts (e.g. ``claims``) are left in place -- their internal
    order is claim-ledger order, which is itself file-derived and stable
    across two reads of the same unchanged file.
    """

    if isinstance(value, dict):
        return {k: _canonical_sort(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        if all(isinstance(item, (str, int, float)) for item in value):
            return sorted(value)
        return [_canonical_sort(item) for item in value]
    return value


def _build_run(
    paths: FoundryPaths, *, run_id: str = RUN_ID, sensitivity: str = "personal"
) -> None:
    """Self-built fixture run (no dependency on committed ``runs/`` data).

    Uses the real ``ingest_source()`` write path (not a hand-rolled card
    dict) so the source card carries SMP-1.2/SMP-1.3's actually-validated
    ``authors``/``doi``/``publisher``/``version``/``trust.source_rank`` --
    the exact fields this test needs the export to hydrate.

    ``run_id``/``sensitivity`` are parametrized (defaulting to the original
    ``RUN_ID``/``"personal"``, so every pre-existing call site is
    byte-identical) so the post-M1-security-gate redaction test below can
    build a second, distinctly-sensitive fixture without duplicating this
    whole builder.
    """

    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": "intent_export_recomputability",
            "status": "planned",
            "sensitivity": sensitivity,
            "created_at": "2026-06-13T22:46:23-04:00",
        },
        rp.run_yaml,
    )

    ingest_source(
        "https://example.com/recomputability-paper",
        run_id=run_id,
        source_type="paper",
        sensitivity=sensitivity,
        content="A study of recomputable exports.",
        authors=["Ada Lovelace", "Alan Turing"],
        doi="10.1000/recompute-001",
        publisher="Recomputability Press",
        version="v3",
        paths=paths,
    )
    # ingest_source derives the card's stem from the locator, not a fixed
    # id -- read back the actually-written card to learn its real
    # source_card_id instead of guessing one, so the claim ledger below
    # references the file that really exists on disk.
    card_paths = sorted(rp.sources.glob("*.md"))
    assert len(card_paths) == 1, "expected exactly one ingested source card"
    card_meta, _ = load_md(card_paths[0])
    source_card_id = card_meta["source_card_id"]
    evidence_id = card_meta["extracted_points"][0]["evidence_id"]

    dump_yaml(
        {
            "schema_version": "0.1",
            "report_ref": "reports/report_draft.md",
            "claims": [
                {
                    "claim_id": "clm_001",
                    "text": "recomputable export fact",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": source_card_id,
                            "evidence_id": evidence_id,
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                },
            ],
        },
        rp.claim_ledger,
    )

    rp.report_draft.write_text(
        "# Report\n\nA recomputable fact. [claim:clm_001]\n", encoding="utf-8"
    )

    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "status": "verified",
            "counts": {"claims_total": 1, "claims_supported": 1},
            "governance": {"sensitivity": sensitivity},
        },
        rp.evidence_bundle,
    )


def _export_twice(paths: FoundryPaths) -> tuple[dict[str, Any], dict[str, Any]]:
    first = svc.export_run(paths, RUN_ID)
    second = svc.export_run(paths, RUN_ID)
    assert first is not None and second is not None
    return first, second


def test_export_run_is_recomputable_over_unchanged_files(
    tmp_foundry: FoundryPaths,
) -> None:
    """Two in-process export_run() calls over unchanged files produce equal
    output once the telemetry timeline is del'd and both are canonically
    sorted (AC-M1-3). Does NOT use `rf verify` -- verification.py never
    calls export_run()."""

    _build_run(tmp_foundry)

    first, second = _export_twice(tmp_foundry)

    # Both exports must carry a timeline key to del -- otherwise the del
    # below would silently no-op and this test would prove nothing about
    # the named risk it exists to guard against.
    assert "timeline" in first and "timeline" in second
    del first["timeline"]
    del second["timeline"]

    assert _canonical_sort(first) == _canonical_sort(second)


def test_export_run_hydrates_source_metadata_at_claim_level(
    tmp_foundry: FoundryPaths,
) -> None:
    """Non-vacuity anchor: the recomputed export actually carries SMP-1.2's
    real authors/DOI/publisher/version and SMP-1.3's derived source_rank at
    claim level -- not the pre-change hardcoded-empty/unknown shape. A test
    that only checked equality above could pass even if _resolve_source()
    hydration were reverted to the pre-M1 all-null shape (two exports of an
    all-null shape are trivially equal to each other); this test fails in
    that scenario because it asserts the actual hydrated values."""

    _build_run(tmp_foundry)
    # Explicit `sensitivity_threshold="personal"` matches this fixture's card
    # sensitivity (the `_build_run` default) so the SMP-1.4 security-gate fix
    # below -- which now correctly redacts these same four fields above the
    # viewer threshold -- doesn't collide with this test's actual purpose
    # (proving hydration happens at all). Redaction of these fields is
    # covered on its own terms by
    # `test_export_run_redacts_source_metadata_above_threshold` below.
    data = svc.export_run(tmp_foundry, RUN_ID, sensitivity_threshold="personal")
    assert data is not None

    claim = next(c for c in data["claims"] if c["claim_id"] == "clm_001")
    src = claim["sources"][0]
    assert src["resolved"] is True
    assert src["authors"] == ["Ada Lovelace", "Alan Turing"]
    assert src["doi"] == "10.1000/recompute-001"
    assert src["publisher"] == "Recomputability Press"
    assert src["version"] == "v3"
    assert src["trust"]["source_rank"] == "primary"  # derive_source_rank("paper")


def test_export_run_redacts_source_metadata_above_threshold(
    tmp_foundry: FoundryPaths,
) -> None:
    """Security-gate fix (M1 gate finding, post-SMP-1.4 review): `authors`/
    `doi`/`publisher`/`version` must be gated by the same
    `effective_rank > threshold_rank` check `summary`/`quote` already use --
    NOT hydrated unconditionally. Concrete exploit the gate named: a
    `client_sensitive` card's `publisher` (etc.) is externally-controlled
    text (reachable via `create_source_card(**merged)` from arbitrary MCP
    `tool_input`, per `agent_job_service.py:688`) that would otherwise ship
    verbatim at a lower viewer threshold while `summary`/`quote` were
    correctly redacted -- a content-leak channel bypassing the exact
    untrusted-input control this milestone's `gate_lens_reason` exists for.

    Non-vacuity: asserts exact equality to `REDACTION_MARKER` (or, for the
    array-typed `authors`, `[REDACTION_MARKER]`) -- not merely
    `!= <original value>` -- so a regression that redacts to `None`, an
    empty value, or omits the key entirely still fails this test. If
    SMP-1.4's redaction gate were reverted to unconditional hydration,
    `authors` would be the real list (`!= [REDACTION_MARKER]`) and this test
    goes RED. `authors` redacts to a single-element LIST, not the bare
    marker string -- a second gate finding caught that a bare-string marker
    would violate `rf-run-export-schema.json`'s `RFResolvedSource.authors`
    (`type: ["array","null"]`); it also must not become `None`, since `null`
    already means absent/dangling/pre-migration and collapsing "withheld"
    into that value would defeat the tri-state absent/withheld/not-yet-
    assessed distinction this plan exists to preserve.
    """

    redacted_run_id = f"{RUN_ID}_client_sensitive"
    _build_run(tmp_foundry, run_id=redacted_run_id, sensitivity="client_sensitive")

    # work_sensitive (rank 2) < client_sensitive (rank 3): the exact
    # "exports at a work_sensitive threshold" scenario the gate finding used.
    data = svc.export_run(
        tmp_foundry, redacted_run_id, sensitivity_threshold="work_sensitive"
    )
    assert data is not None

    claim = next(c for c in data["claims"] if c["claim_id"] == "clm_001")
    src = claim["sources"][0]
    assert src["resolved"] is True
    assert src["redacted"] is True

    assert src["authors"] == [svc.REDACTION_MARKER]
    assert isinstance(src["authors"], list), (
        "authors must stay array-typed when redacted -- a bare marker string "
        "violates RFResolvedSource.authors's declared ['array','null'] type"
    )
    assert src["authors"] is not None, (
        "redacted authors must not collapse to null -- null already means "
        "absent/dangling/pre-migration; withheld must stay distinguishable"
    )
    assert src["doi"] == svc.REDACTION_MARKER
    assert src["publisher"] == svc.REDACTION_MARKER
    assert src["version"] == svc.REDACTION_MARKER
    # summary/quote were already gated pre-fix -- assert them too so this
    # test also proves the four new fields share the SAME gate/marker as the
    # pre-existing ones, not a second, divergent redaction path.
    assert src["summary"] == svc.REDACTION_MARKER
    assert src["quote"] == svc.REDACTION_MARKER

    # Recomputability must survive the gate: the redaction decision is a pure
    # function of card sensitivity + the passed threshold (no wall-clock
    # read, no network call, no persisted state), so calling export_run()
    # again over the same unchanged files must reproduce the same redacted
    # shape byte-for-byte.
    second = svc.export_run(
        tmp_foundry, redacted_run_id, sensitivity_threshold="work_sensitive"
    )
    assert second is not None
    del data["timeline"]
    del second["timeline"]
    assert _canonical_sort(data) == _canonical_sort(second)


def _inject_attribution_summary(rp: Any, mirror: dict[str, Any]) -> None:
    """Rewrite the single ingested source card's frontmatter to add an
    ``attribution_summary`` mirror.

    ``ingest_source()`` has no kwarg for this -- no M2 writer exists yet
    (only the schema, the pure ``attribution_triage``/``attribution_
    validation`` computation library, and now this milestone's read-side
    wiring). This test builds the fixture directly, the same way
    ``tests/test_schema_validation.py`` hand-builds fixture cards carrying
    the mirror.
    """

    from research_foundry.frontmatter import dump_md, load_md

    card_paths = sorted(rp.sources.glob("*.md"))
    assert len(card_paths) == 1, "expected exactly one ingested source card"
    meta, body = load_md(card_paths[0])
    meta["attribution_summary"] = mirror
    dump_md(meta, body, card_paths[0])


def test_export_run_hydrates_attribution_summary_at_claim_level(
    tmp_foundry: FoundryPaths,
) -> None:
    """SMP-4.4 Part 1: closes the wiring gap the SMP-4.2/4.3 ledger entry
    flagged -- ``catalog_service.py`` has read ``src.get("attribution_
    summary")`` since M4's row builders landed, but nothing ever put that
    key on the resolved-source dict, so ``attribution_count`` was NULL for
    every source end-to-end.

    Non-vacuity anchor mirroring ``test_export_run_hydrates_source_
    metadata_at_claim_level`` above: FAILS on the pre-SMP-4.4 shape where
    ``attribution_summary`` was silently dropped (never copied) at export
    time.
    """

    run_id = f"{RUN_ID}_attribution"
    _build_run(tmp_foundry, run_id=run_id, sensitivity="personal")
    rp = tmp_foundry.run_paths(run_id)
    mirror = {
        "attribution_ids": ["attrib_b", "attrib_a"],
        "count": 2,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["attrib_b", "attrib_a"],
                "count": 2,
                "best_attribution_id": "attrib_b",
                "weakest_attribution_id": "attrib_a",
                "comparable": True,
            }
        ],
    }
    _inject_attribution_summary(rp, mirror)

    data = svc.export_run(tmp_foundry, run_id, sensitivity_threshold="personal")
    assert data is not None
    claim = next(c for c in data["claims"] if c["claim_id"] == "clm_001")
    src = claim["sources"][0]
    assert src["attribution_summary"] == mirror

    # Recomputability: a second in-process export_run() call over the same
    # unchanged card must reproduce the identical mirror -- no persisted
    # derived state, no recompute-time drift.
    second = svc.export_run(tmp_foundry, run_id, sensitivity_threshold="personal")
    assert second is not None
    src2 = next(c for c in second["claims"] if c["claim_id"] == "clm_001")["sources"][0]
    assert src2["attribution_summary"] == mirror


def test_export_run_does_not_redact_attribution_summary_above_threshold(
    tmp_foundry: FoundryPaths,
) -> None:
    """``attribution_summary`` is deliberately NOT gated by the
    ``effective_rank > threshold_rank`` redaction check ``authors``/``doi``/
    ``publisher``/``version``/``summary``/``quote`` all go through above.

    Reasoning (recorded here, not just in the schema doc): every property
    this object can ever carry is an id, a count, or a monotone-rollup
    POINTER -- there is no property capable of carrying a raw third-party
    value or free text for a redaction gate to protect. Redacting it would
    also actively corrupt ``catalog_service.py``'s tri-state coverage
    semantics: ``_attribution_count_of()`` treats a ``None`` mirror as "not
    yet assessed", so swapping an assessed card's real (already value-free)
    mirror for ``None`` above threshold would make an ASSESSED card read as
    NOT-YET-ASSESSED for a lower-privilege viewer -- the exact absent/
    withheld conflation the plan's no-backfill decision forbids.

    Non-vacuity: this fixture's card IS redacted for ``authors`` (asserted
    below too), proving the gate genuinely fired for this citation -- so
    ``attribution_summary`` surviving unredacted is a deliberate carve-out,
    not an artifact of the gate never firing.
    """

    redacted_run_id = f"{RUN_ID}_attribution_redaction_guard"
    _build_run(tmp_foundry, run_id=redacted_run_id, sensitivity="client_sensitive")
    rp = tmp_foundry.run_paths(redacted_run_id)
    mirror = {
        "attribution_ids": ["attrib_guard_1"],
        "count": 1,
        "rollups": [],
    }
    _inject_attribution_summary(rp, mirror)

    data = svc.export_run(
        tmp_foundry, redacted_run_id, sensitivity_threshold="work_sensitive"
    )
    assert data is not None
    claim = next(c for c in data["claims"] if c["claim_id"] == "clm_001")
    src = claim["sources"][0]
    assert src["redacted"] is True
    assert src["authors"] == [svc.REDACTION_MARKER]  # sanity: the gate did fire
    assert src["attribution_summary"] == mirror  # unredacted, exact equality

    second = svc.export_run(
        tmp_foundry, redacted_run_id, sensitivity_threshold="work_sensitive"
    )
    assert second is not None
    del data["timeline"]
    del second["timeline"]
    assert _canonical_sort(data) == _canonical_sort(second)


def test_export_run_never_reads_the_wall_clock_between_calls(
    tmp_foundry: FoundryPaths,
) -> None:
    """No wall-clock read on this path: the repo idiom is `now_iso()`
    (services/ids.py:41), not a bare `datetime.now()` call, so a monkeypatch
    that breaks any real-time read would make export_run() raise rather than
    silently drift between the two calls."""

    import research_foundry.ids as ids_module

    _build_run(tmp_foundry)

    def _boom():  # pragma: no cover - only invoked if something reads real time
        raise AssertionError("export_run() must not read the wall clock")

    original_now = ids_module._clock  # noqa: SLF001 - test-only introspection
    ids_module.set_clock(_boom)
    try:
        first, second = _export_twice(tmp_foundry)
    finally:
        ids_module.set_clock(original_now)

    del first["timeline"]
    del second["timeline"]
    assert _canonical_sort(first) == _canonical_sort(second)
