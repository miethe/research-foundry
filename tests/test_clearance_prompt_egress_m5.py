"""clearance-gates-v1 M5 (leg C) -- per-record clearance mediation on the
third-party-LLM prompt surface, plus the two ``ClearanceDenied`` handler gaps
leg B's change opened.

WHY THESE TESTS ARE BEHAVIOUR DELTAS, NOT EXISTENCE CHECKS
----------------------------------------------------------
Every prompt-egress test here does three things together:

1. builds a record that GENUINELY carries a durable clearance stamp
   (``schemas/clearance_taint.schema.yaml`` shape) blocking the checked scope,
   with a unique tainted value string embedded in it;
2. drives the real prompt-composition path (the actual ``complete()`` /
   ``run()`` / ``start_job()`` call, with the provider mocked);
3. asserts the TAINTED VALUE STRING IS ABSENT from the outbound payload the
   mocked provider recorded -- not merely that an exception type exists or that
   some function was called.

Each is paired with a POSITIVE CONTROL that runs the identical path with the
stamp removed and asserts the tainted string IS present on the wire. Without
that pairing an implementation that simply never dispatches would pass, and the
denial test would prove nothing.

NO NETWORK. Every provider is mocked: ``litellm`` is injected into
``sys.modules`` as a stub module, both SDK adapters take an injected mock
client, and both agent providers take a recording stub job service so
``spawn_job`` (a real subprocess) never runs.
"""

from __future__ import annotations

import json
import shutil
import sys
import types
import unittest.mock as mock
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from research_foundry.adapters.claude_agent_sdk import ClaudeAgentSDKAdapter, MockSDKClient
from research_foundry.adapters.litellm_router import LiteLLMRouterAdapter
from research_foundry.adapters.openai_agents import (
    MockOpenAIAgentsClient,
    OpenAIAgentsAdapter,
)
from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services import catalog_service, clearance
from research_foundry.services import prompt_clearance as pc
from research_foundry.services.agent_providers.claude_agent_sdk_provider import (
    ClaudeAgentSDKProvider,
)
from research_foundry.services.agent_providers.openai_agents_provider import (
    OpenAIAgentsProvider,
)
from research_foundry.yamlio import dump_yaml, load_yaml

# A value that exists nowhere else in the repo, so finding it in a recorded
# provider payload is unambiguous evidence it egressed.
_TAINTED = "TAINTED-SOURCE-TEXT-a7f3-do-not-send-to-any-provider"
_ICA_KEY_VAR = "RF_LLM_API_KEY"
_ICA_KEY = "rf-test-key-not-a-real-credential"


def _stamp(*scopes: str) -> dict[str, Any]:
    """A schema-shaped durable taint block blocking *scopes*."""

    return {
        "schema_version": "1.0",
        "blocked_scopes": list(scopes),
        "stamped_at": "2026-08-05T00:00:00Z",
        "stamped_by": "test-fixture",
        "posture_at_stamp": "dev_test",
        "gate_refs": ["DEF-1"],
    }


def _source_record(*, stamp: dict[str, Any] | None) -> dict[str, Any]:
    """One raw source-attribution-shaped record carrying the tainted value.

    ``stamp=None`` produces the pre-clearance shape (no ``clearance`` key at
    all) -- the positive-control / regression-floor record.
    """

    record: dict[str, Any] = {
        "source_card_id": "src_tainted",
        "title": "Provider-fetched record",
        "quote": _TAINTED,
    }
    if stamp is not None:
        record[clearance.TAINT_KEY] = stamp
    return record


# ---------------------------------------------------------------------------
# 0. The collector convention (mirrors writeback._stamped_attribution_records)
# ---------------------------------------------------------------------------


def test_collector_ignores_records_with_no_clearance_key() -> None:
    """An unstamped record is not a finding -- it is the backward-compatibility
    mechanism. Every record kind predating clearance (including the 7 committed
    pediatric bundles) is structurally incapable of carrying a stamp."""

    assert pc.stamped_prompt_records({"quote": _TAINTED}) == []


def test_collector_ignores_an_explicit_null_clearance_key() -> None:
    """``catalog_service``'s row builders emit ``"clearance": None`` when a
    record has no stamp. Keying the collector on key PRESENCE rather than
    ``isinstance(..., dict)`` would refuse every catalog row -- a correctness
    regression, not a safety gain. This pins the discriminator."""

    assert pc.stamped_prompt_records({"quote": _TAINTED, "clearance": None}) == []


