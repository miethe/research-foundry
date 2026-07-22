"""Static regression guard: no code derives one evidence-taxonomy axis from another.

``schemas/source_assertion.schema.yaml`` defines ``extensions.evidence_taxonomy``
with two REQUIRED, INDEPENDENT enum axes:

  - ``evidence_item_type`` (observed_finding | reference_interval_value | ...)
  - ``judgment_basis``     (measured | derived_from_measured | ...)

and a third, independent axis lives on a sibling schema
(``schemas/rights_record.schema.yaml`` / ``content_reuse_assessment.schema.yaml``):

  - ``component_type``

Per FR-8's "three-axes invariant", these three fields must always be set
*independently* — never computed as a function of one another. This module
walks every ``.py`` file under ``src/research_foundry/`` with the ``ast``
module and flags any function that both:

  1. reads one of the three fields (as a parameter name, an attribute access,
     a dict-key lookup/``.get()``, or a plain variable reference), and
  2. writes a *different* one of the three fields (via assignment, a
     constructor/dict-literal keyword, or a dict-literal key) using an
     expression that contains that read.

A violation looks like this (any of these patterns would fail the guard):

    def infer_judgment_basis(component_type: str) -> str:
        # BAD: judgment_basis assigned from component_type
        judgment_basis = "measured" if component_type == "clinical_value" else "unassessed"
        return judgment_basis

    def build_assertion(evidence_item_type: str) -> dict:
        return {
            # BAD: judgment_basis keyword derived from evidence_item_type
            "judgment_basis": "measured" if evidence_item_type == "observed_finding" else "mixed",
        }

Legitimate code that sets these fields *independently* (e.g. from extractor
output, a CLI flag, or a schema default) is NOT flagged, because the
right-hand side of the assignment/keyword does not reference any of the
*other* two fields.

This is a regression guard, not a perfect derivation-detector: it is
deliberately conservative (a function that reads a field but only logs it,
or that returns a field's own value unchanged, is not a violation) and it
only recognizes assignment-shaped and call/dict-literal-shaped sinks (not,
e.g., cross-function derivations that require call-graph tracing). False
negatives are acceptable; false positives are not — see the module docstring
task instructions for rationale.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# The three independent evidence/rights axes. Any function that reads one of
# these and writes a *different* one from an expression containing the first
# is a derivation violation.
AXIS_FIELDS: frozenset[str] = frozenset(
    {"evidence_item_type", "judgment_basis", "component_type"}
)

SRC_ROOT = Path(__file__).parent.parent / "src" / "research_foundry"


def _field_of_store_target(node: ast.AST) -> str | None:
    """If ``node`` is an assignment target naming one of AXIS_FIELDS, return it."""
    if isinstance(node, ast.Name) and node.id in AXIS_FIELDS:
        return node.id
    if isinstance(node, ast.Attribute) and node.attr in AXIS_FIELDS:
        return node.attr
    if isinstance(node, ast.Subscript):
        sl = node.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str) and sl.value in AXIS_FIELDS:
            return sl.value
    return None


def _fields_referenced_in(expr: ast.AST) -> set[str]:
    """Return every AXIS_FIELDS member referenced (read) anywhere inside ``expr``.

    Recognizes: bare names, attribute access (``obj.field``), dict-key
    lookups/subscripts with a string literal key, and string literals used as
    a ``.get("field")`` argument or dict-literal key.
    """
    found: set[str] = set()
    for n in ast.walk(expr):
        if isinstance(n, ast.Name) and n.id in AXIS_FIELDS:
            found.add(n.id)
        elif isinstance(n, ast.Attribute) and n.attr in AXIS_FIELDS:
            found.add(n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in AXIS_FIELDS:
            # Covers subscript keys (obj["field"]), .get("field") calls, and
            # dict-literal keys — all represented as a Constant string node
            # somewhere in the value's subtree.
            found.add(n.value)
    return found


class _SinkCollector(ast.NodeVisitor):
    """Collects (field, value_expr) sink pairs for a single function's own
    statements — deliberately does NOT descend into nested function/lambda
    bodies, so a nested helper's assignments are never misattributed to the
    enclosing function (and are checked independently when visited on their
    own)."""

    def __init__(self) -> None:
        self.sinks: list[tuple[str, ast.AST]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        return  # stop — do not descend into a nested function

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Lambda(self, node: ast.Lambda) -> None:  # noqa: N802
        return  # stop — do not descend into a lambda body

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        for target in node.targets:
            field = _field_of_store_target(target)
            if field:
                self.sinks.append((field, node.value))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if node.value is not None:
            field = _field_of_store_target(node.target)
            if field:
                self.sinks.append((field, node.value))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        for kw in node.keywords:
            if kw.arg in AXIS_FIELDS:
                self.sinks.append((kw.arg, kw.value))
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:  # noqa: N802
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value in AXIS_FIELDS:
                self.sinks.append((key.value, value))
        self.generic_visit(node)


def _iter_functions(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _find_violations_in_function(
    func: ast.FunctionDef | ast.AsyncFunctionDef, filepath: Path
) -> list[str]:
    """Return human-readable violation strings for a single function."""
    collector = _SinkCollector()
    for stmt in func.body:
        collector.visit(stmt)

    violations: list[str] = []
    for sink_field, value_expr in collector.sinks:
        referenced = _fields_referenced_in(value_expr) - {sink_field}
        offending = referenced & AXIS_FIELDS
        if offending:
            violations.append(
                f"{filepath}:{func.lineno}: function `{func.name}` sets "
                f"`{sink_field}` from an expression referencing "
                f"{sorted(offending)} — the three evidence/rights axes "
                f"(evidence_item_type, judgment_basis, component_type) must "
                f"be set independently, never derived from one another "
                f"(see schemas/source_assertion.schema.yaml FR-8)."
            )
    return violations


def _iter_source_files() -> list[Path]:
    assert SRC_ROOT.is_dir(), f"expected source root at {SRC_ROOT}"
    return sorted(SRC_ROOT.rglob("*.py"))


def test_source_tree_has_python_files() -> None:
    """Sanity check: the scan target exists and is non-empty (guards a silently
    no-op test if SRC_ROOT is ever moved/renamed)."""
    files = _iter_source_files()
    assert len(files) > 10, f"expected many .py files under {SRC_ROOT}, found {len(files)}"


@pytest.mark.parametrize("filepath", _iter_source_files(), ids=lambda p: str(p.relative_to(SRC_ROOT)))
def test_no_cross_axis_derivation(filepath: Path) -> None:
    """No function in this file derives one of the three evidence/rights axis
    fields (evidence_item_type, judgment_basis, component_type) from another.

    A failure here means some function's assignment/keyword-argument/dict-
    literal value for one axis field textually references a *different* axis
    field — i.e. exactly the derivation pattern FR-8 forbids. Fix by setting
    each axis independently (from extractor output, an explicit argument, or
    a schema default) rather than computing it from a sibling axis field.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    violations: list[str] = []
    for func in _iter_functions(tree):
        violations.extend(_find_violations_in_function(func, filepath))

    assert not violations, "\n".join(violations)
