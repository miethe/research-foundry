// notebooklm-extended.js
//
// Extended Runs: long-latency, rate-limited, async NotebookLM artifact generation
// (audio deep-dive 10-20 min, video 15-45 min) across N notebooks — typically one
// notebook per swarm leg. Each notebook flows independently through three stages —
// Generate -> Poll -> Collect — via pipeline() with NO inter-item barrier, so a
// slow/rate-limited notebook never blocks the others.
//
// Checkpoint/resume: every completed item records its nlm_task_id into the returned
// `checkpoint` map. An operator passes that map back as args.resume_task_ids to resume
// a run; the Generate stage REUSES a prior task_id instead of regenerating a
// non-deterministic artifact (this is how constraint 4 — no Math.random / non-determinism
// — is handled for inherently non-deterministic audio/video generation).
//
// FOUR HARD CONSTRAINTS honored:
//   1. No fs/child_process/exec/readFile/require in this script body — every notebooklm/rf
//      call is run BY an inner agent via its own Bash tool.
//   2. No Date.now()/Math.random()/new Date() — timestamp derives from args.timestamp;
//      agent labels vary by array index, not randomness.
//   3. No reviewer agents are inline-prompted (this workflow needs no reviewer gate).
//   4. NLM auth is a documented PRECONDITION (operator runs `notebooklm login` out-of-band),
//      so it is NOT a Mode D gate. Destructive NLM ops (delete) are forbidden and never issued.
//
// Workflow args may arrive as a JSON string from the Workflow tool. Always parse first.
const a = typeof args === 'string' ? JSON.parse(args) : (args || {})

export const meta = {
  name: 'notebooklm-extended',
  description: 'Extended Runs: async, long-latency, rate-limited NotebookLM artifact generation (audio deep-dive 10-20 min, video 15-45 min) across N notebooks — one per swarm leg — using pipeline() with no inter-item barrier, background polling, and nlm_task_id checkpoint/resume. Generate -> Poll -> Collect per notebook. Generation legs are budget-guarded (skip when budget.remaining() < 60000). On resume, a prior task_id is REUSED rather than regenerating a non-deterministic artifact. Rate-limit / timeout degrades to a skipped status; never fails the run. Always passes explicit FULL-UUID -n on every generate/wait/download. Completed artifacts download to runs/<run_id>/nlm_artifacts/ and are recorded as non-authoritative artifacts in runs/<run_id>/evidence_bundle.yaml (artifacts.notebooklm_extended[]). Destructive NLM ops (delete) are never issued.',
  phases: [
    { title: 'Generate' },
    { title: 'Poll' },
    { title: 'Collect' },
  ],
  whenToUse: 'Use when an RF run needs long-latency NotebookLM artifacts (audio deep-dive, video) generated across one or more notebooks (e.g. one per swarm leg) without an inter-item barrier, with background polling and checkpoint/resume. Requires `notebooklm login` completed out-of-band and the notebooks already populated with sources. Pass args.resume_task_ids (from a prior run\'s `checkpoint` map) to resume in-flight artifacts instead of regenerating them.',
}

// === Script body ===

const run_id = a.run_id
const artifact = a.artifact || 'audio'
const resumeTaskIds = a.resume_task_ids || {}

// NotebookLM correlation inputs. notebook_id (per notebooks[] item) is OPTIONAL — when a
// notebook list is absent OR an item omits its notebook_id, the run's correlated notebook is
// resolved through `rf notebooklm resolve` (the correlation CLI) at the start of the Generate
// phase. project scopes the correlation registry; notebook_mode selects how the notebook is
// correlated to the run (project | run | explicit).
const project = typeof a.project === 'string' && a.project.trim().length > 0 ? a.project.trim() : null
const NOTEBOOK_MODES = ['project', 'run', 'explicit']
const notebookMode = NOTEBOOK_MODES.includes(a.notebook_mode) ? a.notebook_mode : null

// notebooks is `let` because the resolve step may synthesize a one-item list (or fill in
// missing per-item notebook_ids) when correlation succeeds.
let notebooks = Array.isArray(a.notebooks) ? a.notebooks : []

// ── Dry-run guard (return parsed args without spawning agents) ───────────────────
if (a.dry_run === true) {
  return {
    status: 'dry_run',
    parsed_args: a,
  }
}

