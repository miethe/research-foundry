---
schema_version: 2
doc_type: design_spec
title: "Browser Research Capture Extension"
description: "Shape a least-privilege browser capture path that stages provenance-rich research candidates for explicit promotion into Research Foundry."
status: draft
maturity: shaping
created: 2026-07-18
updated: 2026-07-18
feature_slug: browser-research-capture-extension
problem_statement: "Browser research loses fidelity and provenance when operators copy fragments manually, while direct automated ingestion would create unacceptable access, rights, and trust-boundary risks."
open_questions:
  - "OQ-BRC-01: Which Chromium browsers and operating systems are required for the first supported release?"
  - "OQ-BRC-02: Which page-fidelity mode is the default: selection-only, reader extraction, or a locator-only capture?"
  - "OQ-BRC-03: May authenticated or paywalled page text ever leave the browser, and under which attributable rights decision?"
  - "OQ-BRC-04: How are native-host installation, host identity, and target Research Foundry instance trust established?"
  - "OQ-BRC-05: Which minimal fields may be retained in the extension queue while the native host is unavailable?"
  - "OQ-BRC-06: Does v1 support PDF-viewer selections, and how is the source edition bound when browser PDF text differs from downloaded bytes?"
  - "OQ-BRC-07: What operator action promotes a selected third-party assertion candidate after RF creates an immutable edition and passage?"
  - "OQ-BRC-08: Which target-selection state is safe to remember between captures without risking workspace misrouting?"
explored_alternatives:
  - "Direct loopback HTTP ingestion: simpler transport, but expands origin, CSRF, authentication, port-discovery, and LAN-exposure risk; defer until native messaging proves insufficient."
  - "Silent background capture: rejected because it violates explicit-gesture, least-privilege, rights, and sensitivity boundaries."
  - "Clipboard-only workflow: safe and portable, but loses structured provenance, target selection, receipts, and idempotency."
  - "Browser automation as the primary capture path: useful for testing, but too broad and opaque for routine operator capture."
  - "Immediate assertion-ledger writes: rejected because browser text is untrusted candidate material until immutable edition and passage creation succeeds."
prd_ref: null
plan_ref: null
related_documents:
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
owner: nick
contributors: []
priority: medium
risk_level: high
category: product-planning
tags: [design-spec, browser-extension, capture, provenance, access-control, mv3]
commit_refs: []
pr_refs: []
files_affected: []
---

# Browser Research Capture Extension

## 1. Decision boundary

Shape a Chromium Manifest V3 extension that captures research only after an
explicit operator gesture, uses `activeTab` rather than persistent browsing
permissions, and sends a versioned capture envelope to a local native-messaging
host. The native host stages the envelope as an untrusted candidate in a selected
Research Foundry instance. A separate, explicit promotion action may later create
source-card, edition, passage, or assertion records after policy and fidelity gates
pass.

The recommended first transport is **MV3 extension -> local native messaging**.
It avoids opening a browser-callable HTTP listener and gives the browser an
allowlisted executable boundary. A loopback API remains a deferred alternative,
not an assumed second transport.

This document is a shaping artifact. It does not authorize extension packaging,
native-host installation, browser-store publication, live authenticated capture,
or assertion-ledger writes.

## 2. Why this is additive

The extension is a capture edge, not a second research pipeline. Existing plans
remain authoritative for the capabilities they already define:

| Existing foundation | Reused responsibility | Not reopened here |
|---|---|---|
| RFUP | Machine-readable contracts, governed extraction, exact-passage hard-gating, and fail-soft evidence handling | RF verification or extraction architecture |
| Reusable Assertion Ledger | Immutable editions/passages, source-assertion fidelity, workspace confinement, reuse, and impact semantics | Registry identity, canonical grouping, or public promotion policy |
| Assertion-Ledger Activation | Reachable backfill, forward materialization, and reuse drivers | Activation implementation or flag wiring |
| Research provenance continuity child | Cross-boundary identity and provenance-event continuity | Canonical provenance identifiers |
| External report interchange child | Versioned external import/export envelopes | Report interchange format |
| Knowledge MCP child | Governed read access to RF knowledge | Browser capture mutation |
| Operator MCP child | Governed preview/approve/execute patterns | Browser-native permissions or DOM fidelity |

The extension must call the same candidate-ingest and promotion seams chosen by
those artifacts. It must not fork their schemas in extension-owned storage.

