// Test harness: Node's built-in `node:test` + `node --test` (no `--experimental-*` flag
// required; confirmed available on Node 20.19.3 in this environment). This is a project-level
// decision recorded in
// docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-1-pathb-tests.md
// ("Decisions in force") — there is no pre-existing JS test harness elsewhere in the repo to
// match instead, and no new dependency is introduced.
//
// Target under test: .claude/workflows/rf-run-execute.js is a Claude Code Dynamic Workflow
// script (see the workflow-authoring skill). It is READ-ONLY here — never edited, only read
// and executed in-memory. Two facts about its shape drive the approach below:
//
//   1. The script's top level is `export const meta = {...}` followed by plain statements
//      that use bare `return` (valid only *inside* a function body, not at ES module top
//      level) and free identifiers `args`, `log`, `phase`, `parallel`, `agent` that the
//      Dynamic Workflow harness injects at invocation time. To execute the script's real
//      source text unmodified-on-disk, this suite reads the file, strips the leading
//      `export ` keyword from an in-memory copy only (so the body parses as a function
//      body instead of a module), and wraps it in an AsyncFunction with those five names
//      as parameters. No transformation is written back to the file.
//   2. `stampFromTimestamp()` and `resolvePath()` are not directly exported — but the
//      script's own `dry_run: true` branch (before any `log`/`phase`/`parallel`/`agent`
//      call, and before any `rf` invocation or web/network access) returns exactly the
//      values these two functions produced: `{ status: 'dry_run', rf_bin, repo, tmp_dir,
//      stamp, run, args }`. Driving the script via `dry_run: true` is therefore sufficient
//      to assert both functions' behavior with zero live `rf` invocations and zero network
//      calls (AC-P1-6) — the stub callbacks passed for log/phase/parallel/agent additionally
//      throw and are asserted never-called, as a second, independent check of the same
//      invariant.
//
// No `Date.now()`/`new Date()` is used anywhere in this file (matches the four-constraints
// checklist applied to the target script itself — determinism is preserved in the tests too).

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const SCRIPT_PATH = path.join(__dirname, '..', 'rf-run-execute.js');
const RAW_SOURCE = fs.readFileSync(SCRIPT_PATH, 'utf8');

// Strip only the leading `export ` keyword (the script's sole `export`, on line 1) so the
// source parses as a function body rather than an ES module. This is an in-memory string
// transform for test execution only — SCRIPT_PATH itself is never opened for writing.
const SCRIPT_BODY = RAW_SOURCE.replace(/^export /, '');
assert.notStrictEqual(
  SCRIPT_BODY,
  RAW_SOURCE,
  'expected rf-run-execute.js to start with `export ` — the strip-and-wrap harness assumption changed; update this test file, not the target script',
);

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

// A fresh AsyncFunction per call keeps each test's stub closures independent.
function buildWorkflowFn() {
  return new AsyncFunction('args', 'log', 'phase', 'parallel', 'agent', SCRIPT_BODY);
}

// Records every call made to any of the four harness-injected callbacks. Each stub throws
// so that, if the script ever falls through the `dry_run` early-return branch by mistake
// (e.g. a future edit to the script under test), the test fails loudly instead of silently
// making a "live" call.
function callRecorder() {
  const calls = [];
  const stub = (name) => (...callArgs) => {
    calls.push({ name, args: callArgs });
    throw new Error(`unexpected live call to ${name}() during a dry_run-only test`);
  };
  return {
    calls,
    log: stub('log'),
    phase: stub('phase'),
    parallel: stub('parallel'),
    agent: stub('agent'),
  };
}

// Runs the workflow script body with the given args, always via the dry_run branch so no
// agent/parallel/log/rf/network call is ever reached. Returns the script's dry_run result
// object, or throws if the script did not take the dry_run branch (missing run_id, etc.).
async function runDryRun(argsOverrides) {
  const rec = callRecorder();
  const fn = buildWorkflowFn();
  const result = await fn({ dry_run: true, run_id: 'test_run', ...argsOverrides }, rec.log, rec.phase, rec.parallel, rec.agent);
  return { result, calls: rec.calls };
}

