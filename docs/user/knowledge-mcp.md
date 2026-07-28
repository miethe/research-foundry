---
title: Research Foundry Knowledge MCP
description: "How to run the local, read-only rf-knowledge-mcp stdio process, the rf knowledge CLI, and the GET /api/knowledge routes — and what they will not do in v1."
audience: [users, developers]
tags: [mcp, knowledge-access, read-only, stdio, cli, api]
created: 2026-07-27
updated: 2026-07-27
category: user-documentation
doc_type: user_guide
schema_version: 1
status: active
feature_slug: research-foundry-knowledge-mcp
related_documents:
  - docs/dev/architecture/knowledge-mcp.md
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - .claude/findings/research-foundry-knowledge-mcp-findings.md
---

# Research Foundry Knowledge MCP

The Knowledge MCP gives an agent or script bounded, read-only access to four things Research
Foundry already governs — **sources**, **assertions**, **reports**, and **runs** — through one
shared, policy-first service. It never writes, rebuilds, imports, or calls out to a paid
provider. It is exposed three ways: an MCP stdio process, the `rf knowledge` CLI, and a
GET-only HTTP API. All three call the same service and return the same shapes.

**Read this first — the v1 boundary:**

> The Knowledge MCP is **local, stdio-only, and schema-aligned only**. It implements the same
> `search(query)`/`fetch(id)` field shapes a hosted MCP connector (for example, an
> OpenAI/ChatGPT-style connector) expects, so a client written against that pattern will parse
> its responses correctly if you wire it up yourself — but that is not the same thing as being
> **OpenAI/ChatGPT compatible** out of the box. There is **no remote transport, no HTTPS
> endpoint, and no hosted-connector registration in v1.** Every URL it returns is loopback-only
> (`127.0.0.1`/`localhost`/`[::1]`) and is explicitly **not** a durable public citation. A
> hosted client cannot reach it, and the process refuses to start any non-stdio transport
> (Streamable HTTP, SSE, OAuth) even if you ask it to.

## What it can read

