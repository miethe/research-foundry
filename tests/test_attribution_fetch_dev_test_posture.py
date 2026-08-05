"""Tests for the clearance-gates M3 dev/test live-fetch posture wired into
``services/attribution_fetch/`` — half B of M3 (half A is
``tests/unit/test_dev_test_posture.py``, the config-level posture resolver).

This file was substantially reworked after a CHANGES_REQUESTED cross-model
adversarial review found 8 defects in the first version of this milestone.
Findings B1/B2 shared one root cause -- ``fetch()`` stamped, but the layers
beneath it (the module-level ``fetch_json`` helper, and each adapter's
``_send_request``) were independently reachable and did NOT -- so the fix
collapsed authorize -> network-fetch -> value-shape -> stamp into ONE atomic
composition per adapter (now living in ``_send_request``, which
:func:`fetch` merely delegates to), and closed the module-level helper
entirely (renamed private, mandatory ``config``/``provider``, self-gating).

Proves, per finding:

* B1 -- ``fetch_json`` no longer exists as a public name; the private
  ``_fetch_json`` requires ``config``/``provider`` and refuses (no socket)
  whenever the posture does not authorize it, regardless of caller.
* B2 -- every adapter's ``_send_request``, called DIRECTLY with an active
  config, returns a fully-stamped ``ClearedProviderFetchResult`` -- never a
  bare/unstamped dict.
* B3 -- covered primarily in ``tests/test_clearance_mediation.py::
  test_empty_scopes_is_denied_same_as_malformed`` (the general
  ``mediate_egress`` contract); this file adds the SPECIFIC in-process
  mutation scenario the review described (emptying a real
  ``ClearedProviderFetchResult``'s ``clearance`` dict before ``to_record()``).
* B4 -- ``PROVIDER_GATE_SCOPE`` is an immutable ``MappingProxyType``; an
  unknown provider is refused BEFORE any network attempt, not after.
* M1 -- a failed ``audit_service.record_event`` write does not permanently
  mark a config "audited"; a later fetch retries the audit write.
* M2 -- ``api.app.create_app()`` and this package's fetch-authorization
  point share ONE dedup point (``audit_service.
  emit_dev_test_posture_activated_once``); exercising both against the SAME
  config produces exactly one row, regardless of order.
* M3 -- deeply nested JSON raises ``AdapterError``, not ``RecursionError``.
* M4 -- a disallowed host/scheme is refused before any socket opens; every
  redirect is refused -- proven BEHAVIOURALLY (round 2 MINOR fix): a real
  loopback-only HTTP server answers with an actual 302 and we assert the
  exact opener construction ``_fetch_json`` uses refuses it, plus a
  runtime capture proving ``_fetch_json`` really passes that construction
  (not a source-text grep, which round 1's version of this test was).

Round 2 CHANGES_REQUESTED fixes (second pass):

* B4 redesigned: the mandatory ``"redistribution"`` scope is now a bare
  module constant never read from ``PROVIDER_GATE_SCOPE``, so mutating
  ``_PROVIDER_GATE_SCOPE_DATA`` in place OR rebinding the
  ``PROVIDER_GATE_SCOPE`` module attribute wholesale has ZERO effect on a
  fresh stamp -- tested directly below.
- B1 adjudicated as a non-defect (documented at ``_fetch_json``, no
  behaviour change): posture-off is stopped by the mandatory gate;
  posture-on hands a direct caller only an unstamped dict that
  ``mediate_egress`` already refuses for a governed kind.
* M2: the two audit-emission call sites now share a lock
  (``audit_service._dev_test_posture_audit_lock``), tested with real
  threads in ``tests/unit/test_audit_service.py``.
* Schema (``schemas/clearance_taint.schema.yaml``): ``blocked_scopes`` now
  requires ``minItems: 1``, matching the runtime's B3 refusal.

Also proves (pre-existing / retained coverage): the static provider->scope
map shape, DEF-2 vendor absence, posture-False byte-identical behaviour,
stamp independence from ``GateRegistry`` live state, hostile-response
value-shaping, and the critical durability test (a stamped record stays
denied after the posture is removed and every redistribution gate closes).

Mocks every provider at the ``_fetch_json``/``_send_request`` seam. Most
tests never open a real socket; ONE test
(``test_no_redirect_opener_refuses_a_real_redirect_response``) runs a real
HTTP server bound to ``127.0.0.1`` only (no external network) specifically
to drive an actual 3xx response through urllib's real redirect machinery.
"""

from __future__ import annotations

import shutil
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest
import yaml

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.errors import AdapterError, RFError
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import audit_service, clearance
from research_foundry.services.attribution_fetch import (
    PROVIDER_GATE_SCOPE,
    ClearedProviderFetchResult,
    ProviderFetchResult,
    _fetch_json,
    _NoRedirectHandler,
    authorize_live_fetch,
    crossref,
    openalex,
    semantic_scholar,
)
from research_foundry.services.clearance import (
    ClearanceDenied,
    GateRegistry,
    mediate_egress,
)

_PROVIDER_MODULES = (openalex, crossref, semantic_scholar)


