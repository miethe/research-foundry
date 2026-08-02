"""Unit tests for M4 (SMP-4.2/4.3) catalog attribution/metadata columns.

Covers:
  - SCHEMA_VERSION v5 DDL: the six new `catalog_items` columns
    (`doi`/`publisher`/`source_version`/`authors_json`/`source_rank`/
    `attribution_count`) exist after a schema rebuild.
  - Row-builder wiring of M1's first-party provider metadata
    (authors/doi/publisher/version) end-to-end via `import_run()`.
  - `source_rank` is a DELIBERATELY separate column from the pre-existing
    `trust_label` — a legacy plain-string `trust` value populates
    `trust_label` but leaves `source_rank` null (never treats free text as a
    rank).
  - `attribution_count`'s tri-state hook: NULL ("not yet assessed") vs 0
    ("assessed, none found") vs >0 ("assessed, N found") — exercised
    directly against `_build_source_rows()` since `export_service.py` has
    not yet been widened to surface `attribution_summary` on a resolved
    citation (M2's scope, out of this task's boundary); this proves the row
    builder's own handling of that key is correct and forward-compatible
    with whatever shape lands there, while the end-to-end `import_run()`
    path (which cannot produce a non-null mirror today) proves the honest
    "not yet assessed" default.
  - The `_SUMMARY_COLUMNS` coupling: `source_rank`/`attribution_count` are
    scalar and must surface in `search()` results (and, since `get_item()`
    ALSO builds its top-level summary via `_row_to_summary()` — not
    `dict(row)`, contrary to a stale line-anchor note — there too);
    `doi`/`publisher`/`source_version`/`authors_json` stay payload-only,
    matching the pre-existing `url`/`trust`/`usage` precedent, and are
    still visible via `get_item()`'s `payload` key.
"""

from __future__ import annotations

from typing import Any

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths, RunPaths
from research_foundry.services import catalog_service as svc
from research_foundry.yamlio import dump_yaml

# ---------------------------------------------------------------------------
# Fixture: one run, one source card carrying M1's first-party metadata.
# ---------------------------------------------------------------------------


def _plant_metadata_run(
    paths: FoundryPaths,
    run_id: str = "rf_run_smp4001",
    *,
    trust: Any = None,
) -> RunPaths:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "planned",
            "sensitivity": "public",
            "created_at": "2026-08-02T09:00:00-04:00",
        },
        rp.run_yaml,
    )

    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_meta",
            "sensitivity": "public",
            "trust": trust if trust is not None else {"source_rank": "primary"},
            "usage": "direct",
            "source": {
                "title": "Metadata-Rich Source",
                "source_type": "paper",
                "locator": {"url": "https://example.test/paper", "doi": "10.1234/example"},
                "authors": ["A. Author", "B. Coauthor"],
                "publisher": "Example Press",
                "version": "v2",
            },
            "extracted_points": [
                {
                    "evidence_id": "ev_meta",
                    "locator": "p1",
                    "quote": "quoted text",
                    "summary": "summary text",
                }
            ],
        },
        "# source",
        rp.sources / "src_meta.md",
    )

    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_meta",
                    "text": "A claim citing the metadata-rich source.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_meta",
                            "evidence_id": "ev_meta",
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                }
            ],
        },
        rp.claim_ledger,
    )
    return rp


def _source_row(paths: FoundryPaths, run_id: str) -> Any:
    with svc._db(paths) as conn:
        return conn.execute(
            "SELECT * FROM catalog_items WHERE run_id = ? AND item_type = 'source'",
            (run_id,),
        ).fetchone()


# ---------------------------------------------------------------------------
# DDL / schema version
# ---------------------------------------------------------------------------


def test_schema_version_is_5(tmp_foundry: FoundryPaths) -> None:
    assert svc.SCHEMA_VERSION == 5


def test_rebuild_schema_creates_new_columns(tmp_foundry: FoundryPaths) -> None:
    svc.rebuild_schema(tmp_foundry)
    with svc._db(tmp_foundry) as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(catalog_items)").fetchall()}
    for expected in (
        "doi",
        "publisher",
        "source_version",
        "authors_json",
        "source_rank",
        "attribution_count",
    ):
        assert expected in cols, f"missing column: {expected}"


