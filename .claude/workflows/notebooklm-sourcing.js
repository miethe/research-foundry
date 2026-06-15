// notebooklm-sourcing.js
//
// Drive NotebookLM (NLM) grounded research + cited Q&A for an RF run's research
// questions, then ingest the discovered references into Research Foundry as source
// cards. Purely additive — no Python/src changes. This is the standalone "sourcing"
// use case from docs/projects/research-foundry/notebooklm-integration-plan.md §3.1;
// it complements (does not replace) the future NotebookLMAdapter.
//
// Three phases: Plan (read the run's research brief → ordered question list),
// Source (parallel NLM research/ask per question → cited source candidates), and
// Ingest (pipeline `rf guard check` + `rf ingest` per deduped candidate → source cards).
// Dedup between Source and Ingest is plain in-script JS (merge by locator), no agent.
//
// PRECONDITION (out-of-band): the operator has run `notebooklm login` and the CLI is
// authenticated (NLM has no REST API; the agents wrap the `notebooklm` CLI). NLM is a
// cloud, online-only, non-deterministic engine — every NLM-derived card is tagged
// requires_network / non-reproducible. NLM auth is a documented PRECONDITION, NOT a
// Mode D gate. DESTRUCTIVE NLM ops (delete) are forbidden in this workflow.
//
// The deterministic tail (extract → claim-map → synthesize → verify → bundle →
// writeback) is a POST-RUN step run by Opus/operator after reviewing the manifest;
// it is NOT run inline here. See post_run_commands in the return value and
// notebooklm-sourcing-workflow-spec.md.
//
// Workflow args may arrive as a JSON string from the Workflow tool — parse at the top.
const a = typeof args === 'string' ? JSON.parse(args) : (args || {})

export const meta = {
  name: 'notebooklm-sourcing',
  description: 'Drive NotebookLM grounded research + cited Q&A for an RF run\'s research questions, then ingest the results into Research Foundry as source cards. Plan reads runs/<run_id>/research_brief.md and produces an ordered (primary+secondary) question list; Source fans out parallel python-backend-engineer agents that run `notebooklm source add-research`/`notebooklm ask`/`notebooklm source fulltext --json` and map each NLM reference into a gpt_researcher-shaped source candidate (degrades to empty on missing auth/CLI, never fails); Ingest pipelines each deduped candidate through `rf guard check` then `rf ingest <locator> --run <run_id> --source-type notebooklm`, tagging each card requires_network / non-reproducible. Returns a custom source manifest. POST-RUN (not inline): rf extract → claim-map → synthesize → verify → bundle → writeback. PRECONDITION: operator has run `notebooklm login` out-of-band; NLM has no REST API. DESTRUCTIVE NLM ops (delete) are forbidden.',
  phases: [
    { title: 'Plan' },
    { title: 'Source' },
    { title: 'Ingest' },
  ],
  whenToUse: 'Use when an RF run_id has a research_brief.md and you want NotebookLM grounded research / cited Q&A to seed the run\'s source cards. Requires an initialized RF workspace (`rf init` + `rf doctor` green) and an authenticated NotebookLM CLI (`notebooklm login` run out-of-band). Complements the RF swarm: NLM provides grounded, citation-attached discovery; RF remains the governance and claim-ledger authority.',
}

// === Script body ===

const runId = a.run_id
const resolvedProfile = a.profile || 'personal'
const mode = a.mode === 'fast' ? 'fast' : 'deep'
const maxSources = typeof a.max_sources === 'number' && a.max_sources > 0 ? a.max_sources : 12

// NotebookLM correlation inputs. notebook_id is OPTIONAL — when absent it is resolved
// through `rf notebooklm resolve` (the correlation CLI) at the end of the Plan phase.
// project scopes the correlation registry; notebook_mode selects how the notebook is
// correlated to the run (project | run | explicit). notebookId is `let` because the
// resolve step may populate it.
const project = typeof a.project === 'string' && a.project.trim().length > 0 ? a.project.trim() : null
const NOTEBOOK_MODES = ['project', 'run', 'explicit']
const notebookMode = NOTEBOOK_MODES.includes(a.notebook_mode) ? a.notebook_mode : null
let notebookId = a.notebook_id || null

