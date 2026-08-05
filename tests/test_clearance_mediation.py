"""Tests for the clearance mediation primitive and chokepoint retrofit (M2).

Proves:
* ``mediate_egress`` is SCOPE-SPECIFIC, not a blanket boolean (paired test).
* Denial is caused by taint ABSENCE, not by the function always denying
  (paired test) — for a governed kind only.
* An ungoverned kind skips the check, which is what keeps every pre-existing
  record (source cards, claims, reports, the 7 pediatric bundles) working.
* ``MediationClearance`` cannot be forged, so a transport demanding proof
  cannot be satisfied by a caller that skipped the check.
* The transport backstop refuses a tainted payload at RUNTIME — deliberately
  not merely under mypy, which does not run in CI in this repo (the only
  workflow is .github/workflows/docs.yml and there is no pre-commit config), so
  a static-only guarantee would be unenforced.
* ``_render_notebooklm_update`` cannot be called without a token.

Synthetic-fixture only: no run-data plane, no network. The registry is built
from a tmp_path YAML so these tests do not depend on the shipped gate states.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.errors import ExitCode
from research_foundry.integrations.base import IntegrationClient
from research_foundry.services import clearance
from research_foundry.services.clearance import (
    ClearanceDenied,
    GateRegistry,
    MediatedPayload,
    MediationClearance,
    assert_payload_mediated,
    mediate_egress,
)

_REGISTRY_YAML = """\
schema_version: "1.0"
applies_to_kinds:
  - source_attribution
gates:
  - gate_id: DEF-1
    blocks_scope: redistribution
    state: open
    summary: Unverified.
    evidence_pointer: docs/x.md
    closed_by: null
