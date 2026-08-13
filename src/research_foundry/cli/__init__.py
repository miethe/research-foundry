"""``rf`` command-line interface (Typer).

This package wires the service layer into the ``rf`` command group (spec §10).
Command bodies live in ``services/*`` and ``validators/*``; the CLI stays thin:
parse args → call a service → render result → translate errors to exit codes.

NOTE: This is the Wave-0 skeleton. Subcommand groups are attached by
``_wire()`` which imports service-backed command modules when present, so the
CLI degrades gracefully while the service layer is being built.

Sub-apps defined in ``cli/commands/`` are wired into the root ``rf`` Typer
application in ``cli_commands.py`` via ``app.add_typer(...)``.
"""

from __future__ import annotations

import typer
from rich.console import Console

from .._version_provenance import _emit as _emit_version
from ..config import FoundryConfig
from ..errors import ExitCode, RFError
from ..schemas import SchemaRegistry

#: PyPI distribution name — the key `importlib.metadata` resolves, NOT the import
#: package (`research_foundry`). Provenance is looked up by distribution because
#: that is what carries the declared version and the PEP 610 editable marker.
_DIST_NAME = "research-foundry"

app = typer.Typer(
    name="rf",
    help="Research Foundry — evidence-first research control plane.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    """Eager ``--version`` handler: print provenance and exit 0 before anything else runs.

    Routed through the vendored helper's ``_emit`` rather than ``version_string`` so the
    ``AOS_VERSION_JSON`` env var keeps working — that is how the fleet-wide aggregator
    collects structured output from six CLIs without a per-CLI ``--json`` flag.
    """

    if not value:
        return
    _emit_version(_DIST_NAME, prog_name="rf")
    raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def _root(
    _version: bool = typer.Option(
        False,
        "--version",
        help="Show version provenance (declared version + checkout identity) and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Research Foundry — evidence-first research control plane."""

    # `invoke_without_command=True` is what lets `rf --version` run with no subcommand;
    # bare `rf` still prints help because the group carries `no_args_is_help=True`.


@app.command()
def version() -> None:
    """Print the Research Foundry version provenance (same output as ``rf --version``)."""

    _emit_version(_DIST_NAME, prog_name="rf")


@app.command()
def doctor() -> None:
    """Check the workspace + environment and report readiness (spec §10.15)."""

    from rich.table import Table

    cfg = FoundryConfig.load()
    reg = SchemaRegistry()
    table = Table(title="rf doctor", show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    root = cfg.paths.root
    table.add_row("workspace root", "ok", str(root))
    table.add_row("foundry.yaml", "ok" if cfg.paths.foundry_yaml.exists() else "missing",
                  str(cfg.paths.foundry_yaml))
    n_schemas = len(reg.names())
    table.add_row("schemas", "ok" if n_schemas else "missing", f"{n_schemas} schema(s)")
    table.add_row("governance policy", "ok" if cfg.governance else "missing",
                  f"{len(cfg.policy_rules())} rule(s)")
    table.add_row("model profiles", "ok" if cfg.model_profiles else "missing",
                  f"{len(cfg.model_profiles.get('model_profiles', {}))} profile(s)")

    try:
        from ..adapters import load_all

        adapters = load_all()
        avail = sum(1 for a in adapters.values() if a.available())
        table.add_row("adapters", "ok", f"{avail}/{len(adapters)} available")
    except Exception as exc:  # noqa: BLE001
        table.add_row("adapters", "warn", str(exc))

    # Integration reachability — informational only; offline is not an error.
    try:
        from ..integrations import get_arc_client, get_intenttree_client

        arc_status = "reachable" if get_arc_client().available() else "unreachable"
        it_status = "reachable" if get_intenttree_client().available() else "unreachable"
        table.add_row(
            "integrations",
            "ok",
            f"arc {arc_status} / intenttree {it_status}",
        )
    except Exception as exc:  # noqa: BLE001
        table.add_row("integrations", "warn", str(exc))

    console.print(table)


@app.command(name="schema")
def schema(
    action: str = typer.Argument(..., help="validate | list"),
    target: str = typer.Argument(None, help="instance file (for validate)"),
    schema_name: str = typer.Option(None, "--schema", "-s", help="schema name override"),
) -> None:
    """Validate an instance file or list available schemas (spec §10.1)."""

    reg = SchemaRegistry()
    if action == "list":
        for name in reg.names():
            console.print(f"- {name}")
        return
    if action != "validate" or not target:
        err_console.print("[red]usage: rf schema validate <file> [--schema NAME][/red]")
        raise typer.Exit(int(ExitCode.USAGE))

    from pathlib import Path

    from ..frontmatter import split_frontmatter
    from ..yamlio import loads_yaml

    text = Path(target).read_text(encoding="utf-8")
    if target.endswith((".md", ".markdown")):
        instance, _ = split_frontmatter(text)
    else:
        instance = loads_yaml(text)

    name = schema_name or _guess_schema(target, instance)
    if not name:
        err_console.print("[red]could not infer schema; pass --schema NAME[/red]")
        raise typer.Exit(int(ExitCode.USAGE))

    result = reg.validate(instance, name)
    if result.ok:
        console.print(f"[green]valid[/green] ({name})")
        return
    err_console.print(f"[red]invalid[/red] ({name})")
    for e in result.errors:
        err_console.print(f"  - {e}")
    raise typer.Exit(int(ExitCode.SCHEMA))


def _guess_schema(path: str, instance: object) -> str | None:
    """Best-effort schema inference from a ``type`` field, filename, or shape."""

    from pathlib import Path

    reg = SchemaRegistry()
    if isinstance(instance, dict):
        t = instance.get("type") or instance.get("schema") or ""
        if isinstance(t, str) and reg.has(t):
            return t
        # foundry.yaml has a top-level `foundry:` wrapper, not a `type` field.
        if "foundry" in instance and reg.has("foundry"):
            return "foundry"
    if Path(path).name == "foundry.yaml" and reg.has("foundry"):
        return "foundry"
    return None


def _wire() -> None:
    """Attach service-backed subcommand groups when their modules are present.

    Each ``services.<x>_cli`` (or ``cli_<x>``) module may expose a Typer ``app``
    or a ``register(app)`` function. Missing modules are skipped so the CLI
    works incrementally during the build.
    """

    import importlib

    candidates = [
        "research_foundry.cli_commands",  # aggregated command wiring (Wave 3)
        "research_foundry.services.search_router.cli",  # rf search / rf fetch (Wave 3)
    ]
    for mod_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue
        register = getattr(mod, "register", None)
        if callable(register):
            register(app)


_wire()


def main() -> None:  # console-script style entry, in addition to ``app``
    try:
        app()
    except RFError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise SystemExit(int(exc.exit_code)) from exc


__all__ = ["app", "main"]