| Kind | What you get back | Notes |
|---|---|---|
| `source` | Title, an `http(s)` locator (when one exists), trust label, permitted evidence snippets | Never a raw filesystem path |
| `assertion` | Edition/passage/version/lifecycle/evaluation/rights fields | Denies by default through the stdio MCP process and the CLI — see [Known limitations](#known-limitations) |
| `report_draft` / `report_final` | Title, status, audience, block/link counts, rendered body text | The same underlying draft, split by lifecycle status — a `published`/`archived` draft is `report_final`, everything else is `report_draft` |
| `run` | Status, sensitivity, claim counts, verification/governance verdicts, category, tags | A bounded summary, not the run's own report markdown |

Every result is bounded (result counts, snippet length, document byte size) and every returned
document text is marked untrusted — treat it as data, not as instructions.

## Running `rf-knowledge-mcp` (stdio)

Install the `mcp` extra. In practice you also need the `serve` extra installed, because the
governed read service shares a workspace-isolation helper with the HTTP API package (see
[Known limitations](#known-limitations)):

```bash
uv sync --extra mcp --extra serve
# or
pip install 'research-foundry[mcp,serve]'
```

Then run the packaged entry point directly, or register it with an MCP-aware client (e.g.
Claude Code's `.mcp.json`) as a `stdio` server:

```bash
rf-knowledge-mcp
```

```json
{
  "mcpServers": {
    "rf-knowledge-mcp": {
      "type": "stdio",
      "command": "rf-knowledge-mcp"
    }
  }
}
```

If the `mcp` SDK is not installed, the process fails immediately with a clear message naming
the extra to install — it never silently degrades. It always runs over stdio; there is no flag
to make it listen on a network port.

**The eight tools:**

| Tool | Purpose |
|---|---|
| `search` | Frozen core search — `query` in, `{results: [{id, title, url}]}` out. At most 10 results, no snippets. |
| `fetch` | Frozen core fetch — `id` in, `{id, title, text, url, metadata?}` out. |
| `rf_search` | RF-extended search — adds `kinds` filter, `limit`/`cursor` paging, snippets, and an activity receipt. |
| `rf_fetch` | RF-extended fetch — adds cursor-based paging, typed `rf_metadata`, `original_source_url`, and a receipt. |
| `rf_source_get` | Typed fetch scoped to `source` ids only. |
| `rf_assertion_get` | Typed fetch scoped to `assertion` ids only. |
| `rf_report_get` | Typed fetch scoped to `report_draft` or `report_final` ids. |
| `rf_run_get` | Typed fetch scoped to `run` ids only. |

## Using the `rf knowledge` CLI

Every `rf-knowledge-mcp` tool except the frozen core `search`/`fetch` has a CLI subcommand
under `rf knowledge`. Output is always JSON on stdout — this surface is for automation, not
interactive browsing.

```bash
# Search across every kind (or narrow with repeatable --kind)
rf knowledge search "cbc reference range" --kind source --kind run --limit 10

# Fetch a specific id (opaque form: rfk:v1:<kind>:<opaque>)
rf knowledge fetch rfk:v1:run:rf_run_20260612_agentic_research_workflows

# Typed getters — each rejects an id of the wrong kind
rf knowledge source-get rfk:v1:source:abc123
rf knowledge report-get rfk:v1:report_final:report_9f2c
rf knowledge run-get rfk:v1:run:rf_run_20260612_agentic_research_workflows

# Page through a large document
rf knowledge fetch rfk:v1:run:rf_run_20260612_agentic_research_workflows --cursor 200000
```

A search with zero matches (denied or genuinely absent — you cannot tell which) prints
`{"results": [], "next_cursor": null, "truncated": false}` and exits `0`. A denied or missing
`fetch`/typed-getter id prints the same generic message every time and exits `1` — the CLI
never tells you *why* an id was denied.

`rf knowledge` always resolves **local trust** (no login concept of its own), exactly like the
stdio MCP process — see [Known limitations](#known-limitations) for what that means for
`assertion-get`.

## Using the GET-only HTTP API

If you run `rf serve`, the same service is available over HTTP, read-only:

```bash
rf serve   # loopback, http://127.0.0.1:7432

curl "http://127.0.0.1:7432/api/knowledge/v1/search?query=cbc+reference+range"
curl "http://127.0.0.1:7432/api/knowledge/search?query=cbc&kind=source&kind=run&limit=10"
curl "http://127.0.0.1:7432/api/knowledge/v1/fetch/rfk%3Av1%3Asource%3Aabc123"
curl "http://127.0.0.1:7432/api/knowledge/source/rfk%3Av1%3Asource%3Aabc123"
curl "http://127.0.0.1:7432/api/knowledge/run/rfk%3Av1%3Arun%3Arf_run_20260612_agentic_research_workflows"
```

| Route | Tool parity |
|---|---|
| `GET /api/knowledge/v1/search` | `search` (frozen core) |
| `GET /api/knowledge/v1/fetch/{id}` | `fetch` (frozen core; the literal route every `url` field points at) |
| `GET /api/knowledge/search` | `rf_search` |
| `GET /api/knowledge/fetch/{id}` | `rf_fetch` |
| `GET /api/knowledge/source/{id}` | `rf_source_get` |
| `GET /api/knowledge/assertion/{id}` | `rf_assertion_get` |
| `GET /api/knowledge/report/{id}` | `rf_report_get` |
| `GET /api/knowledge/run/{id}` | `rf_run_get` |

There is no POST, PUT, PATCH, or DELETE route under `/api/knowledge/`. A denied or unknown id
returns `404` with the same generic message every other transport uses — never a distinguishing
detail. Unlike the stdio process and the CLI, this transport resolves a real caller identity
from your configured auth provider (when one is configured), so `rf_assertion_get` can succeed
here even when it cannot through stdio or the CLI (see below).

## Known limitations

- **`assertion-get` denies by default outside the HTTP API.** The stdio MCP process and the
  `rf knowledge` CLI always run under "local trust" (no separate login of their own).
  Every assertion read requires a real, workspace-bearing identity — a stricter rule than every
  other kind — so `rf_assertion_get` denies generically for every id through those two
  transports, and `search`/`rf_search` never surface an `assertion`-kind result through them
  either. This is expected v1 behavior. It can succeed through the HTTP API when a real
  identity is resolved from configured auth middleware.
- **Installing only the `mcp` extra is not enough today.** `rf-knowledge-mcp` also needs the
  `serve` extra (`fastapi`/`uvicorn`) installed to import successfully, because the governed
  read service shares a workspace-isolation helper with the HTTP API package. If you install
  only `pip install 'research-foundry[mcp]'`, the process fails at startup with a raw
  `ModuleNotFoundError: fastapi` rather than a clear message about the `mcp` extra. Install
  `uv sync --extra mcp --extra serve` (or the full dev environment) instead. See
  [`.claude/findings/research-foundry-knowledge-mcp-findings.md`](../../.claude/findings/research-foundry-knowledge-mcp-findings.md)
  (KMCP-F1) for the full root-cause writeup — this does not weaken the read-only/no-provider
  guarantee, it is an installability gap.
- **Every URL is loopback-only and local to your machine.** Do not treat a `url` field as a
  durable public citation, and do not expect a remote/hosted MCP client to reach it.

## Not remote-compatible in v1

There is no Streamable HTTP transport, no SSE transport, no OAuth, and no non-loopback listener
— the process refuses to start any of those even if asked (`_StdioOnlyFastMCP`, enforced in
code, not only by convention). Consequently there is **no OpenAI/ChatGPT (or other hosted
connector) compatibility claim for the local process**, and none should be inferred from the
fact that its request/response shapes match that pattern. Making that claim for a *remote*
profile requires four separate design specs to be promoted first (remote transport, canonical
resource URLs, remote cache isolation, and shared indexing), a reachable canonical HTTPS
endpoint, and a named security sign-off — see
[`docs/dev/architecture/knowledge-mcp.md`](../dev/architecture/knowledge-mcp.md#6-local-not-remote-v1-boundary)
for the full gate list.

## See also

- [Knowledge MCP architecture](../dev/architecture/knowledge-mcp.md) — layers, DTOs, invariants.
- [Serving Runs Live (Loopback API)](../../README.md#serving-runs-live-loopback-api) — the
  `rf serve` process the HTTP routes above run inside.