// Dry-run guard — return the parsed args without spawning any agents.
if (a.dry_run === true) {
  return { status: 'dry_run', parsed_args: a }
}

// Required-arg validation — return blocked, never throw.
const missing = []
if (!runId) missing.push('run_id')
if (missing.length > 0) {
  return {
    status: 'blocked',
    reason: 'missing_args',
    missing,
    run_id: runId || null,
    profile: resolvedProfile,
    timestamp: a.timestamp,
    notebook_id: notebookId,
    manifest: {
      ingested_count: 0,
      failed_count: 0,
      skipped_count: 0,
      source_cards: [],
      notebook_id: notebookId,
    },
    post_run_commands: [],
    report: [],
    error: 'args.run_id is required. Pass the RF run identifier (e.g. "rf_run_20260613_topic").',
  }
}

// ── Phase 1: Plan ────────────────────────────────────────────────────────────────
// ONE read-only codebase-explorer (Mode A) reads the run's research brief and returns
// an ordered question list (primary + secondary), sensitivity, and max_sources. No NLM.
phase('Plan')
log(`[notebooklm-sourcing] Phase 1 — Plan: reading research brief for run "${runId}" (mode: ${mode})`)

const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    research_question: { type: 'string' },
    questions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rank: { type: 'number' },
          tier: { type: 'string' },     // "primary" | "secondary"
          question: { type: 'string' },
        },
        required: ['question'],
      },
    },
    sensitivity: { type: 'string' },     // personal | public | work_internal | client_confidential
    max_sources: { type: 'number' },
  },
  required: ['research_question', 'questions'],
}

const providedQuestions = Array.isArray(a.questions)
  ? a.questions.filter(q => typeof q === 'string' && q.trim().length > 0)
  : []

const plan = await agent(
  `Mode: A — Exploration only. Do NOT git add/commit/push/stash. Do NOT write any files.

You are the RF sourcing planner for run "${runId}". Your job is to read the research brief
and produce an ordered question list for grounded NotebookLM research. Do NOT run any
notebooklm or rf commands — this is read-only planning.

Steps:
1. Locate and read the run's research brief. The canonical path is
   "runs/${runId}/research_brief.md". If it is missing, inspect the run directory
   structure under "runs/${runId}/" first (e.g. list it) to find the brief; also read
   "runs/${runId}/swarm_plan.yaml" and "runs/${runId}/run.yaml" if present for the
   research question, sub-questions, and sensitivity.
2. Extract the primary research_question and an ordered list of research questions
   (primary first, then secondary/supporting). Aim for 3-${maxSources} questions total.
${providedQuestions.length > 0
    ? `   The operator has ALSO supplied these questions verbatim — include them, ranked first as "primary", before any you derive from the brief:\n   ${JSON.stringify(providedQuestions)}`
    : '   Derive the question list entirely from the brief.'}
3. Determine the run's sensitivity (personal | public | work_internal | client_confidential)
   from the brief/run.yaml; default to "${resolvedProfile}" if unstated.
4. Recommend a max_sources cap (cap at ${maxSources}).

Return a JSON object matching this schema exactly:
{
  "research_question": string,
  "questions": [ { "rank": number, "tier": "primary"|"secondary", "question": string } ],
  "sensitivity": string,
  "max_sources": number
}

Run directory: runs/${runId}/
Profile: ${resolvedProfile}

Do NOT run any notebooklm or rf commands. Do NOT write any files. Return the JSON object only.`,
  {
    label: 'nlm_sourcing_planner',
    phase: 'Plan',
    agentType: 'codebase-explorer',
    model: 'sonnet',
    schema: PLAN_SCHEMA,
  }
)

