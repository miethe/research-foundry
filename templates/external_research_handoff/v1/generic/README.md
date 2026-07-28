# Generic Producer Profile

**What this is**: the canonical, platform-agnostic producer profile for
`external_research_handoff/v1`. Use it for any assistant/platform that doesn't have a dedicated
profile in this directory, or as the reference pattern the other four profiles specialize.

**Offline/manual boundary**: fully manual. You paste `prompt.md` into a chat session, copy the
assistant's response by hand, and build the four packet files yourself following `mapping.md`. No
API key, SDK, browser automation, or session file is used or assumed anywhere in this workflow.

**How to produce a packet**:

1. Paste `prompt.md` into your assistant of choice.
2. Copy its prose report, sources list, and candidate table.
3. Follow `mapping.md` to build `report.md`, `sources.yaml`, and `assertion_candidates.yaml`.
4. Compute each file's byte length and sha256, then hand-write `handoff.yaml` per `mapping.md`'s
   template.
5. Place all four files in one directory — that directory is your packet. Hand it to the importer
   (`rf intake external-report`, Phase 5) pointed at a workspace.

**See also**: `../README.md` for the rules shared by every profile, and
`tests/fixtures/external_research_handoff/profiles/generic/` for a complete schema-valid example.
