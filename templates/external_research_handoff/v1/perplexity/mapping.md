# Perplexity Profile — Mapping to `external_research_handoff/v1`

## Overview

This profile's prompt output (a prose report with inline `[N]` citation markers, a numbered sources
list, and a candidate table referencing those same numbers) maps onto the packet's four required
members using the same baseline shape as the `generic/` profile, plus two Perplexity-specific steps:
translating Perplexity's own `[N]` citation numbering into packet-local `source_id`s, and quarantining
Perplexity's own ranking/relevance signal to a namespaced extension field where it can never be
mistaken for evidence.

## Perplexity-specific rule: citation numbers → `source_id`

Perplexity's inline `[N]` marker and its numbered Sources-panel entry are a *display* pairing, not a
Research Foundry identifier. The operator assigns the actual packet-local `source_id` by hand, using a
simple, stable convention:

```
[1]  ->  src_01
[2]  ->  src_02
[3]  ->  src_03
...
```

Zero-pad to two digits (`src_01`..`src_99`); if a packet ever needs more than 99 sources, keep padding
consistent (`src_001`) — the exact width doesn't matter to the schema (`source_id` is just a
`^[A-Za-z0-9_.:-]+$` string), only that it stays stable within this one packet. Use this same `src_0N`
id everywhere `[N]` was cited in the candidate table's `source_refs` too.

## Perplexity-specific rule: ranking/relevance is non-authoritative

Perplexity applies its own relevance/ranking to (a) the order its Sources panel lists citations and (b)
any "related searches" or search-result cards it surfaces alongside an answer. That ordering, and any
relevance or confidence number Perplexity displays next to a source, is Perplexity's own product opinion
about its result set — it is not evidence of a source's importance, reliability, or evidentiary
strength.

