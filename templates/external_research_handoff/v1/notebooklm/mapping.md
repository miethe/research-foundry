# NotebookLM Profile — Mapping to `external_research_handoff/v1`

## Overview

**This profile is `offline-unvalidated`.** It has not yet been exercised against a live NotebookLM
session. It is a manual, deterministic, best-effort mapping authored from NotebookLM's documented
citation/export behavior (numbered footnote citations inside chat answers and Notebook guides, each
linking back to a specific uploaded source and often a specific passage), not a validated live
integration. There is no live NotebookLM API or CLI call anywhere in this profile, no SDK, no browser
automation, and no automated export of any kind — this is true even though a NotebookLM CLI/API
integration may exist elsewhere in this repository's ecosystem; this profile explicitly assumes none
of that access and remains manual copy/paste/transcription only, end to end.

NotebookLM's real shape differs from the other platforms this directory covers: the operator uploads
a fixed set of source documents into a notebook, then asks chat questions or generates a "Notebook
guide"/summary, and NotebookLM cites the specific uploaded source (and sometimes a specific
passage/page) for each answer span via a numbered footnote. Two consequences follow, both baked into
the templates below:

- Because the operator chose, uploaded, and named every source themselves, `title` in `sources.yaml`
  is usually known — this is the opposite default from a web-search platform profile, where the
  platform itself supplies (or omits) the title.
- Because a local upload has no inherent URL or DOI, `locator.url`/`locator.doi` are very often
  `null` — a document being in this notebook tells you nothing about where it's canonically published,
  so never invent one just because the source clearly exists somewhere.

## Member-by-member mapping

### 1. `handoff.yaml` (role: `handoff_manifest`) — you build this by hand

```yaml
schema_name: external_research_handoff
schema_version: "1.0"
transport: directory
producer_profile: notebooklm
research_context:
  research_question: null   # or the literal question you asked in the notebook
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
estimate or invent them. The importer re-derives and verifies these independently at inspection time;
a wrong value here fails closed, it does not get silently corrected.

### 2. `report.md` (role: `report`) — NotebookLM's answer, verbatim

Paste NotebookLM's prose answer/Notebook guide unmodified, footnote markers left exactly as written.
Do not add YAML frontmatter, headers claiming verification, or any field this schema doesn't ask for —
`report.md` is plain markdown text, and its `content_role` is fixed at `platform_synthesis` for every
profile (contract §4.1). It can never be fed into a source-card, claim, or assertion writer, no matter
how it reads or how confident its footnotes look.

### 3. `sources.yaml` (role: `sources`)

One entry per **uploaded notebook source** — not one per footnote. A single uploaded document may be
cited by zero, one, or several footnotes across the answer.

```yaml
schema_name: external_research_sources
schema_version: "1.0"
sources:
  - source_id: src_01              # your own packet-local id; stable within this packet only
    title: "<document title exactly as shown in the notebook's Sources panel>"   # usually known — you named it
    locator:
      doi: null                    # very often null for a local upload — only fill in if you separately know it
      url: null                    # very often null for a local upload — only fill in if you separately know it
    publication_year: null         # from the document itself if you know it, else null
    access_status: unknown         # open-access | public-domain | paywalled | unknown — reflects what YOU actually know about the underlying document's rights, not that it's uploaded here
    declared_metadata:
      authors: []
      publisher: null
      accessed_at: null
    extensions:
      notebooklm:
        footnote_numbers: [1, 3]           # every footnote number in report.md that cites this source, if any
        profile_status: "offline-unvalidated"