# ---------------------------------------------------------------------------
# Row-builder wiring: M1 first-party metadata, end-to-end via import_run()
# ---------------------------------------------------------------------------


def test_import_run_populates_first_party_metadata_columns(tmp_foundry: FoundryPaths) -> None:
    _plant_metadata_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_smp4001")

    row = _source_row(tmp_foundry, "rf_run_smp4001")
    assert row is not None
    assert row["doi"] == "10.1234/example"
    assert row["publisher"] == "Example Press"
    assert row["source_version"] == "v2"
    assert row["authors_json"] == '["A. Author", "B. Coauthor"]'
    assert row["source_rank"] == "primary"
    # export_service.py has not yet been widened to surface `attribution_summary`
    # on a resolved citation (M2 scope) — the honest default is "not yet
    # assessed", never a fabricated 0.
    assert row["attribution_count"] is None


def test_import_run_payload_carries_metadata_for_item_detail(tmp_foundry: FoundryPaths) -> None:
    """`get_item()`'s payload key (not `_SUMMARY_COLUMNS`) is how detail-only
    fields like doi/publisher/version/authors surface — same precedent as
    the pre-existing `url`/`trust`/`usage` fields.
    """

    _plant_metadata_run(tmp_foundry)
    result = svc.import_run(tmp_foundry, "rf_run_smp4001")
    assert result["items"] >= 1

    row = _source_row(tmp_foundry, "rf_run_smp4001")
    item = svc.get_item(tmp_foundry, row["catalog_item_id"])
    assert item is not None
    payload = item["payload"]
    assert payload["doi"] == "10.1234/example"
    assert payload["publisher"] == "Example Press"
    assert payload["version"] == "v2"
    assert payload["authors"] == ["A. Author", "B. Coauthor"]
    assert payload["attribution_summary"] is None


# ---------------------------------------------------------------------------
# source_rank vs trust_label: deliberately distinct semantics
# ---------------------------------------------------------------------------


def test_source_rank_null_for_legacy_string_trust(tmp_foundry: FoundryPaths) -> None:
    """A legacy plain-string `trust` populates `trust_label` (str-cast
    fallback) but must NOT populate `source_rank` — free text is not one of
    {primary, secondary, tertiary, unknown}.
    """

    _plant_metadata_run(tmp_foundry, trust="high")
    svc.import_run(tmp_foundry, "rf_run_smp4001")

    row = _source_row(tmp_foundry, "rf_run_smp4001")
    assert row["trust_label"] == "high"
    assert row["source_rank"] is None


def test_source_rank_populated_from_dict_trust(tmp_foundry: FoundryPaths) -> None:
    _plant_metadata_run(tmp_foundry, trust={"source_rank": "secondary"})
    svc.import_run(tmp_foundry, "rf_run_smp4001")

    row = _source_row(tmp_foundry, "rf_run_smp4001")
    assert row["trust_label"] == "secondary"
    assert row["source_rank"] == "secondary"


# ---------------------------------------------------------------------------
# attribution_count tri-state: NULL vs 0 vs >0
# ---------------------------------------------------------------------------


def _synthetic_export_data(attribution_summary: Any) -> dict[str, Any]:
    """A hand-built `export_run()`-shaped dict carrying `attribution_summary`
    on the resolved citation — proving `_build_source_rows()`'s OWN handling
    of that key, independent of whether the export layer has been widened
    to populate it yet (M2's scope, not this task's).
    """

    return {
        "claims": [
            {
                "claim_id": "clm_1",
                "sources": [
                    {
                        "resolved": True,
                        "dangling": False,
                        "source_card_id": "src_1",
                        "evidence_id": "ev_1",
                        "title": "Source One",
                        "source_type": "paper",
                        "url": None,
                        "authors": None,
                        "doi": None,
                        "publisher": None,
                        "version": None,
                        "trust": {"source_rank": "primary"},
                        "usage": None,
                        "sensitivity": "public",
                        "attribution_summary": attribution_summary,
                        "quote": "q",
                        "summary": "s",
                        "relation": "supports",
                        "evidence_locator": "p1",
                    }
                ],
            }
        ]
    }


def test_attribution_count_not_yet_assessed_when_mirror_absent() -> None:
    rows, _ = svc._build_source_rows(
        _synthetic_export_data(None),
        "rf_run_synth",
        project=None,
        created_at="2026-08-02T00:00:00Z",
        run_sensitivity_rank=0,
        citation_ranks={},
    )
    assert rows[0]["attribution_count"] is None


