"""``rf knowledge`` sub-app -- CLI parity for the RF Knowledge MCP (KMCP-5.1).

Thin command layer over
:mod:`research_foundry.services.knowledge_access` (the shared, governed P2/P3
read service) -- this module contains ONLY argument parsing and JSON
rendering (invariant 4, "one service contract: transports contain parsing/
rendering only"). It adds no local filtering, ranking, redaction, receipt, or
URL logic of its own; every subcommand is a thin wrapper around the SAME
:class:`~research_foundry.services.knowledge_access.KnowledgeAccessService`
methods :mod:`research_foundry.knowledge_mcp.registry` calls for its
``rf_search``/``rf_fetch``/``rf_source_get``/``rf_assertion_get``/
``rf_report_get``/``rf_run_get`` tools (KMCP-4.3) -- CLI subcommand names
drop the ``rf_`` prefix (and use hyphens for the typed getters) but resolve
the identical ``tool=`` string into
:func:`knowledge_access.resolve_context` so a caller-carried activity
receipt always names the correct tool (``knowledge_activity_receipt.
schema.yaml``'s ``tool`` field is one of the eight frozen tool names, never
a CLI-invented string).

Subcommands::

    rf knowledge search QUERY [--kind ... --limit N --cursor C
                                --parent-run-ref REF --sensitivity-threshold T]
    rf knowledge fetch ID [--cursor C --parent-run-ref REF
                            --sensitivity-threshold T]
    rf knowledge source-get ID [--cursor C --parent-run-ref REF
                                 --sensitivity-threshold T]
    rf knowledge assertion-get ID [...]
    rf knowledge report-get ID [...]
    rf knowledge run-get ID [...]

Every subcommand always prints JSON to stdout -- this surface is meant for
automation, not interactive browsing, so there is no ``--json`` toggle (JSON
is the only output mode).

**Local trust (CLI parity with the stdio MCP transport).** Unlike the
GET-only HTTP API (KMCP-5.2), which resolves ``request.state.identity`` from
configured auth middleware, this CLI has no session/login concept of its
own -- it always resolves ``identity=None``, the SAME "local trust" default
the stdio MCP process (KMCP-4.1) and every existing ``rf`` CLI read command
already use. If WKSP-304 row-level isolation is active and a read
unconditionally requires a non-``None`` identity to resolve anything (e.g.
every ``assertion``-kind read, per
:class:`knowledge_access.AssertionKindProjector`), that read denies here
exactly as it does through the stdio MCP transport -- see
``research_foundry.knowledge_mcp.registry``'s own "Local-trust caveat"
docstring for the identical, expected v1 limitation.

**Safe denial (decisions-block Section 0/3 Risk 2, KMCP-OQ-1).** ``search``
never raises for a policy denial or a malformed query -- any
:class:`knowledge_access.KnowledgeAccessError` collapses to the SAME empty,
receipt-less ``{"results": [], "next_cursor": null, "truncated": false}``
shape a zero-match query would produce, exit code 0. ``fetch`` and the four
typed getters map EVERY such error to the SAME generic, detail-free denial
message on stderr (never the exception's own internal ``reason``) and exit
1 -- a caller can never distinguish a missing id, a hidden id, a cross-kind
id, or a local-trust-denied assertion id from one another by CLI output
(mirrors ``research_foundry.knowledge_mcp.registry``'s identical "Safe
denial" contract).

Registered onto the root ``rf`` Typer app from ``cli_commands.register()``
(see that module's own ``agent-job`` import for the established wiring
pattern already used for a ``cli/commands/`` sub-app)::

    from .cli.commands.knowledge import knowledge_app
    app.add_typer(knowledge_app, name="knowledge")
"""

from __future__ import annotations

import json as _json
from typing import Any, NoReturn

import typer
from rich.console import Console

from research_foundry.errors import RFError
from research_foundry.paths import FoundryPaths
from research_foundry.services import knowledge_access as ka

knowledge_app = typer.Typer(
    help="Knowledge read surface -- CLI parity for the RF Knowledge MCP (KMCP-5.1)."
)

console = Console()
err_console = Console(stderr=True)

# Same generic, detail-free denial message every other Knowledge transport
# uses (research_foundry.knowledge_mcp.registry._FETCH_DENIED_MESSAGE) --
# reimplemented by value, not imported, so this CLI module never depends on
# the optional `mcp` SDK's package (research_foundry.knowledge_mcp is an
# independent, optional-SDK process boundary -- invariant 1; this CLI is
# always installed, unlike that extra).
_FETCH_DENIED_MESSAGE = "Unable to fetch the requested knowledge id."

