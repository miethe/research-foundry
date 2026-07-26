# DI-1 Adversarial Re-Audit — Probe 4: Catalog / Evidence-Planning / Share Surfaces

Mode E (read-only). HEAD at audit time: `d71a261`. Baseline for "NEW since remediation":
`08559a0` (feat(multi-user): workspace isolation for runs/claims/evidence + public visibility,
DF-004). Commits in scope: `d824290`, `e1cf560`, `95e8419` (CARP C3 P1–P6), `feab7de`
(planning docs, no code), `d71a261` (claim-term-indexing v1).

Scope note: this probe traces the catalog-retrieval/evidence-planning stack, the shared
catalog API, the assertion-catalog API, the share-link surface, and DF-004 run/report
visibility. It does **not** re-walk the WKSP-304 sensitivity/RBAC surfaces already covered
by prior probes except where a new commit touches them.

---

## 1. `catalog_retrieval.py` (CARP-2 governed adapter) — **NEEDS-REMEDIATION** (one function)

**`retrieve()` / `catalog_receipt()` / `_collect_candidates()` — CONFINED.**
Every data-bearing call requires `identity: AuthIdentity | None`; absence or a blank
`identity.workspace_id` short-circuits to `denial_reason="workspace_context_missing"`
before any catalog call (`catalog_retrieval.py:500-508`, `:226-227`). All actual reads
(`catalog.search(identity=identity, ...)` at `:437`, `catalog.packet(assertion_id,
identity=identity)` at `:541`) pass the caller's own `identity` straight through to
`AssertionCatalog`, which itself roots every read at
`assertion_ledger/workspaces/{sha256(identity.workspace_id)}` (`assertion_catalog.py:279`,
`:266-276`). ws_b calling `retrieve()`/`catalog_receipt()` with its own identity can never
reach ws_a's records through this path — confirmed by code inspection, no gap found.

**`peek_catalog_generation_id(catalog, workspace_id: str) -> str | None` — NEEDS-REMEDIATION.**
`catalog_retrieval.py:185-212`. This is the *one* function in the module that takes a raw
`workspace_id: str` instead of an `AuthIdentity` — no identity, no rights check, nothing:

```python
def peek_catalog_generation_id(catalog: AssertionCatalog, workspace_id: str) -> str | None:
    path = catalog.projection_path(workspace_id)          # deterministic hash of the raw string
    if not path.is_file() or path.is_symlink():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    ...
    return payload.get("catalog_generation_id")
```

It reads `.rf_cache/assertion_catalog/{sha256(workspace_id)}.json` directly off disk and
returns that workspace's `catalog_generation_id` (a sha256 content-digest over its whole
assertion corpus) to *any* caller who can name a `workspace_id` string. It is exported in
`__all__` (`:625`) and is a genuinely new primitive (introduced whole in `95e8419`).

Sole current caller: `research_evidence_planning.py:595`,
`peek_catalog_generation_id(catalog, request.workspace_id)`, where `request` is an
`EvidencePlanRequest` (the mid-plan drift check, carp-contract-freeze §3.4). `request.workspace_id`
is a **plain string field on the request dataclass, independent of the `identity` parameter
`build_evidence_plan` is also given** — nothing inside `build_evidence_plan` or
`peek_catalog_generation_id` asserts `request.workspace_id == identity.workspace_id`.

Both current construction sites happen to keep the two values equal by convention:
- `planning.py:812`: `workspace_id=effective_workspace_id or ""` where
  `effective_workspace_id = workspace_id if identity is None else identity.workspace_id` (`:747`).
- `search_router/router.py:344`: `workspace_id=identity.workspace_id if identity is not None else ""`.

**ws_b vs ws_a outcome (as wired today):** no reachable HTTP path lets ws_b set
`request.workspace_id` to `ws_a` while `identity.workspace_id` is genuinely `ws_b` — both known
call sites derive it from the *same* identity. So through the two known callers there is no
live exploit today.

**Residual risk:** the guarantee is caller discipline, not an enforced invariant on the
primitive. Any future or unaudited caller of `build_evidence_plan()`/`EvidencePlanRequest`
(both public, `__all__`-exported) that supplies a `workspace_id` different from its `identity`
gets: (a) an existence oracle — whether ws_a has ever built an assertion-catalog projection —
and (b) a sha256 digest of ws_a's canonicalized assertion corpus, both read with **zero**
authorization check, via a path that bypasses `AssertionCatalog`'s own identity gate entirely.
This is exactly the "existence-hiding" property the prior audit credited `AssertionCatalog.packet()`
/`catalog_service.get_item()` for (packet returns `None` with no existence hint; catalog's
`get_item` explicitly documents "existence of hidden sensitive items is not leaked") — and this
new function does not honor it. Practical worst case via the two current callers is a
mismatch-triggered fail-closed `residual`/`evaluation_error` on every question (denial, not
disclosure) — but the primitive itself provides no such guarantee, it is incidental to how the
two callers happen to be written today.

