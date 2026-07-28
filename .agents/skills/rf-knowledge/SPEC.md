---
schema_version: 2
doc_type: skill_spec
skill_name: rf-knowledge
skill_version: 1.0.0
status: stable
created: 2026-07-28
updated: 2026-07-28
owner: "Nick Miethe"
source_docs:
  - .Codex/skills/rf-knowledge/SKILL.md
  - .Codex/skills/rf-knowledge/references/tool-reference.md
  - .Codex/skills/rf-knowledge/references/gotchas.md
  - docs/user/knowledge-mcp.md
  - docs/dev/architecture/knowledge-mcp.md
related_skills: [research-foundry, research-foundry-swarm, meatywiki]
affects_commands: []
---

<!-- Convention reference: .Codex/specs/artifact-structures/skill-spec-convention.md -->

# rf-knowledge — Skill Specification

> **Reading this file**: This is the versioned capability contract for the `rf-knowledge` skill.
> For invocation-time routing and command sequences, see `SKILL.md` in this same directory.

---

## 1. Purpose & Scope

**Mission**: Give an agent bounded, read-only access to what Research Foundry already governs —
sources, assertions, report drafts / finals, and runs — through one shared, policy-first service
exposed as an MCP stdio process, the `rf knowledge` CLI, and a GET-only HTTP API.

This skill is the **recall router**. It is the complement to the `research-foundry` skill, which
owns the acquisition pipeline (`rf search` / `rf fetch` — Search Router — plus extraction,
claim-mapping, synthesis, and verification). Load `research-foundry` to acquire new evidence;
load this skill to see what the corpus already holds without writing, spending, or hitting a
paid provider.

**In scope**:

- Selecting between frozen core (`search`, `fetch`) and RF-extended (`rf_search`, `rf_fetch`,
  four typed getters) tool families.
- Selecting a transport — stdio MCP, `rf knowledge` CLI, or GET HTTP API — for a given task.
- Interpreting responses correctly: paging, `content_is_untrusted`, `original_source_url`,
  loopback-only `url`, opaque `rfk:v1:<kind>:<opaque>` ids.
- Recognizing the four kinds of denial that all collapse to one generic error, and the two
  distinct scenarios (zero-match vs full deny) that share the empty-results shape.
- Enforcing the claim-ledger bridge: recall never enters the ledger by being read; citable
  material must go through the acquisition pipeline.

**Out of scope**:

- Acquiring new sources from the web — owned by the `research-foundry` skill (`rf search` /
  `rf fetch`).
- Running the deterministic tail (`rf extract` → `rf claim-map` → `rf synthesize` → `rf verify`
  → `rf bundle` → `rf writeback`) — owned by `research-foundry` / `research-foundry-swarm`.
- Wiki authoring / compilation / publishing — owned by `meatywiki` / `meatywiki-author` /
  `meatywiki-suite`.
- Provider credentials, cost accounting, and the Search Router. The Knowledge MCP holds no
  provider credentials and never imports the Search Router or Operator registries.

---

## 2. Capability Coverage

| Intent | Workflow / Section | Canonical Doc |
|--------|-------------------|---------------|
| Recall what the corpus already holds (any kind) | `SKILL.md` §Decision Tree / §Workflow Recipes | `references/tool-reference.md` |
| Narrow recall to a specific kind (source / run / report) | `SKILL.md` §Workflow Recipes | `references/tool-reference.md` |
| Fetch a known opaque `rfk:v1:...` id (kind unknown) | `SKILL.md` §Workflow Recipes | `references/tool-reference.md` |
| Fetch a known id with a typed guardrail (source / report / run) | `SKILL.md` §Workflow Recipes | `references/tool-reference.md` |
| Fetch an assertion (v1 boundary) | `SKILL.md` §Workflow Recipes; gotcha 1 | `references/gotchas.md` |
| Page through a long document body | `SKILL.md` §Workflow Recipes; `references/tool-reference.md` §Paging | `references/tool-reference.md` |
| Emulate a frozen-schema client (`search`, `fetch`) | `SKILL.md` §Command Map | `references/tool-reference.md` |
| Choose the right transport for a task | `SKILL.md` §Command Map; `references/tool-reference.md` §Transport ↔ route parity | `references/tool-reference.md` |
| Install the process correctly (avoid `KMCP-F1`) | `SKILL.md` §Command Map; §Deferred / Do Not Say | `references/gotchas.md` gotcha 4 |
| Handle the seven gotchas (assertion deny, empty ≠ absent, generic denials, install gap, loopback urls, untrusted text, rights-mint rule) | `references/gotchas.md` | `references/gotchas.md` |
| Uphold the claim-ledger bridge (recall ≠ evidence) | `SKILL.md` §Guardrails; `references/gotchas.md` § "The claim-ledger bridge" | `references/gotchas.md` |
| Refuse remote / OpenAI-compatibility claims | `SKILL.md` §Deferred / Do Not Say | `SKILL.md` §Deferred / Do Not Say |