// ── Required-arg validation (return blocked, never throw) ────────────────────────
// Only run_id is strictly required. notebooks may be omitted/empty: the Generate-phase
// resolve step will correlate a single run-level notebook via `rf notebooklm resolve`.
const missing = []
if (!run_id) missing.push('run_id')

if (missing.length > 0) {
  return {
    status: 'blocked',
    reason: 'missing_args',
    missing,
    run_id: run_id || null,
    timestamp: a.timestamp,
    results: [],
    checkpoint: {},
    report: [
      `notebooklm-extended blocked: missing required args [${missing.join(', ')}]. ` +
      `Provide run_id (string); notebooks (array of { notebook_id?, instructions?, label? }) is ` +
      `optional and auto-resolved via the correlation CLI when omitted.`,
    ],
  }
}

// Normalize artifact type to a known, non-destructive generation kind.
const artifactKind = artifact === 'video' ? 'video' : 'audio'
const artifactExt = artifactKind === 'video' ? 'mp4' : 'mp3'
// Per-kind defaults; format may be overridden via args.format.
const artifactFormat = a.format || (artifactKind === 'video' ? 'explainer' : 'deep-dive')

log(`[notebooklm-extended] run "${run_id}" — ${notebooks.length} notebook(s), artifact: ${artifactKind} (format: ${artifactFormat})`)
log('[notebooklm-extended] SAFETY: every generate/wait/download passes an explicit FULL-UUID -n; partial ids are never used. Destructive NLM ops (delete) are never issued.')

// ── Shared helpers (pure JS — no FS, no shell) ───────────────────────────────────
// Stable per-item label: prefer the caller's label, else the full notebook_id, else index.
const itemLabel = (nb, idx) =>
  (nb && nb.label) || (nb && nb.notebook_id) || `nb_${idx}`

