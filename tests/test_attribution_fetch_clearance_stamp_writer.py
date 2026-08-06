"""Tests for ``services/attribution_fetch.stamp_source_card`` — the production
caller that persists a fetch-time clearance taint onto a source card.

The writer's whole reason to exist is that ``clearance.mediate_egress`` treats
an ABSENT stamp on a governed record as blocked: a card fetched under the
dev/test posture but never stamped is refused outward rather than leaked, so the
stamp has to reach disk. These tests therefore assert three properties that a
"just write the dict" implementation would not have:

* the block written is the one ``stamp_taint`` produced at fetch time — not a
  re-derivation (nothing here consults gate state or rebuilds a taint);
* every merge against an existing stamp is monotone/widen-only — union of
  scopes, ``dev_test`` never downgraded to ``none``, empty set refused,
  ``CLEARED_*``/``counsel_approved``/``attested`` never constructible
  (``docs/dev/architecture/adr-rights-entity-model.md`` Invariant 1 and
  ``services/governance.py`` rule 9 ``no_agent_cleared_clearance_taint``);
* every refusal happens BEFORE any byte is written, and the write itself is
  atomic — a card is either fully stamped or byte-identical to what it was,
  never carrying half-rewritten frontmatter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.errors import SchemaError
from research_foundry.frontmatter import load_md
from research_foundry.services.attribution_fetch import (
    FETCHED_STATUS,
    ClearedProviderFetchResult,
    ProviderFetchResult,
    stamp_dev_test_fetch,
    stamp_source_card,
)
from research_foundry.services.clearance import (
    BLOCKED_SCOPES_KEY,
    TAINT_KEY,
    ClearanceConfigError,
)

CARD_BODY = "## Passage\n\nSome extracted passage text.\n"


def _write_card(path: Path, meta: dict[str, Any] | None = None, body: str = CARD_BODY) -> Path:
    """Write a minimal source-card-shaped Markdown file (frontmatter + body)."""

    from research_foundry.frontmatter import dump_md

    base: dict[str, Any] = {
        "source_card_id": "src_test_0001",
        "title": "A Test Source",
        "locator": "https://example.org/a",
    }
    base.update(meta or {})
    return dump_md(base, body, path)


def _result(
    *,
    provider: str = "openalex",
    clearance: dict[str, Any] | None = None,
) -> ClearedProviderFetchResult:
    """Build a result carrying a REAL ``stamp_taint`` block unless overridden."""

    return ClearedProviderFetchResult(
        provider=provider,
        status=FETCHED_STATUS,
        value={"id": "W1", "title": "A Test Source"},
        clearance=clearance if clearance is not None else stamp_dev_test_fetch(provider=provider),
    )


# --- fresh card gains the block -------------------------------------------


def test_fresh_card_gains_the_clearance_block(tmp_path: Path) -> None:
    card = _write_card(tmp_path / "card.md")
    result = _result()

    stamp_source_card(card, result)

    meta, body = load_md(card)
    assert meta[TAINT_KEY] == result.clearance
    # The stamp is the fetch-time one verbatim, not a re-derivation.
    assert meta[TAINT_KEY]["stamped_by"] == "attribution_fetch.openalex"
    assert meta[TAINT_KEY][BLOCKED_SCOPES_KEY] == ["redistribution"]
    assert meta[TAINT_KEY]["posture_at_stamp"] == "dev_test"
    # Everything else round-trips untouched.
    assert meta["source_card_id"] == "src_test_0001"
    assert meta["locator"] == "https://example.org/a"
    assert body.strip() == CARD_BODY.strip()


def test_success_leaves_no_temp_file_behind(tmp_path: Path) -> None:
    card = _write_card(tmp_path / "card.md")

    stamp_source_card(card, _result())

    assert sorted(p.name for p in tmp_path.iterdir()) == ["card.md"]


# --- merge is monotone / widen-only ---------------------------------------


def test_pre_existing_narrower_stamp_only_widens(tmp_path: Path) -> None:
    """A scope already on the card survives; the incoming scope is added."""

    card = _write_card(
        tmp_path / "card.md",
        {
            TAINT_KEY: {
                "schema_version": "1.0",
                BLOCKED_SCOPES_KEY: ["acquisition"],
                "stamped_at": "2026-01-01T00:00:00-05:00",
                "stamped_by": "operator.hand_edit",
                "posture_at_stamp": "dev_test",
                "gate_refs": ["DEF-9"],
                "note": "operator annotation worth keeping",
            }
        },
    )

    stamp_source_card(card, _result())

    block = load_md(card)[0][TAINT_KEY]
    assert block[BLOCKED_SCOPES_KEY] == ["acquisition", "redistribution"]
    # gate_refs union — advisory provenance, never narrowed.
    assert block["gate_refs"] == ["DEF-1", "DEF-9"]
    # An existing operator annotation is preserved, not dropped.
    assert block["note"] == "operator annotation worth keeping"
    # Provenance for THIS acquisition wins (carries no authority per schema).
    assert block["stamped_by"] == "attribution_fetch.openalex"


def test_existing_dev_test_posture_is_never_downgraded_to_none(tmp_path: Path) -> None:
    """Restamping a dev/test-acquired card as ``none`` is the retroactive
    release ``governance.py`` rule 9 refuses — the writer keeps ``dev_test``."""

    card = _write_card(
        tmp_path / "card.md",
        {
            TAINT_KEY: {
                "schema_version": "1.0",
                BLOCKED_SCOPES_KEY: ["redistribution"],
                "stamped_at": "2026-01-01T00:00:00-05:00",
                "stamped_by": "attribution_fetch.openalex",
                "posture_at_stamp": "dev_test",
                "gate_refs": [],
            }
        },
    )
    incoming = dict(stamp_dev_test_fetch(provider="crossref"))
    incoming["posture_at_stamp"] = "none"

    stamp_source_card(card, _result(provider="crossref", clearance=incoming))

    assert load_md(card)[0][TAINT_KEY]["posture_at_stamp"] == "dev_test"


def test_repeated_stamp_is_idempotent_on_scopes(tmp_path: Path) -> None:
    card = _write_card(tmp_path / "card.md")

    stamp_source_card(card, _result())
    stamp_source_card(card, _result())

    assert load_md(card)[0][TAINT_KEY][BLOCKED_SCOPES_KEY] == ["redistribution"]


def test_empty_incoming_scope_set_is_refused_without_writing(tmp_path: Path) -> None:
    """The empty set is a release assertion, which only a human may make."""

    card = _write_card(tmp_path / "card.md")
    before = card.read_bytes()
    released = dict(stamp_dev_test_fetch(provider="openalex"))
    released[BLOCKED_SCOPES_KEY] = []

    with pytest.raises(ClearanceConfigError, match="EMPTY"):
        stamp_source_card(card, _result(clearance=released))

    assert card.read_bytes() == before
    assert TAINT_KEY not in load_md(card)[0]


@pytest.mark.parametrize("forged", ["CLEARED_ALL", "counsel_approved", "attested"])
def test_human_only_rights_values_are_refused(tmp_path: Path, forged: str) -> None:
    """ADR Invariant 1: no agent-reachable path constructs one of these."""

    card = _write_card(tmp_path / "card.md")
    before = card.read_bytes()
    laundered = dict(stamp_dev_test_fetch(provider="openalex"))
    laundered[BLOCKED_SCOPES_KEY] = ["redistribution", forged]

    with pytest.raises(ClearanceConfigError, match="human-only"):
        stamp_source_card(card, _result(clearance=laundered))

    assert card.read_bytes() == before


def test_unknown_scope_is_refused(tmp_path: Path) -> None:
    card = _write_card(tmp_path / "card.md")
    bogus = dict(stamp_dev_test_fetch(provider="openalex"))
    bogus[BLOCKED_SCOPES_KEY] = ["redistribution", "everything"]

    with pytest.raises(ClearanceConfigError, match="unknown scope"):
        stamp_source_card(card, _result(clearance=bogus))


def test_existing_scope_survives_even_when_incoming_omits_it(tmp_path: Path) -> None:
    """Union, not overwrite: the writer cannot narrow what the card carried."""

    card = _write_card(
        tmp_path / "card.md",
        {
            TAINT_KEY: {
                "schema_version": "1.0",
                BLOCKED_SCOPES_KEY: ["acquisition", "clinical_reliance", "redistribution"],
                "stamped_at": "2026-01-01T00:00:00-05:00",
                "stamped_by": "operator.hand_edit",
                "posture_at_stamp": "dev_test",
                "gate_refs": [],
            }
        },
    )

    stamp_source_card(card, _result())

    assert load_md(card)[0][TAINT_KEY][BLOCKED_SCOPES_KEY] == [
        "acquisition",
        "clinical_reliance",
        "redistribution",
    ]


# --- malformed targets raise BEFORE any write ------------------------------


def test_card_without_frontmatter_raises_before_writing(tmp_path: Path) -> None:
    card = tmp_path / "card.md"
    card.write_text("just a body, no frontmatter\n", encoding="utf-8")
    before = card.read_bytes()

    with pytest.raises(SchemaError, match="no YAML frontmatter"):
        stamp_source_card(card, _result())

    assert card.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["card.md"]


def test_non_mapping_clearance_key_raises_before_writing(tmp_path: Path) -> None:
    card = _write_card(tmp_path / "card.md", {TAINT_KEY: "cleared"})
    before = card.read_bytes()

    with pytest.raises(SchemaError, match="not a mapping"):
        stamp_source_card(card, _result())

    assert card.read_bytes() == before


def test_unreadable_existing_blocked_scopes_raises_before_writing(tmp_path: Path) -> None:
    """A malformed existing list is refused rather than read as the empty set —
    reading it as empty would let a later stamp silently drop a human's scope."""

    card = _write_card(
        tmp_path / "card.md",
        {
            TAINT_KEY: {
                "schema_version": "1.0",
                BLOCKED_SCOPES_KEY: "redistribution",  # a string, not a list
                "stamped_at": "2026-01-01T00:00:00-05:00",
                "stamped_by": "operator.hand_edit",
                "posture_at_stamp": "dev_test",
                "gate_refs": [],
            }
        },
    )
    before = card.read_bytes()

    with pytest.raises(SchemaError, match="not a list"):
        stamp_source_card(card, _result())

    assert card.read_bytes() == before


