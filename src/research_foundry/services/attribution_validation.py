"""Attribution-summary divergence validator (source-metadata-propagation-v1, SMP-2.5).

``check_attribution_divergence`` checks the value-free, recompute-only
``attribution_summary`` mirror carried on ``source_card`` instances (see
``schemas/source_card.schema.yaml``) against the authoritative
``source_attribution`` record(s) it claims to be derived from
(``schemas/source_attribution.schema.yaml``), for a caller-supplied point in
time. Deliberately mirrors ``services/rights_validation.py``'s architecture
(``check_rights_divergence``) rather than inventing a parallel one -- same
dataclass shape (frozen, ``.as_dict()``), same records-cache approach, same
never-raises-at-the-public-boundary posture, same required-``as_of``/
no-wall-clock governance invariant.

Governance-critical invariant
------------------------------
This module (and everything it calls) MUST NEVER read the wall clock. There is
no default for "now" -- the caller must supply ``as_of`` explicitly. This is
enforced by construction: the only time-related stdlib calls anywhere in this
module are ``datetime.fromisoformat`` / ``date.fromisoformat``, which *parse*
an already-supplied value rather than *reading* the current time. Do not add
a wall-clock read -- ``datetime``'s "current moment" constructor, the ``time``
module's epoch-seconds getter, ``date``'s "today" constructor, or the
repository's own injected-ISO-timestamp write-path helper (``ids.py:41``) --
to this module, and do not give ``as_of`` a default value -- a test in
``tests/test_attribution_divergence.py`` monkeypatches ``date``/``datetime``
and blocks the ``time`` module's epoch-seconds getter, asserting this
function completes without triggering any of them.

File conventions
------------------
- ``source_card``/``source_assertion`` instances load exactly as in
  ``rights_validation.py``: ``.md`` front matter via
  ``research_foundry.frontmatter.load_md``, plain ``.yaml`` via
  ``research_foundry.yamlio.load_yaml``. Only ``source_card`` currently
  declares ``attribution_summary`` in its schema, but the loader stays
  generic over both instance kinds for the same reason the anchor's does.
- ``source_attribution`` instances are plain YAML files named
  ``<attribution_id>.yaml`` inside a caller-supplied
  ``attribution_records_dir`` -- established explicitly here (mirroring
  ``rights_validation.py``'s stated ``<rights_record_id>.yaml`` convention;
  ``attribution_triage.py``'s own docstring already anticipated this exact
  naming for "whatever directory it manages").

Recompute, not field-compare
------------------------------
Unlike ``rights_summary`` (whose mirror fields carry real values compared
field-by-field against the authoritative record), ``attribution_summary`` is
schema-enforced value-free -- it carries only ids/counts/pointers, never a
raw asserted value (see the schema's own ``additionalProperties: false``
comment). Divergence is therefore detected by *recomputing* the expected
mirror from the authoritative ``source_attribution`` records that name this
card as their ``source`` (via ``attribution_triage.triage_records`` --
reused, not reimplemented, so the recompute uses the exact same monotone
best=max()/weakest=min() reduction the mirror-writer used; there is no
averaging path here either) and diffing the recomputed shape against what is
actually on the card:

1. **Missing**: an authoritative record whose ``source`` names this card,
   but whose ``attribution_id`` is absent from the mirror's ``attribution_ids``.
2. **Extra / unlinked**: a mirror ``attribution_ids`` entry with no
   authoritative record for this card backing it (the id does not resolve
   under ``attribution_records_dir`` at all, or resolves to a record whose
   ``source`` names a *different* card).
3. **Wrong counts**: the mirror's top-level ``count`` (or a rollup's
   ``count``) disagreeing with ``len(attribution_ids)`` -- checked as a pure
   self-consistency property, needing no directory at all.
4. **Wrong monotone rollup pointers**: a mirror rollup's
   ``best_attribution_id``/``weakest_attribution_id``/``comparable``/
   ``attribution_ids``/``count`` disagreeing with the recomputed rollup for
   the same ``(asserter_id, assertion_kind)`` key, or a rollup key present in
   one side and absent from the other.

``stale`` (non-blocking, mirrors the anchor's scenario-4 pattern) fires when
a mirrored ``attribution_id`` has since been superseded (append-only refresh
chain -- ``source_attribution.schema.yaml``'s ``supersedes_attribution_id``)
by a record observed on or before ``as_of``. This is the one place ``as_of``
does real work: it gates supersession-staleness exactly as the anchor gates
``next_review_at`` staleness, using the one time-shaped field this schema
actually has (``observed_at``) rather than inventing a review-schedule field
that does not exist in this domain.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from ..frontmatter import load_md
from ..yamlio import load_yaml
from .attribution_triage import AttributionRecord, AttributionRollup, triage_records

__all__ = [
    "DivergenceFinding",
    "AttributionCheckResult",
    "check_attribution_divergence",
]

# Reasons a finding was raised.
REASON_UNLINKED = "unlinked_or_foreign_attribution_id"
REASON_MISSING = "missing_from_mirror"
REASON_MISMATCH = "value_mismatch"


@dataclass(frozen=True)
class DivergenceFinding:
    """One thing wrong with an ``attribution_summary`` mirror, at the data level."""

    field: str
    mirror_value: Any
    authoritative_value: Any
    reason: str


@dataclass(frozen=True)
class AttributionCheckResult:
    """Outcome of checking one ``source_card``/``source_assertion`` instance.

    ``needs_backfill`` (``attribution_summary`` entirely absent -- a legacy
    instance pre-dating this phase, or one for which no ``source_attribution``
    records exist yet) is distinct from, and never conflated with, a
    divergence failure: it is non-fatal by design, mirroring
    ``RightsCheckResult``. ``stale`` flags a mirrored ``attribution_id`` that
    has since been superseded (as of ``as_of``) -- also non-blocking, a
    record-the-debt surface only.
    """

    path: str
    instance_id: str | None
    needs_backfill: bool
    stale: bool
    findings: tuple[DivergenceFinding, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True when no divergence findings were raised (backfill/staleness aside)."""

        return not self.findings

    def as_dict(self) -> dict[str, Any]:
        """JSON-safe representation (CLI output; reproducibility tests)."""

        return asdict(self)