---

## 2. `research_evidence_planning.py` / `planning.py` (CARP-3/4.2 evidence-plan builder) — **CONFINED**

`build_evidence_plan()` never touches `assertion_ledger/` directly and never imports
`assertion_catalog`/`assertion_reuse` (module docstring, `:1-10`) — every catalog fact arrives
through the P2 adapter's DTOs. `catalog_receipt(catalog, identity)` (`:569`) is
identity-gated exactly like §1 above. The one gap in this module is the `peek_catalog_generation_id`
call already covered in §1 — no other unscoped read found in this file. `planning.py`'s
CARP-4.2 block (`:792-862`) stamps `EvidencePlanRequest.workspace_id` from
`effective_workspace_id` (`:747`, `identity.workspace_id` whenever identity is present) — same
value `run.yaml.workspace_id` gets stamped with — so the evidence plan and the run it's attached
to always agree on workspace ownership.

---

## 3. `catalog_service.py` / `assertion_catalog.py` (shared evidence catalog + claim-term-index v1) — **CONFINED**

WKSP-304's existing `identity` + `_isolation_active(paths)` scoping (`search()` at
`catalog_service.py:1396-1403`, `get_item()` at `:1698-1699`, `:1730-1810`) is unmodified by
`d71a261`. The new `term`/`role` filters (TASK-2.5/2.6) are `EXISTS` subqueries correlated on
`catalog_items.catalog_item_id` (`:1419-1436`) — since the outer query already carries the
`AND workspace_id = ?` predicate when scoped, a term/role hit can only ever apply to a row
already confined to the caller's workspace. `catalog_terms` itself carries **no**
`workspace_id` column (by design — comment at `:1583-1589`); the one place that queries it
independently of a per-item lookup, `_facets()._distinct_term_column()` (`:1582-1601`),
explicitly `JOIN`s back to `catalog_items` and applies `ci.workspace_id = ?` (`:1590`) when
scoped. No unguarded direct read of `catalog_terms` found. FTS-matched `match_ids`
(`:1461-1466`) are unscoped at the FTS-query step but are AND-combined with the same scoped
`WHERE` before being materialized into rows or a `total` count (`:1495-1520`) — cross-workspace
ids never survive to the response.

`stats()`/`import_run()`/`import_all()` still take no `identity` at all (`catalog_service.py:1818`,
router TODOs at `catalog.py:66-67,150-152,171-172`) — this is a **pre-existing, explicitly
documented** gap (not touched by any of the 4 reviewed commits; confirmed via
`git log 08559a0..HEAD -- catalog_service.py catalog.py` showing only the term-index commit),
carried forward unchanged. Flagging for completeness, not as a new regression.

---

## 4. `assertions.py` router — **CONFINED**

Every route (`search_assertions`, `get_assertion_lineage`, `get_assertion_impact`,
`get_assertion_packet`) resolves `identity = getattr(request.state, "identity", None)`
(`assertions.py:152,172,204,222`) — server-derived only, never from a client-supplied body/query
field — and forwards it straight into `AssertionCatalog`'s identity-gated methods. No client
input anywhere in this router can set a workspace context. Unchanged by the reviewed commits
(no `git log` hits for this file after `08559a0`).

---

## 5. `share_store.py` / share-link surface (`reports.py` `/reports/{id}/share-links`, `/reports/shares/{token}`) — **CONFINED**

Pre-existing (public-multiuser-release Phase 5.6), **not touched** by any of the four reviewed
commits (`git log 08559a0..HEAD` returns nothing for `share_store.py`). Included per the audit
brief for completeness:

- Creation (`reports.py:1044-1113`) requires `_RBAC_REPORT_ADMIN` (owner/admin role) —
  explicit, opt-in, authenticated action by the resource's own owner. The token is 256-bit
  random (`share_store.py:135`), and the draft's sensitivity is checked against the requested
  threshold at creation time (`reports.py:1081-1097`).
