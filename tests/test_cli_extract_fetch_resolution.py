"""Regression test: ``rf extract`` resolves to claim-extraction, ``rf fetch`` to URL-extraction.

The bug (pre-fix): two Typer commands both registered the name ``extract`` on the
root app.  Because search_router.cli was registered AFTER cli_commands, Click's
last-write-wins semantics resolved ``rf extract`` to the URL variant, shadowing
the canonical claim-extraction command (spec §10.7).

This test asserts the correct resolution via the same path the CLI uses at
runtime: ``typer.main.get_command(app).get_command(ctx, name)``.
"""

from __future__ import annotations

import inspect

import typer.main

import research_foundry.cli as c


def test_extract_resolves_to_claim_extraction() -> None:
    """``rf extract`` must resolve to the claim-extraction command (cli_commands.py)."""
    group = typer.main.get_command(c.app)
    extract_cmd = group.get_command(None, "extract")  # type: ignore[arg-type]
    assert extract_cmd is not None, "extract command not found on app"

    sig = inspect.signature(extract_cmd.callback)
    params = list(sig.parameters.keys())
    assert "run" in params, f"expected 'run' param, got {params}"
    assert "model_profile" in params, f"expected 'model_profile' param, got {params}"
    assert extract_cmd.callback.__module__ == "research_foundry.cli_commands"


def test_fetch_resolves_to_url_extraction() -> None:
    """``rf fetch`` must resolve to the URL-extraction command (search_router.cli)."""
    group = typer.main.get_command(c.app)
    fetch_cmd = group.get_command(None, "fetch")  # type: ignore[arg-type]
    assert fetch_cmd is not None, "fetch command not found on app"

    sig = inspect.signature(fetch_cmd.callback)
    params = list(sig.parameters.keys())
    assert "urls" in params, f"expected 'urls' param, got {params}"
    assert fetch_cmd.callback.__module__ == "research_foundry.services.search_router.cli"