def check_attribution_divergence(
    paths: Iterable[Path | str],
    *,
    as_of: date | datetime | str,
    attribution_records_dir: Path | str | None = None,
) -> list[AttributionCheckResult]:
    """Check ``attribution_summary`` mirrors on ``paths`` as of ``as_of``.

    Args:
        paths: ``source_card``/``source_assertion`` instance files to check
            (``.md`` front matter or plain ``.yaml``, auto-detected).
        as_of: The point in time to evaluate supersession-staleness against.
            Required, keyword-only, no default -- see the governance
            invariant in the module docstring. Accepts a ``date``,
            ``datetime``, or ISO-8601 string; never the wall clock.
        attribution_records_dir: Directory containing ``<attribution_id>.yaml``
            authoritative ``source_attribution`` records. When omitted, this
            function can still detect legacy absence (``needs_backfill``) and
            the mirror's own internal self-consistency (count vs.
            ``len(attribution_ids)``, rollup ids being a subset of the
            top-level set), but cannot detect missing/extra/unlinked ids,
            recompute rollup pointers, or detect staleness -- it degrades to
            structural-only checking rather than guessing at a directory
            layout, exactly as the anchor degrades without
            ``rights_records_dir``.

    Returns:
        One :class:`AttributionCheckResult` per input path, in input order.
    """

    as_of_date = _coerce_as_of(as_of)
    records_dir = Path(attribution_records_dir) if attribution_records_dir is not None else None
    have_records_dir = records_dir is not None
    by_source, superseded_by = _index_records(records_dir)

    return [
        _check_one(
            Path(p),
            as_of=as_of_date,
            by_source=by_source,
            superseded_by=superseded_by,
            have_records_dir=have_records_dir,
        )
        for p in paths
    ]


