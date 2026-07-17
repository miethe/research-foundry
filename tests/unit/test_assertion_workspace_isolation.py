"""P1-03: shared workspace-isolation regression harness for assertion-ledger writes.

Proves the contract ``assertion_workspace.py::resolve_or_deny`` and Phase 1's
module docstring establish (AC-1, ``phase-1-foundation.md``):

  (a) a scoped write lands only in its own workspace;
  (b) a write attempt with no usable ``workspace_id`` performs zero writes
      and returns the typed denial from ``resolve_or_deny``;
  (c) a cross-workspace lookup is rejected (returns absence), never a leak.

Reusable-fixture contract
--------------------------
``dual_workspace_registries`` and ``guarded_ingest`` are the shared harness
P2's backfill tests, P3's forward-write tests, and P6's DI-1-scoped audit
MUST reuse rather than re-deriving an equivalent two-workspace
:class:`~research_foundry.services.assertion_registry.AssertionRegistry`
pair (phase-1-foundation.md P1-03: "do not duplicate the fixture per
phase"). Import them directly into a new test module -- pytest discovers an
imported fixture function in the importing module's namespace, no
``conftest.py`` promotion or ``pytest_plugins`` wiring required::

    from tests.unit.test_assertion_workspace_isolation import (
        WORKSPACE_ALPHA,
        WORKSPACE_BRAVO,
        dual_workspace_registries,
        guarded_ingest,
    )

    def test_p2_backfill_is_workspace_confined(dual_workspace_registries):
        resolution = resolve_or_deny(my_backfill_workspace_id)
        guarded_ingest(dual_workspace_registries, resolution, source_key=..., content=...)
        ...
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.services.assertion_workspace import (
    REASON_WORKSPACE_CONTEXT_MISSING,
    REASON_WORKSPACE_ID_RESOLVED,
    WorkspaceWriteResolution,
    resolve_or_deny,
)

RIGHTS = {"sensitivity": "personal", "allowed_for_work_output": True}

WORKSPACE_ALPHA = "workspace-alpha"
WORKSPACE_BRAVO = "workspace-bravo"


@dataclass(frozen=True)
class DualWorkspaceRegistries:
    """Two isolated :class:`AssertionRegistry` instances sharing one foundry root."""

    paths: FoundryPaths
    alpha: AssertionRegistry
    bravo: AssertionRegistry


@pytest.fixture
def dual_workspace_registries(tmp_foundry: FoundryPaths) -> DualWorkspaceRegistries:
    """The P1-P4 shared fixture: two registries, one shared ``FoundryPaths`` root."""

    return DualWorkspaceRegistries(
        paths=tmp_foundry,
        alpha=AssertionRegistry(workspace_id=WORKSPACE_ALPHA, paths=tmp_foundry),
        bravo=AssertionRegistry(workspace_id=WORKSPACE_BRAVO, paths=tmp_foundry),
    )


def guarded_ingest(
    registries: DualWorkspaceRegistries,
    resolution: WorkspaceWriteResolution,
    *,
    source_key: str,
    content: str,
) -> None:
    """The call-site contract every P1/P2/P3/P4 write site must follow.

    Checks ``resolution.allowed`` BEFORE constructing a registry or calling
    ``ingest()`` -- a denied resolution performs literally zero registry
    construction and zero filesystem writes.
    """

    if not resolution.allowed:
        return
    assert resolution.workspace_id is not None
    registry = AssertionRegistry(workspace_id=resolution.workspace_id, paths=registries.paths)
    registry.ingest(source_key, content, allowed_use=RIGHTS)


# ---------------------------------------------------------------------------
# (a) Scoped write lands only in its own workspace.
# ---------------------------------------------------------------------------


def test_scoped_write_lands_only_in_its_own_workspace(
    dual_workspace_registries: DualWorkspaceRegistries,
) -> None:
    resolution = resolve_or_deny(WORKSPACE_ALPHA)

    assert resolution.allowed is True
    assert resolution.workspace_id == WORKSPACE_ALPHA
    assert resolution.reason == REASON_WORKSPACE_ID_RESOLVED

    guarded_ingest(dual_workspace_registries, resolution, source_key="paper:1", content="Alpha-only text.")

    assert dual_workspace_registries.alpha.root.exists()
    assert not dual_workspace_registries.bravo.root.exists()
    matches = dual_workspace_registries.alpha.find_exact_passages("paper:1", "Alpha-only text.")
    assert len(matches) == 1


# ---------------------------------------------------------------------------
# (b) Absent workspace id -> zero writes, typed denial.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_workspace_id", [None, "", "   ", "\t\n", " "])
def test_absent_workspace_id_performs_zero_writes_and_returns_typed_denial(
    dual_workspace_registries: DualWorkspaceRegistries,
    bad_workspace_id: str | None,
) -> None:
    resolution = resolve_or_deny(bad_workspace_id)

    assert isinstance(resolution, WorkspaceWriteResolution)
    assert resolution.allowed is False
    assert resolution.workspace_id is None
    assert resolution.reason == REASON_WORKSPACE_CONTEXT_MISSING

    guarded_ingest(dual_workspace_registries, resolution, source_key="paper:1", content="Should never land.")

    assert not dual_workspace_registries.alpha.root.exists()
    assert not dual_workspace_registries.bravo.root.exists()


def test_resolve_or_deny_rejects_non_string_input_without_raising() -> None:
    """A non-``str`` input (e.g. accidental ``int``/``0``) must deny, never raise."""

    resolution = resolve_or_deny(0)  # type: ignore[arg-type]

    assert resolution.allowed is False
    assert resolution.reason == REASON_WORKSPACE_CONTEXT_MISSING


def test_denied_resolution_construction_is_rejected() -> None:
    """The dataclass's own invariant: a denial can never carry a workspace_id."""

    with pytest.raises(ValueError):
        WorkspaceWriteResolution(allowed=False, workspace_id="workspace-a", reason="bad")


