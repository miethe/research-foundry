"""Unit tests for ``catalog_terms`` (claim-term-indexing v1, TASK-2.3/2.4).

Covers: DDL creation on ``rebuild_schema()``, per-row ``sensitivity_rank``
derived from each claim/inference item's OWN effective rank (decision D3 —
never a single flat blob computed once at the max-permissive tier), absence
handling for claims with no ``_term_index`` block, and rebuild idempotency
(file-is-truth: ``catalog_terms`` is fully regenerated from source
``claim_ledger.yaml`` files, never accumulated). All tests run against
synthetic YAML/Markdown fixtures — no real run data, no network, no LLM.
"""

from __future__ import annotations

from typing import Any

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths, RunPaths
from research_foundry.services import catalog_service as svc
from research_foundry.yamlio import dump_yaml

# ---------------------------------------------------------------------------
# Minimal synthetic-run fixture: two claims, each citing a source at a
# different sensitivity rank, both carrying a `_term_index` block.
# ---------------------------------------------------------------------------


def _build_two_rank_run(paths: FoundryPaths, run_id: str = "rf_run_terms001") -> RunPaths:
    """A run with two claims whose cited sources sit at different sensitivity
    ranks, each claim carrying a `_term_index` block on the SAME term id.

    - ``clm_low`` cites ``src_public`` (``sensitivity: public``) -> the
      lowest possible effective rank.
    - ``clm_high`` cites ``src_sensitive`` (``sensitivity: work_sensitive``)
      -> a strictly higher effective rank.

    This is the fixture the D3 acceptance criterion is written against: the
    resulting ``catalog_terms`` rows for the term ``cbc`` must carry TWO
    DISTINCT ``sensitivity_rank`` values (one per claim's own effective
    rank), never one shared value computed once for the whole run.
    """

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
            "created_at": "2026-07-24T09:00:00-04:00",
            "linked_projects": ["proj-terms"],
            "category": "Pediatrics",
        },
        rp.run_yaml,
    )

    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_public",
            "sensitivity": "public",
            "source": {
                "title": "Public Source",
                "source_type": "web",
                "locator": {"url": "https://example.test/public"},
            },
            "trust": "high",
            "usage": "direct",
            "extracted_points": [
                {
                    "evidence_id": "ev_pub",
                    "locator": "p1",
                    "summary": "public point",
                    "quote": "PUBLIC QUOTE",
                }
            ],
        },
        "",
        rp.sources / "src_public.md",
    )

    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_sensitive",
            "sensitivity": "public",
            "source": {"title": "Sensitive Source", "source_type": "paper"},
            "trust": "medium",
            "usage": "paraphrase",
            "extracted_points": [
                {
                    "evidence_id": "ev_sens",
                    "locator": "s1",
                    "summary": "sensitive point",
                    "quote": "SENSITIVE QUOTE",
                    "sensitivity": "work_sensitive",
                }
            ],
        },
        "",
        rp.sources / "src_sensitive.md",
    )

    claims: list[dict[str, Any]] = [
        {
            "claim_id": "clm_low",
            "text": "CBC panel is unremarkable in this cohort.",
            "materiality": "core",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": "src_public",
                    "evidence_id": "ev_pub",
                    "relation": "supports",
                    "locator": "p1",
                }
            ],
            "inference_basis": {"from_claims": [], "reasoning_summary": None},
            "report_locations": [],
            "_term_index": {
                "terms": ["cbc"],
                "usage_roles": {"cbc": "background"},
                "vocabulary_version": "pediatric-v1",
            },
        },
        {
            "claim_id": "clm_high",
            "text": "CBC threshold above 15 x10^9/L triggers escalation.",
            "materiality": "core",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": "src_sensitive",
                    "evidence_id": "ev_sens",
                    "relation": "supports",
                    "locator": "s1",
                }
            ],
            "inference_basis": {"from_claims": [], "reasoning_summary": None},
            "report_locations": [],
            "_term_index": {
                "terms": ["cbc"],
                "usage_roles": {"cbc": "threshold"},
                "vocabulary_version": "pediatric-v1",
            },
        },
        {
            "claim_id": "clm_no_terms",
            "text": "A claim with zero vocabulary hits.",
            "materiality": "background",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "medium",
            "sources": [],
            "inference_basis": {"from_claims": [], "reasoning_summary": None},
            "report_locations": [],
            # No `_term_index` key at all -- Phase 1's AC-1 resilience case
            # (omitted entirely, not an empty block).
        },
    ]

    dump_yaml({"id": f"ledger_{run_id}", "claims": claims}, rp.claim_ledger)

    return rp