// ── Stage 1: Generate ────────────────────────────────────────────────────────────
// Resume: if a prior task_id exists for this notebook, REUSE it (never regenerate a
// non-deterministic artifact). Else a python-backend-engineer agent runs
// `notebooklm generate <kind> "<instructions>" --format <fmt> --json -n <FULL_UUID>`.
// Budget guard: if budget.remaining() < 60_000, skip generation + downstream stages.
const genStage = async (nb, idx) => {
  const label = itemLabel(nb, idx)
  const notebookId = nb && nb.notebook_id

  if (!notebookId) {
    log(`[notebooklm-extended] Generate: item ${idx} (${label}) has no notebook_id — skipping.`)
    return {
      notebook_id: null,
      label,
      task_id: null,
      status: 'skipped_no_notebook_id',
      artifact_path: null,
    }
  }

  // Resume path: reuse a prior in-flight task_id rather than regenerating.
  const priorTaskId = resumeTaskIds[notebookId]
  if (priorTaskId) {
    log(`[notebooklm-extended] Generate: reusing checkpointed task_id "${priorTaskId}" for ${label} (resume — no regeneration of non-deterministic artifact).`)
    return {
      notebook_id: notebookId,
      label,
      task_id: priorTaskId,
      status: 'resumed',
      artifact_path: null,
    }
  }

  // Budget guard (audio/video generation leg ~60K). Skip downstream stages for this item.
  if (budget.remaining() < 60_000) {
    log(`[notebooklm-extended] Generate: budget low (${budget.remaining()} remaining) — skipping ${label}.`)
    return {
      notebook_id: notebookId,
      label,
      task_id: null,
      status: 'skipped_budget',
      artifact_path: null,
    }
  }

  const instructions = (nb && nb.instructions) || `Produce a ${artifactFormat} ${artifactKind} overview of this notebook's sources.`

  const result = await agent(
    `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash.

You are the NotebookLM extended-run GENERATE agent for one notebook in RF run "${run_id}".
Your job: kick off ONE long-latency ${artifactKind} artifact generation and return its task_id.
Do NOT wait, poll, or download here — that is the downstream Poll/Collect stage's job.

PRECONDITION: \`notebooklm login\` was completed out-of-band by the operator. If auth is missing,
DEGRADE — do not attempt to log in, do not open a browser, do not fail the run.

Notebook (FULL UUID — always pass it explicitly via -n; never a partial id):
  notebook_id: ${notebookId}
  label: ${label}
Instructions for the artifact: ${instructions}

ISOLATION: before any command, set a unique NOTEBOOKLM_HOME for this agent so concurrent
notebooks never share context state:
  export NOTEBOOKLM_HOME=/tmp/nlm-${run_id}-${label}

Steps (stop and degrade on any non-zero exit code — never fail the run):

1. Sanity-check auth without prompting (safe to auto-run):
   notebooklm status
   If it does NOT show "Authenticated as: ..." -> return
   { "notebook_id": "${notebookId}", "label": "${label}", "task_id": null, "status": "skipped_no_auth" }.

2. Kick off generation (exact command — note the FULL-UUID -n and --json):
   notebooklm generate ${artifactKind} "${instructions}" --format ${artifactFormat} --json -n ${notebookId} --retry 2
   - Parse "task_id" from the JSON output.
   - On rate-limit / GENERATION_FAILED / any non-zero exit -> return
     { "notebook_id": "${notebookId}", "label": "${label}", "task_id": null, "status": "skipped_rate_limited" }.

3. On success: return
   { "notebook_id": "${notebookId}", "label": "${label}", "task_id": "<task_id>", "status": "generating", "artifact_path": null }.

Do NOT run notebooklm download, notebooklm artifact wait, notebooklm delete, or any rf command here.
Do NOT git add/commit/push/stash.`,
    {
      label: `nlm_generate_${label}_${idx}`,
      phase: 'Generate',
      agentType: 'python-backend-engineer',
      model: 'sonnet',
      schema: {
        type: 'object',
        properties: {
          notebook_id: { type: 'string' },
          label: { type: 'string' },
          task_id: { type: 'string' },
          status: { type: 'string' },
          artifact_path: { type: 'string' },
        },
        required: ['notebook_id', 'status'],
      },
    }
  )

  if (!result) {
    // agent() returned null (user skipped) — degrade this item, keep the run alive.
    return {
      notebook_id: notebookId,
      label,
      task_id: null,
      status: 'skipped_generate_null',
      artifact_path: null,
    }
  }

  return {
    notebook_id: notebookId,
    label,
    task_id: result.task_id || null,
    status: result.status || 'generating',
    artifact_path: null,
  }
}

// ── Stage 2: Poll ──────────────────────────────────────────────────────────────
// Background-wait on the in-flight task. `artifact wait` auto-runs in subagent context
// per NLM autonomy rules. exit 0 = done, exit 2 = timeout -> degrade to skipped.
const pollStage = async (prev, idx) => {
  // Carry forward terminal/skip states from Generate without spawning a poll agent.
  if (!prev || !prev.task_id || prev.status === 'skipped_budget' ||
      prev.status === 'skipped_no_notebook_id' || prev.status === 'skipped_no_auth' ||
      prev.status === 'skipped_rate_limited' || prev.status === 'skipped_generate_null') {
    return prev
  }

  const { notebook_id: notebookId, label, task_id: taskId } = prev

  const result = await agent(
    `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash.

You are the NotebookLM extended-run POLL agent for one notebook in RF run "${run_id}".
Your job: wait for ONE already-started ${artifactKind} artifact to finish, then report its status.
Do NOT generate and do NOT download here — Collect handles the download.

NOTE: \`notebooklm artifact wait\` auto-runs in subagent context per the NotebookLM autonomy rules
(it is a long-running wait command, allowed without confirmation when running as a subagent).

Notebook (FULL UUID — always -n, never partial):
  notebook_id: ${notebookId}
  label: ${label}
Task to wait on:
  task_id: ${taskId}

ISOLATION: reuse the same per-agent home as generation:
  export NOTEBOOKLM_HOME=/tmp/nlm-${run_id}-${label}

Steps (degrade on failure — never fail the run):

1. Wait for completion (exact command — FULL-UUID -n, timeout 2700s = 45 min ceiling):
   notebooklm artifact wait ${taskId} -n ${notebookId} --timeout 2700
   - Exit code 0 -> artifact is done. Return
     { "notebook_id": "${notebookId}", "label": "${label}", "task_id": "${taskId}", "status": "ready" }.
   - Exit code 2 -> TIMEOUT (still rendering or rate-limited). Return
     { "notebook_id": "${notebookId}", "label": "${label}", "task_id": "${taskId}", "status": "skipped_rate_limited" }.
   - Any other non-zero exit (exit 1 = not found / failed) -> Return
     { "notebook_id": "${notebookId}", "label": "${label}", "task_id": "${taskId}", "status": "skipped_rate_limited" }.

Do NOT run notebooklm download, notebooklm generate, notebooklm delete, or any rf command here.
Do NOT git add/commit/push/stash.`,
    {
      label: `nlm_poll_${label}_${idx}`,
      phase: 'Poll',
      agentType: 'python-backend-engineer',
      model: 'sonnet',
      schema: {
        type: 'object',
        properties: {
          notebook_id: { type: 'string' },
          label: { type: 'string' },
          task_id: { type: 'string' },
          status: { type: 'string' },
        },
        required: ['notebook_id', 'task_id', 'status'],
      },
    }
  )

  if (!result) {
    return { ...prev, status: 'skipped_rate_limited' }
  }

  return {
    notebook_id: notebookId,
    label,
    task_id: taskId,
    status: result.status || 'skipped_rate_limited',
    artifact_path: null,
  }
}

