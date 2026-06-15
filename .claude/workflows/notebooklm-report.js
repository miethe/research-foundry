// notebooklm-report.js
//
// Sits between `rf synthesize` (stage 7) and `rf verify` (stage 8) of a Research
// Foundry run. From a synthesized run it drives NotebookLM grounded artifact
// generation (briefing-doc report, mind-map, data-table) and attaches the results
// to the run as NON-AUTHORITATIVE artifacts.
//
// CRITICAL governance rule (also enforced via the inner agent prompts): the generated
// NotebookLM artifacts are NEVER spliced into runs/<run_id>/reports/report_draft.md.
// They are recorded in runs/<run_id>/evidence_bundle.yaml under
// artifacts.notebooklm_report and the files are written under runs/<run_id>/nlm_artifacts/.
// Any prose from these artifacts that is later to be cited in a report must FIRST become
// a source card (3.1) and earn a [claim:<id>]. This workflow never edits the report draft.
//
// PRECONDITION (out-of-band, NOT a Mode D gate): the operator has authenticated NotebookLM
// via `notebooklm login` and the run's sources are already uploaded to the notebook held
// in args.notebook_id. NLM auth is a documented precondition, not a runtime sign-off.
//
// Destructive NLM ops (delete) are FORBIDDEN in this workflow.
//
// Workflow args may arrive as a JSON string from the Workflow tool.
// Always parse at the top before destructuring.
const a = typeof args === 'string' ? JSON.parse(args) : (args || {})

export const meta = {
  name: 'notebooklm-report',
  description: 'Between `rf synthesize` and `rf verify`, generate NotebookLM grounded artifacts (briefing-doc report, mind-map, data-table) from a synthesized RF run and attach them as NON-AUTHORITATIVE artifacts. Prepare confirms the run dir layout (report_draft.md, claim_ledger.yaml) and resolves the notebook id; Generate fans out `notebooklm generate ...` per requested format capturing task_ids; Integrate waits for and downloads each artifact into runs/<run_id>/nlm_artifacts/ and records it in evidence_bundle.yaml under artifacts.notebooklm_report. Artifacts are NEVER merged into report_draft.md — any prose to be cited must first become a source card and earn a [claim:<id>]. NLM auth is an out-of-band precondition (notebooklm login). Destructive NLM ops are forbidden.',
  phases: [
    { title: 'Prepare' },
    { title: 'Generate' },
    { title: 'Integrate' },
  ],
  whenToUse: 'Use after `rf synthesize` has produced runs/<run_id>/reports/report_draft.md and before `rf verify`, when you want NotebookLM-grounded supporting artifacts (briefing-doc, mind-map, data-table) attached to the run as non-authoritative evidence. Requires the run sources already uploaded to a notebook (args.notebook_id) and `notebooklm login` completed out-of-band.',
}

// === Script body ===

// ── Arg parsing + early-return guards ───────────────────────────────────────────

// Dry-run guard: return the parsed args without spawning any agents.
if (a.dry_run === true) {
  return {
    status: 'dry_run',
    parsed_args: a,
  }
}

// Required-arg validation: never throw — return a blocked status with the missing list.
// notebook_id is OPTIONAL — when absent it is resolved via the correlation CLI in Prepare.
const missing = []
if (!a.run_id) missing.push('run_id')

if (missing.length > 0) {
  return {
    status: 'blocked',
    reason: 'missing_args',
    missing,
    run_id: a.run_id || null,
    notebook_id: a.notebook_id || null,
    timestamp: a.timestamp,
    artifacts: [],
    bundle_updated: false,
    report: [{ phase: 'Prepare', error: `Missing required args: ${missing.join(', ')}` }],
  }
}

const runId = a.run_id

// NotebookLM correlation inputs. notebook_id is OPTIONAL — when absent it is resolved
// through `rf notebooklm resolve` (the correlation CLI) at the start of the Prepare phase.
// project scopes the correlation registry; notebook_mode selects how the notebook is
// correlated to the run (project | run | explicit). notebookId is `let` because the resolve
// step may populate it.
const project = typeof a.project === 'string' && a.project.trim().length > 0 ? a.project.trim() : null
const NOTEBOOK_MODES = ['project', 'run', 'explicit']
const notebookMode = NOTEBOOK_MODES.includes(a.notebook_mode) ? a.notebook_mode : null
let notebookId = a.notebook_id || null
let notebookSource = notebookId ? 'explicit' : null

