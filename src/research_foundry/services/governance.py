"""Governance guard service (spec §7.1/§7.2) — ``rf guard``.

Deterministic, network-free enforcement of the non-negotiable policy rules.
Loads ``config/governance.yaml`` (key_profiles + policy_rules + secret_patterns)
via :class:`FoundryConfig` and falls back to built-ins when the config is absent.

The guard never prints — it returns a frozen :class:`GuardResult` carrying the
exit code so the CLI/hooks render and exit. Exit codes follow the contract:
``0`` ok, ``3`` block, ``7`` require_approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import FoundryConfig
from ..errors import ExitCode
from ..ids import now_iso
from ..paths import FoundryPaths
from ..yamlio import append_jsonl

# --- Sensitivity classes ---------------------------------------------------

_PERSONAL_SENSITIVITIES = {"public", "personal"}
_WORK_SENSITIVITIES = {"work_sensitive", "client_sensitive"}

# --- Rights-clearance write ceiling (FR-23) ---------------------------------
#
# The original 4 fields no agent-writable code path may ever set to a
# "cleared"/"approved"/"attested" value. Enumerated BY NAME — do not infer or
# wildcard this list; future governed fields must be added here explicitly.
#
# M3 (source-metadata-propagation-v1, SMP-3.1/3.2) appends 2 source_attribution
# fields to this SAME tuple rather than starting a second list — and that
# appendage is DEFENCE-IN-DEPTH ONLY. The PRIMARY control for
# source_attribution is a SCHEMA-SHAPE constraint, not a name list:
# schemas/source_attribution.schema.yaml's structural
# `if asserter_type startsWith "third_party_" then retrieval_evidence_ref
# required` (SMP-3.2B) plus source_card.schema.yaml's `attribution_summary`
# mirror being `additionalProperties: false` and genuinely value-free (no
# `value`/`best_value`/etc. property exists on that mirror at all — see its
# own docstring). A name list is structurally blind by construction: it
# catches a write to a NAMED field below, but an agent that instead writes
# an identical disallowed value under an unlisted sibling field name — the
# plan's own example is `trust.third_party_citation_rank` — sails through
# this entire tuple untouched, no matter how many entries it grows to. That
# is exactly why the schema shape, not this tuple, is the control the M3
# Mode-D halt actually gates; see rule 8 below for the concrete miss.
_RIGHTS_GOVERNED_FIELDS: tuple[str, ...] = (
    "rights_record.overall_status",
    "content_reuse_assessment.decision.status",
    "rights_extension.clearance_status",
    "synthesis.attestation.status",
    "source_attribution.asserter_type",
    "source_attribution.license_basis",
)

# Subset of _RIGHTS_GOVERNED_FIELDS added by M3 — used only to scope rule 8's
# violation messaging to the attribution-specific fields. Does not redefine
# or narrow governance: rule 7 below already independently covers these same
# two fields via the shared, extended _RIGHTS_GOVERNED_FIELDS tuple.
_ATTRIBUTION_GOVERNED_FIELDS: tuple[str, ...] = (
    "source_attribution.asserter_type",
    "source_attribution.license_basis",
)

_CLEARED_VALUE_PREFIX = "CLEARED_"
_RIGHTS_DISALLOWED_EXACT_VALUES = {"counsel_approved", "attested"}


def _is_disallowed_rights_value(value: Any) -> bool:
    """True when *value* is a cleared/approved/attested value an agent may not mint."""

    if not isinstance(value, str):
        return False
    if value.startswith(_CLEARED_VALUE_PREFIX):
        return True
    return value in _RIGHTS_DISALLOWED_EXACT_VALUES


# --- Clearance write ceiling (rule 9) ---------------------------------------
#
# Clearance (services/clearance.py, config/clearance_gates.yaml,
# schemas/clearance_taint.schema.yaml) records which USE SCOPES are blocked for
# a record. Two kinds of write must never come from an agent-writable path:
# closing a gate, and releasing a record.
#
# The vocabulary here is deliberately DISTINCT from the rights family above.
# `CLEARED_*`/`counsel_approved`/`attested` are human-only per
# docs/dev/architecture/adr-rights-entity-model.md Invariant 1, and reusing
# those literals for clearance would make this mechanism a laundering path into
# rights state — an agent legitimately stamping a clearance value would be
# writing a token the rights guards are built to refuse.
#
# THE PREDICATE IS MONOTONE, NOT STATEFUL. guard_check is deterministic and
# stateless: it sees proposed (field, value) pairs and never reads the record's
# prior on-disk value, so it cannot ask "did this write remove a scope?".
# Instead the direction of travel is constrained: an agent may ADD a blocked
# scope (tightening) but may never assert the empty set (releasing). That makes
# every agent-reachable clearance write monotonically restrictive, which is a
# stronger and far cheaper guarantee than diffing against prior state — and it
# holds even for a caller that never read the prior value at all.
#
# THE THIRD WRITE: NARROWING `applies_to_kinds` (the global release lever).
# `clearance.py::governs_kind()` is `kind in applies_to_kinds()`, and when it is
# False `mediate_egress` returns a clean clearance token UNCONDITIONALLY. So
# removing a kind from `config/clearance_gates.yaml`'s top-level
# `applies_to_kinds` releases EVERY stamped record of that kind at EVERY egress
# chokepoint, globally, in one line — a strictly larger blast radius than
# releasing one record or closing one gate. That is why it belongs on this rule
# and not in a parallel mechanism.
#
# Narrowing is a REMOVAL, and a stateless predicate cannot see a removal by
# diffing — but it does not have to. The direction is instead pinned against a
# FLOOR that lives in CODE (`_CLEARANCE_REQUIRED_KINDS` below), not on disk: a
# proposed value is refused unless it still contains every required kind.
# Deriving the floor from the registry file would be circular, because the file
# is exactly what the release lever edits. With the floor in code:
#   * dropping a required kind (`[]`, or a narrowed list) -> refused;
#   * adding a kind (superset of the floor)               -> permitted, monotone;
#   * an operator narrowing governance for real            -> must edit CODE (and
#     `test_clearance_required_kinds_covers_the_shipped_registry` fails until they
#     do), i.e. it becomes a reviewed change instead of a one-line config edit.
#
# WHAT THIS RULE STILL MISSES, deliberately, in the same spirit as rule 8's
# note. Three gaps, stated plainly rather than papered over:
#   1. A write to some unlisted sibling field name carrying a release-shaped
#      value sails through this tuple. For `blocked_scopes`/`posture_at_stamp`
#      the PRIMARY control is structural — schemas/clearance_taint.schema.yaml is
#      `additionalProperties: false` with an enum-constrained `blocked_scopes`,
#      and mediate_egress treats an absent or malformed block as blocked rather
#      than clean. This rule is the governance-layer backstop over those.
#   2. For `applies_to_kinds` there is NO schema backstop — the registry file is
#      validated only by `GateRegistry._load` (list-of-non-empty-strings), which
#      accepts a narrowed list happily. This rule is therefore the ONLY control
#      on that field, which is why its predicate fails CLOSED on an
#      uninterpretable value instead of deferring like the other three.
#   3. `applies_to_kinds` remains an OPERATOR-editable release lever by design
#      (config is operator territory, and clearance has no counsel workflow —
#      ADR OQ-RF-6). Guard rule 9 constrains agent-writable CODE paths, not a
#      human's text editor. Nothing here makes a human edit to
#      config/clearance_gates.yaml impossible; it makes an agent-authored one a
#      governance violation.
_CLEARANCE_GOVERNED_FIELDS: tuple[str, ...] = (
    "clearance.blocked_scopes",
    "clearance.posture_at_stamp",
    "clearance_gate.state",
    # The registry-level global release lever. Three spellings are listed
    # because, unlike the record-level fields above, this one has no schema to
    # normalize it and callers serialize `proposed_field_writes` keys
    # inconsistently (see _CLEARANCE_RELEASE_VALUES' own note on that). A
    # spelling this tuple misses is a silent no-op on the only control the
    # field has, so the alias set is cheap insurance, not redundancy.
    "clearance_registry.applies_to_kinds",
    "clearance.applies_to_kinds",
    "applies_to_kinds",
)

#: Field names in :data:`_CLEARANCE_GOVERNED_FIELDS` that address the registry's
#: top-level ``applies_to_kinds`` list. Scoped separately because this field's
#: predicate is a set-containment check against a floor, not a value-literal
#: match, and because it evaluates non-string values (a Python list is the
#: field's natural shape) where the other three deliberately defer.
_CLEARANCE_APPLIES_TO_KINDS_FIELDS: tuple[str, ...] = (
    "clearance_registry.applies_to_kinds",
    "clearance.applies_to_kinds",
    "applies_to_kinds",
)

#: The record kinds clearance must ALWAYS govern — the floor that makes
#: "removal" expressible without prior state. Must stay a superset-or-equal of
#: whatever `config/clearance_gates.yaml` ships (enforced by
#: tests/test_clearance_registry.py::test_clearance_required_kinds_covers_the_shipped_registry).
#: Adding a kind to the registry without adding it here leaves REMOVAL of that
#: new kind unguarded — the drift test exists precisely so that cannot happen
#: quietly.
_CLEARANCE_REQUIRED_KINDS: frozenset[str] = frozenset({"source_attribution"})

#: Values asserting a record carries no blocked scopes. An agent proposing any
#: of these is asserting a release, which only a human editing the record may
#: do. Includes the several ways an empty list renders once stringified into a
#: ``proposed_field_writes`` pair, since callers serialize inconsistently.
_CLEARANCE_RELEASE_VALUES = {"", "[]", "()", "none", "null", "empty", "unrestricted"}

#: The only gate state an agent may not propose. Opening a gate is always safe
#: (it restricts); closing one is the human determination.
_CLEARANCE_DISALLOWED_GATE_STATE = "closed"


def _parse_proposed_kind_set(value: Any) -> frozenset[str] | None:
    """Best-effort parse of a proposed ``applies_to_kinds`` value into a kind set.

    Returns ``None`` — meaning "shape not interpretable" — rather than guessing.
    :func:`_is_disallowed_clearance_value` treats ``None`` as a REFUSAL for this
    field, because an unparseable proposal on the one clearance field with no
    schema backstop must not be waved through.

    Accepts the shapes a ``proposed_field_writes`` pair actually arrives in: a
    real sequence of strings (the field's natural Python shape), or a string
    rendering of one (``"[a, b]"``, ``"a, b"``, ``"- a\\n- b"``, ``"[]"``).
    """

    if value is None:
        # An explicit null is "no kinds governed" — the maximal release. It
        # parses cleanly to the empty set and is then refused by the floor
        # check, rather than being called uninterpretable.
        return frozenset()
    if isinstance(value, (list, tuple, set, frozenset)):
        kinds: list[str] = []
        for entry in value:
            if not isinstance(entry, str):
                return None
            cleaned = entry.strip().strip("\"'").strip()
            if cleaned:
                kinds.append(cleaned)
        return frozenset(kinds)
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= 2 and text[0] in "[(" and text[-1] in "])":
            text = text[1:-1]
        kinds = []
        for part in text.replace("\n", ",").split(","):
            cleaned = part.strip()
            if cleaned.startswith("-"):
                cleaned = cleaned[1:]
            cleaned = cleaned.strip().strip("\"'").strip()
            if cleaned:
                kinds.append(cleaned)
        return frozenset(kinds)
    # A bool/int/dict proposal for a list-valued field is not something to
    # interpret charitably.
    return None


def _is_disallowed_clearance_value(field_name: str, value: Any) -> bool:
    """True when *value* on *field_name* would widen permitted use.

    ``clearance_gate.state``
        ``closed`` is refused — closing a gate is an operator edit of
        ``config/clearance_gates.yaml``, never a code path.
    ``clearance.blocked_scopes``
        A release-shaped value (empty set) is refused; adding a scope passes.
    ``clearance.posture_at_stamp``
        ``none`` is refused when proposed as an overwrite, because restamping a
        dev/test-acquired record as though no posture applied is exactly the
        retroactive-release move the durable stamp exists to prevent.
    ``applies_to_kinds`` (any spelling in
    :data:`_CLEARANCE_APPLIES_TO_KINDS_FIELDS`)
        Refused unless the proposed set still contains every kind in
        :data:`_CLEARANCE_REQUIRED_KINDS`. Narrowing the governed-kind set is
        the global release lever (``governs_kind`` False ⇒ ``mediate_egress``
        hands back a clean token), so removal is refused while ADDING a kind —
        which widens what is governed — passes. Checked before the
        ``isinstance(value, str)`` guard below on purpose: this field's natural
        value is a list, and deferring on a list would be the whole hole.
    """

    if field_name in _CLEARANCE_APPLIES_TO_KINDS_FIELDS:
        proposed = _parse_proposed_kind_set(value)
        if proposed is None:
            return True
        return not _CLEARANCE_REQUIRED_KINDS.issubset(proposed)

    if not isinstance(value, str):
        # A non-string proposed value cannot be evaluated here; the schema's
        # enum + additionalProperties:false is the control for shape. Refusing
        # would block legitimate typed callers, so defer rather than guess.
        return False
    normalized = value.strip().strip("\"'").lower()
    if field_name == "clearance_gate.state":
        return normalized == _CLEARANCE_DISALLOWED_GATE_STATE
    if field_name == "clearance.blocked_scopes":
        return normalized in _CLEARANCE_RELEASE_VALUES
    if field_name == "clearance.posture_at_stamp":
        return normalized == "none"
    return False


# --- Release-gate: judgment_basis: unassessed (decisions-block OQ-6) -------
#
# ``judgment_basis`` (P1) lives on ``source_assertion.extensions.evidence_taxonomy``
# and is an INDEPENDENT axis from ``evidence_item_type`` — see
# tests/test_schema_validation.py. This predicate is the boolean logic behind
# the *bidirectional* release gate the plan's NFR "Release-gate asymmetry"
# calls out: an ``unassessed`` evidence item must BLOCK a release/disposition
# evaluation (e.g. commercial licensing) but must NEVER block an
# internal-capture write — an agent must still be able to honestly record
# "I haven't judged this yet" without being punished for saying so.
#
# ``verification.py::verify_report`` is the CALLER (verify-time check in its
# existing check sequence) — this module owns the logic, verify_report does
# not reimplement it.
_UNASSESSED_JUDGMENT_BASIS = "unassessed"

# Dispositions this predicate gates. Enumerated BY NAME (mirrors
# _RIGHTS_GOVERNED_FIELDS's convention above) — any disposition NOT in this
# set (most notably "internal_capture") always returns False from
# release_gate_blocked_by_unassessed_judgment, regardless of judgment_basis.
_RELEASE_GATED_DISPOSITIONS: frozenset[str] = frozenset({"commercial_release"})


def release_gate_blocked_by_unassessed_judgment(
    judgment_bases: Any, *, disposition: str
) -> bool:
    """True when *disposition* must be blocked by an unassessed evidence item.

    Bidirectional per decisions-block OQ-6:

    - ``disposition == "commercial_release"`` (or any future member of
      :data:`_RELEASE_GATED_DISPOSITIONS`) AND at least one entry in
      *judgment_bases* equals ``"unassessed"`` -> ``True`` (blocked).
    - Any other disposition — in particular ``"internal_capture"`` — always
      returns ``False``: the release-gate asymmetry means writing an honest
      ``judgment_basis: unassessed`` evidence item during capture must never
      be blocked by this rule.

    Parameters
    ----------
    judgment_bases:
        An iterable of ``judgment_basis`` string values (or ``None`` entries,
        which are ignored) drawn from the evidence items involved in the
        operation being gated.
    disposition:
        The kind of operation being evaluated, e.g. ``"commercial_release"``
        or ``"internal_capture"``. Not validated against an enum here —
        callers own their own disposition vocabulary; this predicate only
        checks set membership against :data:`_RELEASE_GATED_DISPOSITIONS`.
    """

    if disposition not in _RELEASE_GATED_DISPOSITIONS:
        return False
    return any(jb == _UNASSESSED_JUDGMENT_BASIS for jb in judgment_bases or ())


# --- Built-in fallbacks (mirror config/governance.yaml) --------------------

_BUILTIN_SECRET_PATTERNS: tuple[str, ...] = (
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9_\-]{20,}",
    r"ghp_[A-Za-z0-9]{36,}",
    r"gho_[A-Za-z0-9]{36,}",
    r"github_pat_[A-Za-z0-9_]{22,}",
    r"AKIA[0-9A-Z]{16}",
    r"ASIA[0-9A-Z]{16}",
    r"AIza[0-9A-Za-z\-_]{35}",
    r"xox[baprse]-[0-9A-Za-z\-]{10,}",
    r"xapp-[0-9]-[A-Za-z0-9\-]{10,}",
    r"glpat-[0-9A-Za-z\-_]{20,}",
    r"(?:sk|rk)_live_[0-9A-Za-z]{20,}",
    r"SG\.[A-Za-z0-9_\-]{22,}\.[A-Za-z0-9_\-]{43,}",
    r"SK[0-9a-fA-F]{32}",
    r"AC[0-9a-fA-F]{32}",
    r"(?i)aws_secret[_a-z]*\s*[:=]\s*['\"]?[A-Za-z0-9/+]{40}",
    r"(?i)bearer\s+[A-Za-z0-9_\-\.=]{16,}",
    r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|client[_-]?secret)"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
    r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?\S{8,}",
    r"-----BEGIN[ A-Z]*PRIVATE KEY-----",
    r"-----BEGIN OPENSSH PRIVATE KEY-----",
    r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
)

# Severity → contributing exit code (worst severity wins).
_BLOCK = "block"
_REQUIRE_APPROVAL = "require_approval"
_WARN = "warn"


# --- Result dataclasses ----------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """A single fired policy rule."""

    rule_id: str
    severity: str  # block|require_approval|warn
    message: str
    detail: str = ""


@dataclass(frozen=True)
class GuardResult:
    """Aggregate outcome of a governance check."""

    passed: bool
    exit_code: int  # 0 ok, 3 block, 7 require_approval
    violations: list[Violation] = field(default_factory=list)


@dataclass(frozen=True)
class GuardContext:
    """Inputs to :func:`guard_check` (all optional; deterministic)."""

    profile: str = "personal"  # runtime key profile
    run_id: str | None = None
    sensitivity: str | None = None  # run/bundle sensitivity
    source_sensitivities: tuple[str, ...] = ()  # sensitivities of involved source cards
    model_provider: str | None = None
    writeback_targets: tuple[str, ...] = ()
    intent_key_profile_allowed: str | None = None
    artifact_paths: tuple[Path, ...] = ()  # files to secret-scan
    unmapped_material_claims: int = 0  # >0 -> material_claims_must_be_mapped fires
    unsupported_claims: int = 0
    # (field_name, value) pairs an agent-authored code path is attempting to
    # write, e.g. ("rights_record.overall_status", "CLEARED_FAIR_USE").
    # See _RIGHTS_GOVERNED_FIELDS / FR-23.
    proposed_field_writes: tuple[tuple[str, str], ...] = ()


# --- Config loading helpers ------------------------------------------------


def _config_for(config: FoundryConfig | None, paths: FoundryPaths | None) -> FoundryConfig:
    if config is not None:
        return config
    return FoundryConfig(paths=paths or FoundryPaths.discover())


def _secret_patterns(config: FoundryConfig) -> list[str]:
    """Return the effective secret-pattern list for `config`'s workspace.

    NEW-5 fix (research-foundry-operator-mcp-v1 security round 2): config-
    declared `governance.secret_patterns` are UNIONED WITH -- never
    REPLACE -- the built-in list. The prior behavior (config patterns
    entirely replacing `_BUILTIN_SECRET_PATTERNS` whenever a workspace
    declared its own list) meant a workspace with a narrow custom pattern
    list became LESS strict than the no-config default -- e.g. a
    governance.yaml declaring only one internal token format would silently
    stop detecting `sk-ant-...`/AWS/GitHub-shaped secrets that the built-in
    list would otherwise catch. Config-declared patterns can only ADD
    detection surface, never remove or replace a built-in.
    """

    gov = config.governance or {}
    pats = gov.get("secret_patterns") if isinstance(gov, dict) else None
    extra = [p for p in pats if isinstance(p, str)] if isinstance(pats, list) else []
    merged = list(_BUILTIN_SECRET_PATTERNS)
    for pattern in extra:
        if pattern not in merged:
            merged.append(pattern)
    return merged


def _approved_providers(config: FoundryConfig) -> set[str]:
    gov = config.governance or {}
    provs = gov.get("approved_work_providers") if isinstance(gov, dict) else None
    if isinstance(provs, list):
        return {str(p) for p in provs}
    return set()


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            continue
    return compiled


# --- Secret scanning -------------------------------------------------------


def scan_secrets(text: str, *, config: FoundryConfig | None = None) -> list[str]:
    """Return the list of secret-pattern matches found in ``text`` (may be empty)."""

    if not text:
        return []
    cfg = config if config is not None else FoundryConfig(paths=FoundryPaths.discover())
    matches: list[str] = []
    for rx in _compile(_secret_patterns(cfg)):
        for m in rx.finditer(text):
            matches.append(m.group(0))
    return matches


def scan_paths(
    paths_to_scan: list[Path], *, config: FoundryConfig | None = None
) -> list[Violation]:
    """Secret-scan each readable file; one ``block`` Violation per hit file."""

    cfg = config if config is not None else FoundryConfig(paths=FoundryPaths.discover())
    violations: list[Violation] = []
    for p in paths_to_scan or []:
        path = Path(p)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = scan_secrets(text, config=cfg)
        if hits:
            violations.append(
                Violation(
                    rule_id="no_secret_in_markdown",
                    severity=_BLOCK,
                    message="Potential secret detected in Markdown/YAML artifact.",
                    detail=f"{path}: {len(hits)} match(es) (e.g. {_redact(hits[0])})",
                )
            )
    return violations


def _redact(secret: str) -> str:
    """Shorten a matched secret so it is never echoed in full."""

    s = secret.strip()
    if len(s) <= 8:
        return s[:2] + "***"
    return f"{s[:4]}…{s[-2:]}"


# --- Recursive payload redaction -------------------------------------------


def _walk_redact(obj: Any, patterns: list[re.Pattern[str]]) -> Any:
    """Recursive inner helper for :func:`redact_payload`."""

    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        for rx in patterns:
            if rx.search(obj):
                return "[REDACTED]"
        return obj
    if isinstance(obj, dict):
        # Walk ALL key types — non-str hashable keys (tuples, ints, …) are
        # recursed just like values so a secret embedded in a tuple dict-key
        # cannot bypass the firewall.  Non-str scalar keys (int, float, bool)
        # are returned unchanged by the scalar guard at the top of this function.
        return {
            _walk_redact(k, patterns): _walk_redact(v, patterns)
            for k, v in obj.items()
        }
    if isinstance(obj, tuple):
        return tuple(_walk_redact(item, patterns) for item in obj)
    if isinstance(obj, list):
        return [_walk_redact(item, patterns) for item in obj]
    return obj


def redact_payload(obj: Any, *, config: FoundryConfig | None = None) -> Any:
    """All agent-job write paths MUST pass data through redact_payload before persistence. Use AgentJobService._safe_write_json() which enforces this automatically.

    Recursively walk *obj* and replace any string matching a secret pattern
    with ``'[REDACTED]'``.

    Returns a sanitized *copy*; does NOT mutate the original.
    Handles nested :class:`dict` and :class:`list` values recursively.
    Scalar types (``None``, ``int``, ``float``, ``bool``) are returned unchanged.

    Parameters
    ----------
    obj:
        The value to sanitize.  Any depth of nesting is supported.
    config:
        Optional :class:`FoundryConfig` used to load additional secret patterns.
        When *None*, the built-in ``_BUILTIN_SECRET_PATTERNS`` are used.
    """

    pats = _compile(
        _secret_patterns(config) if config is not None else list(_BUILTIN_SECRET_PATTERNS)
    )
    return _walk_redact(obj, pats)


# --- Rule evaluation -------------------------------------------------------


def _rule_message(config: FoundryConfig, rule_id: str, default: str) -> str:
    for rule in config.policy_rules():
        if isinstance(rule, dict) and rule.get("id") == rule_id:
            return str(rule.get("message") or default)
    return default


def guard_check(
    ctx: GuardContext, *, paths: FoundryPaths | None = None
) -> GuardResult:
    """Evaluate the §7.2 policy rules against ``ctx`` and return a GuardResult."""

    paths = paths or FoundryPaths.discover()
    cfg = _config_for(None, paths)
    violations: list[Violation] = []

    sources = list(ctx.source_sensitivities or ())
    targets = list(ctx.writeback_targets or ())

    # 1. no_work_keys_for_personal_runs (block)
    if ctx.intent_key_profile_allowed == "personal" and ctx.profile == "work_approved":
        violations.append(
            Violation(
                rule_id="no_work_keys_for_personal_runs",
                severity=_BLOCK,
                message=_rule_message(
                    cfg,
                    "no_work_keys_for_personal_runs",
                    "Work-provided keys cannot be used for personal research.",
                ),
                detail=(
                    "intent.governance.key_profile_allowed=personal "
                    "but runtime.key_profile=work_approved"
                ),
            )
        )

    # 2. no_work_sensitive_to_unapproved_provider (block)
    if ctx.sensitivity in _WORK_SENSITIVITIES and ctx.model_provider:
        if ctx.model_provider not in _approved_providers(cfg):
            violations.append(
                Violation(
                    rule_id="no_work_sensitive_to_unapproved_provider",
                    severity=_BLOCK,
                    message=_rule_message(
                        cfg,
                        "no_work_sensitive_to_unapproved_provider",
                        "Sensitive work/client data cannot be sent to non-approved providers.",
                    ),
                    detail=(
                        f"sensitivity={ctx.sensitivity}, provider={ctx.model_provider!r} "
                        "not in approved_work_providers"
                    ),
                )
            )

    # 3. no_mixed_personal_work_bundle (block)
    has_personal = any(s in _PERSONAL_SENSITIVITIES for s in sources)
    has_work = any(s in _WORK_SENSITIVITIES for s in sources)
    if has_personal and has_work:
        violations.append(
            Violation(
                rule_id="no_mixed_personal_work_bundle",
                severity=_BLOCK,
                message=_rule_message(
                    cfg,
                    "no_mixed_personal_work_bundle",
                    "Personal and work-sensitive source cards cannot be mixed "
                    "in one evidence bundle.",
                ),
                detail=f"source_sensitivities={sorted(set(sources))}",
            )
        )

    # 4. no_secret_in_markdown (block) — scan provided artifact paths.
    violations.extend(scan_paths(list(ctx.artifact_paths or ()), config=cfg))

    # 5. work_writeback_requires_review (require_approval) — meatywiki
    personal_mw_target = any("meatywiki" in t and "personal" in t for t in targets) or (
        "meatywiki" in targets
    )
    work_source = any(s in _WORK_SENSITIVITIES for s in sources) or (
        ctx.sensitivity in _WORK_SENSITIVITIES
    )
    if personal_mw_target and work_source:
        violations.append(
            Violation(
                rule_id="work_writeback_requires_review",
                severity=_REQUIRE_APPROVAL,
                message=_rule_message(
                    cfg,
                    "work_writeback_requires_review",
                    "Work-sensitive content requires sanitization and approval "
                    "before personal MeatyWiki writeback.",
                ),
                detail=f"targets={targets}, sensitivity={ctx.sensitivity}",
            )
        )

    # 5b. intenttree_writeback_requires_review (require_approval) — intenttree
    intenttree_target = "intenttree" in targets
    if intenttree_target and work_source:
        violations.append(
            Violation(
                rule_id="intenttree_writeback_requires_review",
                severity=_REQUIRE_APPROVAL,
                message=_rule_message(
                    cfg,
                    "intenttree_writeback_requires_review",
                    "Work/client-sensitive content requires human review before "
                    "IntentTree writeback.",
                ),
                detail=f"targets={targets}, sensitivity={ctx.sensitivity}",
            )
        )

    # 5c. arc_writeback_requires_review (require_approval) — arc council
    arc_target = "arc" in targets
    if arc_target and work_source:
        violations.append(
            Violation(
                rule_id="arc_writeback_requires_review",
                severity=_REQUIRE_APPROVAL,
                message=_rule_message(
                    cfg,
                    "arc_writeback_requires_review",
                    "Work/client-sensitive content requires human review before "
                    "ARC council writeback.",
                ),
                detail=f"targets={targets}, sensitivity={ctx.sensitivity}",
            )
        )

    # 6. material_claims_must_be_mapped (block)
    if ctx.unmapped_material_claims > 0 or ctx.unsupported_claims > 0:
        violations.append(
            Violation(
                rule_id="material_claims_must_be_mapped",
                severity=_BLOCK,
                message=_rule_message(
                    cfg,
                    "material_claims_must_be_mapped",
                    "Every material claim must map to a source card or be "
                    "labeled inference/speculation.",
                ),
                detail=(
                    f"unmapped={ctx.unmapped_material_claims}, "
                    f"unsupported={ctx.unsupported_claims}"
                ),
            )
        )

    # 7. no_agent_cleared_rights_value (block) — FR-23 write ceiling. Enumerates
    # all 4 governed fields BY NAME; synthesis.attestation.status already has a
    # service-layer guard (assertion_materialization._enforce_synthesis_attestation_ceiling)
    # — this rule is the governance-layer backstop covering it uniformly with
    # the other 3 fields.
    for field_name, value in ctx.proposed_field_writes or ():
        if field_name in _RIGHTS_GOVERNED_FIELDS and _is_disallowed_rights_value(value):
            violations.append(
                Violation(
                    rule_id="no_agent_cleared_rights_value",
                    severity=_BLOCK,
                    message=_rule_message(
                        cfg,
                        "no_agent_cleared_rights_value",
                        "Agent-writable code paths cannot set a rights-clearance "
                        "field to a CLEARED_*, counsel_approved, or attested value "
                        "— that requires human/counsel authorship.",
                    ),
                    detail=f"field={field_name!r}, value={value!r}",
                )
            )

    # 8. no_agent_authored_attribution_value (block) — M3 (SMP-3.1/3.2).
    # DEFENCE-IN-DEPTH ONLY. Mirrors rule 7's exact shape and deliberately
    # reuses the SAME _is_disallowed_rights_value predicate: the "CLEARED_*/
    # counsel_approved/attested" concept is not rights-specific, it means "a
    # human/counsel had to bless this," and no agent-writable path may mint
    # it onto ANY governed field, attribution included. Scoped to
    # _ATTRIBUTION_GOVERNED_FIELDS purely so the violation message names the
    # attribution surface distinctly; rule 7 already independently fires for
    # the same two fields via the shared, extended _RIGHTS_GOVERNED_FIELDS
    # tuple above.
    #
    # WHAT THIS RULE STILL MISSES (by construction, proving SMP-3.2B is the
    # real control): a write to `trust.third_party_citation_rank` — a field
    # name not on _RIGHTS_GOVERNED_FIELDS, _ATTRIBUTION_GOVERNED_FIELDS, or
    # any name list anywhere in this module — carrying an identical
    # disallowed value, or indeed any raw unattested third-party value at
    # all, sails through both rule 7 and this rule untouched. Only the
    # schema's structural if/then over asserter_type / retrieval_evidence_ref
    # (SMP-3.2B, in schemas/source_attribution.schema.yaml) closes that gap.
    for field_name, value in ctx.proposed_field_writes or ():
        if field_name in _ATTRIBUTION_GOVERNED_FIELDS and _is_disallowed_rights_value(value):
            violations.append(
                Violation(
                    rule_id="no_agent_authored_attribution_value",
                    severity=_BLOCK,
                    message=_rule_message(
                        cfg,
                        "no_agent_authored_attribution_value",
                        "Agent-writable code paths cannot set a source-attribution "
                        "field to a CLEARED_*, counsel_approved, or attested value "
                        "— that requires human/counsel authorship. This rule is "
                        "defence-in-depth only; the primary control is the "
                        "source_attribution schema's structural asserter_type / "
                        "retrieval_evidence_ref requirement (SMP-3.2B).",
                    ),
                    detail=f"field={field_name!r}, value={value!r}",
                )
            )

    # 9. no_agent_cleared_clearance_taint (block) — clearance write ceiling.
    # Mirrors rule 7's shape but with its OWN predicate and its OWN vocabulary:
    # clearance never reuses CLEARED_*/counsel_approved/attested (ADR Invariant
    # 1 reserves those for humans, and borrowing them would make a legitimate
    # agent stamp look like a rights-clearance forgery).
    #
    # Monotone by construction, on all three axes: adding a blocked scope
    # passes and asserting the empty set is blocked; opening a gate passes and
    # closing one is blocked; ADDING a governed record kind passes and dropping
    # one below _CLEARANCE_REQUIRED_KINDS is blocked. So no agent-reachable path
    # can widen a record's permitted use, close a gate, or take a whole record
    # kind out of clearance's scope (the global release lever — see the module
    # comment above _CLEARANCE_GOVERNED_FIELDS for why that one is the largest
    # blast radius of the three and why its floor lives in code).
    for field_name, value in ctx.proposed_field_writes or ():
        if field_name in _CLEARANCE_GOVERNED_FIELDS and _is_disallowed_clearance_value(
            field_name, value
        ):
            violations.append(
                Violation(
                    rule_id="no_agent_cleared_clearance_taint",
                    severity=_BLOCK,
                    message=_rule_message(
                        cfg,
                        "no_agent_cleared_clearance_taint",
                        "Agent-writable code paths cannot release a clearance taint, "
                        "close a clearance gate, or narrow the governed record kinds — "
                        "all three are human determinations. An agent may ADD a blocked "
                        "scope but never assert the empty set; may OPEN a gate but not "
                        "close one; may ADD a kind to applies_to_kinds but never drop a "
                        "required one, because a kind outside applies_to_kinds gets a "
                        "clean token from mediate_egress unconditionally. Closing a gate "
                        "or narrowing applies_to_kinds is an operator edit of "
                        "config/clearance_gates.yaml. For the taint fields this rule is "
                        "defence-in-depth (the primary controls are "
                        "clearance_taint.schema.yaml's structural shape and mediate_egress "
                        "treating an absent stamp as blocked); for applies_to_kinds there "
                        "is no schema backstop, so this rule is the only control.",
                    ),
                    detail=f"field={field_name!r}, value={value!r}",
                )
            )

    result = _resolve(violations)
    _trace(paths, ctx, result)
    return result


def load_run_context(
    run_id: str,
    *,
    profile: str = "personal",
    model_provider: str | None = None,
    writeback_targets: tuple[str, ...] = (),
    paths: FoundryPaths | None = None,
) -> GuardContext:
    """Build a :class:`GuardContext` from a planned run's on-disk artifacts.

    Resolves the run's ``run.yaml`` → linked intent (``intents/active/<id>.yaml``)
    to read ``governance.key_profile_allowed`` and sensitivity, scans the run's
    ``sources/*.md`` front matter for their sensitivities, and collects the run's
    Markdown/YAML artifact paths for the secret scan. Missing pieces degrade to
    empty values so the guard is still evaluable. Raises :class:`NotFoundError`
    when the run directory itself is absent.
    """

    from ..errors import NotFoundError  # local import to avoid cycle at module load

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    if not rp.run.exists():
        raise NotFoundError(f"run not found: {run_id} ({rp.run})")

    run_doc = _safe_load_yaml(rp.run_yaml)
    intent_id = run_doc.get("intent_id") if isinstance(run_doc, dict) else None
    run_sensitivity = run_doc.get("sensitivity") if isinstance(run_doc, dict) else None

    key_profile_allowed: str | None = None
    intent_sensitivity: str | None = None
    if intent_id:
        intent = _load_intent_doc(str(intent_id), paths)
        gov = intent.get("governance") if isinstance(intent.get("governance"), dict) else {}
        key_profile_allowed = gov.get("key_profile_allowed")
        intent_sensitivity = intent.get("sensitivity") or gov.get("sensitivity")

    source_sensitivities = _scan_source_sensitivities(rp.sources)
    artifact_paths = _collect_run_artifacts(rp.run)

    return GuardContext(
        profile=profile,
        run_id=run_id,
        sensitivity=intent_sensitivity or run_sensitivity,
        source_sensitivities=tuple(source_sensitivities),
        model_provider=model_provider,
        writeback_targets=tuple(writeback_targets),
        intent_key_profile_allowed=key_profile_allowed,
        artifact_paths=tuple(artifact_paths),
    )


def _safe_load_yaml(path: Path) -> dict:
    from ..yamlio import load_yaml

    try:
        data = load_yaml(path)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_intent_doc(intent_id: str, paths: FoundryPaths) -> dict:
    """Resolve an intent by id under ``intents/active/`` (recursive fallback)."""

    candidate = paths.intents_active / f"{intent_id}.yaml"
    if not candidate.exists():
        matches = sorted(paths.intents.rglob(f"{intent_id}.yaml")) if paths.intents.exists() else []
        candidate = matches[0] if matches else candidate
    return _safe_load_yaml(candidate) if candidate.exists() else {}


def _scan_source_sensitivities(sources_dir: Path) -> list[str]:
    """Collect the ``sensitivity`` front-matter value from each source card."""

    if not sources_dir.exists():
        return []
    from ..frontmatter import load_md

    out: list[str] = []
    for md in sorted(sources_dir.glob("*.md")):
        try:
            meta, _ = load_md(md)
        except (OSError, ValueError):
            continue
        sens = meta.get("sensitivity") if isinstance(meta, dict) else None
        if isinstance(sens, str) and sens:
            out.append(sens)
    return out


def _collect_run_artifacts(run_dir: Path) -> list[Path]:
    """Gather Markdown/YAML files under a run dir for the secret scan."""

    if not run_dir.exists():
        return []
    files: list[Path] = []
    for pattern in ("*.md", "*.yaml", "*.yml"):
        files.extend(run_dir.rglob(pattern))
    return sorted(set(files))


def preflight(
    intent: dict,
    ibom: dict,
    routing: dict,
    profile: str,
    *,
    paths: FoundryPaths | None = None,
) -> GuardResult:
    """Pre-run governance check derived from intent/ibom/routing artifacts."""

    paths = paths or FoundryPaths.discover()
    intent = intent or {}
    ibom = ibom or {}
    routing = routing or {}

    gov = intent.get("governance") if isinstance(intent.get("governance"), dict) else {}
    key_profile_allowed = gov.get("key_profile_allowed")

    sensitivity = (
        intent.get("sensitivity")
        or gov.get("sensitivity")
        or ibom.get("sensitivity")
    )

    provider = (
        routing.get("model_provider")
        or routing.get("provider")
        or (routing.get("selected") or {}).get("provider")
        if isinstance(routing, dict)
        else None
    )

    writeback_targets = gov.get("allowed_writebacks") or []
    if not isinstance(writeback_targets, (list, tuple)):
        writeback_targets = []

    ctx = GuardContext(
        profile=profile,
        run_id=None,
        sensitivity=sensitivity,
        source_sensitivities=(),
        model_provider=provider,
        writeback_targets=tuple(writeback_targets),
        intent_key_profile_allowed=key_profile_allowed,
        artifact_paths=(),
    )
    return guard_check(ctx, paths=paths)


# --- Outcome aggregation + trace ------------------------------------------


def _resolve(violations: list[Violation]) -> GuardResult:
    severities = {v.severity for v in violations}
    if _BLOCK in severities:
        return GuardResult(passed=False, exit_code=int(ExitCode.GOVERNANCE), violations=violations)
    if _REQUIRE_APPROVAL in severities:
        return GuardResult(
            passed=False, exit_code=int(ExitCode.HUMAN_REVIEW), violations=violations
        )
    return GuardResult(passed=True, exit_code=int(ExitCode.OK), violations=violations)


def _trace(paths: FoundryPaths, ctx: GuardContext, result: GuardResult) -> None:
    """Best-effort run-trace record; never fail the guard on trace error."""

    if not ctx.run_id:
        return
    try:
        rp = paths.run_paths(ctx.run_id)
        append_jsonl(
            {
                "stage": "guard",
                "ts": now_iso(),
                "run_id": ctx.run_id,
                "passed": result.passed,
                "exit_code": result.exit_code,
                "violations": [v.rule_id for v in result.violations],
            },
            rp.run_trace,
        )
    except Exception:  # noqa: BLE001 — tracing is best-effort
        pass


__all__ = [
    "Violation",
    "GuardResult",
    "GuardContext",
    "guard_check",
    "preflight",
    "load_run_context",
    "scan_secrets",
    "scan_paths",
    "redact_payload",
]