def test_collector_finds_a_stamp_nested_anywhere_in_the_request() -> None:
    """A caller composing a prompt may nest its records under any key, so the
    walk is structural rather than keyed to one blessed field name."""

    request = {
        "intent": "summarise",
        "inputs": {"batch": [[_source_record(stamp=_stamp("redistribution"))]]},
    }
    found = pc.stamped_prompt_records(request)
    assert len(found) == 1
    assert found[0]["quote"] == _TAINTED


def test_empty_payloads_short_circuit_without_reading_the_registry() -> None:
    """The no-stamped-record fast path must not load the registry, so this
    control cannot break an adapter in a workspace that has no
    ``config/clearance_gates.yaml``. Proven by making any registry read raise."""

    def _boom(**_kwargs: Any) -> Any:  # pragma: no cover - must never be called
        raise AssertionError("registry was read on the no-stamped-record path")

    with mock.patch.object(clearance, "load_registry", _boom):
        assert pc.mediate_prompt_egress({"quote": "clean"}, target="t") is None


# ---------------------------------------------------------------------------
# 1. LiteLLMRouterAdapter.complete() -- the only live third-party model call
# ---------------------------------------------------------------------------


def _fake_litellm() -> types.ModuleType:
    mod = types.ModuleType("litellm")
    msg = types.SimpleNamespace(content="pong")
    choice = types.SimpleNamespace(message=msg, finish_reason="stop")
    usage = types.SimpleNamespace(total_tokens=5)
    response = types.SimpleNamespace(choices=[choice], usage=usage, _hidden_params={})
    mod.completion = mock.MagicMock(name="litellm.completion", return_value=response)  # type: ignore[attr-defined]
    return mod


def _wire_text(fake: types.ModuleType) -> str:
    """Everything ever handed to ``litellm.completion``, as one string.

    This is the *outbound prompt payload*: whatever is in here left the process.
    """

    return "\n".join(repr(call) for call in fake.completion.call_args_list)  # type: ignore[attr-defined]


def _complete(
    paths: FoundryPaths, fake: types.ModuleType, record: dict[str, Any]
) -> dict[str, Any]:
    """Drive the real prompt-composition path: the record's tainted value is
    interpolated into the prompt, and the raw record is declared alongside it."""

    adapter = LiteLLMRouterAdapter()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        return adapter.complete(
            f"Summarise this source: {record['quote']}",
            model_profile="rf_extract_cheap",
            messages=[
                {"role": "user", "content": f"Summarise this source: {record['quote']}"}
            ],
            source_records=[record],
            paths=paths,
            env={_ICA_KEY_VAR: _ICA_KEY},
        )


def test_positive_control_unstamped_source_text_does_reach_the_wire(
    tmp_foundry: FoundryPaths,
) -> None:
    """POSITIVE CONTROL. Without a stamp the identical call fires and the
    tainted string IS on the wire -- so the denial test below is caused by the
    stamp, not by this path never dispatching."""

    fake = _fake_litellm()
    result = _complete(tmp_foundry, fake, _source_record(stamp=None))

    assert result["degraded"] is False
    fake.completion.assert_called_once()  # type: ignore[attr-defined]
    assert _TAINTED in _wire_text(fake), (
        "positive control is broken: the source text never reached the wire even "
        "without a stamp, so a denial assertion would be vacuous"
    )


def test_redistribution_blocked_record_never_reaches_the_wire(
    tmp_foundry: FoundryPaths,
) -> None:
    """THE test that matters: a genuinely stamped-and-blocked record is refused
    and the tainted value string is ABSENT from the outbound prompt payload."""

    fake = _fake_litellm()
    with pytest.raises(clearance.ClearanceDenied):
        _complete(tmp_foundry, fake, _source_record(stamp=_stamp("redistribution")))

    assert _TAINTED not in _wire_text(fake)
    fake.completion.assert_not_called()  # type: ignore[attr-defined]