if (!plan) {
  return {
    status: 'blocked',
    reason: 'plan_failed',
    run_id: runId,
    profile: resolvedProfile,
    timestamp: a.timestamp,
    notebook_id: notebookId,
    manifest: {
      ingested_count: 0,
      failed_count: 0,
      skipped_count: 0,
      source_cards: [],
      notebook_id: notebookId,
    },
    post_run_commands: [],
    report: [{ phase: 'Plan', questions: 0 }],
    error: `nlm_sourcing_planner returned null — could not read the research brief for run "${runId}". Ensure runs/${runId}/research_brief.md exists.`,
  }
}

const sensitivity = plan.sensitivity || resolvedProfile
const planMax = typeof plan.max_sources === 'number' && plan.max_sources > 0
  ? Math.min(plan.max_sources, maxSources)
  : maxSources

// Ordered question list, capped at the source budget.
const orderedQuestions = (plan.questions || [])
  .map((q, idx) => ({
    rank: typeof q.rank === 'number' ? q.rank : idx + 1,
    tier: q.tier || (idx === 0 ? 'primary' : 'secondary'),
    question: typeof q === 'string' ? q : q.question,
  }))
  .filter(q => q.question && q.question.trim().length > 0)
  .slice(0, planMax)

log(`[notebooklm-sourcing] Plan complete — ${orderedQuestions.length} questions (cap ${planMax}), sensitivity: ${sensitivity}`)

if (orderedQuestions.length === 0) {
  return {
    status: 'needs_opus',
    reason: 'no_questions',
    run_id: runId,
    profile: resolvedProfile,
    timestamp: a.timestamp,
    notebook_id: notebookId,
    manifest: {
      ingested_count: 0,
      failed_count: 0,
      skipped_count: 0,
      source_cards: [],
      notebook_id: notebookId,
    },
    post_run_commands: [],
    report: [{ phase: 'Plan', questions: 0, research_question: plan.research_question }],
    error: 'Plan returned zero research questions. Check runs/<run_id>/research_brief.md content.',
  }
}