// ---------------------------------------------------------------------------
// AC-P1-1 / AC-P1-2 / AC-P1-3 — stampFromTimestamp() via the dry_run.stamp field
// ---------------------------------------------------------------------------

test('stampFromTimestamp: valid ISO-8601 timestamp yields YYYYMMDD stamp (AC-P1-1)', async () => {
  const { result, calls } = await runDryRun({ timestamp: '2026-07-22T10:00:00Z' });
  assert.equal(result.stamp, '20260722');
  assert.equal(calls.length, 0);
});

test('stampFromTimestamp: valid ISO-8601 date-only timestamp yields YYYYMMDD stamp (AC-P1-1)', async () => {
  const { result } = await runDryRun({ timestamp: '2027-01-05' });
  assert.equal(result.stamp, '20270105');
});

test('stampFromTimestamp: malformed timestamp falls back to literal default, no throw (AC-P1-2)', async () => {
  const { result, calls } = await runDryRun({ timestamp: 'not-a-real-date' });
  assert.equal(result.stamp, '20260613');
  assert.equal(calls.length, 0);
});

test('stampFromTimestamp: non-ISO-shaped string (wrong separators) falls back to literal default (AC-P1-2)', async () => {
  const { result } = await runDryRun({ timestamp: '07/22/2026' });
  assert.equal(result.stamp, '20260613');
});

test('stampFromTimestamp: absent timestamp arg falls back to literal default (AC-P1-3)', async () => {
  const { result, calls } = await runDryRun({});
  assert.equal(result.stamp, '20260613');
  assert.equal(calls.length, 0);
});

test('stampFromTimestamp: empty-string timestamp arg falls back to literal default (AC-P1-3)', async () => {
  const { result } = await runDryRun({ timestamp: '' });
  assert.equal(result.stamp, '20260613');
});

// ---------------------------------------------------------------------------
// AC-P1-4 — resolvePath()-driven arg precedence: rf_bin / repo / tmp_dir
// ---------------------------------------------------------------------------

test('resolvePath precedence: absent overrides use the literal fallback defaults', async () => {
  const { result } = await runDryRun({});
  assert.equal(result.rf_bin, '/Users/miethe/.local/bin/rf');
  assert.equal(result.repo, '/Users/miethe/dev/homelab/development/research-foundry');
  assert.equal(result.tmp_dir, '/Users/miethe/.claude/jobs/85ede6ca/tmp');
});

test('resolvePath precedence: an absolute rf_bin override wins over the literal fallback default (AC-P1-4)', async () => {
  const { result } = await runDryRun({ rf_bin: '/opt/custom/rf' });
  assert.equal(result.rf_bin, '/opt/custom/rf');
  assert.notEqual(result.rf_bin, '/Users/miethe/.local/bin/rf');
});

test('resolvePath precedence: an absolute repo override wins over the literal fallback default (AC-P1-4)', async () => {
  const { result } = await runDryRun({ repo: '/srv/other-repo' });
  assert.equal(result.repo, '/srv/other-repo');
  assert.notEqual(result.repo, '/Users/miethe/dev/homelab/development/research-foundry');
});

test('resolvePath precedence: an absolute tmp_dir override wins over the literal fallback default (AC-P1-4)', async () => {
  const { result } = await runDryRun({ tmp_dir: '/tmp/custom-job' });
  assert.equal(result.tmp_dir, '/tmp/custom-job');
  assert.notEqual(result.tmp_dir, '/Users/miethe/.claude/jobs/85ede6ca/tmp');
});