- Resolution (`reports.py:1120-1211`) is the **only** intentionally-unauthenticated endpoint in
  the router — `identity` is deliberately *not* threaded from `request.state` (comment at
  `:1145-1151`); both draft loads pass `identity=None` explicitly. `report_id` is taken **only**
  from the resolved `link["report_draft_id"]` (`:1159`), never from any caller-supplied path/body
  field, so there is no way to redirect a valid token at a different draft. Sensitivity is
  **re-checked** against the draft's *current* label at every resolution (`:1172-1188`, PRD AC-2)
  — a relabel to a more sensitive tier after link creation fails closed (422), not open.
- ws_b vs ws_a: ws_b can read ws_a's draft **only** by possessing a valid, non-revoked,
  non-expired token minted by ws_a's own owner/admin action — an explicit, single-resource,
  read-only grant, exactly the "opt-in, correctly gated" shape the audit brief asks about.
  No enumeration path found (`resolve_share_link` does an exact `WHERE share_token = ?` lookup;
  no listing endpoint is unauthenticated).

---

## 6. DF-004 "public visibility" (runs/reports) — **CONFINED** (unchanged by these 4 commits)

`visibility` defaults to `"workspace"` everywhere it is threaded (`planning.py:577,988`,
`run_launch.py:130`, `runs.py:431`) and only the literal string `"public"` changes behavior;
any other value falls back to `"workspace"` (`planning.py:988`). Read-side enforcement lives in
`export_service.py:1132,1142,1161` (`run_meta["visibility"] == "public"` OR
`workspace_id` match) — confirmed via `git diff 08559a0..HEAD -- export_service.py` that this
function's gating logic is **byte-unchanged**; the CARP commit only *adds* a new
`_retrieval_summary()` block (`export_service.py:955-1021`) that reads
`rp.research_evidence_plan` for the **same run only** (`rp` is that run's own `RunPaths`) — no
cross-run, cross-workspace read introduced there. `writeback.py:33,286` explicitly documents
that `public` visibility never grants the mutating writeback action — read-only stays read-only.
`runs.py`'s diff since `08559a0` (CARP-5.1, `retrieval_policy`/`retrieval_limits`/
`evidence_plan_ref`/`retrieval_summary` fields) is purely additive passthrough to `plan_run`
and does not touch the visibility gate.

---

## 7. MCP transport — `search_router/mcp_server.py` + `router.run_search()` (CARP-5.2) — **NEEDS-REMEDIATION — NEW, unscoped**

This is the headline finding. Introduced whole by `95e8419` (CARP C3 P3–P6), **new since
`08559a0`**.

`mcp_server.py:80-104` (`_identity_from_mapping`) marshals a **caller-supplied JSON dict**
straight into an `AuthIdentity` with **zero verification**:

```python
def _identity_from_mapping(identity: dict[str, Any] | None) -> AuthIdentity | None:
    if identity is None:
        return None
    return AuthIdentity(
        user_id=str(identity.get("user_id") or ""),
        workspace_id=str(identity.get("workspace_id") or ""),   # <- caller names any workspace
        roles=tuple(identity.get("roles") or ()),
    )
```

Every one of the 7 registered MCP tools (`search_run`, `search_source_discovery`,
`search_semantic_discovery`, `search_github_discovery`, `search_quick_lookup`,
`search_official_sources`, `search_academic_discovery` — `mcp_server.py:127-`,`176-`) accepts
this `identity` dict **and** a bare `sensitivity_threshold: str | None` argument, both forwarded
verbatim into `router.run_search(request, identity=_identity_from_mapping(identity),
sensitivity_threshold=sensitivity_threshold, evidence_plan=evidence_plan)`. The module's own
docstring calls this "a thin transport adapter... no business logic lives here" (`:53-56`) — by
design, this transport performs **no authentication**, unlike every other reviewed transport
(HTTP routers all resolve `identity = getattr(request.state, "identity", None)` from server-side
auth middleware; the MCP layer resolves it from the tool-call arguments the caller wrote).

Path from there into the real ledger, confirmed by reading `run_search` (`router.py:500-608`):
when `request["retrieval"]["policy"]` is `"catalog_only"`/`"catalog_then_discovery"`,
`_build_ad_hoc_evidence_plan(query, ..., identity=identity, sensitivity_threshold=sensitivity_threshold,
...)` (`router.py:308-358`) builds an `EvidencePlanRequest` with
`workspace_id=identity.workspace_id if identity is not None else ""` (`:344`) and calls
`build_evidence_plan(catalog, identity=identity, request=request)`, which calls the real,
identity-gated `AssertionCatalog.search()`/`.packet()` (§1/§2 above) — **but now `identity` is the
caller's self-declared value, not a server-verified one.**

The result is returned to the MCP caller. `router.py:796-811`:

