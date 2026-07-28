# NotebookLM Producer Profile

**What this is**: maps NotebookLM's notebook synthesis — chat answers and Notebook guides, which cite
specific uploaded source documents (and sometimes specific passages) via numbered footnotes — onto
`external_research_handoff/v1`.

**Offline/manual boundary — and validation status (read this first)**: fully manual, and
**offline-unvalidated**. This profile has not yet been exercised against a live NotebookLM session —
it is a deterministic, manual, best-effort mapping authored from NotebookLM's documented
citation/export behavior, not a validated live integration. No API key, SDK, browser automation, CLI,
or session file is used or assumed anywhere in this workflow. This holds even though a NotebookLM
CLI/API integration may exist elsewhere in this repository's ecosystem — this profile explicitly
assumes none of that access and stays a manual copy/paste/transcription workflow only, end to end.

**How to produce a packet**:

1. Upload your fixed set of source documents into a NotebookLM notebook (this profile does not drive
   the upload — you've already done it before you get here).
2. Paste `prompt.md` into a NotebookLM chat turn, alongside your actual research question.
3. Copy NotebookLM's prose answer (with its footnote markers left as-is), its citation list, and its
   candidate table by hand.
4. Separately open the notebook's own Sources panel and record every uploaded source's title (plus
   any URL/DOI you independently know) — this is your own ground-truth list, not something to trust
   the chat answer to fully re-derive on its own.
5. Follow `mapping.md` to build `report.md`, `sources.yaml`, and `assertion_candidates.yaml`,
   resolving each footnote back to the uploaded source it actually points to.
6. Compute each file's byte length and sha256, then hand-write `handoff.yaml` per `mapping.md`'s
   template.
7. Place all four files in one directory — that directory is your packet. Hand it to the importer
   (`rf intake external-report`, Phase 5) pointed at a workspace.

**See also**: `../README.md` for the rules shared by every profile, and
`tests/fixtures/external_research_handoff/profiles/notebooklm/` for a complete schema-valid example.