// ── Stage 3: Collect ───────────────────────────────────────────────────────────
// Download the finished artifact and record the nlm_task_id checkpoint + artifact path
// into runs/<run_id>/evidence_bundle.yaml under artifacts.notebooklm_extended[].
const collectStage = async (prev, idx) => {
  // Only collect items that polled ready. Carry forward everything else unchanged.
  if (!prev || prev.status !== 'ready' || !prev.task_id) {
    return prev
  }

  const { notebook_id: notebookId, label, task_id: taskId } = prev
  const artifactPath = `./runs/${run_id}/nlm_artifacts/${label}.${artifactExt}`

  const result = await agent(
    `Mode: C — Autonomous execution (Bash-capable). Do NOT git add/commit/push/stash.

You are the NotebookLM extended-run COLLECT agent for one notebook in RF run "${run_id}".
Your job: download ONE finished ${artifactKind} artifact and record it as a NON-AUTHORITATIVE
artifact in the run's evidence bundle. The artifact NEVER enters report_draft.md and NEVER
becomes a material claim — it rides in the evidence bundle only.

Notebook (FULL UUID — always -n, never partial):
  notebook_id: ${notebookId}
  label: ${label}
Finished task:
  task_id: ${taskId}

ISOLATION: reuse the same per-agent home:
  export NOTEBOOKLM_HOME=/tmp/nlm-${run_id}-${label}

Steps (degrade on failure — never fail the run):

1. Ensure the output dir exists:
   mkdir -p runs/${run_id}/nlm_artifacts

2. Download the artifact (exact command — FULL-UUID -n, -a <task_id>, explicit path):
   notebooklm download ${artifactKind} ${artifactPath} -a ${taskId} -n ${notebookId}
   - On non-zero exit (generation incomplete / not found) -> return
     { "notebook_id": "${notebookId}", "label": "${label}", "task_id": "${taskId}", "status": "skipped_download_failed", "artifact_path": null }.

3. Record the checkpoint + artifact into the evidence bundle (NON-AUTHORITATIVE).
   Append to runs/${run_id}/evidence_bundle.yaml under the key artifacts.notebooklm_extended
   (create the list if absent) ONE entry:
     - notebook_id: ${notebookId}
       label: ${label}
       nlm_task_id: ${taskId}
       artifact_type: ${artifactKind}
       artifact_format: ${artifactFormat}
       artifact_path: ${artifactPath}
       authoritative: false
       requires_network: true
       reliability_notes: "NotebookLM-generated; non-reproducible (online, non-deterministic)"
   Preserve all existing bundle content; do not reorder or rewrite other keys. If the bundle
   file is missing, create a minimal one with just the artifacts.notebooklm_extended list.

4. Return
   { "notebook_id": "${notebookId}", "label": "${label}", "task_id": "${taskId}", "status": "collected", "artifact_path": "${artifactPath}" }.

Do NOT run notebooklm generate, notebooklm artifact wait, notebooklm delete here.
Do NOT modify report_draft.md or claim_ledger.yaml. Do NOT git add/commit/push/stash.`,
    {
      label: `nlm_collect_${label}_${idx}`,
      phase: 'Collect',
      agentType: 'python-backend-engineer',
      model: 'sonnet',
      schema: {
        type: 'object',
        properties: {
          notebook_id: { type: 'string' },
          label: { type: 'string' },
          task_id: { type: 'string' },
          status: { type: 'string' },
          artifact_path: { type: 'string' },
        },
        required: ['notebook_id', 'task_id', 'status'],
      },
    }
  )

  if (!result) {
    return { ...prev, status: 'skipped_download_failed', artifact_path: null }
  }

  return {
    notebook_id: notebookId,
    label,
    task_id: taskId,
    status: result.status || 'collected',
    artifact_path: result.artifact_path || (result.status === 'collected' ? artifactPath : null),
  }
}