def test_stamp_nested_only_in_messages_is_refused(tmp_foundry: FoundryPaths) -> None:
    """``messages`` is a raw list of dicts and is walked too, so a caller that
    attaches the stamp to the message rather than to ``source_records`` is still
    refused -- there is no "wrong channel" escape hatch."""

    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    tainted_message = {
        "role": "user",
        "content": f"Summarise: {_TAINTED}",
        clearance.TAINT_KEY: _stamp("redistribution"),
    }
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ), pytest.raises(clearance.ClearanceDenied):
        adapter.complete(
            "ignored",
            model_profile="rf_extract_cheap",
            messages=[tainted_message],
            paths=tmp_foundry,
            env={_ICA_KEY_VAR: _ICA_KEY},
        )

    assert _TAINTED not in _wire_text(fake)
    fake.completion.assert_not_called()  # type: ignore[attr-defined]


def test_emptied_blocked_scopes_is_refused_not_read_as_unrestricted(
    tmp_foundry: FoundryPaths,
) -> None:
    """Fail-closed on the in-memory emptying vector (clearance.py finding B3): a
    stamp whose ``blocked_scopes`` was emptied a moment before egress must be
    refused, never read as "explicitly unrestricted"."""

    fake = _fake_litellm()
    with pytest.raises(clearance.ClearanceDenied):
        _complete(tmp_foundry, fake, _source_record(stamp=_stamp()))

    assert _TAINTED not in _wire_text(fake)


def test_acquisition_stamp_refused_even_though_scope_asked_is_redistribution(
    tmp_foundry: FoundryPaths,
) -> None:
    """A record that should never have been acquired must not travel anywhere,
    regardless of the scope the caller asked about (DEF-2 defence in depth)."""

    fake = _fake_litellm()
    with pytest.raises(clearance.ClearanceDenied):
        _complete(tmp_foundry, fake, _source_record(stamp=_stamp("acquisition")))

    assert _TAINTED not in _wire_text(fake)


def test_clinical_only_stamp_does_not_block_a_prompt(tmp_foundry: FoundryPaths) -> None:
    """Precision, not just fail-closed: ``clinical_reliance`` is about reliance,
    not redistribution (operator decision 4 -- clinical content stays viewable
    and rule-buildable). A clinical-only stamp must NOT refuse the prompt, or
    this control would over-block the entire pediatric surface."""

    fake = _fake_litellm()
    result = _complete(
        tmp_foundry, fake, _source_record(stamp=_stamp("clinical_reliance"))
    )

    assert result["degraded"] is False
    fake.completion.assert_called_once()  # type: ignore[attr-defined]


def test_unstamped_completion_is_unchanged_regression_floor(
    tmp_foundry: FoundryPaths,
) -> None:
    """The pre-existing no-records call shape still behaves exactly as before
    (this is the shape every current caller and every E2 test uses)."""

    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping", model_profile="rf_extract_cheap", paths=tmp_foundry,
            env={_ICA_KEY_VAR: _ICA_KEY},
        )
    assert result["degraded"] is False
    assert result["text"] == "pong"


# ---------------------------------------------------------------------------
# 2. The two SDK adapters -- run() before the job_brief projection
# ---------------------------------------------------------------------------


class _RecordingSDKClient(MockSDKClient):
    """Mock client that records every job_brief it was handed."""

    def __init__(self) -> None:
        self.briefs: list[dict[str, Any]] = []

    def run_agent(self, job_brief: dict[str, Any]) -> dict[str, Any]:
        self.briefs.append(job_brief)
        return super().run_agent(job_brief)


class _RecordingOpenAIClient(MockOpenAIAgentsClient):
    def __init__(self) -> None:
        super().__init__(allowed_tools=["search"])
        self.briefs: list[dict[str, Any]] = []

    def run_agent(self, job_brief: dict[str, Any]) -> dict[str, Any]:
        self.briefs.append(job_brief)
        return super().run_agent(job_brief)

    def run_agent_with_guardrails(
        self, job_brief: dict[str, Any], allowed_tools: list[str], data_scopes: list[str]
    ) -> dict[str, Any]:
        self.briefs.append(job_brief)
        return super().run_agent_with_guardrails(job_brief, allowed_tools, data_scopes)


def _sdk_request(
    paths: FoundryPaths, record: dict[str, Any]
) -> dict[str, Any]:
    return {
        "job_id": "job_1",
        "intent": f"Summarise this source: {record['quote']}",
        "source_records": [record],
        "paths": paths,
    }


