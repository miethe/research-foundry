"""``rf search`` / ``rf fetch`` CLI surface for the Search Router (Wave 3).

Thin command layer: parse args → build a ``search_request`` dict → call the
orchestrator → render with Rich → translate errors to exit codes. Registered
onto the root ``rf`` Typer app via :func:`register`.
"""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from research_foundry.errors import ExitCode, RFError

from .router import extract_urls, run_search

console = Console()
err_console = Console(stderr=True)


def register(app: typer.Typer) -> None:
    """Attach the ``search`` and ``fetch`` commands to the root app."""

    @app.command()
    def search(
        query: str = typer.Argument(..., help="Search query"),
        mode: str = typer.Option("source_discovery", "--mode", "-m", help="search mode"),
        max_results: int = typer.Option(8, "--max-results", "-n", help="max URLs to extract"),
        max_cost: float = typer.Option(0.25, "--max-cost", help="max provider cost (USD)"),
        intent_id: str | None = typer.Option(None, "--intent-id", help="originating intent id"),
        task_node_id: str | None = typer.Option(
            None, "--task-node-id", help="originating IntentTree node id"
        ),
        no_cards: bool = typer.Option(
            False, "--no-cards", help="skip source-card creation (candidates only)"
        ),
    ) -> None:
        """Run a search via the Search Router (spec ADR §11)."""

        request: dict[str, Any] = {
            "query": query,
            "mode": mode,
            "budget": {
                "max_urls_to_extract": max_results,
                "max_provider_cost_usd": max_cost,
            },
            "output_requirements": {"source_cards": not no_cards},
        }
        if intent_id:
            request["intent_id"] = intent_id
        if task_node_id:
            request["task_node_id"] = task_node_id

        try:
            result = run_search(request)
        except RFError as exc:
            err_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(int(getattr(exc, "exit_code", ExitCode.USAGE))) from exc

        candidates = result.get("normalized_results", []) or []
        source_cards = result.get("source_cards", []) or []
        console.print(f"[green]run[/green] {result.get('run_id')}")
        console.print(f"  mode: {result.get('request', {}).get('mode', mode)}")
        console.print(f"  candidates: {len(candidates)}")
        console.print(f"  source cards: {len(source_cards)}")

        if candidates:
            table = Table(title="top candidates", show_header=True, header_style="bold")
            table.add_column("rank", justify="right")
            table.add_column("title")
            table.add_column("url")
            table.add_column("provider")
            for i, hit in enumerate(candidates[:10], start=1):
                table.add_row(
                    str(i),
                    str(hit.get("title", ""))[:60],
                    str(hit.get("url", "")),
                    str(hit.get("provider", "")),
                )
            console.print(table)

    @app.command()
    def fetch(
        urls: list[str] = typer.Argument(..., help="one or more URLs to fetch"),
    ) -> None:
        """Fetch markdown from known URLs into source cards (spec ADR §11)."""

        try:
            result = extract_urls(list(urls))
        except RFError as exc:
            err_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(int(getattr(exc, "exit_code", ExitCode.USAGE))) from exc

        run_id = result.get("run_id")
        card_ids = result.get("source_cards", []) or []
        tag = " [yellow](degraded)[/yellow]" if result.get("degraded") else ""
        console.print(f"[green]run[/green] {run_id}{tag}")
        console.print(f"  source cards: {len(card_ids)}")
        for cid in card_ids:
            typer.echo(cid)


__all__ = ["register"]
