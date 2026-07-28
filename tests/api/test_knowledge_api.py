"""HTTP + cross-transport parity coverage for the RF Knowledge MCP (KMCP-5.3/5.4).

Where ``tests/unit/test_knowledge_access.py`` covers the shared service and
``tests/unit/test_knowledge_mcp_registry.py`` / ``tests/test_knowledge_mcp_process.py``
cover the stdio MCP process, and ``tests/unit/test_knowledge_mcp_settings.py``
covers the process settings module in isolation, THIS file proves the
KMCP-5.3 ("URL/OpenAPI/parity seam") and KMCP-5.4 ("Local-profile truth gate")
acceptance criteria specifically:

1. The committed ``api/openapi.json`` AND the live app expose the exact
   eight-route knowledge inventory and every one of those routes is GET-only
   (KMCP-5.2's "No POST/PUT/PATCH/DELETE" acceptance).
2. A ``rf_search`` result's own ``url`` field is a real, resolvable route on
   the SAME API (the "local resource URL contract",
   ``knowledge_access.build_local_resource_url``'s own docstring) — not a
   dead reference.
3. Byte-for-byte (modulo the receipt's own clock field) parity across all
   four transports — service, CLI (KMCP-5.1), API (KMCP-5.2), and the stdio
   MCP process (KMCP-4.1..4.3, gated behind ``pytest.importorskip("mcp")``
   since it is an optional extra) — for ``rf_search``/``rf_fetch`` against a
   real, seeded ``run``-kind knowledge item (the one kind whose projector
   needs no caller identity, unlike ``assertion``).
4. Denial-shape parity between CLI and API for every distinct "safe denial"
   cause (decisions-block Sec 0/Sec 3 Risk 2, KMCP-OQ-1): a malformed id, a
   genuinely missing id, a wrong-kind id addressed to a typed getter, and an
   id whose sensitivity exceeds the caller's ceiling — all four must collapse
   to the SAME generic, detail-free outcome on both transports.
5. The ``assertion``-kind "local trust" caveat (``registry.py``'s own
   docstring) holds identically on CLI and API: neither transport ever
   builds a real, workspace-bearing identity in v1, so every assertion read
   denies generically on both.
6. KMCP-5.4's local-profile truth gate: the repo-wide no-unqualified-hosted-
   compatibility-claim scan (KMCP-4.4's own scan, extended here to the CLI
   and API transport source plus the committed ``openapi.json`` text itself),
   a foundry.yaml NEGATIVE-config fixture proving
   ``KnowledgeMcpSettings`` has no ``origin``/``canonical_base_url`` field for
   a poisoned ``knowledge_mcp.*`` config block to bind to, and a parametrized
   matrix proving ``build_local_resource_url`` rejects every non-loopback
   origin shape it is handed.
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from research_foundry.api.app import create_app
from research_foundry.api.routers import knowledge as knowledge_api_router
from research_foundry.api.routers.runs import get_paths
from research_foundry.cli import app as rf_cli_app
from research_foundry.cli.commands import knowledge as knowledge_cli
from research_foundry.config import FoundryConfig
from research_foundry.knowledge_mcp import settings as kmcp_settings
from research_foundry.paths import FoundryPaths
from research_foundry.services import knowledge_access as ka
from research_foundry.yamlio import dump_yaml, load_yaml

# Sibling test modules, imported by name for their fixture builders (same
# convention ``tests/unit/test_knowledge_access.py`` itself already uses for
# ``tests.unit.test_export_service.build_run`` -- ``tests`` is a real
# package, so this is a plain import, not a sys.path hack).
from tests.unit.test_export_service import build_run
from tests.unit.test_knowledge_access import _set_run_yaml_fields

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "src" / "research_foundry" / "api" / "openapi.json"

# Same generic, detail-free denial message every Knowledge transport uses
# (research_foundry.knowledge_mcp.registry._FETCH_DENIED_MESSAGE) --
# reimplemented by value, not imported, matching the CLI/API/registry
# modules' own established convention of never importing this string across
# an independent transport boundary.
_FETCH_DENIED_MESSAGE = "Unable to fetch the requested knowledge id."

_RUNNER = CliRunner()


@pytest.fixture(autouse=True)
def _clean_projector_registry() -> Any:
    """Every test starts and ends with an empty projector registry -- mirrors
    ``tests/unit/test_knowledge_access.py``'s own fixture of the same name."""

    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)
    yield
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)