@pytest.mark.parametrize(
    ("adapter_factory", "client_factory"),
    [
        (ClaudeAgentSDKAdapter, _RecordingSDKClient),
        (OpenAIAgentsAdapter, _RecordingOpenAIClient),
    ],
    ids=["claude_agent_sdk", "openai_agents"],
)
def test_sdk_adapter_positive_control_unstamped_text_reaches_the_client(
    tmp_foundry: FoundryPaths, adapter_factory: Any, client_factory: Any
) -> None:
    """POSITIVE CONTROL for both SDK adapters: without a stamp the tainted string
    genuinely reaches the third-party client's job_brief."""

    client = client_factory()
    adapter = adapter_factory(sdk_client=client)
    result = adapter.run(_sdk_request(tmp_foundry, _source_record(stamp=None)))

    assert result.degraded is False
    assert client.briefs, "positive control is broken: client was never invoked"
    assert _TAINTED in json.dumps(client.briefs), (
        "positive control is broken: the source text never reached the SDK client, "
        "so a denial assertion would be vacuous"
    )


@pytest.mark.parametrize(
    ("adapter_factory", "client_factory"),
    [
        (ClaudeAgentSDKAdapter, _RecordingSDKClient),
        (OpenAIAgentsAdapter, _RecordingOpenAIClient),
    ],
    ids=["claude_agent_sdk", "openai_agents"],
)
def test_sdk_adapter_blocked_record_never_reaches_the_client(
    tmp_foundry: FoundryPaths, adapter_factory: Any, client_factory: Any
) -> None:
    """Blocked record => refused, and the tainted value never reaches the
    third-party client at all."""

    client = client_factory()
    adapter = adapter_factory(sdk_client=client)
    with pytest.raises(clearance.ClearanceDenied):
        adapter.run(_sdk_request(tmp_foundry, _source_record(stamp=_stamp("redistribution"))))

    assert client.briefs == []
    assert _TAINTED not in json.dumps(client.briefs)


@pytest.mark.parametrize(
    "adapter_factory",
    [ClaudeAgentSDKAdapter, OpenAIAgentsAdapter],
    ids=["claude_agent_sdk", "openai_agents"],
)
def test_sdk_adapter_degraded_branch_refuses_and_does_not_echo_the_value(
    tmp_foundry: FoundryPaths, adapter_factory: Any
) -> None:
    """The check runs on the degraded branch too. Otherwise enforcement would
    depend on whether a third-party SDK happens to be installed, AND the
    degraded stub (which echoes ``request["prompt"]`` into its returned
    artifact) would hand the tainted text straight back to the caller."""

    adapter = adapter_factory()  # no client injected -> degraded path
    assert adapter.available() is False
    request = _sdk_request(tmp_foundry, _source_record(stamp=_stamp("redistribution")))
    request["prompt"] = f"Summarise: {_TAINTED}"

    with pytest.raises(clearance.ClearanceDenied):
        adapter.run(request)


@pytest.mark.parametrize(
    "adapter_factory",
    [ClaudeAgentSDKAdapter, OpenAIAgentsAdapter],
    ids=["claude_agent_sdk", "openai_agents"],
)
def test_sdk_adapter_unstamped_degraded_run_is_unchanged(
    tmp_foundry: FoundryPaths, adapter_factory: Any
) -> None:
    """Regression floor: the pre-existing degraded stub shape is untouched for
    an unstamped request (the shape every current caller uses)."""

    adapter = adapter_factory()
    result = adapter.run({"intent": "summarise X"})
    assert result.degraded is True
    assert result.artifacts


# ---------------------------------------------------------------------------
# 3. The two agent providers -- start_job before the AgentJob projection
# ---------------------------------------------------------------------------


class _RecordingJobService:
    """Stub AgentJobService: records spawns instead of forking a subprocess."""

    def __init__(self, paths: FoundryPaths) -> None:
        self._paths = paths
        self.spawned: list[Any] = []
        self.events: list[Any] = []

    def spawn_job(self, job: Any, cred_bytes: bytes) -> None:
        self.spawned.append(job)

    def persist_event(self, job_id: str, event: dict[str, Any]) -> None:
        self.events.append((job_id, event))


@pytest.mark.parametrize(
    "provider_factory",
    [ClaudeAgentSDKProvider, OpenAIAgentsProvider],
    ids=["claude_agent_sdk", "openai_agents"],
)
def test_provider_positive_control_unstamped_job_spawns(
    tmp_foundry: FoundryPaths, provider_factory: Any
) -> None:
    """POSITIVE CONTROL: an unstamped job still spawns, so the denial below is
    caused by the stamp rather than by start_job never spawning."""

    svc = _RecordingJobService(tmp_foundry)
    provider = provider_factory(job_service=svc)
    job_id = provider.start_job(
        {"job_id": "job_ok", "source_records": [_source_record(stamp=None)]}
    )
    assert job_id == "job_ok"
    assert len(svc.spawned) == 1


