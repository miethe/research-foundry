// Test harness: Node's built-in `node:test` + `node --test` — same project-level decision as
// rf-run-execute.test.js (see that file's header), recorded in
// docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-1-pathb-tests.md
// ("Decisions in force"). No new dependency introduced.
//
// Target under test: .claude/workflows/rf-pediatric-cds-run-execute.js is a Claude Code Dynamic
// Workflow script. It is READ-ONLY here — never edited, only read and executed in-memory.
//
// UNLIKE rf-run-execute.js, this script has NO `dry_run` branch and NO `stampFromTimestamp()` /
// `resolvePath()` helper functions at all:
//   - `STAMP` is `A.stamp || '20260718'` — a plain `||` fallback on the raw arg string, with
//     zero date parsing or format validation. A "malformed" (non-YYYYMMDD-shaped) stamp is used
//     VERBATIM, not rejected/replaced — only a falsy `stamp` (absent or `''`) falls back.
//   - `REPO`/`RF`/`TMP` are plain `||` fallbacks too; there is no cwd-join / path-resolution
//     helper anywhere in this file (grep confirms no `function resolvePath` exists here). A
//     relative or traversal-shaped override is stored and used exactly as passed, never
//     re-anchored under invocation cwd.
//   - `RF`'s fallback is `REPO + '/.venv/bin/rf'` — the DIRECT local venv binary — NOT the
//     `~/.local/bin/rf` shim that `rf-run-execute.js` falls back to (that shim SSHes to the
//     node; see this script's own inline comment on line 27). Because `RF`'s fallback derives
//     from `REPO`, overriding `repo` alone (with `rf_bin` absent) changes the resolved `RF`
//     value too — asserted explicitly below, not just the literal-default case.
//
// To reach these resolved values with zero live `agent`/`parallel` calls (AC-P1-10), this suite
// reads the file, strips the leading `export ` keyword from an in-memory copy only (so the body
// parses as a function body instead of a module — identical technique to rf-run-execute.test.js),
// then TRUNCATES that in-memory copy at the literal `// ====== ORCHESTRATION ======` comment
// (confirmed present via an assertion below, so a future edit that moves/removes it fails this
// suite loudly instead of silently). Everything before that marker is pure declarations (schemas,
// templates, prompt-builder function bodies that are never invoked) plus the `if (!run) return`
// guard — none of it calls `log`/`phase`/`parallel`/`agent`. The real script's first live call is
// `log(...)` on the first orchestration line, which this truncation never reaches. An explicit
// `return { REPO, RF, TMP, STAMP, MODE, run }` is appended after the cut so the resolved values
// are observable without ever touching the orchestration body. No transformation is written back
// to the target script file.
//
// No `Date.now()`/`new Date()` is used anywhere in this file (four-constraints checklist,
// applied to the tests too, per the phase plan's Quality Gates).

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const SCRIPT_PATH = path.join(__dirname, '..', 'rf-pediatric-cds-run-execute.js');
const RAW_SOURCE = fs.readFileSync(SCRIPT_PATH, 'utf8');

// Strip only the leading `export ` keyword (this script's sole `export`, on line 1) so the
// source parses as a function body rather than an ES module — same in-memory-only transform as
// rf-run-execute.test.js. SCRIPT_PATH itself is never opened for writing.
const EXPORT_STRIPPED = RAW_SOURCE.replace(/^export /, '');
assert.notStrictEqual(
  EXPORT_STRIPPED,
  RAW_SOURCE,
  'expected rf-pediatric-cds-run-execute.js to start with `export ` — the strip-and-wrap harness assumption changed; update this test file, not the target script',
);

// Truncate at the literal orchestration-section marker so the wrapped function body never
// reaches a `log`/`phase`/`parallel`/`agent` call. Everything before this marker is pure
// declarations plus the `if (!run) return` guard.
const ORCHESTRATION_MARKER = '// ====================== ORCHESTRATION ======================';
const markerIndex = EXPORT_STRIPPED.indexOf(ORCHESTRATION_MARKER);
assert.ok(
  markerIndex > 0,
  'expected to find the ORCHESTRATION section marker in rf-pediatric-cds-run-execute.js — the truncation point this suite relies on changed; update this test file, not the target script',
);