def _request_for(module: Any) -> Any:
    if module is openalex:
        return openalex.OpenAlexRequest(identifier="10.1234/example")
    if module is crossref:
        return crossref.CrossrefRequest(doi="10.1234/example")
    if module is semantic_scholar:
        return semantic_scholar.SemanticScholarRequest(paper_id="abc123")
    raise AssertionError(f"unexpected module: {module}")  # pragma: no cover


def _fake_raw_for(module: Any) -> dict[str, Any]:
    """A well-formed raw provider response for *module*'s own shape."""

    if module is openalex:
        return {"id": "W1", "cited_by_count": 1}
    if module is crossref:
        return {"status": "ok", "message": {"DOI": "10.1/x", "is-referenced-by-count": 3}}
    if module is semantic_scholar:
        return {"paperId": "abc123", "citationCount": 9}
    raise AssertionError(f"unexpected module: {module}")  # pragma: no cover


def _posture_config(
    tmp_path: Path,
    *,
    declared: bool = True,
    declared_by: str = "nick",
    rationale: str = "local dev/test only; no license/ToS posture asserted",
    declared_at: str = "2026-08-05",
    subdir: str = "fdry",
) -> FoundryConfig:
    """Minimal ``FoundryConfig`` with (or without) a fully-declared
    ``dev_test_posture`` block. Mirrors ``tests/unit/test_dev_test_posture.
    py::_make_config`` — no schemas/config/templates copy, suitable for
    calling ``FoundryConfig`` accessors and ``attribution_fetch`` adapters
    directly (both of which only touch ``foundry.yaml`` and, on the audit
    path, ``.rf_state/rbac.db``, auto-created under this same root).
    """

    root = tmp_path / subdir
    root.mkdir(parents=True, exist_ok=True)
    foundry: dict[str, Any] = {"owner": "Test"}
    if declared:
        foundry["dev_test_posture"] = {
            "live_fetch_enabled": True,
            "rationale": rationale,
            "declared_at": declared_at,
            "declared_by": declared_by,
        }
    (root / "foundry.yaml").write_text(
        yaml.safe_dump({"foundry": foundry}, sort_keys=False), encoding="utf-8"
    )
    return FoundryConfig(paths=FoundryPaths(root=root))


