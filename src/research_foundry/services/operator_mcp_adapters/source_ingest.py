"""`source.ingest` Operator MCP adapter (research-foundry-operator-mcp-v1,
M1 remainder leg B).

Wraps `research_foundry.services.source_cards.ingest_source` behind the
fixed authorize -> consume -> execute -> bounded-result pipeline in
`operator_mcp_adapters.base.run_pipeline`, following the exact shape
`run_plan.py`/`swarm_start.py` established.

**Workspace binding (m1-remainder-implementer-contract.md, decision D2).**
`cli_commands.py`'s own `ingest` command resolves
`assertion_registry_workspace_id` from a hard-coded single-operator literal
(`cli_commands.py:354`; see `assertion_workspace.resolve_or_deny`'s own
docstring for what that literal is and why the CLI's bare invocation, with
no operator identity in play, resolves it that way). This adapter does NOT
reproduce that literal and does NOT change the CLI's own resolution (an M1
acceptance criterion requires CLI parity to hold; changing that call site is
therefore out of this leg's scope and is logged as a follow-up in this
task's completion note). Instead, `assertion_registry_workspace_id` is
resolved from `ctx.identity.workspace_id` -- the SAME structurally-resolved
identity every other Operator MCP adapter in this family uses (mirrors
`job_lifecycle.py`'s `request_cancellation(..., workspace_id=ctx.identity.workspace_id, ...)`
call sites).

**`run` target / cross-workspace gate.** `source.ingest` REQUIRES a `run`
target (`operator_mcp_policy._REQUIRED_TARGET_KINDS`). This adapter resolves
the target run's OWN owning workspace from its already-governed `run.yaml`
-- the SAME read-only, fail-closed-to-`None` pattern
`swarm_start._resolve_run_context` uses for the identical field -- rather
than trusting any caller-supplied claim about ownership. A caller can
therefore only ingest a source into a run the ONE configured operator
identity's workspace already owns; a missing/foreign/malformed run resolves
to `None` and denies at the RBAC stage (H3) with the SAME `not_found` shape
an above-ceiling-sensitivity denial gets (H6/H7) -- never a distinguishing
leak.

**Confirmation binds `content` via digest, not raw text (F4 fix).** Raw
`content` is deliberately excluded from the canonical `input_payload` this
module builds -- `PolicyContext.canonical_digest()` hashes `input_payload`
verbatim, and embedding caller-supplied free text there would both risk the
capability stage's 64KiB payload-size gate for a large extraction and
reintroduce packet/content-derived text into a hashed, potentially-logged
structure -- the same convention `ImportOutcome.safe_dict()` already follows
for the sibling `external_report.import` adapter. Instead, a `sha256`
`content_digest` of `content` (plus `extra_limitations` and
`created_by_agent`, both short/bounded so included verbatim) IS bound into
`input_payload`, and therefore into `canonical_digest()`. A confirmation
minted for one `content` value cannot be replayed against a different one:
`invoke()` recomputes `content_digest` from whatever `content` the live call
actually supplies, so a mismatched `content` yields a mismatched canonical
digest, and the confirmation stage denies with `confirmation_mismatch`
before `_run()` -- and therefore before `ingest_source` -- is ever reached.

**`effective_sensitivity` is resolved structurally from the target run, not
from the caller (F3 fix).** The caller-supplied `sensitivity` parameter is
still forwarded to `ingest_source` unchanged -- it is the CONTENT
classification the new source card itself is filed under, exactly as before
-- but it is never what the ceiling guard (`_check_guard`, comparing
`ctx.effective_sensitivity` against `ctx.sensitivity_ceiling`) evaluates. A
caller cannot self-attest their way past the local sensitivity ceiling by
mislabeling `sensitivity="public"` on genuinely sensitive content: the
operation's `effective_sensitivity` is instead read from the TARGET run's
own already-governed `run.yaml` `sensitivity` field, the same read-only,
fail-closed-to-`None` pattern `swarm_start._resolve_run_context` uses for
the identical field (module docstring's "run target / cross-workspace gate"
section, above) -- a missing/foreign/malformed run resolves to `None`,
which `policy.resolve_effective_sensitivity` fails closed to the STRICTEST
label, never a permissive fallback value.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_cancel_resume_service import (
    ActionEffect,
    ActionSpec,
    ExecutionOutcome,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_operation_service import OperatorOperationService
from research_foundry.services import source_cards
from research_foundry.yamlio import load_yaml

from . import base

_logger = logging.getLogger(__name__)

__all__ = ["OPERATION_KIND", "SourceIngestAdapter", "ADAPTER", "invoke"]

OPERATION_KIND = "source.ingest"


def _resolved_within(root: Path, candidate: Path) -> Path | None:
    """M2 fix cycle 3 (F3.1/SEC2-1) -- AUTHORITATIVE, not advisory: returns
    the resolved, root-anchored `Path` when `candidate` is contained,
    `None` otherwise. Originally bool-returning (M2 fix cycle 2); the
    security re-gate found that a bool-returning validator lets the check
    and the DOWNSTREAM USE disagree about what a RELATIVE `candidate` means
    -- this function resolved a relative value against `root`, but the
    caller then forwarded the ORIGINAL, UNRESOLVED string to
    `source_cards.ingest_source`, which resolves relative paths against the
    server PROCESS's CWD, a different anchor entirely (SEC2-1: `locator=
    "secret.txt"` after chdir). Returning the resolved `Path` and requiring
    the caller to forward THAT (never the raw string) closes the anchor
    mismatch structurally.

    The exact resolve-then-contain posture `verify_bundle.
    _explicit_path_within_run` (F5) and `external_import._resolved_within`
    (SEC-1) establish: resolves both `root` and `candidate` (symlinks
    included) and requires `candidate` to land AT `root` or somewhere
    BENEATH it. Never probes whether the resolved `candidate` exists -- an
    existence check on a location outside the authorized boundary would
    itself be an oracle (F6/H6's own class of leak). `candidate` may be
    relative (joined under `root` first, still returned in resolved
    absolute form) or absolute (resolved as given)."""

    try:
        root_resolved = root.resolve()
        effective = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    except OSError as exc:
        _logger.warning(
            "operator_mcp_adapters.source_ingest: path resolution failed (%s) -- "
            "denying (never a permissive fallback)",
            type(exc).__name__,
        )
        return None
    if effective == root_resolved or root_resolved in effective.parents:
        return effective
    return None


#: F3.2 fix (M2 fix cycle 3, SEC2-2, BLOCKING) -- the ONLY URL schemes this
#: adapter ever treats as "fetch over the network", checked explicitly and
#: authoritatively HERE, before any dispatch to `source_cards.ingest_
#: source`. `"file"` was PREVIOUSLY included alongside `"http"`/`"https"` in
#: this family's own scheme check (M2 wave 1) on the reasoning that "its
#: fetch ... goes over the network, a separate concern" -- that reasoning
#: was wrong: `file:` is not a network scheme, and `source_cards._fetch_url`
#: (a canonical service, off limits to this leg) has no scheme allowlist of
#: its own, so a `file://` locator with `fetch=True` reached `urllib.
#: request.urlopen`, whose built-in `FileHandler` reads local files --
#: proven to read `/etc/passwd` verbatim, byte-identical, into a durable
#: ledger artifact, across `file:///etc/passwd`, `file://localhost/...`,
#: `FILE://...` (urlparse lowercases the scheme), and `file:/...`
#: (single-slash) variants alike. The MCP surface must not depend on a
#: downstream service being safe -- this allowlist is checked
#: UNCONDITIONALLY before `ingest_source` is ever called, regardless of
#: `fetch`, so `source_cards.py`'s own missing allowlist (filed separately,
#: a canonical-service defect outside this leg's files) never matters on
#: this route.
_ALLOWED_LOCATOR_SCHEMES = frozenset({"http", "https"})


