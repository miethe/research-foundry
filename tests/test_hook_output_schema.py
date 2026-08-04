"""Claude Code hook-output schema conformance for the §7.3 validators.

Every hook this repo registers in ``.claude/settings.json`` must print stdout
that survives Claude Code's hook-output validation. Historically none of them
did: ``guard_pretool`` and ``scan_artifact`` both led with
``{"decision": "allow"}``, and ``"allow"`` has never been a member of the
top-level ``decision`` enum on any event. Validation therefore failed on 100% of
invocations and the hooks' verdicts were discarded wholesale — the guard's
*denies* included, which made it a no-op that only produced stderr noise.

The schema encoded in :func:`validate_hook_output` is transcribed from the
official reference (``code.claude.com/docs/en/hooks``):

* Recognised top-level fields: ``continue``, ``stopReason``, ``suppressOutput``,
  ``systemMessage``, ``terminalSequence``, ``decision``, ``reason``,
  ``hookSpecificOutput``.
* ``decision``'s only value is ``"block"``; omit it (or print nothing at all) to
  allow. PreToolUse additionally accepts the *deprecated* ``"approve"``/
  ``"block"`` pair, which maps onto ``permissionDecision`` ``allow``/``deny``.
* ``hookSpecificOutput.permissionDecision`` (PreToolUse only) is one of
  ``allow``, ``deny``, ``ask``, ``defer``.
* Exit 0 with empty stdout is the documented "no decision" idiom.

:func:`validate_hook_output` is itself covered by positive controls below, so it
cannot pass every input vacuously — a validator that accepts anything would make
the conformance sweep meaningless.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
SETTINGS = REPO / ".claude" / "settings.json"

_TOP_LEVEL_FIELDS = frozenset(
    {
        "continue",
        "stopReason",
        "suppressOutput",
        "systemMessage",
        "terminalSequence",
        "decision",
        "reason",
        "hookSpecificOutput",
    }
)

# The only current top-level decision value, for the events that support it.
_DECISION_VALUES = frozenset({"block"})
# PreToolUse's deprecated spelling, retained for back-compat by Claude Code.
_DEPRECATED_PRETOOLUSE_DECISIONS = frozenset({"approve", "block"})
_PERMISSION_DECISIONS = frozenset({"allow", "deny", "ask", "defer"})

_HOOK_SPECIFIC_FIELDS: dict[str, frozenset[str]] = {
    "PreToolUse": frozenset(
        {
            "hookEventName",
            "permissionDecision",
            "permissionDecisionReason",
            "updatedInput",
            "additionalContext",
        }
    ),
    "PostToolUse": frozenset(
        {
            "hookEventName",
            "additionalContext",
            "updatedToolOutput",
            "updatedMCPToolOutput",
        }
    ),
    "Stop": frozenset({"hookEventName"}),
}


def validate_hook_output(raw: str, *, event: str) -> list[str]:
    """Return the schema violations in a hook's raw stdout (empty == conformant).

    ``raw`` may be empty or whitespace: exit 0 with no stdout is the documented
    way to say "no decision, apply the normal flow".
    """

    if not raw or not raw.strip():
        return []

    violations: list[str] = []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"stdout is not valid JSON: {exc}"]
    if not isinstance(payload, dict):
        return [f"hook output must be a JSON object, got {type(payload).__name__}"]

    unknown = sorted(set(payload) - _TOP_LEVEL_FIELDS)
    if unknown:
        violations.append(f"unrecognised top-level field(s): {', '.join(unknown)}")

    if "decision" in payload:
        decision = payload["decision"]
        allowed = (
            _DEPRECATED_PRETOOLUSE_DECISIONS if event == "PreToolUse" else _DECISION_VALUES
        )
        if decision not in allowed:
            violations.append(
                f"decision={decision!r} is not a member of the {event} enum "
                f"({{{', '.join(sorted(repr(v) for v in allowed))}}}); "
                "omit `decision` to allow"
            )

    hso = payload.get("hookSpecificOutput")
    if hso is not None:
        if not isinstance(hso, dict):
            violations.append("hookSpecificOutput must be an object")
        else:
            name = hso.get("hookEventName")
            if name != event:
                violations.append(
                    f"hookSpecificOutput.hookEventName={name!r} does not match event {event!r}"
                )
            known = _HOOK_SPECIFIC_FIELDS.get(event, frozenset({"hookEventName"}))
            extra = sorted(set(hso) - known)
            if extra:
                violations.append(
                    f"unrecognised hookSpecificOutput field(s) for {event}: {', '.join(extra)}"
                )
            if "permissionDecision" in hso:
                if event != "PreToolUse":
                    violations.append(f"permissionDecision is not valid on {event}")
                elif hso["permissionDecision"] not in _PERMISSION_DECISIONS:
                    violations.append(
                        f"permissionDecision={hso['permissionDecision']!r} is not one of "
                        f"{sorted(_PERMISSION_DECISIONS)}"
                    )
    return violations


# ---------------------------------------------------------------------------
# Positive controls: the validator must REJECT the payloads that shipped.
# Without these, a permissive validator would green-light the whole sweep.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event", ["PreToolUse", "PostToolUse", "Stop"])
def test_validator_rejects_decision_allow(event: str):
    """``{"decision": "allow"}`` — the exact payload that failed 100% of runs."""

    violations = validate_hook_output(json.dumps({"decision": "allow"}), event=event)
    assert violations, f"validator must reject decision='allow' on {event}"
    assert any("decision" in v for v in violations)


@pytest.mark.parametrize("event", ["PreToolUse", "PostToolUse", "Stop"])
def test_validator_rejects_decision_deny(event: str):
    """``"deny"`` is a ``permissionDecision`` value, never a top-level decision."""

    assert validate_hook_output(json.dumps({"decision": "deny"}), event=event)


def test_validator_rejects_unrecognised_top_level_fields():
    """The old deny payload's ``violations`` key and warn payload's ``warnings``."""

    assert validate_hook_output(json.dumps({"violations": ["secret_path_access"]}), event="PreToolUse")
    assert validate_hook_output(json.dumps({"warnings": ["secret found"]}), event="PostToolUse")


def test_validator_rejects_bad_permission_decision_and_mismatched_event():
    assert validate_hook_output(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "nope"}}
        ),
        event="PreToolUse",
    )
    # permissionDecision has no meaning on PostToolUse.
    assert validate_hook_output(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PostToolUse", "permissionDecision": "deny"}}
        ),
        event="PostToolUse",
    )
    # hookEventName must agree with the event the hook is registered on.
    assert validate_hook_output(
        json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}), event="PostToolUse"
    )


def test_validator_accepts_the_documented_conformant_shapes():
    """Negative control: valid payloads must produce no violations."""

    assert validate_hook_output("", event="PreToolUse") == []
    assert validate_hook_output("   \n", event="PostToolUse") == []
    assert (
        validate_hook_output(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "secret path",
                    }
                }
            ),
            event="PreToolUse",
        )
        == []
    )
    assert (
        validate_hook_output(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "advisory text",
                    }
                }
            ),
            event="PostToolUse",
        )
        == []
    )
    assert validate_hook_output(json.dumps({"suppressOutput": True}), event="Stop") == []
    assert validate_hook_output(json.dumps({"decision": "block", "reason": "no"}), event="Stop") == []


# ---------------------------------------------------------------------------
# The real hooks, run as subprocesses exactly as Claude Code runs them.
# ---------------------------------------------------------------------------


def _run_hook(module: str, stdin: str) -> subprocess.CompletedProcess[str]:
    """Run a validator module, pinned to *this* test file's source tree.

    ``PYTHONPATH`` is set explicitly from ``REPO`` so a worktree run can never
    silently exercise another checkout's validators via an editable install.
    """

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO / "src"), env.get("PYTHONPATH", "")) if p
    )
    return subprocess.run(
        [sys.executable, "-m", module],
        cwd=REPO,
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


_SECRET = "sk-ant-" + "abcdefghij1234567890abcdef"  # split so guard_pretool ignores this file

# (label, stdin) pairs exercising the allow/clean and deny/warn branches.
_PRETOOL_INPUTS: list[tuple[str, str]] = [
    ("empty_stdin", ""),
    ("whitespace_stdin", "   "),
    ("malformed_stdin", "not json {{{"),
    ("benign_write", json.dumps({"tool_name": "Write", "tool_input": {"file_path": "notes.md", "content": "hi"}})),
    ("bash_passthrough", json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})),
    ("deny_secret_path", json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/h/.env", "content": "x"}})),
    ("deny_secret_content", json.dumps({"tool_name": "Write", "tool_input": {"file_path": "notes.md", "content": _SECRET}})),
]


@pytest.mark.parametrize("label,stdin", _PRETOOL_INPUTS, ids=[label for label, _ in _PRETOOL_INPUTS])
def test_guard_pretool_output_is_schema_valid(label: str, stdin: str):
    proc = _run_hook("research_foundry.validators.guard_pretool", stdin)
    violations = validate_hook_output(proc.stdout, event="PreToolUse")
    assert not violations, f"[{label}] {violations} (stdout={proc.stdout!r})"


def test_guard_pretool_allow_path_emits_nothing_and_does_not_auto_approve():
    """Silence is the point: ``permissionDecision: "allow"`` would skip the prompt.

    An allow must leave the user's normal permission flow intact, so the hook has
    to emit *no* decision rather than an affirmative one.
    """

    proc = _run_hook(
        "research_foundry.validators.guard_pretool",
        json.dumps({"tool_name": "Write", "tool_input": {"file_path": "notes.md", "content": "hi"}}),
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", f"allow path must be silent, got {proc.stdout!r}"
    assert "permissionDecision" not in proc.stdout


def test_guard_pretool_deny_blocks_by_exit_code_with_reason_on_stderr():
    """Exit 2 makes Claude Code discard stdout and use stderr as the reason."""

    proc = _run_hook(
        "research_foundry.validators.guard_pretool",
        json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/h/.env", "content": "x"}}),
    )
    assert proc.returncode == 2, "deny must fail closed on the exit status alone"
    assert proc.stdout.strip() == "", "stdout is ignored on exit 2; it must stay empty"
    assert ".env" in proc.stderr and "secret_path_access" in proc.stderr


@pytest.mark.parametrize(
    "label,builder",
    [
        ("empty_stdin", lambda _p: ""),
        ("missing_target", lambda _p: json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/tmp/nope-xyz-123.md"}})),
        ("clean_file", lambda p: json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(p)}})),
        ("secret_file", lambda p: json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(p)}})),
    ],
)
def test_scan_artifact_output_is_schema_valid(label: str, builder, tmp_path: Path):
    target = tmp_path / "artifact.md"
    target.write_text(f"token {_SECRET}\n" if label == "secret_file" else "plain notes\n", encoding="utf-8")
    proc = _run_hook("research_foundry.validators.scan_artifact", builder(target))
    violations = validate_hook_output(proc.stdout, event="PostToolUse")
    assert proc.returncode == 0, "PostToolUse advisory must never block"
    assert not violations, f"[{label}] {violations} (stdout={proc.stdout!r})"


def test_scan_artifact_warning_reaches_claude_as_additional_context(tmp_path: Path):
    """The warning must be *delivered*, not just schema-valid.

    The previous payload was rejected as a whole, so its ``warnings`` never
    reached the model. ``additionalContext`` is the documented channel.
    """

    target = tmp_path / "leaky.md"
    target.write_text(f"token {_SECRET}\n", encoding="utf-8")
    proc = _run_hook(
        "research_foundry.validators.scan_artifact",
        json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target)}}),
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert validate_hook_output(proc.stdout, event="PostToolUse") == []
    assert "decision" not in payload, "an advisory hook must not emit a decision at all"
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "secret" in context.lower() and target.name in context


def test_emit_ccdash_event_output_is_schema_valid():
    proc = _run_hook("research_foundry.validators.emit_ccdash_event", json.dumps({"session_id": "s1"}))
    assert proc.returncode == 0
    assert validate_hook_output(proc.stdout, event="Stop") == []


# ---------------------------------------------------------------------------
# Sweep every hook actually registered in .claude/settings.json, so a newly
# added validator is covered without editing this file (node AC: "audit sibling
# PostToolUse validators for the same invalid enum literal").
# ---------------------------------------------------------------------------


def _registered_validators() -> list[tuple[str, str]]:
    """Return ``(event, module)`` for each research_foundry validator hook."""

    if not SETTINGS.exists():  # pragma: no cover - settings.json is committed
        return []
    hooks: dict[str, Any] = json.loads(SETTINGS.read_text(encoding="utf-8")).get("hooks", {})
    found: list[tuple[str, str]] = []
    for event, matchers in hooks.items():
        for matcher in matchers or []:
            for hook in matcher.get("hooks", []) or []:
                m = re.search(r"-m\s+(research_foundry\.validators\.[\w.]+)", hook.get("command", ""))
                if m:
                    found.append((event, m.group(1)))
    return found


def test_settings_json_registers_the_validators_under_test():
    """Guard the sweep against silently discovering nothing."""

    registered = _registered_validators()
    modules = {module for _, module in registered}
    assert modules >= {
        "research_foundry.validators.guard_pretool",
        "research_foundry.validators.scan_artifact",
        "research_foundry.validators.emit_ccdash_event",
    }, f"expected all three validators to be registered, found {modules}"
    assert {event for event, _ in registered} >= {"PreToolUse", "PostToolUse", "Stop"}


def test_every_registered_validator_emits_schema_valid_output_on_empty_stdin():
    """No registered hook may fail validation on the trivial no-payload path.

    This is the path Claude Code hits constantly, and the one that produced
    ~1,488 ``hook_non_blocking_error`` records in under four days.
    """

    failures: list[str] = []
    for event, module in _registered_validators():
        proc = _run_hook(module, "")
        violations = validate_hook_output(proc.stdout, event=event)
        if violations:
            failures.append(f"{event}:{module} -> {violations} (stdout={proc.stdout!r})")
    assert not failures, "\n".join(failures)


def test_no_validator_emits_the_invalid_allow_or_deny_literal():
    """Regression net against the enum drifting back.

    Asserts on *behaviour* (what the process prints) rather than grepping the
    source, so a refactor that reintroduces the bug through a helper is caught.
    """

    offenders: list[str] = []
    for event, module in _registered_validators():
        proc = _run_hook(module, "")
        if not proc.stdout.strip():
            continue
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            offenders.append(f"{event}:{module} printed non-JSON {proc.stdout!r}")
            continue
        if isinstance(payload, dict) and payload.get("decision") in {"allow", "deny"}:
            offenders.append(f"{event}:{module} emitted decision={payload['decision']!r}")
    assert not offenders, "\n".join(offenders)
