"""Capture-time ``rights_summary`` computation (rights-entity-model-v1, P4-1).

``compute_capture_rights_summary`` is the single site both ``ingest_source``
(``services/source_cards.py``) and the source_assertion materializer
(``services/assertion_materialization.py``'s ``_prepare_one``) call to
populate the fail-closed ``rights_summary`` mirror in the SAME call that
creates the entity -- no separate backfill sweep is needed for newly-ingested
instances (AC P4-A).

Deviation from the plan's literal AC text (documented; report to phase owner)
-------------------------------------------------------------------------------
The PRD/implementation-plan AC text for P4-1 asks for
``review_status: "agent_triage_only"`` directly on capture. That is
unimplementable as written: ``rights_summary``'s own link-before-assert
``allOf``/``if``/``then`` (``schemas/source_card.schema.yaml``,
``schemas/source_assertion.schema.yaml`` -- P2-1/P2-2) requires
``rights_record_ids`` to be non-empty whenever ``review_status`` is anything
other than its ``"unknown"`` sentinel -- verified empirically against
``SchemaRegistry.validate()`` -- and there is no ``rights_record`` creation
path anywhere in this codebase for a bare capture to link to. Minting a
``rights_record_id`` that resolves to nothing would be exactly the
"fail-open bug" that invariant's own schema comment warns against, and
setting ``review_status: "agent_triage_only"`` with an empty
``rights_record_ids`` fails schema validation outright, which would abort
every capture -- violating this same task's hard requirement that capture
must always complete. The safe, schema-valid resolution used here is the
all-``"unknown"`` block (``rights_backfill.all_unknown_rights_summary``),
which still satisfies the AC's *operative* requirement (a non-null,
schema-valid ``rights_summary`` present on every new capture, no backfill
sweep needed) without violating the P2-established governance invariant.

Fail-closed by construction
----------------------------
``_classify_capture_rights`` is the seam a future capture-time classifier
(e.g. locator-pattern-based reasoning, once a rights_record link becomes
available) would extend. No such signal exists yet -- a bare locator alone
carries no rights determination -- so it always returns the all-"unknown"
block today. It is kept as its own function, and wrapped by
``compute_capture_rights_summary``, so that (a) a future classifier and
(b) the structural-failure-record wiring below both have a single call site
to extend without touching either capture call site. If the classifier
raises for any reason, ``compute_capture_rights_summary`` catches it and
degrades to a fresh all-"unknown" block rather than ever propagating -- a
triage failure must never abort or silently skip populating an entity's
``rights_summary``.

Structural failure record (P4 fix-cycle 1, karen review)
-----------------------------------------------------------
A classification failure is never a *silent* degrade: the caught exception
is also recorded as a ``rights_summary.rights_triage_failure`` block
(``reason``/``detail``/``attempted_at`` -- see
``schemas/source_card.schema.yaml`` / ``schemas/source_assertion.schema.yaml``),
mirroring ``services/terms_snapshot.py``'s ``TermsSnapshotFailure`` /
``rights_record.access.terms_snapshot_failure`` convention (P4-3). A
successful classification (today, always the all-"unknown" default) leaves
``rights_triage_failure`` ``None`` -- the field disambiguates "classification
ran and produced all-unknown" from "classification itself blew up," the same
way ``access_terms_snapshot_status`` disambiguates a null
``terms_snapshot_uri``.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from pathlib import Path

from ..ids import now_iso
from .rights_backfill import all_unknown_rights_summary
from .rights_substitutability import assess_substitutability

__all__ = ["compute_capture_rights_summary", "maybe_assess_substitutability"]


def _classify_capture_rights() -> dict[str, Any]:
    """Attempt a capture-time rights classification.

    No real classification signal exists at bare ingest time -- a locator or
    passage alone carries no rights determination, and there is no
    rights_record for the mirror to link to yet -- so this always returns a
    fresh all-"unknown" block today. Kept separate from
    :func:`compute_capture_rights_summary` (rather than inlined) so a future
    signal-bearing classifier, and P4-3's failure-record wiring, have exactly
    one call site to extend.
    """

    return all_unknown_rights_summary()


def compute_capture_rights_summary() -> dict[str, Any]:
    """A well-formed ``rights_summary`` for a newly-captured entity.

    Never raises. Any exception from the classification step degrades to a
    fresh all-"unknown" block -- capture always completes with a non-null,
    schema-valid ``rights_summary`` -- but the degrade is never silent: the
    caught exception is recorded on the returned block's
    ``rights_triage_failure`` field (``reason``/``detail``/``attempted_at``),
    mirroring ``terms_snapshot.py``'s ``TermsSnapshotFailure`` pattern. A
    successful classification returns :func:`all_unknown_rights_summary`
    unmodified -- ``rights_triage_failure`` is absent (schema-equivalent to
    ``None``), not explicitly nulled, so the success path stays
    byte-identical to every pre-existing all-"unknown" fixture/test.
    """

    try:
        return _classify_capture_rights()
    except Exception as exc:  # noqa: BLE001 -- a triage failure must never abort capture
        summary = all_unknown_rights_summary()
        summary["rights_triage_failure"] = {
            "reason": "classification_error",
            "detail": f"{type(exc).__name__}: {exc}",
            "attempted_at": now_iso(),
        }
        return summary


def maybe_assess_substitutability(
    rights_summary: dict[str, Any],
    *,
    query_terms: Sequence[str] | None = None,
    corpus_paths: Iterable[Path | str] | None = None,
    exclude_source_id: str | None = None,
) -> dict[str, Any]:
    """P4-4 integration seam: run a substitutability search iff ``rights_summary``
    carries a use-blocking ``clearance_status``.

    Additive to this module -- does not alter ``compute_capture_rights_summary``
    or ``_classify_capture_rights`` (P4-1). Wired into the real capture path
    as of the P4 fix-cycle 1 review: both ``services/source_cards.py``'s
    ``ingest_source`` and ``services/assertion_materialization.py``'s
    ``_prepare_one`` call this immediately after
    ``compute_capture_rights_summary`` and persist the result on the
    entity's top-level ``substitutability`` field. Since ``rights_summary``
    always emits ``clearance_status: "UNKNOWN"`` at capture time today (no
    real classifier exists yet -- see the module docstring), every fresh
    capture is currently blocking and this now runs on every real capture;
    once a real capture-time classifier lands, only its blocking outcomes
    will trigger a search. Never raises -- delegates entirely to
    :func:`rights_substitutability.assess_substitutability`, which is
    itself exception-safe.

    Deterministic clock (bug fix, karen end-of-feature review)
    -------------------------------------------------------------
    Always passes ``now=now_iso()`` (the same injectable, suite-pinned clock
    ``compute_capture_rights_summary``/``source_cards.py``/
    ``assertion_materialization.py`` already use) rather than leaving
    ``assess_substitutability``'s ``now`` at its default. Its default
    (``rights_substitutability._resolve_now``) falls back to a real
    ``datetime.now(timezone.utc)`` wall-clock read when ``now`` is omitted --
    correct for a standalone caller, but this is the ONLY caller reachable
    from every real capture, so omitting ``now`` here made every capture's
    ``substitutability.searched_at`` a real timestamp, breaking capture-time
    reproducibility (byte-identical output for byte-identical input).

    Self-file corpus exclusion (bug fix, same review)
    -----------------------------------------------------
    Also filters ``corpus_paths`` to drop any path whose stem equals
    ``exclude_source_id`` before delegating. ``source_card_id`` is
    content-derived (title + locator + capture day, not wall-clock-precise),
    and both call sites write the entity's own file as ``{source_card_id}.md``
    in the exact same directory the corpus glob (``sources.glob("*.md")``)
    reads. A byte-identical re-ingest of the same locator/title on the same
    day therefore finds its *own* prior-write file already sitting in the
    corpus at glob time -- inflating ``coverage_notes``'s reported corpus
    size (e.g. "searched 1 corpus source(s)" instead of "searched 0") even
    though ``exclude_source_id`` already (and still) keeps that file out of
    ``candidate_source_ids``. ``exclude_source_id`` is designed expressly to
    guard against "a re-ingest of the same locator matching itself once its
    own file exists in the corpus glob" (see ``source_cards.py``'s comment at
    its call site) -- filtering it out of the corpus *before* it is counted,
    not just before it is ranked, is required for that guard to make capture
    fully reproducible rather than only candidate-safe.
    """

    clearance_status = rights_summary.get("clearance_status")
    filtered_corpus_paths = corpus_paths
    if corpus_paths is not None and exclude_source_id:
        filtered_corpus_paths = [p for p in corpus_paths if Path(p).stem != exclude_source_id]
    return assess_substitutability(
        clearance_status,
        query_terms=query_terms,
        corpus_paths=filtered_corpus_paths,
        exclude_source_id=exclude_source_id,
        now=now_iso(),
    )
