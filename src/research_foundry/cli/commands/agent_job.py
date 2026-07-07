"""``rf agent-job`` sub-app — CLI parity for the Agent Jobs API (FR-20).

Provides five subcommands that mirror the REST contract in
``research_foundry.api.routers.agent_jobs``:

  rf agent-job launch   -- POST /api/agent-jobs
  rf agent-job list     -- local scan of workspace agent_jobs/ dir
  rf agent-job stream   -- GET  /api/agent-jobs/{id}/events  (SSE)
  rf agent-job accept   -- POST /api/agent-jobs/{id}/accept
  rf agent-job status   -- GET  /api/agent-jobs/{id}

Transport strategy
------------------
Commands that can be satisfied entirely from on-disk state (``list``,
``status``, ``stream`` read-only path) call the :class:`AgentJobService`
directly and never require a running server.

Commands that mutate state (``launch``, ``accept``) fall back to
``httpx`` when the server appears to be running; when the server is not
reachable they exercise the service layer directly where possible and
print a clear message for operations that genuinely require the API
(e.g. ``launch`` needs governance guard + subprocess spawn).

Wire-up instruction
-------------------
To attach this sub-app to the root ``rf`` Typer app, add the following
two lines inside the ``register(app)`` function in ``cli_commands.py``
(after the existing ``app.add_typer(...)`` calls)::

    from .cli.commands.agent_job import agent_job_app
    app.add_typer(agent_job_app, name="agent-job")
"""

from __future__ import annotations

import json as _json
import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

agent_job_app = typer.Typer(help="Agent-job lifecycle management (FR-20).")

console = Console()
err_console = Console(stderr=True)

# Default host/port used by ``rf serve``.
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 7432


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _api_base(host: str, port: int) -> str:
    return f"http://{host}:{port}/api"


def _fail(msg: str, code: int = 1) -> None:
    err_console.print(f"[red]{msg}[/red]")
    raise typer.Exit(code)


def _get_service() -> tuple[Any, Any]:
    """Return ``(AgentJobService, FoundryPaths)``; exit with an error if unavailable."""
    try:
        from research_foundry.paths import FoundryPaths
        from research_foundry.services.agent_job_service import AgentJobService

        paths = FoundryPaths.discover()
        return AgentJobService(paths), paths
    except Exception as exc:  # noqa: BLE001
        _fail(f"Could not initialise AgentJobService: {exc}")


def _probe_server(host: str, port: int) -> bool:
    """Return True if the RF serve API is reachable (fast probe)."""
    try:
        import httpx

        resp = httpx.get(f"http://{host}:{port}/health", timeout=1.0)
        return resp.status_code < 500
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# rf agent-job launch
# ---------------------------------------------------------------------------