def _locator_scheme(locator: str) -> str:
    """The lowercase URL scheme `urlparse` detects for `locator` (empty
    string if none). `urlparse` itself lowercases the scheme, so `FILE://
    ...`/`file://...` are indistinguishable here -- matching what the
    security re-gate proved: no case-based bypass is possible."""

    return urlparse(locator).scheme


def _looks_like_url(locator: str) -> bool:
    """`locator` has an ALLOWED (http/https) scheme -- used to decide
    whether `locator` needs workspace containment (a bare local path, or
    any locator with a scheme outside the allowlist -- the latter is
    refused outright before this even matters, see `_ALLOWED_LOCATOR_
    SCHEMES` -- does; an allowed URL locator does not, since its fetch, when
    `fetch=True`, goes over the network, a separate concern)."""

    return _locator_scheme(locator) in _ALLOWED_LOCATOR_SCHEMES


@dataclass(frozen=True)
class _RunContext:
    """Read-only, best-effort resolution of everything `source.ingest` needs
    from the target run's OWN already-governed state -- both fields are
    `None` on ANY resolution failure (missing run, malformed `run.yaml`,
    non-dict document, non-string/blank field), never a permissive
    fallback. Mirrors `swarm_start._resolve_run_context`'s identical
    `workspace_id`/`sensitivity` field resolution."""

    workspace_id: str | None
    sensitivity: str | None


