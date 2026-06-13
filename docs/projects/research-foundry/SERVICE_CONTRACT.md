---
schema_version: 0.1
type: build_contract
title: "Research Foundry — Service API & Artifact Contract"
status: authoritative
created_at: "2026-06-13"
---

# Service API & Artifact Contract

This document is the **single coordination contract** for the parallel service
build (Wave 2). Every service agent implements the signatures below exactly so
the CLI (Wave 3) can wire them and so services interoperate. When in doubt, the
MVP spec (`research-foundry-mvp-spec.md`) wins on field names; this doc wins on
function signatures and Python conventions.

## 0. Conventions (apply to ALL services)

- Python ≥ 3.11, `from __future__ import annotations`, full type hints, concise
  docstrings. Line length ≤ 100. Pass `ruff`.
- Import foundation modules — **do not reimplement them**:
  - `from ..paths import FoundryPaths, RunPaths`
  - `from ..ids import ...` (slugify, now_iso, today_compact, and the typed id makers)
  - `from ..yamlio import load_yaml, dump_yaml, loads_yaml, dumps_yaml, append_jsonl`
  - `from ..frontmatter import load_md, dump_md, split_frontmatter, join_frontmatter`
  - `from ..config import FoundryConfig`
  - `from ..schemas import default_registry, validate` (validate(instance, schema_name) -> ValidationResult; `.ok`, `.errors`)
  - `from ..registry import Registry, SOURCE_INDEX, RUN_INDEX, CLAIM_INDEX, REPORT_INDEX, SKILLBOM_INDEX`
  - `from ..errors import ExitCode, RFError, SchemaError, GovernanceError, UnsupportedClaimError, HumanReviewRequired, NotFoundError`
- **Artifact files store fields at the TOP LEVEL** (no wrapper key). The spec's
  `raw_idea:` / `research_intent:` wrappers are illustrative only.
- Every service function accepts an optional `paths: FoundryPaths | None = None`
  and resolves `paths = paths or FoundryPaths.discover()` first. Tests inject a
  temp-workspace `FoundryPaths(root=tmp)`.
- After writing any artifact, **validate it** against its schema with
  `validate(obj, "<schema_name>")`; if `not result.ok`, raise `SchemaError`
  with the joined errors. (Skip silently only if the schema file is absent.)
- Result objects are frozen `@dataclass`es (defined in the owning module) with
  plain fields + `Path`s. No printing inside services — the CLI renders.
- Determinism: default execution path must NOT require network or API keys.
  Anything LLM/network is opt-in (`llm: bool = False` / adapter availability)
  and degrades to deterministic behavior.
- Records appended to `telemetry/run_trace.jsonl` via `append_jsonl({...stage, ts...})`
  at the end of each stage (best-effort; never fail the stage on trace error).

## 1. capture.py  (owner: W2-2)  — `rf capture`, `rf triage`