# Shared option objects (module-level singletons so every subcommand's
# --help text and defaults stay byte-identical -- mirrors this repo's own
# `_PATHS_DEP`/`_TERM_QUERY` singleton convention in api/routers/catalog.py).
_KIND_OPTION = typer.Option(
    None,
    "--kind",
    help=(
        "Restrict to a knowledge kind (repeatable): source, assertion, "
        "report_draft, report_final, run. Narrows eligibility; never widens it."
    ),
)
_CURSOR_OPTION = typer.Option(
    None, "--cursor", help="Byte-offset pagination cursor from a prior response's next_cursor."
)
_PARENT_RUN_REF_OPTION = typer.Option(
    None,
    "--parent-run-ref",
    help="Optional caller-supplied correlation hint echoed into the activity receipt.",
)
_SENSITIVITY_OPTION = typer.Option(
    None,
    "--sensitivity-threshold",
    help="Override foundry.yaml viewer.sensitivity_threshold for this call.",
)


def _print(payload: dict[str, Any]) -> None:
    typer.echo(_json.dumps(payload, ensure_ascii=False, indent=2))


def _fail(message: str, code: int = 1) -> NoReturn:
    err_console.print(f"[red]{message}[/red]")
    raise typer.Exit(code)


def _bootstrap_projectors(paths: FoundryPaths) -> None:
    """Seed :mod:`knowledge_access`'s process-global projector registry for
    THIS CLI invocation's resolved workspace.

    Every ``rf knowledge`` invocation is a fresh OS process, so (unlike the
    long-lived ``rf-knowledge-mcp`` stdio process, which bootstraps once per
    server lifetime) this must run once per invocation, before any service
    call -- otherwise every kind would resolve through the P2 skeleton's own
    "no projector registered" exit condition (empty results /
    ``projection_unavailable`` denial for everything). Reimplemented by
    value from ``research_foundry.knowledge_mcp.registry._bootstrap_
    projectors`` (not imported -- this CLI never depends on the optional
    ``mcp`` SDK package).
    """

    ka.register_projector("source", ka.SourceKindProjector(paths))
    ka.register_projector("assertion", ka.AssertionKindProjector(paths))
    ka.register_projector("report_draft", ka.ReportKindProjector(paths, target_kind="report_draft"))
    ka.register_projector("report_final", ka.ReportKindProjector(paths, target_kind="report_final"))
    ka.register_projector("run", ka.RunKindProjector(paths))


def _context(paths: FoundryPaths, tool: str, sensitivity_threshold: str | None) -> ka.KnowledgeAccessContext:
    """Resolve one call's :class:`knowledge_access.KnowledgeAccessContext`.

    Always ``identity=None`` (local trust; see module docstring). Raises via
    :func:`_fail` -- never a raw traceback -- if ``sensitivity_threshold`` is
    not a recognised label (``export_service.resolve_threshold``'s own
    fail-closed validation, surfaced here as a real usage error since a
    caller typo in this flag is a CLI misconfiguration, not a policy
    denial).
    """

    try:
        return ka.resolve_context(
            paths, tool=tool, identity=None, sensitivity_threshold=sensitivity_threshold
        )
    except RFError as exc:
        _fail(str(exc), int(getattr(exc, "exit_code", 1)))


def _typed_get(
    tool: str,
    expected_kinds: frozenset[str],
    *,
    id: str,
    cursor: str | None,
    parent_run_ref: str | None,
    sensitivity_threshold: str | None,
) -> None:
    """Shared body for every typed getter (source-get/assertion-get/
    report-get/run-get) -- a THIN ``fetch_extended`` call additionally gated
    to ``expected_kinds``, checked via :func:`knowledge_access.
    parse_knowledge_id` BEFORE the underlying governed read authority is
    ever touched (mirrors ``research_foundry.knowledge_mcp.registry``'s
    identical ``_typed_get`` helper)."""

    paths = FoundryPaths.discover()
    _bootstrap_projectors(paths)
    context = _context(paths, tool, sensitivity_threshold)
    service = ka.KnowledgeAccessService(paths)
    try:
        resolved_kind, _opaque = ka.parse_knowledge_id(id)
        if resolved_kind not in expected_kinds:
            raise ka.KnowledgeDenied("kind_not_eligible")
        document = service.fetch_extended(
            context,
            knowledge_id=id,
            cursor=cursor,
            parent_run_ref=parent_run_ref,
            include_receipt=True,
        )
    except ka.KnowledgeAccessError:
        _fail(_FETCH_DENIED_MESSAGE)
    _print(document.to_dict())


@knowledge_app.command("search")
def search(
    query: str = typer.Argument(..., help=f"Search query (<= {ka.QUERY_MAX_LENGTH} chars)."),
    kind: list[str] | None = _KIND_OPTION,
    limit: int = typer.Option(
        ka.RF_SEARCH_DEFAULT_LIMIT,
        "--limit",
        help=f"Max results (server-clamped to 1-{ka.RF_SEARCH_MAX_RESULTS}).",
    ),
    cursor: str | None = _CURSOR_OPTION,
    parent_run_ref: str | None = _PARENT_RUN_REF_OPTION,
    sensitivity_threshold: str | None = _SENSITIVITY_OPTION,
) -> None:
    """RF-extended knowledge search (``rf_search`` parity, KMCP-FR-5).

    Safe denial: a malformed query or a fully-denied context prints the same
    empty-results shape a zero-match query would, exit code 0 (see module
    docstring).
    """

    paths = FoundryPaths.discover()
    _bootstrap_projectors(paths)
    context = _context(paths, "rf_search", sensitivity_threshold)
    service = ka.KnowledgeAccessService(paths)
    try:
        outcome = service.search_extended(
            context,
            query=query,
            kinds=kind or None,
            limit=limit,
            cursor=cursor,
            parent_run_ref=parent_run_ref,
            include_receipt=True,
        )
    except ka.KnowledgeAccessError:
        outcome = ka.RfKnowledgeSearchOutcome()
    _print(outcome.to_dict())