def _coerce_as_of(value: date | datetime | str) -> date:
    """Parse ``value`` into a ``date``. Never reads the wall clock."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return datetime.fromisoformat(text).date()
    raise TypeError(f"as_of must be a date, datetime, or ISO-8601 string, got {type(value)!r}")


def _load_instance(path: Path) -> dict[str, Any]:
    """Load a source_card (.md front matter) or source_assertion (.yaml) instance."""

    if path.suffix.lower() == ".md":
        metadata, _body = load_md(path)
        return metadata
    return load_yaml(path) or {}


def _parse_observed_at(value: str) -> date:
    """Parse an ISO-8601 date/datetime string from a loaded record. No wall clock."""

    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return date.fromisoformat(text[:10])


def _index_records(
    records_dir: Path | None,
) -> tuple[dict[str, list[AttributionRecord]], dict[str, AttributionRecord]]:
    """Build the two lookup indices once per call, from a single directory scan.

    A one-shot full-directory index (rather than the anchor's lazy per-id
    file-existence lookup) because this validator's stated divergence
    surface -- "missing/extra attribution_ids" -- requires knowing every
    authoritative record for a given ``source`` up front, not just resolving
    ids the mirror already names. Malformed or unreadable record files are
    skipped rather than raising: a corrupt sibling record must never abort
    validation of every other instance in the batch (same never-raises
    posture as the public entrypoint, applied one layer down).

    Returns:
        ``(by_source, superseded_by)`` -- ``by_source`` maps a card's
        ``source_card_id`` to every record naming it as ``source``;
        ``superseded_by`` maps an old ``attribution_id`` to the newest
        record whose ``supersedes_attribution_id`` points back at it (by
        ``observed_at``), the input to the staleness check.
    """

    by_source: dict[str, list[AttributionRecord]] = {}
    superseded_by: dict[str, AttributionRecord] = {}

    if records_dir is None or not records_dir.exists():
        return by_source, superseded_by

    for candidate in sorted(records_dir.glob("*.yaml")):
        try:
            loaded = load_yaml(candidate)
            if not isinstance(loaded, dict):
                continue
            record = AttributionRecord.from_dict(loaded)
        except Exception:  # noqa: BLE001 -- one bad file must not sink the batch
            continue
        by_source.setdefault(record.source, []).append(record)
        if record.supersedes_attribution_id:
            previous = record.supersedes_attribution_id
            existing = superseded_by.get(previous)
            if existing is None or _observed_at_key(record) > _observed_at_key(existing):
                superseded_by[previous] = record

    return by_source, superseded_by


def _observed_at_key(record: AttributionRecord) -> str:
    """Sortable proxy for ``observed_at`` -- string compare is safe for ISO-8601."""

    return record.observed_at or ""


def _self_consistency_findings(mirror: dict[str, Any]) -> list[DivergenceFinding]:
    """Checks needing no ``attribution_records_dir`` at all -- pure mirror-shape sanity.

    Runs unconditionally (even without a directory supplied), mirroring the
    anchor's "structural-only checking" degrade mode -- scenario 1 there is
    also detectable without the authoritative directory.
    """

    findings: list[DivergenceFinding] = []
    top_ids = list(mirror.get("attribution_ids") or [])
    top_count = mirror.get("count")
    if top_count != len(top_ids):
        findings.append(
            DivergenceFinding(
                field="count",
                mirror_value=top_count,
                authoritative_value=len(top_ids),
                reason=REASON_MISMATCH,
            )
        )

    top_id_set = set(top_ids)
    for rollup in mirror.get("rollups") or []:
        key = f"{rollup.get('asserter_id')}:{rollup.get('assertion_kind')}"
        rollup_ids = list(rollup.get("attribution_ids") or [])
        rollup_count = rollup.get("count")
        if rollup_count != len(rollup_ids):
            findings.append(
                DivergenceFinding(
                    field=f"rollups[{key}].count",
                    mirror_value=rollup_count,
                    authoritative_value=len(rollup_ids),
                    reason=REASON_MISMATCH,
                )
            )
        stray = [rid for rid in rollup_ids if rid not in top_id_set]
        if stray:
            findings.append(
                DivergenceFinding(
                    field=f"rollups[{key}].attribution_ids",
                    mirror_value=stray,
                    authoritative_value=None,
                    reason=REASON_MISMATCH,
                )
            )
    return findings


def _rollup_findings(
    mirror_rollups: list[dict[str, Any]],
    recomputed_rollups: tuple[AttributionRollup, ...],
) -> list[DivergenceFinding]:
    """Diff mirror rollups against ``attribution_triage.triage_records``'s recomputed ones."""

    findings: list[DivergenceFinding] = []
    mirror_by_key: dict[tuple[Any, Any], dict[str, Any]] = {
        (r.get("asserter_id"), r.get("assertion_kind")): r for r in mirror_rollups
    }
    recomputed_by_key: dict[tuple[Any, Any], AttributionRollup] = {
        (r.asserter_id, r.assertion_kind): r for r in recomputed_rollups
    }

    for key, recomputed in recomputed_by_key.items():
        label = f"{key[0]}:{key[1]}"
        mirror_rollup = mirror_by_key.get(key)
        if mirror_rollup is None:
            findings.append(
                DivergenceFinding(
                    field=f"rollups[{label}]",
                    mirror_value=None,
                    authoritative_value=recomputed.as_dict(),
                    reason=REASON_MISSING,
                )
            )
            continue
        for attr in ("best_attribution_id", "weakest_attribution_id", "comparable"):
            mirror_value = mirror_rollup.get(attr)
            authoritative_value = getattr(recomputed, attr)
            if mirror_value != authoritative_value:
                findings.append(
                    DivergenceFinding(
                        field=f"rollups[{label}].{attr}",
                        mirror_value=mirror_value,
                        authoritative_value=authoritative_value,
                        reason=REASON_MISMATCH,
                    )
                )
        mirror_ids = set(mirror_rollup.get("attribution_ids") or [])
        authoritative_ids = set(recomputed.attribution_ids)
        if mirror_ids != authoritative_ids:
            findings.append(
                DivergenceFinding(
                    field=f"rollups[{label}].attribution_ids",
                    mirror_value=sorted(mirror_ids),
                    authoritative_value=sorted(authoritative_ids),
                    reason=REASON_MISMATCH,
                )
            )

    for key in mirror_by_key.keys() - recomputed_by_key.keys():
        label = f"{key[0]}:{key[1]}"
        findings.append(
            DivergenceFinding(
                field=f"rollups[{label}]",
                mirror_value=mirror_by_key[key],
                authoritative_value=None,
                reason=REASON_MISMATCH,
            )
        )
    return findings


