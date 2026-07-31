# M2 pre-gate review — Terra

Scope reviewed: M2 `a759aa6` ("feat(operator-mcp): M2 wave 1"). Focused M2 suite passed: `47 passed` via
`./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py tests/integration/test_operator_mcp_writeback_preview.py tests/test_operator_mcp_offline_import.py tests/unit/test_operator_mcp_adapter_writeback_preview.py tests/unit/test_operator_mcp_packaging.py -q`.

## TERRA-1

Severity: BLOCKING

File: `src/research_foundry/operator_mcp/server.py:478-488`, `src/research_foundry/services/operator_operation_service.py:1250-1256`

Defect: A confirmation minted by the MCP preflight tool is never persisted, so no normal MCP preflight-to-execute flow can consume it.

Evidence: `_preflight_tool` calls `mint_confirmation(...)` and returns `issued.record`, but never calls `OperatorOperationService.record_confirmation`.  The only consume path first queries `confirmations` by `confirmation_id` and returns `confirmation_missing` when no row exists.  The preview integration helper masks this by manually doing `op_service.record_confirmation(issued.record)` before direct adapter invocation (`tests/integration/test_operator_mcp_writeback_preview.py:139-151`).

Suggested fix: Define the intended durable handoff, then persist the issued confirmation atomically before returning it (with a governed persistence-failure envelope), or change the approved protocol so execute can safely consume the presented record; update D5 and its zero-effect proof accordingly.

## TERRA-2

Severity: HIGH

File: `src/research_foundry/operator_mcp/server.py:466-476`, `src/research_foundry/services/operator_mcp_policy.py:1491-1498`

Defect: `operation.preflight` can never mint a usable `writeback.preview` confirmation because it drops the caller's writeback target list when constructing `PolicyContext`.

Evidence: The preflight context passes `targets=tuple(target_refs)` but no `writeback_targets`; the dataclass default is therefore empty.  Policy explicitly returns `preflight_failed` for `writeback.preview` when `ctx.writeback_targets` is empty.  Direct preview tests build a context with `writeback_targets=normalized` themselves (`tests/integration/test_operator_mcp_writeback_preview.py:128-141`), so they do not cover the registered MCP route.

Suggested fix: Specify a closed, canonical source for preview target names in preflight, validate and pass it as `writeback_targets`, and add a real MCP preflight-to-preview test.

## TERRA-3

Severity: BLOCKING

File: `src/research_foundry/operator_mcp/server.py:398-405`, `src/research_foundry/services/operator_mcp_adapters/run_plan.py:206-251`

Defect: Caller-controlled `run.plan.retrieval_limits` reaches `planning.plan_run` without being included in the adapter's canonical payload, so a valid confirmation can be reused with changed retrieval limits.

Evidence: The generic handler expands `input_payload` into the adapter.  `run_plan.invoke` accepts `retrieval_limits` and forwards it to `planning.plan_run` at line 250, but the `input_payload` used to construct `PolicyContext` lists `retrieval_policy` and omits `retrieval_limits` at lines 206-221.  Thus preflighting without that key and executing with it produces the same execution digest.  Leg B's D8 table treats all semantic keys as one `input_payload` row rather than enumerating this parameter (`m2-leg-b-completion.md:115-121`).

Suggested fix: Include `retrieval_limits` in the canonical payload (or resolve it server-side) and replace generic D8 coverage with per-operation parameter/binding tests.

## TERRA-4

Severity: HIGH

File: `src/research_foundry/operator_mcp/server.py:387-405`, `src/research_foundry/services/operator_mcp_adapters/writeback_preview.py:158-170,279-290`, `src/research_foundry/services/operator_mcp_policy.py:1703-1705,1911-1932`

Defect: The generic dispatcher exposes test-only adapter DI parameters such as `now` through `input_payload`, allowing an in-process caller to supply the clock used for confirmation expiry.

Evidence: The handler supplies no explicit `now` and expands all `input_payload` keys; `WritebackPreviewAdapter.invoke(**kwargs)` forwards them to `invoke_preview`, whose `now` then reaches `base.run_pipeline` and `verify_confirmation`.  Policy explicitly says P2/P5 must never thread a caller/request timestamp through this seam.  The D8 note says `now` is test-only and that server-reserved keys including `now` raise, but only explicitly supplied keys such as `paths` collide; `now` does not (`m2-leg-b-completion.md:117-121`, `m2-leg-a-completion.md:229-232`).

