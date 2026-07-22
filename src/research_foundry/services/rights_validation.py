"""Rights-summary divergence validator (rights-entity-model-v1, P2-3).

``check_rights_divergence`` checks the denormalized, non-authoritative
``rights_summary`` mirror carried on ``source_card`` and ``source_assertion``
instances (see ``schemas/source_card.schema.yaml`` /
``schemas/source_assertion.schema.yaml``) against the authoritative
``rights_record`` instance(s) it claims to be derived from
(``schemas/rights_record.schema.yaml``), for a caller-supplied point in time.

Governance-critical invariant
------------------------------
This module (and everything it calls) MUST NEVER read the wall clock. There is
no default for "now" — the caller must supply ``as_of`` explicitly. This is
enforced by construction: the only time-related stdlib calls anywhere in this
module are ``datetime.fromisoformat`` / ``date.fromisoformat``, which *parse*
an already-supplied value rather than *reading* the current time. Do not add
a call to ``datetime.now()``, ``time.time()``, or ``date.today()`` to this
module, and do not give ``as_of`` a default value — a test in
``tests/test_rights_validation.py`` monkeypatches all three to raise and
asserts this function completes without triggering them.

File conventions (established here — no prior Python consumer of
``rights_record`` existed before this task)
--------------------------------------------
- ``source_card`` instances are Markdown files with YAML front matter
  (see ``research_foundry.frontmatter.load_md``), matching
  ``services/source_cards.py``.
- ``source_assertion`` instances are plain YAML files (see
  ``research_foundry.yamlio.load_yaml``), matching
  ``services/assertion_materialization.py``'s ``assertions/<id>.yaml``
  convention.
- ``rights_record`` instances are plain YAML files named
  ``<rights_record_id>.yaml`` inside a caller-supplied ``rights_records_dir``.
  No such directory/registry existed prior to this phase; P2-4/P2-5 should
  reuse this convention rather than inventing another one.

Divergence semantics
---------------------
Only mirror fields whose enum is byte-identical to the authoritative field it
mirrors are compared for value-level divergence: ``copyright_status`` vs.
``copyright.status``, ``access_basis`` vs. ``access.basis``, ``review_status``
vs. ``review.review_status`` (skipped when the mirror is at its ``"unknown"``
sentinel, which the authoritative enum does not have), and
``restrictions.{bulk_retrieval,model_training}`` vs.
``contract.{bulk_retrieval,model_training}`` (the one restriction pair the
schema's own §9.4 adjudication says shares an identical enum with the
mirror's unified restriction enum). The remaining four ``restrictions.*``
mirror fields intentionally compress a *wider* ``rights_record.contract.*``
enum into a narrower one (see the schema's own comment on
``rights_summary.restrictions``) and ``clearance_status`` mirrors a
``rights_extension`` record this module has no loader for yet — both are
deliberately excluded from value-level comparison rather than guessing at an
unverified mapping.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from ..frontmatter import load_md
from ..yamlio import load_yaml

__all__ = [
    "DivergenceFinding",
    "RightsCheckResult",
    "check_rights_divergence",
]

# Reasons a finding was raised.
REASON_UNLINKED = "unlinked_substantive_value"
REASON_MISMATCH = "value_mismatch"

# Mirror field -> (authoritative section, authoritative key) for the fields
# whose enums are byte-identical between rights_summary and rights_record.
_DIRECT_FIELD_MAP: dict[str, tuple[str, str]] = {
    "copyright_status": ("copyright", "status"),
    "access_basis": ("access", "basis"),
    "review_status": ("review", "review_status"),
}
# rights_summary.restrictions.* -> rights_record.contract.* pairs sharing an
# identical enum (§9.4). The other 4 restriction fields are intentionally
# excluded — see module docstring.
_DIRECT_RESTRICTION_FIELDS: tuple[str, ...] = ("bulk_retrieval", "model_training")


@dataclass(frozen=True)
class DivergenceFinding:
    """One thing wrong with a ``rights_summary`` mirror, at the data level."""

    field: str
    mirror_value: Any
    authoritative_value: Any
    reason: str


@dataclass(frozen=True)
class RightsCheckResult:
    """Outcome of checking one ``source_card``/``source_assertion`` instance.

    ``needs_backfill`` (rights_summary entirely absent — a legacy instance
    pre-dating this phase) is distinct from, and never conflated with, a
    divergence failure: it is non-fatal by design. ``stale`` flags a linked
    ``rights_record`` whose ``review.next_review_at`` has passed as of
    ``as_of`` — also non-blocking, a record-the-debt surface only.
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
        """JSON-safe representation (P2-4 CLI output; reproducibility tests)."""

        return asdict(self)