```python
@dataclass(frozen=True)
class CaptureResult:
    raw_idea_id: str
    path: Path
    data: dict

def capture_idea(
    text: str, *,
    title: str | None = None,
    captured_from: str = "manual",      # chat|voice|note|clip|email|meeting|manual
    sensitivity: str = "personal",      # public|personal|work_sensitive|client_sensitive
    urgency: str = "medium",            # low|medium|high
    tags: list[str] | None = None,
    research_potential: str = "unknown",
    suggested_project: str = "Research Foundry",
    paths: FoundryPaths | None = None,
) -> CaptureResult: ...
# Writes inbox/raw_ideas/<raw_id>.md (front matter raw_idea fields TOP LEVEL + body).
# title defaults to first ~8 words of text. id = ids.raw_idea_id(title).
# triage: {status: untriaged, intent_id: null}. Validate vs "raw_idea".

@dataclass(frozen=True)
class TriageResult:
    raw_idea_id: str
    intent_id: str | None
    ibom_id: str | None
    node_id: str | None
    intent_path: Path | None
    ibom_path: Path | None
    node_path: Path | None

def triage_idea(
    raw_idea_ref: str | Path, *,           # path to raw_idea.md OR a raw_idea_id
    create_intent: bool = True,
    create_ibom: bool = True,
    create_tree_node: bool = True,
    paths: FoundryPaths | None = None,
) -> TriageResult: ...
# Deterministically derive:
#  - research_intent -> intents/active/<intent_id>.yaml (id=ids.intent_id(title)).
#    objective from idea body; status: active; type: research; governance from
#    idea sensitivity (key_profile_allowed = personal if sensitivity in
#    {public,personal} else work_approved; requires_human_review = sensitivity in
#    {work_sensitive,client_sensitive}; allowed_writebacks defaults
#    [meatywiki_personal, skillmeat_personal, ccdash_local]).
#    research_questions.primary seeded from idea.initial_questions (or 1 derived).
#    ibom_ref, intenttree_node_ref set when those are created.
#  - ibom -> iboms/active/<ibom_id>.yaml (intent_id link, tools_available defaults,
#    model_policy {extraction_profile: rf_extract_cheap, synthesis_profile:
#    rf_synthesize_deep, verification_profile: rf_verify_balanced},
#    security_boundaries defaults from spec §6.4).
#  - intenttree_node -> intenttree/nodes/<node_id>.yaml (level L4, parent
#    tree_research_foundry, intent_id link, status ready, required postures
#    [researcher,critic,synthesizer], expected_artifacts [evidence_bundle, report,
#    meatywiki_writeback, ccdash_event]).
# Update the raw_idea triage -> {status: converted_to_intent, intent_id}.
# Validate each vs "research_intent" / "ibom" / "intenttree_node".

def load_intent(intent_id: str, paths=None) -> dict: ...   # helper, raises NotFoundError
```

## 2. planning.py  (owner: W2-3)  — `rf plan`

```python
@dataclass(frozen=True)
class PlanResult:
    run_id: str
    brief_id: str
    swarm_id: str
    routing_id: str
    run_dir: Path
    brief_path: Path
    swarm_path: Path
    routing_path: Path

def plan_run(
    intent_id: str, *,
    depth: str = "standard",       # skim|standard|deep|exhaustive
    audience: str = "technical",
    max_cost_usd: float = 5.0,
    max_runtime_minutes: int = 60,
    freshness_days: int = 180,
    paths: FoundryPaths | None = None,
) -> PlanResult: ...
# Load intent (+ ibom via ibom_ref). run_id = ids.run_id(intent_slug). Create the
# run dir via paths.run_paths(run_id).ensure_scaffold().
# Write research_brief.md (front matter brief fields TOP LEVEL + body), swarm_plan.yaml
# (agents list from spec §6.7, model profiles from ibom.model_policy, budget from
# max_cost/runtime), routing_decision.yaml (spec §14: selected_posture_chain,
# selected_tools from config.tools enabled, validation list, writebacks list,
# human_required from intent.governance.requires_human_review), and run.yaml
# (run_id, intent_id, created_at, status: planned, profile).
# Validate brief vs "research_brief", swarm vs "swarm_plan", routing vs "routing_decision".
# Update registries/run_index.yaml.
```

## 3. source_cards.py  (owner: W2-4)  — `rf ingest`, `rf source-card create`

