"""Tests for the clearance-gate registry, taint schema, and governance rule 9 (M1).

Proves:
* ``GateRegistry`` REFUSES an unknown/missing/misspelled value rather than
  defaulting — in particular a misspelled ``state`` never silently reads as
  ``open``.
* ``schemas/clearance_taint.schema.yaml`` is load-bearing: an unknown scope in
  ``blocked_scopes`` is rejected by the real validator.
* Governance rule 9 is MONOTONE, proven by a PAIR of tests: a release-shaped
  write is blocked AND a scope-adding write passes. Either test alone would be
  satisfied by a rule that always fires (or never does), so the pair is the
  actual assertion.
* Rule 9's vocabulary does not collide with the human-only rights family.

Synthetic-fixture only for the registry tests; the schema test reads the real
``schemas/`` directory because the schema file itself is the thing under test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.errors import ExitCode
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import clearance
from research_foundry.services.clearance import (
    BLOCKING_SCOPES,
    ClearanceConfigError,
    GateRegistry,
)
from research_foundry.services.governance import GuardContext, guard_check

_VALID_GATE = """\
schema_version: "1.0"
applies_to_kinds:
  - source_attribution
gates:
  - gate_id: DEF-1
    blocks_scope: redistribution
    state: open
    summary: Per-provider license terms unverified.
    evidence_pointer: docs/x.md
    closed_by: null
"""


def _registry(tmp_path: Path, body: str) -> GateRegistry:
    path = tmp_path / "clearance_gates.yaml"
    path.write_text(body, encoding="utf-8")
    return GateRegistry(path=path)


# --- registry: unknown values are refused, never defaulted -------------------


def test_valid_registry_loads(tmp_path: Path) -> None:
    reg = _registry(tmp_path, _VALID_GATE)
    gates = reg.gates()
    assert len(gates) == 1
    assert gates[0].gate_id == "DEF-1"
    assert gates[0].is_open is True
    assert reg.open_scopes() == frozenset({"redistribution"})
    assert reg.governs_kind("source_attribution") is True
    assert reg.governs_kind("source_card") is False


def test_misspelled_state_raises_rather_than_defaulting_to_open(tmp_path: Path) -> None:
    """AC1. The load must REFUSE, not guess.

    A registry that defaulted a misspelled state to ``open`` would be
    indistinguishable from one that read the operator's intent correctly — and
    the same silent default applied to a *closed* gate would silently re-block,
    while applied to an open one it would silently release.
    """

    reg = _registry(tmp_path, _VALID_GATE.replace("state: open", "state: opne"))
    with pytest.raises(ClearanceConfigError) as exc:
        reg.gates()
    assert "unknown state" in str(exc.value)
    assert "opne" in str(exc.value)


def test_missing_state_raises(tmp_path: Path) -> None:
    reg = _registry(tmp_path, _VALID_GATE.replace("    state: open\n", ""))
    with pytest.raises(ClearanceConfigError):
        reg.gates()


def test_unknown_blocks_scope_raises(tmp_path: Path) -> None:
    reg = _registry(tmp_path, _VALID_GATE.replace("blocks_scope: redistribution", "blocks_scope: whatever"))
    with pytest.raises(ClearanceConfigError) as exc:
        reg.gates()
    assert "unknown blocks_scope" in str(exc.value)


def test_missing_registry_file_raises_not_treated_as_no_gates(tmp_path: Path) -> None:
    """Fail-closed: an absent registry is refused, not read as 'nothing is gated'."""

    reg = GateRegistry(path=tmp_path / "does_not_exist.yaml")
    with pytest.raises(ClearanceConfigError) as exc:
        reg.gates()
    assert "fail-closed" in str(exc.value)


def test_duplicate_gate_id_raises(tmp_path: Path) -> None:
    body = _VALID_GATE + """\
  - gate_id: DEF-1
    blocks_scope: acquisition
    state: closed
    summary: Duplicate.
    evidence_pointer: docs/x.md
    closed_by: someone
