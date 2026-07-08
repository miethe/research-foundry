"""Smoke test: rf workspace migrate-dry-run --help exits 0.

Verifies that the cli.py → cli/__init__.py merge resolves the
research_foundry.cli:app entry point correctly so `rf workspace ...` is
invokable (was broken by Python preferring the cli/ package over cli.py module).
"""

from __future__ import annotations

from typer.testing import CliRunner


def test_workspace_migrate_dry_run_help() -> None:
    """rf workspace migrate-dry-run --help must exit 0."""
    from research_foundry.cli import app  # noqa: PLC0415

    runner = CliRunner()
    result = runner.invoke(app, ["workspace", "migrate-dry-run", "--help"])
    assert result.exit_code == 0, (
        f"Expected exit 0, got {result.exit_code}\n"
        f"output: {result.output}"
    )


def test_cli_app_import() -> None:
    """research_foundry.cli:app resolves to the Typer app named 'rf'."""
    from research_foundry.cli import app  # noqa: PLC0415

    assert app.info.name == "rf"