```python
@dataclass(frozen=True)
class IngestResult:
    source_card_id: str
    path: Path
    source_type: str
    degraded: bool   # True if content could not be fetched/read

def ingest_source(
    locator: str, *,                 # URL or local file path
    run_id: str,
    source_type: str = "other",      # official_doc|paper|standard|repo|news|blog|book|personal_note|internal_doc|other
    sensitivity: str = "personal",
    title: str | None = None,
    created_by_agent: str = "rf_source_carder",
    fetch: bool = False,             # attempt URL fetch (best-effort; offline -> degraded)
    paths: FoundryPaths | None = None,
) -> IngestResult: ...
# Resolve content: if locator is an existing file -> read text (pdf: read bytes,
# record path only if no text extractor). If URL and fetch and reachable ->
# urllib best-effort (timeout 8s; any failure -> degraded, locator-only). Else
# degraded (locator only).
# Build source_card per spec §6.8: front matter (type: source_card, source_card_id,
# created_at, created_by_agent, sensitivity, source{title,source_type,locator{url|file_path|doi|repo},
# accessed_at}, trust{source_rank: unknown, reliability_notes}, usage{
# allowed_for_public_output: sensitivity=='public', allowed_for_work_output: sensitivity in
# {public,work_sensitive,personal}, allowed_for_personal_meatywiki: sensitivity!='client_sensitive',
# citation_required: true}, extracted_points[...]).
# extracted_points: deterministically split available content into up to 8 key
# points (evidence_id ev_001.., locator "para/N", summary, quote when short). If
# degraded, one placeholder point flagged needs_content.
# id = ids.source_card_id(title, locator). Write runs/<run>/sources/<src_id>.md.
# Update registries/source_index.yaml. Validate vs "source_card".

def create_source_card(**kwargs) -> IngestResult: ...   # thin alias to ingest_source
def list_source_cards(run_id: str, paths=None) -> list[Path]: ...
```

## 4. extraction.py  (owner: W2-4)  — `rf extract`

```python
@dataclass(frozen=True)
class ExtractResult:
    run_id: str
    cards: list[str]      # extraction_card ids
    count: int

def extract_run(
    run_id: str, *,
    model_profile: str = "rf_extract_cheap",
    paths: FoundryPaths | None = None,
) -> ExtractResult: ...
# For each source card in runs/<run>/sources/: read front matter + body; produce
# one extraction_card -> runs/<run>/extractions/ext_<srchash>_NNN.yaml per spec §6.9.
# extracted_facts derived deterministically from the source card's extracted_points
# (each ev_ -> a fact {evidence_id, text, locator, confidence: medium, quote_available}).
# Pull contradictions_or_cautions from any source 'Limitations' / conflicts.
# Validate vs "extraction_card".
```

## 5. claim_mapping.py  (owner: W2-4)  — `rf claim-map`

```python
@dataclass(frozen=True)
class ClaimMapResult:
    run_id: str
    ledger_path: Path
    claims_total: int
    by_status: dict           # {supported: n, inference: n, ...}

def build_claim_ledger(
    run_id: str, *,
    intent_id: str | None = None,
    paths: FoundryPaths | None = None,
) -> ClaimMapResult: ...
# Read all extraction cards (+ their source_card_id). Map each extracted fact ->
# a claim per spec §6.10: claim_id clm_001.., text=fact.text, materiality:
# 'material' (facts/metrics) else 'background', claim_type heuristic
# (quantitative if contains a number/%, comparative if 'more|less|than|vs',
# causal if 'because|causes|leads to|reduces|increases', attribution if 'says|
# according to|claims', else factual), status: 'supported',
# sources:[{source_card_id, evidence_id, relation: supports, locator}], confidence.
# Write claims/claim_ledger.yaml (id, intent_id, report_ref:
# reports/report_draft.md, verification_status: pending, claims[...],
# unresolved_questions[]). Also write claims/contradiction_log.yaml and
# claims/inference_log.yaml (seed contradictions from extraction
# contradictions_or_cautions + source conflicts_with). Validate vs "claim_ledger".
# Update registries/claim_index.yaml. by_status counts each status.
```

## 6. synthesis.py  (owner: W2-5)  — `rf synthesize`

