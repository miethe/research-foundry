# RFUP Enhancement Areas: Current-State Fact Sheet

Evidence snapshot for 7 planned enhancement areas (RFUP-1..7). Coordinates: relative to src/research_foundry/* unless otherwise noted.

---

## RFUP-1: Workflow Hard-Coded Paths & Stamps

**File:** `.claude/workflows/rf-run-execute.js`

### Facts
- **RF binary location** (line 18): `/Users/miethe/.local/bin/rf`
- **REPO checkout path** (line 19): `/Users/miethe/dev/homelab/development/research-foundry`
- **Temporary working dir** (line 20): `/Users/miethe/.claude/jobs/85ede6ca/tmp` (unique per workflow invocation)
- **Date stamp (frozen)** (line 21): `20260613` (YYYYMMDD format; baked into source_card_id generation: line 121, `STAMP.slice()`)
- **Write rule hard-coded** (lines 97-100): prohibits Write/Edit tools under `REPO/runs/*`, mandates TMP→Bash cp pattern for all file writes
- **File-write pattern**: always author to TMP, then `cp $TMP/<name> $DEST` + verify with `ls -la` (lines 127, 164, 189, 212)

### Relevant Files
- `.claude/workflows/rf-run-execute.js:18–21, 97–100` (path + TMP + stamp constants)
- `.claude/workflows/rf-run-execute.js:121, 164, 189, 207, 212` (usage in prompts)

---

## RFUP-2: URL/PDF Extraction in rf fetch

**Files:** `services/search_router/router.py`, `services/source_cards.py`

### Facts
- **URL extraction entry point** (line 288–347): `extract_urls()` is the known-URL extraction path used by `rf fetch`
- **Extraction provider preference** (line 31): `("jina", "firecrawl")` — first available in this order selected via `_first_extraction_provider()`
- **Provider role check** (line 103): providers must have `"extraction"` in their `roles` set to be callable
- **Markdown extraction** (line 202–204): calls `extractor.extract([hit.url])` → gets `.docs[0].markdown` if available
- **Degradation logic** (line 208–209, 344–345): if `.markdown` is None → extraction failure recorded; card still created with "locator-only" degradation (`degraded=True` in ingest result) but card created anyway
- **PDF text extraction**: no dedicated PDF parser in this module; relies entirely on extractor provider (jina/firecrawl) to emit `.markdown` — if provider fails, locator card is produced without text content
- **Source card creation** (line 211–221): `create_source_card(locator=url, content=markdown, fetch=False)` — markdown passed directly as content; None allowed

### Relevant Files
- `services/search_router/router.py:31, 103, 186, 202–209, 288–347` (URL extraction + degradation)
- `services/search_router/router.py:344–346` (degraded flag set when markdown extraction fails but card succeeds)

---

## RFUP-3: rf verify — Locator/Passage Checks

**File:** `services/verification.py`

### Facts
- **Check severity hierarchy** (lines 52–62): 10 built-in checks defined; each has `severity: error | warning`
- **Locator check: WARNING not ERROR** (line 57): `source_cards_have_locators` is a *warning* (not blocking); lines 598–622
- **Locator structure** (line 266–268): locator is a dict with keys `{url, file_path, doi, repo}`; ANY non-empty value satisfies `has_locator` check
- **Exact-passage handling**: NO dedicated "passage" extraction check; passages verified only implicitly via quote matching (line 1032–1033): `if any(q and q in body_text for q in quotes)` — raw quote string-match against report body, fail-closed on mismatch
- **Material sentence heuristics** (line 79–118): 7 types (quantitative, comparative, attribution, causal, prediction, recommendation, factual) classified via regex; sentence without tag + material = unsupported (error)
- **Supported claims require source cards** (line 56): `supported_claims_have_source_cards` is ERROR; supported claim with no resolvable source card blocks publish (exit 4)
- **Inference basis check** (line 58): `inferences_have_basis` ERROR; inference claim missing `inference_basis.from_claims` blocks publish
- **Labeled-claim enforcement** (line 648–680): inference/speculation/mixed/contradicted statuses *must* carry the bold label (`**Inference:**` etc.) if rendered in report body

### Relevant Files
- `services/verification.py:52–62` (check registry)
- `services/verification.py:266–268, 598–622` (locator check: warning severity)
- `services/verification.py:79–118` (material claim heuristics)
- `services/verification.py:540–566` (material_claims_have_claim_ids error check)

---

## RFUP-4: CLI Output Schema & Machine Contracts

**Files:** `errors.py`, `cli_commands.py`

### Facts
- **Exit codes (stable contract)** (errors.py:12–26):
  - `OK = 0`
  - `USAGE = 1` (bad args)
  - `SCHEMA = 2` (validation failed)
  - `GOVERNANCE = 3` (policy blocked)
  - `UNSUPPORTED = 4` (untagged material claim)
  - `BUDGET = 5` (budget exceeded)
  - `ADAPTER = 6` (tool failure)
  - `HUMAN_REVIEW = 7` (review required)
- **CLI output format** (cli_commands.py): Rich for human output; `--json/--no-json` flags on most commands return structured results
- **Schema version stamps**: run export (run-export.ts for runs-viewer) uses schema 1.5 (not embedded in CLI core); workflows use no `schema_version` field in output
- **No hardened JSON output contract yet**: CLI commands print Rich + optional JSON flags; cross-command consistency via error types carrying `exit_code` attribute (error.py:36, 40)

### Relevant Files
- `errors.py:12–26` (ExitCode enum contract)
- `cli_commands.py:~30–40` (exit code translation via typer)
- `cli_commands.py:grep "json_out.*Option"` (--json flag presence)

---

## RFUP-5: rf council — Consensus Results Format

**File:** `adapters/arc_council.py`

### Facts
- **Adapter pattern** (line 36–88): ARC Council is ONE adapter (arc_council) calling `scaffold_review()` + `get_run()` on ARC server
- **Verdict field** (line 74): reads `run_record.get("verdict")` — expected to be a STRING (no enum); line 78 defaults to `"pending"` if missing
- **Output format** (line 80–86): returns `AdapterResult(artifacts={"arc_run_id": <id>, "arc_verdict": <string>}, notes=[...])`
- **No built-in consensus logic**: arc_council is ONE external adapter; consensus results are free-form text from ARC (whatever ARC's verdict field contains), NOT an enum
- **Degraded mode** (line 90–100): if ARC unreachable, returns stub `AdapterResult(degraded=True, artifacts={}, notes=["arc unreachable: deterministic stub"])`

### Relevant Files
- `adapters/arc_council.py:36–88` (run/verdict flow)
- `adapters/arc_council.py:74, 78` (verdict field: string, "pending" default)

---

## RFUP-6: Native Discovery Adapters — 6 Installed

**Files:** `adapters/__init__.py`, `adapters/base.py`

### Facts
- **Declared adapters** (adapters/__init__.py:17–26): list of 8 concrete adapter names:
  1. `arc_council` (post-research review council)
  2. `claude_agent_sdk` (Claude agent integration)
  3. `gpt_researcher` (GPT Researcher wrapper)
  4. `notebooklm` (NotebookLM integration)
  5. `openai_agents` (OpenAI agents wrapper)
  6. `paperqa2` (PaperQA2 integration)
  7. `opencode` (OpenCode integration)
  8. `litellm_router` (LiteLLM provider routing)
- **Installation handling** (adapters/__init__.py:29–39): `load_all()` imports each module; **any import error is silently caught** (line 37: `except Exception: continue`), so missing optional deps never break startup
- **Availability method** (base.py:79–81, line 94–95): each adapter implements `available()` returning bool; defaults to checking `all(module_available(m) for m in self.requires)`
- **Module availability check** (base.py:27–33): `module_available()` uses `importlib.util.find_spec()` (no import side-effects)
- **Roles system** (base.py:73–86): adapters declare `roles: tuple[str, ...]` (e.g., `"discovery"`, `"extraction"`); `_first_extraction_provider()` searches for `"extraction"` in roles

### Relevant Files
- `adapters/__init__.py:17–26` (_CONCRETE list)
- `adapters/__init__.py:29–39` (load_all: graceful degradation)
- `adapters/base.py:27–33, 79–95` (availability + module checks)

---

## RFUP-7: Run Immutability — Storage, Mutation, Audit

**Files:** `paths.py`, `services/assertion_registry.py`, `services/verification.py`

### Facts
- **Run structure** (paths.py:188–192, 195–336): runs live at `runs/<run_id>/` with standard subdirs: `sources/`, `claims/`, `reports/`, `reviews/`, `writebacks/`, `telemetry/`
- **Claim ledger** (paths.py:234–235): `runs/<run_id>/claims/claim_ledger.yaml` — YAML dict with `claims:` list; no append-only index (mutable file)
- **Source cards** (paths.py:222–223): `runs/<run_id>/sources/*.md` — one markdown file per source card; card ID embedded in frontmatter + filename
- **Assertion registry (immutable audit)** (assertion_registry.py:1–8): **separate from run-local source cards**; workspace-scoped, immutable YAML files at `assertion_ledger/workspaces/<workspace_hash>/sources/<source_id>/`
- **Atomic writes** (assertion_registry.py:50–64, 67–81): all registry writes use temp file + `os.fsync()` + `os.replace()` (atomic replace); no partial-file exposure
- **Edition immutability** (assertion_registry.py:156–200): editions are content-addressable (digest-identified), passages track quote ranges; once written, editions never mutate (new edits create new edition_id)
- **Report mutation tracking** (verification.py:785–791): `verify_report()` updates ledger's `verification_status` field after run; verification.yaml persisted separately in `runs/<run_id>/reviews/verification.yaml`
- **What can mutate a completed run**: run-local files (claim_ledger.yaml, report_draft.md) are mutable YAML/Markdown; verification.yaml is recomputable; assertion_registry editions are immutable once written

### Relevant Files
- `paths.py:188–336` (RunPaths structure + ensure_scaffold)
- `assertion_registry.py:1–8, 50–81, 156–200` (atomic writes + edition immutability)
- `services/verification.py:785–791` (verification status update to mutable ledger)

---

## Cross-Cutting Observations

1. **Write safety**: RFUP-1 workflow enforces TMP→cp pattern to avoid tool-edit rejections on runs/ directories; no built-in transaction layer
2. **Degradation-first design**: RFUP-2 (fetch), RFUP-6 (adapters) both degrade gracefully rather than fail; locator-only cards are the minimal unit of success
3. **Verification gates**: RFUP-3 verification runs AFTER synthesis/enrichment; re-verification via `rf verify` is deterministic (re-reads ledger + report)
4. **Assertion ledger isolation**: RFUP-7 assertion registry is workspace-scoped and intentionally separate from run-local claim_ledger; no shared mutation
5. **No cross-run claim deduplication**: runs reference source_card_id by value (string), not by assertion-registry edition_id; each run's ledger is independent