// ── Resolve notebook (correlation CLI) ───────────────────────────────────────────
// notebook_id is OPTIONAL. When the notebooks list is empty, or any item omits its
// notebook_id, resolve the run's correlated notebook through the correlation CLI so the
// pipeline has a stable, run/project-correlated notebook to generate against. This runs ONCE
// (not per item) via a Bash-capable python-backend-engineer agent — resolution may CREATE
// the notebook (`rf notebooklm resolve ... --create`). It DEGRADES — if NLM is unavailable /
// unauthenticated, the agent returns resolved:false. Items that still lack a notebook_id are
// left to the genStage `skipped_no_notebook_id` path; the run never throws or fails here.
phase('Generate')

let notebookSource = 'explicit'
const needsResolve = notebooks.length === 0 || notebooks.some((nb) => !(nb && nb.notebook_id))
if (needsResolve) {
  log(`[notebooklm-extended] Generate — Resolve: ${notebooks.length === 0 ? 'no notebooks provided' : 'one or more notebooks missing notebook_id'} — resolving via \`rf notebooklm resolve\` (mode: ${notebookMode || 'default'}, project: ${project || 'inferred'})`)

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

You are the RF NotebookLM correlation resolver for run "${run_id}". One or more extended-run
notebooks have no notebook_id, so resolve (and create if needed) the run's correlated
NotebookLM notebook through the RF correlation CLI, then return its id. This is the ONLY thing
you do — no generation, no poll, no download.

DEGRADE CONTRACT (critical): NotebookLM is online-only and may be unauthenticated or
offline. If \`rf notebooklm resolve\` fails for ANY reason (NLM unavailable, auth/cookie
error, RPC error, non-zero exit), DO NOT fail. Return
{ "resolved": false, "reason": "<one-line cause>" } with NO notebook_id. NEVER run
\`notebooklm delete\` / \`notebooklm notebook delete\` or any destructive op.

Steps (stop and degrade on any non-zero exit code):

1. Resolve (and create on miss) the correlated notebook:
   \`rf notebooklm resolve --run ${run_id}${projectFlag}${modeFlag} --create\`
   This reads the correlation registry (registries/notebooklm/notebooks.yaml), maps the run
   to its notebook per the correlation mode, and creates the notebook if it does not yet
   exist. Parse the printed/JSON output for the resolved notebook id, title, project, and
   mode.

2. On exit code 0 with a notebook id, return EXACTLY:
   { "resolved": true, "notebook_id": "<id>", "notebook_title": "<title>", "project": "<project-slug>", "mode": "<mode>" }

3. On ANY failure (non-zero exit, no id, NLM unavailable), return EXACTLY:
   { "resolved": false, "reason": "<what failed, one line>" }

Do NOT run any notebooklm generate/wait/download command. Do NOT run any other rf command. Do
NOT write any files. Do NOT git add/commit/push/stash. Return the JSON object only.`,
    {
      label: 'nlm_extended_resolve',
      phase: 'Generate',
      agentType: 'python-backend-engineer',
      model: 'sonnet',
      schema: RESOLVE_SCHEMA,
    }
  )

  if (resolved && resolved.resolved === true && resolved.notebook_id) {
    notebookSource = `resolved:${resolved.mode || notebookMode || 'default'}`
    if (notebooks.length === 0) {
      // No list was provided — synthesize a single run-correlated notebook item.
      notebooks = [{ notebook_id: resolved.notebook_id, label: resolved.project || project || run_id }]
    } else {
      // Fill the resolved id into any item that is missing one (preserve provided ids).
      notebooks = notebooks.map((nb) =>
        nb && nb.notebook_id ? nb : { ...(nb || {}), notebook_id: resolved.notebook_id })
    }
    log(`[notebooklm-extended] Generate — Resolve complete — notebook_id "${resolved.notebook_id}" (title: ${resolved.notebook_title || 'n/a'}, project: ${resolved.project || project || 'n/a'}, mode: ${resolved.mode || notebookMode || 'default'})`)
  } else {
    const reason = (resolved && resolved.reason) || 'rf notebooklm resolve returned no notebook_id'
    notebookSource = 'unresolved'
    log(`[notebooklm-extended] Generate — Resolve: degraded — ${reason}. NLM is likely unauthenticated/offline; items without a notebook_id will be skipped (skipped_no_notebook_id).`)
  }
}