```python
@dataclass(frozen=True)
class SynthResult:
    run_id: str
    report_path: Path
    claims_cited: list[str]

def synthesize_report(
    run_id: str, *,
    model_profile: str = "rf_synthesize_deep",
    final: bool = False,          # write report_final.md instead of report_draft.md
    audience: str | None = None,
    sensitivity: str | None = None,
    llm: bool = False,            # opt-in LLM synthesis via claude_agent_sdk adapter; default deterministic
    paths: FoundryPaths | None = None,
) -> SynthResult: ...
# DETERMINISTIC default: read claims/claim_ledger.yaml. Write reports/report_draft.md
# (or report_final.md if final) with report_frontmatter (type: research_report,
# report_id, title, intent_id, evidence_bundle_id: null-or-pending, created_at,
# status: draft, audience, sensitivity, claim_policy text, verification_status: pending).
# Body, in this exact discipline:
#   ## Findings  -> one sentence per SUPPORTED claim ending with [claim:<id>]
#   ## Inferences -> per INFERENCE claim: "**Inference:** <text> [claim:<id>]"
#   ## Speculation -> per SPECULATION claim: "**Speculation:** <text> [claim:<id>]"
#   ## Open questions -> ledger.unresolved_questions
#   ## Sources -> list source cards used (id + title)
# HARD RULE: cite ONLY claim_ids present in the ledger; never emit an untagged
# material sentence. (This guarantees `rf verify` returns 0 on this path.)
# audience/sensitivity default from the linked intent. claims_cited = ids emitted.
# llm=True path: call adapters.get_adapter('claude_agent_sdk'); if unavailable or
# degraded, fall back to deterministic and note it.
```

## 7. verification.py  (owner: W2-5)  — `rf verify`  ★ CROWN JEWEL ★

```python
@dataclass(frozen=True)
class CheckResult:
    id: str
    severity: str        # error|warning
    status: str          # pass|fail|warn|skip
    detail: str
    locations: list[str]

@dataclass(frozen=True)
class VerificationResult:
    run_id: str
    passed: bool
    exit_code: int       # int(ExitCode.*)
    checks: list[CheckResult]
    verification_path: Path
    unsupported: list[str]

def verify_report(
    run_id: str, *,
    report_path: Path | None = None,        # default reports/report_draft.md (fallback report_final.md)
    claim_ledger_path: Path | None = None,  # default claims/claim_ledger.yaml
    fail_on_unsupported: bool = True,
    paths: FoundryPaths | None = None,
) -> VerificationResult: ...
```
Implement the spec §12.3 verifier_checks deterministically. Load `config/claim_policy.yaml`
for the check list + material_claim_types when present; otherwise use built-in defaults.
Parse the report body: extract every `[claim:<id>]` tag; segment sentences;
detect label prefixes `**Inference:**` / `**Speculation:**` / `Mixed evidence` /
`Contradicted`. Checks:

- `report_has_frontmatter` (error→ExitCode.SCHEMA/2 if missing).
- `all_claim_ids_exist` (error): every `[claim:id]` in the report exists in the ledger.
- `material_claims_have_claim_ids` (error→**ExitCode.UNSUPPORTED/4**): any sentence
  classified material (matches a material_claim_type heuristic) that has NO
  `[claim:]` tag and is NOT under an Inference/Speculation label → unsupported.
- `supported_claims_have_source_cards` (error): ledger claims status==supported have ≥1 source.source_card_id.
- `source_cards_have_locators` (warning): cited source cards resolve to a file with a locator.
- `inferences_have_basis` (error): ledger claims status==inference have inference_basis.from_claims non-empty.
- `speculation_is_labeled` (error): report speculation claims carry the Speculation label.
- `unsupported_claims_block_publish` (error→4): any ledger claim status==unsupported.
- `work_sensitive_claims_block_public_report` (error→3 GOVERNANCE): report sensitivity==public but a cited source card sensitivity ∈ {work_sensitive, client_sensitive}.