"""
    reg = _registry(tmp_path, body)
    with pytest.raises(ClearanceConfigError) as exc:
        reg.gates()
    assert "duplicate gate_id" in str(exc.value)


def test_condition_and_severity_keys_are_refused(tmp_path: Path) -> None:
    """The registry is DATA. Executable-looking keys are refused by design.

    config/governance.yaml's ``policy_rules`` carries ``condition:``/``severity:``
    keys that are never parsed — documentation masquerading as enforcement. This
    registry refuses that shape outright so it cannot drift into the same trap.
    """

    body = _VALID_GATE.replace(
        "    closed_by: null\n",
        '    closed_by: null\n    condition: "always"\n    severity: block\n',
    )
    reg = _registry(tmp_path, body)
    with pytest.raises(ClearanceConfigError) as exc:
        reg.gates()
    assert "condition" in str(exc.value)


def test_closed_gate_requires_named_closer(tmp_path: Path) -> None:
    """An anonymous closure is refused — only a named human closes a gate."""

    body = _VALID_GATE.replace("state: open", "state: closed")
    reg = _registry(tmp_path, body)
    with pytest.raises(ClearanceConfigError) as exc:
        reg.gates()
    assert "closed_by" in str(exc.value)


def test_malformed_applies_to_kinds_raises(tmp_path: Path) -> None:
    reg = _registry(tmp_path, _VALID_GATE.replace("  - source_attribution", "  - ''"))
    with pytest.raises(ClearanceConfigError) as exc:
        reg.gates()
    assert "applies_to_kinds" in str(exc.value)


def test_gate_ids_for_scope_rejects_unknown_scope(tmp_path: Path) -> None:
    reg = _registry(tmp_path, _VALID_GATE)
    with pytest.raises(ClearanceConfigError):
        reg.gate_ids_for_scope("not_a_scope")


def test_clearance_config_error_carries_schema_exit_code(tmp_path: Path) -> None:
    reg = GateRegistry(path=tmp_path / "nope.yaml")
    with pytest.raises(ClearanceConfigError) as exc:
        reg.gates()
    assert exc.value.exit_code == ExitCode.SCHEMA


# --- the shipped registry is itself valid ------------------------------------


def test_shipped_registry_loads_and_gates_are_open() -> None:
    """The real config/clearance_gates.yaml parses, and DEF-1/DEF-6 are OPEN.

    Asserting the open state is deliberate: DEF-1 and DEF-6 are legal
    determinations with no code referent, and nothing in this feature closes
    them. A future edit flipping either to ``closed`` should have to change this
    test explicitly.
    """

    reg = GateRegistry(path=distribution_root() / "config" / "clearance_gates.yaml")
    by_id = {g.gate_id: g for g in reg.gates()}
    assert by_id["DEF-1"].state == "open"
    assert by_id["DEF-6"].state == "open"
    assert by_id["DEF-1"].blocks_scope == "redistribution"
    # DEF-2 blocks ACQUISITION, not merely redistribution — the dev/test posture
    # must never be able to open it.
    assert by_id["DEF-2"].blocks_scope == "acquisition"
    assert by_id["CLIN-ATTEST"].blocks_scope == "clinical_reliance"
    # Only source_attribution is governed in M1; pre-existing kinds are excluded
    # so records that can never carry a stamp are not retroactively blocked.
    assert reg.applies_to_kinds() == frozenset({"source_attribution"})


def test_every_shipped_gate_scope_is_in_the_vocabulary() -> None:
    reg = GateRegistry(path=distribution_root() / "config" / "clearance_gates.yaml")
    assert all(g.blocks_scope in BLOCKING_SCOPES for g in reg.gates())


def test_summarize_is_read_only_projection() -> None:
    reg = GateRegistry(path=distribution_root() / "config" / "clearance_gates.yaml")
    out = clearance.summarize(reg)
    assert set(out) == {"registry_path", "applies_to_kinds", "open_scopes", "gates"}
    assert "redistribution" in out["open_scopes"]


# --- taint schema is load-bearing -------------------------------------------


def _valid_taint() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "blocked_scopes": ["redistribution"],
        "stamped_at": "2026-08-03T00:00:00Z",
        "stamped_by": "attribution_fetch.openalex",
        "posture_at_stamp": "dev_test",
        "gate_refs": ["DEF-1"],
    }


def _schema_registry() -> SchemaRegistry:
    return SchemaRegistry(schemas_dir=distribution_root() / "schemas")


def test_valid_taint_passes_schema() -> None:
    result = _schema_registry().validate(_valid_taint(), "clearance_taint")
    assert result.ok, result.errors


def test_unknown_blocked_scope_is_rejected() -> None:
    """AC2. Proves the schema is enforcing, not decorative."""

    instance = _valid_taint() | {"blocked_scopes": ["not_a_real_scope"]}
    result = _schema_registry().validate(instance, "clearance_taint")
    assert not result.ok
    assert any("not_a_real_scope" in e or "enum" in e.lower() for e in result.errors)


def test_taint_rejects_additional_properties() -> None:
    instance = _valid_taint() | {"license_basis": "public_domain"}
    result = _schema_registry().validate(instance, "clearance_taint")
    assert not result.ok, "additionalProperties:false must refuse a smuggled field"


def test_taint_rejects_duplicate_scopes() -> None:
    instance = _valid_taint() | {"blocked_scopes": ["redistribution", "redistribution"]}
    result = _schema_registry().validate(instance, "clearance_taint")
    assert not result.ok, "uniqueItems must refuse duplicates"


def test_taint_rejects_unknown_posture() -> None:
    instance = _valid_taint() | {"posture_at_stamp": "production"}
    result = _schema_registry().validate(instance, "clearance_taint")
    assert not result.ok


@pytest.mark.parametrize("missing", sorted(_valid_taint().keys()))
def test_every_taint_field_is_required(missing: str) -> None:
    instance = {k: v for k, v in _valid_taint().items() if k != missing}
    result = _schema_registry().validate(instance, "clearance_taint")
    assert not result.ok, f"{missing} must be required"


def test_empty_blocked_scopes_is_schema_invalid() -> None:
    """clearance-gates M3 CHANGES_REQUESTED round 2 ("schema and runtime now
    disagree"): ``blocked_scopes`` now requires ``minItems: 1``. Superseded
    design (round 1 and earlier): an empty array was accepted as a legal
    SHAPE on the theory that governance (rule 9), not schema, was the
    ceiling on an agent asserting it. That left a gap — the schema accepted
    a record that ``mediate_egress`` would refuse outright at read time
    (finding B3) — so the shape itself is now tightened to match the
    runtime, at the SAME layer, rather than relying on a downstream check
    to catch what an upstream layer still calls valid.
    """

    instance = _valid_taint() | {"blocked_scopes": []}
    result = _schema_registry().validate(instance, "clearance_taint")
    assert not result.ok
    assert any("blocked_scopes" in e or "minItems" in e.lower() for e in result.errors)


# --- governance rule 9: the MONOTONE pair -----------------------------------


def test_rule9_blocks_release_shaped_write(tmp_path: Path) -> None:
    """AC3a. Asserting the empty set is a release — refused from an agent path."""

    ctx = GuardContext(proposed_field_writes=(("clearance.blocked_scopes", "[]"),))
    result = guard_check(ctx, paths=FoundryPaths(root=tmp_path))
    assert result.passed is False
    assert result.exit_code == ExitCode.GOVERNANCE
    assert any(v.rule_id == "no_agent_cleared_clearance_taint" for v in result.violations)


def test_rule9_allows_scope_adding_write(tmp_path: Path) -> None:
    """AC3b. The companion half — without this, a rule that ALWAYS fires passes AC3a.

    Agent writes are monotone: tightening is legitimate and must not be blocked,
    because the M3 stamping writer is itself an agent-reachable path that adds
    ``redistribution`` to every fetched record.
    """

    ctx = GuardContext(proposed_field_writes=(("clearance.blocked_scopes", "redistribution"),))
    result = guard_check(ctx, paths=FoundryPaths(root=tmp_path))
    assert not any(
        v.rule_id == "no_agent_cleared_clearance_taint" for v in result.violations
    ), "adding a blocked scope must be permitted — the rule is monotone, not a blanket block"


@pytest.mark.parametrize("release_value", ["", "[]", "()", "none", "NULL", " empty ", "unrestricted"])
def test_rule9_blocks_every_release_spelling(tmp_path: Path, release_value: str) -> None:
    ctx = GuardContext(proposed_field_writes=(("clearance.blocked_scopes", release_value),))
    result = guard_check(ctx, paths=FoundryPaths(root=tmp_path))
    assert any(v.rule_id == "no_agent_cleared_clearance_taint" for v in result.violations)


def test_rule9_blocks_agent_closing_a_gate(tmp_path: Path) -> None:
    """Closing a gate is an operator file edit, never a code path."""

    ctx = GuardContext(proposed_field_writes=(("clearance_gate.state", "closed"),))
    result = guard_check(ctx, paths=FoundryPaths(root=tmp_path))
    assert result.exit_code == ExitCode.GOVERNANCE
    assert any(v.rule_id == "no_agent_cleared_clearance_taint" for v in result.violations)


def test_rule9_allows_agent_opening_a_gate(tmp_path: Path) -> None:
    """Opening restricts, so it is permitted — the companion to the close test."""

    ctx = GuardContext(proposed_field_writes=(("clearance_gate.state", "open"),))
    result = guard_check(ctx, paths=FoundryPaths(root=tmp_path))
    assert not any(v.rule_id == "no_agent_cleared_clearance_taint" for v in result.violations)


def test_rule9_blocks_restamping_posture_as_none(tmp_path: Path) -> None:
    """Restamping a dev/test record as 'no posture applied' is retroactive release."""

    ctx = GuardContext(proposed_field_writes=(("clearance.posture_at_stamp", "none"),))
    result = guard_check(ctx, paths=FoundryPaths(root=tmp_path))
    assert any(v.rule_id == "no_agent_cleared_clearance_taint" for v in result.violations)


def test_rule9_ignores_unrelated_fields(tmp_path: Path) -> None:
    ctx = GuardContext(proposed_field_writes=(("some.other.field", "[]"),))
    result = guard_check(ctx, paths=FoundryPaths(root=tmp_path))
    assert not any(v.rule_id == "no_agent_cleared_clearance_taint" for v in result.violations)


# --- rule 9, third axis: applies_to_kinds (the GLOBAL release lever) --------
#
# `governs_kind()` is `kind in applies_to_kinds()`, and when it is False
# `mediate_egress` returns a clean clearance token unconditionally. So dropping
# a kind from config/clearance_gates.yaml releases every stamped record of that
# kind at every chokepoint at once. Same MONOTONE pair discipline as the two
# axes above: a removal must be refused AND an addition must pass, because
# either assertion alone is satisfied by a rule that always (or never) fires.


def _rule9_fired(value: object, tmp_path: Path, *, field: str = "applies_to_kinds") -> bool:
    ctx = GuardContext(proposed_field_writes=((field, value),))
    result = guard_check(ctx, paths=FoundryPaths(root=tmp_path))
    return any(v.rule_id == "no_agent_cleared_clearance_taint" for v in result.violations)


@pytest.mark.parametrize(
    "removal_value",
    [
        [],
        (),
        "",
        "[]",
        "()",
        None,
        ["source_card"],
        "source_card",
        "[source_card, claim]",
        "['source_card']",
        "- source_card\n- claim",
    ],
    ids=[
        "empty-list",
        "empty-tuple",
        "empty-string",
        "empty-list-string",
        "empty-tuple-string",
        "explicit-null",
        "narrowed-list",
        "narrowed-bare-string",
        "narrowed-bracketed",
        "narrowed-quoted",
        "narrowed-yaml-block",
    ],
)
def test_rule9_blocks_narrowing_applies_to_kinds(tmp_path: Path, removal_value: object) -> None:
    """Every rendering that drops ``source_attribution`` must be refused.

    This is the one-line global release the M1 OQ-1 correction describes. The
    predicate cannot diff against a prior value (guard_check is stateless), so
    the direction is pinned against ``_CLEARANCE_REQUIRED_KINDS``, a floor in
    CODE — a proposal missing a required kind is a removal by definition,
    whatever the caller's serialization.
    """

    assert _rule9_fired(removal_value, tmp_path)


@pytest.mark.parametrize(
    "addition_value",
    [
        ["source_attribution"],
        ["source_attribution", "source_card"],
        ("source_card", "source_attribution"),
        "source_attribution",
        "[source_attribution, source_card]",
        "['source_attribution', 'claim']",
        "- source_attribution\n- report",
    ],
)
def test_rule9_allows_widening_applies_to_kinds(tmp_path: Path, addition_value: object) -> None:
    """The companion half — without it, a rule that ALWAYS fires passes the pair above.

    Adding a kind WIDENS what clearance governs, which is the tightening
    direction for this field, so it must not be blocked. Restating the current
    set unchanged must also pass, or every honest registry rewrite becomes a
    governance violation.
    """

    assert not _rule9_fired(addition_value, tmp_path), (
        "widening (or restating) applies_to_kinds must be permitted — the rule is "
        "monotone, not a blanket block on the field"
    )


@pytest.mark.parametrize(
    "field",
    ["applies_to_kinds", "clearance.applies_to_kinds", "clearance_registry.applies_to_kinds"],
)
def test_rule9_covers_every_applies_to_kinds_spelling(tmp_path: Path, field: str) -> None:
    """A spelling the tuple misses is a silent no-op on this field's ONLY control.

    Unlike ``blocked_scopes`` there is no schema to normalize the key, so the
    alias set is load-bearing rather than decorative: proven by checking the
    monotone pair holds under each spelling, not merely that the block fires.
    """

    assert _rule9_fired([], tmp_path, field=field)
    assert not _rule9_fired(["source_attribution"], tmp_path, field=field)


def test_applies_to_kinds_field_names_are_registered_in_both_tuples() -> None:
    """The alias tuple is a manual SUBSET of the governed tuple (rule 8's shape).

    ``_ATTRIBUTION_GOVERNED_FIELDS`` duplicates entries from
    ``_RIGHTS_GOVERNED_FIELDS`` the same way, so this follows the established
    convention rather than deriving one from the other. The cost of manual
    duplication is drift — a spelling added to the alias tuple but not to
    ``_CLEARANCE_GOVERNED_FIELDS`` is never reached by rule 9's loop at all, and
    the predicate would look correct in isolation. This test is the fence, and
    it also pins the parametrize list above to the real tuple.
    """

    from research_foundry.services import governance as gov

    assert set(gov._CLEARANCE_APPLIES_TO_KINDS_FIELDS) <= set(gov._CLEARANCE_GOVERNED_FIELDS), (
        "a spelling in the alias tuple but not in _CLEARANCE_GOVERNED_FIELDS is "
        "unreachable — rule 9 only evaluates fields in the governed tuple"
    )
    assert set(gov._CLEARANCE_APPLIES_TO_KINDS_FIELDS) == {
        f for f in gov._CLEARANCE_GOVERNED_FIELDS if f.endswith("applies_to_kinds")
    }


@pytest.mark.parametrize("junk_value", [True, 0, 1, {"source_attribution": True}, [1, 2], object()])
def test_rule9_fails_closed_on_uninterpretable_applies_to_kinds(
    tmp_path: Path, junk_value: object
) -> None:
    """This field has no schema backstop, so an unparseable proposal is REFUSED.

    Deliberately opposite to the other three clearance fields, whose predicate
    defers on a non-string because clearance_taint.schema.yaml's enum +
    ``additionalProperties: false`` is their real control. Nothing validates a
    narrowed ``applies_to_kinds`` except this rule (``GateRegistry._load`` only
    checks list-of-non-empty-strings), so deferring here would BE the hole.
    """

    assert _rule9_fired(junk_value, tmp_path)


def test_clearance_required_kinds_covers_the_shipped_registry() -> None:
    """DRIFT GUARD: a kind in the real registry but not in the floor is unguarded.

    ``_CLEARANCE_REQUIRED_KINDS`` is hardcoded on purpose — deriving it from
    ``config/clearance_gates.yaml`` would be circular, since that file is exactly
    what the release lever edits. The cost of hardcoding is drift, so this test
    is the mechanism that converts drift into a red suite: add a kind to the
    registry and you must add it to the floor, or removal of that new kind
    silently stops being a rule-9 violation.

    Corollary, and the intended ratchet: an operator who genuinely wants to
    narrow governance must edit CODE (and this test), which is a reviewed
    change, rather than one line of YAML.
    """

    from research_foundry.services import governance as gov

    registry_path = distribution_root() / "config" / clearance.REGISTRY_FILENAME
    shipped = GateRegistry(registry_path).applies_to_kinds()
    assert shipped, "registry must govern at least one kind"
    assert shipped <= gov._CLEARANCE_REQUIRED_KINDS, (
        f"kinds governed by the shipped registry but absent from the code-level floor: "
        f"{sorted(shipped - gov._CLEARANCE_REQUIRED_KINDS)} — removal of these is NOT a "
        f"rule-9 violation until they are added to _CLEARANCE_REQUIRED_KINDS"
    )


def test_rule9_state_axis_is_unchanged_by_the_applies_to_kinds_addition(tmp_path: Path) -> None:
    """Regression fence: the new field must not perturb the pre-existing axes.

    The applies_to_kinds branch runs BEFORE the ``isinstance(value, str)`` guard,
    so it is the one edit that could plausibly change how the other three fields
    evaluate. Asserted here as a pair per field rather than trusting the branch
    order by inspection.
    """

    assert _rule9_fired("closed", tmp_path, field="clearance_gate.state")
    assert not _rule9_fired("open", tmp_path, field="clearance_gate.state")
    assert _rule9_fired("[]", tmp_path, field="clearance.blocked_scopes")
    assert not _rule9_fired("redistribution", tmp_path, field="clearance.blocked_scopes")
    assert _rule9_fired("none", tmp_path, field="clearance.posture_at_stamp")
    assert not _rule9_fired("dev_test", tmp_path, field="clearance.posture_at_stamp")
    # A non-string on a taint field still DEFERS (returns False) — the
    # fail-closed behaviour is scoped to applies_to_kinds alone.
    assert not _rule9_fired([], tmp_path, field="clearance.blocked_scopes")


def test_clearance_vocabulary_does_not_collide_with_rights_family(tmp_path: Path) -> None:
    """Clearance must not reuse the human-only rights literals.

    ADR Invariant 1 reserves ``CLEARED_*``/``counsel_approved``/``attested`` for
    humans. If clearance borrowed them, the M3 stamping writer — a legitimate
    agent path — would be emitting a token the rights guards exist to refuse,
    and rule 7 would fire on honest work.
    """

    from research_foundry.services import governance as gov

    assert not (set(gov._CLEARANCE_GOVERNED_FIELDS) & set(gov._RIGHTS_GOVERNED_FIELDS))
    for value in gov._CLEARANCE_RELEASE_VALUES | {gov._CLEARANCE_DISALLOWED_GATE_STATE}:
        assert not gov._is_disallowed_rights_value(value), (
            f"{value!r} must not be a rights-family literal"
        )
    # And the reverse: a rights-cleared value on a clearance field is not
    # silently accepted as a legitimate clearance value.
    assert not gov._is_disallowed_clearance_value("clearance.blocked_scopes", "CLEARED_OPEN_LICENSE")