const RESOLUTION_PREFIX = EXPORT_STRIPPED.slice(0, markerIndex);
const RESOLUTION_BODY = RESOLUTION_PREFIX + '\nreturn { REPO, RF, TMP, STAMP, MODE, run };';

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

// A fresh AsyncFunction per call keeps each test's stub closures independent.
function buildResolutionFn() {
  return new AsyncFunction('args', 'log', 'phase', 'parallel', 'agent', RESOLUTION_BODY);
}

// Records every call made to any of the four harness-injected callbacks. Each stub throws so
// that, if the truncation point above ever stops matching the real script's shape (e.g. a
// future edit moves a live call above the ORCHESTRATION marker), the test fails loudly instead
// of silently making a "live" call.
function callRecorder() {
  const calls = [];
  const stub = (name) => (...callArgs) => {
    calls.push({ name, args: callArgs });
    throw new Error(`unexpected live call to ${name}() during a resolution-only test`);
  };
  return {
    calls,
    log: stub('log'),
    phase: stub('phase'),
    parallel: stub('parallel'),
    agent: stub('agent'),
  };
}

// Runs the truncated (pre-orchestration) script body with the given args. Returns the resolved
// { REPO, RF, TMP, STAMP, MODE, run } object, or the script's own `{ error: ... }` early return
// (e.g. when run_id is missing), plus the list of any (unexpected) harness-callback calls made.
async function runResolution(argsOverrides) {
  const rec = callRecorder();
  const fn = buildResolutionFn();
  const result = await fn({ run_id: 'test_run', ...argsOverrides }, rec.log, rec.phase, rec.parallel, rec.agent);
  return { result, calls: rec.calls };
}

// ---------------------------------------------------------------------------
// AC-P1-7 — STAMP resolution: valid arg / malformed arg (verbatim, NOT fallback) / absent arg
// ---------------------------------------------------------------------------

test('STAMP: an explicit valid-shaped stamp arg is used verbatim (AC-P1-7)', async () => {
  const { result, calls } = await runResolution({ stamp: '20270105' });
  assert.equal(result.STAMP, '20270105');
  assert.equal(calls.length, 0);
});

test('STAMP: a malformed (non-YYYYMMDD) stamp arg is used VERBATIM, not replaced with the fallback (AC-P1-7)', async () => {
  // Unlike rf-run-execute.js's stampFromTimestamp() (Date-parses and falls back on invalid
  // input), this script's STAMP is a plain `||` — there is no format validation at all, so a
  // malformed string is truthy and passes straight through. Asserting this distinction (rather
  // than a false "falls back on malformed input" claim) is the correct coverage for this
  // script's actual resolution logic.
  const { result } = await runResolution({ stamp: 'not-a-real-stamp' });
  assert.equal(result.STAMP, 'not-a-real-stamp');
  assert.notEqual(result.STAMP, '20260718');
});

test('STAMP: absent stamp arg falls back to the literal default 20260718 (AC-P1-7)', async () => {
  const { result, calls } = await runResolution({});
  assert.equal(result.STAMP, '20260718');
  assert.equal(calls.length, 0);
});

test('STAMP: empty-string stamp arg falls back to the literal default (falsy, same as absent) (AC-P1-7)', async () => {
  const { result } = await runResolution({ stamp: '' });
  assert.equal(result.STAMP, '20260718');
});

// ---------------------------------------------------------------------------
// AC-P1-8 — REPO / RF / TMP override precedence, including the direct-venv-binary distinction
// ---------------------------------------------------------------------------

test('REPO/RF/TMP: all absent overrides resolve to the literal fallback defaults', async () => {
  const { result } = await runResolution({});
  assert.equal(result.REPO, '/Users/miethe/dev/homelab/development/research-foundry');
  assert.equal(result.RF, '/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/rf');
  assert.equal(result.TMP, '/Users/miethe/dev/homelab/development/research-foundry/.claude/tmp/rf-peds-swarm');
});