"""


@pytest.fixture()
def registry(tmp_path: Path) -> GateRegistry:
    path = tmp_path / "clearance_gates.yaml"
    path.write_text(_REGISTRY_YAML, encoding="utf-8")
    return GateRegistry(path=path)


def _record(*scopes: str) -> dict[str, Any]:
    return {
        "attribution_id": "attr_demo",
        "value": 42,
        "clearance": {
            "schema_version": "1.0",
            "blocked_scopes": list(scopes),
            "stamped_at": "2026-08-03T00:00:00Z",
            "stamped_by": "attribution_fetch.openalex",
            "posture_at_stamp": "dev_test",
            "gate_refs": ["DEF-1"],
        },
    }


# --- scope specificity: the PAIR --------------------------------------------


def test_blocked_scope_is_refused(registry: GateRegistry) -> None:
    with pytest.raises(ClearanceDenied) as exc:
        mediate_egress(
            [_record("redistribution")],
            kind="source_attribution",
            target_scope="redistribution",
            target="notebooklm",
            registry=registry,
        )
    assert "redistribution" in str(exc.value)
    assert exc.value.exit_code == ExitCode.GOVERNANCE


def test_unblocked_scope_is_allowed_for_the_same_record(registry: GateRegistry) -> None:
    """The companion half. Without this, a function that ALWAYS denies passes above.

    Same record, different scope: a redistribution-blocked value is still
    perfectly usable for clinical-reliance purposes, and conflating the two would
    make the whole three-scope taxonomy pointless.
    """

    token = mediate_egress(
        [_record("redistribution")],
        kind="source_attribution",
        target_scope="clinical_reliance",
        target="local-view",
        registry=registry,
    )
    assert isinstance(token, MediationClearance)
    assert token.target_scope == "clinical_reliance"


# --- absence fails closed: the PAIR -----------------------------------------


def test_absent_stamp_is_refused_for_governed_kind(registry: GateRegistry) -> None:
    """Absence means untrusted. A stamp dropped by a projection must not read as clean."""

    with pytest.raises(ClearanceDenied) as exc:
        mediate_egress(
            [{"attribution_id": "attr_demo", "value": 42}],
            kind="source_attribution",
            target_scope="redistribution",
            target="meatywiki",
            registry=registry,
        )
    assert "no usable clearance stamp" in str(exc.value)


def test_empty_scopes_is_denied_same_as_malformed(registry: GateRegistry) -> None:
    """clearance-gates M3 CHANGES_REQUESTED B3: an empty ``blocked_scopes``
    is treated identically to an absent/malformed stamp, not as "explicitly
    unrestricted" (the ORIGINAL M1/M2 design this test replaces). Nothing
    in this read path can tell a genuinely-human-authored empty-set record
    apart from a caller that emptied a real stamp's list in-process a
    moment before mediation (e.g. mutating a ``ClearedProviderFetchResult``
    's ``clearance`` dict in place) -- guard rule 9's monotonicity governs
    on-disk agent WRITES only, not that in-memory window. See
    ``schemas/clearance_taint.schema.yaml``'s ``blocked_scopes`` field for
    the updated contract.

    ``test_unblocked_scope_is_allowed_for_the_same_record`` above remains
    the "not always deny" companion for scope-specificity -- this test is
    no longer paired with an "empty is allowed" counterpart because that
    state no longer exists at the mediation layer.
    """

    with pytest.raises(ClearanceDenied) as exc:
        mediate_egress(
            [_record()],
            kind="source_attribution",
            target_scope="redistribution",
            target="meatywiki",
            registry=registry,
        )
    assert "no usable clearance stamp" in str(exc.value)


@pytest.mark.parametrize(
    "malformed",
    [
        {"clearance": None},
        {"clearance": "redistribution"},
        {"clearance": {}},
        {"clearance": {"blocked_scopes": "redistribution"}},
        {"clearance": {"blocked_scopes": None}},
    ],
)
def test_malformed_stamp_is_refused(registry: GateRegistry, malformed: dict[str, Any]) -> None:
    """A present-but-unusable stamp is refused, never read as unrestricted."""

    with pytest.raises(ClearanceDenied):
        mediate_egress(
            [{"attribution_id": "a", **malformed}],
            kind="source_attribution",
            target_scope="redistribution",
            target="arc",
            registry=registry,
        )


# --- ungoverned kinds skip the check (backward compatibility) ----------------


def test_ungoverned_kind_skips_check_entirely(registry: GateRegistry) -> None:
    """source_card is NOT in applies_to_kinds, so an unstamped card is fine.

    This is the mechanism that keeps the 7 committed pediatric bundles and every
    other pre-existing record working: they predate clearance and can never carry
    a stamp, so demanding one would be a correctness regression dressed up as
    safety.
    """

    token = mediate_egress(
        [{"source_card_id": "sc_demo"}],
        kind="source_card",
        target_scope="redistribution",
        target="notebooklm",
        registry=registry,
    )
    assert token.record_count == 1


def test_governed_kind_with_no_records_is_allowed(registry: GateRegistry) -> None:
    token = mediate_egress(
        [], kind="source_attribution", target_scope="redistribution",
        target="notebooklm", registry=registry,
    )
    assert token.record_count == 0


# --- acquisition scope refuses everything ------------------------------------


def test_acquisition_blocked_record_is_refused_for_any_scope(registry: GateRegistry) -> None:
    """A record that should never have been fetched must not travel anywhere."""

    for scope in ("redistribution", "clinical_reliance"):
        with pytest.raises(ClearanceDenied) as exc:
            mediate_egress(
                [_record("acquisition")],
                kind="source_attribution",
                target_scope=scope,
                target="anywhere",
                registry=registry,
            )
        assert "acquisition" in str(exc.value)


def test_unknown_target_scope_raises(registry: GateRegistry) -> None:
    with pytest.raises(clearance.ClearanceConfigError):
        mediate_egress(
            [_record()], kind="source_attribution", target_scope="nonsense",
            target="x", registry=registry,
        )


# --- the token is unforgeable ------------------------------------------------


def test_mediation_clearance_cannot_be_constructed_directly() -> None:
    """Without this, a caller could fabricate proof and skip the check entirely."""

    with pytest.raises(ClearanceDenied) as exc:
        MediationClearance(target_scope="redistribution", target="notebooklm", record_count=1)
    assert "cannot be constructed directly" in str(exc.value)


def test_mediation_clearance_cannot_be_forged_with_a_guessed_sentinel() -> None:
    with pytest.raises(ClearanceDenied):
        MediationClearance(
            target_scope="redistribution", target="x", record_count=1, _sentinel=object()
        )


def test_mediated_payload_requires_a_real_clearance() -> None:
    with pytest.raises(ClearanceDenied):
        MediatedPayload(payload={"a": 1}, clearance="not-a-token")  # type: ignore[arg-type]


def test_mediated_payload_round_trips(registry: GateRegistry) -> None:
    # A record stamped for a DIFFERENT scope (clinical_reliance) than the
    # one requested (redistribution) -- genuinely stamped and cleared for
    # this scope, unlike `_record()` bare (empty scopes), which B3 now
    # denies for a governed kind (see test_empty_scopes_is_denied_same_as_malformed).
    token = mediate_egress(
        [_record("clinical_reliance")], kind="source_attribution", target_scope="redistribution",
        target="meatywiki", registry=registry,
    )
    wrapped = MediatedPayload(payload={"a": 1}, clearance=token)
    assert wrapped.unwrap() == {"a": 1}


# --- transport backstop: RUNTIME enforcement --------------------------------


def test_backstop_allows_untainted_bare_dict() -> None:
    """Every pre-existing call site passes a bare untainted dict — must keep working."""

    assert assert_payload_mediated({"a": 1}, target="x") == {"a": 1}


def test_backstop_refuses_tainted_bare_dict() -> None:
    with pytest.raises(ClearanceDenied) as exc:
        assert_payload_mediated({"records": [_record("redistribution")]}, target="notebooklm")
    assert "no proof of mediation" in str(exc.value)


def test_backstop_finds_taint_nested_deeply() -> None:
    payload = {"a": {"b": {"c": [{"d": _record("redistribution")}]}}}
    with pytest.raises(ClearanceDenied):
        assert_payload_mediated(payload, target="arc")


def test_backstop_ignores_taint_with_empty_scopes() -> None:
    """A record with no usable stamp (empty ``blocked_scopes``, post-B3) is
    not 'tainted' from the BACKSTOP's narrow point of view either -- there
    is no non-empty scope set for it to find. This is not a statement that
    the record is "cleared" (mediate_egress, the PRIMARY control, now
    refuses it outright for a governed kind); it only means the backstop
    -- which is deliberately a secondary, best-effort scan for a non-empty
    scope list on a post-projection payload -- has nothing to flag here.
    """

    assert assert_payload_mediated({"r": _record()}, target="x") is not None


def test_backstop_accepts_wrapped_payload(registry: GateRegistry) -> None:
    token = mediate_egress(
        [_record("clinical_reliance")], kind="source_attribution", target_scope="redistribution",
        target="meatywiki", registry=registry,
    )
    wrapped = MediatedPayload(payload={"records": [_record("redistribution")]}, clearance=token)
    # Proof present: the backstop defers to the upstream check and unwraps.
    assert assert_payload_mediated(wrapped, target="meatywiki")["records"]


def test_backstop_is_depth_bounded() -> None:
    """A pathological structure must not hang the transport path."""

    node: dict[str, Any] = {}
    cursor = node
    for _ in range(200):
        nxt: dict[str, Any] = {}
        cursor["next"] = nxt
        cursor = nxt
    cursor["r"] = _record("redistribution")
    # Deeper than the bound, so not found — and crucially it RETURNS rather than
    # recursing forever. The bound is a liveness guarantee, not a coverage claim.
    assert assert_payload_mediated(node, target="x") is not None


# --- the retrofit actually bites at the transport ---------------------------


class _Probe(IntegrationClient):
    """Records whether a socket would have been opened."""

    def __init__(self) -> None:
        super().__init__("http://localhost:9999")
        self.sent: list[Any] = []

    def available(self, timeout: float = 2.0) -> bool:
        return True


def test_post_refuses_tainted_payload_at_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC3. Enforcement is RUNTIME, so pytest is the gate — mypy does not run in CI here.

    Also asserts no socket was opened: the refusal must happen before any network
    attempt, otherwise a blocked record has already been transmitted.
    """

    import urllib.request

    opened: list[str] = []

    def _boom(*args: Any, **kwargs: Any) -> Any:
        opened.append("urlopen")
        raise AssertionError("no socket may open for a refused payload")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)

    probe = _Probe()
    with pytest.raises(ClearanceDenied):
        probe._post("/x", {"records": [_record("redistribution")]})
    assert opened == []


