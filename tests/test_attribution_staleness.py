"""Append-only-invariant tests for ``services/attribution_triage.py``.

source-metadata-propagation-v1, M2 / SMP-2.8. Proves the plan's named risk
("Staleness reads as currency") directly: *"Refresh must create a new
record; in-place overwrite is forbidden -- so a bad value is superseded,
never corrected. This needs a test, not just a convention."*

Each assertion below is written so it FAILS if the invariant were violated
-- confirmed by temporarily breaking ``refresh_attribution_record`` (see the
task report for exactly what was broken, the RED output observed, and the
restore) rather than merely asserted to be so.

This module does not modify ``attribution_triage.py`` or
``test_attribution_triage.py`` -- it is a separate, additive test file per
this task's scope.
"""

from __future__ import annotations

from pathlib import Path

from research_foundry.services.attribution_triage import (
    load_attribution_records,
    mint_attribution_record,
    refresh_attribution_record,
)
from research_foundry.yamlio import dumps_yaml


def _mint(**overrides):
    defaults = dict(
        source="src_20260802_example_abc123",
        asserter_id="semantic_scholar",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=42,
        observed_at="2026-08-02T10:00:00+00:00",
        license_basis="open_api",
    )
    defaults.update(overrides)
    return mint_attribution_record(**defaults)


def test_refresh_creates_a_new_record_not_a_mutation():
    """A refresh must return a distinct object with a new id and timestamp."""

    original = _mint()
    refreshed = refresh_attribution_record(
        original,
        value=99,
        observed_at="2026-08-03T10:00:00+00:00",
    )

    assert refreshed is not original
    assert refreshed.attribution_id != original.attribution_id
    assert refreshed.observed_at != original.observed_at
    assert refreshed.observed_at == "2026-08-03T10:00:00+00:00"
    assert refreshed.value == 99


def test_prior_record_left_completely_unmodified_after_refresh():
    """Compare the PRIOR record's full serialized state before/after -- not one field."""

    original = _mint()
    before = original.as_dict()

    refresh_attribution_record(original, value=99, observed_at="2026-08-03T10:00:00+00:00")

    after = original.as_dict()
    assert after == before
    # Independent field checks too, in case as_dict() itself were the thing broken.
    assert original.value == 42
    assert original.observed_at == "2026-08-02T10:00:00+00:00"
    assert original.attribution_id == before["attribution_id"]


def test_supersession_points_backward_only():
    """The new record points back at the prior one; the prior points at nothing forward."""

    original = _mint()
    refreshed = refresh_attribution_record(original, value=99, observed_at="2026-08-03T10:00:00+00:00")

    assert refreshed.supersedes_attribution_id == original.attribution_id
    assert original.supersedes_attribution_id is None
    # No field on the prior record references the new record's id (nothing points forward).
    assert refreshed.attribution_id not in {
        v for k, v in original.as_dict().items() if k != "attribution_id"
    }


def test_refresh_chain_of_three_only_ever_points_backward():
    """A multi-hop chain: each refresh points only at its immediate predecessor."""

    r1 = _mint()
    r2 = refresh_attribution_record(r1, value=50, observed_at="2026-08-03T10:00:00+00:00")
    r3 = refresh_attribution_record(r2, value=60, observed_at="2026-08-04T10:00:00+00:00")

    assert r2.supersedes_attribution_id == r1.attribution_id
    assert r3.supersedes_attribution_id == r2.attribution_id
    assert r1.supersedes_attribution_id is None
    # Refreshing r2 into r3 must not reach back and touch r1 or r2's own fields.
    assert r1.value == 42
    assert r2.value == 50
    assert r1.observed_at == "2026-08-02T10:00:00+00:00"
    assert r2.observed_at == "2026-08-03T10:00:00+00:00"


def test_superseded_record_remains_on_disk_and_unchanged_after_refresh(tmp_path: Path):
    """On-disk behaviour, not just in-memory.

    ``attribution_triage.py`` has no persistence entrypoint -- only
    ``load_attribution_records`` (a reader). This test therefore persists the
    records itself, the way any real caller would per the module's stated
    file convention: ``dumps_yaml(record.as_dict())`` written to
    ``<attribution_id>.yaml``.
    """

    original = _mint()
    original_path = tmp_path / f"{original.attribution_id}.yaml"
    original_path.write_text(dumps_yaml(original.as_dict()), encoding="utf-8")
    original_bytes_before = original_path.read_bytes()

    refreshed = refresh_attribution_record(original, value=99, observed_at="2026-08-03T10:00:00+00:00")
    refreshed_path = tmp_path / f"{refreshed.attribution_id}.yaml"
    refreshed_path.write_text(dumps_yaml(refreshed.as_dict()), encoding="utf-8")

    # The prior record's file still exists, byte-for-byte unchanged.
    assert original_path.exists()
    assert original_path.read_bytes() == original_bytes_before

    # It is still readable -- a superseded record stays readable, never deleted/overwritten.
    [reloaded] = load_attribution_records([original_path])
    assert reloaded.as_dict() == original.as_dict()
    assert reloaded.value == 42

    # The refresh landed in a genuinely separate file.
    assert original_path != refreshed_path
    assert refreshed_path.exists()
    assert refreshed_path.read_bytes() != original_bytes_before


def test_staleness_detectable_from_supersession_chain_alone_no_wall_clock():
    """Staleness is derivable from the chain alone, with no wall-clock read.

    Every timestamp here is an explicit literal passed by the caller -- the
    ``as_of`` idiom (``rights_validation.py:128``) -- never
    ``now_iso()``/``datetime.now()`` (the pattern this module's docstring
    explicitly disavows, per ``ids.py:41``). The "current vs stale" split
    below is computed purely from ``supersedes_attribution_id`` pointers.
    """

    r1 = _mint(observed_at="2026-08-01T10:00:00+00:00")
    r2 = refresh_attribution_record(r1, value=50, observed_at="2026-08-02T10:00:00+00:00")
    r3 = refresh_attribution_record(r2, value=60, observed_at="2026-08-03T10:00:00+00:00")

    records = [r1, r2, r3]
    superseded_ids = {
        r.supersedes_attribution_id for r in records if r.supersedes_attribution_id is not None
    }
    current = [r for r in records if r.attribution_id not in superseded_ids]
    stale = [r for r in records if r.attribution_id in superseded_ids]

    assert [r.attribution_id for r in current] == [r3.attribution_id]
    assert {r.attribution_id for r in stale} == {r1.attribution_id, r2.attribution_id}