## 3. User and job

**Primary actor:** a Research Foundry operator doing intentional research in a
browser.

**Job to be done:** while viewing a useful page or selecting a relevant passage,
capture enough context to revisit and evaluate it without turning browser content
into trusted evidence prematurely or sending it to the wrong workspace.

**Expected interaction:**

1. The operator invokes the extension from the active tab or context menu.
2. The extension previews the locator, selected content, capture type, sensitivity,
   rights disposition, and target instance/workspace.
3. The operator confirms staging or cancels.
4. The native host validates and durably stages the capture envelope, or returns a
   typed denial/degraded result.
5. The extension displays the receipt state.
6. Promotion, when requested, is a separate RF action with its own preview and
   receipt.

## 4. Capture semantics

The UI and envelope must keep three content classes distinct.

| Content class | Meaning | Initial RF state | Promotion rule |
|---|---|---|---|
| Source candidate | Locator and page metadata identifying material worth evaluating | Untrusted candidate; no evidentiary authority | RF fetch/extraction and policy evaluation may create an edition and passages |
| Selected third-party assertion candidate | Verbatim text asserted by the page author or quoted source | Candidate bound to locator and selection context; not reusable | Requires immutable source edition, exact passage binding, evaluator disposition, and assertion creation |
| User annotation or paraphrase | Operator interpretation, summary, question, or note | Explicit `inference`/annotation candidate; never represented as a source quote | May inform a brief or inference record, but cannot become source-backed merely by sharing a capture packet |

The extension must never infer which class applies from prose alone. The operator
chooses the capture type in preview; the native host validates the combination and
records the choice.

### 4.1 Assertion promotion invariant

A selected third-party assertion candidate cannot become a source assertion until
Research Foundry has created or resolved:

- an immutable source edition identity tied to retrieved or owner-approved bytes;
- an exact passage selector and passage hash within that edition;
- the selected text or a documented, reviewable normalization of it;
- workspace, sensitivity, rights, and allowed-use dispositions;
- an evaluator result that does not abstain or fail closed; and
- a provenance link back to the capture packet and receipt.

If exact bytes cannot be retrieved, the capture remains `locator_only`,
`selection_unverified`, or another explicit non-reusable state. Browser-rendered
text alone does not silently satisfy edition identity.

## 5. Fidelity modes

V1 should support the smallest fidelity modes that preserve operator intent.
Each mode is explicit in the envelope.

| Mode | Captured content | Strength | Limitation |
|---|---|---|---|
| `locator_only` | Canonical/original URL, title, page metadata | Lowest rights and storage exposure | No exact-passage claim support |
| `selection` | User-selected text plus bounded surrounding context and selectors | Best default for intentional quote capture | Dynamic DOM or later page change may prevent replay |
| `reader_excerpt` | Operator-previewed readable excerpt | Useful for article context | Extraction may omit tables, captions, or qualifiers |
| `dom_snapshot` | Sanitized, bounded snapshot or digest | Stronger replay diagnostics | Highest privacy, storage, and prompt-injection exposure; not a v1 default |
| `pdf_selection` | Browser PDF selection plus page coordinates when available | Supports document research | Browser text layer may not match downloaded edition bytes |

Recommended default: `selection` when text is selected, otherwise
`locator_only`. `reader_excerpt`, `dom_snapshot`, and `pdf_selection` remain gated
until fixtures prove fidelity and rights handling.

Required fidelity metadata includes selection start/end selectors where available,
surrounding-context hashes, document language, browser-rendered text hash, and an
explicit `rendered_not_edition_bound` flag until RF resolves immutable bytes.

## 6. Capture envelope

The versioned envelope is a transport artifact, not a source card. Proposed fields:

```yaml
schema_version: browser_capture.v1
capture_packet_id: <stable UUID created once>
idempotency_key: <digest of canonical capture payload>
captured_at: <UTC timestamp>
capture_mode: selection
content_class: selected_third_party_assertion_candidate
source:
  original_locator: <redacted URL when required>
  canonical_locator: <normalized URL or null>
  title: <untrusted string>
  mime_hint: text/html
  language: en
selection:
  verbatim_text: <operator-previewed text>
  prefix: <bounded context>
  suffix: <bounded context>
  rendered_text_hash: <digest>
  rendered_not_edition_bound: true
annotation:
  text: null
  semantic_type: null
policy_intent:
  workspace_id: <explicit target>
  sensitivity_profile: personal
  rights_basis: unknown
  allowed_use: research_review_only
target:
  instance_id: <selected local RF instance>
  project_slug: <optional>
client:
  extension_version: <semver>
  browser_family: chromium
  native_host_protocol_version: <semver>
```