def test_non_string_entry_in_existing_scopes_raises_before_writing(tmp_path: Path) -> None:
    card = _write_card(
        tmp_path / "card.md",
        {
            TAINT_KEY: {
                "schema_version": "1.0",
                BLOCKED_SCOPES_KEY: ["redistribution", 7],
                "stamped_at": "2026-01-01T00:00:00-05:00",
                "stamped_by": "operator.hand_edit",
                "posture_at_stamp": "dev_test",
                "gate_refs": [],
            }
        },
    )
    before = card.read_bytes()

    with pytest.raises(SchemaError, match="non-string entry"):
        stamp_source_card(card, _result())

    assert card.read_bytes() == before


def test_schema_invalid_block_raises_before_writing(tmp_path: Path) -> None:
    """Validation is a pre-write gate, not a post-write audit."""

    card = _write_card(tmp_path / "card.md")
    before = card.read_bytes()
    bad = dict(stamp_dev_test_fetch(provider="openalex"))
    bad["schema_version"] = "9.9"  # schema pins const "1.0"

    with pytest.raises(SchemaError, match="clearance_taint validation failed"):
        stamp_source_card(card, _result(clearance=bad))

    assert card.read_bytes() == before
    assert TAINT_KEY not in load_md(card)[0]


def test_missing_card_raises_before_creating_anything(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        stamp_source_card(tmp_path / "absent.md", _result())

    assert list(tmp_path.iterdir()) == []


def test_unavailable_schema_fails_closed(tmp_path: Path) -> None:
    """An unlocatable schema refuses the write rather than skipping validation
    (unlike ``source_cards._validate``, whose skip would here mean writing an
    unvalidated governance stamp)."""

    card = _write_card(tmp_path / "card.md")
    before = card.read_bytes()
    empty_schemas = tmp_path / "no_schemas"
    empty_schemas.mkdir()

    import research_foundry.services.attribution_fetch as af

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(af, "distribution_root", lambda: empty_schemas)
        with pytest.raises(SchemaError, match="unavailable"):
            stamp_source_card(card, _result())

    assert card.read_bytes() == before


# --- input type discipline -------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        {"provider": "openalex", "clearance": {"blocked_scopes": ["redistribution"]}},
        ProviderFetchResult(provider="openalex", status="disabled", reason="off"),
        None,
    ],
)
def test_non_cleared_result_is_refused(tmp_path: Path, bad: Any) -> None:
    """Only a ``ClearedProviderFetchResult`` is accepted, so the only stamp this
    writer can persist is one ``stamp_taint`` already produced at fetch time."""

    card = _write_card(tmp_path / "card.md")
    before = card.read_bytes()

    with pytest.raises(TypeError, match="ClearedProviderFetchResult"):
        stamp_source_card(card, bad)

    assert card.read_bytes() == before


# --- atomicity -------------------------------------------------------------


def test_failure_mid_write_leaves_the_card_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Temp-file + ``os.replace``: a crash in the writer never leaves partial
    frontmatter on the real card, and no temp file survives."""

    card = _write_card(tmp_path / "card.md")
    before = card.read_bytes()

    import research_foundry.services.attribution_fetch as af

    def _boom(metadata: Any, body: Any, path: Any) -> Any:
        Path(path).write_text("---\npartial: true\n", encoding="utf-8")
        raise OSError("disk went away")

    monkeypatch.setattr(af, "dump_md", _boom)

    with pytest.raises(OSError, match="disk went away"):
        stamp_source_card(card, _result())

    assert card.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["card.md"]


def test_replace_failure_leaves_the_card_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = _write_card(tmp_path / "card.md")
    before = card.read_bytes()

    import research_foundry.services.attribution_fetch as af

    def _boom(src: Any, dst: Any) -> None:
        raise OSError("rename failed")

    monkeypatch.setattr(af.os, "replace", _boom)

    with pytest.raises(OSError, match="rename failed"):
        stamp_source_card(card, _result())

    assert card.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["card.md"]
