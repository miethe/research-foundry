"""Governed catalog adapter for Catalog-Assisted Research Planning (CARP-2).

This module is the *only* path CARP uses to reach assertion data. It never
reads ``assertion_ledger/`` paths directly -- every read goes through
:class:`~research_foundry.services.assertion_catalog.AssertionCatalog`'s
public surface (``search()``, ``packet()``, ``rebuild()``,
``projection_path()``). See ``docs/dev/architecture/carp-contract-freeze.md``
for the frozen policy this adapter implements against.

Identity precedes retrieval: every function here takes an
:class:`~research_foundry.api.auth.provider.AuthIdentity` and denies before
any catalog call when it is absent or workspace-less. Every denial reuses
:meth:`AssertionCatalog.denied_payload`'s reason-code vocabulary and exposes
zero candidate-derived fields.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..api.auth.provider import AuthIdentity
from .assertion_catalog import AssertionCatalog, AssertionCatalogDenied
from .assertion_reuse import ReuseDecision, evaluate_reuse
from .sensitivity import SENSITIVITY_RANK

#: Frozen ceilings (carp-contract-freeze.md §3.3). Enforced defensively here
#: in addition to the schema layer -- a caller-supplied limit is clamped to
#: the ceiling, never trusted verbatim.
MAX_CANDIDATES_PER_QUESTION = 50
MAX_PAGES_PER_QUESTION = 5
MAX_PAGE_SIZE = 100
_DEFAULT_PAGE_SIZE = 25

#: evaluate_reuse() reason codes that mean "the immediate-before-selection
#: lifecycle re-read disagrees with any earlier projection" -- mapped to the
#: frozen residual reason `lifecycle_ineligible` (carp-contract-freeze.md §CARP-2.2 table).
_LIFECYCLE_DENY_REASONS = frozenset({"lifecycle_blocked", "lifecycle_unknown"})

#: source_assertion.schema.yaml's own lifecycle vocabulary (eligible, stale,
#: invalidated, tombstoned) differs from assertion_reuse.evaluate_reuse()'s
#: vocabulary (eligible, stale, blocked, invalid, retracted, deleted,
#: superseded). Only these two states represent "not invalidated" in the
#: ledger's own terms; every other value (including "invalidated"/
#: "tombstoned") is deliberately left unmapped so evaluate_reuse denies with
#: `lifecycle_unknown` rather than this adapter guessing an equivalence.
_NOT_INVALIDATED_LIFECYCLE_STATES = frozenset({"eligible", "stale"})


@dataclass(frozen=True)
class RetrievalQuestion:
    """A stable CARP question: identity + the lexical/coverage constraints P3 will judge.

    ``required_source_types``/``required_qualifiers`` are accepted and
    threaded through unchanged for a future evidence-plan builder (CARP-3.1
    owns mapping them to `source_type_mismatch`/`qualifier_missing` --
    condition 4 of the six covered conditions is explicitly out of this
    adapter's scope). This adapter only acts on ``required_terms``
    (condition 1, Seam 2) and the reuse/version constraints below.
    """

    question_id: str
    required_terms: tuple[str, ...] = ()
    required_source_types: tuple[str, ...] = ()
    required_qualifiers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalConstraints:
    """Exact reuse-reachability constraints for one evaluation pass.

    ``sensitivity_threshold`` is the caller's (never-defaulted) ceiling for
    ``source_edition.access_scope`` -- see :func:`_project_reuse_input`. When
    ``None`` (the dataclass default), :func:`_project_reuse_input` omits
    ``sensitivity_allowed`` entirely rather than defaulting a threshold, and
    :func:`~research_foundry.services.assertion_reuse.evaluate_reuse` denies
    with ``sensitivity_denied`` -- fail-closed, never fail-open.

    ``automated_reuse_allowed`` is the caller's (never-defaulted) capability
    signal -- the same
    :class:`~research_foundry.config.AssertionLedgerCapabilities.automated_reuse_allowed`
    the pre-existing :func:`~research_foundry.services.run_launch.retrieve_first_reuse_decision`
    seam already gates on (``run_launch.py`` ~L106-107). Absence semantics
    mirror ``sensitivity_threshold``: ``None`` (the dataclass default) is a
    caller who never supplied a capability, and :func:`retrieve` maps every
    otherwise-``allow`` candidate to the SAME
    ``deny``/``automated_reuse_disabled`` decision (frozen residual reason
    ``reuse_denied``) rather than defaulting the capability to allowed.
    Fail-closed, never fail-open -- the CARP catalog-retrieval path must
    honor the same capability gate as the ledger.
    """

    required_edition_id: str | None = None
    required_extraction_contract: str | None = None
    sensitivity_threshold: str | None = None
    automated_reuse_allowed: bool | None = None


@dataclass(frozen=True)
class RetrievalLimits:
    """Caller-requested limits, clamped to the frozen ceilings before use."""

    max_candidates_per_question: int = MAX_CANDIDATES_PER_QUESTION
    max_pages_per_question: int = MAX_PAGES_PER_QUESTION
    page_size: int = _DEFAULT_PAGE_SIZE

    def clamped(self) -> RetrievalLimits:
        return RetrievalLimits(
            max_candidates_per_question=max(1, min(self.max_candidates_per_question, MAX_CANDIDATES_PER_QUESTION)),
            max_pages_per_question=max(1, min(self.max_pages_per_question, MAX_PAGES_PER_QUESTION)),
            # page_size is intentionally NOT clamped here: AssertionCatalog.search()
            # already fail-closes on an out-of-range page_size via `denied_payload("invalid_page_size")`
            # (assertion_catalog.py:134) -- clamping it here would silently mask that
            # denial instead of reusing the catalog's own typed response, which
            # CARP-1.2 requires ("never invent a new [denial] shape").
            page_size=self.page_size,
        )


@dataclass(frozen=True)
class CatalogReceipt:
    """Plan-level proof of the catalog generation a retrieval was evaluated against.

    Mirrors ``research_evidence_plan.schema.yaml``'s ``catalog_receipt``:
    ``record_count`` is forced to ``0`` and ``catalog_generation_id`` to
    ``None`` whenever ``denial_reason`` is set (CARP-1.2 zero-candidate-derived-fields rule).
    """

    record_count: int
    catalog_generation_id: str | None
    denial_reason: str | None


@dataclass(frozen=True)
class RetrievalReceipt:
    """Persistable per-candidate retrieval receipt (safe by construction of ReuseDecision)."""

    action: str
    reason_code: str
    assertion_id: str
    assertion_version: int
    source: str = "catalog"
    catalog_generation_id: str | None = None


@dataclass(frozen=True)
class EvaluatedCandidate:
    """One bounded, immediately-re-read candidate evaluated for exact reuse/version eligibility.

    ``lifecycle_state`` and ``assertion_version`` are read fresh from
    :meth:`AssertionCatalog.packet` immediately before this evaluation runs
    (CARP-2.2's "not from a cached projection snapshot" rule) -- never
    copied from the search-phase summary.
    """

    assertion_id: str
    assertion_version: int
    lifecycle_state: str
    lexical_match: bool
    matched_terms: tuple[str, ...]
    qualifiers: Mapping[str, Any]
    reuse_decision: ReuseDecision
    residual_reason: str | None
    retrieval_receipt: RetrievalReceipt


@dataclass(frozen=True)
class RetrievalResult:
    """Bounded result of one question's search+evaluate pass.

    ``denial_reason`` set means the whole result is a fail-closed denial:
    ``candidates`` is empty and no candidate-derived signal was computed.
    """

    question_id: str
    denial_reason: str | None
    catalog_generation_id: str | None
    candidates: tuple[EvaluatedCandidate, ...]
    pagination_limit_reached: bool
    candidate_limit_reached: bool


def peek_catalog_generation_id(catalog: AssertionCatalog, workspace_id: str) -> str | None:
    """Read the persisted ``catalog_generation_id`` *without* forcing a rebuild.

    Reads the catalog's own on-disk projection cache
    (``.rf_cache/assertion_catalog/*.json`` via
    :meth:`AssertionCatalog.projection_path`, a public method) -- this is the
    catalog's non-authoritative derived cache, not an ``assertion_ledger/``
    path, so reading it directly does not violate the "never read ledger
    paths" constraint. Returns ``None`` when no projection has been built yet
    (treat as "no baseline established", not as a generation mismatch) or
    when the persisted file fails a basic integrity check. Callers use this
    for the CARP contract-freeze §3.4 mid-plan drift check: capture a
    generation id once via :func:`catalog_receipt`, then re-check it here
    (never via another ``rebuild()``) before resolving each remaining
    question in the same plan.
    """

    path = catalog.projection_path(workspace_id)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    generation_id = payload.get("catalog_generation_id")
    return generation_id if isinstance(generation_id, str) else None


def catalog_receipt(catalog: AssertionCatalog, identity: AuthIdentity | None) -> CatalogReceipt:
    """Plan-level receipt: proof of the catalog generation a plan is built against.

    Calls only :class:`AssertionCatalog`'s public surface: ``search()`` first
    (the identity/rights fail-closed gate -- ``rebuild()`` itself performs no
    rights checking), then ``rebuild()`` for the generation id. ``rebuild()``
    is idempotent under the content-digest scheme (Seam 1): calling it
    repeatedly against an unchanged corpus returns a byte-identical receipt,
    so this is safe to call once per plan without perturbing anything.
    """

    if identity is None or not identity.workspace_id:
        return CatalogReceipt(record_count=0, catalog_generation_id=None, denial_reason="workspace_context_missing")
    probe = catalog.search(identity=identity, limit=1)
    if probe["denial_reason"] is not None:
        return CatalogReceipt(record_count=0, catalog_generation_id=None, denial_reason=probe["denial_reason"])
    receipt = catalog.rebuild(identity.workspace_id)
    return CatalogReceipt(
        record_count=receipt.record_count,
        catalog_generation_id=receipt.catalog_generation_id,
        denial_reason=None,
    )


def _residual_reason(decision: ReuseDecision) -> str | None:
    """Map a `ReuseDecision` to the frozen residual-reason vocabulary (CARP-2.2 table)."""

    if decision.action == "allow":
        return None
    if decision.action == "refresh":
        return "reuse_refresh_required"
    if decision.reason_code in _LIFECYCLE_DENY_REASONS:
        return "lifecycle_ineligible"
    return "reuse_denied"


def _project_reuse_input(
    packet: Mapping[str, Any],
    *,
    workspace_id: str,
    sensitivity_threshold: str | None,
) -> dict[str, Any]:
    """Project a catalog packet into ``evaluate_reuse()``'s flat input shape.

    Absolute rule (CARP-2.2 brief): pass through authoritative values only;
    never synthesize, infer, or default a missing field -- if the packet
    does not authoritatively carry a field, omit it and let
    :func:`evaluate_reuse` deny. Every field below is either a direct
    pass-through of an existing packet value, or a same-fact translation
    between two representations the catalog/ledger already authoritatively
    record (documented per-field below) -- never an invented default.

    * ``assertion_id`` -- direct pass-through (``packet["assertion"]["assertion_id"]``).
    * ``workspace_id`` -- not a field the ledger stamps on the record itself.
      Structurally established instead: :meth:`AssertionCatalog.packet` only
      ever returns records read from ``identity.workspace_id``'s own ledger
      partition (``assertion_catalog.py::_build_records`` roots at
      ``assertion_ledger/workspaces/{workspace_key(workspace_id)}``), so this
      is the same fact the catalog already enforced, not an inferred default.
    * ``lifecycle_state`` -- direct pass-through, re-read fresh by the caller
      via ``packet()`` immediately before this projection runs.
    * ``freshness_current`` -- ``packet["freshness"]`` is *itself* the
      catalog's own (lifecycle-state-keyed) freshness representation today
      (``assertion_catalog.py``'s ``"freshness": {"lifecycle_state": ...}``),
      not a second independent signal. True iff eligible, False iff stale;
      omitted for every other state (no authoritative signal to translate).
    * ``rights_allowed`` -- ``AssertionCatalog`` computes exactly one
      combined permission boolean (``_rights_decision``: known
      ``access_scope`` membership + ``allowed_for_work_output``). Direct
      pass-through of ``packet["rights_decision"]["allowed"]``.
    * ``sensitivity_allowed`` -- **not** aliased from ``rights_allowed``.
      The packet carries a second, independently-computed axis:
      ``packet["access_scope"]`` (``source_edition.access_scope`` --
      ``assertion_catalog.py``'s ``_build_records`` stamps it onto every
      packet unconditionally, whether or not rights allow reuse). This is
      ranked via the shared :data:`~research_foundry.services.sensitivity.SENSITIVITY_RANK`
      ordinal ordering against ``sensitivity_threshold`` -- a value that
      MUST come from the caller (:attr:`RetrievalConstraints.sensitivity_threshold`)
      and is never defaulted here. ``sensitivity_allowed`` is ``True`` iff
      the threshold resolves to a known rank AND the access-scope rank is at
      or below it; ``False`` if the threshold is present but unrecognized/
      malformed/empty (no ceiling to grant against -- denies outright, it
      never falls through to "allow up to the most sensitive tier") or the
      comparison otherwise denies (including an unrecognized ``access_scope``,
      ranked as maximally sensitive so it can never leak); and the key is
      **omitted entirely** when ``sensitivity_threshold`` is ``None`` --
      CARP-2.G's fix for a prior fail-closed-to-fail-open inversion where this
      field was aliased from ``rights_allowed``, making an edition's rights
      grant (which never evaluates a sensitivity ceiling) silently double as
      sensitivity clearance. Omission, not a synthesized default, is what
      lets :func:`evaluate_reuse` fail closed when no caller ever supplied a
      threshold -- the same principle a malformed/garbage threshold value
      must also honor (a follow-up CARP-2.G finding: the unknown-scope side
      already denied by falling to max rank, but the unknown-threshold side
      was defaulting to a ceiling instead of denying).
    * ``evaluation_passed`` -- derived from ``packet["evaluations"]`` (real,
      already-recorded ``assertion_evaluation`` verdicts for this exact
      assertion+version): True iff every recorded verdict is ``pass``, False
      iff any verdict is ``fail``, omitted otherwise (no evaluations, or an
      inconclusive abstain/needs_review-only mix).
    * ``invalidation_state`` -- source_assertion's own lifecycle vocabulary
      already has a distinct terminal state for "invalidated"
      (``invalidated``/``tombstoned``, disjoint from evaluate_reuse's own
      ``eligible``/``stale``/``blocked``/``invalid``/``retracted``/``deleted``/``superseded``
      vocabulary). ``"active"`` iff lifecycle_state is eligible or stale;
      omitted otherwise.
    * ``source_edition_id`` -- direct pass-through (``packet["assertion"]["source_edition_id"]``).
    * ``extraction_contract`` -- no field of this exact name exists on
      ``source_assertion``. ``extraction_provenance.schema_version`` is the
      ledger's own versioned identifier for the extraction methodology that
      produced this assertion -- the same concept "extraction contract"
      names -- so it is projected through under evaluate_reuse's field name.

    These are judgment calls a reviewer should scrutinize explicitly (see the
    CARP-2 completion report); none of them requires a code change to
    ``assertion_catalog.py``/``assertion_reuse.py`` -- they are all read-only
    reinterpretations of already-authoritative packet data.
    """

    projected: dict[str, Any] = {"workspace_id": workspace_id}

    assertion = packet.get("assertion")
    if isinstance(assertion, Mapping):
        assertion_id = assertion.get("assertion_id")
        if isinstance(assertion_id, str):
            projected["assertion_id"] = assertion_id
        source_edition_id = assertion.get("source_edition_id")
        if isinstance(source_edition_id, str):
            projected["source_edition_id"] = source_edition_id
        extraction_provenance = assertion.get("extraction_provenance")
        if isinstance(extraction_provenance, Mapping):
            schema_version = extraction_provenance.get("schema_version")
            if isinstance(schema_version, str):
                projected["extraction_contract"] = schema_version

    lifecycle_state = packet.get("lifecycle_state")
    if isinstance(lifecycle_state, str):
        projected["lifecycle_state"] = lifecycle_state
        if lifecycle_state == "eligible":
            projected["freshness_current"] = True
        elif lifecycle_state == "stale":
            projected["freshness_current"] = False
        if lifecycle_state in _NOT_INVALIDATED_LIFECYCLE_STATES:
            projected["invalidation_state"] = "active"

    rights_decision = packet.get("rights_decision")
    if isinstance(rights_decision, Mapping) and isinstance(rights_decision.get("allowed"), bool):
        projected["rights_allowed"] = rights_decision["allowed"]

    if sensitivity_threshold is not None:
        # Deliberate asymmetry: unknown SCOPE ranks maximally-sensitive (denies
        # by comparison), but unknown/malformed THRESHOLD has no ceiling to
        # grant against and must deny outright -- `.get(x, len(RANK))` on the
        # threshold side would turn a garbage/empty caller threshold into "allow
        # up to the most sensitive tier" (CARP-2.G finding: the fail-open twin
        # of the original inversion this field's fix already closed once).
        threshold_rank = SENSITIVITY_RANK.get(sensitivity_threshold)
        access_scope = packet.get("access_scope")
        scope_rank = (
            SENSITIVITY_RANK.get(access_scope, len(SENSITIVITY_RANK))
            if isinstance(access_scope, str)
            else len(SENSITIVITY_RANK)
        )
        projected["sensitivity_allowed"] = threshold_rank is not None and scope_rank <= threshold_rank
    # else: sensitivity_threshold is None -- omit `sensitivity_allowed`
    # entirely rather than defaulting a threshold. evaluate_reuse() denies
    # with `sensitivity_denied` on a missing key, same as on `False`.

    evaluations = packet.get("evaluations")
    if isinstance(evaluations, Iterable) and not isinstance(evaluations, (str, bytes, Mapping)):
        verdicts = {
            evaluation.get("verdict")
            for evaluation in evaluations
            if isinstance(evaluation, Mapping)
        }
        if verdicts:
            if verdicts == {"pass"}:
                projected["evaluation_passed"] = True
            elif "fail" in verdicts:
                projected["evaluation_passed"] = False

    return projected


def _collect_candidates(
    catalog: AssertionCatalog,
    identity: AuthIdentity,
    *,
    question: RetrievalQuestion,
    limits: RetrievalLimits,
) -> tuple[dict[str, frozenset[str]], bool, str | None]:
    """Discover authorized+eligible candidates and per-candidate matched-term evidence.

    Returns ``(matches, pagination_limit_reached, denial_reason)``. ``matches``
    maps ``assertion_id`` -> the subset of ``question.required_terms`` whose
    case-folded form is a substring of that candidate's catalog
    ``search_text`` -- computed entirely *inside*
    :meth:`AssertionCatalog.search` (one whole-string substring match per
    call, unchanged); this adapter never reads ``search_text`` itself
    (Seam 2, carp-contract-freeze.md §3.6). ``max_pages_per_question`` is a
    budget *shared* across every required-term sub-query for this one
    question (the frozen contract's explicit pagination-arithmetic ruling --
    NOT ``max_pages_per_question`` multiplied by the term count).

    When ``required_terms`` is empty, condition 1 is vacuous: one unfiltered
    sweep (bounded by the same shared budget) gathers the base authorized+eligible
    candidate set and every one of them is reported with an empty matched-term set.
    """

    terms: tuple[str | None, ...] = question.required_terms if question.required_terms else (None,)
    pages_remaining = limits.max_pages_per_question
    per_term_hits: dict[str | None, set[str]] = {}
    pagination_limit_reached = False

    for term in terms:
        hits: set[str] = set()
        cursor: str | None = None
        if pages_remaining <= 0:
            pagination_limit_reached = True
            per_term_hits[term] = hits
            continue
        while pages_remaining > 0:
            page = catalog.search(identity=identity, query=term, limit=limits.page_size, cursor=cursor)
            if page["denial_reason"] is not None:
                return {}, False, page["denial_reason"]
            pages_remaining -= 1
            hits.update(item["assertion_id"] for item in page["items"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        if cursor is not None:
            pagination_limit_reached = True
        per_term_hits[term] = hits

    if question.required_terms:
        union_ids: set[str] = set()
        for hits in per_term_hits.values():
            union_ids |= hits
        matches = {
            assertion_id: frozenset(
                term for term in question.required_terms if assertion_id in per_term_hits.get(term, set())
            )
            for assertion_id in union_ids
        }
    else:
        matches = {assertion_id: frozenset() for assertion_id in per_term_hits.get(None, set())}

    return matches, pagination_limit_reached, None


def retrieve(
    catalog: AssertionCatalog,
    *,
    identity: AuthIdentity | None,
    question: RetrievalQuestion,
    constraints: RetrievalConstraints | None = None,
    limits: RetrievalLimits | None = None,
    receipt: CatalogReceipt | None = None,
) -> RetrievalResult:
    """Bounded search + exact reuse/version evaluation for one CARP question.

    CARP-2.1 (search/packet adapter) and CARP-2.2 (exact reuse/version
    evaluation) combined: gathers a bounded, deterministically-ordered
    candidate set via :func:`_collect_candidates`, then for each candidate --
    ascending by ``assertion_id``, matching the catalog's own sort -- re-reads
    the full packet *immediately before evaluation* (never from the
    search-phase summary) and evaluates it against
    :func:`assertion_reuse.evaluate_reuse`. A candidate that disappears or
    becomes rights-denied between the search and packet-fetch steps (TOCTOU)
    is skipped silently: no signal about it is ever returned.

    ``receipt`` lets a multi-question caller (the future evidence-plan
    builder, CARP-3.2) capture one :class:`CatalogReceipt` at plan start via
    :func:`catalog_receipt` and pass it into every per-question ``retrieve()``
    call, rather than forcing a fresh ``rebuild()`` per question -- the
    frozen contract's own §3.4 mid-plan drift check expects the generation id
    to be captured *once* and only *re-checked* (via
    :func:`peek_catalog_generation_id`, never another ``rebuild()``) before
    each remaining question. When omitted, this function fetches its own
    receipt (convenient for a single, one-off question).
    """

    constraints = constraints or RetrievalConstraints()
    limits = (limits or RetrievalLimits()).clamped()

    if identity is None or not identity.workspace_id:
        return RetrievalResult(
            question_id=question.question_id,
            denial_reason="workspace_context_missing",
            catalog_generation_id=None,
            candidates=(),
            pagination_limit_reached=False,
            candidate_limit_reached=False,
        )

    receipt = receipt if receipt is not None else catalog_receipt(catalog, identity)
    if receipt.denial_reason is not None:
        return RetrievalResult(
            question_id=question.question_id,
            denial_reason=receipt.denial_reason,
            catalog_generation_id=None,
            candidates=(),
            pagination_limit_reached=False,
            candidate_limit_reached=False,
        )

    matches, pagination_limit_reached, denial_reason = _collect_candidates(
        catalog, identity, question=question, limits=limits
    )
    if denial_reason is not None:
        return RetrievalResult(
            question_id=question.question_id,
            denial_reason=denial_reason,
            catalog_generation_id=None,
            candidates=(),
            pagination_limit_reached=False,
            candidate_limit_reached=False,
        )

    ordered_ids = sorted(matches)
    candidate_limit_reached = len(ordered_ids) > limits.max_candidates_per_question
    selected_ids = ordered_ids[: limits.max_candidates_per_question]

    candidates: list[EvaluatedCandidate] = []
    for assertion_id in selected_ids:
        try:
            packet = catalog.packet(assertion_id, identity=identity)
        except AssertionCatalogDenied:
            # TOCTOU: rights flipped to denied between search() and packet() --
            # skip silently, no candidate-derived signal leaks for this entry.
            continue
        if packet is None:
            # TOCTOU: the record vanished between search() and packet() (e.g. a
            # concurrent rebuild dropped it) -- skip silently.
            continue

        lifecycle_state = packet.get("lifecycle_state")
        assertion_version = packet.get("assertion_version")
        if not isinstance(lifecycle_state, str) or not isinstance(assertion_version, int):
            continue

        reuse_input = _project_reuse_input(
            packet,
            workspace_id=identity.workspace_id,
            sensitivity_threshold=constraints.sensitivity_threshold,
        )
        decision = evaluate_reuse(
            reuse_input,
            workspace_id=identity.workspace_id,
            required_edition_id=constraints.required_edition_id,
            required_extraction_contract=constraints.required_extraction_contract,
        )
        # CARP capability gate -- mirror run_launch.py:106-107 exactly.
        # ``constraints.automated_reuse_allowed`` is caller-supplied and never
        # defaulted here (§8.1 sensitivity-threshold precedent): a missing
        # (``None``) or explicitly-``False`` capability collapses every
        # otherwise-``allow`` decision into the SAME
        # ``deny``/``automated_reuse_disabled`` reason code the ledger seam
        # already emits -- CARP's catalog-retrieval path is bound by the
        # same capability gate as the ledger, never fail-open. Fail-closed
        # here (``coverage_state == residual`` / ``residual_reason ==
        # reuse_denied`` via ``_residual_reason``) is the frozen behavior;
        # the §3.2 residual-reason enum is CLOSED and needs no new member.
        if decision.allowed and constraints.automated_reuse_allowed is not True:
            decision = ReuseDecision("deny", "automated_reuse_disabled", decision.assertion_id)
        matched_terms = matches.get(assertion_id, frozenset())
        lexical_match = (not question.required_terms) or (matched_terms == frozenset(question.required_terms))
        qualifiers = packet.get("qualifiers")

        candidates.append(
            EvaluatedCandidate(
                assertion_id=assertion_id,
                assertion_version=assertion_version,
                lifecycle_state=lifecycle_state,
                lexical_match=lexical_match,
                matched_terms=tuple(term for term in question.required_terms if term in matched_terms),
                qualifiers=qualifiers if isinstance(qualifiers, Mapping) else {},
                reuse_decision=decision,
                residual_reason=_residual_reason(decision),
                retrieval_receipt=RetrievalReceipt(
                    action=decision.action,
                    reason_code=decision.reason_code,
                    assertion_id=assertion_id,
                    assertion_version=assertion_version,
                    catalog_generation_id=receipt.catalog_generation_id,
                ),
            )
        )

    return RetrievalResult(
        question_id=question.question_id,
        denial_reason=None,
        catalog_generation_id=receipt.catalog_generation_id,
        candidates=tuple(candidates),
        pagination_limit_reached=pagination_limit_reached,
        candidate_limit_reached=candidate_limit_reached,
    )


__all__ = [
    "MAX_CANDIDATES_PER_QUESTION",
    "MAX_PAGES_PER_QUESTION",
    "MAX_PAGE_SIZE",
    "RetrievalQuestion",
    "RetrievalConstraints",
    "RetrievalLimits",
    "CatalogReceipt",
    "RetrievalReceipt",
    "EvaluatedCandidate",
    "RetrievalResult",
    "peek_catalog_generation_id",
    "catalog_receipt",
    "retrieve",
]