Sensitive values may be omitted or locally redacted before staging. Query strings,
fragments, titles, selected text, and annotations are untrusted input even when the
operator initiated the capture.

## 7. Rights, authentication, and sensitivity

### 7.1 Authenticated and paywalled pages

- The extension must not collect cookies, authorization headers, form fields,
  passwords, hidden DOM, or browser history.
- Authenticated page text is not assumed exportable merely because it is visible to
  the operator.
- Default disposition for authenticated/paywalled content is metadata plus selection
  preview with `rights_basis: unknown` and `allowed_use: research_review_only`.
- Raw text staging beyond the browser requires an attributable operator decision and
  a policy that permits the target workspace to retain it.
- Native-host or RF re-fetch must not attempt to reuse the browser session.

### 7.2 Sensitivity

- Target workspace and sensitivity profile are explicit before confirmation.
- The extension must not downgrade a previously selected sensitivity profile when a
  target changes.
- Content and locator secret scanning happens before durable promotion; obvious URL
  credentials or tokens are redacted before queue persistence where possible.
- Denial is a successful governed outcome and receives a non-content-leaking receipt.

### 7.3 Rights

The extension records operator-stated rights intent, not a legal conclusion.
Unknown, disputed, expired, or revoked rights block public promotion and external
writeback. Public rights remain governed by the RAL promotion design, not by an
extension checkbox.

## 8. Security and untrusted-content boundary

All controls in this section are future promotion requirements, not claims about
currently shipped protection. The extension/native-host capability remains absent
until implementation and canary evidence prove each requirement on the exact build.

### 8.1 Least privilege

Initial MV3 permissions should be limited to `activeTab`, `scripting`,
`contextMenus`, `storage`, and `nativeMessaging` where required. Broad host
permissions, `history`, `cookies`, `downloads`, and persistent background page
access are excluded unless a later reviewed requirement proves necessity.

### 8.2 SSRF controls

- A capture packet never authorizes a fetch merely by containing a URL.
- Accept only supported schemes; reject executable, browser-internal, data, and file
  schemes by default.
- A promoted implementation MUST call an RF fetch policy that validates schemes,
  every DNS answer, redirects, connected peers, and private/reserved/link-local/
  metadata targets before network access; this shaping spec assumes no current guard.
- A target instance cannot be selected through page-provided content or query
  parameters.
- Re-fetch is a separately logged operation with policy and network dispositions.

### 8.3 Prompt-injection controls

- Page titles, metadata, selected text, DOM fragments, and annotations remain
  untrusted data; none become agent instructions.
- The native host parses a bounded schema and never interpolates page text into shell
  commands.
- Agent-facing renderers delimit captured material and label its trust state.
- Candidate staging performs no autonomous tool call, writeback, MCP action, or
  assertion promotion based on captured instructions.

### 8.4 Native-host trust

A promoted implementation MUST use the browser's allowlisted native-messaging
manifest. The native host MUST validate the browser-supplied caller origin at process
launch/message establishment against an explicit allowlist of expected
`chrome-extension://<extension-id>` origins and the manifest `allowed_origins` before
parsing a capture envelope. Missing, malformed, page-supplied, or mismatched caller
origins fail closed; a webpage, content payload, query parameter, or claimed extension
ID inside message data can never authorize the host.

After caller-origin validation, the host MUST return its instance ID, protocol
version, repository identity, supported capture schema, and host-key fingerprint before
the extension enables confirmation. Unknown/mismatched hosts or callers fail closed,
and the denial response reveals no workspace, checkout, or target-instance details.

## 9. Target-instance and workspace selection

Multiple RF checkouts or workspaces may exist on one machine. The target picker must
show stable, host-provided identities rather than ports or folder labels scraped from
the page.

Selection order:

1. Resolve installed native host identities.
2. Choose Research Foundry instance.
3. Choose workspace visible to the authenticated local operator.
4. Optionally choose project/run association.
5. Choose sensitivity and rights intent.
6. Preview the full target path and confirm.