def test_patch_refuses_tainted_payload_at_runtime() -> None:
    probe = _Probe()
    with pytest.raises(ClearanceDenied):
        probe._patch("/x", {"records": [_record("redistribution")]})


def test_post_untainted_payload_is_not_refused() -> None:
    """The companion — proves the refusal is caused by taint, not by the retrofit itself.

    The call still degrades to None (nothing is listening on the probe port),
    which is the pre-existing fail-soft contract; the point is that it got PAST
    the clearance check rather than being refused.
    """

    probe = _Probe()
    assert probe._post("/x", {"a": 1}) is None


# --- NotebookLM: the subprocess bypass is gated at its call site ------------


def test_notebooklm_overrides_mirror_the_base_payload_type() -> None:
    """The narrowed `type: ignore` must not be re-broadened.

    NotebookLMClient overrides _post/_patch as dead stubs and does its real work
    through a subprocess, so the transport backstop is unreachable from it. The
    previous blanket `# type: ignore[override]` would have silently swallowed the
    base class's payload-type widening. This asserts the annotations stayed in
    sync so that drift is visible rather than hidden.
    """

    import inspect

    from research_foundry.integrations.notebooklm import NotebookLMClient

    for name in ("_post", "_patch"):
        sig = inspect.signature(getattr(NotebookLMClient, name))
        annotation = str(sig.parameters["payload"].annotation)
        assert "MediatedPayload" in annotation, (
            f"NotebookLMClient.{name} payload annotation drifted from the base class"
        )


def test_render_notebooklm_update_requires_a_token() -> None:
    """The richest egress path in the codebase cannot be invoked without proof."""

    import inspect

    from research_foundry.services.writeback import _render_notebooklm_update

    sig = inspect.signature(_render_notebooklm_update)
    assert "mediation" in sig.parameters
    param = sig.parameters["mediation"]
    assert param.default is inspect.Parameter.empty, "mediation must be REQUIRED"


def test_render_notebooklm_update_rejects_a_non_token() -> None:
    """Passing something that isn't a MediationClearance is refused, not coerced."""

    from research_foundry.services.writeback import _render_notebooklm_update

    with pytest.raises(ClearanceDenied):
        _render_notebooklm_update(
            None, None, bundle_ident="b", ledger={}, requires_review=False,
            mediation="pretend-token",  # type: ignore[arg-type]
        )