def test_attribution_count_zero_when_mirror_assessed_empty() -> None:
    rows, _ = svc._build_source_rows(
        _synthetic_export_data({"attribution_ids": [], "count": 0, "rollups": []}),
        "rf_run_synth",
        project=None,
        created_at="2026-08-02T00:00:00Z",
        run_sensitivity_rank=0,
        citation_ranks={},
    )
    assert rows[0]["attribution_count"] == 0


def test_attribution_count_positive_when_mirror_has_records() -> None:
    mirror = {
        "attribution_ids": ["attrib_a", "attrib_b", "attrib_c"],
        "count": 3,
        "rollups": [
            {
                "asserter_id": "scopus",
                "assertion_kind": "citation_count",
                "attribution_ids": ["attrib_a", "attrib_b", "attrib_c"],
                "count": 3,
                "best_attribution_id": "attrib_c",
                "weakest_attribution_id": "attrib_a",
                "comparable": True,
            }
        ],
    }
    rows, _ = svc._build_source_rows(
        _synthetic_export_data(mirror),
        "rf_run_synth",
        project=None,
        created_at="2026-08-02T00:00:00Z",
        run_sensitivity_rank=0,
        citation_ranks={},
    )
    assert rows[0]["attribution_count"] == 3
    # Value-free mirror propagated verbatim, never recomputed here.
    assert rows[0]["payload_json"]
    import json as _json

    payload = _json.loads(rows[0]["payload_json"])
    assert payload["attribution_summary"] == mirror


# ---------------------------------------------------------------------------
# _SUMMARY_COLUMNS coupling: search() and get_item() both surface the
# scalar new attributes (source_rank/attribution_count); the detail-only
# ones stay in `payload` for both.
# ---------------------------------------------------------------------------


def test_search_results_include_source_rank(tmp_foundry: FoundryPaths) -> None:
    _plant_metadata_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_smp4001")

    result = svc.search(tmp_foundry, item_type="source")
    assert result["items"], "expected at least one source item in search results"
    item = result["items"][0]
    assert item["source_rank"] == "primary"
    assert "attribution_count" in item
    # Detail-only fields are deliberately absent from search summaries.
    assert "doi" not in item
    assert "authors_json" not in item


def test_get_item_summary_includes_source_rank_via_row_to_summary(
    tmp_foundry: FoundryPaths,
) -> None:
    """get_item()'s top-level summary is built via `_row_to_summary()` (the
    SAME `_SUMMARY_COLUMNS` allowlist `search()` uses), not `dict(row)` —
    so `source_rank`/`attribution_count` must appear at the top level here
    too, exactly like search() results.
    """

    _plant_metadata_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_smp4001")
    row = _source_row(tmp_foundry, "rf_run_smp4001")

    item = svc.get_item(tmp_foundry, row["catalog_item_id"])
    assert item is not None
    assert item["source_rank"] == "primary"
    assert item["attribution_count"] is None


# ---------------------------------------------------------------------------
# Non-regression: existing item types unaffected by the new _base_row kwargs
# ---------------------------------------------------------------------------


def test_claim_rows_unaffected_by_new_optional_columns(tmp_foundry: FoundryPaths) -> None:
    """Claim/inference rows never pass the source-only kwargs to
    `_base_row()` — `doi`/`publisher`/`source_version`/`authors_json`/
    `source_rank` must default to null, not error or silently inherit a
    source row's values.

    `attribution_count` is the one exception as of SMP-4.4 Part 2: claim
    rows now DO pass it (from a cross-source merge over the claim's own
    cited sources — see the `_merge_attribution_summaries` tests below).
    It still reads null here because this fixture's single source card
    carries no `attribution_summary` mirror at all — that is the honest
    "not yet assessed" default, not evidence the kwarg is unwired for
    claims (see `test_claim_attribution_count_populates_from_multiple_
    cited_sources` for the wired, non-null case).
    """

    _plant_metadata_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_smp4001")

    with svc._db(tmp_foundry) as conn:
        claim_row = conn.execute(
            "SELECT * FROM catalog_items WHERE run_id = ? AND item_type = 'claim'",
            ("rf_run_smp4001",),
        ).fetchone()
    assert claim_row is not None
    assert claim_row["doi"] is None
    assert claim_row["publisher"] is None
    assert claim_row["source_version"] is None
    assert claim_row["authors_json"] is None
    assert claim_row["source_rank"] is None
    assert claim_row["attribution_count"] is None