Suggested fix: Derive an allowlist from each real adapter signature and reject all DI/test-only names at the server boundary; do not forward arbitrary nested keys.

## TERRA-5

Severity: BLOCKING

File: `src/research_foundry/operator_mcp/server.py:260-288`

Defect: The stdio-only guard is bypassable by invoking unbound `FastMCP` base transport methods on the guarded instance.

Evidence: The subclass blocks only normal virtual dispatch (`server.sse_app()` and `server.streamable_http_app()`), but the installed base class remains callable.  Read-only reproduction: `FastMCP.sse_app(build_server())` and `FastMCP.streamable_http_app(build_server())` each returned a `Starlette` app.  The tests exercise only overridden-instance methods (`tests/integration/test_operator_mcp_server.py:186-205`), not this base-class route.

Suggested fix: Do not expose a subclass of a network-capable public server object as the security boundary; use an API/object design that cannot be recast to the base transport implementation, and test base-method/unbound-method calls.

## TERRA-6

Severity: MED

File: `src/research_foundry/operator_mcp/server.py:224-240,298-315`

Defect: Payload size/depth handling happens after the SDK has materialized arguments and can itself escape the transport envelope on deeply nested data.

Evidence: `call_tool` receives a `dict`, then `_check_transport_payload_size` re-serializes it; it therefore cannot reject an oversized raw stdio frame before deserialization.  That size call is outside the subsequent broad exception boundary and catches only `TypeError`/`ValueError`; directly passing a 100,000-level nested mapping to `_check_transport_payload_size` raised `RecursionError: Stack overflow ...` rather than producing `internal_error`.  The oversize test only calls `server.call_tool` with a prebuilt dict (`tests/integration/test_operator_mcp_server.py:225-229`).

Suggested fix: Enforce a byte/frame limit at the earliest SDK-supported stdio boundary, put all argument inspection inside a safe mapper, and add an explicit depth/structure cap.

## TERRA-7

Severity: MED

File: `src/research_foundry/services/operator_mcp_adapters/writeback_preview.py:198-213,239-245`, `src/research_foundry/services/writeback.py:1280-1397`

Defect: `writeback.preview` has no target-count or per-name bound, so a bounded 64-KiB request can expand to a much larger result and receipt computation.

Evidence: The adapter deduplicates arbitrary caller strings and policy limits only total input bytes, not `writeback_targets` cardinality.  `preview_writeback` creates one result per unique target, including arbitrary unsupported strings, and the adapter concatenates every `target=status` pair to hash the effect.  Thousands of short unsupported targets can therefore produce a several-hundred-KiB response from one accepted request, contrary to D7's bounded-result requirement.

Suggested fix: Apply an explicit max count and item-length/enum bound before normalization, and cap the returned target list/effect summary.

## TERRA-8

Severity: MED

File: `src/research_foundry/services/writeback.py:1265,1300-1387`

Defect: Preview artifacts are scoped only to a run and fixed target filename, so one operation can overwrite or leave stale content at the staged path returned for another operation.

Evidence: Every invocation stages under `<run>/staging/writeback_preview/` and writes fixed names such as `meatywiki.md`, `skillmeat.md`, and `<target>.json`; there is no operation or content-digest namespace and no locking/version check.  The completion note acknowledges this overwrite behavior (`m2-leg-a-completion.md:64-83`).  No registered tool reads the staging files today, so this is preview-integrity/cross-operation confusion rather than a demonstrated live-writeback escalation.

Suggested fix: Namespace staged content by operation ID or immutable candidate digest and return only that operation-specific reference; define cleanup/replay semantics.

TERRA VERDICT: 8 findings, 3 blocking

Checked clean: H2 execution-time workspace and canonical binding are re-derived by each adapter, so preflight's optimistic workspace guess cannot grant cross-workspace execution; H3 `dest`/`stage_only` are not MCP caller-reachable and all live call sites use defaults; H4 has no registered tool that retrieves staged output for a second caller (TERRA-8 is the separate cross-operation integrity defect); H5 normal error envelopes redact raw exception/path detail and target `not_found` remains one denial shape; H6 reports root-level `additionalProperties: false` on all 14 tools, but that does not close TERRA-3/TERRA-4's nested generic dispatcher; H8 `evidence_bundle` re-use of `run_id` does not have a target-kind-specific RBAC bypass; H9 preview calls read-only `notebook_for_run`, not `resolve_notebook`, so it does not write the correlation registry; preview call graph did not construct an integration client or reach a network primitive.