def _full_posture_config(
    tmp_path: Path, *, declared_by: str = "nick", subdir: str = "fdry_full"
) -> FoundryConfig:
    """A FULL config (schemas/config/templates copied) so ``create_app()``
    can fully wire routers — mirrors ``tests/unit/test_dev_test_posture.py::
    _make_full_config``. Needed only for the M2 cross-site dedup test.
    """

    root = tmp_path / subdir
    root.mkdir(parents=True, exist_ok=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    for d in ("runs", "inbox/raw_ideas", "intents/active"):
        (root / d).mkdir(parents=True, exist_ok=True)

    foundry_yaml_path = root / "foundry.yaml"
    from research_foundry.yamlio import dump_yaml, load_yaml

    foundry_src = dist / "foundry.yaml"
    existing = load_yaml(foundry_src) if foundry_src.exists() else {}
    if not isinstance(existing, dict):
        existing = {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    existing["foundry"]["viewer"] = {
        **(existing["foundry"].get("viewer") or {}),
        "auth_mode": "none",
        "bind_host": "127.0.0.1",
    }
    existing["foundry"]["auth"] = {
        **(existing["foundry"].get("auth") or {}),
        "provider": "none",
    }
    existing["foundry"]["dev_test_posture"] = {
        "live_fetch_enabled": True,
        "rationale": "M2 cross-site dedup test",
        "declared_at": "2026-08-05",
        "declared_by": declared_by,
    }
    dump_yaml(existing, foundry_yaml_path)
    return FoundryConfig(paths=FoundryPaths(root=root))


# ---------------------------------------------------------------------------
# Static provider -> scope map (B4)
# ---------------------------------------------------------------------------


def test_provider_gate_scope_is_static_and_redistribution_only() -> None:
    assert dict(PROVIDER_GATE_SCOPE) == {
        "openalex": "redistribution",
        "crossref": "redistribution",
        "semantic_scholar": "redistribution",
    }
    assert "acquisition" not in PROVIDER_GATE_SCOPE.values()


def test_def2_vendors_absent_by_construction() -> None:
    """No Scopus/WoS/JCR/SCImago key, and no adapter module for any of them."""

    for name in ("scopus", "web_of_science", "wos", "jcr", "scimago"):
        assert name not in PROVIDER_GATE_SCOPE
    import importlib

    for mod in ("scopus", "web_of_science", "wos", "jcr", "scimago"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(f"research_foundry.services.attribution_fetch.{mod}")


def test_provider_gate_scope_is_immutable() -> None:
    """B4 round 1: 'static' means structurally immutable, not merely 'not
    derived from the registry'. Both mutation forms round 1's review named
    are refused BY THIS OBJECT -- round 2 found this insufficient on its
    own (see the two tests below): Python has no real access control, so
    the underlying dict can still be mutated in place, and the module
    attribute can still be rebound wholesale. This test still holds; it
    just is not, on its own, the actual fix anymore."""

    from types import MappingProxyType

    assert isinstance(PROVIDER_GATE_SCOPE, MappingProxyType)
    with pytest.raises(TypeError):
        PROVIDER_GATE_SCOPE["openalex"] = "acquisition"  # type: ignore[index]
    with pytest.raises(TypeError):
        del PROVIDER_GATE_SCOPE["openalex"]  # type: ignore[misc]
    # Confirm the map is genuinely unchanged after both refused attempts.
    assert PROVIDER_GATE_SCOPE["openalex"] == "redistribution"


def test_mutating_the_underlying_dict_does_not_touch_the_mandatory_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B4 round 2, THE actual repro: mutate ``_PROVIDER_GATE_SCOPE_DATA``
    (the plain dict the ``MappingProxyType`` wraps -- round 1's
    immutability guard does not, and cannot, prevent this) to mis-scope
    ``openalex`` as ``acquisition``, and confirm a fresh stamp STILL blocks
    ``redistribution`` -- because ``stamp_dev_test_fetch`` no longer reads
    ``PROVIDER_GATE_SCOPE``'s value to decide the mandatory scope at all.
    """

    import research_foundry.services.attribution_fetch as af

    monkeypatch.setitem(af._PROVIDER_GATE_SCOPE_DATA, "openalex", "acquisition")
    # Confirm the mutation genuinely landed -- otherwise this test would be
    # vacuous (proving nothing was ever mutated, not that the mutation had
    # no effect).
    assert af.PROVIDER_GATE_SCOPE["openalex"] == "acquisition"

    stamp = af.stamp_dev_test_fetch(provider="openalex")
    assert stamp["blocked_scopes"] == ["redistribution"]
    assert "acquisition" not in stamp["blocked_scopes"]


def test_rebinding_provider_gate_scope_wholesale_does_not_touch_the_mandatory_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B4 round 2, the OTHER repro the review named: rebind the
    ``PROVIDER_GATE_SCOPE`` module attribute itself to an entirely
    different mapping (immutability of the OLD object is irrelevant once
    the name points somewhere else) and confirm a fresh stamp is still
    unaffected.
    """

    import research_foundry.services.attribution_fetch as af

    monkeypatch.setattr(af, "PROVIDER_GATE_SCOPE", {"openalex": "acquisition"})
    assert af.PROVIDER_GATE_SCOPE == {"openalex": "acquisition"}  # mutation landed

    stamp = af.stamp_dev_test_fetch(provider="openalex")
    assert stamp["blocked_scopes"] == ["redistribution"]


def test_stamp_dev_test_fetch_refuses_rather_than_stamps_when_scope_resolver_omits_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct, non-tautological test of the runtime assertion itself: force
    ``_resolve_provider_fetch_scopes`` (the ONLY thing
    ``stamp_dev_test_fetch`` consults for the scopes list) to return a set
    that omits the mandatory scope, and confirm ``stamp_dev_test_fetch``
    refuses to stamp rather than silently producing an under-restrictive
    taint. This proves the guard actually fires on a genuine divergence,
    not merely that the un-tampered-with code path happens to include the
    literal twice.
    """

    import research_foundry.services.attribution_fetch as af

    monkeypatch.setattr(af, "_resolve_provider_fetch_scopes", lambda provider: ["clinical_reliance"])

    with pytest.raises(clearance.ClearanceConfigError, match="mandatory"):
        af.stamp_dev_test_fetch(provider="openalex")


def test_unknown_provider_refused_before_any_network_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B4: resolve+validate the provider's scope BEFORE the network call.

    Even with a fully-declared posture, an unknown provider raises
    immediately -- `_fetch_json` never gets called, so `build_opener` is
    never touched.
    """

    config = _posture_config(tmp_path)

    def _boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("must not build an opener for an unknown provider")

    import urllib.request

    monkeypatch.setattr(urllib.request, "build_opener", _boom)

    with pytest.raises(clearance.ClearanceConfigError, match="unknown provider"):
        authorize_live_fetch(config, provider="bogus_provider")

    # Also unconditional -- checked even when config is None.
    with pytest.raises(clearance.ClearanceConfigError, match="unknown provider"):
        authorize_live_fetch(None, provider="bogus_provider")


# ---------------------------------------------------------------------------
# B1 -- _fetch_json is private, mandatory-gated, unauthenticated no more
# ---------------------------------------------------------------------------


def test_fetch_json_is_not_a_public_name() -> None:
    import research_foundry.services.attribution_fetch as af

    assert "fetch_json" not in dir(af)
    assert "fetch_json" not in af.__all__
    assert "_fetch_json" not in af.__all__


def test_fetch_json_requires_config_and_provider_keywords() -> None:
    import inspect

    sig = inspect.signature(_fetch_json)
    assert "config" in sig.parameters
    assert "provider" in sig.parameters
    assert sig.parameters["config"].default is inspect.Parameter.empty
    assert sig.parameters["provider"].default is inspect.Parameter.empty


def test_fetch_json_refuses_with_posture_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The exact B1 repro: calling the fetcher directly with the posture
    OFF must not reach a socket, regardless of caller."""

    config = _posture_config(tmp_path, declared=False)

    def _boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("must not open a socket with posture OFF")

    import urllib.request

    monkeypatch.setattr(urllib.request, "build_opener", _boom)

    with pytest.raises(NotImplementedError, match="not declared"):
        _fetch_json(
            "https://api.openalex.org/works/W1", config=config, provider="openalex"
        )


def test_fetch_json_refuses_with_no_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ORIGINAL B1 repro verbatim: `fetch_json("https://attacker.example/x")`
    must be impossible to even call in the old shape (no config param to
    omit), and calling the new one with config=None must refuse."""

    import urllib.request

    def _boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("must not open a socket with config=None")

    monkeypatch.setattr(urllib.request, "build_opener", _boom)

    with pytest.raises(NotImplementedError):
        _fetch_json("https://attacker.example/x", config=None, provider="openalex")


# ---------------------------------------------------------------------------
# B2 -- every adapter's _send_request, called directly, returns a STAMPED
# result -- never a bare dict
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_send_request_called_directly_returns_stamped_result(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _posture_config(tmp_path)
    monkeypatch.setattr(
        module, "_fetch_json", lambda url, **kw: _fake_raw_for(module)
    )

    result = module._send_request(_request_for(module), config=config)

    assert isinstance(result, ClearedProviderFetchResult)
    assert not isinstance(result, dict)
    assert result.clearance["blocked_scopes"] == ["redistribution"]
    assert result.clearance["posture_at_stamp"] == "dev_test"


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_send_request_never_returns_bare_dict_even_with_active_config(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The literal B2 repro: '_send_request called directly with an active
    config ... hands back a raw dict with no stamp'. Assert the opposite."""

    config = _posture_config(tmp_path)
    monkeypatch.setattr(
        module, "_fetch_json", lambda url, **kw: _fake_raw_for(module)
    )

    result = module._send_request(_request_for(module), config=config)

    assert type(result) is not dict
    assert hasattr(result, "clearance")
    assert result.clearance  # non-empty, present


# ---------------------------------------------------------------------------
# Posture False preserves today's exact behaviour (this plumbing specifically)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_posture_explicitly_false_keeps_disabled_result(module: Any, tmp_path: Path) -> None:
    config = _posture_config(tmp_path, declared=False)
    request = _request_for(module)

    result = module.fetch(request, config=config)

    assert type(result) is ProviderFetchResult
    assert result.status == "disabled"


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_send_request_with_declared_false_posture_raises_same_message_shape(
    module: Any, tmp_path: Path
) -> None:
    config = _posture_config(tmp_path, declared=False)
    request = _request_for(module)

    with pytest.raises(NotImplementedError, match="unreachable scaffolding"):
        module._send_request(request, config=config)


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_fetch_never_calls_send_request_when_posture_false(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _posture_config(tmp_path, declared=False)
    request = _request_for(module)

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("_send_request must not be called when posture is False")

    monkeypatch.setattr(module, "_send_request", _boom)
    result = module.fetch(request, config=config)
    assert result.status == "disabled"


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_posture_off_no_public_symbol_reaches_socket_or_yields_a_value(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enumerated per the review's ask: with posture OFF, every public (and
    adapter-internal) entrypoint that COULD fetch must refuse, for every
    provider module. `fetch()` and `_send_request()` are the only two --
    `_parse_raw_response`/the dataclasses never touch the network."""

    config = _posture_config(tmp_path, declared=False)
    request = _request_for(module)

    assert module.fetch(request, config=config).status == "disabled"
    with pytest.raises(NotImplementedError):
        module._send_request(request, config=config)
    with pytest.raises(NotImplementedError):
        _fetch_json(
            "https://api.openalex.org/works/W1", config=config, provider=module.PROVIDER_NAME
        )


# ---------------------------------------------------------------------------
# A real (mocked-transport) fetch under a declared posture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_declared_posture_returns_cleared_result_stamped(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _posture_config(tmp_path)
    request = _request_for(module)

    monkeypatch.setattr(module, "_fetch_json", lambda url, **kw: _fake_raw_for(module))

    result = module.fetch(request, config=config)

    assert isinstance(result, ClearedProviderFetchResult)
    assert result.provider == module.PROVIDER_NAME
    assert result.status == "fetched"
    assert isinstance(result.value, dict)

    stamp = result.clearance
    assert stamp["blocked_scopes"] == ["redistribution"]
    assert stamp["posture_at_stamp"] == "dev_test"
    assert stamp["stamped_by"] == f"attribution_fetch.{module.PROVIDER_NAME}"
    assert stamp["schema_version"] == "1.0"
    assert isinstance(stamp["gate_refs"], list)

    reg = SchemaRegistry()
    validated = reg.validate(stamp, "clearance_taint")
    assert validated.ok, validated.errors


def test_openalex_value_shape_from_a_full_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _posture_config(tmp_path)
    monkeypatch.setattr(
        openalex, "_fetch_json", lambda url, **kw: {"id": "https://openalex.org/W1", "cited_by_count": 42}
    )
    result = openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)
    assert result.value == {"openalex_id": "https://openalex.org/W1", "cited_by_count": 42}


def test_crossref_value_shape_from_a_full_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _posture_config(tmp_path)
    monkeypatch.setattr(
        crossref,
        "_fetch_json",
        lambda url, **kw: {"status": "ok", "message": {"DOI": "10.1/x", "is-referenced-by-count": 5}},
    )
    result = crossref.fetch(crossref.CrossrefRequest("10.1/x"), config=config)
    assert result.value == {"doi": "10.1/x", "is_referenced_by_count": 5}


def test_semantic_scholar_value_shape_from_a_full_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _posture_config(tmp_path)
    monkeypatch.setattr(
        semantic_scholar,
        "_fetch_json",
        lambda url, **kw: {"paperId": "abc123", "citationCount": 11},
    )
    result = semantic_scholar.fetch(semantic_scholar.SemanticScholarRequest("abc123"), config=config)
    assert result.value == {"paper_id": "abc123", "citation_count": 11}


# ---------------------------------------------------------------------------
# Half-declared posture propagates the fail-closed RFError from fetch()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_half_declared_posture_raises_from_fetch(module: Any, tmp_path: Path) -> None:
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    (root / "foundry.yaml").write_text(
        "foundry:\n"
        "  dev_test_posture:\n"
        "    live_fetch_enabled: true\n"
        "    declared_by: nick\n",
        encoding="utf-8",
    )
    config = FoundryConfig(paths=FoundryPaths(root=root))
    request = _request_for(module)

    with pytest.raises(RFError, match="rationale"):
        module.fetch(request, config=config)


# ---------------------------------------------------------------------------
# The stamp is never re-derived from GateRegistry's live state
# ---------------------------------------------------------------------------


def test_stamp_ignores_registry_entirely(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Even with no registry file anywhere under this workspace, the stamp
    still blocks 'redistribution' -- because the stamping path never loads
    or consults a GateRegistry at all."""

    config = _posture_config(tmp_path)
    monkeypatch.setattr(openalex, "_fetch_json", lambda url, **kw: {"id": "W1", "cited_by_count": 1})

    result = openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)
    assert result.clearance["blocked_scopes"] == ["redistribution"]


def test_stamp_taint_never_calls_gate_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct proof at the clearance.stamp_taint level: no GateRegistry
    method is ever invoked while building a stamp."""

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("stamp_taint must never touch GateRegistry")

    monkeypatch.setattr(GateRegistry, "gates", _boom)
    monkeypatch.setattr(GateRegistry, "open_scopes", _boom)
    monkeypatch.setattr(GateRegistry, "gate_ids_for_scope", _boom)

    stamp = clearance.stamp_taint(
        blocked_scopes=["redistribution"],
        stamped_by="attribution_fetch.openalex",
        posture_at_stamp="dev_test",
    )
    assert stamp["blocked_scopes"] == ["redistribution"]


# ---------------------------------------------------------------------------
# B3 -- the specific in-process mutation scenario the review described
# ---------------------------------------------------------------------------


def test_emptying_a_real_stamp_in_process_no_longer_defeats_mediation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact B3 repro: fetch a real (mocked-transport) record, then
    empty its `clearance["blocked_scopes"]` list IN PROCESS before calling
    `to_record()` -- as a careless/malicious caller might, since
    `ClearedProviderFetchResult` is a frozen dataclass but its `clearance`
    FIELD is a plain mutable dict. `_blocked_scopes_of`'s B3 fix (empty ==
    no-usable-stamp) means this no longer defeats mediation.
    """

    config = _posture_config(tmp_path)
    monkeypatch.setattr(openalex, "_fetch_json", lambda url, **kw: {"id": "W1", "cited_by_count": 1})
    result = openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)

    # The attack: mutate the dict IN PLACE (the dataclass itself stays
    # frozen -- this is precisely why freezing the dataclass alone was
    # never sufficient).
    result.clearance["blocked_scopes"] = []
    record = result.to_record()
    assert record["clearance"]["blocked_scopes"] == []

    reg_yaml = tmp_path / "clearance_gates.yaml"
    reg_yaml.write_text(
        "schema_version: '1.0'\n"
        "applies_to_kinds: [source_attribution]\n"
        "gates:\n"
        "  - gate_id: DEF-1\n"
        "    blocks_scope: redistribution\n"
        "    state: open\n"
        "    summary: x\n"
        "    evidence_pointer: docs/x.md\n"
        "    closed_by: null\n",
        encoding="utf-8",
    )
    registry = GateRegistry(path=reg_yaml)

    with pytest.raises(ClearanceDenied, match="no usable clearance stamp"):
        mediate_egress(
            [record], kind="source_attribution", target_scope="redistribution",
            target="notebooklm", registry=registry,
        )


# ---------------------------------------------------------------------------
# M3 -- deeply nested JSON must not crash with a raw RecursionError
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def read(self, n: int) -> bytes:
        return self._body[:n]


class _FakeOpener:
    def __init__(self, body: bytes | None = None, *, http_error: Exception | None = None) -> None:
        self._body = body
        self._http_error = http_error

    def open(self, *a: Any, **k: Any) -> Any:
        if self._http_error is not None:
            raise self._http_error
        return _FakeResponse(self._body or b"{}")


def test_fetch_json_refuses_oversized_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import urllib.request

    config = _posture_config(tmp_path)
    oversized = b"x" * 10
    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: _FakeOpener(oversized))

    with pytest.raises(AdapterError, match="exceeded"):
        _fetch_json(
            "https://api.openalex.org/works/W1", config=config, provider="openalex", max_bytes=5
        )


def test_fetch_json_refuses_malformed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    config = _posture_config(tmp_path)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: _FakeOpener(b"not json{"))

    with pytest.raises(AdapterError, match="not valid JSON"):
        _fetch_json("https://api.openalex.org/works/W1", config=config, provider="openalex")


def test_fetch_json_refuses_non_object_top_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    config = _posture_config(tmp_path)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: _FakeOpener(b"[1, 2, 3]"))

    with pytest.raises(AdapterError, match="not a JSON object"):
        _fetch_json("https://api.openalex.org/works/W1", config=config, provider="openalex")


def test_fetch_json_refuses_deeply_nested_json_without_recursion_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M3: deeply nested JSON is cheap in bytes (does not trip the size
    cap) but can blow json.loads's recursion limit. Must surface as
    AdapterError, never a raw RecursionError escaping to the caller."""

    import json as _json
    import urllib.request

    config = _posture_config(tmp_path)
    depth = 100_000
    nested = ("[" * depth) + ("]" * depth)
    body = nested.encode("utf-8")
    assert len(body) < 1_000_000  # cheap in bytes -- the size cap does not catch this

    # Sanity: confirm this really does raise RecursionError from plain json.loads
    # (otherwise this test would not exercise the code path it claims to).
    with pytest.raises(RecursionError):
        _json.loads(body)

    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: _FakeOpener(body))

    with pytest.raises(AdapterError, match="deeply nested"):
        _fetch_json("https://api.openalex.org/works/W1", config=config, provider="openalex")


def test_fetch_json_wraps_network_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error
    import urllib.request

    config = _posture_config(tmp_path)
    monkeypatch.setattr(
        urllib.request,
        "build_opener",
        lambda *a, **k: _FakeOpener(http_error=urllib.error.URLError("boom")),
    )

    with pytest.raises(AdapterError, match="failed"):
        _fetch_json("https://api.openalex.org/works/W1", config=config, provider="openalex")


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_parse_raw_response_degrades_on_missing_or_wrong_typed_fields(module: Any) -> None:
    """A hostile/short response (missing every expected key, or carrying
    the wrong type) must degrade to None fields, never raise."""

    hostile_payloads: list[dict[str, Any]] = [
        {},
        {"id": 123, "cited_by_count": "not-an-int"},
        {"message": "not-a-dict"},
        {"paperId": None, "citationCount": True},
    ]
    for payload in hostile_payloads:
        value = module._parse_raw_response(payload)
        assert isinstance(value, dict)
        assert all(v is None or isinstance(v, (str, int)) for v in value.values())
        assert not any(isinstance(v, bool) for v in value.values())


# ---------------------------------------------------------------------------
# M4 -- host/scheme allowlist + redirect refusal (SSRF)
# ---------------------------------------------------------------------------


def test_disallowed_host_refused_before_any_network_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A URL pointing at a private/metadata address must be refused BEFORE
    any socket-capable primitive is even constructed."""

    import urllib.request

    config = _posture_config(tmp_path)

    def _boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("must not build an opener for a disallowed host")

    monkeypatch.setattr(urllib.request, "build_opener", _boom)

    with pytest.raises(AdapterError, match="host/scheme allowlist"):
        _fetch_json(
            "http://169.254.169.254/latest/meta-data/",
            config=config,
            provider="openalex",
        )


def test_disallowed_scheme_refused_even_for_an_allowed_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import urllib.request

    config = _posture_config(tmp_path)

    def _boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("must not build an opener for a disallowed scheme")

    monkeypatch.setattr(urllib.request, "build_opener", _boom)

    with pytest.raises(AdapterError, match="host/scheme allowlist"):
        _fetch_json(
            "http://api.openalex.org/works/W1",  # http, not https
            config=config,
            provider="openalex",
        )


def test_no_redirect_handler_refuses_every_redirect() -> None:
    """Direct unit test of the redirect-refusal primitive itself."""

    handler = _NoRedirectHandler()
    assert handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example/") is None
    assert handler.redirect_request(None, None, 301, "Moved", {}, "https://evil.example/") is None


class _RedirectingHandler(BaseHTTPRequestHandler):
    """A REAL (loopback-only) HTTP server that answers every GET with a 302
    to an address it must never actually be followed to."""

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        self.send_response(302, "Found")
        self.send_header("Location", "http://evil.example.invalid/should-never-be-followed")
        self.end_headers()

    def log_message(self, *args: Any) -> None:  # silence test-run noise
        return None


def test_no_redirect_opener_refuses_a_real_redirect_response() -> None:
    """Round 2, MINOR finding: the round-1 pair here was vacuous (one test
    grepped source text; its companion injected an already-constructed
    HTTPError and never drove a real 3xx through urllib's own redirect
    machinery). This drives an ACTUAL 302 response, from a real (loopback
    -only -- no external network) HTTP server, through the EXACT opener
    construction ``_fetch_json`` uses (``build_opener(_NoRedirectHandler())``),
    and asserts urllib raises for the 3xx rather than following it to the
    bogus Location header -- proving the refusal by observed behaviour, not
    by inspecting source text or a pre-fabricated exception.
    """

    server = HTTPServer(("127.0.0.1", 0), _RedirectingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        opener = urllib.request.build_opener(_NoRedirectHandler())
        with pytest.raises(urllib.error.HTTPError) as exc:
            opener.open(f"http://127.0.0.1:{port}/", timeout=5)
        assert exc.value.code == 302
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_fetch_json_wires_no_redirect_handler_into_its_opener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Behavioural (not source-text) proof that ``_fetch_json`` really
    passes a ``_NoRedirectHandler`` instance to ``build_opener`` on a real
    call -- captures the ACTUAL arguments ``_fetch_json`` passes at
    runtime, closing the gap the real-redirect test above leaves (that test
    proves the handler+opener combination refuses a 3xx in isolation; this
    proves ``_fetch_json`` is the one constructing that exact combination).
    """

    config = _posture_config(tmp_path)
    captured: dict[str, Any] = {}

    def _spy_build_opener(*handlers: Any) -> Any:
        captured["handlers"] = handlers
        return _FakeOpener(b'{"id": "W1", "cited_by_count": 1}')

    monkeypatch.setattr(urllib.request, "build_opener", _spy_build_opener)

    _fetch_json("https://api.openalex.org/works/W1", config=config, provider="openalex")

    assert any(isinstance(h, _NoRedirectHandler) for h in captured.get("handlers", ()))


# ---------------------------------------------------------------------------
# M1 -- a failed audit write must not permanently suppress the audit trail
# ---------------------------------------------------------------------------


def test_failed_audit_write_does_not_permanently_suppress_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The literal M1 repro: record_event() returning None (fail-open,
    simulating a transient write failure) on the FIRST authorization call
    must not mark the config permanently audited -- a SECOND call, with
    the write now succeeding, must retry and land exactly one row."""

    config = _posture_config(tmp_path)

    real_record_event = audit_service.record_event
    calls = {"n": 0}

    def _flaky_record_event(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # simulate a failed write, fail-open contract
        return real_record_event(*args, **kwargs)

    monkeypatch.setattr(audit_service, "record_event", _flaky_record_event)

    # First call: authorization succeeds regardless (fail-open is for the
    # audit side-channel only, never for the authorization gate), but the
    # audit write itself failed.
    assert authorize_live_fetch(config, provider="openalex") is True
    assert calls["n"] == 1
    result = audit_service.list_events(config.paths, mutation_type="dev_test_posture_activated")
    assert result["items"] == [], "a failed write must not produce a row"

    # Second call against the SAME config: since it was never marked
    # audited, this retries -- and this time record_event succeeds.
    assert authorize_live_fetch(config, provider="openalex") is True
    assert calls["n"] == 2
    result = audit_service.list_events(config.paths, mutation_type="dev_test_posture_activated")
    assert len(result["items"]) == 1, "the retry must land exactly one row"

    # Third call: now genuinely audited -- no further write attempts.
    assert authorize_live_fetch(config, provider="openalex") is True
    assert calls["n"] == 2, "an already-audited config must not retry"


# ---------------------------------------------------------------------------
# M2 -- ONE dedup point shared by api.app.create_app() and this package
# ---------------------------------------------------------------------------


def test_create_app_then_fetch_on_same_config_emits_exactly_one_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _full_posture_config(tmp_path, declared_by="nick-m2-a")

    create_app(config)  # site 1: server startup
    monkeypatch.setattr(openalex, "_fetch_json", lambda url, **kw: {"id": "W1", "cited_by_count": 1})
    openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)  # site 2: fetch

    result = audit_service.list_events(config.paths, mutation_type="dev_test_posture_activated")
    assert len(result["items"]) == 1, f"expected exactly one row, got {result['items']}"


def test_fetch_then_create_app_on_same_config_emits_exactly_one_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Order reversed -- proves the dedup is genuinely shared, not merely
    'whichever site runs first has no competition because the other was
    never exercised in the other test'."""

    config = _full_posture_config(tmp_path, declared_by="nick-m2-b")

    monkeypatch.setattr(openalex, "_fetch_json", lambda url, **kw: {"id": "W1", "cited_by_count": 1})
    openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)  # site 2 first
    create_app(config)  # site 1 second

    result = audit_service.list_events(config.paths, mutation_type="dev_test_posture_activated")
    assert len(result["items"]) == 1, f"expected exactly one row, got {result['items']}"


def test_audit_event_fires_without_create_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No ``create_app()`` call anywhere in this test -- yet a bare fetch
    under a declared posture must still produce exactly one audit row."""

    config = _posture_config(tmp_path, declared_by="nick-fetch-test")
    monkeypatch.setattr(openalex, "_fetch_json", lambda url, **kw: {"id": "W1", "cited_by_count": 1})

    openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)

    result = audit_service.list_events(config.paths, mutation_type="dev_test_posture_activated")
    items = result["items"]
    assert len(items) == 1, f"expected exactly one audit row, got {items}"
    row = items[0]
    assert row["mutation_type"] == "dev_test_posture_activated"
    assert row["action"] == "dev_test_posture.live_fetch_enabled"
    assert row["policy_snapshot"]["declared_by"] == "nick-fetch-test"


def test_audit_event_fires_exactly_once_across_many_records_and_providers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not once per record: fetching 5 records across all 3 providers
    through the SAME config must still yield exactly ONE audit row."""

    config = _posture_config(tmp_path)
    monkeypatch.setattr(openalex, "_fetch_json", lambda url, **kw: {"id": "W1", "cited_by_count": 1})
    monkeypatch.setattr(
        crossref, "_fetch_json", lambda url, **kw: {"message": {"DOI": "10.1/x"}}
    )
    monkeypatch.setattr(
        semantic_scholar, "_fetch_json", lambda url, **kw: {"paperId": "p1"}
    )

    for _ in range(5):
        openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)
    crossref.fetch(crossref.CrossrefRequest("10.1/x"), config=config)
    semantic_scholar.fetch(semantic_scholar.SemanticScholarRequest("p1"), config=config)

    result = audit_service.list_events(config.paths, mutation_type="dev_test_posture_activated")
    assert len(result["items"]) == 1