# ---------------------------------------------------------------------------
# TASK-2.3: DDL + per-row sensitivity_rank
# ---------------------------------------------------------------------------


def test_rebuild_schema_creates_catalog_terms_table(tmp_foundry: FoundryPaths) -> None:
    svc.rebuild_schema(tmp_foundry)
    with svc._db(tmp_foundry) as conn:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_terms'"
        ).fetchone()
        assert row is not None


def test_two_ranked_sources_produce_two_distinct_ranked_term_rows(
    tmp_foundry: FoundryPaths,
) -> None:
    """The D3 acceptance criterion: two evidence points at different
    sensitivity ranks must yield two ``catalog_terms`` rows carrying two
    DIFFERENT ``sensitivity_rank`` values for the SAME term ``cbc`` — never
    one blob computed once at the run's (or the max-permissive) tier.
    """

    _build_two_rank_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_terms001")

    with svc._db(tmp_foundry) as conn:
        rows = conn.execute(
            "SELECT catalog_item_id, term, role, sensitivity_rank FROM catalog_terms "
            "WHERE run_id = ? ORDER BY sensitivity_rank",
            ("rf_run_terms001",),
        ).fetchall()

    assert [r["term"] for r in rows] == ["cbc", "cbc"]
    ranks = [r["sensitivity_rank"] for r in rows]
    assert ranks[0] != ranks[1], "term rows must carry distinct per-item ranks, not one blob"

    roles_by_rank = {r["sensitivity_rank"]: r["role"] for r in rows}
    assert roles_by_rank[ranks[0]] in {"background", "threshold"}
    assert roles_by_rank[ranks[1]] in {"background", "threshold"}
    assert roles_by_rank[ranks[0]] != roles_by_rank[ranks[1]]

    # Each term row's rank must equal ITS OWN claim item's catalog_items rank
    # (never the run's own rank, never a run-wide max).
    with svc._db(tmp_foundry) as conn:
        item_ranks = {
            r["local_ref"]: r["sensitivity_rank"]
            for r in conn.execute(
                "SELECT local_ref, sensitivity_rank FROM catalog_items "
                "WHERE run_id = ? AND item_type = 'claim'",
                ("rf_run_terms001",),
            ).fetchall()
        }
    assert item_ranks["clm_low"] != item_ranks["clm_high"]
    assert set(ranks) == {item_ranks["clm_low"], item_ranks["clm_high"]}


def test_claim_without_term_index_produces_no_term_rows(tmp_foundry: FoundryPaths) -> None:
    """AC-1 resilience (Phase 1): a claim with an omitted `_term_index` block
    must not produce a placeholder/empty catalog_terms row.
    """

    _build_two_rank_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_terms001")

    with svc._db(tmp_foundry) as conn:
        no_terms_item = conn.execute(
            "SELECT catalog_item_id FROM catalog_items WHERE run_id = ? AND local_ref = ?",
            ("rf_run_terms001", "clm_no_terms"),
        ).fetchone()
        assert no_terms_item is not None
        rows = conn.execute(
            "SELECT * FROM catalog_terms WHERE catalog_item_id = ?",
            (no_terms_item["catalog_item_id"],),
        ).fetchall()
    assert rows == []


# ---------------------------------------------------------------------------
# TASK-2.4: rebuild wiring + idempotency (file-is-truth doctrine)
# ---------------------------------------------------------------------------