// Normalize and validate the requested formats against the allowed set.
const ALLOWED_FORMATS = ['briefing-doc', 'mind-map', 'data-table']
const requestedFormats = Array.isArray(a.formats) && a.formats.length > 0
  ? a.formats.filter((f) => ALLOWED_FORMATS.includes(f))
  : ['briefing-doc', 'mind-map']

const dataTableDesc = a.data_table_desc || ''

// Per-format leg cost hint (tokens). NLM generation legs are guarded below.
const LEG_COST = 50_000

// Per-format static metadata: the download type token and the file extension.
// briefing-doc → report (.md); mind-map → mind-map (.json); data-table → data-table (.csv).
const FORMAT_META = {
  'briefing-doc': { downloadType: 'report', ext: 'md', sync: false },
  'mind-map': { downloadType: 'mind-map', ext: 'json', sync: true },
  'data-table': { downloadType: 'data-table', ext: 'csv', sync: false },
}

// ── Phase 1: Prepare ─────────────────────────────────────────────────────────────
// Resolve the notebook (correlation CLI) when notebook_id is absent, then the read-only
// codebase-explorer (Mode A) confirms the run dir layout. The resolve agent is Bash-capable
// (python-backend-engineer) because resolution may CREATE the notebook
// (`rf notebooklm resolve ... --create`); the inspector that follows is read-only.
phase('Prepare')