@pytest.mark.parametrize(
    "provider_factory",
    [ClaudeAgentSDKProvider, OpenAIAgentsProvider],
    ids=["claude_agent_sdk", "openai_agents"],
)
def test_provider_blocked_job_is_never_spawned(
    tmp_foundry: FoundryPaths, provider_factory: Any
) -> None:
    """A blocked record refuses the whole spawn: the child process that would
    drive the third-party SDK is never started, so the tainted value never
    crosses the process boundary."""

    svc = _RecordingJobService(tmp_foundry)
    provider = provider_factory(job_service=svc)
    with pytest.raises(clearance.ClearanceDenied):
        provider.start_job(
            {
                "job_id": "job_blocked",
                "source_records": [_source_record(stamp=_stamp("redistribution"))],
            }
        )

    assert svc.spawned == []
    assert _TAINTED not in repr(svc.spawned)


# ---------------------------------------------------------------------------
# 4. Handler gap A -- api/routers/catalog.py: 403, never a 500
# ---------------------------------------------------------------------------


def _make_client(tmp_path: Path) -> tuple[TestClient, FoundryConfig]:
    """Auth-free API client over a real workspace (mirrors tests/test_serve_catalog.py)."""

    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    foundry_src = dist / "foundry.yaml"
    if foundry_src.exists():
        shutil.copyfile(foundry_src, root / "foundry.yaml")
    else:  # pragma: no cover
        (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    for d in ("runs", "inbox/raw_ideas", "intents/active"):
        (root / d).mkdir(parents=True, exist_ok=True)

    existing = load_yaml(root / "foundry.yaml") or {}
    if not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer = dict(existing["foundry"].get("viewer") or {})
    viewer["auth_mode"] = "none"
    viewer["sensitivity_threshold"] = "client_sensitive"
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, root / "foundry.yaml")

    cfg = FoundryConfig(paths=FoundryPaths(root=root))
    app = create_app(cfg)
    from research_foundry.api.routers.runs import get_paths

    app.dependency_overrides[get_paths] = lambda: cfg.paths
    # raise_server_exceptions=False so an UNHANDLED exception surfaces as the
    # 500 it would be in production instead of propagating into the test -- that
    # is exactly the pre-fix behaviour this asserts against.
    return TestClient(app, raise_server_exceptions=False), cfg