def _resolve_run_context(run_id: str, paths: FoundryPaths) -> _RunContext:
    """See `_RunContext`'s own docstring. Swallows EVERY exception (missing
    run, malformed YAML, filesystem error) and resolves BOTH fields to
    `None` on ANY failure -- never a permissive fallback. Mirrors
    `swarm_start._resolve_run_context`'s identical field resolution.

    **M2 fix cycle 2 (path-containment sweep, sibling to SEC-1).** `run_id`
    is contained to `paths.runs` FIRST -- before `paths.run_paths(run_id)`
    is ever read -- so a traversal-shaped `run_id` (e.g. `".."`, legal
    against `operator_mcp_policy._TARGET_REF_PATTERN` since it contains no
    `/`) can never cause a read outside the `runs/` tree before that
    pattern would eventually (too late) reject it. See
    `external_import._resolve_run_workspace_id`'s identical fix for the
    full rationale."""

    if not _resolved_within(paths.runs, Path(run_id)):
        _logger.warning(
            "operator_mcp_adapters.source_ingest: run_id=%s escapes the authorized "
            "runs/ tree -- resolving context to None (deny, never a fallback)",
            run_id,
        )
        return _RunContext(None, None)

    try:
        run_doc = load_yaml(paths.run_paths(run_id).run_yaml)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.source_ingest: run.yaml lookup failed (%s) for "
            "run_id=%s -- resolving owning workspace and sensitivity to None "
            "(deny, never a fallback)",
            type(exc).__name__,
            run_id,
        )
        return _RunContext(None, None)
    if not isinstance(run_doc, dict):
        return _RunContext(None, None)
    workspace_id = run_doc.get("workspace_id")
    workspace_id = workspace_id if isinstance(workspace_id, str) and workspace_id else None
    sensitivity = run_doc.get("sensitivity")
    sensitivity = sensitivity if isinstance(sensitivity, str) else None
    return _RunContext(workspace_id, sensitivity)


def _result_to_dict(result: "source_cards.IngestResult") -> dict[str, Any]:
    return {
        "status": "completed",
        "source_card_id": result.source_card_id,
        "path": str(result.path),
        "source_type": result.source_type,
        "degraded": result.degraded,
        "extraction_status": result.extraction_status,
        "canonical_refs_available": True,
    }