Exit-code precedence (return the FIRST that applies): missing frontmatter/schema →2;
governance (work-sensitive in public) →3; any unsupported material claim / unsupported
ledger claim →4 (when fail_on_unsupported); else 0. Also: if the linked intent has
`governance.requires_human_review: true` and no approval recorded, the CLI (not the
service) may surface →7; expose `human_review_required: bool` on the result for that.
Write `reviews/verification.yaml` (verification schema-free YAML: run_id, passed,
exit_code, generated_at, checks[...], unsupported[...]); also set the ledger's
`verification_status` to passed/failed. Validate written report front matter vs
"report_frontmatter".

## 8. governance.py  (owner: W2-1)  — `rf guard`

```python
@dataclass(frozen=True)
class Violation:
    rule_id: str
    severity: str       # block|require_approval|warn
    message: str
    detail: str

@dataclass(frozen=True)
class GuardResult:
    passed: bool
    exit_code: int      # 0 ok, 3 block, 7 require_approval
    violations: list[Violation]

@dataclass(frozen=True)
class GuardContext:
    profile: str = "personal"               # runtime key profile
    run_id: str | None = None
    sensitivity: str | None = None          # run/bundle sensitivity
    source_sensitivities: list[str] = ()    # sensitivities of involved source cards
    model_provider: str | None = None
    writeback_targets: list[str] = ()
    intent_key_profile_allowed: str | None = None
    artifact_paths: list[Path] = ()         # files to secret-scan

def guard_check(ctx: GuardContext, *, paths: FoundryPaths | None = None) -> GuardResult: ...
def preflight(intent: dict, ibom: dict, routing: dict, profile: str, *, paths=None) -> GuardResult: ...
def scan_secrets(text: str, *, config: FoundryConfig | None = None) -> list[str]: ...
def scan_paths(paths_to_scan: list[Path], *, config=None) -> list[Violation]: ...
```
Evaluate the §7.2 rules deterministically (load `config/governance.yaml`
key_profiles + policy_rules + secret_patterns; fall back to built-ins):
`no_work_keys_for_personal_runs`, `no_work_sensitive_to_unapproved_provider`,
`no_mixed_personal_work_bundle`, `no_secret_in_markdown`,
`work_writeback_requires_review` (severity require_approval → exit 7),
`material_claims_must_be_mapped` (may defer to verification result if provided).
exit_code: any block → 3; else any require_approval → 7; else 0.

### Hook entrypoints (owner: W2-1), under validators/:
- `validators/guard_pretool.py` — reads Claude Code hook JSON from stdin
  (tool_name, tool_input), runs a lightweight governance preflight + secret scan
  on Write/Edit content and `.env`/secret path access; prints a JSON decision and
  exits 0 (allow) / non-zero/blocking JSON (deny). `main()` + `__main__`.
- `validators/scan_artifact.py` — PostToolUse: secret-scan the written file and
  lint claim labels; warn (non-blocking). `main()` + `__main__`.
- `validators/emit_ccdash_event.py` — Stop hook shim → calls
  `services.telemetry.emit_latest_or_noop()`. `main()` + `__main__`.
All three must be safe no-ops when not inside a foundry workspace / no stdin.

## 9. writeback.py  (owner: W2-6)  — `rf bundle`, `rf writeback`, `rf council`, `rf skillbom`

