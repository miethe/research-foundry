"""Guard: ``services.attribution_fetch.stamp_source_card`` stays the ONLY
write path for the ``clearance`` taint key on a source card's frontmatter.

Why this guard exists (and why the zero-caller state below is intentional,
not a bug)
----------------------------------------------------------------------------
``stamp_source_card`` (``src/research_foundry/services/attribution_fetch/
__init__.py``) is the single sanctioned mechanism for writing a ``clearance``
taint block onto a source card. As of this writing it has **zero production
callers** — deliberately. ``ClearedProviderFetchResult.to_record()``'s own
docstring names the reason: merging an acquired provider *value* onto an
existing source card is "a separate, later concern" that this package does
not implement. Stamping a card's ``clearance`` block before the provider
data that block describes has actually landed on that card would assert a
governance fact (`this card carries acquired-under-posture X data`) that
isn't true yet. Wiring a caller is deferred until that value -> source-card
merge path exists; when it lands, it will call ``stamp_source_card`` (never
duplicate its logic).

This test does not (and must not) add that caller. It exists to make the
deferral safe: so a future contributor cannot quietly add a *second* module
that writes the taint key directly (bypassing the merge/validation/
type-gating logic centralized in ``stamp_source_card``) without this test
failing and naming the offending module.

Detection is fail-CLOSED by construction: it matches ANY subscript
assignment whose key resolves to the taint key, regardless of what the base
mapping expression is named (``meta``, ``metadata``, ``card_meta``, ``fm``,
``front``, or anything else). An earlier revision of this guard restricted
detection to a fixed set of "frontmatter-looking" base variable names
(``{"meta", "metadata"}``) to exclude ``export_service.py``'s non-persisting
projection write -- that filter was a sibling-name bypass: any write using a
differently-named base variable (``card_meta["clearance"] = ...``) passed
silently, and the guard's own mutation test only ever exercised the
allowed-by-construction ``meta[...]`` shape, so it never actually proved the
bypass was closed. The exclusion for ``export_service.py`` now lives in
``_ALLOWED_TAINT_WRITE_SITES`` below -- an explicit, reasoned, per-module
allowlist -- rather than in what the detector is capable of seeing at all.

Conventions mirrored from ``tests/test_pediatric_namespace_containment.py``
(``test_writer_modules_never_reference_pediatric_cds_literal``):

* Pure-Python AST/substring scan — never a shell ``rg``/``grep`` subprocess.
* Every target path's existence is asserted with ``.is_file()`` BEFORE it is
  scanned, so a renamed or moved module can never read as a silent pass.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from research_foundry.services import clearance
from research_foundry.services.attribution_fetch import stamp_source_card

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src" / "research_foundry"

#: Explicit, per-module allowlist of modules the detector below is permitted
#: to find a clearance-taint subscript-write in, each with a written reason.
#: Adding an entry here is a visible, deliberate edit -- there is no filter
#: elsewhere (no base-variable-name allowlist, no line-number allowlist) that
#: can widen what this guard tolerates. A module hit that is NOT a key in
#: this dict is an unconditional failure naming that module.
_ALLOWED_TAINT_WRITE_SITES: dict[str, str] = {
    "services/attribution_fetch/__init__.py": (
        "the sanctioned writer (ADR Invariant 4, adr-rights-entity-model.md): "
        "stamp_source_card is the single mechanism that may persist a "
        "clearance taint onto a source card's on-disk frontmatter."
    ),
    "services/export_service.py": (
        "non-persisting outward projection (_resolve_source's "
        "resolved[\"clearance\"] = stamp, clearance-gates-v1 M5): propagates "
        "an ALREADY-EXISTING stamp read off a card's frontmatter into a "
        "returned, transient dict for downstream read paths -- it never "
        "writes a card and never originates a stamp. See that call site's "
        "own inline comment for why the key must not be dropped there."
    ),
}

assert _ALLOWED_TAINT_WRITE_SITES, "the allowlist must name at least the sanctioned writer"

#: The taint key this guard hunts for, as both the named constant it should
#: be referenced through and the raw literal a contributor might use instead
#: (bypassing the constant). ``clearance.TAINT_KEY`` is re-asserted equal to
#: the literal below so the two detection modes can never silently diverge.
_TAINT_KEY_CONST_NAME = "TAINT_KEY"
_TAINT_KEY_LITERAL = "clearance"

assert clearance.TAINT_KEY == _TAINT_KEY_LITERAL, (
    "clearance.TAINT_KEY no longer equals the literal this guard hunts for -- "
    "update _TAINT_KEY_LITERAL (and re-derive the guard) before trusting it."
)


def _is_taint_key_expr(node: ast.AST) -> bool:
    """True if *node* (a subscript key expression) names the taint key.

    Matches three shapes a writer could use: ``x[TAINT_KEY]`` (bare name
    import), ``x[clearance.TAINT_KEY]`` (attribute access), and
    ``x["clearance"]`` (the raw literal, bypassing the constant entirely --
    still caught so a contributor cannot dodge the guard just by not
    importing the name). Deliberately indifferent to what ``x`` is named or
    shaped -- see the module docstring for why a base-expression filter is
    exactly the bypass this guard must not have.
    """

    if isinstance(node, ast.Name) and node.id == _TAINT_KEY_CONST_NAME:
        return True
    if isinstance(node, ast.Attribute) and node.attr == _TAINT_KEY_CONST_NAME:
        return True
    if isinstance(node, ast.Constant) and node.value == _TAINT_KEY_LITERAL:
        return True
    return False


def _subscript_targets(target: ast.AST) -> list[ast.Subscript]:
    """Flatten an assignment target into the ``Subscript`` nodes within it.

    Handles the common case (a bare ``Subscript`` target) and tuple/list
    unpacking targets (``a[k], b[k2] = ...``), which is the only other shape
    that can appear as an assignment target in Python's grammar.
    """

    if isinstance(target, ast.Subscript):
        return [target]
    if isinstance(target, (ast.Tuple, ast.List)):
        out: list[ast.Subscript] = []
        for elt in target.elts:
            out.extend(_subscript_targets(elt))
        return out
    return []


def _taint_key_write_lines(source: str) -> list[int]:
    """Return the 1-indexed line numbers of every taint-key subscript WRITE
    in *source* (``Assign`` and ``AugAssign`` targets only -- a read like
    ``meta.get(TAINT_KEY)`` never appears as an assignment target, so it is
    structurally excluded, not merely unmatched by these node types).

    Matches regardless of the subscripted base expression's name or shape --
    ``meta[...]``, ``card_meta[...]``, ``self._fm[...]``, and
    ``some_call()[...]`` are all in scope. Only the KEY expression is
    inspected; narrowing by base-name was tried and rejected (see module
    docstring) as a bypass surface.
    """

    tree = ast.parse(source)
    hits: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            for sub in _subscript_targets(target):
                if _is_taint_key_expr(sub.slice):
                    hits.append(sub.lineno)
    return hits


def _iter_source_files():
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        yield path


def _scan_all_modules() -> dict[str, list[int]]:
    """Return ``{module_rel_path: [lineno, ...]}`` for every module under
    ``_SRC_ROOT`` that contains >=1 detected taint-key subscript write,
    regardless of whether that module is allowlisted. Callers decide what to
    do with allowlisted vs. non-allowlisted hits -- this function reports
    ground truth only.
    """

    hits_by_module: dict[str, list[int]] = {}
    for module_path in _iter_source_files():
        assert module_path.is_file(), f"expected source module at {module_path}"
        rel = module_path.relative_to(_SRC_ROOT).as_posix()
        text = module_path.read_text(encoding="utf-8")
        lines = _taint_key_write_lines(text)
        if lines:
            hits_by_module[rel] = lines
    return hits_by_module


def test_only_allowlisted_modules_write_the_taint_key():
    """Across every module under ``src/research_foundry``, a clearance-taint
    subscript write is tolerated ONLY in a module named in
    ``_ALLOWED_TAINT_WRITE_SITES``. Any other hit names its module and
    line(s) in the failure message, per this repo's rg-AC-path-existence
    convention, and tells the offender exactly which allowlist (and written
    reason) it needs to justify itself against.
    """

    hits_by_module = _scan_all_modules()
    assert hits_by_module, f"expected to detect >=1 clearance-taint write under {_SRC_ROOT}"

    offenders = {
        module: lines
        for module, lines in hits_by_module.items()
        if module not in _ALLOWED_TAINT_WRITE_SITES
    }
    assert not offenders, (
        "found a clearance-taint write path in a module NOT present in "
        f"_ALLOWED_TAINT_WRITE_SITES ({sorted(_ALLOWED_TAINT_WRITE_SITES)}): "
        f"{offenders}. stamp_source_card is the single sanctioned mechanism "
        "for persisting a clearance taint onto a card -- either route the "
        "new write through it, or (only if it is a non-persisting read/"
        "propagation site like export_service.py's) add a reasoned entry to "
        "_ALLOWED_TAINT_WRITE_SITES explaining why it is not a second writer."
    )


def test_the_sanctioned_writer_is_detected_non_vacuously():
    """Pin the detector against the one write it is SUPPOSED to find and
    ENFORCE (not merely allowlist away).

    Without this assertion, a future refactor of ``stamp_source_card`` (e.g.
    renaming ``TAINT_KEY``, switching to ``setdefault``, or moving the write
    behind a helper) could make the scan above stop matching ANYTHING and
    still pass vacuously -- an empty offenders dict is indistinguishable from
    "no offenders" and "detector is dead" unless something asserts the
    detector still fires on ground truth.
    """

    module_path = _SRC_ROOT / "services" / "attribution_fetch" / "__init__.py"
    assert module_path.is_file(), f"expected the sanctioned writer at {module_path}"
    text = module_path.read_text(encoding="utf-8")
    hits = _taint_key_write_lines(text)
    assert hits, (
        f"expected >=1 detected clearance-taint write in {module_path}, found none -- "
        "the detector no longer matches the known write in stamp_source_card. "
        "This guard is only meaningful while it can prove a positive."
    )


def test_the_allowlisted_projection_site_is_detected_not_merely_unseen():
    """Prove the allowlist is doing the suppressing for export_service.py --
    not the detector failing to see that site at all.

    If the detector ever stopped matching ``export_service.py``'s
    ``resolved["clearance"] = stamp`` (e.g. because a refactor changed its
    shape to something outside what ``_taint_key_write_lines`` recognizes),
    ``test_only_allowlisted_modules_write_the_taint_key`` would stay green
    for the wrong reason: not because the site is legitimately allowlisted,
    but because the guard can no longer see it to allowlist it. That would
    silently narrow this guard's real coverage. This test fails loudly
    instead.
    """

    module_path = _SRC_ROOT / "services" / "export_service.py"
    assert module_path.is_file(), f"expected the allowlisted projection module at {module_path}"
    assert "services/export_service.py" in _ALLOWED_TAINT_WRITE_SITES, (
        "export_service.py's allowlist entry was removed from "
        "_ALLOWED_TAINT_WRITE_SITES -- this test's premise no longer holds; "
        "update both together."
    )
    text = module_path.read_text(encoding="utf-8")
    hits = _taint_key_write_lines(text)
    assert hits, (
        f"expected >=1 detected clearance-taint write in {module_path} (the "
        "known non-persisting projection site), found none -- the detector "
        "no longer sees the site this guard's allowlist exempts, which means "
        "the allowlist entry is currently doing NOTHING (a vacuous "
        "exemption), not suppressing a real, seen hit."
    )


@pytest.mark.parametrize(
    "bad_result",
    [
        {"clearance": {"blocked_scopes": ["dev_test_unverified_provider_terms"]}},
        None,
        "not-a-result",
    ],
)
def test_type_gate_rejects_anything_that_is_not_a_cleared_result(
    tmp_path: Path, bad_result: Any
) -> None:
    """``stamp_source_card`` refuses a hand-assembled taint before any write.

    A dict shaped like ``result.clearance`` (or any other non-
    ``ClearedProviderFetchResult`` value) must raise ``TypeError`` -- the
    whole point of the signature is that the only stamp reachable through
    this function is one ``stamp_taint`` already produced at real fetch
    time, never one a caller assembled by hand.
    """

    card_path = tmp_path / "card.md"
    card_path.write_text("---\ntitle: x\n---\nbody\n", encoding="utf-8")
    with pytest.raises(TypeError):
        stamp_source_card(card_path, bad_result)  # type: ignore[arg-type]

    # Refusing before any write means the card is untouched.
    assert card_path.read_text(encoding="utf-8") == "---\ntitle: x\n---\nbody\n"