Remembering a default is optional and unresolved. If implemented, remember only the
stable instance/workspace identifiers; target disappearance or authorization change
forces a new selection. A queued packet retains the target chosen at capture time and
must not silently reroute to a new default.

## 10. Offline queue and idempotency

Captures must remain recoverable when the native host or selected RF instance is
temporarily unavailable.

- Create `capture_packet_id` once and preserve it through retries.
- Derive `idempotency_key` from the canonicalized payload, excluding retry counters and
  transport timestamps.
- Store queued packets in extension-local storage only when the operator opts in;
  never use synchronized browser storage.
- Apply a bounded queue size and retention period. Show both limits before capture.
- Minimize or encrypt queued sensitive text where platform support permits; otherwise
  queue metadata only and require recapture for the text.
- Retry is explicit or bounded with visible backoff. Do not spin in a background loop.
- The native host atomically records a packet before acknowledging it and returns the
  same receipt for repeated `(target_instance_id, idempotency_key)` submissions.
- Queue deletion happens only after a durable receipt is received or the operator
  explicitly discards the packet.

Conflict states include `duplicate_same_payload`, `duplicate_changed_target`,
`schema_unsupported`, and `policy_changed_since_capture`. They require typed handling,
not a generic success toast.

## 11. Provenance receipt

Every staging attempt returns a durable receipt safe to display and audit. Proposed
fields:

| Field | Purpose |
|---|---|
| `receipt_id` | Stable identity for this processing result |
| `capture_packet_id` / `idempotency_key` | Correlate retry and deduplication |
| `received_at` / `processed_at` | Transport and policy timing |
| `instance_id` / `workspace_id` / `project_slug` | Prove the selected target |
| `capture_schema_version` / `host_protocol_version` | Reproduce compatibility decisions |
| `content_class` / `capture_mode` | Preserve operator intent |
| `locator_digest` / `rendered_text_hash` | Correlate content without always echoing secrets |
| `sensitivity_disposition` / `rights_disposition` | Record policy outcome and reason code |
| `secret_scan_disposition` | Show redacted, blocked, or passed state |
| `stage_status` | `staged`, `queued`, `denied`, `degraded`, or `duplicate` |
| `candidate_refs` | Created source/selection/annotation candidate ids, if any |
| `edition_ref` / `passage_ref` / `assertion_ref` | Null until explicit promotion creates them |
| `promotion_status` | `not_requested`, `pending_review`, `promoted`, or `denied` |
| `policy_version` / `actor_ref` | Attribute the decision context |
| `reason_codes` | Machine-readable non-success explanations |

A receipt must not echo selected sensitive text by default. Receipt generation does
not imply assertion promotion, external writeback, or live-network qualification.

## 12. UX state model

| State | Operator-visible behavior | Allowed next action |
|---|---|---|
| `selecting` | Shows current tab and selected text boundary | Choose capture type or cancel |
| `target_required` | Shows no trusted target | Select instance/workspace |
| `preview` | Shows content class, target, sensitivity, rights, and retained fields | Confirm or edit |
| `sending` | Shows one in-flight packet id | Cancel transport if supported; do not duplicate |
| `queued_offline` | Shows retention and retry state | Retry, export packet, or discard |
| `staged_candidate` | Shows candidate refs and receipt | Open RF review or request promotion |
| `needs_policy_review` | Shows reason code without claiming success | Adjust only with authorized review |
| `denied` | Shows governed denial and safe receipt | Close or export receipt |
| `degraded_locator_only` | Explains that exact text was not retained/verified | Revisit or keep locator candidate |
| `promotion_pending` | Shows immutable-edition/passage prerequisites | Open RF review |
| `promoted` | Shows edition/passage/assertion refs | View provenance in RF |
| `error_recoverable` | Shows typed retry guidance | Retry once prerequisites change |

No state may display “captured as evidence” before immutable edition/passage and
evaluation requirements succeed.

## 13. Execution order and promotion gates

This order applies only after the design reaches `maturity: ready` and a child PRD or
feature contract authorizes implementation.