def invoke(
    *,
    locator: str,
    run_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    source_type: str = "other",
    sensitivity: str = "personal",
    title: str | None = None,
    created_by_agent: str = "rf_source_carder",
    fetch: bool = False,
    content: str | None = None,
    extra_limitations: list[str] | None = None,
    extraction_status: str | None = None,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `source.ingest` Operator MCP tool.

    Deliberately accepts NO `identity`/`AuthIdentity`-shaped parameter and
    NO `assertion_registry_workspace_id` parameter -- both resolved
    structurally from `ctx.identity` (module docstring, decision D2).

    Also deliberately accepts NO `sensitivity_ceiling` parameter (H7 defect
    fix, `8b694d5`) -- resolved structurally via `resolve_local_sensitivity_
    ceiling`, exactly like every other adapter in this family.

    `confirmation_record`/`presented_token` are the caller's already-minted
    confirmation for this exact request -- both are ignored entirely when
    `dry_run=True`.
    """

    from . import resolve_local_sensitivity_ceiling  # lazy: see operator_mcp_adapters/__init__.py's own docstring -- avoids the circular import a module-level import back into the package would create

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)

    run_ctx = _resolve_run_context(run_id, resolved_paths)
    run_workspace_id = run_ctx.workspace_id
    # F3 fix: effective_sensitivity (what the ceiling guard evaluates) is
    # resolved STRUCTURALLY from the target run's own already-governed
    # `run.yaml` -- never from the caller-supplied `sensitivity` parameter
    # (that value is still forwarded to `ingest_source` below as the new
    # source card's own content classification, unchanged; see module
    # docstring's "effective_sensitivity is resolved structurally" section).
    # A missing/foreign/malformed run resolves to None here, which
    # resolve_effective_sensitivity fails closed to the STRICTEST label.
    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    # F4 fix: bind content (via digest, never raw text -- see module
    # docstring), extra_limitations, and created_by_agent into the canonical
    # payload the confirmation digest covers. Every input that reaches
    # `ingest_source` below must be bound here; a confirmation minted
    # without content (or for different content) must not authorize
    # executing WITH content.
    content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest() if content else None

    input_payload: dict[str, Any] = {
        "locator": locator,
        "run_id": run_id,
        "source_type": source_type,
        "sensitivity": sensitivity,
        "title": title,
        "fetch": fetch,
        "extraction_status": extraction_status,
        "content_digest": content_digest,
        "extra_limitations": extra_limitations,
        "created_by_agent": created_by_agent,
    }
    # PolicyContext.canonical_digest() hashes input_payload verbatim -- drop
    # None-valued optionals so two callers who both omit the same optional
    # produce the SAME canonical digest (mirrors run_plan.py's own rationale).
    input_payload = {k: v for k, v in input_payload.items() if v is not None}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(policy.TargetRef("run", run_id),),
        # H3: run_id's OWN recorded owning workspace (never the caller's
        # say-so) -- a missing/foreign/malformed run resolves to None and
        # denies at the rbac stage (module docstring).
        resolved_target_workspaces=(run_workspace_id,),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    # Captures ingest_source's own IngestResult so `_build_result` can read
    # the real canonical refs after `run_or_replay` executes this action --
    # empty on a genuine exact-replay of an already-terminal operation (the
    # same documented "replay result-recovery gap" run_plan.py/swarm_start.py
    # already report for their own targets; operator_receipt_service.py is
    # out of this leg's file ownership).
    captured: list["source_cards.IngestResult"] = []

    def _run() -> ActionEffect:
        assert ctx.identity is not None
        # F3.2 fix (M2 fix cycle 3, SEC2-2, BLOCKING) -- an explicit scheme
        # allowlist, checked UNCONDITIONALLY before any dispatch to
        # `ingest_source`, regardless of `fetch`/`content`. See
        # `_ALLOWED_LOCATOR_SCHEMES`'s own module-level docstring for the
        # full `file://` bypass this closes. A locator with NO scheme at
        # all (a bare local path) is not refused here -- it is handled by
        # the resolve-and-substitute branch below instead.
        locator_scheme = _locator_scheme(locator)
        if locator_scheme and locator_scheme not in _ALLOWED_LOCATOR_SCHEMES:
            raise RuntimeError(
                f"source.ingest: locator scheme {locator_scheme!r} is not permitted -- "
                "only http(s) URLs or local workspace paths are accepted"
            )
        # F3.1 fix (M2 fix cycle 3, SEC2-1) -- resolve-and-substitute, not
        # merely validate: `source_cards.ingest_source` unconditionally
        # treats `locator` as a local file (`Path(locator).exists() and
        # .is_file()`) and reads its FULL CONTENT whenever `content` is not
        # already supplied and `locator` has no (allowed) URL scheme.
        # `content is not None` bypasses that local-file branch entirely
        # (source_cards.py's own precedence order), so this only applies
        # when the caller is relying on `ingest_source`'s own local-read
        # behavior. The RESOLVED, root-anchored path is forwarded to
        # `ingest_source` -- NEVER the caller's raw string -- closing the
        # SAME check/use anchor mismatch SEC2-1 found for `packet_dir`: the
        # old bool-returning guard resolved a relative `locator` against
        # the workspace root, then forwarded the ORIGINAL unresolved string,
        # which `Path(locator)` inside `ingest_source` resolves against the
        # server PROCESS's CWD instead (`locator="secret.txt"` after
        # `chdir`). Checked HERE, inside `_run()`, after authorization (F6
        # posture). Genuine URL locators are unaffected -- their content
        # only ever reaches this process over the network.
        effective_locator = locator
        if content is None and not locator_scheme:
            resolved_locator = _resolved_within(resolved_paths.root, Path(locator))
            if resolved_locator is None:
                raise RuntimeError(
                    "source.ingest: locator escapes the authorized workspace tree"
                )
            effective_locator = str(resolved_locator)
        result = source_cards.ingest_source(
            effective_locator,
            run_id=run_id,
            source_type=source_type,
            sensitivity=sensitivity,
            title=title,
            created_by_agent=created_by_agent,
            fetch=fetch,
            content=content,
            extra_limitations=extra_limitations,
            # Decision D2: structurally resolved from identity, never the
            # CLI's own hard-coded single-operator literal.
            assertion_registry_workspace_id=ctx.identity.workspace_id,
            paths=resolved_paths,
            extraction_status=extraction_status,
        )
        captured.append(result)
        effect_ref = f"{OPERATION_KIND}:{run_id}:{result.source_card_id}"
        return ActionEffect(
            effect_kind="source_ingested",
            effect_digest=hashlib.sha256(effect_ref.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        # base.run_pipeline only ever calls this for "completed"/"canceled"
        # -- "failed"/"denied" are already turned into a build_error
        # envelope before build_result is reached.
        if execution.status == "completed" and captured:
            return _result_to_dict(captured[0])
        if execution.status == "completed":
            return {
                "status": "completed",
                "replayed": True,
                "canonical_refs_available": False,
            }
        return {"status": execution.status, "replayed": execution.replayed}

    action_manifest: dict[str, Any] = {
        "adapter": OPERATION_KIND,
        "run_id": run_id,
        "locator": locator,
        "source_type": source_type,
        "sensitivity": sensitivity,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="ingest_source", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


@dataclass(frozen=True)
class SourceIngestAdapter:
    """`base.OperatorAdapter` Protocol implementation for `source.ingest`."""

    operation_kind: str = OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke(**kwargs)


ADAPTER = SourceIngestAdapter()
base.register(ADAPTER)