def test_allowed_resolution_construction_requires_a_workspace_id() -> None:
    """The dataclass's own invariant: an allow can never carry an empty workspace_id."""

    with pytest.raises(ValueError):
        WorkspaceWriteResolution(allowed=True, workspace_id=None, reason="bad")


def test_allowed_resolution_construction_rejects_whitespace_only_workspace_id() -> None:
    """The dataclass's own invariant: an allow can never carry a whitespace-only
    workspace_id -- truthiness alone is not enough, ``"   "`` is truthy but blank."""

    with pytest.raises(ValueError):
        WorkspaceWriteResolution(allowed=True, workspace_id="   ", reason="x")


def test_resolve_or_deny_strips_surrounding_whitespace() -> None:
    """``" default "`` and ``"default"`` must resolve to the same workspace root --
    the pass-through is stripped, not raw, so padding can't fragment workspaces."""

    resolution = resolve_or_deny("  default  ")

    assert resolution.allowed is True
    assert resolution.workspace_id == "default"
    assert resolution.reason == REASON_WORKSPACE_ID_RESOLVED


# ---------------------------------------------------------------------------
# (c) Cross-workspace attempt is rejected, not leaked.
# ---------------------------------------------------------------------------


def test_cross_workspace_lookup_is_rejected_not_leaked(
    dual_workspace_registries: DualWorkspaceRegistries,
) -> None:
    alpha_resolution = resolve_or_deny(WORKSPACE_ALPHA)
    guarded_ingest(dual_workspace_registries, alpha_resolution, source_key="paper:1", content="Alpha secret text.")

    # Bravo's own registry -- scoped to a different workspace_id -- must not
    # find alpha's content via any lookup path. This is a plain empty/absent
    # result, not a raised denial exception: matches the "same absence" idiom
    # `assertion_impact.py` documents for cross-workspace reads (no
    # membership-oracle leak via a differently shaped response).
    cross_workspace_matches = dual_workspace_registries.bravo.find_exact_passages(
        "paper:1", "Alpha secret text."
    )

    assert cross_workspace_matches == ()
    assert dual_workspace_registries.bravo.root.exists() is False


def test_cross_workspace_registries_never_share_a_root_or_key(
    dual_workspace_registries: DualWorkspaceRegistries,
) -> None:
    assert dual_workspace_registries.alpha.root != dual_workspace_registries.bravo.root
    assert dual_workspace_registries.alpha.workspace_key != dual_workspace_registries.bravo.workspace_key


def test_writing_to_both_workspaces_keeps_each_confined(
    dual_workspace_registries: DualWorkspaceRegistries,
) -> None:
    """Both workspaces can legitimately hold the same source_key without collision."""

    alpha_resolution = resolve_or_deny(WORKSPACE_ALPHA)
    bravo_resolution = resolve_or_deny(WORKSPACE_BRAVO)

    guarded_ingest(dual_workspace_registries, alpha_resolution, source_key="paper:1", content="Alpha text.")
    guarded_ingest(dual_workspace_registries, bravo_resolution, source_key="paper:1", content="Bravo text.")

    assert dual_workspace_registries.alpha.find_exact_passages("paper:1", "Alpha text.")
    assert not dual_workspace_registries.alpha.find_exact_passages("paper:1", "Bravo text.")
    assert dual_workspace_registries.bravo.find_exact_passages("paper:1", "Bravo text.")
    assert not dual_workspace_registries.bravo.find_exact_passages("paper:1", "Alpha text.")
