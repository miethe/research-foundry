"""Dedicated CLI-only coverage for ``rf knowledge ...`` (KMCP-5.1, KMCP-6.1).

``tests/api/test_knowledge_api.py`` already proves CLI/API/MCP cross-transport
*parity* (denial-shape parity, 4-way rf_search/rf_fetch equality) and
``tests/integration/test_knowledge_parity.py`` proves the same across all four
transports for one shared fixture. THIS file stays scoped to the CLI as its
own transport, closing gaps neither of those files exercises:

1. ``--help`` lists the exact six subcommands (``search fetch source-get
   assertion-get report-get run-get``) -- the CLI's own advertised surface.
2. Click/Typer USAGE errors (missing required argument, unknown option) exit
   2 -- distinct from this module's OWN application-level exit codes (0 for
   ``search``, 1 for a policy denial on ``fetch``/typed getters).
3. An invalid ``--sensitivity-threshold`` value fails as a clear usage error
   (``export_service.resolve_threshold``'s own fail-closed validation,
   surfaced via ``knowledge.py``'s ``_context``/``_fail`` helper), never a
   raw traceback, for every subcommand that accepts the flag.
4. Golden-JSON key-set assertions for a REAL success path on every one of the
   six subcommands (``assertion-get``'s success path is unreachable in v1 --
   see ``registry.py``'s "Local-trust caveat" docstring -- so only its denial
   path is exercised here).
5. ``--kind`` narrows (never widens) ``search`` results; ``--limit`` is
   server-clamped, never rejected, above ``RF_SEARCH_MAX_RESULTS`` (the CLI's
   own help text promise, ``knowledge.py``'s ``limit`` option docstring).
6. ``--parent-run-ref`` threads into the caller-carried receipt's
   ``correlation_ref`` field exactly as supplied, unmodified.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app as rf_cli_app
from research_foundry.paths import FoundryPaths
from research_foundry.services import builder_service
from research_foundry.services import knowledge_access as ka

# Sibling test modules, imported by name for their fixture builders -- same
# convention every other Knowledge test module already uses.
from tests.unit.test_catalog_service import _write_threshold, build_catalog_run
from tests.unit.test_export_service import build_run
from tests.unit.test_knowledge_access import _set_run_yaml_fields

_RUNNER = CliRunner()

# Same generic, detail-free denial message every Knowledge transport uses
# (research_foundry.knowledge_mcp.registry._FETCH_DENIED_MESSAGE /
# research_foundry.cli.commands.knowledge._FETCH_DENIED_MESSAGE) --
# reimplemented by value, matching this repo's established convention of
# never importing this string across a transport boundary.
_FETCH_DENIED_MESSAGE = "Unable to fetch the requested knowledge id."

_SUBCOMMANDS = ("search", "fetch", "source-get", "assertion-get", "report-get", "run-get")


@pytest.fixture(autouse=True)
def _clean_projector_registry() -> Any:
    """Every test starts and ends with an empty projector registry -- mirrors
    every sibling Knowledge test module's own convention. Each ``rf
    knowledge`` invocation re-bootstraps its own projectors on entry (see
    ``knowledge.py``'s ``_bootstrap_projectors``), so this is defensive, not
    load-bearing, for the CLI tests themselves."""

    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)
    yield
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)


def _cli_invoke(tmp_foundry: FoundryPaths, args: list[str]) -> Any:
    """Run ``rf knowledge <args>`` from ``tmp_foundry.root`` so the CLI's own
    ``FoundryPaths.discover()`` call resolves there (mirrors
    ``tests/test_cli_rights.py`` and ``tests/api/test_knowledge_api.py``'s
    own identically-named helper)."""

    prev = Path.cwd()
    os.chdir(tmp_foundry.root)
    try:
        return _RUNNER.invoke(rf_cli_app, ["knowledge", *args])
    finally:
        os.chdir(prev)


# ===========================================================================
# 1. --help surface
# ===========================================================================


def test_help_lists_the_exact_six_subcommands() -> None:
    result = _RUNNER.invoke(rf_cli_app, ["knowledge", "--help"])
    assert result.exit_code == 0
    for name in _SUBCOMMANDS:
        assert name in result.output
    assert len(_SUBCOMMANDS) == 6


# ===========================================================================
# 2. Click/Typer usage errors exit 2 -- distinct from this module's own
#    application-level exit codes (0 for search, 1 for a fetch-shaped denial)
# ===========================================================================


@pytest.mark.parametrize("subcommand", _SUBCOMMANDS)
def test_missing_required_id_or_query_argument_exits_usage_error(
    tmp_foundry: FoundryPaths, subcommand: str
) -> None:
    result = _cli_invoke(tmp_foundry, [subcommand])
    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_unknown_option_exits_usage_error(tmp_foundry: FoundryPaths) -> None:
    result = _cli_invoke(tmp_foundry, ["search", "hello", "--not-a-real-option", "x"])
    assert result.exit_code == 2
    assert "No such option" in result.output


# ===========================================================================
# 3. Invalid --sensitivity-threshold: a clear usage error, never a traceback
# ===========================================================================


@pytest.mark.parametrize(
    ("subcommand", "id_or_query"),
    [
        ("search", "anything"),
        ("fetch", "rfk:v1:run:does-not-matter"),
        ("source-get", "rfk:v1:source:does-not-matter"),
        ("run-get", "rfk:v1:run:does-not-matter"),
    ],
)
def test_invalid_sensitivity_threshold_fails_as_a_clear_usage_error(
    tmp_foundry: FoundryPaths, subcommand: str, id_or_query: str
) -> None:
    result = _cli_invoke(
        tmp_foundry, [subcommand, id_or_query, "--sensitivity-threshold", "not-a-real-threshold"]
    )
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert result.output.strip() != ""


# ===========================================================================
# 4. Golden-JSON key-set assertions across every reachable success path
# ===========================================================================


def test_search_golden_json_key_set(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_cli_golden_search")
    _set_run_yaml_fields(tmp_foundry, "rf_run_cli_golden_search", sensitivity="public")

    result = _cli_invoke(tmp_foundry, ["search", "golden_search"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload) == {"results", "next_cursor", "truncated", "receipt"}
    assert len(payload["results"]) == 1
    item = payload["results"][0]
    assert set(item) >= {"id", "title", "url", "kind", "content_is_untrusted"}
    assert payload["receipt"]["tool"] == "rf_search"


def test_fetch_golden_json_key_set(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_cli_golden_fetch")
    _set_run_yaml_fields(tmp_foundry, "rf_run_cli_golden_fetch", sensitivity="public")

    result = _cli_invoke(tmp_foundry, ["fetch", "rfk:v1:run:rf_run_cli_golden_fetch"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert {"id", "title", "url", "kind", "content_is_untrusted", "receipt"} <= set(payload)
    assert payload["id"] == "rfk:v1:run:rf_run_cli_golden_fetch"
    assert payload["receipt"]["tool"] == "rf_fetch"


def test_source_get_golden_json_key_set(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    from research_foundry.services import catalog_service as catalog_svc

    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")
    item_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    result = _cli_invoke(tmp_foundry, ["source-get", f"rfk:v1:source:{item_id}"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "source"
    assert payload["id"] == f"rfk:v1:source:{item_id}"
    assert payload["receipt"]["tool"] == "rf_source_get"


def test_run_get_golden_json_key_set(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_cli_golden_runget")
    _set_run_yaml_fields(tmp_foundry, "rf_run_cli_golden_runget", sensitivity="public")

    result = _cli_invoke(tmp_foundry, ["run-get", "rfk:v1:run:rf_run_cli_golden_runget"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "run"
    assert payload["receipt"]["tool"] == "rf_run_get"


def test_report_get_golden_json_key_set_for_both_draft_and_final(tmp_foundry: FoundryPaths) -> None:
    draft = builder_service.create_draft(
        tmp_foundry, title="CLI Golden Draft", sensitivity="public", blocks=[{"markdown": "BODY"}]
    )
    draft_id = draft["report_draft_id"]

    result = _cli_invoke(tmp_foundry, ["report-get", f"rfk:v1:report_draft:{draft_id}"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "report_draft"
    assert payload["receipt"]["tool"] == "rf_report_get"


def test_assertion_get_only_reaches_its_denial_path_under_local_trust(tmp_foundry: FoundryPaths) -> None:
    """``assertion-get``'s SUCCESS path is unreachable through this local
    CLI transport in v1 -- see ``registry.py``'s "Local-trust caveat"
    docstring (this repo's CLI always resolves ``identity=None``, and every
    assertion read unconditionally requires a non-``None`` identity). This
    is the only one of the six subcommands whose golden-JSON is its DENIAL
    shape, not a success shape -- documented explicitly rather than silently
    absent from the golden-JSON set above."""

    result = _cli_invoke(tmp_foundry, ["assertion-get", "rfk:v1:assertion:cli-local-trust-01"])
    assert result.exit_code == 1
    assert _FETCH_DENIED_MESSAGE in result.output


# ===========================================================================
# 5. --kind narrows search; --limit is server-clamped, never rejected
# ===========================================================================


def test_kind_option_narrows_search_results(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_cli_kindfilter")
    _set_run_yaml_fields(tmp_foundry, "rf_run_cli_kindfilter", sensitivity="public")
    builder_service.create_draft(
        tmp_foundry, title="Kindfilter Draft Report", sensitivity="public", blocks=[{"markdown": "BODY"}]
    )

    unfiltered = _cli_invoke(tmp_foundry, ["search", "kindfilter"])
    assert unfiltered.exit_code == 0
    unfiltered_kinds = {item["kind"] for item in json.loads(unfiltered.stdout)["results"]}
    assert unfiltered_kinds == {"run", "report_draft"}

    filtered = _cli_invoke(tmp_foundry, ["search", "kindfilter", "--kind", "run"])
    assert filtered.exit_code == 0
    filtered_results = json.loads(filtered.stdout)["results"]
    assert filtered_results and all(item["kind"] == "run" for item in filtered_results)


def test_limit_option_is_server_clamped_never_rejected(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_cli_limitclamp")
    _set_run_yaml_fields(tmp_foundry, "rf_run_cli_limitclamp", sensitivity="public")

    over_max = ka.RF_SEARCH_MAX_RESULTS + 500
    result = _cli_invoke(tmp_foundry, ["search", "limitclamp", "--limit", str(over_max)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["receipt"]["bounds"]["results_max"] == ka.RF_SEARCH_MAX_RESULTS


# ===========================================================================
# 6. --parent-run-ref threads unmodified into the receipt's correlation_ref
# ===========================================================================


def test_parent_run_ref_threads_into_receipt_correlation_ref(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_cli_correlation")
    _set_run_yaml_fields(tmp_foundry, "rf_run_cli_correlation", sensitivity="public")

    result = _cli_invoke(
        tmp_foundry,
        ["fetch", "rfk:v1:run:rf_run_cli_correlation", "--parent-run-ref", "external-caller-ref-42"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["receipt"]["correlation_ref"] == "external-caller-ref-42"


__all__: list[str] = []
