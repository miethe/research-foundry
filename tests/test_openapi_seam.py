"""CARP-5.4: OpenAPI / type seam.

Proves ``src/research_foundry/api/openapi.json`` is not hand-edited drift but
an exact mirror of the live FastAPI app (``create_app().openapi()``), and that
the CARP-5.1 ``retrieval_policy``/``retrieval_limits`` addition to
``LaunchRunRequest`` is wired end-to-end: declared as optional in the
committed schema, accepted by the real Pydantic model FastAPI validates
against, and round-tripped through the actual
``POST /api/runs`` service -> router -> response seam
(``services/run_launch.py`` -> ``routers/runs.py``).

Regeneration mechanism: ``scripts/generate_openapi.py`` (``create_app(
FoundryConfig.load()).openapi()``) -- there is no other canonical mechanism
in this repo (confirmed by prior investigation in
``docs/project_plans/feature_contracts/features/http-run-launch-endpoint.md``
Deviation #3). ``test_committed_openapi_json_matches_live_app`` below is the
drift guard: any router/model change that isn't followed by re-running that
script fails this test.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = REPO_ROOT / "src" / "research_foundry" / "api" / "openapi.json"


def _committed_spec() -> dict:
    return json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))


def _client(tmp_foundry) -> TestClient:
    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    return TestClient(app, raise_server_exceptions=True)


def test_committed_openapi_json_matches_live_app() -> None:
    """The committed ``openapi.json`` must be byte-for-byte what
    ``create_app(FoundryConfig.load()).openapi()`` produces right now --
    never hand-edited, never stale."""

    live_config = FoundryConfig.load(REPO_ROOT)
    live_spec = create_app(live_config).openapi()
    assert live_spec == _committed_spec(), (
        "src/research_foundry/api/openapi.json is stale relative to the live "
        "app. Regenerate with: PYTHONPATH=src .venv/bin/python "
        "scripts/generate_openapi.py"
    )


def test_launch_run_request_schema_declares_retrieval_fields_optional() -> None:
    """CARP-5.1's ``retrieval_policy``/``retrieval_limits`` must be present
    on the documented request schema, nullable, and absent from
    ``required`` -- the additive/optional contract carp-contract-freeze.md
    §1 promises callers."""

    schema = _committed_spec()["components"]["schemas"]["LaunchRunRequest"]
    required = set(schema.get("required") or [])
    assert "retrieval_policy" not in required
    assert "retrieval_limits" not in required

    properties = schema["properties"]
    for field in ("retrieval_policy", "retrieval_limits"):
        assert field in properties, f"{field} missing from documented LaunchRunRequest"
        types = {branch.get("type") for branch in properties[field].get("anyOf", [])}
        assert "null" in types, f"{field} must be declared nullable"


def test_legacy_payload_validates_against_schema_and_round_trips(tmp_foundry) -> None:
    """A legacy payload with no ``retrieval_*`` keys at all -- the shape
    every pre-CARP client already sends -- must validate against the
    documented schema (clients tolerate the new optional fields being
    entirely absent) AND must round-trip through the real service/router
    seam with the response omitting ``evidence_plan_ref``/
    ``retrieval_summary`` entirely."""

    schema = _committed_spec()["components"]["schemas"]["LaunchRunRequest"]
    legacy_payload = {"text": "Legacy caller, no retrieval fields."}
    jsonschema.validate(instance=legacy_payload, schema=schema)

    resp = _client(tmp_foundry).post("/api/runs", json=legacy_payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "evidence_plan_ref" not in body
    assert "retrieval_summary" not in body


def test_retrieval_payload_validates_against_schema_and_round_trips(tmp_foundry) -> None:
    """A payload actively using ``retrieval_policy``/``retrieval_limits``
    must validate against the documented schema AND reach
    ``run_launch.launch_run`` -> ``plan_run`` for real, producing a
    ``retrieval_summary`` in the HTTP response -- proving the schema, the
    router's ``LaunchRunRequest`` model, and the service underneath all
    agree on this shape."""

    schema = _committed_spec()["components"]["schemas"]["LaunchRunRequest"]
    retrieval_payload = {
        "text": "Catalog-only retrieval via the documented schema.",
        "retrieval_policy": "catalog_only",
        "retrieval_limits": {"max_questions": 3},
    }
    jsonschema.validate(instance=retrieval_payload, schema=schema)

    resp = _client(tmp_foundry).post("/api/runs", json=retrieval_payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["evidence_plan_ref"].startswith("evp_")
    assert "retrieval_summary" in body
    # Empty/fresh tmp_foundry catalog -> frozen catalog_empty denial shape
    # (carp-contract-freeze.md §3.2): zero candidate-derived fields.
    assert set(body["retrieval_summary"]) == {"questions_total"}