test('REPO/RF/TMP: RF fallback is the direct local venv binary path, NOT the ~/.local/bin/rf shim (AC-P1-8)', async () => {
  // This is the explicit distinction the phase plan calls out: rf-run-execute.js's RF fallback
  // is the `~/.local/bin/rf` shim (asserted in rf-run-execute.test.js); this script's RF
  // fallback is instead `REPO + '/.venv/bin/rf'` — a direct local binary invocation, never the
  // shim. A test that didn't check this would pass falsely if the two scripts' fallbacks were
  // ever collapsed together.
  const { result } = await runResolution({});
  assert.equal(result.RF, result.REPO + '/.venv/bin/rf');
  assert.notEqual(result.RF, '/Users/miethe/.local/bin/rf');
  assert.ok(!result.RF.includes('.local/bin/rf'), `expected RF fallback to avoid the shim path, got: ${result.RF}`);
});

test('REPO/RF/TMP: an explicit repo override wins over its literal fallback default (AC-P1-8)', async () => {
  const { result } = await runResolution({ repo: '/srv/other-peds-repo' });
  assert.equal(result.REPO, '/srv/other-peds-repo');
  assert.notEqual(result.REPO, '/Users/miethe/dev/homelab/development/research-foundry');
});

test('REPO/RF/TMP: overriding repo alone (rf_bin/tmp absent) re-derives RF and TMP from the NEW repo, not the original default (AC-P1-8)', async () => {
  // RF and TMP's fallbacks are `REPO + '/...'` expressions, not independent hardcoded absolute
  // defaults — so overriding just `repo` changes their resolved values too. This is the
  // precedence-interaction half of AC-P1-8 that a naive "assert RF/TMP unaffected by repo"
  // test would miss.
  const { result } = await runResolution({ repo: '/srv/other-peds-repo' });
  assert.equal(result.RF, '/srv/other-peds-repo/.venv/bin/rf');
  assert.equal(result.TMP, '/srv/other-peds-repo/.claude/tmp/rf-peds-swarm');
});

test('REPO/RF/TMP: an explicit rf_bin override wins over the repo-derived RF fallback, even with repo also overridden (AC-P1-8)', async () => {
  const { result } = await runResolution({ repo: '/srv/other-peds-repo', rf_bin: '/opt/custom/rf' });
  assert.equal(result.RF, '/opt/custom/rf');
  assert.notEqual(result.RF, '/srv/other-peds-repo/.venv/bin/rf');
});

test('REPO/RF/TMP: an explicit tmp override wins over the repo-derived TMP fallback (AC-P1-8)', async () => {
  const { result } = await runResolution({ tmp: '/tmp/custom-peds-job' });
  assert.equal(result.TMP, '/tmp/custom-peds-job');
  assert.notEqual(result.TMP, result.REPO + '/.claude/tmp/rf-peds-swarm');
});

test('REPO/RF/TMP: all three overrides win simultaneously, independent of each other (AC-P1-8)', async () => {
  const { result } = await runResolution({
    repo: '/srv/other-peds-repo',
    rf_bin: '/opt/custom/rf',
    tmp: '/tmp/custom-peds-job',
  });
  assert.deepEqual(
    { REPO: result.REPO, RF: result.RF, TMP: result.TMP },
    { REPO: '/srv/other-peds-repo', RF: '/opt/custom/rf', TMP: '/tmp/custom-peds-job' },
  );
});

test('mode: defaults to clinical when mode arg is absent', async () => {
  const { result } = await runResolution({});
  assert.equal(result.MODE, 'clinical');
});

test('mode: an explicit mode override wins over the literal default', async () => {
  const { result } = await runResolution({ mode: 'regulatory' });
  assert.equal(result.MODE, 'regulatory');
});