# ---------------------------------------------------------------------------
# SMP-4.4 Part 2: `_merge_attribution_summaries` — cross-source rollup
# consumption. Monotone-only (no averaging path exists), refuses to launder
# a raw value when a (asserter_id, assertion_kind) key is contributed by
# more than one source, and canonically sorts every id list.
# ---------------------------------------------------------------------------

_ROLLUP_KEYS = {
    "asserter_id",
    "assertion_kind",
    "attribution_ids",
    "count",
    "best_attribution_id",
    "weakest_attribution_id",
    "comparable",
}


def test_merge_attribution_summaries_returns_none_when_all_absent() -> None:
    assert svc._merge_attribution_summaries([None, None]) is None
    assert svc._merge_attribution_summaries([]) is None
    assert svc._merge_attribution_summaries([None, "not-a-dict", 42]) is None


def test_merge_attribution_summaries_single_source_passthrough() -> None:
    """Exactly one contributing source per key: that source's own
    already-computed best/weakest pointers are still authoritative and
    must pass through unchanged — this function never second-guesses a
    single source's own monotone reduction."""

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
    merged = svc._merge_attribution_summaries([mirror])
    assert merged == {
        "attribution_ids": ["attrib_a", "attrib_b"],  # canonically sorted
        "count": 2,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["attrib_a", "attrib_b"],
                "count": 2,
                "best_attribution_id": "attrib_b",
                "weakest_attribution_id": "attrib_a",
                "comparable": True,
            }
        ],
    }


def test_merge_attribution_summaries_cross_source_ambiguous_key_refuses_to_pick_a_winner() -> None:
    """Two DIFFERENT sources both assert under the SAME (asserter_id,
    assertion_kind) key. Picking a "best" between them would require the
    raw values, which this value-free mirror never carries — the merge
    must NOT launder a winner. It degrades to `comparable=False` with both
    pointers `None`, while still unioning the id set and disjoint keys
    (`crossref` below) still pass through as single-source, unaffected.
    """

    source_a = {
        "attribution_ids": ["a1", "a2", "a3"],
        "count": 3,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["a1", "a2"],
                "count": 2,
                "best_attribution_id": "a2",
                "weakest_attribution_id": "a1",
                "comparable": True,
            },
            {
                "asserter_id": "crossref",
                "assertion_kind": "citation_count",
                "attribution_ids": ["a3"],
                "count": 1,
                "best_attribution_id": "a3",
                "weakest_attribution_id": "a3",
                "comparable": True,
            },
        ],
    }
    source_b = {
        "attribution_ids": ["b1"],
        "count": 1,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["b1"],
                "count": 1,
                "best_attribution_id": "b1",
                "weakest_attribution_id": "b1",
                "comparable": True,
            }
        ],
    }

    merged = svc._merge_attribution_summaries([source_a, source_b])
    assert merged is not None
    assert merged["attribution_ids"] == ["a1", "a2", "a3", "b1"]
    assert merged["count"] == 4

    by_key = {(r["asserter_id"], r["assertion_kind"]): r for r in merged["rollups"]}

    ambiguous = by_key[("semantic_scholar", "citation_count")]
    assert ambiguous["attribution_ids"] == ["a1", "a2", "b1"]
    assert ambiguous["count"] == 3
    assert ambiguous["comparable"] is False
    assert ambiguous["best_attribution_id"] is None
    assert ambiguous["weakest_attribution_id"] is None

    unambiguous = by_key[("crossref", "citation_count")]
    assert unambiguous["attribution_ids"] == ["a3"]
    assert unambiguous["best_attribution_id"] == "a3"
    assert unambiguous["weakest_attribution_id"] == "a3"
    assert unambiguous["comparable"] is True

    # Structural, not vocabulary-based, non-averaging proof: every rollup
    # entry has EXACTLY the schema-shaped 7 keys — no `best_value`/
    # `weakest_value`/`average_value`/`mean_value` leaked through, and no
    # numeric field exists anywhere for an averaging path to write into.
    for entry in merged["rollups"]:
        assert set(entry.keys()) == _ROLLUP_KEYS