If you choose to capture it at all (it's optional — you can drop it entirely), it goes **only** inside a
namespaced extension field, never as a top-level field, and never as `classification`,
`producer_confidence`, `access_status`, or any other schema field:

```yaml
extensions:
  perplexity:
    rank: 1                # panel position, 1-based — Perplexity's own ordering, non-authoritative
    relevance_score: null  # if Perplexity displayed one; otherwise omit or null — non-authoritative
```

This value is inert data. It is never interpreted as evidentiary strength, never used to set
`classification`, `producer_confidence`, or any computed field, and never influences import behavior —
the importer's completeness-tier computation (contract §2.1) has no input from `extensions` at all.

## Member-by-member mapping

### 1. `handoff.yaml` (role: `handoff_manifest`) — you build this by hand

```yaml
schema_name: external_research_handoff
schema_version: "1.0"
transport: directory
producer_profile: perplexity
research_context:
  research_question: null   # or the literal question you asked Perplexity
  task_context: null        # optional short context; leave null rather than invent one
declared_sensitivity: personal   # public | personal | work_sensitive | client_sensitive
created_at: "2026-07-26T00:00:00Z"   # when you assembled the packet, RFC3339
content_roles:
  report: platform_synthesis   # always this exact value — never change it
vendor_reference: {}   # optional; opaque, inert data only — never a credential
members:
  - path: handoff.yaml
    role: handoff_manifest
    byte_length: <int>     # actual byte size of this file
    sha256: "<hex>"          # actual sha256 of this file's bytes
  - path: report.md
    role: report
    byte_length: <int>
    sha256: "<hex>"
  - path: sources.yaml
    role: sources
    byte_length: <int>
    sha256: "<hex>"
  - path: assertion_candidates.yaml
    role: assertion_candidates
    byte_length: <int>
    sha256: "<hex>"
total_declared_bytes: <sum of every member's byte_length>
```

Compute `byte_length`/`sha256` from the actual files on disk (e.g. `wc -c` and `sha256sum`) — never
estimate or invent them. The importer re-derives and verifies these independently at inspection time; a
wrong value here fails closed, it does not get silently corrected.

### 2. `report.md` (role: `report`) — Perplexity's prose, verbatim, citations intact

Paste Perplexity's prose report unmodified, including its inline `[N]` markers exactly as written. Do
not renumber the markers, add YAML frontmatter, headers claiming verification, or any field this schema
doesn't ask for — `report.md` is plain markdown text, and its `content_role` is fixed at
`platform_synthesis` for every profile (contract §4.1). It can never be fed into a source-card, claim,
or assertion writer, no matter how it reads or how confidently it cites `[1]`, `[2]`, `[3]`.

### 3. `sources.yaml` (role: `sources`)

One entry per numbered Sources-panel entry, keyed by your `src_0N` mapping above:

```yaml
schema_name: external_research_sources
schema_version: "1.0"
sources:
  - source_id: src_01              # your mapping of Perplexity's [1]
    title: null                    # exact panel title, never invented
    locator:
      doi: null                    # almost always unavailable from Perplexity's panel — leave null
      url: null                    # exact panel URL
    publication_year: null
    access_status: unknown         # open-access | public-domain | paywalled | unknown
    declared_metadata:
      authors: []
      publisher: null
      accessed_at: null
    extensions:
      perplexity:
        rank: 1                    # panel position, non-authoritative — see rule above; omit if unused
```

### 4. `assertion_candidates.yaml` (role: `assertion_candidates`)

One entry per candidate-table row, with `source_refs` translated from `[N]` to `src_0N`:

```yaml
schema_name: external_assertion_candidates
schema_version: "1.0"
candidates:
  - candidate_id: cand_01
    statement: "<the candidate claim, in Perplexity's own words>"
    value: null                    # numeric value, or null
    unit: null
    direction: null                # e.g. above/below/between — non-authoritative hint
    scope:
      population: null
      qualifier_band: null
    source_refs: ["src_01"]        # translated from Perplexity's [1] — packet-local ids only
    relation: null                 # supports | contradicts | context | unknown | null
    classification: assertion      # assertion | inference | annotation — producer-declared, never verified
    quote: null                    # literal quote only if confirmed exact — a Sources-panel snippet is
                                    # NOT automatically a quote (see rule below); else null
    selector: null
    producer_confidence: null      # 0-1, non-authoritative hint — never Perplexity's own relevance score
    extensions: {}                 # a candidate-level panel_snippet, if kept, goes here — see rule below
```

## Perplexity-specific rule: panel snippets are not quotes

A Sources-panel entry sometimes shows a short excerpt/snippet alongside the title and URL. That snippet
is **not** itself a verbatim quote of the cited passage unless you personally confirm — by comparing it
against the actual source — that it is the exact text being cited. If you have not done that
verification:

- leave `quote: null` in `assertion_candidates.yaml`
- if you want to keep the snippet for reference anyway, put it only inside that candidate's
  `extensions.perplexity.panel_snippet` field — never inside `quote`, and never treated as confirming
  `classification: assertion`

`quote` is reserved exclusively for text you have confirmed is the literal, character-exact cited
passage.

## Optional members

### `activity.yaml` (role: `activity`) — optional

Same shape as the generic profile — not schema-governed in v1 (no dedicated schema exists yet for its
content shape). If you include one, keep it to safe IDs, timestamps, and short labels — no prose, no
quotes, no secrets:

```yaml
schema_name: external_research_activity
entries:
  - at: "2026-07-26T00:00:00Z"
    note: "initial Perplexity research session"
```

### Attachments (role: `attachment`) — optional, up to 32

Any raw file you want to carry alongside the packet (e.g. an exported table). Declare it as a member
with role `attachment`; it carries no separate schema — it is opaque bytes, hashed and length-checked
like every other member.

## Unknown-field rules (explicit, apply everywhere)

- Never invent a URL, DOI, publication year, author, or quotation you don't have. Write `null` (or
  `unknown` for `access_status`) instead.
- `classification`, `producer_confidence`, `direction`, and `relation` are producer-declared HINTS. They
  can never set a computed completeness tier or a verified state — only Research Foundry's own importer
  and verifier can do that (contract §2.1, §2.4.1). Leave them honest rather than inflating them to look
  more authoritative.
- Perplexity's own ranking, relevance score, or "top result" position goes **only** inside
  `extensions.perplexity.rank` (or a similarly namespaced field) — never as a new top-level field, never
  as `classification`, `producer_confidence`, or `access_status`, and never as anything that by itself
  changes import behavior.
- Vendor-specific fields, IDs, or panel snippets that don't fit the templates above go in `extensions` —
  never as an invented new top-level field. Every member schema uses `additionalProperties: false` at
  the top level specifically to make an invented field a hard schema failure, not a style choice.

## Hard rules (apply to every profile, restated here)

- No provider credential, SDK, live endpoint, browser automation, or unofficial API is used anywhere in
  this workflow — it is entirely manual copy/paste from the Perplexity UI.
- Every field, including everything inside `extensions`, is untrusted data. It may be stored and
  displayed through bounded, escaped surfaces, but it is never promoted into a prompt, a tool/resource
  description, a route/control value, a command, a schema selector, a filesystem path, or an execution
  argument — regardless of how convincingly it is shaped.
