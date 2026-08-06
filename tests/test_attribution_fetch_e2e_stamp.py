"""Clearance-gates M3 — the ON-DISK end-to-end proof of the fetch chain.

WHY THIS FILE EXISTS SEPARATELY FROM THE UNIT SUITES. Both halves of the M3
chain were already heavily unit-tested before this file
(``tests/test_attribution_fetch_dev_test_posture.py`` for the fetch/stamp
half, the M2 writer's own tests for the persist half), but they were
"joined only in tests of their halves" — nothing exercised
posture -> fetch -> stamp -> **file on disk** -> mediation as one chain.
The nearest precedent,
``test_stamped_record_stays_denied_after_posture_removed_and_gates_closed``,
proves stamp durability entirely IN PROCESS: it mediates the very
``ClearedProviderFetchResult.to_record()`` dict it just built, so a writer
that silently dropped, reshaped, or narrowed the ``clearance`` block on its
way to disk would not be caught by it.

This file closes exactly that gap. Every assertion below is made against a
``clearance`` block that has made a full round trip through
``frontmatter.dump_md`` -> the filesystem -> ``frontmatter.load_md``, and
the mediation half re-reads the card from disk AFTER the posture
declaration has been physically deleted from ``foundry.yaml``.

Network posture: no socket is opened by any test here. The provider is
mocked at the ``_fetch_json`` seam (the same seam
``tests/test_attribution_fetch_dev_test_posture.py`` uses), which is the
seam ``authorize_live_fetch`` actually gates — deliberately NOT a third
mocking convention that could drift from what the real gate checks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import clearance
from research_foundry.services.attribution_fetch import (
    ClearedProviderFetchResult,
    openalex,
    stamp_source_card,
)
from research_foundry.services.clearance import ClearanceDenied, GateRegistry

_FAKE_RAW: dict[str, Any] = {"id": "W2741809807", "cited_by_count": 42}

_POSTURE_BLOCK: dict[str, Any] = {
    "live_fetch_enabled": True,
    "rationale": "local dev/test only; no license/ToS posture asserted",
    "declared_at": "2026-08-05",
    "declared_by": "nick",
}


def _write_foundry_yaml(root: Path, *, posture: bool) -> None:
    """(Re)write ``<root>/foundry.yaml``, with or without the posture block.

    Called twice per test against the SAME root — once to declare the
    posture, once to delete it — so the removal is a real edit to the real
    file the resolver reads, not a second config object built beside the
    first.
    """

    foundry: dict[str, Any] = {"owner": "Test"}
    if posture:
        foundry["dev_test_posture"] = dict(_POSTURE_BLOCK)
    (root / "foundry.yaml").write_text(
        yaml.safe_dump({"foundry": foundry}, sort_keys=False), encoding="utf-8"
    )


def _posture_workspace(tmp_path: Path, *, subdir: str = "fdry_e2e") -> FoundryPaths:
    """A ``tmp_path``-scoped workspace root with the posture declared.

    Mirrors ``tests/test_attribution_fetch_dev_test_posture.py::
    _posture_config`` — no ``schemas``/``config``/``templates`` copy is
    needed: the adapters touch only ``foundry.yaml`` (plus
    ``.rf_state/rbac.db`` on the audit path, auto-created under this same
    root), and the writer's schema lookup falls back to the distribution
    ``schemas/`` directory when the workspace has none.
    """

    root = tmp_path / subdir
    root.mkdir(parents=True, exist_ok=True)
    _write_foundry_yaml(root, posture=True)
    return FoundryPaths(root=root)


def _write_source_card(paths: FoundryPaths, *, run_id: str = "rf_run_e2e_stamp") -> Path:
    """Write a REAL source card (no ``clearance`` block yet) under ``runs/``.

    Frontmatter shape mirrors a committed card (see
    ``runs/rf_run_20260613_*/sources/src_*.md``) rather than a minimal stub,
    so the writer is proven to patch one key onto a realistic card without
    disturbing the rest — the failure mode a stub card cannot expose.
    """

    card_path = paths.root / "runs" / run_id / "sources" / "src_e2e_openalex_01.md"
    metadata: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": "src_e2e_openalex_01",
        "created_at": "2026-08-05T12:00:00-04:00",
        "created_by_agent": "rf_source_carder",
        "sensitivity": "personal",
        "source": {
            "title": "An OpenAlex work used for the M3 on-disk chain proof",
            "source_type": "other",
            "locator": {
                "url": "https://api.openalex.org/works/10.1%2Fe2e",
                "file_path": None,
                "doi": "10.1/e2e",
                "repo": None,
            },
            "authors": [],
            "publisher": None,
            "published_at": None,
            "accessed_at": "2026-08-05T12:00:00-04:00",
            "version": None,
        },
        "trust": {
            "source_rank": "unknown",
            "reliability_notes": "",
            "known_limitations": [],
            "conflicts_with": [],
        },
        "usage": {
            "allowed_for_public_output": False,
            "allowed_for_work_output": True,
            "allowed_for_personal_meatywiki": True,
            "citation_required": True,
            "quote_limit_notes": "Short excerpts only.",
        },
        "extracted_points": [],
    }
    dump_md(metadata, "# Source content\n\nBody preserved across the stamp write.\n", card_path)
    return card_path


def _registry(tmp_path: Path, *, state: str, name: str) -> GateRegistry:
    """A single-gate registry blocking ``redistribution`` in ``state``.

    Built inline (rather than reusing ``config/clearance_gates.yaml``) so
    each test states the gate world it is asserting against, and so the
    "gate closed" and "gate open" worlds can both be exercised against the
    SAME on-disk stamp.
    """

    reg_yaml = tmp_path / name
    closed_by = "    closed_by: a-human\n" if state == "closed" else ""
    reg_yaml.write_text(
        "schema_version: '1.0'\n"
        "applies_to_kinds: [source_attribution]\n"
        "gates:\n"
        "  - gate_id: DEF-1\n"
        "    blocks_scope: redistribution\n"
        f"    state: {state}\n"
        "    summary: inline registry for the M3 on-disk chain proof\n"
        "    evidence_pointer: docs/x.md\n" + closed_by,
        encoding="utf-8",
    )
    return GateRegistry(path=reg_yaml)


def test_fetch_stamp_persists_on_disk_and_stays_denied_after_posture_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole M3 chain, on disk: posture -> fetch -> stamp -> card ->
    posture DELETED -> re-read from disk -> still denied.

    The on-disk equivalent of ``test_stamped_record_stays_denied_after_
    posture_removed_and_gates_closed``. Where that test mediates the
    in-memory ``to_record()`` dict, every mediation here runs against a
    mapping freshly parsed out of a file by ``load_md``.
    """

    # ---- 1. Posture declared on a tmp_path-scoped workspace. ------------
    paths = _posture_workspace(tmp_path)
    on_config = FoundryConfig(paths=paths)
    assert on_config.dev_test_posture_live_fetch_enabled() is True

    card_path = _write_source_card(paths)
    pre_meta, pre_body = load_md(card_path)
    # The card genuinely starts with NO stamp -- so the assertion further
    # down is proving the writer put one there, not that a fixture did.
    assert clearance.TAINT_KEY not in pre_meta

    # ---- 2. Fetch through the real adapter, provider mocked at the -------
    #         seam authorize_live_fetch actually gates.
    monkeypatch.setattr(openalex, "_fetch_json", lambda url, **kw: dict(_FAKE_RAW))
    result = openalex.fetch(openalex.OpenAlexRequest("10.1/e2e"), config=on_config)
    assert isinstance(result, ClearedProviderFetchResult)
    assert result.clearance["blocked_scopes"] == ["redistribution"]
    assert result.clearance["posture_at_stamp"] == "dev_test"

    # ---- 3. Persist the stamp onto the real card via M2's writer. --------
    stamp_source_card(card_path, result)

    # ---- 4. Read the card back OFF DISK and assert the stamp survived. ---
    meta, body = load_md(card_path)
    stamped = meta[clearance.TAINT_KEY]
    assert stamped["blocked_scopes"] == ["redistribution"]
    assert stamped["schema_version"] == "1.0"
    assert stamped["posture_at_stamp"] == "dev_test"
    assert stamped["stamped_by"] == "attribution_fetch.openalex"
    # A rights-clearance value must never appear anywhere on the written
    # card (ADR Invariant 1) -- asserted on the RENDERED file text, so a
    # value smuggled into any nested key or the body is still caught.
    rendered = card_path.read_text(encoding="utf-8")
    for forbidden in ("CLEARED_", "counsel_approved", "attested"):
        assert forbidden not in rendered

    # The rest of the card is untouched -- the writer patches one key.
    assert body == pre_body
    assert {k: v for k, v in meta.items() if k != clearance.TAINT_KEY} == pre_meta

    # ---- 5. DELETE the posture declaration from the real foundry.yaml. ---
    _write_foundry_yaml(paths.root, posture=False)
    assert (
        "dev_test_posture"
        not in yaml.safe_load((paths.root / "foundry.yaml").read_text(encoding="utf-8"))["foundry"]
    )
    off_config = FoundryConfig(paths=FoundryPaths(root=paths.root))
    assert off_config.dev_test_posture_live_fetch_enabled() is False
    # The removal is REAL, not just a differently-configured object: the
    # same adapter that fetched a moment ago now refuses at the same root.
    assert not isinstance(
        openalex.fetch(openalex.OpenAlexRequest("10.1/e2e"), config=off_config),
        ClearedProviderFetchResult,
    )

    # ---- 6. Re-read the card from disk and mediate. Still denied. --------
    post_meta, _ = load_md(card_path)
    for state in ("closed", "open"):
        registry = _registry(tmp_path, state=state, name=f"gates_{state}.yaml")
        with pytest.raises(ClearanceDenied) as exc:
            clearance.mediate_egress(
                [post_meta],
                kind="source_attribution",
                target_scope="redistribution",
                target="notebooklm",
                registry=registry,
            )
        assert "redistribution" in str(exc.value)
    # Gate CLOSED and gate OPEN both deny, from the same on-disk stamp:
    # mediation reads the record's own frozen block and never re-derives
    # from live gate state (design invariant 2).
    assert (
        _registry(tmp_path, state="closed", name="gates_closed.yaml").open_scopes() == frozenset()
    )