def test_no_audit_event_when_posture_not_declared(tmp_path: Path) -> None:
    config = _posture_config(tmp_path, declared=False)
    openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)

    result = audit_service.list_events(config.paths, mutation_type="dev_test_posture_activated")
    assert result["items"] == []


# ---------------------------------------------------------------------------
# ProviderFetchResult is unchanged (regression guard for the non-laundering
# guarantee, alongside the fuller check in test_attribution_fetch_seam.py)
# ---------------------------------------------------------------------------


def test_provider_fetch_result_still_has_no_value_field() -> None:
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(ProviderFetchResult)}
    assert field_names == {"provider", "status", "reason"}


def test_cleared_provider_fetch_result_is_a_distinct_type() -> None:
    assert ProviderFetchResult is not ClearedProviderFetchResult
    assert not issubclass(ClearedProviderFetchResult, ProviderFetchResult)
    assert not issubclass(ProviderFetchResult, ClearedProviderFetchResult)


def test_to_record_is_mediate_egress_consumable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _posture_config(tmp_path)
    monkeypatch.setattr(openalex, "_fetch_json", lambda url, **kw: {"id": "W1", "cited_by_count": 1})
    result = openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=config)

    record = result.to_record()
    assert record["clearance"] == result.clearance

    reg_yaml = tmp_path / "clearance_gates.yaml"
    reg_yaml.write_text(
        "schema_version: '1.0'\n"
        "applies_to_kinds: [source_attribution]\n"
        "gates:\n"
        "  - gate_id: DEF-1\n"
        "    blocks_scope: redistribution\n"
        "    state: open\n"
        "    summary: x\n"
        "    evidence_pointer: docs/x.md\n"
        "    closed_by: null\n",
        encoding="utf-8",
    )
    registry = GateRegistry(path=reg_yaml)

    with pytest.raises(ClearanceDenied):
        mediate_egress(
            [record], kind="source_attribution", target_scope="redistribution",
            target="notebooklm", registry=registry,
        )