| Gate | Deliverable | Exit evidence |
|---|---|---|
| BRC-G0 — Threat model and boundary | Permissions, data-flow, native-host, queue, SSRF, prompt-injection, and rights threat model | Independent security review accepts the default-deny design |
| BRC-G1 — Envelope contract | Versioned capture envelope, JSON Schema, canonicalization, and fixtures | Strict validation covers source, assertion-candidate, annotation, malformed, and oversized packets |
| BRC-G2 — Fidelity and rights | Selection replay experiments and authenticated/paywalled disposition matrix | Exact-text, changed-page, dynamic-page, and denied-rights fixtures have explicit outcomes |
| BRC-G3 — Native messaging transport | Manifest allowlist, browser-supplied caller-origin validation, host discovery/identity handshake, target selection, and atomic staging | Missing/mismatched extension origin, page-claimed identity, unknown host, wrong instance/workspace, and protocol mismatch fail closed without target detail |
| BRC-G4 — Offline durability | Queue retention, retry, dedupe, conflict, and discard behavior | Repeated packet submission returns one durable result per target and idempotency key |
| BRC-G5 — Candidate staging | Source, selected assertion, and annotation candidate persistence | Candidate types remain distinguishable; ledger counts are unchanged before promotion |
| BRC-G6 — Explicit promotion | RF review path resolving edition, passage, evaluation, and assertion refs | Promotion receipt proves prerequisites or records a typed denial |
| BRC-G7 — Adversarial validation | Malicious page, URL token, SSRF, prompt-injection, large selection, and workspace-isolation tests | Security reviewer and task-completion validator approve the exact tree |
| BRC-G8 — Packaging and operator canary | Signed local package, native-host installer, uninstall/revocation docs, owner-authorized canary | Canary receipt recorded; live state labeled `qualified` or exact failure disposition |

Gate dependencies: `G0 -> G1 -> G2 -> G3 -> G4 -> G5 -> G6 -> G7 -> G8`.
Schema and fixture drafting may overlap the threat-model review, but no transport or
promotion implementation begins before G0 acceptance.

## 14. Open questions ledger

| ID | Question | Default direction while shaping | Blocks |
|---|---|---|---|
| OQ-BRC-01 | Required Chromium browsers and operating systems? | Chrome/Chromium on the current operator machine only | Packaging matrix |
| OQ-BRC-02 | Default fidelity mode? | `selection`, else `locator_only` | Envelope defaults |
| OQ-BRC-03 | May authenticated/paywalled text leave the browser? | No, absent attributable rights and sensitivity approval | Rights matrix |
| OQ-BRC-04 | How is native-host trust bootstrapped? | Manifest allowlist plus runtime browser-supplied caller-origin validation and host/repo/protocol/key identity handshake | G3 |
| OQ-BRC-05 | What may the offline queue retain? | Metadata by default; selected text only after explicit opt-in | G4 |
| OQ-BRC-06 | Is PDF selection in v1? | Defer unless page/coordinate and byte-edition fidelity is proven | G2 |
| OQ-BRC-07 | What exact action requests promotion? | Open RF review; no one-click auto-promote | G6 |
| OQ-BRC-08 | Can target selection persist? | Remember stable ids only; force reselection on auth/identity change | G3/G4 |
| OQ-BRC-09 | Is a loopback HTTP API needed? | No for v1; revisit after native-host canary | Future transport |
| OQ-BRC-10 | How are annotations exported to interchange/MCP consumers? | Explicit inference/annotation type with provenance, never source quote | Child contract alignment |

## 15. Promotion criteria

Promote this design from `shaping` to `ready` only when:

- OQ-BRC-01 through OQ-BRC-08 have attributable decisions;
- the initiative epic and provenance-continuity child define stable ids and receipt
  ownership that the capture envelope can reference rather than duplicate;
- the external-interchange child defines how captured candidates are represented, or
  explicitly excludes them;
- the knowledge and operator MCP children preserve read-versus-mutation separation for
  candidate review and promotion;
- a threat model accepts MV3 permissions, native-host identity, queue retention, SSRF,
  prompt-injection, rights, and workspace controls;
- fixtures prove the default `selection`/`locator_only` behavior without claiming
  immutable edition fidelity prematurely; and
- an owner approves the live-canary scope, target workspace, data sensitivity, and
  rollback/uninstall path.

If authenticated content, PDF fidelity, secure offline retention, or native-host trust
cannot meet these gates, keep the design at `shaping` or shelve the affected mode. A
design review alone does not qualify browser-store distribution or external writeback.