def test_rf_catalog_rebuild_regenerates_term_rows_from_source(
    tmp_foundry: FoundryPaths,
) -> None:
    _build_two_rank_run(tmp_foundry)
    result = svc.rebuild(tmp_foundry)
    assert result["errors"] == []

    with svc._db(tmp_foundry) as conn:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM catalog_terms WHERE run_id = ?", ("rf_run_terms001",)
        ).fetchone()
    assert count == 2


def test_rebuild_is_idempotent_for_catalog_terms(tmp_foundry: FoundryPaths) -> None:
    """A second rebuild over unchanged source produces identical rows."""

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)
    with svc._db(tmp_foundry) as conn:
        first = sorted(
            tuple(r)
            for r in conn.execute(
                "SELECT catalog_item_id, term, role, run_id, sensitivity_rank "
                "FROM catalog_terms ORDER BY catalog_item_id, term"
            ).fetchall()
        )

    svc.rebuild(tmp_foundry)
    with svc._db(tmp_foundry) as conn:
        second = sorted(
            tuple(r)
            for r in conn.execute(
                "SELECT catalog_item_id, term, role, run_id, sensitivity_rank "
                "FROM catalog_terms ORDER BY catalog_item_id, term"
            ).fetchall()
        )

    assert first == second
    assert len(first) == 2