def check_rights_divergence(
    paths: Iterable[Path | str],
    *,
    as_of: date | datetime | str,
    rights_records_dir: Path | str | None = None,
) -> list[RightsCheckResult]:
    """Check ``rights_summary`` mirrors on ``paths`` as of ``as_of``.

    Args:
        paths: ``source_card``/``source_assertion`` instance files to check
            (``.md`` front-matter or plain ``.yaml``, auto-detected).
        as_of: The point in time to evaluate staleness against. Required,
            keyword-only, no default — see the governance invariant in the
            module docstring. Accepts a ``date``, ``datetime``, or ISO-8601
            string; never the wall clock.
        rights_records_dir: Directory containing ``<rights_record_id>.yaml``
            files for the linked authoritative records. When omitted, this
            function can still detect the link-before-assert violation
            (scenario 1) and legacy absence (scenario 3), but cannot compare
            mirror values against an authoritative record (scenario 2) or
            detect staleness (scenario 4) for any instance — it degrades to
            structural-only checking rather than guessing at a directory
            layout.

    Returns:
        One :class:`RightsCheckResult` per input path, in input order.
    """

    as_of_date = _coerce_as_of(as_of)
    records_dir = Path(rights_records_dir) if rights_records_dir is not None else None
    records_cache: dict[str, dict[str, Any] | None] = {}

    return [
        _check_one(Path(p), as_of=as_of_date, rights_records_dir=records_dir, records_cache=records_cache)
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


def _load_rights_record(
    record_id: str,
    rights_records_dir: Path | None,
    cache: dict[str, dict[str, Any] | None],
) -> dict[str, Any] | None:
    """Resolve one ``rights_record_id`` to its instance, memoized per call."""

    if rights_records_dir is None:
        return None
    if record_id in cache:
        return cache[record_id]
    candidate = rights_records_dir / f"{record_id}.yaml"
    record: dict[str, Any] | None = None
    if candidate.exists():
        loaded = load_yaml(candidate)
        record = loaded if isinstance(loaded, dict) else None
    cache[record_id] = record
    return record


def _parse_authoritative_date(value: str) -> date:
    """Parse an ISO-8601 date/datetime string from a loaded record. No wall clock."""

    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return date.fromisoformat(text[:10])


def _substantive_mirror_fields(summary: dict[str, Any]) -> set[str]:
    """Mirror fields set to something other than their "unknown" sentinel.

    Mirrors the schema's own link-before-assert `allOf`/`if` condition
    (source_card.schema.yaml / source_assertion.schema.yaml), checked here
    independently at the data level per the P2-3 task contract — a
    hand-crafted or legacy instance can violate this even if newly-authored
    instances cannot (the schema constraint only binds instances validated
    after it existed).
    """

    fields: set[str] = set()
    if summary.get("copyright_status", "unknown") not in (None, "unknown"):
        fields.add("copyright_status")
    if summary.get("access_basis", "unknown") not in (None, "unknown"):
        fields.add("access_basis")
    if summary.get("clearance_status", "UNKNOWN") not in (None, "UNKNOWN"):
        fields.add("clearance_status")
    if summary.get("review_status", "unknown") not in (None, "unknown"):
        fields.add("review_status")
    restrictions = summary.get("restrictions") or {}
    for key, val in restrictions.items():
        if val not in (None, "unknown"):
            fields.add(f"restrictions.{key}")
    return fields


def _compare_mirror_to_record(summary: dict[str, Any], record: dict[str, Any]) -> list[DivergenceFinding]:
    """Value-level divergence between a mirror and its linked authoritative record.

    Only compares the fields documented in the module docstring as sharing a
    byte-identical enum; see there for why the rest are excluded.
    """

    findings: list[DivergenceFinding] = []

    for mirror_field, (section, key) in _DIRECT_FIELD_MAP.items():
        mirror_value = summary.get(mirror_field, "unknown")
        if mirror_value in (None, "unknown"):
            continue
        authoritative_value = (record.get(section) or {}).get(key)
        if authoritative_value is not None and mirror_value != authoritative_value:
            findings.append(
                DivergenceFinding(
                    field=mirror_field,
                    mirror_value=mirror_value,
                    authoritative_value=authoritative_value,
                    reason=REASON_MISMATCH,
                )
            )

    mirror_restrictions = summary.get("restrictions") or {}
    contract = record.get("contract") or {}
    for key in _DIRECT_RESTRICTION_FIELDS:
        mirror_value = mirror_restrictions.get(key, "unknown")
        if mirror_value in (None, "unknown"):
            continue
        authoritative_value = contract.get(key)
        if authoritative_value is not None and mirror_value != authoritative_value:
            findings.append(
                DivergenceFinding(
                    field=f"restrictions.{key}",
                    mirror_value=mirror_value,
                    authoritative_value=authoritative_value,
                    reason=REASON_MISMATCH,
                )
            )

    return findings


def _check_one(
    path: Path,
    *,
    as_of: date,
    rights_records_dir: Path | None,
    records_cache: dict[str, dict[str, Any] | None],
) -> RightsCheckResult:
    metadata = _load_instance(path)
    instance_id = metadata.get("source_card_id") or metadata.get("assertion_id")

    rights_summary = metadata.get("rights_summary")
    if rights_summary is None:
        # Scenario 3: absent entirely on a legacy (pre-backfill) instance.
        # Distinct, non-fatal — never conflated with a divergence failure.
        return RightsCheckResult(
            path=str(path),
            instance_id=instance_id,
            needs_backfill=True,
            stale=False,
            findings=(),
        )

    findings: list[DivergenceFinding] = []
    record_ids = list(rights_summary.get("rights_record_ids") or [])

    # Scenario 1: substantive mirror value with no linked rights_record_ids.
    substantive_fields = _substantive_mirror_fields(rights_summary)
    if substantive_fields and not record_ids:
        findings.append(
            DivergenceFinding(
                field="rights_record_ids",
                mirror_value=record_ids,
                authoritative_value=None,
                reason=REASON_UNLINKED,
            )
        )

    stale = False
    for record_id in record_ids:
        record = _load_rights_record(record_id, rights_records_dir, records_cache)
        if record is None:
            # Not resolvable (no rights_records_dir, or the id is unknown) —
            # cannot compare values or detect staleness for this link.
            continue

        # Scenario 2: mirror value diverges from the linked record's value.
        findings.extend(_compare_mirror_to_record(rights_summary, record))

        # Scenario 4: linked record's next review date has passed as_of.
        next_review_at = (record.get("review") or {}).get("next_review_at")
        if next_review_at and _parse_authoritative_date(next_review_at) < as_of:
            stale = True

    return RightsCheckResult(
        path=str(path),
        instance_id=instance_id,
        needs_backfill=False,
        stale=stale,
        findings=tuple(findings),
    )