---

## 3. Invariants & Constraints

1. **Read-only across every transport.** No cache/index rebuild, no database creation, no run
   or source creation, no audit or telemetry write, no writeback. This holds for stdio MCP, the
   `rf knowledge` CLI, and the GET-only HTTP API without exception.
   _Source_: `SKILL.md` §Guardrails; `references/tool-reference.md`.

2. **Local / loopback only.** URLs in responses are strictly
   `http(s)://(127.0.0.1|localhost|[::1])[:port]/api/knowledge/v1/fetch/<percent-encoded-id>`.
   They are route-backed, explicitly non-canonical, unreachable by remote clients, and never a
   citation.
   _Source_: `references/gotchas.md` gotcha 5.

3. **Schema-aligned only.** There is NO OpenAI/ChatGPT (or other hosted-connector) compatibility
   claim in v1, and none may be inferred from the fact that the request/response shapes match
   that pattern. Making a remote claim requires four deferred design specs to be independently
   promoted, a reachable canonical HTTPS endpoint, and a named security sign-off.
   _Source_: `SKILL.md` §Deferred / Do Not Say.

4. **Stdio only for the MCP transport, enforced in code.** Streamable HTTP, SSE, OAuth, and any
   non-loopback listener are refused **in code** (`_StdioOnlyFastMCP`), not by convention.
   _Source_: `SKILL.md` §Guardrails.

5. **No provider credentials, no Search Router / Operator dependency.** The Knowledge MCP is a
   separate process / registry that never imports or calls a Search Router or Operator tool,
   and holds no provider credentials. It cannot mint a source card, cannot spend money, and
   cannot reach the outside network.
   _Source_: `SKILL.md` §Guardrails.

6. **Denial is generic and identical.** Malformed id, missing id, hidden id, cross-workspace id,
   rights-denied id, stale projection, and wrong-kind id (typed getter) all collapse to the
   same detail-free response on every transport. Never infer *why* an id was denied, and never
   report a guessed reason to the user.
   _Source_: `references/gotchas.md` gotcha 3.

7. **Empty results never mean "absent".** A zero-match search and a fully-denied search return
   the identical `{"results": [], "next_cursor": null, "truncated": false}` and exit 0. The
   correct phrasing is "not retrievable to me here", never "does not exist".
   _Source_: `references/gotchas.md` gotcha 2.

8. **Knowledge MCP output is recall, not evidence.** Nothing read here is a source card, a
   claim, or an assertion, and it never enters the claim ledger by being read. To make anything
   citable, it must go through the acquisition pipeline (`rf ingest` / `rf fetch` / `rf search`
   → `rf extract` → `rf claim-map` → ledger → `rf verify`). Reading a rights field is not
   granting one — the `no_agent_cleared_rights_value` guard rule holds.
   _Source_: `references/gotchas.md` § "The claim-ledger bridge"; `references/gotchas.md` gotcha 7.

---

## 4. Enhancement Backlog

- **[BL-1] Remote / hosted transport.**
  _Status_: deferred.
  _Rationale_: Requires four deferred design specs to be independently promoted, a reachable
  canonical HTTPS endpoint, and a named security sign-off. v1 is stdio + loopback HTTP only.

- **[BL-2] OpenAI / hosted-connector compatibility claim.**
  _Status_: deferred.
  _Rationale_: Depends on BL-1. Schema alignment does not confer compatibility while the
  transport is loopback-only.

- **[BL-3] `rf_assertion_get` parity over stdio / CLI.**
  _Status_: expected v1 boundary.
  _Rationale_: stdio and CLI run under local trust with no login of their own; every assertion
  read requires a real workspace-bearing identity. HTTP with real auth is the intended path.
  Revisit only if a portable identity contract lands on stdio.

- **[BL-4] Fix `KMCP-F1` — `mcp` extra self-sufficiency.**
  _Status_: known gap, unfixed.
  _Rationale_: The `mcp` extra alone fails with a raw `ModuleNotFoundError: fastapi`. The
  governed read service shares a workspace-isolation helper with the HTTP API package. Fix
  requires either splitting that helper out or making it optional. Documented workaround:
  `uv sync --extra mcp --extra serve`.

