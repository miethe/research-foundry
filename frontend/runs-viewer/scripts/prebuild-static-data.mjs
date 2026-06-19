#!/usr/bin/env node
/**
 * prebuild-static-data.mjs — static SPA pre-build step (P5-BUILD)
 *
 * Runs `rf run export --all` via the project Python venv, then copies the
 * resulting runs/<run_id>/run.json files into public/data/<run_id>/run.json
 * so the Vite build bundles them as static assets.
 *
 * Also emits public/data/index.json — an array of { run_id, status_derived,
 * created_at, sensitivity } summaries — used by fetchRunList() in static mode
 * IF VITE_RUNS_FRONTEND_LOOPBACK_API is not set (the build is purely static).
 *
 * NOTE: The current client.ts static mode loads the fixture import directly via
 * `import fixtureRunJson from "@/test/fixtures/run.json"`. The public/data/ tree
 * produced here is the *build-time* copy used by vite preview. For runtime
 * static serving the SPA reads public/data at the served URL, but the bundled
 * import always wins in the compiled JS. This script ensures the dist copy is
 * populated so `vite preview` serves the data correctly.
 *
 * Data layout:
 *   public/data/<run_id>/run.json    — full export per run
 *   public/data/index.json           — summary list
 */

import { execSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
// scripts/ → runs-viewer/ → frontend/ → runs-frontend-v1 (repo root for worktree)
const REPO_ROOT = resolve(__dirname, "../../../");
const RUNS_DIR = join(REPO_ROOT, "runs");
const PUBLIC_DATA_DIR = join(__dirname, "..", "public", "data");
const VENV_PYTHON = join(REPO_ROOT, ".venv", "bin", "python");

// ── 1. Run rf run export --all ────────────────────────────────────────────────

console.log("[prebuild] Running rf run export --all …");
try {
  execSync(`"${VENV_PYTHON}" -m research_foundry run export --all`, {
    cwd: REPO_ROOT,
    stdio: "inherit",
  });
} catch (err) {
  console.error("[prebuild] ERROR: rf run export --all failed:", err.message);
  process.exit(1);
}

// ── 2. Discover all run.json files written by the export ──────────────────────

if (!existsSync(RUNS_DIR)) {
  console.error(`[prebuild] ERROR: runs/ directory not found at ${RUNS_DIR}`);
  process.exit(1);
}

const { readdirSync } = await import("node:fs");
const runDirs = readdirSync(RUNS_DIR, { withFileTypes: true })
  .filter((d) => d.isDirectory() && d.name.startsWith("rf_run_"))
  .map((d) => d.name);

console.log(`[prebuild] Found ${runDirs.length} run director${runDirs.length === 1 ? "y" : "ies"}.`);

// ── 3. Copy run.json → public/data/<run_id>/run.json ─────────────────────────

const summaries = [];

for (const runId of runDirs) {
  const src = join(RUNS_DIR, runId, "run.json");
  if (!existsSync(src)) {
    console.warn(`[prebuild] WARN: no run.json for ${runId} — skipping`);
    continue;
  }

  const destDir = join(PUBLIC_DATA_DIR, runId);
  mkdirSync(destDir, { recursive: true });
  const dest = join(destDir, "run.json");

  // Read + parse to build summary
  let run;
  try {
    run = JSON.parse(readFileSync(src, "utf8"));
  } catch (e) {
    console.warn(`[prebuild] WARN: could not parse ${src}: ${e.message}`);
    continue;
  }

  writeFileSync(dest, JSON.stringify(run, null, 2));
  console.log(`[prebuild]   copied → public/data/${runId}/run.json`);

  summaries.push({
    run_id:         run.run_id,
    status_derived: run.status_derived ?? null,
    created_at:     run.created_at ?? null,
    sensitivity:    run.sensitivity ?? null,
    claim_counts:   run.claim_counts ?? null,
  });
}

// ── 4. Write index.json ───────────────────────────────────────────────────────

const indexPath = join(PUBLIC_DATA_DIR, "index.json");
writeFileSync(indexPath, JSON.stringify(summaries, null, 2));
console.log(`[prebuild] Wrote index with ${summaries.length} run(s) → public/data/index.json`);
console.log("[prebuild] Static data pre-build complete.");
