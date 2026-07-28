---
name: project-knowledge-mcp-p5a-cli-api-parity
description: RF Knowledge MCP Phase P5 Part A (KMCP-5.1/5.2, Knowledge CLI + GET-only API) shipped -- route/tool-naming resolution and a known deferred OpenAPI-drift test failure for whoever runs P5 Part B / P6
metadata:
  type: project
---

KMCP-5.1 (`rf knowledge` CLI) and KMCP-5.2 (GET-only API) shipped: `src/research_foundry/cli/commands/knowledge.py`
(registered in `cli_commands.py` next to the `agent-job` import) and `src/research_foundry/api/routers/knowledge.py`
(registered in `api/app.py`, unconditional, tag `knowledge`), on top of the committed P2/P3
`services/knowledge_access.py` and P4 `knowledge_mcp/registry.py`. Commit `ed24cb3` on
`feat/research-foundry-knowledge-mcp`. Builds on [[project_knowledge_mcp_p4b_rf_tools_inventory]].

**Why this matters for KMCP-5.3/5.4/P6:** the plan text's endpoint list ("/api/knowledge/search",
"/api/knowledge/fetch/{id}", "typed GET routes") is casual shorthand, not the literal route set -- resolving it
required cross-referencing the P1-frozen schemas, which turned out to demand MORE routes than the plan literally
named.

1. **The API ships 8 GET routes, not 6** -- full 1:1 parity with the MCP's 8-tool inventory, not just the 6 RF-extended
   ones the plan text lists. Reason: `knowledge_access.build_local_resource_url`/`_LOCAL_URL_RE` HARD-CODE every
   `url` field (in every search result and fetch document, core AND RF-extended) to the literal path
   `/api/knowledge/v1/fetch/<percent-encoded-id>` (schema-frozen regex in both `knowledge_search_response.
   schema.yaml` and `knowledge_document.schema.yaml`). Skipping that exact route would leave every URL the service
   emits a dead link through this API. So the router registers BOTH a frozen-core pair
   (`GET /api/knowledge/v1/search` -> `search_core`, `GET /api/knowledge/v1/fetch/{id}` -> `fetch_core`, exact DTOs,
   NO `stamp()` -- would violate the closed-root `additionalProperties: false` contract) AND the 6
   RF-extended/typed-getter routes under the unversioned `/api/knowledge/` prefix (`search`, `fetch/{id}`,
   `source/{id}`, `assertion/{id}`, `report/{id}`, `run/{id}`) that map onto `rf_search`/`rf_fetch`/`rf_*_get`
   1:1 (`include_receipt=True` always, matching what `registry.py`'s rf_* tools already do).
2. **CLI subcommand names (`search fetch source-get assertion-get report-get run-get`) are the RF-extended tool
   set with the `rf_` prefix dropped** -- confirmed by `KnowledgeAccessContext.__post_init__`'s hard validation
   that `tool` must be a literal member of `knowledge_access.TOOL_NAMES` (raises `KnowledgeRequestError
   ("unknown_tool")` otherwise) -- so whatever a transport calls internally, the `tool=` string passed into
   `resolve_context()` must be one of the 8 frozen names, which is what makes the CLI-vs-API tool-name mapping
   unambiguous once you trace it through. CLI never exposes the frozen core `search`/`fetch` tool names at all
   (no CLI equivalent of `/api/knowledge/v1/...`) -- there's no CLI-side "resource URL" concept requiring the exact
   core route, so only the API needed it.
3. **CLI identity stays `identity=None` (local trust) always; API resolves `request.state.identity`.** Confirmed
   by reading `knowledge_search_request.schema.yaml`'s header, which literally says the CLI+API "resolve and
   enforce an explicit workspace/identity exactly like existing RF read services" -- BUT no `rf` CLI command in
   this repo has EVER built a real `AuthIdentity` for a read (grepped `cli_commands.py` for `AuthIdentity(`/
   `identity=` -- zero hits outside two unrelated `workspace_id=` params). Building a net-new CLI identity
   mechanism (env vars / `foundry.mcp.principal`-style config, mirroring `search_router.mcp_launcher`'s launch
   principal) was judged out of scope for "CLI + GET-only API" wiring and would be genuinely new transport logic,
   not just parsing/rendering -- flagged here rather than silently invented. If a future phase needs CLI-side
   identity, `search_router.mcp_launcher.resolve_launch_principal` is the precedent pattern to copy.
4. **`_bootstrap_projectors` is reimplemented BY VALUE in three places now** (`knowledge_mcp/registry.py`,
   `cli/commands/knowledge.py`, `api/routers/knowledge.py`) -- 5 lines each, not factored into a shared helper on
   `knowledge_access.py` itself, to avoid touching that already-committed P3 file per this task's explicit
   instruction ("reuse the committed P3 service... add NO transport-local logic"). The projector registry is a
   process-global dict; every fresh CLI invocation AND every `rf serve` request handler re-registers all five
   projectors (cheap, idempotent dict writes) since skipping this makes every kind resolve through the P2
   skeleton's "no projector registered" exit condition (empty/denied for everything) -- verified this live via a
   smoke workspace before trusting it.
5. **A bad `--sensitivity-threshold`/`?sensitivity_threshold=` value raises `export_service.ExportError`, NOT
   `knowledge_access.KnowledgeAccessError`** -- `resolve_context()` calls `resolve_threshold()` before ever
   constructing `KnowledgeAccessContext`, so a transport's denial-catching `except ka.KnowledgeAccessError` around
   the SERVICE CALL never sees this; it must be caught separately (broader `RFError`) around the CONTEXT
   RESOLUTION step specifically, or it escapes as an unhandled 500 (API) / raw traceback (CLI). Both new
   `_context()` helpers catch `RFError` there and map to HTTP 400 / CLI exit 2 respectively -- confirmed live via
   `rf knowledge search q --sensitivity-threshold bogus` and the FastAPI TestClient equivalent.
6. **Known, deferred, EXPECTED test regression:** `tests/test_openapi_seam.py::
   test_committed_openapi_json_matches_live_app` now FAILS (confirmed via `git stash -u` that it passes on a true
   clean baseline and fails only once `api/app.py` registers the new router) -- `api/openapi.json` has not been
   regenerated for the 8 new routes, which is explicitly KMCP-5.3's job ("URL/OpenAPI/parity seam"), not this
   task's. Whoever runs KMCP-5.3 should expect and close this specific failure, not chase it as a new bug.
   Everything else in the full suite that fails is PRE-EXISTING (confirmed on the same clean-baseline stash: 10
   unrelated failures in `test_serve_api.py`/`test_assertion_rollout.py`/`test_report_anchors.py`/pediatric-CDS
   verification tests -- don't re-diagnose these, they predate this change).
7. **`from research_foundry.api.app import app` (a literal command in some task briefs) will always fail** --
   `api/app.py` only exports the `create_app(config)` factory, never a module-level `app` instance (unlike a
   typical `uvicorn module:app` layout). The working smoke-test shape is
   `create_app(FoundryConfig.load())` or `create_app(FoundryConfig.load())` inside a `FastAPI TestClient`.

See [[project_knowledge_mcp_p4b_rf_tools_inventory]] and [[project_knowledge_mcp_p4_stdio_process]] for the P4
transport's own equivalent findings this phase mirrors by value.