// ── Resolve notebook (correlation CLI) ───────────────────────────────────────────
// notebook_id is OPTIONAL. When absent, resolve it through the correlation CLI so the
// Source legs query a stable, run/project-correlated notebook. This runs a Bash-capable
// python-backend-engineer agent (not the read-only Plan inspector) because resolution may
// CREATE the notebook (`rf notebooklm resolve ... --create`). It DEGRADES — if NLM is
// unavailable / unauthenticated, the agent returns resolved:false and we hand back to Opus
// with status 'needs_opus' (clear reason); it NEVER throws or fails the pipeline.
let notebookSource = notebookId ? 'explicit' : null
if (!notebookId) {
  phase('Plan')
  log(`[notebooklm-sourcing] Resolve: no notebook_id provided — resolving via \`rf notebooklm resolve\` (mode: ${notebookMode || 'default'}, project: ${project || 'inferred'})`)

  const RESOLVE_SCHEMA = {
    type: 'object',
    properties: {
      resolved: { type: 'boolean' },
      notebook_id: { type: 'string' },
      notebook_title: { type: 'string' },
      project: { type: 'string' },
      mode: { type: 'string' },
      reason: { type: 'string' },
    },
    required: ['resolved'],
  }

  const projectFlag = project ? ` --project ${project}` : ''
  const modeFlag = notebookMode ? ` --mode ${notebookMode}` : ''

  const resolved = await agent(
    `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash. Do NOT write or edit any files.

You are the RF NotebookLM correlation resolver for run "${runId}". No notebook_id was
provided, so resolve (and create if needed) the run's correlated NotebookLM notebook through
the RF correlation CLI, then return its id. This is the ONLY thing you do — no sourcing, no
ingest, no generation.

DEGRADE CONTRACT (critical): NotebookLM is online-only and may be unauthenticated or
offline. If \`rf notebooklm resolve\` fails for ANY reason (NLM unavailable, auth/cookie
error, RPC error, non-zero exit), DO NOT fail. Return
{ "resolved": false, "reason": "<one-line cause>" } with NO notebook_id. NEVER run
\`notebooklm delete\` / \`notebooklm notebook delete\` or any destructive op.

Steps (stop and degrade on any non-zero exit code):

1. Resolve (and create on miss) the correlated notebook:
   \`rf notebooklm resolve --run ${runId}${projectFlag}${modeFlag} --create\`
   This reads the correlation registry (registries/notebooklm/notebooks.yaml), maps the run
   to its notebook per the correlation mode, and creates the notebook if it does not yet
   exist. Parse the printed/JSON output for the resolved notebook id, title, project, and
   mode.

2. On exit code 0 with a notebook id, return EXACTLY:
   { "resolved": true, "notebook_id": "<id>", "notebook_title": "<title>", "project": "<project-slug>", "mode": "<mode>" }

3. On ANY failure (non-zero exit, no id, NLM unavailable), return EXACTLY:
   { "resolved": false, "reason": "<what failed, one line>" }

Do NOT run any notebooklm generate/ask/source/download command. Do NOT run any other rf
command. Do NOT write any files. Do NOT git add/commit/push/stash. Return the JSON object only.`,
    {
      label: 'nlm_sourcing_resolve',
      phase: 'Plan',
      agentType: 'python-backend-engineer',
      model: 'sonnet',
      schema: RESOLVE_SCHEMA,
    }
  )

  if (!resolved || resolved.resolved !== true || !resolved.notebook_id) {
    const reason = (resolved && resolved.reason) || 'rf notebooklm resolve returned no notebook_id'
    log(`[notebooklm-sourcing] Resolve: degraded — ${reason}. NLM is likely unauthenticated/offline; handing back to Opus.`)
    return {
      status: 'needs_opus',
      reason: 'notebook_unresolved',
      run_id: runId,
      profile: resolvedProfile,
      timestamp: a.timestamp,
      notebook_id: null,
      manifest: {
        ingested_count: 0,
        failed_count: 0,
        skipped_count: 0,
        source_cards: [],
        notebook_id: null,
      },
      post_run_commands: [],
      report: [
        { phase: 'Plan', questions: orderedQuestions.length, research_question: plan.research_question, sensitivity, notebook_resolved: false },
      ],
      error: `Could not resolve a NotebookLM notebook for run "${runId}" (${reason}). ` +
        'Ensure `notebooklm login` is authenticated, then either rerun (NLM will be auto-resolved) ' +
        'or pass an explicit notebook_id.',
    }
  }

  notebookId = resolved.notebook_id
  notebookSource = `resolved:${resolved.mode || notebookMode || 'default'}`
  log(`[notebooklm-sourcing] Resolve complete — notebook_id "${notebookId}" (title: ${resolved.notebook_title || 'n/a'}, project: ${resolved.project || project || 'n/a'}, mode: ${resolved.mode || notebookMode || 'default'})`)
}

// ── Phase 2: Source ──────────────────────────────────────────────────────────────
// parallel() over the questions. Each leg is a python-backend-engineer agent that, AT
// RUNTIME, drives the notebooklm CLI for grounded research / cited Q&A and maps each NLM
// reference into a gpt_researcher-shaped source candidate. It DEGRADES (empty candidates
// + note) on missing auth/CLI — it never fails the run. Budget guard: skip a leg when
// budget.remaining() < 40_000.
phase('Source')
log(`[notebooklm-sourcing] Phase 2 — Source: fanning out ${orderedQuestions.length} NotebookLM research legs (notebook_id: ${notebookId || 'discovery'})`)

