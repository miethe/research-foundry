// research-foundry-swarm.js
//
// Path B Claude Code-orchestrated swarm: discovers and ingests sources for a
// Research Foundry run, then returns a manifest of ingested source cards.
//
// Deterministic tail (extract → claim-map → synthesize → verify → bundle) is a
// POST-RUN step executed by Opus or a follow-on workflow after this workflow returns.
// It is NOT run inline here — the tail requires human-in-the-loop model selection and
// governance confirmation (rf verify --fail-on-unsupported may return exit code 4, 7).
// See meta.description for the operator note and research-foundry-swarm-workflow-spec.md §7.
//
// Workflow args may arrive as a JSON string from the Workflow tool.
// Always parse at the top before destructuring.
const parsedArgs = typeof args === 'string' ? JSON.parse(args) : args

export const meta = {
  name: 'research-foundry-swarm',
  description: 'Path B Claude Code-orchestrated swarm: reads a Research Foundry research brief, fans out domain-researcher and source-scout agents to discover source candidates, deduplicates results, then ingests each accepted candidate via `rf ingest` (guarded by `rf guard check`). Returns a manifest of ingested source cards. POST-RUN (not inline): run `rf extract`, `rf claim-map`, `rf synthesize`, `rf verify --fail-on-unsupported`, `rf bundle`, and `rf writeback` manually or via a follow-on workflow. Exit code 7 from `rf verify` means human council review is required before bundling.',
  phases: [
    { title: 'Plan' },
    { title: 'Discover' },
    { title: 'Dedup' },
    { title: 'Ingest' },
  ],
  whenToUse: 'Use when a Research Foundry run_id has a research_brief.md but no source cards yet, and you want a Claude Code agent swarm (not RF-native adapters) to perform discovery and populate runs/<run_id>/sources/. Requires an initialized RF workspace (`rf init` + `rf doctor` green). Always run `rf guard check` before invoking.',
}

// === Script body ===

const { run_id, profile, dry_run, timestamp } = parsedArgs

if (!run_id) {
  return {
    status: 'blocked',
    reason: 'missing_run_id',
    report: [],
    error: 'args.run_id is required. Pass the RF run identifier (e.g. "rf_run_20260613_topic").',
  }
}

const resolvedProfile = profile || 'personal'

if (dry_run === true) {
  return {
    status: 'dry_run',
    parsed_args: parsedArgs,
  }
}

// ── Phase 1: Plan ──────────────────────────────────────────────────────────────
// rf_discovery_lead reads the research brief and produces a structured source strategy.
phase('Plan')
log(`[research-foundry-swarm] Phase 1 — Plan: rf_discovery_lead reads brief for run "${run_id}"`)

const sourceStrategy = await agent(
  `Mode: A — Exploration only. Do NOT git add/commit/push/stash.

You are the RF discovery lead for run "${run_id}". Your job is to read the research brief
and produce a structured source strategy for the swarm.

Steps:
1. Read "runs/${run_id}/research_brief.md" (and "runs/${run_id}/swarm_plan.yaml" if it exists).
2. Extract the research question, key topics, required source types, and any constraints
   (sensitivity level, freshness window, domain restrictions).
3. Produce a DiscoveryStrategy object (see schema below).

Return a JSON object matching this schema exactly:
{
  "research_question": string,
  "key_topics": string[],          // 3-8 main topic areas to research
  "source_types": string[],        // e.g. ["paper", "web_page", "official_doc", "other"]
  "domain_legs": [                 // 2-4 independent research legs for parallel discovery
    {
      "leg_id": string,            // e.g. "leg-architecture", "leg-benchmarks"
      "focus": string,             // one sentence describing this leg's focus
      "search_queries": string[],  // 2-4 seed queries for this leg
      "preferred_source_types": string[]
    }
  ],
  "sensitivity": string,           // personal | public | work_internal | client_confidential
  "max_sources": number,           // recommended cap (suggest 5-15)
  "freshness_days": number         // max age in days (default 365)
}

Run directory: runs/${run_id}/
Profile: ${resolvedProfile}

Do NOT run any rf commands. Do NOT write any files. Return the JSON object only.`,
  {
    label: 'rf_discovery_lead',
    phase: 'Plan',
    agentType: 'codebase-explorer',
    model: 'sonnet',
    schema: {
      type: 'object',
      properties: {
        research_question: { type: 'string' },
        key_topics: { type: 'array', items: { type: 'string' } },
        source_types: { type: 'array', items: { type: 'string' } },
        domain_legs: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              leg_id: { type: 'string' },
              focus: { type: 'string' },
              search_queries: { type: 'array', items: { type: 'string' } },
              preferred_source_types: { type: 'array', items: { type: 'string' } },
            },
            required: ['leg_id', 'focus', 'search_queries'],
          },
        },
        sensitivity: { type: 'string' },
        max_sources: { type: 'number' },
        freshness_days: { type: 'number' },
      },
      required: ['research_question', 'key_topics', 'domain_legs'],
    },
  }
)