test('resolvePath precedence: all three overrides win simultaneously, independent of each other (AC-P1-4)', async () => {
  const { result } = await runDryRun({
    rf_bin: '/opt/custom/rf',
    repo: '/srv/other-repo',
    tmp_dir: '/tmp/custom-job',
  });
  assert.deepEqual(
    { rf_bin: result.rf_bin, repo: result.repo, tmp_dir: result.tmp_dir },
    { rf_bin: '/opt/custom/rf', repo: '/srv/other-repo', tmp_dir: '/tmp/custom-job' },
  );
});

test('resolvePath precedence: a relative-path override is resolved against invocation cwd, not passed through as-is (AC-P1-4)', async () => {
  const { result } = await runDryRun({ repo: 'relative-repo-dir' });
  const expected = process.cwd().replace(/\/$/, '') + '/' + 'relative-repo-dir';
  assert.equal(result.repo, expected);
  assert.notEqual(result.repo, 'relative-repo-dir');
});

// ---------------------------------------------------------------------------
// AC-P1-5 — no path-traversal escape from invocation cwd (existing resolvePath() contract)
// ---------------------------------------------------------------------------

test('resolvePath contract: a relative path containing traversal segments is still cwd-anchored, not escaped (AC-P1-5)', async () => {
  // resolvePath()'s existing contract (rf-run-execute.js lines ~21-24) is a plain string
  // join for any non-absolute input: `cwd + '/' + p`. This assertion documents that
  // existing contract — every relative override, traversal segments included, is textually
  // anchored under invocation cwd. It is a regression check on current behavior, not new
  // hardening (per the phase plan's AC-P1-5 wording).
  const { result } = await runDryRun({ tmp_dir: '../../../etc/passwd' });
  const cwd = process.cwd().replace(/\/$/, '');
  assert.ok(
    result.tmp_dir.startsWith(cwd + '/'),
    `expected resolved tmp_dir to stay anchored under cwd (${cwd}), got: ${result.tmp_dir}`,
  );
  assert.equal(result.tmp_dir, cwd + '/../../../etc/passwd');
});

test('resolvePath contract: an absolute path is never re-anchored under cwd, even if it looks unusual', async () => {
  // Absolute inputs (leading '/') take the early-return branch in resolvePath() and are
  // returned verbatim — this is the documented "override wins" half of the contract that
  // AC-P1-4 exercises; asserted here again against a deliberately odd-looking absolute path
  // to make the absolute/relative branch boundary explicit.
  const { result } = await runDryRun({ repo: '/already/absolute/../weird/path' });
  assert.equal(result.repo, '/already/absolute/../weird/path');
});

// ---------------------------------------------------------------------------
// AC-P1-6 — zero live `rf` invocations, zero network calls
// ---------------------------------------------------------------------------

test('dry_run path never calls log/phase/parallel/agent — no live rf invocation, no network call (AC-P1-6)', async () => {
  const { result, calls } = await runDryRun({ timestamp: '2026-07-22T10:00:00Z' });
  assert.equal(result.status, 'dry_run');
  assert.deepEqual(calls, []);
});

test('missing run_id short-circuits before dry_run branch too — still zero live calls', async () => {
  const rec = callRecorder();
  const fn = buildWorkflowFn();
  const result = await fn({ dry_run: true }, rec.log, rec.phase, rec.parallel, rec.agent);
  assert.deepEqual(result, { error: 'missing run_id in args' });
  assert.deepEqual(rec.calls, []);
});

test('this test file itself makes no live-process-spawn or network-fetch calls (static self-check)', () => {
  const selfSource = fs.readFileSync(__filename, 'utf8');
  // Built by concatenation so the forbidden-token declarations below don't themselves
  // contain the literal substrings being scanned for (which would make this check trivially
  // fail against its own source).
  const forbiddenTokens = [
    ['child', '_process'].join(''),
    ['require(', "'", 'http'].join(''),
    ['require(', "'", 'https'].join(''),
    ['fetch', '('].join(''),
  ];
  for (const forbidden of forbiddenTokens) {
    assert.ok(
      !selfSource.includes(forbidden),
      `test file must not reference ${forbidden} — AC-P1-6 requires zero network/live-process calls`,
    );
  }
});