def _insert_tainted_source_row(paths: FoundryPaths, *, run_id: str, local_ref: str) -> str:
    """Insert one catalog row whose raw payload carries a blocked stamp.

    Direct insert (leg B's own ``_insert_row`` precedent) because the taint must
    exist in ``payload_json`` for the READ paths to mediate -- ``import_run``
    would refuse the run before a row was ever written.
    """

    payload = {
        "title": "Tainted Source",
        "source_type": "web",
        "url": None,
        "authors": None,
        "doi": None,
        "publisher": None,
        "version": None,
        "trust": None,
        "usage": None,
        "attribution_summary": None,
        "evidence_points": [
            {
                "claim_id": "clm_t",
                "evidence_id": "ev_t",
                "relation": "supports",
                "locator": "p.1",
                "quote": _TAINTED,
                "summary": _TAINTED,
                "sensitivity_rank": 0,
            }
        ],
        clearance.TAINT_KEY: _stamp("redistribution"),
    }
    row = catalog_service._base_row(
        item_type="source",
        run_id=run_id,
        local_ref=local_ref,
        project=None,
        title="Tainted Source",
        summary="web",
        status=None,
        sensitivity_rank=0,
        trust_label=None,
        confidence=None,
        source_count=1,
        created_at="2026-08-05T00:00:00Z",
        updated_at="2026-08-05T00:00:00Z",
        payload=payload,
    )
    with catalog_service._db(paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        catalog_service._insert_rows(conn, [row], [], run_id, [])
        conn.commit()
    return str(row["catalog_item_id"])


def test_catalog_search_route_refuses_with_403_and_leaks_nothing(tmp_path: Path) -> None:
    client, cfg = _make_client(tmp_path)
    _insert_tainted_source_row(cfg.paths, run_id="run_s", local_ref="src_s")

    resp = client.get("/api/catalog/search", params={"item_type": "source"})

    assert resp.status_code == 403, (
        f"clearance refusal must be a policy refusal, not {resp.status_code} "
        "(pre-fix this was an unhandled 500)"
    )
    assert _TAINTED not in resp.text


def test_catalog_item_route_refuses_with_403_and_leaks_nothing(tmp_path: Path) -> None:
    client, cfg = _make_client(tmp_path)
    item_id = _insert_tainted_source_row(cfg.paths, run_id="run_i", local_ref="src_i")

    resp = client.get(f"/api/catalog/items/{item_id}")

    assert resp.status_code == 403
    assert _TAINTED not in resp.text


def test_catalog_item_route_still_200s_for_an_unstamped_row(tmp_path: Path) -> None:
    """POSITIVE CONTROL: the same route on an unstamped row returns the payload,
    so the 403 above is caused by the stamp, not by the route always refusing."""

    client, cfg = _make_client(tmp_path)
    payload = {
        "title": "Clean Source",
        "source_type": "web",
        "url": None,
        "authors": None,
        "doi": None,
        "publisher": None,
        "version": None,
        "trust": None,
        "usage": None,
        "attribution_summary": None,
        "evidence_points": [
            {
                "claim_id": "clm_c",
                "evidence_id": "ev_c",
                "relation": "supports",
                "locator": "p.1",
                "quote": "clean quote",
                "summary": "clean summary",
                "sensitivity_rank": 0,
            }
        ],
    }
    row = catalog_service._base_row(
        item_type="source", run_id="run_c", local_ref="src_c", project=None,
        title="Clean Source", summary="web", status=None, sensitivity_rank=0,
        trust_label=None, confidence=None, source_count=1,
        created_at="2026-08-05T00:00:00Z", updated_at="2026-08-05T00:00:00Z",
        payload=payload,
    )
    with catalog_service._db(cfg.paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        catalog_service._insert_rows(conn, [row], [], "run_c", [])
        conn.commit()

    resp = client.get(f"/api/catalog/items/{row['catalog_item_id']}")
    assert resp.status_code == 200
    assert resp.json()["payload"]["evidence_points"][0]["quote"] == "clean quote"


def _plant_run_with_tainted_card(paths: FoundryPaths, run_id: str) -> None:
    """A run whose single cited source card carries a blocked stamp.

    Same shape as leg B's ``_build_run``: the stamp is injected directly onto the
    card's frontmatter (no writer produces this today, by design) so the test
    does not depend on M3 stamping plumbing.
    """

    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "planned",
            "sensitivity": "public",
            "created_at": "2026-08-05T00:00:00-04:00",
        },
        rp.run_yaml,
    )
    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_001",
            "sensitivity": "public",
            "trust": "high",
            "usage": "direct",
            "source": {"title": "Tainted", "source_type": "web"},
            "extracted_points": [
                {
                    "evidence_id": "ev_001",
                    "locator": "p1",
                    "quote": _TAINTED,
                    "summary": _TAINTED,
                }
            ],
            clearance.TAINT_KEY: _stamp("redistribution"),
        },
        "# Tainted card",
        rp.sources / "src_001.md",
    )
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_001",
                    "text": "A supported claim.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_001",
                            "evidence_id": "ev_001",
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                }
            ],
        },
        rp.claim_ledger,
    )


def test_catalog_import_run_route_refuses_with_403_not_500(tmp_path: Path) -> None:
    """``import_run`` derives rows via ``export_run``, which leg B made
    mediating. ``ClearanceDenied`` is not a ``CatalogError``, so the pre-existing
    handler never saw it and the route 500'd."""

    client, cfg = _make_client(tmp_path)
    _plant_run_with_tainted_card(cfg.paths, "rf_run_imp")

    resp = client.post("/api/catalog/import/run/rf_run_imp")

    assert resp.status_code == 403, (
        f"expected a policy refusal, got {resp.status_code}"
    )
    assert _TAINTED not in resp.text


