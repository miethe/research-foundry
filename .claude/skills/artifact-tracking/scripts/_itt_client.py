#!/usr/bin/env python3
"""Thin, injectable IntentTree client — the shared seam for the M2 node-join tools.

Both ``stamp-node-slug.py`` and ``verify-slug-roundtrip.py`` talk to IntentTree exclusively
through this module, never by shelling out or opening sockets directly. This module
deliberately uses **two different transports for two different concerns** — do not "fix" this
back into a single seam:

- **Reads go through the ``itt --json`` CLI** (``tree graph``, ``sync status``, ``node get``).
  That surface is proven and stays as-is.
- **Writes go through a raw HTTP PATCH** to ``/api/v1/nodes/{id}`` instead of shelling out to
  ``itt node update --meta``. Reason (measured, not theoretical): the CLI's ``--meta KEY=VALUE``
  parser has no JSON-object mode, so it JSON-*stringifies* a nested dict/list value
  (``node.meta.fingerprint`` is one on this tree) — the write round-trips the *content*
  losslessly but silently changes its *type* from object to string. 38 of this tree's 143 nodes
  carry such nested meta values, many of them already ``completed``. That is silent degradation
  of live shared state and is not an acceptable write path for this tool. The HTTP PATCH was
  verified directly against the live node server (``tree_01KVTH95ETM8YRYCV2ENHVR124``): round-
  tripping the ledger node's real ``meta`` dict through this endpoint returned a byte-identical
  dict with ``fingerprint`` still typed as a JSON object. ``/api/v2/nodes/...`` is 404 for this
  resource — ``/api/v1`` is correct. The CLI's ``--meta`` JSON-object gap is a genuine product
  gap in ``../intenttree``, logged as a follow-up there — this module works around it, it does
  not fix it upstream.

Every ``itt`` CLI invocation funnels through a single injectable ``runner`` callable, and every
HTTP write funnels through a single injectable ``http_call`` callable, so unit tests can fake
both seams with plain Python functions — no subprocess, no network (this repo's suites are
deterministic + offline).

Probed CLI gotchas this module still encodes for the read seam:

1. ``--json`` is a **global** flag and must precede the subcommand: ``itt --json node get <id>``
   works, ``itt node get <id> --json`` does not. :meth:`IttClient._json` always prepends it.
2. Whole-``meta`` replace semantics still apply to the write path too: the PATCH body's ``meta``
   REPLACES the node's entire meta dict server-side, same as the CLI did. Callers MUST
   read-merge-write (see ``stamp-node-slug.py``), never pass a partial dict.

Config resolution (mirrors the ``itt`` CLI's own precedence — see
``intenttree_client.cli.config.CliConfig``): explicit constructor args > environment variables
(``INTENTTREE_API_URL`` / ``INTENTTREE_API_TOKEN``) > the config file at
``~/.config/intenttree/config.toml`` (TOML keys ``api_url`` / ``api_token``) > a bare-localhost
default for the URL (there is no default token). The token is never logged or included in any
exception message.

Python 3.10+ floor (must import on the node's 3.11 — no 3.12-only syntax).
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

Runner = Callable[[list[str]], "CliResult"]
HttpCall = Callable[[str, str, dict[str, Any], dict[str, str]], "HttpResult"]

_ENV_API_URL = "INTENTTREE_API_URL"
_ENV_API_TOKEN = "INTENTTREE_API_TOKEN"
_CONFIG_FILE = Path.home() / ".config" / "intenttree" / "config.toml"
_DEFAULT_API_URL = "http://localhost:8000"


@dataclass
class CliResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class HttpResult:
    status: int
    body: str


class IttError(RuntimeError):
    """Raised when an ``itt`` invocation or an HTTP write fails or returns unparsable JSON."""


def _default_runner(args: list[str]) -> CliResult:
    proc = subprocess.run(["itt", *args], capture_output=True, text=True, timeout=60)
    return CliResult(proc.returncode, proc.stdout, proc.stderr)


def _load_config_file() -> dict[str, Any]:
    """Best-effort TOML read of ``~/.config/intenttree/config.toml``. Never raises."""
    if not _CONFIG_FILE.exists():
        return {}
    try:
        import tomllib  # Python 3.11+ stdlib

        with _CONFIG_FILE.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def resolve_api_url(explicit: str | None = None) -> str:
    """flag/arg > ``INTENTTREE_API_URL`` env > config file ``api_url`` > localhost default."""
    if explicit:
        return explicit
    env_val = os.environ.get(_ENV_API_URL)
    if env_val:
        return env_val
    file_val = _load_config_file().get("api_url")
    if file_val:
        return str(file_val)
    return _DEFAULT_API_URL


def resolve_api_token(explicit: str | None = None) -> str | None:
    """flag/arg > ``INTENTTREE_API_TOKEN`` env > config file ``api_token`` > None.

    Never logged; callers must not print the return value.
    """
    if explicit:
        return explicit
    env_val = os.environ.get(_ENV_API_TOKEN)
    if env_val:
        return env_val
    file_val = _load_config_file().get("api_token")
    return str(file_val) if file_val else None


def _default_http_call(
    url: str, method: str, body: dict[str, Any], headers: dict[str, str]
) -> HttpResult:
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:  # noqa: S310 (internal API host)
            return HttpResult(resp.status, resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, exc.read().decode("utf-8"))


class IttClient:
    """Injectable wrapper over the ``itt`` CLI (reads) + a raw HTTP PATCH (writes).

    Production code uses the default subprocess runner + the default ``urllib``-based HTTP
    call; tests construct ``IttClient(runner=fake_runner, http_call=fake_http)`` with canned
    callables — no real subprocess or socket ever touched in the suite.
    """

    def __init__(
        self,
        runner: Runner | None = None,
        http_call: HttpCall | None = None,
        *,
        api_url: str | None = None,
        api_token: str | None = None,
    ) -> None:
        self._runner = runner or _default_runner
        self._http_call = http_call or _default_http_call
        self._api_url = resolve_api_url(api_url)
        self._api_token = resolve_api_token(api_token)

    def _json(self, args: list[str]) -> Any:
        result = self._runner(["--json", *args])
        if result.returncode != 0:
            raise IttError(
                f"itt {' '.join(args)} failed (exit {result.returncode}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise IttError(f"itt {' '.join(args)} returned non-JSON output: {exc}") from exc

    def get_node(self, node_id: str) -> dict:
        return self._json(["node", "get", node_id])

    def tree_graph(self, tree_id: str) -> dict:
        return self._json(["tree", "graph", tree_id])

    def list_bindings_page(
        self, tree: str | None = None, cursor: str | None = None, limit: int = 200
    ) -> dict:
        """One page of ``GET /api/v2/work-item-sync/bindings``.

        ``--tree`` is passed through for documentation/intent, but per the probed gotcha it is
        silently ignored server-side — callers MUST still filter client-side (see
        ``_slug_resolution.build_binding_maps``, which takes the tree's own node-id set).
        """
        args = ["sync", "status"]
        if tree:
            args += ["--tree", tree]
        if cursor:
            args += ["--cursor", cursor]
        args += ["--limit", str(limit)]
        return self._json(args)

    def iter_bindings(self, tree: str | None = None, limit: int = 200) -> Iterator[dict]:
        """Paginate every binding page, yielding each ``items[]`` entry."""
        cursor: str | None = None
        while True:
            page = self.list_bindings_page(tree=tree, cursor=cursor, limit=limit)
            items = page.get("items") or []
            for item in items:
                yield item
            cursor = page.get("next_cursor")
            if not cursor or not items:
                break

    def update_node_meta(self, node_id: str, meta: dict[str, Any]) -> dict:
        """PATCH the FULL ``meta`` dict — this REPLACES the node's existing meta server-side.

        Callers must have already read the node and merged in memory (gotcha 2); this method
        performs no merge of its own. Empty ``meta`` is a no-op (returns current state untouched,
        no HTTP call made). Body is a real JSON object — nested dict/list values are preserved
        as objects, never JSON-stringified (see module docstring for why the old
        ``itt node update --meta`` path was rejected).
        """
        if not meta:
            return self.get_node(node_id)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        url = f"{self._api_url.rstrip('/')}/api/v1/nodes/{node_id}"
        result = self._http_call(url, "PATCH", {"meta": meta}, headers)
        if result.status < 200 or result.status >= 300:
            raise IttError(
                f"PATCH /api/v1/nodes/{node_id} failed (status {result.status}): "
                f"{result.body.strip()}"
            )
        try:
            return json.loads(result.body)
        except json.JSONDecodeError as exc:
            raise IttError(
                f"PATCH /api/v1/nodes/{node_id} returned non-JSON response: {exc}"
            ) from exc

    # ------------------------------------------------------------------------------------------
    # Shipped Work Ledger M3 additions — the typed evidence/external-link/validation write seam
    # (see the M3 leg contract §2/§3). All of these are raw HTTP through the same injectable
    # ``http_call`` seam as ``update_node_meta``; none of them shell out to the ``itt`` CLI (the
    # CLI has no coverage for these routes at all). Additive only — nothing above this point is
    # touched.
    # ------------------------------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        return headers

    def _raw_http(self, path: str, method: str, body: dict[str, Any]) -> HttpResult:
        url = f"{self._api_url.rstrip('/')}{path}"
        return self._http_call(url, method, body, self._headers())

    def _parse_json_response(self, result: HttpResult, context: str) -> Any:
        try:
            return json.loads(result.body)
        except json.JSONDecodeError as exc:
            raise IttError(f"{context} returned non-JSON response: {exc}") from exc

    def _http_json(self, path: str, method: str, body: dict[str, Any] | None = None) -> Any:
        """Raw HTTP call that raises :class:`IttError` on any non-2xx status."""
        result = self._raw_http(path, method, body or {})
        if result.status < 200 or result.status >= 300:
            raise IttError(
                f"{method} {path} failed (status {result.status}): {result.body.strip()}"
            )
        return self._parse_json_response(result, f"{method} {path}")

    def get_node_full(
        self,
        node_id: str,
        include: tuple[str, ...] = ("completion_evidence", "external_links", "validation_runs"),
    ) -> dict:
        """``GET /api/v1/nodes/{node_id}?include=...`` — the node payload WITH its typed evidence
        rows, external links, and validation runs, none of which the plain ``get_node`` (CLI-based
        ``itt node get``) response carries. Read-only."""
        query = f"?include={','.join(include)}" if include else ""
        return self._http_json(f"/api/v1/nodes/{node_id}{query}", "GET")

    def tree_nodes(self, tree_id: str) -> list[dict]:
        """``GET /api/v1/trees/{tree_id}/graph`` -> the tree's ``nodes`` list. Read-only."""
        payload = self._http_json(f"/api/v1/trees/{tree_id}/graph", "GET")
        return payload.get("nodes", [])

    def attach_external_link(
        self,
        node_id: str,
        *,
        system: str,
        external_id: str,
        external_path: str | None = None,
        context_label: str | None = None,
        stored_ref: dict[str, Any] | None = None,
    ) -> dict:
        """``POST /api/v1/nodes/{node_id}/external-links``. Server-side UPSERT semantics on
        (target, system, external_id) — safe to call repeatedly with the same identity."""
        body: dict[str, Any] = {"system": system, "external_id": external_id}
        if external_path is not None:
            body["external_path"] = external_path
        if context_label is not None:
            body["context_label"] = context_label
        if stored_ref is not None:
            body["stored_ref"] = stored_ref
        return self._http_json(f"/api/v1/nodes/{node_id}/external-links", "POST", body)

    def attach_evidence(
        self,
        node_id: str,
        *,
        kind: str,
        label: str | None = None,
        ref_value: str | None = None,
        delivery_class: str | None = None,
        occurred_at: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict:
        """``POST /api/v1/nodes/{node_id}/evidence`` — a typed ``CompletionEvidence`` row."""
        body: dict[str, Any] = {"kind": kind}
        if label is not None:
            body["label"] = label
        if ref_value is not None:
            body["ref_value"] = ref_value
        if delivery_class is not None:
            body["delivery_class"] = delivery_class
        if occurred_at is not None:
            body["occurred_at"] = occurred_at
        if data is not None:
            body["data"] = data
        return self._http_json(f"/api/v1/nodes/{node_id}/evidence", "POST", body)

    def record_validation(
        self,
        node_id: str,
        *,
        command: str,
        status: str,
        kind: str = "custom",
        started_at: str | None = None,
        finished_at: str | None = None,
        output_ref: str | None = None,
        environment: dict[str, Any] | None = None,
    ) -> dict:
        """Record a validation result, per D-M3-1's forward-compatibility requirement.

        Tries ``POST /api/v1/nodes/{node_id}/validations`` first (the typed ``ValidationRun``
        route — not yet live on the running server, confirmed 404 at probe time). On a 404, falls
        back to ``attach_evidence(kind="validation", ...)`` so a typed row is always written
        today, with zero code change required the day the upstream route lands. Any OTHER non-2xx
        status (from either path) raises :class:`IttError` — only 404 on the primary route is
        treated as "route not deployed yet".

        The returned dict always carries a ``_write_path`` key — ``"validations"`` or
        ``"evidence_fallback"`` — so callers can tell which path was actually used.
        """
        body: dict[str, Any] = {"command": command, "status": status, "kind": kind}
        if started_at is not None:
            body["started_at"] = started_at
        if finished_at is not None:
            body["finished_at"] = finished_at
        if output_ref is not None:
            body["output_ref"] = output_ref
        if environment is not None:
            body["environment"] = environment

        path = f"/api/v1/nodes/{node_id}/validations"
        result = self._raw_http(path, "POST", body)
        if 200 <= result.status < 300:
            raw_payload = self._parse_json_response(result, f"POST {path}")
            payload: dict[str, Any] = dict(raw_payload) if isinstance(raw_payload, dict) else {"result": raw_payload}
            payload["_write_path"] = "validations"
            return payload

        if result.status != 404:
            raise IttError(f"POST {path} failed (status {result.status}): {result.body.strip()}")

        evidence_data: dict[str, Any] = {"command": command, "status": status, "kind": kind}
        if started_at is not None:
            evidence_data["started_at"] = started_at
        if finished_at is not None:
            evidence_data["finished_at"] = finished_at
        if output_ref is not None:
            evidence_data["output_ref"] = output_ref
        if environment is not None:
            evidence_data["environment"] = environment

        raw_evidence_payload = self.attach_evidence(
            node_id, kind="validation", label=command, ref_value=output_ref, data=evidence_data
        )
        evidence_payload: dict[str, Any] = (
            dict(raw_evidence_payload) if isinstance(raw_evidence_payload, dict)
            else {"result": raw_evidence_payload}
        )
        evidence_payload["_write_path"] = "evidence_fallback"
        return evidence_payload