- **[BL-5] CLI parity for frozen core `search` / `fetch`.**
  _Status_: deferred by design.
  _Rationale_: The CLI is the automation surface; the frozen core is a compatibility shape for
  hosted-schema clients. Exposing frozen core on the CLI would blur that distinction and give
  agents a worse tool than `rf knowledge search` (no snippets, no paging, no `--kind`). Revisit
  only if a real client-emulation use case appears.

---

## 5. Changelog

### v1.0.0 — 2026-07-28

- Initial SPEC.md authored and published as `stable`.
- Structural remediation of an already-shipped SKILL.md against
  `.Codex/skills/_meta/skill-authoring-guide.md`: added `version` / `app_version` / `updated` /
  `spec` frontmatter; folded `description`; added explicit `Triggers`; added mandatory `When
  NOT To Use` section (previously frontmatter-only) and mandatory `Deferred / Do Not Say`
  section (six entries); restructured to router shape (Overview → naming collision → Decision
  Tree → Command Map → Recipes → Guardrails → When NOT → Deferred → References Pointer Table →
  Contract Pointer → Key References); moved DTO detail to `references/tool-reference.md`;
  moved gotchas + claim-ledger bridge to `references/gotchas.md`; converted `Key References` to
  absolute paths.
- Content unchanged in meaning: the naming-collision table stays in SKILL.md as the load-bearing
  routing content; the eight tools, three transports, seven gotchas, and claim-ledger bridge
  are preserved verbatim in intent across SKILL.md and `references/`.
- Capability coverage: 12 intents mapped across SKILL.md sections and reference files.
- Invariants: 8 numbered, testable.
- Enhancement Backlog: 5 entries (BL-1 through BL-5).
- Related skills: `research-foundry`, `research-foundry-swarm`, `meatywiki`.

---

## 6. Integration Points

| Agent / Command | Invocation Pattern | Notes |
|-----------------|--------------------|-------|
| `rf_knowledge_lookup` subagent | Delegated by an orchestrator that needs to keep recall out of its own context | Answers a bounded question against the governed RF corpus; returns an answer + opaque ids and never writes, acquires, or mints evidence. Definition: `.Codex/agents/research/rf_knowledge_lookup.md`. |
| `research-foundry` skill | Co-loaded when an orient-then-acquire loop is likely — recall via `rf-knowledge`, acquire via `research-foundry` (`rf search` / `rf fetch`), then run the pipeline. | Enforces the claim-ledger bridge across the two skills. |
| Any agent running inside an MCP-aware client | `.mcp.json` entry: `{"mcpServers": {"rf-knowledge-mcp": {"type": "stdio", "command": "rf-knowledge-mcp"}}}` | Requires `uv sync --extra mcp --extra serve` on the host. |
| Any agent with the `rf` CLI on PATH | Invokes `rf knowledge search` / `fetch` / `source-get` / `assertion-get` / `report-get` / `run-get` directly | Automation surface; JSON on stdout. Exposes only the six RF-extended tools — frozen core has no CLI parity. |
| A caller against a running `rf serve` | GET `/api/knowledge/...` with real auth wired | The only transport on which `rf_assertion_get` can actually resolve. |

---

## 7. Success Signals

- Agents pick `rf knowledge` for recall and `rf search` / `rf fetch` for acquisition, and never
  confuse the two — the naming-collision table settles a live footgun.
- No agent-authored artifact carries a Knowledge-MCP loopback URL as a citation.
- No agent-authored artifact carries a rights-clearance value (`CLEARED_*`, `counsel_approved`,
  `attested`) sourced from a Knowledge MCP read.
- Empty search responses are described as "not retrievable to me here", never as "does not
  exist in the corpus".
- Denials are reported as "denied", not with a guessed reason (typo / cross-workspace / rights).
- Installation instructions specify `uv sync --extra mcp --extra serve`; nobody documents the
  `mcp` extra alone as sufficient while `KMCP-F1` remains open.
- No agent-authored text describes the Knowledge MCP as OpenAI-compatible, remotely reachable,
  or exposed over anything other than stdio MCP / loopback HTTP.

---

## 8. Version-Bump Triggers

The following changes require a `version` **major** bump (and a corresponding entry in
`CHANGELOG.md`):

- Routing table changes — a tool added or removed, a transport added or removed, or the
  frozen-vs-RF-extended split shifting.
- Any change to the `When NOT To Use` scope exclusions.
- Any change to the `Deferred / Do Not Say` table (adding, removing, or reclassifying an
  entry — including the resolution of `KMCP-F1` or the promotion of the remote / OpenAI-
  compatibility claim).
- Any change to the invariants above (§3).

Prose updates, recipe additions, reference-link fixes, and clarifications that do not shift
routing take a `version` **minor** bump. Every SKILL.md edit refreshes `app_version` and
`updated`.