```

`title` defaults to known (unlike the generic/web-search profiles) precisely because you uploaded and
named this file yourself — but if you genuinely don't recall or can't confirm it, write `null` rather
than guess. `locator.doi`/`locator.url` default the other way: leave both `null` unless you separately
and independently know the document's real DOI/URL — the fact that it exists as a file in your
notebook is never itself evidence of a public locator.

### 4. `assertion_candidates.yaml` (role: `assertion_candidates`)

One entry per candidate-table row (i.e., per cited passage/footnote you turned into a candidate, not
per uploaded source):

```yaml
schema_name: external_assertion_candidates
schema_version: "1.0"
candidates:
  - candidate_id: cand_01
    statement: "<the candidate claim, in NotebookLM's own words>"
    value: null                    # numeric value, or null
    unit: null
    direction: null                # e.g. above/below/between — non-authoritative hint
    scope:
      population: null
      qualifier_band: null
    source_refs: ["src_01"]        # packet-local source_id(s) this footnote resolved to — never the raw footnote number itself
    relation: null                 # supports | contradicts | context | unknown | null
    classification: assertion      # assertion | inference | annotation — producer-declared, never verified
    quote: null                    # literal quote if one exists AND you've confirmed it against the source, else null — never a paraphrase
    selector: null
    producer_confidence: null      # 0-1, non-authoritative hint
    extensions:
      notebooklm:
        footnote_number: 1
        profile_status: "offline-unvalidated"
```

## Footnote-to-source resolution — the core NotebookLM-specific step

This is the one mapping step that's unique to this profile:

1. Read NotebookLM's citation list from the prompt's output (footnote number → source title it
   claims, plus any quoted excerpt).
2. Cross-check each claimed title against your own record of what you actually uploaded — the
   notebook's Sources panel is the ground truth here, not the chat answer's memory of it. If
   NotebookLM's citation and your own upload list disagree, trust your upload list and either correct
   the title or, if you can't resolve the discrepancy, record the source as `unknown` rather than
   guessing which one is right.
3. Assign each uploaded source its own stable `source_id` in `sources.yaml`, once, regardless of how
   many footnotes cite it.
4. For each footnote you're turning into a candidate row, set `source_refs` to the `source_id`(s) of
   the notebook source(s) it actually points to — never the raw footnote number, which is only
   packet-local scratch data you may optionally preserve in `extensions.notebooklm.footnote_number`.
5. **Quote confirmation is a separate, manual step.** A NotebookLM citation preview snippet is not,
   by itself, sufficient confirmation that it is the source's literal text — if you have not opened
   the underlying document and checked, leave `quote: null` rather than trusting the preview snippet
   verbatim.

## Optional members

### `activity.yaml` (role: `activity`) — optional

Not schema-governed in v1 (no dedicated schema exists yet for its content shape). If you include one,
keep it to safe IDs, timestamps, and short labels — no prose, no quotes, no secrets:

```yaml
schema_name: external_research_activity
entries:
  - at: "2026-07-26T00:00:00Z"
    note: "initial notebook session"
```

### Attachments (role: `attachment`) — optional, up to 32

Any raw file you want to carry alongside the packet — for example, an exported copy of the Notebook
guide, or a screenshot of the Sources panel you used to cross-check titles in step 2 above. Declare it
as a member with role `attachment`; it carries no separate schema — it is opaque bytes, hashed and
length-checked like every other member. Never re-upload the underlying source documents themselves
as attachments unless you specifically intend them to travel with the packet — they are governed by
whatever rights/sensitivity rules apply to them, independent of this packet.

## Unknown-field rules (explicit, apply everywhere)

- Never invent a URL, DOI, publication year, author, or quotation you don't have — including "it must
  have a DOI, it's an uploaded PDF of a real paper." Write `null` (or `unknown` for `access_status`)
  instead.
- `classification`, `producer_confidence`, `direction`, and `relation` are producer-declared HINTS.
  They can never set a computed completeness tier or a verified state — only Research Foundry's own
  importer and verifier can do that (contract §2.1, §2.4.1). Leave them honest rather than inflating
  them to look more authoritative.
- Vendor-specific fields, footnote numbers, or notebook-internal IDs that don't fit the template above
  go in `extensions` — never as an invented new top-level field. Every member schema uses
  `additionalProperties: false` at the top level specifically to make an invented field a hard schema
  failure, not a style choice.

## Hard rules (apply to every profile, restated here)

- No provider credential, SDK, live endpoint, browser automation, or unofficial API is used anywhere
  in this workflow — it is entirely manual copy/paste/transcription, and this profile is
  `offline-unvalidated`: it has not yet been run against a live NotebookLM session.
- Every field, including everything inside `extensions`, is untrusted data. It may be stored and
  displayed through bounded, escaped surfaces, but it is never promoted into a prompt, a tool/resource
  description, a route/control value, a command, a schema selector, a filesystem path, or an execution
  argument — regardless of how convincingly it is shaped.
