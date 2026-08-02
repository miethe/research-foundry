"""SMP-3.5 — the `pediatric_cds` namespace stays clean.

source-metadata-propagation-v1's named risk (Named risks, plan): both `oneOf`
branches of ``src/research_foundry/schemas/pediatric_cds.schema.json``
(``PediatricCdsBlockLegacy`` / ``PediatricCdsBlockRich``) are
``additionalProperties: false``, so a single stray key anywhere inside a
``pediatric_cds`` block is a hard ``ExitCode.SCHEMA(2)`` — and there are 7
committed pediatric_cds bundles (``runs/*pediatric_cds*/``) that must keep
validating. This plan introduces new keys (``authors``/``doi``/``publisher``/
``version`` on a card's ``source``/``source.locator``, ``trust.source_rank``,
and the ``attribution_summary`` mirror plus its ``attribution_ids``/``count``/
``rollups``) — none of which may ever land inside ``pediatric_cds.*``.

Selectable via ``pytest tests/ -q -k pediatric_namespace`` (the plan's own AC
command, `AC -> command -> evidence` table, row "M3 pediatric namespace
clean").

Primary assertion is BEHAVIOURAL: it exercises the real production functions
named in the plan's own risk section and inline comments
(``export_service._load_source_cards`` / ``_resolve_source`` /
``export_run``) against the 7 real committed bundles, and proves those
functions never add a forbidden key inside a card's ``pediatric_cds`` block.
A supplementary static guard (grep-equivalent, done in pure Python — no
shelling to ``rg``) additionally confirms today's actual "writer" modules
(``source_cards.py``, ``export_service.py``, ``attribution_triage.py``,
``attribution_validation.py``, ``governance.py``, ``cli_commands.py``) never
even reference the string ``pediatric_cds`` literal.

The 7 bundles under ``runs/`` are treated as READ-ONLY throughout: every read
here uses ``frontmatter.load_md`` or ``export_service.export_run`` (which its
own docstring says never writes — ``_atomic_write_json`` is only reachable
via ``export_to_file``/``export_all``, neither of which this module calls).
``test_export_run_and_resolve_source_never_write_to_the_bundles`` additionally
proves this affirmatively via a pre/post mtime+content snapshot, rather than
merely asserting it by convention.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import export_service
from tests.test_pediatric_cds_redteam_fixtures import _VERIFIED_BUNDLE_RUN_IDS

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The new key NAMES this plan introduces (PRD FR-*, M1/M2 milestones):
# authors/doi/publisher/version on source/source.locator, trust.source_rank,
# and the attribution_summary mirror's own required fields
# (attribution_ids/count/rollups). None of these literal names appear
# anywhere in either oneOf branch of pediatric_cds.schema.json today, so a
# recursive scan for them inside a pediatric_cds subtree has zero legitimate
# collisions -- any hit is real contamination.
_NEW_KEYS = frozenset(
    {
        "authors",
        "doi",
        "publisher",
        "version",
        "source_rank",
        "attribution_summary",
        "attribution_ids",
        "count",
        "rollups",
    }
)

# Writer/emitter modules this plan touches (per the plan's `files_affected`
# across M1-M3). None of them may reference the `pediatric_cds` literal at
# all -- today, none do (see test_writer_modules_never_reference_pediatric_cds_literal).
_WRITER_MODULE_PATHS = (
    _REPO_ROOT / "src" / "research_foundry" / "services" / "source_cards.py",
    _REPO_ROOT / "src" / "research_foundry" / "services" / "export_service.py",
    _REPO_ROOT / "src" / "research_foundry" / "services" / "attribution_triage.py",
    _REPO_ROOT / "src" / "research_foundry" / "services" / "attribution_validation.py",
    _REPO_ROOT / "src" / "research_foundry" / "services" / "governance.py",
    _REPO_ROOT / "src" / "research_foundry" / "cli_commands.py",
)


def _forbidden_keys_in_block(block: Any, *, root_label: str = "pediatric_cds") -> list[str]:
    """Recursively walk *block* and return the dotted/indexed path of every
    dict key that matches one of ``_NEW_KEYS``. Empty list == clean."""

    hits: list[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                here = f"{path}.{key}"
                if key in _NEW_KEYS:
                    hits.append(here)
                _walk(value, here)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")

    _walk(block, root_label)
    return hits


def _pediatric_cds_subtrees(node: Any, *, path: str = "$") -> list[tuple[str, Any]]:
    """Recursively collect every ``(path, value)`` found under a dict key
    literally named ``pediatric_cds``, anywhere inside *node*."""

    found: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}"
            if key == "pediatric_cds":
                found.append((here, value))
            found.extend(_pediatric_cds_subtrees(value, path=here))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found.extend(_pediatric_cds_subtrees(item, path=f"{path}[{i}]"))
    return found


def _iter_bundle_pediatric_cds_blocks():
    """Yield ``(run_id, card_path, evidence_id, block)`` for every non-null
    ``pediatric_cds`` block across the 7 committed bundles. READ-ONLY: uses
    ``frontmatter.load_md`` exclusively, mirroring
    ``test_pediatric_cds_redteam_fixtures._iter_bundle_pediatric_cds_blocks``.
    """

    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        sources_dir = _REPO_ROOT / "runs" / run_id / "sources"
        assert sources_dir.is_dir(), f"expected verified bundle sources dir at {sources_dir}"
        card_paths = sorted(sources_dir.glob("*.md"))
        assert card_paths, f"expected >=1 source card under {sources_dir}"
        for card_path in card_paths:
            front, _body = load_md(card_path)
            for point in front.get("extracted_points", []) or []:
                if not isinstance(point, dict):
                    continue
                block = point.get("pediatric_cds")
                if block is None:
                    continue
                yield run_id, card_path, point.get("evidence_id"), block


# --- Behavioural core: exercise the real _load_source_cards/_resolve_source ---


def test_resolve_source_never_mutates_pediatric_cds_block():
    """Call the REAL production hydration function
    (``export_service._resolve_source``, the exact function the plan's own
    inline comment at ``export_service.py:655-687`` identifies as where
    SMP-1.4's ``authors``/``doi``/``publisher``/``version`` fields get
    added) against every pediatric_cds-bearing point across the 7 real
    bundles, and prove it never mutates the point's ``pediatric_cds``
    sub-object in place.

    ``_load_source_cards`` returns ``card["points"][eid]`` as a live
    reference into the parsed frontmatter dict (not a copy) -- if
    ``_resolve_source`` (or anything it calls) ever merged the new
    metadata fields onto the point itself, this would catch it as a
    mutation of the SAME object, not just a static shape mismatch.
    """

    paths = FoundryPaths(root=_REPO_ROOT)
    threshold_rank = export_service._sensitivity_rank(
        export_service.resolve_threshold(paths, "client_sensitive")
    )

    n_blocks_checked = 0
    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        rp = export_service.resolve_run_paths(paths, run_id)
        cards = export_service._load_source_cards(rp, run_id=run_id)
        assert cards, f"expected >=1 source card loaded for {run_id}"

        for sid, card in cards.items():
            for eid, point in card["points"].items():
                block = point.get("pediatric_cds")
                if block is None:
                    continue
                n_blocks_checked += 1
                before = copy.deepcopy(block)

                citation = {
                    "source_card_id": sid,
                    "evidence_id": eid,
                    "relation": "supports",
                    "locator": "p.1",
                }
                resolved = export_service._resolve_source(citation, cards, threshold_rank)

                # (1) the point's own pediatric_cds sub-object, the SAME
                # object _resolve_source just read from, must be
                # byte-for-byte unchanged -- no in-place contamination.
                after = point.get("pediatric_cds")
                assert after == before, (
                    f"{run_id}/{sid}#{eid}: pediatric_cds block mutated by "
                    f"_resolve_source() (before={before!r}, after={after!r})"
                )
                # Belt-and-suspenders: even if it HAD changed, it must not
                # have gained one of the plan's new keys.
                hits = _forbidden_keys_in_block(after)
                assert not hits, f"{run_id}/{sid}#{eid}: forbidden key(s) after mutation: {hits}"

                # (2) the resolved/exported source object _resolve_source
                # returns must never surface a pediatric_cds key at all
                # (by design it only copies title/source_type/url/authors/
                # doi/publisher/version/trust/usage/.../quote -- never the
                # point dict wholesale).
                resolved_subtrees = _pediatric_cds_subtrees(resolved)
                assert not resolved_subtrees, (
                    f"{run_id}/{sid}#{eid}: _resolve_source() output unexpectedly "
                    f"surfaced a pediatric_cds key: {resolved_subtrees}"
                )

    # Non-vacuity guard on THIS test's own coverage (mirrors the redteam
    # test's "n_blocks > 0" sanity check): if bundle discovery regresses to
    # finding zero blocks, fail loudly rather than reporting a silent pass.
    assert n_blocks_checked > 0, "expected >=1 pediatric_cds block exercised via _resolve_source"


def test_export_run_pediatric_cds_namespace_stays_clean():
    """End-to-end behavioural check: run the REAL full export pipeline
    (``export_service.export_run``, which internally calls
    ``_load_source_cards`` -> ``_build_claims`` -> ``_resolve_source`` for
    every claim/citation) against each of the 7 real bundles, then walk the
    ENTIRE emitted structure for any subtree rooted at a ``pediatric_cds``
    key and assert none carry a forbidden key.

    ``export_run`` is read-only by its own docstring ("All reads are
    path-derived") -- ``_atomic_write_json`` is reachable only via
    ``export_to_file``/``export_all``, neither called here.
    """

    paths = FoundryPaths(root=_REPO_ROOT)
    n_bundles_checked = 0
    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        exported = export_service.export_run(paths, run_id)
        assert exported is not None, f"export_run() returned None for {run_id}"
        n_bundles_checked += 1

        for subtree_path, subtree in _pediatric_cds_subtrees(exported):
            hits = _forbidden_keys_in_block(subtree, root_label=subtree_path)
            assert not hits, f"{run_id}: forbidden key(s) inside {subtree_path}: {hits}"

    assert n_bundles_checked == 7


def test_export_run_and_resolve_source_never_write_to_the_bundles():
    """Affirmative proof (not just a comment) that exercising the pipeline
    above never mutates the 7 committed bundles on disk: snapshot every
    source card's mtime + exact text before, run the same real calls as the
    two tests above, then re-snapshot and assert byte-for-byte identity."""

    paths = FoundryPaths(root=_REPO_ROOT)
    card_paths: list[Path] = []
    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        sources_dir = _REPO_ROOT / "runs" / run_id / "sources"
        card_paths.extend(sorted(sources_dir.glob("*.md")))
    assert card_paths, "expected >=1 source card across the 7 bundles"

    before = {p: (p.stat().st_mtime_ns, p.read_text(encoding="utf-8")) for p in card_paths}

    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        export_service.export_run(paths, run_id)

    after = {p: (p.stat().st_mtime_ns, p.read_text(encoding="utf-8")) for p in card_paths}
    assert before == after, "one or more pediatric_cds bundle source cards were modified"


# --- On-disk baseline: the blocks already committed carry none of the new keys ---


def test_seven_bundles_pediatric_cds_blocks_carry_no_new_keys():
    """Baseline sanity: every ``pediatric_cds`` block actually committed
    across the 7 bundles is, today, already free of the plan's new keys.
    Supplements (does not replace) the behavioural tests above."""

    n_blocks = 0
    failures: list[str] = []
    for run_id, card_path, evidence_id, block in _iter_bundle_pediatric_cds_blocks():
        n_blocks += 1
        hits = _forbidden_keys_in_block(block)
        if hits:
            rel = card_path.relative_to(_REPO_ROOT)
            failures.append(f"{run_id}:{rel}#{evidence_id}: {hits}")

    assert n_blocks > 0, "expected >=1 pediatric_cds block across the 7 verified bundles"
    assert not failures, f"forbidden key(s) found in committed bundles:\n" + "\n".join(failures)


# --- Non-vacuity proof: the forbidden-key check actually catches contamination ---


def test_forbidden_key_check_is_non_vacuous_for_source_rank_injection():
    """Prove ``_forbidden_keys_in_block`` is not vacuous: inject a
    ``pediatric_cds.source_rank`` key (the plan's own example contamination)
    into an in-memory COPY of a real committed block and confirm the check
    goes RED. No bundle file or source module is touched -- this mutates a
    ``copy.deepcopy`` of the block only.
    """

    real_blocks = list(_iter_bundle_pediatric_cds_blocks())
    assert real_blocks, "expected >=1 real pediatric_cds block to base the injection on"
    _run_id, _card_path, _evidence_id, real_block = real_blocks[0]

    clean = copy.deepcopy(real_block)
    assert _forbidden_keys_in_block(clean) == [], "fixture precondition: real block must start clean"

    contaminated = copy.deepcopy(real_block)
    contaminated["source_rank"] = "high"  # pediatric_cds.source_rank

    hits = _forbidden_keys_in_block(contaminated)
    assert hits == ["pediatric_cds.source_rank"], hits

    with pytest.raises(AssertionError):
        assert not _forbidden_keys_in_block(contaminated), "expected to go RED"


def test_forbidden_key_check_also_catches_nested_trust_source_rank_and_attribution_summary():
    """A second non-vacuity case: the sibling-field / nested-namespace shape
    named in the plan (``trust.source_rank`` nested, and a full
    ``attribution_summary`` mirror) must also be caught, not just a bare
    top-level key."""

    real_blocks = list(_iter_bundle_pediatric_cds_blocks())
    contaminated = copy.deepcopy(real_blocks[0][3])
    contaminated["trust"] = {"source_rank": "high"}
    contaminated["attribution_summary"] = {"attribution_ids": ["attr_1"], "count": 1, "rollups": []}

    hits = _forbidden_keys_in_block(contaminated)
    assert "pediatric_cds.trust.source_rank" in hits
    assert "pediatric_cds.attribution_summary" in hits
    assert "pediatric_cds.attribution_summary.attribution_ids" in hits
    assert "pediatric_cds.attribution_summary.count" in hits
    assert "pediatric_cds.attribution_summary.rollups" in hits


# --- Supplementary static guard (paths existence asserted per repo rule) ----


def test_writer_modules_never_reference_pediatric_cds_literal():
    """Supplementary static guard: none of today's actual writer/emitter
    modules for this plan (M1-M3's ``files_affected``) reference the
    ``pediatric_cds`` literal at all. Implemented as a pure-Python substring
    scan (not a shell ``rg``/``grep`` call), but the repo's rg-AC-path-
    existence rule (ITT ``node_01KYVBG7K191K4BKAZPEP5CRDF``) is honored
    anyway: every target path's existence is asserted before the substring
    check runs, so a renamed/missing module can never read as a silent pass.
    """

    assert len(_WRITER_MODULE_PATHS) > 0
    hits: list[str] = []
    for module_path in _WRITER_MODULE_PATHS:
        assert module_path.is_file(), f"expected writer module at {module_path}"
        text = module_path.read_text(encoding="utf-8")
        if "pediatric_cds" in text:
            hits.append(str(module_path.relative_to(_REPO_ROOT)))

    assert not hits, f"writer module(s) unexpectedly reference 'pediatric_cds': {hits}"