# ---------------------------------------------------------------------------
# THE CRITICAL TEST — a stamp survives the posture being removed AND every
# redistribution gate being closed. A wrong design passes every other test
# above and fails only this one.
# ---------------------------------------------------------------------------


def test_stamped_record_stays_denied_after_posture_removed_and_gates_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 1. Fetch a record under a DECLARED posture.
    on_config = _posture_config(tmp_path, subdir="fdry_on", declared_by="nick")
    monkeypatch.setattr(
        openalex, "_fetch_json", lambda url, **kw: {"id": "W1", "cited_by_count": 1}
    )
    result = openalex.fetch(openalex.OpenAlexRequest("10.1/x"), config=on_config)
    assert isinstance(result, ClearedProviderFetchResult)
    record = result.to_record()

    # 2. Build a SEPARATE config with the posture block deleted entirely,
    # and confirm it genuinely resolves False -- this is not a no-op check.
    off_config = _posture_config(tmp_path, subdir="fdry_off", declared=False)
    assert off_config.dev_test_posture_live_fetch_enabled() is False

    # 3. Build a registry where the ONLY gate blocking redistribution is
    # now CLOSED (by a named human) -- simulating the gate itself closing,
    # not merely the posture being withdrawn.
    reg_yaml = tmp_path / "clearance_gates_closed.yaml"
    reg_yaml.write_text(
        "schema_version: '1.0'\n"
        "applies_to_kinds: [source_attribution]\n"
        "gates:\n"
        "  - gate_id: DEF-1\n"
        "    blocks_scope: redistribution\n"
        "    state: closed\n"
        "    summary: closed for this test\n"
        "    evidence_pointer: docs/x.md\n"
        "    closed_by: a-human\n",
        encoding="utf-8",
    )
    closed_registry = GateRegistry(path=reg_yaml)
    assert closed_registry.open_scopes() == frozenset()  # nothing open now

    # 4. Re-run mediation on the SAME already-existing record. It must
    # STILL be denied -- the stamp is durable and was never re-derived.
    with pytest.raises(ClearanceDenied) as exc:
        mediate_egress(
            [record],
            kind="source_attribution",
            target_scope="redistribution",
            target="notebooklm",
            registry=closed_registry,
        )
    assert "redistribution" in str(exc.value)
