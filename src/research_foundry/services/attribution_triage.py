"""Source-attribution triage/assembly (source-metadata-propagation-v1, M2 / SMP-2.4).

Mirrors ``services/rights_triage.py``'s shape: a private worker that does the
real (and potentially raise-y) work, wrapped by a public entrypoint that
never raises and degrades to a structured failure record on exception rather
than propagating or silently swallowing the error. Here the worker reads and
assembles already-minted ``source_attribution`` records (schema:
``schemas/source_attribution.schema.yaml``) instead of classifying a
capture-time rights posture -- there is no first-party signal to classify;
this module's whole job is reducing existing authoritative records into the
structured result a later mirror-computation step (the card's
``attribution_summary``, M2's next task) consumes.

Append-only by construction
----------------------------
There is no ``update_attribution_record``/``patch_*`` function anywhere in
this module, and :class:`AttributionRecord` is a frozen dataclass -- there is
no ``setattr`` path to an existing instance's fields. A refresh
(:func:`refresh_attribution_record`) always returns a brand-new
:class:`AttributionRecord` with a freshly minted ``attribution_id`` and its
own ``observed_at``, carrying ``supersedes_attribution_id`` pointing
backward at the record it replaces. The record being refreshed is only ever
read (for its stable identity fields), never written to. A bad value is
superseded, never corrected in place.

Clock discipline (deliberate deviation from ``rights_triage.py``, per this
task's explicit instruction)
-------------------------------------------------------------------------------
``rights_triage.py``'s own capture-time wrapper stamps a caught failure with
a direct wall-clock read. This module does not do that: every timestamp it
ever emits (a minted record's ``observed_at``, a triage failure's
``attempted_at``) is an explicit, injected, keyword-only parameter with no
default -- following ``rights_validation.py``'s ``as_of`` idiom rather than
reading the clock itself. This module never imports or calls the ids
module's wall-clock helpers (the injectable ``now()``/ISO-timestamp
functions, or the raw stdlib clock) -- callers obtain "now" however they
like at their own write call site and pass the resulting string in. The only
``ids`` helpers imported here (``slugify``, ``short_hash``) are pure string/
hash functions with no clock dependency.

File conventions
-----------------
``source_attribution`` instances are plain YAML files, one record per file
(mirrors ``rights_validation.py``'s stated convention for
``rights_record`` -- no prior Python consumer of this schema existed before
this task, so this establishes the convention rather than inventing a
second one; a future writer should reuse ``<attribution_id>.yaml`` naming in
whatever directory it manages).

Cross-source rollups without a separate API
--------------------------------------------
:func:`triage_records` / :func:`compute_source_attribution_triage` group
purely by ``(asserter_id, assertion_kind)`` and are indifferent to which
physical source each input record was captured against -- ``source`` is only
a caller-supplied label carried on the returned result, never a filter over
the input records. Passing records gathered from multiple source_cards into
one call is therefore how the plan's "cross-source values propagate as a
set-union keyed by (asserter_id, assertion_kind)" requirement is satisfied,
without a second, redundant merge function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..ids import short_hash, slugify
from ..yamlio import load_yaml

__all__ = [
    "AttributionRecord",
    "AttributionRollup",
    "AttributionTriageResult",
    "mint_attribution_record",
    "refresh_attribution_record",
    "load_attribution_records",
    "triage_records",
    "compute_source_attribution_triage",
]

SCHEMA_VERSION = "1.0"

_REQUIRED_FIELDS = (
    "source",
    "asserter_id",
    "asserter_type",
    "assertion_kind",
    "value",
    "observed_at",
    "license_basis",
)


@dataclass(frozen=True)
class AttributionRecord:
    """Immutable in-memory view of one ``source_attribution`` instance.

    Frozen by construction -- there is no way to mutate an existing instance's
    fields. See the module docstring's append-only invariant.
    """

    schema_version: str
    attribution_id: str
    source: str
    asserter_id: str
    asserter_type: str
    assertion_kind: str
    value: Any
    observed_at: str
    license_basis: str
    retrieval_evidence_ref: str | None = None
    supersedes_attribution_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Schema-shaped ``dict`` (all declared properties present, optionals as ``null``)."""

        return {
            "schema_version": self.schema_version,
            "attribution_id": self.attribution_id,
            "source": self.source,
            "asserter_id": self.asserter_id,
            "asserter_type": self.asserter_type,
            "assertion_kind": self.assertion_kind,
            "value": self.value,
            "observed_at": self.observed_at,
            "license_basis": self.license_basis,
            "retrieval_evidence_ref": self.retrieval_evidence_ref,
            "supersedes_attribution_id": self.supersedes_attribution_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AttributionRecord":
        """Build a record from a loaded YAML mapping. Raises on missing required fields."""

        missing = [f for f in _REQUIRED_FIELDS if f not in data]
        if "attribution_id" not in data:
            missing.append("attribution_id")
        if missing:
            raise ValueError(f"attribution record missing required field(s): {sorted(set(missing))}")
        return cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            attribution_id=data["attribution_id"],
            source=data["source"],
            asserter_id=data["asserter_id"],
            asserter_type=data["asserter_type"],
            assertion_kind=data["assertion_kind"],
            value=data["value"],
            observed_at=data["observed_at"],
            license_basis=data["license_basis"],
            retrieval_evidence_ref=data.get("retrieval_evidence_ref"),
            supersedes_attribution_id=data.get("supersedes_attribution_id"),
        )