const CANDIDATE_LEG_SCHEMA = {
  type: 'object',
  properties: {
    rank: { type: 'number' },
    question: { type: 'string' },
    status: { type: 'string' },          // ok | degraded | skipped_budget | skipped_no_auth
    degraded: { type: 'boolean' },
    note: { type: 'string' },
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          candidate_id: { type: 'string' },
          title: { type: 'string' },
          source_type: { type: 'string' },          // always "notebook"
          locator: {
            type: 'object',
            properties: {
              url: { type: 'string' },
              notebook_source_id: { type: 'string' },
            },
          },
          discovery_method: { type: 'string' },      // "notebook_knowledge"
          label: { type: 'string' },
          notes: { type: 'string' },
          quote: { type: 'string' },
        },
        required: ['candidate_id', 'title', 'source_type', 'locator', 'discovery_method'],
      },
    },
  },
  required: ['question', 'status', 'candidates'],
}

const sourceResults = await parallel(
  orderedQuestions.map((q, idx) => async () => {
    if (budget.remaining() < 40_000) {
      log(`[notebooklm-sourcing] Source: budget low (${budget.remaining()} remaining) — skipping question #${idx + 1}`)
      return {
        rank: q.rank,
        question: q.question,
        status: 'skipped_budget',
        degraded: true,
        note: `Skipped — budget.remaining() (${budget.remaining()}) below 40000 threshold.`,
        candidates: [],
      }
    }

    const nbFlag = notebookId ? ` -n ${notebookId}` : ''
    const discoveryClause = notebookId
      ? `A notebook_id ("${notebookId}") was provided — query it directly with \`notebooklm ask\`.`
      : `No notebook_id was provided — first DISCOVER grounded sources with \`notebooklm source add-research\`, then query.`

    const legResult = await agent(
      `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash.

You are the RF NotebookLM sourcing runner for ONE research question. Drive the
\`notebooklm\` CLI to obtain grounded, citation-attached evidence for the question, then
map each NLM reference into a source-candidate dict. NotebookLM is online-only and
non-deterministic; the operator has run \`notebooklm login\` out-of-band.

Run: ${runId}
Profile: ${resolvedProfile}
Sensitivity: ${sensitivity}
Research mode: ${mode}
Question (rank ${q.rank}, ${q.tier}): "${q.question}"
${discoveryClause}

DEGRADE CONTRACT (critical): If \`notebooklm\` is not installed, not authenticated, or any
command errors (auth/cookie error, rate limit, RPC error), DO NOT fail. Return
{ "rank": ${q.rank}, "question": "<the question>", "status": "degraded" (or "skipped_no_auth"
for auth failures), "degraded": true, "note": "<what failed>", "candidates": [] }.
Run a cheap auth probe FIRST: \`notebooklm status\` (exit 0 = authenticated). If it is not
authenticated, immediately return the degraded shape with status "skipped_no_auth" and an
EMPTY candidates array — do NOT attempt further NLM calls. NEVER run \`notebooklm delete\`
or \`notebooklm notebook delete\` — destructive ops are forbidden.

Steps (run each EXACTLY as written; quote the question; stop and degrade on persistent error):

1. Auth probe: \`notebooklm status\`  (exit 0 = authenticated; else degrade as above).

${notebookId
  ? `2. Cited Q&A against the provided notebook:
   \`notebooklm ask "${q.question}" --json${nbFlag}\`
   Parse the JSON: capture \`answer\` (telemetry only — NEVER a report claim) and the
   \`references\` array (each has source_id, citation_number, cited_text).`
  : `2. Grounded web research (discovery), then cited Q&A:
   \`notebooklm source add-research "${q.question}" --mode ${mode} --json\`
   (this discovers + imports grounded sources; for --mode deep it may take 2-5 min).
   Then ask against the new sources:
   \`notebooklm ask "${q.question}" --json\`
   Parse the JSON: capture \`answer\` (telemetry only) and the \`references\` array.`}

3. For EACH reference, fetch quote-level evidence (best-effort; skip on error):
   \`notebooklm source fulltext <source_id> --json\`
   Use the returned \`content\`/\`cited_text\` to populate the candidate's "quote" field
   (a short verbatim passage). If fulltext fails, omit "quote".

4. Map each NLM reference into a source-candidate dict matching the RF gpt_researcher
   candidate shape EXACTLY:
   {
     "candidate_id": "<stable id, e.g. nlm-<source_id-or-index>>",
     "title": "<reference title or a short descriptor>",
     "source_type": "notebook",
     "locator": { "url": "<source url if known>", "notebook_source_id": "<NLM source_id>" },
     "discovery_method": "notebook_knowledge",
     "label": "<one-line relevance label tying it to the question>",
     "notes": "NotebookLM-grounded (cited_text #<citation_number>); non-reproducible (online).",
     "quote": "<verbatim passage from fulltext, if available>"
   }
   Include "url" in locator when the reference resolves to a real URL; otherwise include
   only "notebook_source_id". At least one of url / notebook_source_id MUST be present.

5. Return a JSON object EXACTLY:
   {
     "rank": ${q.rank},
     "question": "${q.question}",
     "status": "ok",
     "degraded": false,
     "note": "<optional brief note>",
     "candidates": [ <the mapped candidate dicts> ]
   }

Cap candidates from this leg at ${Math.max(2, Math.ceil(planMax / orderedQuestions.length) + 2)}.
Do NOT run rf commands. Do NOT write any files. Do NOT git add/commit/push/stash. Do NOT
delete any notebook or source. Return the JSON object only.`,
      {
        label: `nlm_source_q${idx + 1}`,
        phase: 'Source',
        agentType: 'python-backend-engineer',
        model: 'sonnet',
        schema: CANDIDATE_LEG_SCHEMA,
      }
    )

    return legResult
  })
)