// ---------------------------------------------------------------------------
// AC-P1-9 — no path-traversal escape from invocation cwd (existing resolution contract)
// ---------------------------------------------------------------------------

test('REPO/RF/TMP contract: this script has no resolvePath()/cwd-join helper at all — grep confirms', () => {
  // Regression check on the *absence* of a path-resolution helper in this file (unlike
  // rf-run-execute.js, which has one). Documented here so the traversal assertion below is
  // read against the correct baseline contract, not an assumed-but-nonexistent one.
  assert.ok(
    !RAW_SOURCE.includes('function resolvePath'),
    'expected rf-pediatric-cds-run-execute.js to have no resolvePath() helper — if one was added, this suite\'s traversal assertions need updating to match it',
  );
});

test('REPO/RF/TMP contract: a traversal-shaped repo override is stored and used VERBATIM, never expanded or re-anchored (AC-P1-9)', async () => {
  // Because there is no cwd-join step (see the prior test), a relative/traversal-shaped
  // override cannot be "escaped" further than the literal string supplied — it is passed
  // straight through unchanged. This is a regression assertion on current (absent) resolution
  // behavior, not new hardening, matching the phase plan's AC-P1-9/AC-P1-5 wording.
  const { result } = await runResolution({ repo: '../../../etc/passwd' });
  assert.equal(result.REPO, '../../../etc/passwd');
  assert.ok(
    !path.isAbsolute(result.REPO),
    'expected the traversal-shaped override to remain exactly as supplied (relative), with no cwd-anchoring applied',
  );
});

test('REPO/RF/TMP contract: an absolute override with unusual segments is stored verbatim too', async () => {
  const { result } = await runResolution({ tmp: '/already/absolute/../weird/tmp-path' });
  assert.equal(result.TMP, '/already/absolute/../weird/tmp-path');
});

// ---------------------------------------------------------------------------
// AC-P1-10 — zero live `rf` invocations, zero network calls
// ---------------------------------------------------------------------------

test('resolution-only truncated body never calls log/phase/parallel/agent (AC-P1-10)', async () => {
  const { result, calls } = await runResolution({ stamp: '20270101' });
  assert.equal(result.STAMP, '20270101');
  assert.deepEqual(calls, []);
});

test('missing run_id short-circuits before the resolution return too — still zero live calls', async () => {
  const rec = callRecorder();
  const fn = buildResolutionFn();
  const result = await fn({}, rec.log, rec.phase, rec.parallel, rec.agent);
  assert.deepEqual(result, { error: 'missing run_id in args' });
  assert.deepEqual(rec.calls, []);
});

test('this test file itself makes no live-process-spawn or network-fetch calls (static self-check)', () => {
  const selfSource = fs.readFileSync(__filename, 'utf8');
  // Built by concatenation so the forbidden-token declarations below don't themselves contain
  // the literal substrings being scanned for (which would make this check trivially fail
  // against its own source).
  const forbiddenTokens = [
    ['child', '_process'].join(''),
    ['require(', "'", 'http'].join(''),
    ['require(', "'", 'https'].join(''),
    ['fetch', '('].join(''),
  ];
  for (const forbidden of forbiddenTokens) {
    assert.ok(
      !selfSource.includes(forbidden),
      `test file must not reference ${forbidden} — AC-P1-10 requires zero network/live-process calls`,
    );
  }
});

test('target script itself is never opened for writing by this suite (static self-check)', () => {
  const selfSource = fs.readFileSync(__filename, 'utf8');
  // Built by concatenation, same reasoning as the forbidden-network-tokens check above: the
  // token literals must not appear verbatim in this declaration, or the check would trivially
  // fail against its own source.
  const writeCallTokens = [
    ['write', 'FileSync'].join(''),
    ['append', 'FileSync'].join(''),
    ['create', 'WriteStream'].join(''),
  ];
  for (const token of writeCallTokens) {
    assert.ok(
      !selfSource.includes(token),
      `test file must not write to any file (including the read-only target script) — found ${token}`,
    );
  }
});