def test_reimport_after_removing_term_index_removes_term_rows(
    tmp_foundry: FoundryPaths,
) -> None:
    """Delete-then-insert (import_run's contract) must also clear stale
    catalog_terms rows -- a claim that loses its `_term_index` on re-import
    (e.g. a vocabulary rollback) must not leave orphaned term rows behind.
    """

    rp = _build_two_rank_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_terms001")
    with svc._db(tmp_foundry) as conn:
        (before,) = conn.execute(
            "SELECT COUNT(*) FROM catalog_terms WHERE run_id = ?", ("rf_run_terms001",)
        ).fetchone()
    assert before == 2

    dump_yaml(
        {
            "id": "ledger_rf_run_terms001",
            "claims": [
                {
                    "claim_id": "clm_low",
                    "text": "CBC panel is unremarkable in this cohort.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                }
            ],
        },
        rp.claim_ledger,
    )
    svc.import_run(tmp_foundry, "rf_run_terms001")

    with svc._db(tmp_foundry) as conn:
        (after,) = conn.execute(
            "SELECT COUNT(*) FROM catalog_terms WHERE run_id = ?", ("rf_run_terms001",)
        ).fetchone()
    assert after == 0


# ---------------------------------------------------------------------------
# TASK-2.5: `rf catalog search --term`/`--role` facets (OQ-C)
# ---------------------------------------------------------------------------


def _local_refs(result: dict[str, Any]) -> set[str]:
    return {item["local_ref"] for item in result["items"]}


def test_search_term_filter_returns_every_claim_carrying_the_term(
    tmp_foundry: FoundryPaths,
) -> None:
    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    result = svc.search(tmp_foundry, term=["cbc"], sensitivity_threshold="client_sensitive")
    assert _local_refs(result) == {"clm_low", "clm_high"}


def test_search_term_filter_excludes_claims_with_no_matching_term(
    tmp_foundry: FoundryPaths,
) -> None:
    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    result = svc.search(
        tmp_foundry, term=["not_a_real_term"], sensitivity_threshold="client_sensitive"
    )
    assert result["items"] == []
    assert result["total"] == 0


def test_search_role_filter_narrows_to_the_matching_role(tmp_foundry: FoundryPaths) -> None:
    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    result = svc.search(tmp_foundry, role=["threshold"], sensitivity_threshold="client_sensitive")
    assert _local_refs(result) == {"clm_high"}


def test_search_term_and_role_together_is_and_not_or(tmp_foundry: FoundryPaths) -> None:
    """OQ-C: distinct flags (``--term`` + ``--role``) combine with AND. Both
    ``clm_low`` and ``clm_high`` carry the term ``cbc``, but only
    ``clm_low``'s role for that term is ``background`` — ``clm_high``'s is
    ``threshold``. If the two flags were silently OR'd, ``clm_high`` would
    also match (it has *some* row satisfying ``role=background``... it does
    not, so this also proves the filter isn't silently ignored).
    """

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    result = svc.search(
        tmp_foundry, term=["cbc"], role=["background"], sensitivity_threshold="client_sensitive"
    )
    assert _local_refs(result) == {"clm_low"}


def test_search_term_repeated_is_or_within_the_same_flag(tmp_foundry: FoundryPaths) -> None:
    """OQ-C: repeats of the SAME flag OR together. ``clm_low``'s only term is
    ``cbc``; ``clm_high``'s only term (via role) is also ``cbc`` but under a
    role that would fail an AND-role test above — here we filter on term
    alone with two values, one real (``cbc``) and one that matches nothing,
    and expect the same result as filtering on ``cbc`` alone (OR, not AND,
    within the repeats).
    """

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    result = svc.search(
        tmp_foundry,
        term=["cbc", "not_a_real_term"],
        sensitivity_threshold="client_sensitive",
    )
    assert _local_refs(result) == {"clm_low", "clm_high"}


def test_search_term_filter_combines_with_item_type_filter_and_not_or(
    tmp_foundry: FoundryPaths,
) -> None:
    """Combining ``--term`` with an existing filter (``--item-type``) narrows
    (AND) rather than being silently ignored: no ``source`` item carries a
    ``catalog_terms`` row (TASK-2.3/2.4 only wire claims/inferences), so
    adding ``item_type="source"`` to a term filter that otherwise matches two
    claims must drop the result to zero, not return the two claims unfiltered.
    """

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    unfiltered = svc.search(tmp_foundry, term=["cbc"], sensitivity_threshold="client_sensitive")
    assert len(unfiltered["items"]) == 2

    narrowed = svc.search(
        tmp_foundry,
        term=["cbc"],
        item_type="source",
        sensitivity_threshold="client_sensitive",
    )
    assert narrowed["items"] == []
    assert narrowed["total"] == 0


def test_search_term_filter_combines_with_project_filter(tmp_foundry: FoundryPaths) -> None:
    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    matching = svc.search(
        tmp_foundry,
        term=["cbc"],
        project="proj-terms",
        sensitivity_threshold="client_sensitive",
    )
    assert _local_refs(matching) == {"clm_low", "clm_high"}

    non_matching = svc.search(
        tmp_foundry,
        term=["cbc"],
        project="proj-does-not-exist",
        sensitivity_threshold="client_sensitive",
    )
    assert non_matching["items"] == []


# ---------------------------------------------------------------------------
# TASK-2.7: sensitivity-threshold gate on catalog_terms (D3, service layer)
# ---------------------------------------------------------------------------


def test_search_term_filter_hides_above_threshold_term_row(tmp_foundry: FoundryPaths) -> None:
    """AC-5 (redaction parity, service layer): a term row above the caller's
    resolved threshold must not match, even though the underlying claim item
    exists in the catalog at some (higher) threshold. ``clm_high`` sits at
    the ``work_sensitive``-derived rank; a caller pinned to ``public`` must
    get zero matches for ``--term cbc --role threshold`` (the ``clm_high``
    row), while ``clm_low`` (public rank) still matches on its own term row.
    """

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    with svc._db(tmp_foundry) as conn:
        ranks = {
            r["local_ref"]: r["sensitivity_rank"]
            for r in conn.execute(
                "SELECT local_ref, sensitivity_rank FROM catalog_items "
                "WHERE run_id = ? AND item_type = 'claim'",
                ("rf_run_terms001",),
            ).fetchall()
        }
    assert ranks["clm_low"] < ranks["clm_high"]

    low_label = svc._label_for_rank(ranks["clm_low"])

    at_low_threshold = svc.search(tmp_foundry, term=["cbc"], sensitivity_threshold=low_label)
    assert _local_refs(at_low_threshold) == {"clm_low"}

    at_high_threshold = svc.search(
        tmp_foundry, term=["cbc"], sensitivity_threshold="client_sensitive"
    )
    assert _local_refs(at_high_threshold) == {"clm_low", "clm_high"}


def test_term_filter_predicate_itself_checks_sensitivity_rank_not_just_the_item_gate(
    tmp_foundry: FoundryPaths,
) -> None:
    """White-box: the ``EXISTS`` predicate added for ``--term``/``--role``
    (TASK-2.5) must carry its OWN ``ct.sensitivity_rank <= threshold_rank``
    check, not merely ride on the outer ``catalog_items.sensitivity_rank``
    gate. Today's write path always sets a term row's rank equal to its
    parent item's rank (D3/``_build_term_rows``), so the two gates are
    indistinguishable from the public API alone — this test decouples them by
    directly inserting a second ``catalog_terms`` row at an inflated rank on
    an otherwise-visible item, proving the term-row-level check is real and
    not an artifact of the item-level filter already excluding the row.
    """

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    with svc._db(tmp_foundry) as conn:
        item = conn.execute(
            "SELECT catalog_item_id, sensitivity_rank FROM catalog_items "
            "WHERE run_id = ? AND local_ref = ?",
            ("rf_run_terms001", "clm_low"),
        ).fetchone()
        item_id, item_rank = item["catalog_item_id"], item["sensitivity_rank"]

        # A hypothetical higher-sensitivity term on an item that is itself
        # still visible at every tested threshold.
        conn.execute(
            "INSERT INTO catalog_terms "
            "(catalog_item_id, term, role, run_id, sensitivity_rank) "
            "VALUES (?, 'injected_term', 'background', ?, ?)",
            (item_id, "rf_run_terms001", item_rank + 1),
        )
        conn.commit()

    # The item itself remains visible at the top threshold...
    visible = svc.search(tmp_foundry, sensitivity_threshold="client_sensitive")
    assert "clm_low" in _local_refs(visible)

    # ...but the inflated-rank term must not match at a threshold that sits
    # between the item's own rank and the injected row's rank.
    below_injected = svc._label_for_rank(item_rank)
    result = svc.search(
        tmp_foundry, term=["injected_term"], sensitivity_threshold=below_injected
    )
    assert result["items"] == []

    # It DOES match once the threshold reaches the injected row's own rank.
    at_injected = svc._label_for_rank(item_rank + 1)
    result2 = svc.search(tmp_foundry, term=["injected_term"], sensitivity_threshold=at_injected)
    assert _local_refs(result2) == {"clm_low"}


# ---------------------------------------------------------------------------
# Phase 4 review gap: `_facets()` computed no terms/roles facet at all, so
# the frontend chip-row was permanently empty in loopback (LAN API) mode.
# ---------------------------------------------------------------------------


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


def test_facets_reflect_visible_terms_and_roles(tmp_foundry: FoundryPaths) -> None:
    """Positive case: the terms/roles the caller is entitled to see actually
    show up in the facet — not just an empty-list vacuous pass."""

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    result = svc.search(tmp_foundry, sensitivity_threshold="client_sensitive")
    assert result["facets"]["terms"] == ["cbc"]
    assert set(result["facets"]["roles"]) == {"background", "threshold"}


def test_facets_terms_exclude_rows_above_caller_threshold(tmp_foundry: FoundryPaths) -> None:
    """A term/role whose ``catalog_terms.sensitivity_rank`` exceeds the
    resolved threshold must not appear in the facet, at any tier — the same
    fail-closed guarantee ``search(term=..., role=...)`` already enforces via
    its ``EXISTS`` predicate, now required of ``_facets()`` too."""

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    with svc._db(tmp_foundry) as conn:
        high_item = conn.execute(
            "SELECT catalog_item_id, sensitivity_rank FROM catalog_items "
            "WHERE run_id = ? AND local_ref = ?",
            ("rf_run_terms001", "clm_high"),
        ).fetchone()
        # A second, higher-tier-only term row on the same (already-high-rank)
        # item -- distinct from the shared "cbc" term both claims carry, so
        # the exclusion is observable in the `terms` facet itself, not just
        # `roles`.
        conn.execute(
            "INSERT INTO catalog_terms "
            "(catalog_item_id, term, role, run_id, sensitivity_rank) "
            "VALUES (?, 'hgb', 'background', ?, ?)",
            (high_item["catalog_item_id"], "rf_run_terms001", high_item["sensitivity_rank"]),
        )
        conn.commit()

        ranks = {
            r["local_ref"]: r["sensitivity_rank"]
            for r in conn.execute(
                "SELECT local_ref, sensitivity_rank FROM catalog_items WHERE run_id = ?",
                ("rf_run_terms001",),
            ).fetchall()
        }

    low_label = svc._label_for_rank(ranks["clm_low"])
    at_low = svc.search(tmp_foundry, sensitivity_threshold=low_label)
    assert at_low["facets"]["terms"] == ["cbc"]
    assert at_low["facets"]["roles"] == ["background"]

    at_high = svc.search(tmp_foundry, sensitivity_threshold="client_sensitive")
    assert at_high["facets"]["terms"] == ["cbc", "hgb"]
    assert set(at_high["facets"]["roles"]) == {"background", "threshold"}


def test_facets_terms_workspace_isolation_excludes_other_workspace_term(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WKSP-304: ``catalog_terms`` carries no ``workspace_id`` of its own, so
    the facet must join back to ``catalog_items`` to scope by workspace --
    otherwise a term belonging to another workspace's item silently crosses
    the boundary even though the item itself never would."""

    row = svc._base_row(
        item_type="claim",
        run_id="ws_run",
        local_ref="c_other",
        project=None,
        title="Other workspace claim",
        summary="Other workspace claim",
        status="supported",
        sensitivity_rank=0,
        trust_label=None,
        confidence="high",
        source_count=0,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        payload={"text": "other"},
    )
    row["workspace_id"] = "ws-other"
    item_id = row["catalog_item_id"]

    with svc._db(tmp_foundry) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            svc._insert_rows(conn, [row], [], "ws_run")
            conn.execute(
                "INSERT INTO catalog_terms "
                "(catalog_item_id, term, role, run_id, sensitivity_rank) "
                "VALUES (?, 'other_ws_term', 'background', ?, 0)",
                (item_id, "ws_run"),
            )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise

    _force_isolation_active(monkeypatch)

    cross_ws_result = svc.search(
        tmp_foundry, page_size=200, identity=AuthIdentity("u1", "ws-mine", ("owner",))
    )
    assert "other_ws_term" not in cross_ws_result["facets"]["terms"]
    assert cross_ws_result["facets"]["roles"] == []

    same_ws_result = svc.search(
        tmp_foundry, page_size=200, identity=AuthIdentity("u2", "ws-other", ("owner",))
    )
    assert "other_ws_term" in same_ws_result["facets"]["terms"]
    assert "background" in same_ws_result["facets"]["roles"]


def test_facets_workspace_id_none_matches_pre_existing_facets_shape(
    tmp_foundry: FoundryPaths,
) -> None:
    """No-regression check: ``identity=None`` (isolation inactive) is
    byte-identical to the pre-claim-term-indexing behaviour for the three
    pre-existing facets, alongside the new ``terms``/``roles`` keys."""

    _build_two_rank_run(tmp_foundry)
    svc.rebuild(tmp_foundry)

    baseline = svc.search(tmp_foundry, sensitivity_threshold="client_sensitive")
    with_none_identity = svc.search(
        tmp_foundry, sensitivity_threshold="client_sensitive", identity=None
    )
    assert with_none_identity["facets"] == baseline["facets"]
    assert baseline["facets"]["projects"] == ["proj-terms"]
    assert baseline["facets"]["terms"] == ["cbc"]