// ── Dedup (plain JS — no agent) ──────────────────────────────────────────────────
// Merge all leg candidates and dedup by locator (url first, then notebook_source_id).
// Mirrors the swarm's in-script Dedup: no FS, no shell, no agent.
log('[notebooklm-sourcing] Dedup: merging and deduplicating NotebookLM candidates (plain JS)')

const mergedCandidates = []
const seenKeys = new Set()
let degradedLegs = 0
let skippedLegs = 0

for (const leg of sourceResults.filter(Boolean)) {
  if (leg.status === 'skipped_budget') skippedLegs++
  if (leg.degraded === true || leg.status === 'degraded' || leg.status === 'skipped_no_auth') degradedLegs++
  const candidates = leg.candidates || []
  for (const c of candidates) {
    const loc = c.locator || {}
    const key = ((loc.url || loc.notebook_source_id || c.candidate_id || '') + '').trim().toLowerCase()
    if (!key) continue
    if (seenKeys.has(key)) {
      log(`[notebooklm-sourcing] Dedup: skipping duplicate "${c.title || key}"`)
      continue
    }
    seenKeys.add(key)
    mergedCandidates.push(c)
  }
}

const acceptedCandidates = mergedCandidates.slice(0, planMax)

log(`[notebooklm-sourcing] Dedup complete — ${mergedCandidates.length} unique candidates, accepting top ${acceptedCandidates.length} (cap ${planMax}); ${degradedLegs} degraded leg(s), ${skippedLegs} budget-skipped leg(s)`)