@knowledge_app.command("fetch")
def fetch(
    id: str = typer.Argument(..., help="Opaque knowledge id (rfk:v1:<kind>:<opaque>)."),
    cursor: str | None = _CURSOR_OPTION,
    parent_run_ref: str | None = _PARENT_RUN_REF_OPTION,
    sensitivity_threshold: str | None = _SENSITIVITY_OPTION,
) -> None:
    """RF-extended knowledge fetch (``rf_fetch`` parity, KMCP-FR-5).

    Denies generically (see module docstring's "Safe denial" section) for a
    malformed, missing, hidden, cross-workspace, rights-denied, or
    stale/unavailable-projection id -- exit 1, same message every time.
    """

    paths = FoundryPaths.discover()
    _bootstrap_projectors(paths)
    context = _context(paths, "rf_fetch", sensitivity_threshold)
    service = ka.KnowledgeAccessService(paths)
    try:
        document = service.fetch_extended(
            context,
            knowledge_id=id,
            cursor=cursor,
            parent_run_ref=parent_run_ref,
            include_receipt=True,
        )
    except ka.KnowledgeAccessError:
        _fail(_FETCH_DENIED_MESSAGE)
    _print(document.to_dict())


@knowledge_app.command("source-get")
def source_get(
    id: str = typer.Argument(..., help="Opaque knowledge id (must be a 'source'-kind id)."),
    cursor: str | None = _CURSOR_OPTION,
    parent_run_ref: str | None = _PARENT_RUN_REF_OPTION,
    sensitivity_threshold: str | None = _SENSITIVITY_OPTION,
) -> None:
    """Typed getter scoped to the ``source`` kind (``rf_source_get`` parity)."""

    _typed_get(
        "rf_source_get",
        frozenset({"source"}),
        id=id,
        cursor=cursor,
        parent_run_ref=parent_run_ref,
        sensitivity_threshold=sensitivity_threshold,
    )


@knowledge_app.command("assertion-get")
def assertion_get(
    id: str = typer.Argument(..., help="Opaque knowledge id (must be an 'assertion'-kind id)."),
    cursor: str | None = _CURSOR_OPTION,
    parent_run_ref: str | None = _PARENT_RUN_REF_OPTION,
    sensitivity_threshold: str | None = _SENSITIVITY_OPTION,
) -> None:
    """Typed getter scoped to the ``assertion`` kind (``rf_assertion_get`` parity).

    Local trust caveat: like the stdio MCP transport, this always denies
    generically while ``identity`` is ``None`` and WKSP-304 isolation
    requires a workspace-bearing identity for every assertion read -- see
    module docstring.
    """

    _typed_get(
        "rf_assertion_get",
        frozenset({"assertion"}),
        id=id,
        cursor=cursor,
        parent_run_ref=parent_run_ref,
        sensitivity_threshold=sensitivity_threshold,
    )


@knowledge_app.command("report-get")
def report_get(
    id: str = typer.Argument(
        ..., help="Opaque knowledge id (must be a 'report_draft' or 'report_final'-kind id)."
    ),
    cursor: str | None = _CURSOR_OPTION,
    parent_run_ref: str | None = _PARENT_RUN_REF_OPTION,
    sensitivity_threshold: str | None = _SENSITIVITY_OPTION,
) -> None:
    """Typed getter addressing BOTH ``report_draft`` and ``report_final`` ids
    (KMCP-OQ-2 -- two distinct kinds, one getter name; ``rf_report_get`` parity)."""

    _typed_get(
        "rf_report_get",
        frozenset({"report_draft", "report_final"}),
        id=id,
        cursor=cursor,
        parent_run_ref=parent_run_ref,
        sensitivity_threshold=sensitivity_threshold,
    )


@knowledge_app.command("run-get")
def run_get(
    id: str = typer.Argument(..., help="Opaque knowledge id (must be a 'run'-kind id)."),
    cursor: str | None = _CURSOR_OPTION,
    parent_run_ref: str | None = _PARENT_RUN_REF_OPTION,
    sensitivity_threshold: str | None = _SENSITIVITY_OPTION,
) -> None:
    """Typed getter scoped to the ``run`` kind (``rf_run_get`` parity)."""

    _typed_get(
        "rf_run_get",
        frozenset({"run"}),
        id=id,
        cursor=cursor,
        parent_run_ref=parent_run_ref,
        sensitivity_threshold=sensitivity_threshold,
    )


__all__ = ["knowledge_app"]