```python
@dataclass(frozen=True)
class BundleResult:
    run_id: str
    bundle_id: str
    bundle_path: Path
    counts: dict
    verified: bool

def build_bundle(run_id: str, *, verify: bool = True, paths=None) -> BundleResult: ...
# Assemble evidence_bundle.yaml (spec §6.11) referencing all run artifacts +
# counts (source_cards, extraction_cards, claims_total, claims_supported/inference/
# speculation/unsupported). If verify: run verification.verify_report first; set
# status verified/draft accordingly; governance.approved_for_writeback only when
# verified. lineage from intent/ibom/node. Validate vs "evidence_bundle".

@dataclass(frozen=True)
class WritebackResult:
    run_id: str
    meatywiki_path: Path | None
    skillbom_path: Path | None
    ccdash_path: Path | None
    requires_review: bool

def writeback(run_id: str, *, targets=("meatywiki","skillmeat","ccdash"),
              require_review: bool = False, paths=None) -> WritebackResult: ...
# meatywiki: writebacks/meatywiki_writeback.md (+ mirror meatywiki/sources/<slug>.md)
#   from templates/meatywiki_source_note.md, key_claims from supported claims.
# skillmeat: writebacks/skillbom_candidate.md (+ mirror skillmeat/skillboms/<id>.md)
#   from templates/skillbom_candidate.md (proposed_skillbom_id skill_research_swarm_v0).
# ccdash: delegate to telemetry.emit_ccdash_event(run_id) -> writebacks/ccdash_event.yaml
#   (+ mirror ccdash/events/<event_id>.yaml).
# Honor governance: if require_review or run sensitivity work/client -> set
# requires_review True and mark writebacks status proposed (not written) for
# meatywiki. Update registries/skillbom_index.yaml + report_index.yaml.

def council_review(run_id: str, *, roles: list[str], vote: str = "approve-concern-block", paths=None) -> Path: ...
# Deterministic council: produce reviews/council_review.yaml (spec §13.5) with one
# member per role; votes derived from the verification result (pass -> approve,
# warnings -> concern, fail -> block). Validate vs "review_packet".

def skillbom_propose(run_id, paths=None) -> Path: ...
def skillbom_promote(candidate_id, *, reviewer: str, paths=None) -> Path: ...
```

## 10. telemetry.py  (owner: W2-6)  — `rf ccdash summarize`

```python
def emit_ccdash_event(run_id: str, *, paths=None) -> Path: ...
# Build execution_event (spec §6.15) from run artifacts: metrics (counts from
# claim ledger + bundle), tools (from swarm_plan/routing), agent_postures,
# governance{sensitivity, key_profile_used, policy_passed}, reuse flags
# (meatywiki_writeback_candidate/skillbom_candidate True). Write
# writebacks/ccdash_event.yaml + ccdash/events/<event_id>.yaml. Validate vs "ccdash_event".

def summarize(period: str = "daily", *, paths=None) -> Path: ...
# Aggregate ccdash/events/*.yaml into ccdash/daily/<date>.yaml + a ccdash/summaries
# rollup: totals for runs, claims, unsupported, cost, verification pass rate, reuse
# candidates.

def emit_latest_or_noop(paths=None) -> Path | None: ...   # used by the Stop hook shim
```

## 11. adapters/*.py  (owner: W2-7)

Each subclasses `BaseAdapter`, sets `id` + `requires`, implements `run(request)`
returning `AdapterResult`, and calls `register(<instance>())` at module load.
All must produce a deterministic `degraded=True` result when `available()` is False.
- `claude_agent_sdk.py` (requires=("claude_agent_sdk",)) — orchestration; degraded
  returns a structured stub echoing the request intent.
- `gpt_researcher.py` (requires=("gpt_researcher",)) — discovery; degraded turns the
  brief's research questions into labeled source_candidates (no network).
- `paperqa2.py` (requires=("paperqa",)) — scientific RAG over a local pdf dir;
  degraded lists local PDFs as candidates or returns a note.
- `opencode.py` (requires=()) — available() = shutil.which("opencode") is not None;
  degraded returns a note.
- `litellm_router.py` (requires=("litellm",)) — exposes `route(model_profile) -> dict`
  reading config/model_profiles + env; degraded returns the profile's preferred entry.

## 12. CLI wiring (Wave 3, orchestrator) — `cli_commands.py`

A single `register(app: typer.Typer)` attaches all commands per spec §10:
`capture, triage, plan, ingest, source-card, extract, claim-map, synthesize,
verify, council, bundle, writeback, guard, skillbom (propose|promote), status,
doctor, cost, index, ccdash (summarize)`. Each command calls the matching service,
renders with Rich, and `raise typer.Exit(result.exit_code)` for verify/guard.