if (acceptedCandidates.length === 0) {
  return {
    status: 'needs_opus',
    reason: 'no_candidates',
    run_id: runId,
    profile: resolvedProfile,
    timestamp: a.timestamp,
    notebook_id: notebookId,
    manifest: {
      ingested_count: 0,
      failed_count: 0,
      skipped_count: skippedLegs,
      source_cards: [],
      notebook_id: notebookId,
    },
    post_run_commands: [],
    report: [
      { phase: 'Plan', questions: orderedQuestions.length, research_question: plan.research_question },
      { phase: 'Source', legs_run: sourceResults.filter(Boolean).length, degraded_legs: degradedLegs, skipped_legs: skippedLegs, candidates_found: 0 },
    ],
    error: 'NotebookLM sourcing returned zero candidates (NLM likely unauthenticated/offline, or no grounded references found). Run `notebooklm login`, verify `notebooklm status`, then rerun.',
  }
}

// ── Phase 3: Ingest ──────────────────────────────────────────────────────────────
// pipeline() over the deduped candidates. Each item → python-backend-engineer agent that,
// AT RUNTIME, runs `rf guard check` then `rf ingest <locator> --run <run_id>
// --source-type notebooklm` and tags the resulting card requires_network / non-reproducible.
// Budget guard: skip `rf guard check` (i.e. the whole ingest leg) when budget.remaining() < 60_000.
phase('Ingest')
log(`[notebooklm-sourcing] Phase 3 — Ingest: ingesting ${acceptedCandidates.length} NotebookLM source(s) into run "${runId}"`)

const INGEST_SCHEMA = {
  type: 'object',
  properties: {
    success: { type: 'boolean' },
    source_card_path: { type: 'string' },
    candidate_id: { type: 'string' },
    locator: { type: 'string' },
    title: { type: 'string' },
    exit_code: { type: 'number' },
    step: { type: 'string' },
    error: { type: 'string' },
    skipped: { type: 'boolean' },
    note: { type: 'string' },
  },
  required: ['success'],
}

const ingestResults = await pipeline(
  acceptedCandidates,
  async (candidate) => {
    if (budget.remaining() < 60_000) {
      log(`[notebooklm-sourcing] Ingest: budget low (${budget.remaining()} remaining) — skipping "${candidate.title}"`)
      return { success: false, skipped: true, reason: 'budget_low', candidate_id: candidate.candidate_id, title: candidate.title, note: 'skipped_budget' }
    }

    const loc = candidate.locator || {}
    const locator = loc.url || loc.notebook_source_id || candidate.candidate_id

    const result = await agent(
      `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash.

You are the RF ingest runner. Ingest ONE NotebookLM-derived source candidate into the
Research Foundry run as a source card. NotebookLM output is non-reproducible (online); the
resulting card MUST be tagged accordingly.

Run: ${runId}
Profile: ${resolvedProfile}
Sensitivity: ${sensitivity}
Candidate:
  candidate_id: ${candidate.candidate_id}
  title: ${candidate.title}
  locator (url|notebook_source_id): ${locator}
  discovery_method: ${candidate.discovery_method || 'notebook_knowledge'}
  label: ${candidate.label || ''}
  notes: ${candidate.notes || ''}

Steps (in order — stop on any non-zero exit code and report the error; NEVER delete anything):

1. Governance preflight:
   \`rf guard check --profile ${resolvedProfile} --run ${runId} --sensitivity ${sensitivity}\`
   If exit code is non-zero (3 = governance violation), return
   { "success": false, "exit_code": <code>, "step": "guard_check", "candidate_id": "${candidate.candidate_id}", "title": "${candidate.title}", "error": "<stderr>" }.

2. Ingest this source as a source card:
   \`rf ingest "${locator}" --run ${runId} --source-type notebooklm --sensitivity ${sensitivity} --title "${(candidate.title || '').replace(/"/g, '\\"')}"\`
   (\`--source-type\` is a free-form option; "notebooklm" is the correct value here.)
   If exit code is non-zero, return
   { "success": false, "exit_code": <code>, "step": "rf_ingest", "candidate_id": "${candidate.candidate_id}", "title": "${candidate.title}", "error": "<stderr>" }.
   The command prints the created source card path on its last line — capture it.

3. Tag the card as non-reproducible: open the newly created source card file
   (the path printed by \`rf ingest\`, under runs/${runId}/sources/) and ensure its YAML
   front matter records that this is NotebookLM-grounded and requires network:
     - add/ensure  usage.requires_network: true
     - add/ensure  trust.reliability_notes: "NotebookLM-grounded; non-reproducible (online)"
   Edit ONLY this one source card file. Do NOT touch any other file. Do NOT
   git add/commit/push/stash.

4. On success (exit code 0), return
   { "success": true, "source_card_path": "<path>", "candidate_id": "${candidate.candidate_id}", "locator": "${locator}", "title": "${candidate.title}" }.

Do NOT run rf extract, rf claim-map, rf synthesize, rf verify, rf bundle, or rf writeback.
Do NOT run any notebooklm command. Do NOT delete any notebook, source, or file.
Do NOT git add/commit/push/stash.`,
      {
        label: `nlm_ingest_${seenKeys.size}_${candidate.candidate_id}`,
        phase: 'Ingest',
        agentType: 'python-backend-engineer',
        model: 'sonnet',
        schema: INGEST_SCHEMA,
      }
    )

    return result
  }
)