@agent_job_app.command("launch")
def launch(
    provider: str = typer.Option(..., "--provider", help="Agent provider id (e.g. claude_agent_sdk, openai_agents)"),
    project_id: str = typer.Option("default", "--project-id", help="Project id for the job"),
    request_kind: str = typer.Option("research", "--request-kind", help="Logical request kind (e.g. research, synthesis)"),
    policy_snapshot: Path = typer.Option(
        None,
        "--policy-snapshot",
        exists=True,
        help="Path to a JSON/YAML file containing the policy snapshot (allowed_tools, data_scopes, …)",
    ),
    model_profile: str = typer.Option("rf_extract_cheap", "--model-profile", help="Model profile key"),
    host: str = typer.Option(_DEFAULT_HOST, "--host", help="rf serve host"),
    port: int = typer.Option(_DEFAULT_PORT, "--port", help="rf serve port"),
    json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
) -> None:
    """Launch a new agent job via the RF serve API.

    Requires a running ``rf serve`` instance (governance guard and subprocess
    spawn both happen server-side).  Pass ``--policy-snapshot PATH`` with a JSON
    file containing at minimum ``allowed_tools`` and ``data_scopes`` fields.
    """
    try:
        import httpx
    except ImportError:
        _fail("httpx is required for 'rf agent-job launch'. Install with: pip install httpx")

    if not _probe_server(host, port):
        _fail(
            f"rf serve is not reachable at {host}:{port}. "
            "Start it with 'rf serve' before launching agent jobs."
        )

    # Load policy snapshot from file (or use a minimal default).
    policy: dict[str, Any] = {"allowed_tools": [], "data_scopes": []}
    if policy_snapshot:
        raw = policy_snapshot.read_text(encoding="utf-8")
        if policy_snapshot.suffix in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore[import-untyped]
                policy = yaml.safe_load(raw) or policy
            except ImportError:
                _fail("PyYAML is required to load a .yaml policy snapshot: pip install pyyaml")
        else:
            policy = _json.loads(raw)

    body = {
        "provider": provider,
        "model_profile": model_profile,
        "request_kind": request_kind,
        "policy_snapshot": policy,
        "project_id": project_id,
    }

    try:
        resp = httpx.post(
            f"{_api_base(host, port)}/agent-jobs",
            json=body,
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        _fail(f"Request to rf serve failed: {exc}")

    if resp.status_code not in (200, 201):
        err_console.print(f"[red]HTTP {resp.status_code}[/red] {resp.text}")
        raise typer.Exit(1)

    data = resp.json()
    if json_out:
        typer.echo(_json.dumps(data, ensure_ascii=False, indent=2))
        return

    job_id = data.get("agent_job_id", "?")
    status = data.get("status", "?")
    console.print(f"[green]launched[/green] {job_id}  (status={status})")
    typer.echo(f"agent_job_id={job_id}")


# ---------------------------------------------------------------------------
# rf agent-job list
# ---------------------------------------------------------------------------


@agent_job_app.command("list")
def list_jobs(
    status: str = typer.Option(None, "--status", help="Filter by status (e.g. running, completed, failed)"),
    limit: int = typer.Option(50, "--limit", help="Maximum number of jobs to show"),
    sensitivity_threshold: str = typer.Option(
        None,
        "--sensitivity-threshold",
        help="Exclude jobs whose sensitivity exceeds this level (e.g. public, personal, work_sensitive)",
    ),
    json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
) -> None:
    """List agent jobs by scanning the workspace ``agent_jobs/`` directory.

    Reads persisted ``job.json`` files directly — does not require a running
    ``rf serve`` instance.
    """
    svc, paths = _get_service()

    job_dir: Path = paths.agent_jobs
    if not job_dir.exists():
        console.print("[yellow]no agent_jobs directory found (no jobs yet)[/yellow]")
        return

    jobs: list[dict[str, Any]] = []
    for job_json in sorted(job_dir.glob("*/job.json")):
        try:
            data = _json.loads(job_json.read_text(encoding="utf-8"))
            jobs.append(data)
        except Exception:  # noqa: BLE001
            continue

    # Filters
    if status:
        jobs = [j for j in jobs if j.get("status") == status]

    # Sensitivity filter (exclude jobs whose sensitivity rank exceeds threshold).
    _SENS_ORDER = {
        "public": 0,
        "personal": 1,
        "work_sensitive": 2,
        "client_sensitive": 3,
        "top_secret": 4,
    }
    if sensitivity_threshold:
        threshold_rank = _SENS_ORDER.get(sensitivity_threshold, len(_SENS_ORDER))
        jobs = [
            j for j in jobs
            if _SENS_ORDER.get(
                str((j.get("policy_snapshot") or {}).get("sensitivity") or "public"), 0
            ) <= threshold_rank
        ]

    jobs = jobs[:limit]

    if json_out:
        typer.echo(_json.dumps(jobs, ensure_ascii=False, indent=2))
        return

    if not jobs:
        console.print("[yellow]no agent jobs found[/yellow]")
        return

    table = Table(title="agent jobs", show_header=True, header_style="bold")
    table.add_column("job_id")
    table.add_column("provider")
    table.add_column("request_kind")
    table.add_column("status")
    table.add_column("created_at")
    for j in jobs:
        table.add_row(
            j.get("agent_job_id", ""),
            j.get("provider", ""),
            j.get("request_kind", ""),
            j.get("status", ""),
            str(j.get("created_at", "")),
        )
    console.print(table)
    console.print(f"[dim]{len(jobs)} job(s)[/dim]")


# ---------------------------------------------------------------------------
# rf agent-job stream
# ---------------------------------------------------------------------------


@agent_job_app.command("stream")
def stream(
    job_id: str = typer.Argument(..., help="Agent job id"),
    host: str = typer.Option(_DEFAULT_HOST, "--host", help="rf serve host (for live streaming)"),
    port: int = typer.Option(_DEFAULT_PORT, "--port", help="rf serve port"),
    sensitivity_threshold: str = typer.Option(
        None,
        "--sensitivity-threshold",
        help="Exclude events whose sensitivity exceeds this level",
    ),
    follow: bool = typer.Option(False, "--follow/--no-follow", help="Follow live SSE stream from server (requires rf serve)"),
) -> None:
    """Stream events for a job.

    Without ``--follow``: reads persisted ``events.jsonl`` from disk.
    With ``--follow``: connects to the SSE endpoint of a running ``rf serve``
    instance and streams events until the job reaches a terminal state.
    """
    _SENS_ORDER = {
        "public": 0,
        "personal": 1,
        "work_sensitive": 2,
        "client_sensitive": 3,
        "top_secret": 4,
    }
    threshold_rank = _SENS_ORDER.get(sensitivity_threshold or "top_secret", len(_SENS_ORDER))

    def _filter_event(event: dict[str, Any]) -> bool:
        """Return True if the event's sensitivity is within threshold."""
        if sensitivity_threshold is None:
            return True
        sens = str(event.get("sensitivity") or "public")
        return _SENS_ORDER.get(sens, 0) <= threshold_rank

    if follow:
        # Live SSE mode — requires httpx[http2] or httpx with SSE support.
        try:
            import httpx
        except ImportError:
            _fail("httpx is required for --follow mode. Install with: pip install httpx")

        if not _probe_server(host, port):
            _fail(f"rf serve is not reachable at {host}:{port}.")

        console.print(f"[cyan]streaming[/cyan] events for {job_id} (Ctrl-C to stop)...")
        try:
            with httpx.stream(
                "GET",
                f"{_api_base(host, port)}/agent-jobs/{job_id}/events",
                timeout=None,
            ) as resp:
                if resp.status_code == 404:
                    _fail(f"job not found: {job_id}")
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        raw = line[6:]
                        try:
                            event = _json.loads(raw)
                        except _json.JSONDecodeError:
                            continue
                        if not _filter_event(event):
                            continue
                        event_type = event.get("event_type", "event")
                        msg = event.get("message") or _json.dumps(event)
                        console.print(f"  [{event_type}] {msg}")
        except KeyboardInterrupt:
            console.print("\n[yellow]stream interrupted[/yellow]")
        return

    # Offline mode — read from disk.
    svc, paths = _get_service()
    try:
        events = svc.load_events(job_id)
    except (ValueError, KeyError):
        _fail(f"job not found: {job_id}")

    if not events:
        console.print(f"[yellow]no events found for {job_id}[/yellow]")
        return

    for event in events:
        if not _filter_event(event):
            continue
        event_type = event.get("event_type", "event")
        msg = event.get("message") or _json.dumps(event)
        console.print(f"  [{event_type}] {msg}")

    console.print(f"[dim]{len(events)} event(s)[/dim]")


# ---------------------------------------------------------------------------
# rf agent-job accept
# ---------------------------------------------------------------------------


@agent_job_app.command("accept")
def accept(
    job_id: str = typer.Argument(..., help="Agent job id to accept"),
    accepted_by: str = typer.Option(None, "--accepted-by", help="Identity of the accepting operator"),
    notes: str = typer.Option(None, "--notes", help="Optional acceptance notes"),
    host: str = typer.Option(_DEFAULT_HOST, "--host", help="rf serve host"),
    port: int = typer.Option(_DEFAULT_PORT, "--port", help="rf serve port"),
    json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
) -> None:
    """Accept staged artifacts for a job (SOLE WRITE PATH into catalog/report).

    Calls the RF serve API when reachable; falls back to the service layer
    directly when the server is offline (direct service acceptance is supported
    for testing without a running server).
    """
    if _probe_server(host, port):
        try:
            import httpx
        except ImportError:
            _fail("httpx is required for API mode. Install with: pip install httpx")

        body: dict[str, Any] = {}
        if accepted_by:
            body["accepted_by"] = accepted_by
        if notes:
            body["notes"] = notes

        try:
            resp = httpx.post(
                f"{_api_base(host, port)}/agent-jobs/{job_id}/accept",
                json=body,
                timeout=30.0,
            )
        except httpx.RequestError as exc:
            _fail(f"Request to rf serve failed: {exc}")

        if resp.status_code == 404:
            _fail(f"job not found: {job_id}")
        if resp.status_code not in (200, 201):
            err_console.print(f"[red]HTTP {resp.status_code}[/red] {resp.text}")
            raise typer.Exit(1)

        data = resp.json()
    else:
        # Direct service path (offline / test mode).
        svc, _ = _get_service()
        try:
            data = svc.accept_job(job_id, accepted_by=accepted_by, notes=notes)
        except (ValueError, KeyError) as exc:
            _fail(str(exc))

    if json_out:
        typer.echo(_json.dumps(data, ensure_ascii=False, indent=2))
        return

    accepted_count = data.get("accepted_count", 0)
    console.print(f"[green]accepted[/green] {job_id}  ({accepted_count} artifact(s))")


# ---------------------------------------------------------------------------
# rf agent-job status
# ---------------------------------------------------------------------------


@agent_job_app.command("status")
def job_status(
    job_id: str = typer.Argument(..., help="Agent job id"),
    host: str = typer.Option(_DEFAULT_HOST, "--host", help="rf serve host"),
    port: int = typer.Option(_DEFAULT_PORT, "--port", help="rf serve port"),
    json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
) -> None:
    """Show status and metadata for a job.

    Reads from disk directly; no ``rf serve`` instance required.
    """
    svc, _ = _get_service()
    try:
        job = svc.load_job(job_id)
    except (ValueError, KeyError):
        _fail(f"job not found: {job_id}")

    data = job.to_dict()

    if json_out:
        typer.echo(_json.dumps(data, ensure_ascii=False, indent=2))
        return

    table = Table(title=f"agent job: {job_id}", show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")
    for field in (
        "agent_job_id",
        "provider",
        "model_profile",
        "request_kind",
        "status",
        "project_id",
        "workspace_id",
        "created_by",
        "created_at",
        "updated_at",
    ):
        val = data.get(field)
        if val is not None:
            table.add_row(field, str(val))
    console.print(table)


__all__ = ["agent_job_app"]
