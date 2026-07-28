# Gemini Producer Profile

**What this is**: the producer profile for `external_research_handoff/v1` specialized for Gemini's
actual output shape — prose broken into spans, where some spans show small numbered grounding
chips/footnotes (each pointing at a web source Gemini says it used, with a title and a URL) and some
spans show no grounding chip at all.

**Offline/manual boundary**: fully manual, and **no Google API coupling of any kind**. You paste
`prompt.md` into a Gemini chat session (or read it as a transcription guide against an AI Overview
response), copy the assistant's response by hand — including which chip(s), if any, sit next to each
span — and build the four packet files yourself following `mapping.md`. This profile never calls,
imports, or depends on Gemini's API or its `groundingMetadata` structure; it does not use a browser
automation tool, a session file, or any unofficial API. Every chip and every span is read by a human
and transcribed into operator-assigned packet-local IDs.

**How to produce a packet**:

1. Paste `prompt.md` into Gemini, or use it as your checklist while reading a Gemini AI Overview
   response you already have in front of you.
2. Copy Gemini's prose report, its sources list, and its candidate table (one row per answer span).
3. For every grounding chip shown, assign it a `source_id` and record its displayed title/URL — see
   `mapping.md`'s chip-to-source rules.
4. For every span, record whether it was grounded (chip attached) or ungrounded (no chip) and follow
   `mapping.md`'s two candidate shapes accordingly. Never invent a source for an ungrounded span, and
   never treat a grounded paraphrase as a quote.
5. Follow `mapping.md` to build `report.md`, `sources.yaml`, and `assertion_candidates.yaml`. Leave
   any value you cannot confirm explicitly `null` rather than omitting the field or guessing.
6. Compute each file's byte length and sha256, then hand-write `handoff.yaml` per `mapping.md`'s
   template.
7. Place all four files in one directory — that directory is your packet. Hand it to the importer
   (`rf intake external-report`, Phase 5) pointed at a workspace.

**See also**: `../README.md` for the rules shared by every profile, `../generic/` for the baseline
pattern this profile specializes, and
`tests/fixtures/external_research_handoff/profiles/gemini/` for a complete schema-valid example.