// ── Build manifest and return ────────────────────────────────────────────────────
const ingested = ingestResults.filter(r => r && r.success === true)
const failed = ingestResults.filter(r => r && r.success === false && r.skipped !== true)
const skipped = ingestResults.filter(r => r && r.skipped === true)

log(`[notebooklm-sourcing] Ingest complete — ${ingested.length} ingested, ${failed.length} failed, ${skipped.length} skipped`)

log('[notebooklm-sourcing] POST-RUN NOTE: the deterministic tail is NOT run automatically. ' +
    'After reviewing the manifest, run: rf extract → rf claim-map → rf synthesize → ' +
    'rf verify --fail-on-unsupported → rf bundle → rf writeback. ' +
    'NLM-derived cards are tagged requires_network / non-reproducible. ' +
    'Exit code 4 from rf verify = unsupported claim; exit code 7 = council review required.')

return {
  status: ingested.length > 0 ? 'complete' : 'needs_opus',
  run_id: runId,
  profile: resolvedProfile,
  timestamp: a.timestamp,
  manifest: {
    ingested_count: ingested.length,
    failed_count: failed.length,
    skipped_count: skipped.length + skippedLegs,
    source_cards: ingested.map(r => ({
      path: r.source_card_path,
      candidate_id: r.candidate_id,
      locator: r.locator,
      title: r.title,
      source_type: 'notebooklm',
    })),
    failed_sources: failed.map(r => ({
      candidate_id: r.candidate_id,
      title: r.title,
      step: r.step,
      exit_code: r.exit_code,
      error: r.error,
    })),
    notebook_id: notebookId,
    notebook_source: notebookSource,
  },
  notebook_id: notebookId,
  notebook_source: notebookSource,
  post_run_commands: [
    `rf extract ${runId} --model-profile rf_extract_cheap`,
    `rf claim-map ${runId}`,
    `rf synthesize ${runId} --report reports/report_draft.md --model-profile rf_synthesize_deep`,
    `rf verify ${runId} --report reports/report_draft.md --claim-ledger claims/claim_ledger.yaml --fail-on-unsupported`,
    `rf bundle ${runId} --verify --out evidence_bundle.yaml`,
    `rf writeback ${runId} --targets meatywiki,skillmeat,ccdash --require-review`,
  ],
  report: [
    { phase: 'Plan', questions: orderedQuestions.length, research_question: plan.research_question, sensitivity, notebook_source: notebookSource },
    { phase: 'Source', legs_run: sourceResults.filter(Boolean).length, degraded_legs: degradedLegs, skipped_legs: skippedLegs, candidates_found: mergedCandidates.length, accepted: acceptedCandidates.length },
    { phase: 'Ingest', ingested: ingested.length, failed: failed.length, skipped: skipped.length },
  ],
}