def test_merge_attribution_summaries_is_order_independent() -> None:
    """Canonical sort means the merge result must not depend on the order
    mirrors are passed in — `json.dump` preserves insertion order but does
    not impose one (plan decision)."""

    source_a = {
        "attribution_ids": ["z9", "a1"],
        "count": 2,
        "rollups": [
            {
                "asserter_id": "openalex",
                "assertion_kind": "citation_count",
                "attribution_ids": ["z9"],
                "count": 1,
                "best_attribution_id": "z9",
                "weakest_attribution_id": "z9",
                "comparable": True,
            }
        ],
    }
    source_b = {
        "attribution_ids": ["m5"],
        "count": 1,
        "rollups": [
            {
                "asserter_id": "openalex",
                "assertion_kind": "retraction_status",
                "attribution_ids": ["m5"],
                "count": 1,
                "best_attribution_id": "m5",
                "weakest_attribution_id": "m5",
                "comparable": True,
            }
        ],
    }

    forward = svc._merge_attribution_summaries([source_a, source_b])
    backward = svc._merge_attribution_summaries([source_b, source_a])
    assert forward == backward
    assert forward["attribution_ids"] == sorted(forward["attribution_ids"])


def test_claim_attribution_count_populates_from_multiple_cited_sources() -> None:
    """SMP-4.4 Part 2, wired end-to-end through `_build_claim_and_inference_
    rows()`: a claim citing TWO distinct source_card_ids, each carrying its
    own `attribution_summary` mirror, gets a merged claim-level
    `attribution_summary` in its payload and a populated `attribution_count`
    column — not the perpetual NULL a claim would get if this were still
    unwired."""

    mirror_a = {
        "attribution_ids": ["a1", "a2"],
        "count": 2,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["a1", "a2"],
                "count": 2,
                "best_attribution_id": "a2",
                "weakest_attribution_id": "a1",
                "comparable": True,
            }
        ],
    }
    mirror_b = {
        "attribution_ids": ["b1"],
        "count": 1,
        "rollups": [
            {
                "asserter_id": "crossref",
                "assertion_kind": "citation_count",
                "attribution_ids": ["b1"],
                "count": 1,
                "best_attribution_id": "b1",
                "weakest_attribution_id": "b1",
                "comparable": True,
            }
        ],
    }

    export_data = {
        "claims": [
            {
                "claim_id": "clm_multi",
                "text": "A claim citing two distinct sources.",
                "materiality": "core",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "high",
                "report_locations": [],
                "inference_basis": {"from_claims": [], "reasoning_summary": None},
                "sources": [
                    {
                        "resolved": True,
                        "dangling": False,
                        "source_card_id": "src_a",
                        "evidence_id": "ev_a",
                        "relation": "supports",
                        "locator": "p1",
                        "evidence_locator": "p1",
                        "attribution_summary": mirror_a,
                    },
                    {
                        "resolved": True,
                        "dangling": False,
                        "source_card_id": "src_b",
                        "evidence_id": "ev_b",
                        "relation": "supports",
                        "locator": "p2",
                        "evidence_locator": "p2",
                        "attribution_summary": mirror_b,
                    },
                ],
            }
        ]
    }

    rows, claim_id_to_item_id, _report_claim_ids, _term_rows = svc._build_claim_and_inference_rows(
        export_data,
        "rf_run_synth_claim",
        project=None,
        created_at="2026-08-02T00:00:00Z",
        run_sensitivity_rank=0,
        citation_ranks={},
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["attribution_count"] == 3  # len({a1, a2, b1})
    assert claim_id_to_item_id["clm_multi"] == row["catalog_item_id"]

    import json as _json

    payload = _json.loads(row["payload_json"])
    assert payload["attribution_summary"]["attribution_ids"] == ["a1", "a2", "b1"]
    assert payload["attribution_summary"]["count"] == 3
    by_key = {
        (r["asserter_id"], r["assertion_kind"]): r
        for r in payload["attribution_summary"]["rollups"]
    }
    assert by_key[("semantic_scholar", "citation_count")]["best_attribution_id"] == "a2"
    assert by_key[("crossref", "citation_count")]["best_attribution_id"] == "b1"