// Resolve notebook_id via the correlation CLI when it was not passed in. DEGRADES — if NLM
// is unavailable/unauthenticated the agent returns resolved:false and we hand back to Opus
// with status 'blocked' (clear reason); it NEVER throws or fails the pipeline.
if (!notebookId) {
  log(`[notebooklm-report] Prepare — Resolve: no notebook_id provided — resolving via \`rf notebooklm resolve\` (mode: ${notebookMode || 'default'}, project: ${project || 'inferred'})`)

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
the RF correlation CLI, then return its id. This is the ONLY thing you do — no generation, no
download, no bundle edit.

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

Do NOT run any notebooklm generate/download command. Do NOT run any other rf command. Do NOT
write any files. Do NOT git add/commit/push/stash. Return the JSON object only.`,
    {
      label: 'nlm_report_resolve',
      phase: 'Prepare',
      agentType: 'python-backend-engineer',
      model: 'sonnet',
      schema: RESOLVE_SCHEMA,
    }
  )

  if (!resolved || resolved.resolved !== true || !resolved.notebook_id) {
    const reason = (resolved && resolved.reason) || 'rf notebooklm resolve returned no notebook_id'
    log(`[notebooklm-report] Prepare — Resolve: degraded — ${reason}. NLM is likely unauthenticated/offline; handing back to Opus.`)
    return {
      status: 'blocked',
      reason: 'notebook_unresolved',
      run_id: runId,
      notebook_id: null,
      timestamp: a.timestamp,
      artifacts: [],
      bundle_updated: false,
      report: [
        {
          phase: 'Prepare',
          notebook_resolved: false,
          error: `Could not resolve a NotebookLM notebook for run "${runId}" (${reason}). ` +
            'Ensure `notebooklm login` is authenticated, then rerun (NLM will be auto-resolved) ' +
            'or pass an explicit notebook_id.',
        },
      ],
    }
  }

  notebookId = resolved.notebook_id
  notebookSource = `resolved:${resolved.mode || notebookMode || 'default'}`
  log(`[notebooklm-report] Prepare — Resolve complete — notebook_id "${notebookId}" (title: ${resolved.notebook_title || 'n/a'}, project: ${resolved.project || project || 'n/a'}, mode: ${resolved.mode || notebookMode || 'default'})`)
}

log(`[notebooklm-report] Phase 1 — Prepare: confirming run dir layout for "${runId}" and resolving notebook "${notebookId}"`)

const prepReport = await agent(
  `Mode: A — Exploration only. Do NOT git add/commit/push/stash. Do NOT write or edit any files.

You are the RF/NotebookLM preflight inspector for run "${runId}". Confirm the synthesized run
is ready for NotebookLM artifact attachment and resolve the notebook id. Do NOT call any
notebooklm or rf command that mutates state. Read-only inspection only.

Steps:
1. Confirm the run directory layout exists by inspecting these paths (relative to the workspace root):
   - "runs/${runId}/reports/report_draft.md"   (the synthesized report draft — REQUIRED)
   - "runs/${runId}/claims/claim_ledger.yaml"   (the claim ledger — REQUIRED)
   - "runs/${runId}/evidence_bundle.yaml"        (the evidence bundle — may not exist yet; note presence)
   - "runs/${runId}/nlm_artifacts/"              (artifact output dir — may not exist yet; note presence)
2. Resolve the notebook id. The expected notebook is "${notebookId}". You MAY run the read-only
   command 'notebooklm list --json' to confirm a notebook with id "${notebookId}" exists and that
   the run's sources are present. If 'notebooklm list' fails (auth not set up, offline), DEGRADE:
   do NOT fail — record notebook_resolved=false with the reason, and let the operator handle auth
   out-of-band. Never run 'notebooklm login', 'notebooklm create', 'notebooklm delete', or any
   generate/download command in this phase.
3. Return a structured ok/missing report.

Return a JSON object matching this schema exactly:
{
  "report_draft_exists": boolean,
  "claim_ledger_exists": boolean,
  "evidence_bundle_exists": boolean,
  "nlm_artifacts_dir_exists": boolean,
  "notebook_resolved": boolean,
  "notebook_id": "${notebookId}",
  "missing": string[],          // names of REQUIRED paths that are absent (report_draft / claim_ledger)
  "notes": string               // one line: any degrade reason (e.g. notebooklm list failed offline)
}

Do NOT write any files. Return the JSON object only.`,
  {
    label: 'nlm_report_preflight',
    phase: 'Prepare',
    agentType: 'codebase-explorer',
    model: 'sonnet',
    schema: {
      type: 'object',
      properties: {
        report_draft_exists: { type: 'boolean' },
        claim_ledger_exists: { type: 'boolean' },
        evidence_bundle_exists: { type: 'boolean' },
        nlm_artifacts_dir_exists: { type: 'boolean' },
        notebook_resolved: { type: 'boolean' },
        notebook_id: { type: 'string' },
        missing: { type: 'array', items: { type: 'string' } },
        notes: { type: 'string' },
      },
      required: ['report_draft_exists', 'claim_ledger_exists', 'missing'],
    },
  }
)

if (!prepReport) {
  return {
    status: 'blocked',
    reason: 'prepare_failed',
    run_id: runId,
    notebook_id: notebookId,
    timestamp: a.timestamp,
    artifacts: [],
    bundle_updated: false,
    report: [{ phase: 'Prepare', error: 'Preflight inspector returned null — could not inspect run directory.' }],
  }
}

// The report draft and claim ledger MUST exist — this workflow runs only on a synthesized run.
if (prepReport.report_draft_exists !== true || prepReport.claim_ledger_exists !== true) {
  return {
    status: 'blocked',
    reason: 'run_not_synthesized',
    run_id: runId,
    notebook_id: notebookId,
    timestamp: a.timestamp,
    artifacts: [],
    bundle_updated: false,
    report: [
      {
        phase: 'Prepare',
        report_draft_exists: prepReport.report_draft_exists === true,
        claim_ledger_exists: prepReport.claim_ledger_exists === true,
        missing: prepReport.missing || [],
        error: 'report_draft.md and/or claim_ledger.yaml missing — run `rf synthesize` before this workflow.',
      },
    ],
  }
}

log(`[notebooklm-report] Prepare complete — report_draft & claim_ledger present; notebook_resolved=${prepReport.notebook_resolved === true}; generating formats: ${requestedFormats.join(', ')}`)

// ── Phase 2: Generate ────────────────────────────────────────────────────────────
// parallel() over the requested formats. Each kicks off a NotebookLM generation and
// captures a task_id (or, for the sync mind-map, a marker). Budget-guarded per leg.
// Degrade on rate-limit/failure (status 'skipped_rate_limited'); never fail the run.
phase('Generate')
log(`[notebooklm-report] Phase 2 — Generate: fanning out ${requestedFormats.length} NotebookLM generation leg(s) for notebook "${notebookId}"`)

const GENERATE_SCHEMA = {
  type: 'object',
  properties: {
    format: { type: 'string' },
    type: { type: 'string' },         // download type token: report | mind-map | data-table
    ext: { type: 'string' },          // md | json | csv
    sync: { type: 'boolean' },        // true for the instant mind-map (no wait needed)
    task_id: { type: 'string' },      // present for async (briefing-doc, data-table); empty for sync mind-map
    status: { type: 'string' },       // generated | skipped_rate_limited | skipped_invalid | skipped_budget
    error: { type: 'string' },
  },
  required: ['format', 'status'],
}

const generateResults = await parallel(
  requestedFormats.map((format, idx) => async () => {
    const fmtMeta = FORMAT_META[format]

    // Budget guard: skip the generation leg if remaining budget can't cover one leg.
    if (budget.remaining() < LEG_COST) {
      log(`[notebooklm-report] Generate: budget low (${budget.remaining()} remaining) — skipping "${format}"`)
      return {
        format,
        type: fmtMeta.downloadType,
        ext: fmtMeta.ext,
        sync: fmtMeta.sync,
        task_id: '',
        status: 'skipped_budget',
        error: `budget.remaining() (${budget.remaining()}) < leg cost (${LEG_COST})`,
      }
    }

    // data-table requires a description. If it was requested without one, skip it cleanly.
    if (format === 'data-table' && dataTableDesc.trim() === '') {
      log('[notebooklm-report] Generate: data-table requested but data_table_desc is empty — skipping')
      return {
        format,
        type: fmtMeta.downloadType,
        ext: fmtMeta.ext,
        sync: fmtMeta.sync,
        task_id: '',
        status: 'skipped_invalid',
        error: 'data-table requested but args.data_table_desc was empty.',
      }
    }

    // Build the exact NotebookLM generate command (quoted from notebooklm SKILL.md).
    // Vary the agent label by array index (NOT randomness).
    let generateCmd
    if (format === 'briefing-doc') {
      generateCmd = `notebooklm generate report --format briefing-doc --json -n ${notebookId}`
    } else if (format === 'mind-map') {
      generateCmd = `notebooklm generate mind-map -n ${notebookId}`
    } else {
      // data-table: description is required and goes first as a positional arg.
      generateCmd = `notebooklm generate data-table "${dataTableDesc}" --json -n ${notebookId}`
    }

    const legResult = await agent(
      `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash.

You are the NotebookLM artifact generator for the "${format}" leg of RF run "${runId}".
NotebookLM is already authenticated out-of-band (notebooklm login) and the run's sources are
already uploaded to notebook "${notebookId}". Your ONLY job is to kick off ONE generation and
capture its task id. Do NOT wait, do NOT download, do NOT edit any files in this phase.

GOVERNANCE: Never run 'notebooklm delete' or 'notebooklm notebook delete' or any destructive
command. Never run 'notebooklm create'. Never touch runs/${runId}/reports/report_draft.md.

Steps:
1. Run EXACTLY this command (do not alter flags or add extra ones):
   ${generateCmd}
${fmtMeta.sync
  ? `   The mind-map is generated synchronously (instant) — there is no task_id to capture. On exit
   code 0, return { format: "${format}", type: "${fmtMeta.downloadType}", ext: "${fmtMeta.ext}", sync: true, task_id: "", status: "generated" }.
   (The Integrate phase will download it directly.)`
  : `   Parse the JSON output and extract the "task_id" field.
   On exit code 0 with a task_id, return { format: "${format}", type: "${fmtMeta.downloadType}", ext: "${fmtMeta.ext}", sync: false, task_id: "<the task_id>", status: "generated" }.`}
2. DEGRADE-ON-FAILURE (never fail the run):
   - If the command returns a non-zero exit code due to rate limiting (stderr mentions rate limit,
     GENERATION_FAILED, or "No result found for RPC ID"), return
     { format: "${format}", type: "${fmtMeta.downloadType}", ext: "${fmtMeta.ext}", sync: ${fmtMeta.sync}, task_id: "", status: "skipped_rate_limited", error: "<stderr summary>" }.
   - For any other non-zero exit (auth failure, invalid notebook, offline), return
     { format: "${format}", type: "${fmtMeta.downloadType}", ext: "${fmtMeta.ext}", sync: ${fmtMeta.sync}, task_id: "", status: "skipped_rate_limited", error: "<stderr summary>" }.
   In all cases return a JSON object — never throw, never exit non-zero yourself.

Do NOT run rf commands. Do NOT git add/commit/push/stash. Return the JSON object only.`,
      {
        label: `nlm_generate_${format}_${idx}`,
        phase: 'Generate',
        agentType: 'python-backend-engineer',
        model: 'sonnet',
        schema: GENERATE_SCHEMA,
      }
    )

    return legResult
  })
)

// Keep only legs that successfully kicked off a generation (status 'generated').
const generatedLegs = generateResults.filter((r) => r && r.status === 'generated')
const skippedLegs = generateResults.filter((r) => r && r.status && r.status !== 'generated')

log(`[notebooklm-report] Generate complete — ${generatedLegs.length} generated, ${skippedLegs.length} skipped (${skippedLegs.map((s) => `${s.format}:${s.status}`).join(', ') || 'none'})`)

if (generatedLegs.length === 0) {
  // Nothing to integrate. Report the skip reasons and hand back to Opus.
  return {
    status: 'needs_opus',
    reason: 'no_artifacts_generated',
    run_id: runId,
    notebook_id: notebookId,
    timestamp: a.timestamp,
    artifacts: skippedLegs.map((s) => ({
      type: s.type || (FORMAT_META[s.format] && FORMAT_META[s.format].downloadType) || s.format,
      path: null,
      task_id: s.task_id || null,
      status: s.status,
    })),
    bundle_updated: false,
    notebook_source: notebookSource,
    report: [
      { phase: 'Prepare', notebook_resolved: prepReport.notebook_resolved === true, notebook_source: notebookSource },
      { phase: 'Generate', requested: requestedFormats.length, generated: 0, skipped: skippedLegs.length },
    ],
    error: 'No NotebookLM artifacts were generated (all legs skipped — budget, rate-limit, or invalid args). Inspect the per-format statuses and rerun.',
  }
}

// ── Phase 3: Integrate ───────────────────────────────────────────────────────────
// pipeline() over the generated legs (no inter-item barrier — a slow report wait does
// not block a fast mind-map download). Each leg: wait (async only) → download into
// runs/<run_id>/nlm_artifacts/ → record in evidence_bundle.yaml under
// artifacts.notebooklm_report[]. Never touch report_draft.md.
phase('Integrate')
log(`[notebooklm-report] Phase 3 — Integrate: waiting for + downloading ${generatedLegs.length} artifact(s) and recording into evidence_bundle.yaml (non-authoritative)`)

const INTEGRATE_SCHEMA = {
  type: 'object',
  properties: {
    format: { type: 'string' },
    type: { type: 'string' },
    path: { type: 'string' },
    task_id: { type: 'string' },
    status: { type: 'string' },       // ok | skipped_timeout | skipped_rate_limited | skipped_download_failed
    bundle_recorded: { type: 'boolean' },
    error: { type: 'string' },
  },
  required: ['format', 'type', 'status'],
}

const integrateResults = await pipeline(
  generatedLegs,
  async (leg) => {
    const fmtMeta = FORMAT_META[leg.format]
    const artifactPath = `./runs/${runId}/nlm_artifacts/${fmtMeta.downloadType}.${fmtMeta.ext}`
    const generatedAt = a.timestamp

    // Build the exact wait + download commands (quoted from notebooklm SKILL.md).
    // Sync mind-map has no task_id, so it skips the wait step and downloads directly.
    const waitCmd = leg.sync
      ? null
      : `notebooklm artifact wait ${leg.task_id} -n ${notebookId} --timeout 1200`
    const downloadCmd = leg.sync
      ? `notebooklm download ${fmtMeta.downloadType} ${artifactPath} -n ${notebookId}`
      : `notebooklm download ${fmtMeta.downloadType} ${artifactPath} -a ${leg.task_id} -n ${notebookId}`

    const result = await agent(
      `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash.

You are the NotebookLM artifact integrator for the "${leg.format}" artifact of RF run "${runId}".
The generation was already kicked off (${leg.sync ? 'synchronous mind-map — no task_id' : `task_id ${leg.task_id}`}).
Wait for it (if async), download it into the run, and record it in the evidence bundle as a
NON-AUTHORITATIVE artifact.

CRITICAL GOVERNANCE — read carefully:
- You MUST NOT edit, append to, or touch "runs/${runId}/reports/report_draft.md". The generated
  artifact is NON-AUTHORITATIVE. Any prose from it that someone later wants to cite must first
  become a separate source card and earn a [claim:<id>]. That is a separate, later step — NOT
  yours. Your edit is confined to evidence_bundle.yaml and the downloaded file.
- Never run 'notebooklm delete' / 'notebooklm notebook delete' or any destructive command.

Steps (degrade on failure — never fail the run; always return a JSON object):
${leg.sync
  ? `1. (mind-map is synchronous — skip the wait step.)`
  : `1. Wait for the artifact to complete:
   ${waitCmd}
   Exit code 0 = ready; exit code 2 = timeout. On timeout (exit 2), return
   { format: "${leg.format}", type: "${fmtMeta.downloadType}", path: "", task_id: "${leg.task_id}", status: "skipped_timeout", bundle_recorded: false, error: "artifact wait timed out at 1200s" } and STOP (do not download).`}
2. Ensure the directory "runs/${runId}/nlm_artifacts/" exists (create it if missing), then download:
   ${downloadCmd}
   If the download exits non-zero, return
   { format: "${leg.format}", type: "${fmtMeta.downloadType}", path: "", task_id: "${leg.task_id}", status: "skipped_download_failed", bundle_recorded: false, error: "<stderr summary>" }.
3. Record the artifact in the evidence bundle. Open "runs/${runId}/evidence_bundle.yaml" (create the
   file with a top-level 'artifacts:' mapping if it does not exist). Under 'artifacts:', ensure a list
   key 'notebooklm_report' exists, and APPEND (do not overwrite existing entries) this entry:
     - type: ${fmtMeta.downloadType}
       path: runs/${runId}/nlm_artifacts/${fmtMeta.downloadType}.${fmtMeta.ext}
       task_id: ${leg.sync ? '""' : leg.task_id}
       status: ok
       generated_at: ${generatedAt}
   Write valid YAML. Do NOT remove or reorder any other keys in the bundle. Do NOT touch any other file.
4. On full success return
   { format: "${leg.format}", type: "${fmtMeta.downloadType}", path: "runs/${runId}/nlm_artifacts/${fmtMeta.downloadType}.${fmtMeta.ext}", task_id: "${leg.sync ? '' : leg.task_id}", status: "ok", bundle_recorded: true }.

Do NOT run rf commands. Do NOT git add/commit/push/stash. Return the JSON object only.`,
      {
        label: `nlm_integrate_${leg.format}`,
        phase: 'Integrate',
        agentType: 'python-backend-engineer',
        model: 'sonnet',
        schema: INTEGRATE_SCHEMA,
      }
    )

    return result
  }
)

// ── Build artifact list and return ───────────────────────────────────────────────
const integrated = integrateResults.filter((r) => r && r.status === 'ok')
const integrateFailed = integrateResults.filter((r) => r && r.status && r.status !== 'ok')

// Merge: integrated/failed legs + the legs that never generated (skipped in Generate).
const artifacts = []
for (const r of integrateResults.filter(Boolean)) {
  artifacts.push({
    type: r.type || (FORMAT_META[r.format] && FORMAT_META[r.format].downloadType) || r.format,
    path: r.path && r.path.length > 0 ? r.path : null,
    task_id: r.task_id && r.task_id.length > 0 ? r.task_id : null,
    status: r.status,
  })
}
for (const s of skippedLegs) {
  artifacts.push({
    type: s.type || (FORMAT_META[s.format] && FORMAT_META[s.format].downloadType) || s.format,
    path: null,
    task_id: s.task_id && s.task_id.length > 0 ? s.task_id : null,
    status: s.status,
  })
}

const bundleUpdated = integrateResults.some((r) => r && r.bundle_recorded === true)

log(`[notebooklm-report] Integrate complete — ${integrated.length} attached, ${integrateFailed.length} degraded; bundle_updated=${bundleUpdated}`)
log('[notebooklm-report] GOVERNANCE NOTE: NotebookLM artifacts are NON-AUTHORITATIVE — recorded under ' +
    'evidence_bundle.yaml artifacts.notebooklm_report, NOT merged into report_draft.md. To cite any ' +
    'of this prose, first create a source card (rf ingest) and earn a [claim:<id>]. Next step: rf verify.')

return {
  status: integrated.length > 0 ? 'complete' : 'needs_opus',
  run_id: runId,
  notebook_id: notebookId,
  notebook_source: notebookSource,
  timestamp: a.timestamp,
  artifacts,
  bundle_updated: bundleUpdated,
  report: [
    { phase: 'Prepare', report_draft_exists: true, claim_ledger_exists: true, notebook_resolved: prepReport.notebook_resolved === true, notebook_source: notebookSource },
    { phase: 'Generate', requested: requestedFormats.length, generated: generatedLegs.length, skipped: skippedLegs.length },
    { phase: 'Integrate', attached: integrated.length, degraded: integrateFailed.length, bundle_updated: bundleUpdated },
  ],
}