if (!sourceStrategy) {
  return {
    status: 'blocked',
    reason: 'plan_failed',
    report: [],
    error: `rf_discovery_lead returned null — could not parse research brief for run "${run_id}". Ensure runs/${run_id}/research_brief.md exists.`,
  }
}

const domainLegs = sourceStrategy.domain_legs || []
const maxSources = sourceStrategy.max_sources || 10

log(`[research-foundry-swarm] Plan complete — ${domainLegs.length} discovery legs, max ${maxSources} sources, sensitivity: ${sourceStrategy.sensitivity || resolvedProfile}`)

// ── Phase 2: Discover ──────────────────────────────────────────────────────────
// Parallel rf_domain_researcher + rf_source_scout agents per leg.
// Each returns structured source candidates with provenance.
phase('Discover')
log(`[research-foundry-swarm] Phase 2 — Discover: fanning out ${domainLegs.length} parallel discovery legs`)

const CANDIDATE_SCHEMA = {
  type: 'object',
  properties: {
    leg_id: { type: 'string' },
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          url_or_path: { type: 'string' },
          title: { type: 'string' },
          source_type: { type: 'string' },
          relevance_rationale: { type: 'string' },
          provenance: { type: 'string' },
          freshness_estimate: { type: 'string' },
        },
        required: ['url_or_path', 'title', 'source_type', 'relevance_rationale', 'provenance'],
      },
    },
  },
  required: ['leg_id', 'candidates'],
}

const discoveryResults = await parallel(
  domainLegs.map((leg, idx) => async () => {
    // Alternate between domain_researcher and source_scout personas for diversity.
    const isResearcher = idx % 2 === 0

    const legResult = await agent(
      `Mode: A — Exploration only. Do NOT git add/commit/push/stash.

You are the RF ${isResearcher ? 'domain researcher' : 'source scout'} for discovery leg "${leg.leg_id}".

Research context:
- Run: ${run_id}
- Research question: ${sourceStrategy.research_question}
- This leg focus: ${leg.focus}
- Seed queries: ${JSON.stringify(leg.search_queries)}
- Preferred source types: ${JSON.stringify(leg.preferred_source_types || sourceStrategy.source_types || [])}
- Sensitivity: ${sourceStrategy.sensitivity || resolvedProfile}
- Freshness window: ${sourceStrategy.freshness_days || 365} days
- Max candidates from this leg: ${Math.ceil(maxSources / domainLegs.length) + 2}

${isResearcher
  ? 'As domain researcher: use web search and document reads to find authoritative papers, official docs, and technical references directly relevant to this leg\'s focus. Prioritize depth over breadth — find 3-5 high-quality sources.'
  : 'As source scout: use web search to broadly survey the landscape for this leg\'s focus. Find web pages, blog posts, supplementary sources, and emerging work. Aim for 3-6 diverse sources.'
}

For each source found, record:
- url_or_path: the URL or local file path
- title: human-readable title
- source_type: one of paper | web_page | official_doc | other
- relevance_rationale: 1-2 sentences explaining relevance to the research question
- provenance: how you found it (search query used, link from another source, etc.)
- freshness_estimate: approximate publication/update date if visible (else "unknown")

Return the leg_id and candidates array only. Do NOT ingest or write any files.`,
      {
        label: `rf_${isResearcher ? 'domain_researcher' : 'source_scout'}_${leg.leg_id}`,
        phase: 'Discover',
        agentType: 'codebase-explorer',
        model: 'sonnet',
        schema: CANDIDATE_SCHEMA,
      }
    )

    return legResult
  })
)

// ── Phase 3: Dedup ─────────────────────────────────────────────────────────────
// Pure JS merge and deduplication of candidates from all legs.
// No agent needed — this is deterministic in-script logic (no FS, no shell).
phase('Dedup')
log('[research-foundry-swarm] Phase 3 — Dedup: merging and deduplicating candidates')

const allCandidates = []
const seenUrls = new Set()

for (const legResult of discoveryResults.filter(Boolean)) {
  const candidates = legResult.candidates || []
  for (const candidate of candidates) {
    const key = (candidate.url_or_path || '').trim().toLowerCase()
    if (!key) continue
    if (seenUrls.has(key)) {
      log(`[research-foundry-swarm] Dedup: skipping duplicate "${candidate.title || key}"`)
      continue
    }
    seenUrls.add(key)
    allCandidates.push(candidate)
  }
}

// Trim to maxSources
const acceptedCandidates = allCandidates.slice(0, maxSources)

log(`[research-foundry-swarm] Dedup complete — ${allCandidates.length} unique candidates, accepting top ${acceptedCandidates.length} (max: ${maxSources})`)

if (acceptedCandidates.length === 0) {
  return {
    status: 'needs_opus',
    reason: 'no_candidates',
    report: [{ phase: 'Dedup', candidates_found: 0 }],
    error: 'Discovery returned zero source candidates. Check research_brief.md, search connectivity, and leg focus queries.',
    strategy: sourceStrategy,
  }
}

// ── Phase 4: Ingest ────────────────────────────────────────────────────────────
// For each accepted candidate: run `rf guard check`, then `rf ingest`.
// Each ingest writes a schema-valid source card to runs/<run_id>/sources/src_*.md.
phase('Ingest')
log(`[research-foundry-swarm] Phase 4 — Ingest: ingesting ${acceptedCandidates.length} sources into run "${run_id}"`)