@dataclass(frozen=True)
class AttributionRollup:
    """Monotone best/weakest reduction of every record sharing one ``(asserter_id, assertion_kind)`` key.

    ``best_value``/``weakest_value`` are computed with Python's built-in
    ``max()``/``min()`` over the group's raw ``value``s -- and nothing else.
    There is no numeric-averaging code path anywhere in this module; if the
    group's values are not mutually comparable (``TypeError``, e.g. a mix of
    numbers and structured objects for the same key), ``comparable`` is
    ``False`` and both best/weakest fields are left ``None`` rather than
    guessing at an ordering.
    """

    asserter_id: str
    assertion_kind: str
    attribution_ids: tuple[str, ...]
    best_attribution_id: str | None
    best_value: Any
    weakest_attribution_id: str | None
    weakest_value: Any
    comparable: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "asserter_id": self.asserter_id,
            "assertion_kind": self.assertion_kind,
            "attribution_ids": list(self.attribution_ids),
            "best_attribution_id": self.best_attribution_id,
            "best_value": self.best_value,
            "weakest_attribution_id": self.weakest_attribution_id,
            "weakest_value": self.weakest_value,
            "comparable": self.comparable,
        }


@dataclass(frozen=True)
class AttributionTriageResult:
    """Structured, mirror-ready outcome of triaging one caller-supplied record set.

    ``triage_failure`` (``reason``/``detail``/``attempted_at``) mirrors
    ``rights_triage.py``'s ``rights_triage_failure`` convention: it
    disambiguates "triage ran and found nothing" (``triage_failure is None``,
    ``count == 0``) from "triage itself blew up" (``triage_failure`` set).
    """

    source: str
    attribution_ids: tuple[str, ...]
    count: int
    rollups: tuple[AttributionRollup, ...] = field(default_factory=tuple)
    triage_failure: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "attribution_ids": list(self.attribution_ids),
            "count": self.count,
            "rollups": [r.as_dict() for r in self.rollups],
            "triage_failure": self.triage_failure,
        }


def _date_compact_from_observed_at(observed_at: str) -> str:
    """Lift an 8-digit ``YYYYMMDD`` prefix from an already-injected ISO-8601 string.

    Pure string slicing -- never parses or reads a clock. Falls back to a
    fixed placeholder on unexpected input rather than raising, so a
    malformed-but-present ``observed_at`` degrades id minting instead of
    aborting it.
    """

    prefix = (observed_at or "")[:10].replace("-", "")
    return prefix if len(prefix) == 8 and prefix.isdigit() else "00000000"


def _mint_attribution_id(*, source: str, asserter_id: str, assertion_kind: str, observed_at: str) -> str:
    """Content-derived id: deterministic for identical inputs, no wall-clock read."""

    date_compact = _date_compact_from_observed_at(observed_at)
    digest = short_hash(source, asserter_id, assertion_kind, observed_at)
    return f"attrib_{date_compact}_{slugify(source)}_{digest}"


def mint_attribution_record(
    *,
    source: str,
    asserter_id: str,
    asserter_type: str,
    assertion_kind: str,
    value: Any,
    observed_at: str,
    license_basis: str,
    retrieval_evidence_ref: str | None = None,
    supersedes_attribution_id: str | None = None,
) -> AttributionRecord:
    """Mint one brand-new, schema-shaped ``source_attribution`` record.

    ``observed_at`` is a required, injected ISO-8601 timestamp -- obtained by
    the caller however it likes at its own write call site (e.g. the ids
    module's ISO-timestamp helper, per ``ids.py:41``). This function itself
    never reads a wall clock.
    """

    attribution_id = _mint_attribution_id(
        source=source,
        asserter_id=asserter_id,
        assertion_kind=assertion_kind,
        observed_at=observed_at,
    )
    return AttributionRecord(
        schema_version=SCHEMA_VERSION,
        attribution_id=attribution_id,
        source=source,
        asserter_id=asserter_id,
        asserter_type=asserter_type,
        assertion_kind=assertion_kind,
        value=value,
        observed_at=observed_at,
        license_basis=license_basis,
        retrieval_evidence_ref=retrieval_evidence_ref,
        supersedes_attribution_id=supersedes_attribution_id,
    )