def _check_one(
    path: Path,
    *,
    as_of: date,
    by_source: dict[str, list[AttributionRecord]],
    superseded_by: dict[str, AttributionRecord],
    have_records_dir: bool,
) -> AttributionCheckResult:
    metadata = _load_instance(path)
    instance_id = metadata.get("source_card_id") or metadata.get("assertion_id")

    mirror = metadata.get("attribution_summary")
    if mirror is None:
        # Absent entirely on a legacy (pre-backfill) instance. Distinct,
        # non-fatal -- never conflated with a divergence failure.
        return AttributionCheckResult(
            path=str(path),
            instance_id=instance_id,
            needs_backfill=True,
            stale=False,
            findings=(),
        )

    findings: list[DivergenceFinding] = _self_consistency_findings(mirror)
    mirror_ids: set[str] = set(mirror.get("attribution_ids") or [])

    # Missing/extra/rollup-pointer divergence all require knowing the full
    # authoritative record set -- not resolvable without a directory at all
    # (an empty `authoritative_ids` in that case would otherwise misread as
    # "every mirrored id is unlinked"). Degrade to self-consistency-only
    # checking, exactly as the anchor degrades without `rights_records_dir`.
    if have_records_dir:
        authoritative_records = by_source.get(instance_id, []) if instance_id is not None else []
        authoritative_ids = {r.attribution_id for r in authoritative_records}

        # Missing: an authoritative record for this source not named in the mirror.
        for missing_id in sorted(authoritative_ids - mirror_ids):
            findings.append(
                DivergenceFinding(
                    field="attribution_ids",
                    mirror_value=None,
                    authoritative_value=missing_id,
                    reason=REASON_MISSING,
                )
            )

        # Extra/unlinked: a mirrored id with no authoritative record for THIS
        # source backing it -- either it does not resolve at all, or it
        # resolves to a record naming a different card as its `source`.
        for mirror_id in sorted(mirror_ids - authoritative_ids):
            findings.append(
                DivergenceFinding(
                    field="attribution_ids",
                    mirror_value=mirror_id,
                    authoritative_value=None,
                    reason=REASON_UNLINKED,
                )
            )

        recomputed = triage_records(str(instance_id or path), authoritative_records)
        findings.extend(_rollup_findings(list(mirror.get("rollups") or []), recomputed.rollups))

    # Staleness: a mirrored id has since been superseded by a newer record
    # observed on or before `as_of` -- non-blocking, record-the-debt only.
    stale = any(
        mid in superseded_by and _parse_observed_at(superseded_by[mid].observed_at) <= as_of
        for mid in mirror_ids
    )

    return AttributionCheckResult(
        path=str(path),
        instance_id=instance_id,
        needs_backfill=False,
        stale=stale,
        findings=tuple(findings),
    )