```python
search_run["retrieval"] = {
    "policy": retrieval_policy,
    "evidence_plan_ref": plan_dict.get("evidence_plan_id"),
    "selections": [
        {
            "question_id": q["question_id"],
            "assertion_id": (q.get("selected_assertion_ref") or {}).get("assertion_id"),
            "assertion_version": (q.get("selected_assertion_ref") or {}).get("assertion_version"),
            "retrieval_receipt": q.get("retrieval_receipt"),
        }
        for q in plan_dict.get("questions", [])
    ],
    "metrics": plan_dict.get("summary", {}),
}
```

**Concrete ws_b-vs-ws_a outcome:** an MCP caller who genuinely belongs to ws_b invokes
`search_run` with `request.query="<term guessed/known to exist in ws_a's ledger>"`,
`request.retrieval.policy="catalog_only"`, `identity={"workspace_id": "ws_a", "user_id":
"anyone", "roles": []}`, and `sensitivity_threshold` set to the loosest tier they want
(also self-declared — there is no server-side ceiling override on this transport, unlike
`catalog.py`'s `_sensitivity_threshold_override(request)` which reads a server-set
`app.state` value the HTTP routers use). If ws_a has an eligible, rights-cleared,
lexically-matching assertion at/below that self-declared threshold, the tool response
discloses that assertion's real `assertion_id`/`assertion_version` (plus
`summary.questions_covered`/`candidates_evaluated` counts) — content that belongs to ws_a,
obtained by a caller who never proved membership in ws_a, merely declared it. Iterating
query terms turns this into a lexical enumeration oracle over ws_a's entire eligible catalog.
Two self-asserted trust inputs stack here (`workspace_id` *and* `sensitivity_threshold`), which
is strictly worse than the single-input gap in §1.

**Residual risk / what code alone cannot settle:** whether this is exploitable in practice
depends entirely on this MCP server's deployment topology — a per-user local `stdio` process
spawned under an already-fully-trusted local operator (where self-asserting a workspace buys
nothing an operator couldn't already do by reading the filesystem directly) is a materially
different risk than a shared, network-reachable MCP endpoint serving multiple identities behind
one process (where this is a full cross-tenant break). The code establishes no boundary either
way — CARP-5.2 added a caller-controlled identity parameter specifically because multiple
identities were expected to call the *same* running server; that expectation is the load-bearing
fact a human needs to confirm against how this server is actually run (systemd unit / LAN-bound
port vs. per-session subprocess) before this can be called adversarially safe or unsafe. Per the
audit's hard rule, this is not something to certify from code alone — it is exactly the shape of
finding that needs a Mode-D human gate.

---

## Summary (5 lines)

1. **New, real gap (needs human Mode-D review): the CARP-5.2 MCP transport** (`mcp_server.py` +
   `router.run_search`) accepts a caller-supplied, unverified `identity` (including
   `workspace_id`) **and** an unverified `sensitivity_threshold`, both wired straight into the
   real `AssertionCatalog` read path, with `assertion_id`/`assertion_version`/coverage counts
   returned in the tool response — self-declared workspace membership, not proven.
2. **New, latent gap (defense-in-depth, no live exploit found today): `peek_catalog_generation_id`**
   (`catalog_retrieval.py`) is an identity-free file-read primitive keyed by a raw `workspace_id`
   string; both current callers keep it aligned with `identity.workspace_id` by convention, not
   by any enforced invariant in the primitive or its caller `build_evidence_plan`.
3. Every other new CARP/term-index read surface traced — `retrieve()`/`catalog_receipt()`
   (catalog_retrieval), `build_evidence_plan()` (research_evidence_planning), the term/role
   facet additions in `catalog_service.search()`/`_facets()`, and every HTTP router
   (`assertions.py`, `catalog.py`) — is CONFINED: identity is always server-derived from
   `request.state`, never client input, and every new query composes correctly with the
   pre-existing workspace_id predicate.
4. The share-link surface and DF-004 public-visibility gate are both pre-existing (untouched by
   these 4 commits, confirmed via `git log`/`git diff` against `08559a0`) and remain CONFINED:
   share access is opt-in/RBAC-gated/single-resource/re-checked-at-resolution; visibility
   defaults to workspace-only and is read-only even when explicitly public.
5. Net: no HTTP-reachable regression was found. The regression is transport-shaped — CARP wired
   a real, workspace-partitioned data source into a channel (MCP) that has no equivalent of the
   HTTP layer's server-side identity resolution, and gave that channel a second self-asserted
   knob (`sensitivity_threshold`) the HTTP layer doesn't expose to callers at all.