def refresh_attribution_record(
    previous: AttributionRecord,
    *,
    value: Any,
    observed_at: str,
    license_basis: str | None = None,
    retrieval_evidence_ref: str | None = None,
) -> AttributionRecord:
    """Mint the NEXT record in a refresh chain. Never mutates ``previous``.

    Structurally enforced, not merely discouraged: ``previous`` is a frozen
    dataclass (no attribute-assignment path exists on it), and this function
    only ever returns a new :class:`AttributionRecord` built by
    :func:`mint_attribution_record` with
    ``supersedes_attribution_id=previous.attribution_id``. There is no
    function in this module's public surface that accepts a record and
    writes back into it -- refreshing is always "mint a new one that points
    backward," never "patch this one."
    """

    return mint_attribution_record(
        source=previous.source,
        asserter_id=previous.asserter_id,
        asserter_type=previous.asserter_type,
        assertion_kind=previous.assertion_kind,
        value=value,
        observed_at=observed_at,
        license_basis=license_basis if license_basis is not None else previous.license_basis,
        retrieval_evidence_ref=(
            retrieval_evidence_ref if retrieval_evidence_ref is not None else previous.retrieval_evidence_ref
        ),
        supersedes_attribution_id=previous.attribution_id,
    )


def load_attribution_records(paths: Iterable[Path | str]) -> list[AttributionRecord]:
    """Load ``source_attribution`` YAML files into :class:`AttributionRecord` instances.

    One record per file, per this module's stated file convention. Raises
    (does not degrade) on a missing file or a record missing required
    fields -- this is the raise-y worker; :func:`compute_source_attribution_triage`
    is the layer that catches and degrades.
    """

    records: list[AttributionRecord] = []
    for p in paths:
        path = Path(p)
        loaded = load_yaml(path)
        if not isinstance(loaded, dict):
            raise ValueError(f"{path}: expected a YAML mapping, got {type(loaded).__name__}")
        records.append(AttributionRecord.from_dict(loaded))
    return records


def _compute_rollup(
    asserter_id: str,
    assertion_kind: str,
    group: Sequence[AttributionRecord],
) -> AttributionRollup:
    attribution_ids = tuple(sorted(r.attribution_id for r in group))
    best_id: str | None = None
    best_value: Any = None
    weakest_id: str | None = None
    weakest_value: Any = None
    comparable = True
    try:
        best_record = max(group, key=lambda r: r.value)
        weakest_record = min(group, key=lambda r: r.value)
        best_id, best_value = best_record.attribution_id, best_record.value
        weakest_id, weakest_value = weakest_record.attribution_id, weakest_record.value
    except TypeError:
        comparable = False
    return AttributionRollup(
        asserter_id=asserter_id,
        assertion_kind=assertion_kind,
        attribution_ids=attribution_ids,
        best_attribution_id=best_id,
        best_value=best_value,
        weakest_attribution_id=weakest_id,
        weakest_value=weakest_value,
        comparable=comparable,
    )


def triage_records(source: str, records: Iterable[AttributionRecord]) -> AttributionTriageResult:
    """Pure reduction of an already-loaded record set into the mirror-ready result.

    This is the worker :func:`compute_source_attribution_triage` wraps and can
    degrade around -- it is free to raise (e.g. on a truly malformed input
    iterable) without itself worrying about failure bookkeeping.
    """

    records = tuple(records)
    groups: dict[tuple[str, str], list[AttributionRecord]] = {}
    for r in records:
        groups.setdefault((r.asserter_id, r.assertion_kind), []).append(r)

    rollups = tuple(
        _compute_rollup(asserter_id, assertion_kind, group)
        for (asserter_id, assertion_kind), group in sorted(groups.items())
    )
    attribution_ids = tuple(sorted(r.attribution_id for r in records))

    return AttributionTriageResult(
        source=source,
        attribution_ids=attribution_ids,
        count=len(records),
        rollups=rollups,
        triage_failure=None,
    )


def compute_source_attribution_triage(
    source: str,
    paths: Iterable[Path | str],
    *,
    attempted_at: str | None = None,
) -> AttributionTriageResult:
    """Never-raises entrypoint -- mirrors ``rights_triage.py``'s public wrapper.

    Loads and reduces the ``source_attribution`` files at ``paths`` for
    ``source``. Any exception from loading or reduction degrades to an empty
    result carrying a ``triage_failure`` record
    (``reason``/``detail``/``attempted_at``) rather than propagating --
    triage must never abort a caller that just wants the current rollup
    state. ``attempted_at`` is an optional, injected ISO-8601 timestamp for
    that failure record; this function never reads a wall clock to produce
    one itself, so a caller that omits it simply gets ``attempted_at: None``
    on failure rather than a synthesized timestamp.
    """

    try:
        records = load_attribution_records(paths)
        return triage_records(source, records)
    except Exception as exc:  # noqa: BLE001 -- a triage failure must never abort the caller
        return AttributionTriageResult(
            source=source,
            attribution_ids=(),
            count=0,
            rollups=(),
            triage_failure={
                "reason": "triage_error",
                "detail": f"{type(exc).__name__}: {exc}",
                "attempted_at": attempted_at,
            },
        )