def test_catalog_import_run_route_still_imports_an_unstamped_run(tmp_path: Path) -> None:
    """POSITIVE CONTROL for the import route."""

    client, cfg = _make_client(tmp_path)
    _plant_run_with_tainted_card(cfg.paths, "rf_run_clean")
    # Strip the stamp so the run is the pre-clearance shape.
    card = cfg.paths.run_paths("rf_run_clean").sources / "src_001.md"
    card.write_text(
        card.read_text(encoding="utf-8").replace(clearance.TAINT_KEY + ":", "_unused:"),
        encoding="utf-8",
    )

    resp = client.post("/api/catalog/import/run/rf_run_clean")
    assert resp.status_code == 200, resp.text
    assert resp.json()["imported"]["runs"] == 1


# ---------------------------------------------------------------------------
# 5. Handler gap B -- builder_service.export_run() feeding report-draft creation
# ---------------------------------------------------------------------------


def test_create_draft_from_run_refuses_a_blocked_run(tmp_foundry: FoundryPaths) -> None:
    """The service-layer half: ``ClearanceDenied`` is re-raised (never folded
    into ``NotFoundError``/``BuilderError``) with the seeding context, so it
    keeps ``ExitCode.GOVERNANCE`` for the CLI and stays distinguishable from a
    missing run."""

    from research_foundry.services import builder_service as bsvc

    _plant_run_with_tainted_card(tmp_foundry, "rf_run_draft")

    with pytest.raises(clearance.ClearanceDenied) as excinfo:
        bsvc.create_draft_from_run(tmp_foundry, run_id="rf_run_draft")

    assert "rf_run_draft" in str(excinfo.value)
    assert _TAINTED not in str(excinfo.value)


def test_create_draft_route_maps_clearance_denied_to_403_not_500(tmp_path: Path) -> None:
    """The HTTP half: pre-fix this surfaced as a bare 500 because
    ``ClearanceDenied`` is neither ``NotFoundError`` nor ``BuilderError``."""

    client, cfg = _make_client(tmp_path)
    _plant_run_with_tainted_card(cfg.paths, "rf_run_draft_api")

    resp = client.post(
        "/api/reports",
        json={"origin": "run", "source_run_id": "rf_run_draft_api"},
    )

    assert resp.status_code == 403, (
        f"expected a policy refusal, got {resp.status_code}: {resp.text[:400]}"
    )
    assert _TAINTED not in resp.text


def test_create_draft_from_collection_route_also_maps_to_403(tmp_path: Path) -> None:
    """The same router handler covers ``origin: collection``, whose
    ``catalog_service.get_item()`` reads leg B also made mediating — enumerating
    the whole pattern rather than only the one call site named in the brief."""

    client, cfg = _make_client(tmp_path)
    item_id = _insert_tainted_source_row(cfg.paths, run_id="run_coll", local_ref="src_coll")

    resp = client.post(
        "/api/reports",
        json={"origin": "collection", "catalog_item_ids": [item_id]},
    )

    assert resp.status_code == 403, (
        f"expected a policy refusal, got {resp.status_code}: {resp.text[:400]}"
    )
    assert _TAINTED not in resp.text


def test_create_draft_clearance_refusal_is_distinguishable_from_a_missing_run(
    tmp_path: Path,
) -> None:
    """A clearance refusal must stay distinguishable from "no such run" --
    folding the former into the latter would hide the governance event and make a
    blocked run look absent.

    PRE-EXISTING, UNRELATED DEFECT pinned here rather than silently fixed: the
    missing-run branch is currently a **500**, not the 404 this router's own
    comment claims. ``export_service.export_run`` raises ``ExportError`` for a
    genuinely-absent run (it never reaches the ``return None`` path that
    ``builder_service`` maps to ``NotFoundError``), and ``create_draft`` handles
    only ``NotFoundError``/``BuilderError``. That is the same *class* of gap as
    the clearance one this leg closes, but a different exception on a different
    code path — out of scope here, reported for a follow-up. This assertion pins
    only what leg C is responsible for: the clearance refusal is its own status,
    never collapsed into whatever the not-found branch returns.
    """

    client, _ = _make_client(tmp_path)
    resp = client.post(
        "/api/reports",
        json={"origin": "run", "source_run_id": "rf_run_does_not_exist"},
    )
    assert resp.status_code != 403, (
        "a missing run must not report a clearance refusal — that would make an "
        "absent run indistinguishable from a governance-blocked one"
    )
    assert resp.status_code == 500, (
        "if this now returns 404 the pre-existing ExportError gap was fixed "
        "elsewhere; update this test's rationale rather than deleting it"
    )
