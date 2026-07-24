"""Deterministic, catalog-backed evidence-plan builder (CARP-3).

This module implements the frozen six-condition coverage rule and the
evidence-plan builder against the CARP-2 governed catalog adapter
(:mod:`research_foundry.services.catalog_retrieval`) *only*. It never imports
``assertion_catalog``/``assertion_reuse`` and never reads ``assertion_ledger/``
paths -- every fact this module reasons about arrives through the adapter's
own DTOs (``RetrievalResult``/``EvaluatedCandidate``/``CatalogReceipt``). See
``docs/dev/architecture/carp-contract-freeze.md`` for the frozen contract this
builder implements against.

Two functions matter:

* :func:`evaluate_question_coverage` -- CARP-3.1, the coverage rule. Pure and
  total: given one question's bounded ``RetrievalResult``, it always returns
  exactly one terminal :class:`CoverageDecision`. It never raises past its own
  boundary -- any internal inconsistency resolves to ``residual`` /
  ``evaluation_error``.
* :func:`build_evidence_plan` -- CARP-3.2, the orchestrator. Calls the adapter
  once per question (plus one bounded "pin re-check" call per would-be-covered
  question, to enforce condition 6 -- see below), assembles a schema-shaped
  plan dict, and never touches the filesystem itself.
  :func:`write_evidence_plan` performs the atomic write separately.

Design decisions a reviewer should scrutinize explicitly (none of them widens
or weakens the frozen contract; each is documented here because the contract
freeze either left the mechanism open or the current ledger schema has no
reachable signal for it):

* **Condition 4a, ``required_source_types`` -- structurally unsatisfiable in
  v1.** No field named or shaped like a "source type" is reachable through
  :meth:`AssertionCatalog.packet`'s returned mapping -- it lives only on
  ``source_card.schema.yaml``'s ``source.source_type``, which the packet
  never carries (confirmed by inspecting ``source_assertion.schema.yaml``,
  ``source_edition.schema.yaml``, and ``passage.schema.yaml``: none of them
  has any such field, and :class:`~.catalog_retrieval.EvaluatedCandidate`
  does not expose one either). This is the same shape of gap the freeze doc's
  own §3.6 names for ``search_text`` (Seam 2) and ``catalog_generation_id``
  (Seam 1) -- a real contract gap, not a documentation oversight. Per §3.1
  condition 4's own wording ("a constraint the candidate cannot be *shown* to
  meet is residual"), this module treats any question that declares a
  non-empty ``required_source_types`` as always failing condition 4a
  (``source_type_mismatch``) -- never covered, never silently ignored. A
  question that declares no ``required_source_types`` is unaffected (the
  constraint is vacuous, matching the adapter's own empty-``required_terms``
  convention).
* **Condition 5, contradiction -- no ledger-level signal exists.** The only
  "contradicts"-shaped field anywhere in the ledger schemas is
  ``source_assertion.schema.yaml``'s ``synthesis.input_refs[].contribution``
  enum (which records how OTHER assertions fed one ``derived_synthesis``
  assertion, not a general pairwise relationship between arbitrary
  candidates), and it is not surfaced on ``EvaluatedCandidate`` at all. This
  module instead detects contradiction structurally, from data the adapter
  already exposes: two otherwise-authorized candidates (lexically matched,
  lifecycle-eligible, reuse-allowed) for the *same* question that disagree
  (exact, non-null inequality) on the same ``qualifiers`` key. This is a
  deliberate, documented interpretation of condition 5 -- not a workaround
  for missing data and not a semantic/model judgement -- it only compares
  already-authoritative structured values the adapter surfaces on every
  candidate, the same way condition 4b's own qualifier check does.
* **Condition 6, version pinning -- an explicit "pin re-check".** The freeze
  doc's H3 scenario 9 names "the pin-at-selection re-check" as an expected
  mechanism. This module implements it literally: once a candidate wins
  conditions 1-5, it issues exactly one more bounded ``retrieve()`` call for
  that same question (reusing the plan's single captured
  :class:`~.catalog_retrieval.CatalogReceipt`, never a fresh rebuild) and
  confirms the winner's ``assertion_id``/``assertion_version`` are still
  present and unchanged immediately before finalizing the selection. A
  version delta resolves to ``version_mismatch``; a vanished candidate
  resolves to ``evaluation_error`` (an uncertain/unrepresentable state, per
  §3.2's catch-all).
* **``summary.questions_total`` reports the plan's own bounded question
  count**, i.e. ``len(questions)`` after the ``max_questions`` ceiling is
  applied -- not the caller's raw, pre-clamp request size. There is no
  residual-reason code for "question dropped by the max_questions ceiling"
  (the 14-member enum has none), so a value above the ceiling is never
  represented as a question entry at all; reporting the *bounded* total keeps
  ``summary.questions_total`` internally consistent with
  ``len(plan["questions"])`` in every case, rather than naming a count with no
  entries to match it.
* **``summary.avoided_provider_calls`` == ``questions_covered``.** Every
  covered question is, by definition, one question a ``catalog_then_discovery``
  caller would not need to route to a provider. The frozen contract only
  requires this counter be ``0``/absent on a denied or empty catalog; it does
  not define the counter's formula, so this is this module's own documented
  choice.
* **``EvidencePlanQuestion.forced_residual_reason`` (P6 CARP-6.9 F4).** A
  question's derived ``required_terms`` can be empty for two different
  reasons that must stay distinguishable: a caller genuinely declaring no
  term constraints (the adapter's frozen, correct vacuous-match rule at
  ``catalog_retrieval.py``'s condition 1), or a plan-construction call site's
  own free-text derivation failing to extract anything from real, non-empty
  text (a defect if left unmarked -- it would let condition 1's vacuous rule
  fire for a question that actually said something, resolving an arbitrary
  candidate ``covered``). This field lets ``planning.py``/``search_router/
  router.py`` mark the second case explicitly; when set, this module never
  calls ``retrieve()`` for that question and emits it terminal ``residual``
  with the given (frozen-enum) reason instead. A hand-built
  ``EvidencePlanQuestion`` that never sets this field (e.g. every direct
  adapter-level test) is completely unaffected -- the vacuous rule it
  exercises is untouched.

No network call, no model call, no ambient time/randomness (``datetime.now``,
``uuid4``) appears anywhere in this module -- every timestamp/identifier the
output plan carries (``evidence_plan_id``, ``generated_at``, ``decided_at``)
is an *injected* field on :class:`EvidencePlanRequest`, never computed here.
This is what makes :func:`build_evidence_plan` byte-equivalent on replay
(carp-contract-freeze.md §3.4): same inputs, same captured catalog generation,
same output bytes.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..api.auth.provider import AuthIdentity
from ..yamlio import dumps_yaml
from .catalog_retrieval import (
    CatalogReceipt,
    EvaluatedCandidate,
    RetrievalConstraints,
    RetrievalLimits,
    RetrievalQuestion,
    RetrievalResult,
    catalog_receipt,
    peek_catalog_generation_id,
    retrieve,
)

if TYPE_CHECKING:  # pragma: no cover - static typing only, never imported at runtime.
    from .assertion_catalog import AssertionCatalog

#: Frozen ceiling (carp-contract-freeze.md §3.3). Enforced defensively here,
#: same "clamp, never trust verbatim" style as catalog_retrieval.RetrievalLimits.
MAX_QUESTIONS = 200

#: Per-candidate blocking-reason severity, in the same order as
#: carp-contract-freeze.md §3.1's six conditions (1 -> lexical, 2/3 -> the
#: adapter's own combined lifecycle/reuse residual_reason, 4a -> source type,
#: 4b -> qualifiers, 5 -> contradiction). When no candidate for a question is
#: fully covered, the question's single residual_reason is the reason carried
#: by whichever candidate reached the *deepest* condition before failing --
#: ties broken by ascending assertion_id (the adapter's own candidate order).
_REASON_RANK: Mapping[str, int] = {
    "lexical_miss": 1,
    "reuse_refresh_required": 2,
    "reuse_denied": 2,
    "lifecycle_ineligible": 2,
    "source_type_mismatch": 3,
    "qualifier_missing": 4,
    "contradiction": 5,
}


@dataclass(frozen=True)
class EvidencePlanQuestion:
    """One CARP question as the evidence-plan builder receives it.

    A superset of :class:`~.catalog_retrieval.RetrievalQuestion` (adds
    ``question_text``, the schema's own optional descriptive field) --
    :meth:`as_retrieval_question` narrows it back down for the adapter call.
    """

    question_id: str
    question_text: str | None = None
    required_terms: tuple[str, ...] = ()
    required_source_types: tuple[str, ...] = ()
    required_qualifiers: Mapping[str, str] = field(default_factory=dict)
    #: P6 CARP-6.9 F4: set ONLY by a plan-construction call site (``planning.py``'s
    #: CARP block, ``search_router/router.py::_build_ad_hoc_evidence_plan``) when
    #: its own free-text term derivation produced an empty ``required_terms`` from
    #: genuinely non-empty source text -- a derivation failure, never a caller's
    #: real "no term constraints" declaration. ``catalog_retrieval.retrieve()``'s
    #: coverage condition 1 (frozen, carp-contract-freeze.md §3.1) treats an empty
    #: ``required_terms`` as vacuously true for every authorized candidate; that
    #: rule stays correct and untouched for a genuinely caller-declared empty
    #: ``required_terms`` (e.g. a hand-built ``EvidencePlanQuestion`` in a test
    #: exercising the adapter directly, which never sets this field). It is NOT
    #: correct for a question whose ``required_terms`` is empty only because its
    #: own derivation step failed to extract anything from real text -- letting
    #: that flow into ``retrieve()`` unmarked would let an arbitrary, unrelated
    #: catalog candidate resolve ``covered``. When set, :func:`build_evidence_plan`
    #: never calls ``retrieve()`` for this question and instead emits it as a
    #: terminal ``residual`` with this exact reason (must be a member of the
    #: frozen, closed ``residual_reason`` enum -- §3.2; no new member is added).
    forced_residual_reason: str | None = None

    def as_retrieval_question(self) -> RetrievalQuestion:
        return RetrievalQuestion(
            question_id=self.question_id,
            required_terms=self.required_terms,
            required_source_types=self.required_source_types,
            required_qualifiers=self.required_qualifiers,
        )


@dataclass(frozen=True)
class EvidencePlanLimits:
    """Caller-requested ceilings, clamped to the frozen §3.3 ceilings before use."""

    max_questions: int = MAX_QUESTIONS
    retrieval: RetrievalLimits = field(default_factory=RetrievalLimits)

    def clamped(self) -> EvidencePlanLimits:
        return EvidencePlanLimits(
            max_questions=max(1, min(self.max_questions, MAX_QUESTIONS)),
            retrieval=self.retrieval.clamped(),
        )


@dataclass(frozen=True)
class EvidencePlanRequest:
    """Everything one :func:`build_evidence_plan` call needs, injected.

    ``evidence_plan_id``/``generated_at``/``decided_at`` are caller-supplied
    on purpose -- this module never mints an id or reads the clock, which is
    what keeps the same request replaying byte-identical.
    """

    evidence_plan_id: str
    workspace_id: str
    retrieval_policy: str
    questions: tuple[EvidencePlanQuestion, ...] = ()
    schema_version: str | None = None
    brief_id: str | None = None
    run_id: str | None = None
    generated_at: str | None = None
    decided_at: str | None = None
    constraints: RetrievalConstraints = field(default_factory=RetrievalConstraints)
    limits: EvidencePlanLimits = field(default_factory=EvidencePlanLimits)


@dataclass(frozen=True)
class CoverageDecision:
    """CARP-3.1's pure output: one question's terminal coverage state.

    ``evaluated_candidates`` is the deduplicated (by ``assertion_id``),
    ascending-``assertion_id``-ordered candidate set this decision was
    computed from -- the caller (CARP-3.2) reuses it verbatim to build the
    plan's ``evaluated_candidates`` array, so ``candidates_evaluated`` never
    double-counts a duplicate raw hit. ``selection_note`` is audit-only
    (never serialized into the schema-constrained plan output, which has no
    field for it) -- the plan's own ``evaluated_candidates`` array, carrying
    every equivalent hit with only the winner marked ``selected: true``, is
    the schema-valid form of the same audit trail.
    """

    coverage_state: str
    residual_reason: str | None
    evaluated_candidates: tuple[EvaluatedCandidate, ...]
    selected: EvaluatedCandidate | None
    selection_note: str | None


def _dedupe(candidates: Sequence[EvaluatedCandidate]) -> tuple[EvaluatedCandidate, ...]:
    """Ascending-``assertion_id`` order, first-occurrence-wins deduplication.

    The adapter's own ``_collect_candidates`` already dedupes via dict
    semantics, so a real ``retrieve()`` call should never hand this function
    a duplicate ``assertion_id`` -- this is defense-in-depth against a future
    adapter change or a hand-built ``RetrievalResult`` (H3 scenario 13,
    "duplicate candidate"), never relied upon to mask a real defect.
    """

    seen: set[str] = set()
    ordered: list[EvaluatedCandidate] = []
    for candidate in sorted(candidates, key=lambda item: item.assertion_id):
        if candidate.assertion_id in seen:
            continue
        seen.add(candidate.assertion_id)
        ordered.append(candidate)
    return tuple(ordered)


def _qualifiers_satisfied(required: Mapping[str, str], candidate_qualifiers: Mapping[str, Any]) -> bool:
    """Condition 4b: every required qualifier key/value pair, exact match.

    A required key absent from the candidate's qualifiers, or present with a
    different value, is "missing constraint data" per §3.1 condition 4 --
    never treated as satisfied.
    """

    if not required:
        return True
    return all(key in candidate_qualifiers and candidate_qualifiers[key] == value for key, value in required.items())


def _contradicts(candidate: EvaluatedCandidate, pool: Sequence[EvaluatedCandidate]) -> bool:
    """Condition 5, this module's documented mechanism (see module docstring).

    True iff another authorized (lexically-matched, lifecycle-eligible,
    reuse-allowed) candidate for the same question carries a different
    non-null value for a qualifier key ``candidate`` itself also has a
    non-null value for.
    """

    own = {key: value for key, value in candidate.qualifiers.items() if value is not None}
    if not own:
        return False
    for other in pool:
        if other.assertion_id == candidate.assertion_id:
            continue
        if not other.lexical_match or other.residual_reason is not None:
            continue
        for key, value in own.items():
            other_value = other.qualifiers.get(key)
            if other_value is not None and other_value != value:
                return True
    return False


def _candidate_blocking_reason(
    candidate: EvaluatedCandidate,
    question: EvidencePlanQuestion,
    pool: Sequence[EvaluatedCandidate],
) -> str | None:
    """The first (per §3.1's own 1-6 ordering) condition this candidate fails, if any.

    Conditions 2 and 3 (lifecycle eligibility re-read, reuse decision) are
    both already resolved by the adapter into ``candidate.residual_reason``
    -- this function trusts that value rather than re-deriving it, per "this
    module consumes adapter DTOs only".
    """

    if not candidate.lexical_match:
        return "lexical_miss"
    if candidate.residual_reason is not None:
        return candidate.residual_reason
    if question.required_source_types:
        return "source_type_mismatch"
    if not _qualifiers_satisfied(question.required_qualifiers, candidate.qualifiers):
        return "qualifier_missing"
    if _contradicts(candidate, pool):
        return "contradiction"
    return None


def evaluate_question_coverage(result: RetrievalResult, question: EvidencePlanQuestion) -> CoverageDecision:
    """CARP-3.1: pure, total mapping from one question's bounded retrieval
    result to exactly one terminal :class:`CoverageDecision`.

    Never raises past this boundary -- any internal inconsistency resolves to
    ``residual`` / ``evaluation_error`` rather than propagating an exception.
    """

    try:
        return _evaluate_question_coverage(result, question)
    except Exception:
        try:
            candidates = _dedupe(getattr(result, "candidates", None) or ())
        except Exception:
            candidates = ()
        return CoverageDecision("residual", "evaluation_error", candidates, None, None)


def _evaluate_question_coverage(result: RetrievalResult, question: EvidencePlanQuestion) -> CoverageDecision:
    if result.denial_reason is not None:
        return CoverageDecision("residual", "evaluation_error", (), None, None)

    candidates = _dedupe(result.candidates)

    if not candidates:
        if result.pagination_limit_reached:
            return CoverageDecision("residual", "pagination_limit", candidates, None, None)
        if result.candidate_limit_reached:
            return CoverageDecision("residual", "candidate_limit", candidates, None, None)
        return CoverageDecision("residual", "no_candidate", candidates, None, None)

    reasons = [(_candidate_blocking_reason(candidate, question, candidates), candidate) for candidate in candidates]
    winners = [candidate for reason, candidate in reasons if reason is None]
    if winners:
        winner = winners[0]
        note = (
            f"selected lowest assertion_id ({winner.assertion_id}) among "
            f"{len(winners)} equivalent covered candidates"
            if len(winners) > 1
            else None
        )
        return CoverageDecision("covered", None, candidates, winner, note)

    # No candidate is fully covering. A limit that truncated the search means
    # this result is an incomplete view of the corpus -- prefer that signal
    # over a per-candidate reason that might be wrong precisely because the
    # sweep never finished.
    if result.pagination_limit_reached:
        return CoverageDecision("residual", "pagination_limit", candidates, None, None)
    if result.candidate_limit_reached:
        return CoverageDecision("residual", "candidate_limit", candidates, None, None)

    best_reason = "evaluation_error"
    best_rank = -1
    for reason, _ in reasons:
        rank = _REASON_RANK.get(reason or "", -1)
        if rank > best_rank:
            best_rank = rank
            best_reason = reason or "evaluation_error"
    return CoverageDecision("residual", best_reason, candidates, None, None)


def _pin_recheck(
    catalog: AssertionCatalog,
    *,
    identity: AuthIdentity | None,
    question: EvidencePlanQuestion,
    constraints: RetrievalConstraints,
    limits: RetrievalLimits,
    receipt: CatalogReceipt,
    winner: EvaluatedCandidate,
) -> tuple[str, str | None, EvaluatedCandidate | None]:
    """Condition 6's "pin-at-selection re-check" (H3 scenario 9).

    One more bounded ``retrieve()`` call for the same question, reusing the
    plan's single captured receipt (never a fresh ``rebuild()``), confirming
    the winner's exact ``assertion_id``/``assertion_version`` are still
    present and otherwise-covering immediately before the plan pins them.
    """

    recheck = retrieve(
        catalog,
        identity=identity,
        question=question.as_retrieval_question(),
        constraints=constraints,
        limits=limits,
        receipt=receipt,
    )
    if recheck.denial_reason is not None:
        return "residual", "evaluation_error", None
    match = next((candidate for candidate in recheck.candidates if candidate.assertion_id == winner.assertion_id), None)
    if match is None:
        return "residual", "evaluation_error", None
    if match.assertion_version != winner.assertion_version:
        return "residual", "version_mismatch", None
    reason = _candidate_blocking_reason(match, question, recheck.candidates)
    if reason is not None:
        return "residual", reason, None
    return "covered", None, match


def _candidate_dict(
    candidate: EvaluatedCandidate,
    question: EvidencePlanQuestion,
    pool: Sequence[EvaluatedCandidate],
    selected_id: str | None,
) -> dict[str, Any]:
    return {
        "assertion_id": candidate.assertion_id,
        "assertion_version": candidate.assertion_version,
        "lifecycle_state": candidate.lifecycle_state,
        "lexical_match": candidate.lexical_match,
        "source_type_satisfied": not question.required_source_types,
        "qualifiers_satisfied": _qualifiers_satisfied(question.required_qualifiers, candidate.qualifiers),
        "reuse_decision": {
            "action": candidate.reuse_decision.action,
            "reason_code": candidate.reuse_decision.reason_code,
        },
        "contradicts": _contradicts(candidate, pool),
        "selected": candidate.assertion_id == selected_id,
    }


def _terminal_question_dict(question: EvidencePlanQuestion, reason: str) -> dict[str, Any]:
    """A whole-plan denial/empty/drift terminal: zero candidate-derived signal."""

    return {
        "question_id": question.question_id,
        "question_text": question.question_text,
        "required_terms": list(question.required_terms),
        "required_source_types": list(question.required_source_types),
        "required_qualifiers": dict(question.required_qualifiers),
        "evaluated_candidates": [],
        "selected_assertion_ref": None,
        "retrieval_receipt": None,
        "coverage_state": "residual",
        "residual_reason": reason,
    }


def _question_dict(
    question: EvidencePlanQuestion,
    evaluated_candidates: Sequence[EvaluatedCandidate],
    coverage_state: str,
    residual_reason: str | None,
    selected: EvaluatedCandidate | None,
    receipt: CatalogReceipt,
    decided_at: str | None,
) -> dict[str, Any]:
    selected_id = selected.assertion_id if selected is not None else None
    candidate_dicts = [_candidate_dict(candidate, question, evaluated_candidates, selected_id) for candidate in evaluated_candidates]

    base: dict[str, Any] = {
        "question_id": question.question_id,
        "question_text": question.question_text,
        "required_terms": list(question.required_terms),
        "required_source_types": list(question.required_source_types),
        "required_qualifiers": dict(question.required_qualifiers),
        "evaluated_candidates": candidate_dicts,
    }
    if coverage_state == "covered" and selected is not None:
        base["selected_assertion_ref"] = {
            "assertion_id": selected.assertion_id,
            "assertion_version": selected.assertion_version,
        }
        base["retrieval_receipt"] = {
            "source": "catalog",
            "catalog_generation_id": receipt.catalog_generation_id,
            "decided_at": decided_at,
        }
        base["coverage_state"] = "covered"
        base["residual_reason"] = None
    else:
        base["selected_assertion_ref"] = None
        base["retrieval_receipt"] = None
        base["coverage_state"] = "residual"
        base["residual_reason"] = residual_reason or "evaluation_error"
    return base


def _summary(questions_total: int, plan_state: Sequence[tuple[str, str | None, int]], record_count: int) -> dict[str, Any]:
    """§2.4/§3's zero-candidate-derived-fields rule: gate all six
    candidate-derived counters (``questions_residual`` included) on
    ``record_count > 0``; ``questions_total`` is the sole exception."""

    summary: dict[str, Any] = {"questions_total": questions_total}
    if record_count <= 0:
        return summary

    covered = sum(1 for state, _, _ in plan_state if state == "covered")
    residual = sum(1 for state, _, _ in plan_state if state == "residual")
    candidates_evaluated = sum(count for _, _, count in plan_state)
    reason_counts: dict[str, int] = {}
    for state, reason, _ in plan_state:
        if state == "residual" and reason:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    summary["questions_covered"] = covered
    summary["questions_residual"] = residual
    summary["candidates_evaluated"] = candidates_evaluated
    summary["candidates_selected"] = covered
    summary["avoided_provider_calls"] = covered
    summary["residual_reason_counts"] = reason_counts
    return summary


def build_evidence_plan(
    catalog: AssertionCatalog,
    *,
    identity: AuthIdentity | None,
    request: EvidencePlanRequest,
) -> dict[str, Any]:
    """CARP-3.2: build one schema-shaped evidence plan dict (no filesystem I/O).

    Iterates ``request.questions`` in ascending ``question_id`` order (stable,
    bounded to ``request.limits.max_questions``), captures exactly one
    :class:`~.catalog_retrieval.CatalogReceipt` at plan start, and re-checks
    (never re-``rebuild()``s) the catalog generation before resolving each
    remaining question (§3.4's mid-plan drift rule). Call
    :func:`write_evidence_plan` separately to persist the result atomically.
    """

    limits = request.limits.clamped()
    questions = tuple(sorted(request.questions, key=lambda item: item.question_id))[: limits.max_questions]

    receipt = catalog_receipt(catalog, identity)
    receipt_dict = {
        "record_count": receipt.record_count,
        "catalog_generation_id": receipt.catalog_generation_id,
        "generated_at": request.generated_at,
        "denial_reason": receipt.denial_reason,
    }

    plan_state: list[tuple[str, str | None, int]] = []
    question_dicts: list[dict[str, Any]] = []

    if receipt.record_count <= 0:
        fallback_reason = "catalog_denied" if receipt.denial_reason is not None else "catalog_empty"
        for question in questions:
            question_dicts.append(_terminal_question_dict(question, fallback_reason))
            plan_state.append(("residual", fallback_reason, 0))
    else:
        captured_generation_id = receipt.catalog_generation_id
        for question in questions:
            if question.forced_residual_reason is not None:
                # P6 CARP-6.9 F4: a derivation failure at the plan-construction
                # boundary, not a catalog fact -- never call retrieve() for it.
                question_dicts.append(_terminal_question_dict(question, question.forced_residual_reason))
                plan_state.append(("residual", question.forced_residual_reason, 0))
                continue

            current_generation_id = peek_catalog_generation_id(catalog, request.workspace_id)
            if captured_generation_id is not None and current_generation_id != captured_generation_id:
                question_dicts.append(_terminal_question_dict(question, "evaluation_error"))
                plan_state.append(("residual", "evaluation_error", 0))
                continue

            result = retrieve(
                catalog,
                identity=identity,
                question=question.as_retrieval_question(),
                constraints=request.constraints,
                limits=limits.retrieval,
                receipt=receipt,
            )
            decision = evaluate_question_coverage(result, question)

            state, reason, selected = decision.coverage_state, decision.residual_reason, None
            if state == "covered" and decision.selected is not None:
                state, reason, selected = _pin_recheck(
                    catalog,
                    identity=identity,
                    question=question,
                    constraints=request.constraints,
                    limits=limits.retrieval,
                    receipt=receipt,
                    winner=decision.selected,
                )

            question_dicts.append(_question_dict(question, decision.evaluated_candidates, state, reason, selected, receipt, request.decided_at))
            plan_state.append((state, reason, len(decision.evaluated_candidates)))

    summary = _summary(len(questions), plan_state, receipt.record_count)

    return {
        "evidence_plan_id": request.evidence_plan_id,
        "schema_version": request.schema_version or "1",
        "workspace_id": request.workspace_id,
        "brief_id": request.brief_id,
        "run_id": request.run_id,
        "retrieval_policy": request.retrieval_policy,
        "catalog_receipt": receipt_dict,
        "limits": {
            "max_questions": limits.max_questions,
            "max_candidates_per_question": limits.retrieval.max_candidates_per_question,
            "max_pages_per_question": limits.retrieval.max_pages_per_question,
            "page_size": limits.retrieval.page_size,
        },
        "questions": question_dicts,
        "summary": summary,
    }


def write_evidence_plan(plan: Mapping[str, Any], path: Path) -> Path:
    """Write ``plan`` atomically: temp file in ``path``'s own directory, then
    ``os.replace``. Mirrors ``builder_service._atomic_write_yaml`` -- a crash
    mid-write must never leave a torn/partial plan file visible at ``path``."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(dumps_yaml(dict(plan)))
        os.replace(temporary_name, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(temporary_name)
        raise
    return path


__all__ = [
    "MAX_QUESTIONS",
    "EvidencePlanQuestion",
    "EvidencePlanLimits",
    "EvidencePlanRequest",
    "CoverageDecision",
    "evaluate_question_coverage",
    "build_evidence_plan",
    "write_evidence_plan",
]