const ingestResults = await pipeline(
  acceptedCandidates,
  async (candidate) => {
    if (budget.remaining() < 60_000) {
      log(`[research-foundry-swarm] Ingest: budget low (${budget.remaining()} remaining) — skipping "${candidate.title}"`)
      return { skipped: true, reason: 'budget_low', candidate }
    }

    const result = await agent(
      `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash.

You are the RF ingest runner. Ingest one source candidate into the Research Foundry run.

Run: ${run_id}
Profile: ${resolvedProfile}
Source to ingest:
  url_or_path: ${candidate.url_or_path}
  title: ${candidate.title}
  source_type: ${candidate.source_type}
  relevance_rationale: ${candidate.relevance_rationale}
  provenance: ${candidate.provenance}

Steps (in order — stop on any non-zero exit code and report the error):

1. Run governance preflight:
   rf guard check --profile ${resolvedProfile}
   If exit code is non-zero, return { success: false, exit_code: <code>, step: "guard_check", error: <stderr> }.

2. Run ingest for this source:
   rf ingest "${candidate.url_or_path}" \\
     --run ${run_id} \\
     --source-type ${candidate.source_type} \\
     --sensitivity ${sourceStrategy.sensitivity || resolvedProfile}
   If exit code is non-zero, return { success: false, exit_code: <code>, step: "rf_ingest", error: <stderr> }.

3. On success (exit code 0):
   - Find the newly created source card file (runs/${run_id}/sources/src_*.md, most recent).
   - Return { success: true, source_card_path: "<path>", url_or_path: "${candidate.url_or_path}", title: "${candidate.title}", source_type: "${candidate.source_type}" }.

Do NOT run rf extract, rf claim-map, rf synthesize, rf verify, rf bundle, or rf writeback.
Do NOT git add/commit/push/stash.`,
      {
        label: `rf_ingest_${candidate.source_type}_${seenUrls.size}`,
        phase: 'Ingest',
        agentType: 'python-backend-engineer',
        model: 'sonnet',
        schema: {
          type: 'object',
          properties: {
            success: { type: 'boolean' },
            source_card_path: { type: 'string' },
            url_or_path: { type: 'string' },
            title: { type: 'string' },
            source_type: { type: 'string' },
            exit_code: { type: 'number' },
            step: { type: 'string' },
            error: { type: 'string' },
            skipped: { type: 'boolean' },
          },
          required: ['success'],
        },
      }
    )

    return result
  }
)

// ── Build manifest and return ──────────────────────────────────────────────────
const ingested = ingestResults.filter(r => r && r.success === true)
const failed = ingestResults.filter(r => r && r.success === false)
const skipped = ingestResults.filter(r => r && r.skipped === true)

log(`[research-foundry-swarm] Ingest complete — ${ingested.length} ingested, ${failed.length} failed, ${skipped.length} skipped`)

log('[research-foundry-swarm] POST-RUN NOTE: The deterministic tail is NOT run automatically. ' +
    'After reviewing the manifest, run: rf extract → rf claim-map → rf synthesize → ' +
    'rf verify --fail-on-unsupported → rf bundle → rf writeback. ' +
    'Exit code 4 = unsupported claim (fix in ledger). Exit code 7 = council review required.')

return {
  status: ingested.length > 0 ? 'complete' : 'needs_opus',
  run_id,
  profile: resolvedProfile,
  timestamp,
  manifest: {
    ingested_count: ingested.length,
    failed_count: failed.length,
    skipped_count: skipped.length,
    source_cards: ingested.map(r => ({
      path: r.source_card_path,
      url_or_path: r.url_or_path,
      title: r.title,
      source_type: r.source_type,
    })),
    failed_sources: failed.map(r => ({
      url_or_path: r.url_or_path,
      title: r.title,
      step: r.step,
      exit_code: r.exit_code,
      error: r.error,
    })),
  },
  strategy: sourceStrategy,
  post_run_commands: [
    `rf extract ${run_id} --model-profile rf_extract_cheap`,
    `rf claim-map ${run_id} --from extractions --out claims/claim_ledger.yaml`,
    `rf synthesize ${run_id} --report reports/report_draft.md --model-profile rf_synthesize_deep`,
    `rf verify ${run_id} --report reports/report_draft.md --claim-ledger claims/claim_ledger.yaml --fail-on-unsupported`,
    `rf bundle ${run_id} --verify --out evidence_bundle.yaml`,
    `rf writeback ${run_id} --targets meatywiki,skillmeat,ccdash --require-review`,
  ],
  report: [
    { phase: 'Plan', legs: domainLegs.length, strategy_summary: sourceStrategy.research_question },
    { phase: 'Discover', candidates_found: allCandidates.length, legs_run: discoveryResults.filter(Boolean).length },
    { phase: 'Dedup', unique_candidates: allCandidates.length, accepted: acceptedCandidates.length },
    { phase: 'Ingest', ingested: ingested.length, failed: failed.length, skipped: skipped.length },
  ],
}