def _cli_invoke(tmp_foundry: FoundryPaths, args: list[str]) -> Any:
    """Run ``rf knowledge <args>`` from ``tmp_foundry.root`` so the CLI's own
    ``FoundryPaths.discover()`` call resolves there (mirrors
    ``tests/test_cli_rights.py``'s own ``_invoke`` helper)."""

    prev = Path.cwd()
    os.chdir(tmp_foundry.root)
    try:
        return _RUNNER.invoke(rf_cli_app, ["knowledge", *args])
    finally:
        os.chdir(prev)


def _api_client(tmp_foundry: FoundryPaths) -> TestClient:
    """A live app bound to ``tmp_foundry``, no auth middleware installed --
    ``request.state.identity`` is absent, so ``_identity_from_request``
    resolves ``None`` (the SAME local-trust default the CLI and MCP
    transports use unconditionally in v1)."""

    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    return TestClient(app)


def _mcp_structured_content(tmp_foundry: FoundryPaths, tool: str, arguments: dict[str, Any]) -> Any:
    """Call one stdio MCP tool end-to-end and return its ``structuredContent``.

    Skips (never fails) the calling test when the optional ``mcp`` extra is
    not installed -- a per-test skip, not a module-level one, since this
    file's other parity legs (service/CLI/API) must always run regardless.
    """

    pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")
    from research_foundry.knowledge_mcp import registry as kmcp_registry

    settings = kmcp_settings.KnowledgeMcpSettings(
        paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING"
    )
    server = kmcp_registry.build_server(settings)
    result = asyncio.run(server.call_tool(tool, arguments))
    return result.structuredContent


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy ``payload`` and drop the ONE receipt field that legitimately
    varies between two calls against the same snapshot (KMCP-3.4's
    ``generated_at``) so a byte-for-byte cross-transport comparison is
    meaningful."""

    normalized = json.loads(json.dumps(payload))
    receipt = normalized.get("receipt")
    if isinstance(receipt, dict):
        receipt.pop("generated_at", None)
    return normalized


# ===========================================================================
# KMCP-5.3: OpenAPI GET-only route inventory (committed spec AND live app)
# ===========================================================================

_EXPECTED_KNOWLEDGE_PATHS: frozenset[str] = frozenset(
    {
        "/api/knowledge/v1/search",
        "/api/knowledge/v1/fetch/{knowledge_id}",
        "/api/knowledge/search",
        "/api/knowledge/fetch/{knowledge_id}",
        "/api/knowledge/source/{knowledge_id}",
        "/api/knowledge/assertion/{knowledge_id}",
        "/api/knowledge/report/{knowledge_id}",
        "/api/knowledge/run/{knowledge_id}",
    }
)


def _knowledge_paths(spec: dict[str, Any]) -> dict[str, set[str]]:
    return {
        path: set(methods)
        for path, methods in spec["paths"].items()
        if path.startswith("/api/knowledge")
    }


def test_committed_openapi_json_has_exact_get_only_knowledge_route_inventory() -> None:
    spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    knowledge_paths = _knowledge_paths(spec)

    assert set(knowledge_paths) == _EXPECTED_KNOWLEDGE_PATHS
    # One route per frozen tool name (KMCP-1.1 CORE_TOOL_NAMES + RF_TOOL_NAMES) --
    # ties the literal path set above back to the service's own source of truth.
    assert len(_EXPECTED_KNOWLEDGE_PATHS) == len(ka.TOOL_NAMES) == 8
    for path, methods in knowledge_paths.items():
        assert methods == {"get"}, f"{path} exposes non-GET methods: {methods}"


def test_live_app_has_exact_get_only_knowledge_route_inventory() -> None:
    live_config = FoundryConfig.load(REPO_ROOT)
    live_spec = create_app(live_config).openapi()
    knowledge_paths = _knowledge_paths(live_spec)

    assert set(knowledge_paths) == _EXPECTED_KNOWLEDGE_PATHS
    for path, methods in knowledge_paths.items():
        assert methods == {"get"}, f"{path} exposes non-GET methods: {methods}"

    committed_spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert knowledge_paths == _knowledge_paths(committed_spec)


# ===========================================================================
# KMCP-5.3: local resource URL resolves through the SAME API
# ===========================================================================


def test_rf_search_result_url_resolves_through_the_same_api(tmp_foundry: FoundryPaths) -> None:
    """A ``rf_search`` result's own ``url`` -- built by
    ``knowledge_access.build_local_resource_url`` against the frozen
    ``/api/knowledge/v1/fetch/<id>`` route -- must be a real, resolvable
    route on THIS SAME API, not a dead reference (module docstring's
    "Local resource URL contract")."""

    run_id = "rf_run_kmlocalurl001"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="public")

    client = _api_client(tmp_foundry)
    search_resp = client.get("/api/knowledge/search", params={"query": "kmlocalurl"})
    assert search_resp.status_code == 200
    results = search_resp.json()["results"]
    assert len(results) == 1
    item = results[0]

    path = urlsplit(item["url"]).path
    assert path == f"/api/knowledge/v1/fetch/rfk%3Av1%3Arun%3A{run_id}"

    fetch_resp = client.get(path)
    assert fetch_resp.status_code == 200
    fetched = fetch_resp.json()
    assert fetched["id"] == item["id"]
    # The core FetchDTO is a DIFFERENT (frozen, snippet-free) shape from the
    # RF-extended search result item it was reached from -- see the router's
    # own "Local resource URL contract" docstring; only `id`/`title`/`url`
    # (plus optional `text`/`metadata`) may appear.
    assert set(fetched) <= {"id", "title", "text", "url", "metadata"}


# ===========================================================================
# KMCP-5.3: 4-way normalized parity -- service / CLI / API / MCP
# ===========================================================================


def test_four_way_rf_search_parity_on_seeded_run_kind(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_kmparitysearch001"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="public")
    query = "kmparitysearch"

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service_outcome = ka.KnowledgeAccessService(tmp_foundry).search_extended(
        ka.resolve_context(tmp_foundry, tool="rf_search"), query=query, include_receipt=True
    ).to_dict()

    cli_result = _cli_invoke(tmp_foundry, ["search", query])
    assert cli_result.exit_code == 0
    cli_outcome = json.loads(cli_result.stdout)

    api_resp = _api_client(tmp_foundry).get("/api/knowledge/search", params={"query": query})
    assert api_resp.status_code == 200
    api_outcome = api_resp.json()

    mcp_outcome = _mcp_structured_content(tmp_foundry, "rf_search", {"query": query})

    normalized = [_normalize(x) for x in (service_outcome, cli_outcome, api_outcome, mcp_outcome)]
    assert len(normalized[0]["results"]) == 1
    assert normalized[0] == normalized[1] == normalized[2] == normalized[3]


def test_four_way_rf_fetch_parity_on_seeded_run_kind(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_kmparityfetch001"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="public")
    knowledge_id = f"rfk:v1:run:{run_id}"

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service_doc = ka.KnowledgeAccessService(tmp_foundry).fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=knowledge_id, include_receipt=True
    ).to_dict()

    cli_result = _cli_invoke(tmp_foundry, ["fetch", knowledge_id])
    assert cli_result.exit_code == 0
    cli_doc = json.loads(cli_result.stdout)

    api_resp = _api_client(tmp_foundry).get(f"/api/knowledge/fetch/{knowledge_id}")
    assert api_resp.status_code == 200
    api_doc = api_resp.json()

    mcp_doc = _mcp_structured_content(tmp_foundry, "rf_fetch", {"id": knowledge_id})

    normalized = [_normalize(x) for x in (service_doc, cli_doc, api_doc, mcp_doc)]
    assert normalized[0]["id"] == knowledge_id
    assert normalized[0] == normalized[1] == normalized[2] == normalized[3]


# ===========================================================================
# Denial-shape parity across CLI + API (KMCP-OQ-1, decisions-block Sec 0/Sec 3
# Risk 2) -- malformed / missing / wrong-kind / hidden-above-threshold
# ===========================================================================


def test_fetch_denial_parity_malformed_id_across_cli_and_api(tmp_foundry: FoundryPaths) -> None:
    bad_id = "not-a-valid-knowledge-id"

    cli_result = _cli_invoke(tmp_foundry, ["fetch", bad_id])
    assert cli_result.exit_code == 1
    assert _FETCH_DENIED_MESSAGE in cli_result.output

    api_resp = _api_client(tmp_foundry).get(f"/api/knowledge/fetch/{bad_id}")
    assert api_resp.status_code == 404
    assert api_resp.json()["detail"] == _FETCH_DENIED_MESSAGE


def test_fetch_denial_parity_missing_id_across_cli_and_api(tmp_foundry: FoundryPaths) -> None:
    missing_id = "rfk:v1:run:km-missing-000"

    cli_result = _cli_invoke(tmp_foundry, ["fetch", missing_id])
    assert cli_result.exit_code == 1
    assert _FETCH_DENIED_MESSAGE in cli_result.output

    api_resp = _api_client(tmp_foundry).get(f"/api/knowledge/fetch/{missing_id}")
    assert api_resp.status_code == 404
    assert api_resp.json()["detail"] == _FETCH_DENIED_MESSAGE


def test_fetch_denial_parity_wrong_kind_typed_getter_across_cli_and_api(tmp_foundry: FoundryPaths) -> None:
    """A well-formed ``run``-kind id addressed to the ``source`` typed getter
    denies with the SAME generic shape as a missing id -- never a
    distinguishing "wrong kind" signal (mirrors
    ``knowledge_mcp.registry``'s identical typed-getter kind-scoping
    contract)."""

    run_id = "rf_run_kmwrongkind001"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="public")
    run_kind_id = f"rfk:v1:run:{run_id}"

    cli_result = _cli_invoke(tmp_foundry, ["source-get", run_kind_id])
    assert cli_result.exit_code == 1
    assert _FETCH_DENIED_MESSAGE in cli_result.output

    api_resp = _api_client(tmp_foundry).get(f"/api/knowledge/source/{run_kind_id}")
    assert api_resp.status_code == 404
    assert api_resp.json()["detail"] == _FETCH_DENIED_MESSAGE


def test_fetch_denial_parity_hidden_above_threshold_across_cli_and_api(tmp_foundry: FoundryPaths) -> None:
    """``export_run``'s own ``sensitivity_threshold`` argument only redacts
    per-claim text; the run PROJECTOR additionally hides the record itself
    once its own declared sensitivity exceeds the caller's ceiling -- CLI and
    API must deny identically for the SAME id/ceiling pair."""

    run_id = "rf_run_kmhidden001"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="client_sensitive")
    knowledge_id = f"rfk:v1:run:{run_id}"

    cli_result = _cli_invoke(tmp_foundry, ["fetch", knowledge_id, "--sensitivity-threshold", "public"])
    assert cli_result.exit_code == 1
    assert _FETCH_DENIED_MESSAGE in cli_result.output

    api_resp = _api_client(tmp_foundry).get(
        f"/api/knowledge/fetch/{knowledge_id}", params={"sensitivity_threshold": "public"}
    )
    assert api_resp.status_code == 404
    assert api_resp.json()["detail"] == _FETCH_DENIED_MESSAGE

    # Sanity: the SAME id resolves fine at its own (or a looser) ceiling --
    # proves the denial above is genuinely threshold-driven, not a fixture bug.
    cli_visible = _cli_invoke(
        tmp_foundry, ["fetch", knowledge_id, "--sensitivity-threshold", "client_sensitive"]
    )
    assert cli_visible.exit_code == 0
    api_visible = _api_client(tmp_foundry).get(
        f"/api/knowledge/fetch/{knowledge_id}", params={"sensitivity_threshold": "client_sensitive"}
    )
    assert api_visible.status_code == 200


def test_assertion_kind_local_trust_denial_parity_across_cli_and_api(tmp_foundry: FoundryPaths) -> None:
    """Local trust caveat (``registry.py``'s own docstring): every
    ``assertion``-kind read denies generically under ``identity=None`` -- the
    CLI (KMCP-5.1) always resolves local trust, and the API (KMCP-5.2)
    resolves the SAME ``None`` identity absent an auth middleware, so both
    must deny identically for a well-formed assertion id."""

    assertion_id = "rfk:v1:assertion:km-local-trust-01"

    cli_result = _cli_invoke(tmp_foundry, ["assertion-get", assertion_id])
    assert cli_result.exit_code == 1
    assert _FETCH_DENIED_MESSAGE in cli_result.output

    api_resp = _api_client(tmp_foundry).get(f"/api/knowledge/assertion/{assertion_id}")
    assert api_resp.status_code == 404
    assert api_resp.json()["detail"] == _FETCH_DENIED_MESSAGE


# ===========================================================================
# KMCP-5.4: Local-profile truth gate
# ===========================================================================

# Same marker list ``tests/test_knowledge_mcp_process.py`` uses for its own
# KMCP-4.4 process-level scan -- reimplemented by value (this file scans
# different, transport-boundary-crossing sources than that one does).
_HOSTED_COMPAT_CLAIM_MARKERS = (
    "chatgpt-compatible",
    "chatgpt compatible",
    "openai-compatible",
    "openai compatible",
    "hosted-compatible",
    "compatible with chatgpt",
    "compatible with openai",
)


def test_no_unqualified_hosted_compatibility_claim_in_cli_api_or_openapi_json() -> None:
    """Extends the KMCP-4.4 process-level scan to the CLI (KMCP-5.1) and API
    (KMCP-5.2) transport source plus the committed ``openapi.json`` text
    itself -- decisions-block Sec 10's ban on an unqualified hosted-client
    compatibility claim is repo-wide, not scoped to the dedicated stdio
    process's own package."""

    texts = [
        inspect.getsource(knowledge_cli).lower(),
        inspect.getsource(knowledge_api_router).lower(),
        OPENAPI_PATH.read_text(encoding="utf-8").lower(),
    ]
    combined = "\n".join(texts)
    for marker in _HOSTED_COMPAT_CLAIM_MARKERS:
        assert marker not in combined, f"unqualified hosted-compatibility claim found: {marker!r}"


def test_knowledge_mcp_settings_has_no_origin_or_canonical_base_url_field() -> None:
    """``KnowledgeMcpSettings`` declares exactly the three fields decisions-
    block Sec 9.3 allows (``paths``/``sensitivity_threshold_max``/
    ``log_level``) -- neither ``origin`` nor ``canonical_base_url`` exists on
    the dataclass at all, so a config value under either name has nothing to
    bind to (the local profile never grows a config-driven remote-origin
    knob)."""

    field_names = {f.name for f in dataclasses.fields(kmcp_settings.KnowledgeMcpSettings)}
    assert field_names == {"paths", "sensitivity_threshold_max", "log_level"}
    assert "origin" not in field_names
    assert "canonical_base_url" not in field_names


def test_knowledge_mcp_settings_ignores_origin_and_canonical_base_url_config_keys(
    tmp_foundry: FoundryPaths,
) -> None:
    """A foundry.yaml NEGATIVE-config fixture: an operator setting
    ``foundry.knowledge_mcp.origin``/``canonical_base_url`` (as if this were
    a remote-transport knob) has nothing to bind to -- ``resolve_settings``
    reads ONLY ``sensitivity_threshold_max`` from this namespace (module
    docstring's exhaustive list), and the resolved settings object carries no
    trace of either poisoned key."""

    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["knowledge_mcp"] = {
        "origin": "https://evil-remote.example.com",
        "canonical_base_url": "https://evil-remote.example.com",
        "sensitivity_threshold_max": "personal",
    }
    dump_yaml(data, tmp_foundry.foundry_yaml)

    resolved = kmcp_settings.resolve_settings(tmp_foundry)
    assert resolved.sensitivity_threshold_max == "personal"
    assert not hasattr(resolved, "origin")
    assert not hasattr(resolved, "canonical_base_url")
    assert "evil-remote.example.com" not in repr(resolved)


@pytest.mark.parametrize(
    "origin",
    [
        "https://example.com",
        "http://evil.example.com",
        "https://192.168.1.5",
        "http://8.8.8.8",
        "https://127.0.0.1.evil.com",
        "ftp://127.0.0.1",
        "http://localhost.evil.com",
        "https://[::2]",
        "http://0.0.0.0",
        "http://",
    ],
    ids=[
        "public-domain",
        "public-subdomain",
        "private-lan-ip",
        "public-ip",
        "loopback-lookalike-suffix",
        "disallowed-scheme",
        "localhost-lookalike-suffix",
        "wrong-ipv6-loopback",
        "unspecified-ipv4",
        "empty-host",
    ],
)
def test_build_local_resource_url_rejects_non_loopback_origin_matrix(origin: str) -> None:
    """Parametrized rejection matrix -- extends the single-case
    ``test_build_local_resource_url_rejects_non_loopback_origin`` in
    ``tests/unit/test_knowledge_access.py`` to a broader set of shapes an
    operator or a future remote-transport misconfiguration could plausibly
    hand this function (a real public host/IP, a loopback-LOOKALIKE
    hostname, a disallowed scheme, the wrong IPv6 loopback literal, and an
    empty host) -- every one must be rejected the SAME way."""

    with pytest.raises(ka.KnowledgeInvariantError):
        ka.build_local_resource_url("rfk:v1:source:abc", origin=origin)


__all__: list[str] = []