// If, after resolution, there is still nothing to process, hand back to Opus rather than
// running an empty pipeline.
if (notebooks.length === 0) {
  return {
    status: 'needs_opus',
    reason: 'notebook_unresolved',
    run_id,
    notebook_source: notebookSource,
    timestamp: a.timestamp,
    results: [],
    checkpoint: {},
    report: [
      `notebooklm-extended could not resolve a NotebookLM notebook for run "${run_id}" and no ` +
      `notebooks were provided. Ensure \`notebooklm login\` is authenticated, then rerun (NLM ` +
      `will be auto-resolved) or pass notebooks explicitly.`,
    ],
  }
}

// ── Pipeline: each notebook flows Generate -> Poll -> Collect with NO inter-item barrier ──
log(`[notebooklm-extended] Generate -> Poll -> Collect pipeline starting over ${notebooks.length} notebook(s). No inter-item barrier: a slow/rate-limited notebook never blocks others.`)

const pipelineResults = await pipeline(
  notebooks,
  genStage,
  pollStage,
  collectStage
)

// A stage that throws drops that item to null — filter nulls before building the return.
const results = pipelineResults.filter(Boolean)

// ── Build checkpoint map + return ────────────────────────────────────────────────
// checkpoint: notebook_id -> task_id, for every item that has a real task_id. This is
// exactly what an operator passes back as args.resume_task_ids to resume the run.
const checkpoint = {}
for (const r of results) {
  if (r && r.notebook_id && r.task_id) {
    checkpoint[r.notebook_id] = r.task_id
  }
}

const collected = results.filter(r => r && r.status === 'collected')
const ready = results.filter(r => r && r.status === 'ready')
const skipped = results.filter(r => r && typeof r.status === 'string' && r.status.indexOf('skipped') === 0)
const resumed = results.filter(r => r && r.status === 'resumed')

log(`[notebooklm-extended] pipeline complete — ${collected.length} collected, ${ready.length} ready-not-downloaded, ${resumed.length} resumed, ${skipped.length} skipped/degraded.`)
log('[notebooklm-extended] CHECKPOINT: pass the returned `checkpoint` map back as args.resume_task_ids to resume in-flight artifacts without regenerating them.')

// status: 'complete' if at least one artifact was collected; else 'needs_opus' so the
// operator can inspect degraded/skipped items (rate limits, auth, budget) and resume.
const status = collected.length > 0 ? 'complete' : 'needs_opus'

return {
  status,
  run_id,
  notebook_source: notebookSource,
  timestamp: a.timestamp,
  results: results.map(r => ({
    notebook_id: r.notebook_id,
    label: r.label,
    task_id: r.task_id,
    status: r.status,
    artifact_path: r.artifact_path,
  })),
  checkpoint,
  report: [
    { phase: 'Generate', notebooks: notebooks.length, artifact: artifactKind, format: artifactFormat, notebook_source: notebookSource },
    { phase: 'Poll', polled: results.filter(r => r && r.task_id).length },
    { phase: 'Collect', collected: collected.length, skipped: skipped.length, resumed: resumed.length },
  ],
}
