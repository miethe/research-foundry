# Resume Prompt — Operator MCP P1 / close OPM-1.G

> Paste the block below verbatim to the executing agent. Everything it needs is either inline or
> reachable from the three READ-FIRST paths. Written 2026-07-29 against branch
> `worktree-operator-mcp-v1` @ `1ba320f`.

---

```
Close out P1 of research-foundry-operator-mcp so the OPM-1.G gate can pass.

WORKSPACE — do not deviate:
- Work in the EXISTING worktree .claude/worktrees/operator-mcp-v1 (branch worktree-operator-mcp-v1,
  draft PR #7, based on main 65d658d). Do NOT create a new worktree. Do NOT re-run P1 from scratch.
- Do NOT merge to main and do NOT start P2. P1 is 4 of 29 points; merging one of six phases would
  fragment the plan and put an uncalled authorization module on main whose gate has not passed.
- Commit to the branch as you go. Push is fine (the branch already tracks origin).

READ FIRST, in this order:
1. .claude/findings/research-foundry-operator-mcp-findings.md  — section FIND-P1-R3 (the six
   blocking findings, the Karen queue, and the methodology trap). This is the work order.
2. docs/project_plans/human-briefs/operator-mcp-p1-execution-retro.md  — §4 and §5.
3. docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md  — the
   "Implementer Defect-Class Checklist (mandatory)" section and the "Revised gate structure
   (post-P1 retro)" section. The revised gate table is authoritative; ignore any older gate text.

═══════════════════════════════════════════════════════════════════════════════
WORK ORDER
═══════════════════════════════════════════════════════════════════════════════

STEP 1 — Close the six blocking findings, IN THIS ORDER. The order is the reviewer's; keep it.

  NEW-23 (HIGH) — Serve-extra import boundary claim is false.
    `import operator_mcp_policy` fails without fastapi/uvicorn installed, breaking the local-stdio
    topology P5 explicitly declares.
    FIX: break the transitive import so the policy module imports cleanly in a base install. Add a
    test that imports it with the serve extra absent.

  NEW-18 (HIGH) — PolicyContext.identity is caller-supplied.
    Decisions-block Risk 1 is rated *critical* ("no default workspace on mutation"; configured-local
    identity only), but the mitigation here is prose, not shape — a caller can hand in an identity
    rather than having it derived.
    FIX: make identity derivation STRUCTURAL. Resolve inside the policy module from configured local
    config, or make the caller-supplied path unreachable from the public API.
    ⚠ This is a textbook "fix the layer below" case (see checklist item 2). Enumerate EVERY public
    entry point, not just PolicyContext, and prove none of them still accepts an injected identity.

  NEW-22 (HIGH) — `researcher` granted agent-job-class operations that api/auth/rbac.py reserves for
    owner/admin. The written justification is factually wrong.
    FIX: align the role grants with rbac.py's convention, OR justify the divergence with an accurate
    rationale. Karen adjudicates this one (see Step 4) — but the false justification text must be
    corrected either way.

  NEW-20 (MED-HIGH) — `denial_reason_code` is an open string despite BOTH the receipt schema and the
    completion note claiming a closed enum.
    FIX: close the enum in schema and code; add a negative fixture.

  NEW-21 (MED) — `audit_delivery.detail` accepts raw tracebacks; its natural producer is str(exc).
    Violates AC OPM-7's bounded/redacted requirement.
    FIX: apply the same _SAFE_MESSAGES / redact-then-cap treatment already used for the error envelope.

  NEW-19 (MED) — Audit-health is permanently bricked after the first failed probe, with an
    unachievable retryable=True. The NEW-3 fix overcorrected.
    FIX: allow recovery — re-probe on a later call rather than latching the failure.

STEP 2 — Re-derive the non-blocking findings.
  NEW-15, NEW-16, NEW-17, NEW-24, NEW-25 plus documentation nits exist but their DETAIL WAS NEVER
  CAPTURED. Do not treat their absence from the ledger as "no findings". Re-derive them by re-running
  the consolidated gate, or by asking the reviewer to re-emit only the non-blocking rows. Record them
  in the ledger with real detail, then fix or explicitly defer each with a reason.

STEP 3 — Re-run the consolidated security + validation gate on the resulting exact tree.
  Both lenses. A material fix invalidates any prior exact-tree approval, so this runs LAST, after all
  edits are final.
  Pay particular attention to schemas/operator_mcp_receipt.schema.yaml: it had never been
  adversarially attacked before round 3, and two of the six blocking findings came from its first
  real review. Treat it as STILL UNDER-REVIEWED — do not assume it is now clean.

STEP 4 — Run Karen, with exactly these three queued adjudications:
  1. PART C ratification of the governance.py serialization-barrier write. The reviewer recommends
     ACCEPT WITH CONDITIONS: it is a provable no-op for the shipped config, restores redact_payload's
     own documented "additional" contract, and is strictly fail-closed. (Context: config
     secret_patterns now UNION with built-ins rather than replacing them; governance.py is a declared
     serialization-barrier file outside P1's phase ownership, so this needs explicit ratification.)
  2. FIND-P1-B — the net-new _MUTATION_ROLES/_READ_ROLES primitive, now carrying NEW-22's concrete
     privilege-escalation dimension. It is no longer a style question.
  3. The governance.preflight() deviation from decisions-block line 30.

═══════════════════════════════════════════════════════════════════════════════
MANDATORY DEFECT-CLASS CHECKLIST — apply to every fix you write
═══════════════════════════════════════════════════════════════════════════════
These four classes recurred in EVERY P1 review round, and the fix cycle itself introduced new
instances of them while "closing" prior findings.

1. NO FAIL-OPEN DEFAULTS. No permissive default on a security-relevant field, no None-means-skip, no
   unknown-label fallback that grants rather than denies. Check the PRODUCER of a value, not just the
   field — NEW-4 survived round 1 because the field default was removed while the function producing
   it still returned "public".

2. FIX THE LAYER BELOW. After hardening a symbol, enumerate its delegates, callers, and __all__
   siblings and ask whether reaching for any of them yields the unsafe behavior. This is what found
   the critical defect in round 2: the fix hardened authorize_operation while its delegate
   verify_confirmation still reported the replay as an accept — and the new docstring steered callers
   to the weaker door.

3. NEVER PIN UNSAFE BEHAVIOR WITH A TEST. If a test asserts current behavior and the current behavior
   is wrong, the test is wrong. Say so and invert it. Three round-2 defects were pinned as correct by
   tests the fix cycle itself wrote.

4. NEVER FABRICATE A VALIDATION TRANSCRIPT. Paste real output or report the failure. A fabricated
   transcript was caught in round 1.

═══════════════════════════════════════════════════════════════════════════════
TRAPS — read before running anything
═══════════════════════════════════════════════════════════════════════════════

⚠ PYTEST PYTHONPATH TRAP (highest-value gotcha; a reviewer nearly published a wrong conclusion off it)
  pyproject.toml sets [tool.pytest.ini_options] pythonpath = ["src"], which pytest inserts AHEAD OF
  the PYTHONPATH env var. A mutation sweep against a scratch copy therefore silently tests the REAL
  worktree source and reports false negatives ("no test detects this defect").
  - Correct form: --override-ini="pythonpath=<scratch>/src"
  - Mirror config/, schemas/, templates/ into the scratch root (distribution_root() resolves via
    parents[2]); purge stale __pycache__; always establish a baseline first.
  - `python -c "import x; print(x.__file__)"` is NOT a sufficient check — it exercises the env var
    that pytest then overrides.
  - Any PYTHONPATH=$PWD/src prefix is decorative and is not evidence of an isolated run.

⚠ DO NOT USE CODEX for the security lens here. `codex exec` REFUSED the adversarial security-audit
  framing under its safety classifier after burning a long reasoning trace. That is a policy refusal
  on their side, not a config problem. (Unrelated but true: pipe prompts via stdin, not as an
  argument — the arg form hangs waiting on stdin.)

⚠ DO NOT USE phase-owner agents. They cannot reliably dispatch nested Task() in this environment,
  which historically caused them to implement directly or emit false passes. Dispatch implementers
  directly — that worked cleanly for P1.

⚠ RE-RUN THE SUITE YOURSELF after every agent. It costs ~2k tokens and is how a fabricated validation
  transcript was contradicted with real evidence. An agent's self-reported test output is not evidence.

⚠ PRE-EXISTING, DO NOT CHASE: tests/test_verification_pediatric_cds.py and
  tests/test_verification_seam001_gate_composition.py fail to COLLECT under -k filtering (sibling
  `import test_claim_verifier`). Present on base 65d658d.

⚠ THERE IS NO .venv IN THIS WORKTREE. Use the main checkout's interpreter, invoked FROM the worktree
  root (verified working 2026-07-29):
      /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest <args>
  Run it with the worktree as cwd. pytest resolves pyproject's pythonpath=["src"] relative to rootdir
  (= the worktree), so it correctly picks up WORKTREE source — no PYTHONPATH prefix needed, and
  adding one changes nothing (see the trap above). Do NOT use the pyenv shim: it gives "No module
  named research_foundry".
  Baseline confirmed: `... -m pytest tests/unit/test_operator_mcp_policy.py -q` → 105 passed, exit 0,
  which reproduces the reviewer's reported count exactly. Establish this baseline before your first
  edit.
  Note this repo's pytest config suppresses the "N passed" summary line — trust the exit code.

═══════════════════════════════════════════════════════════════════════════════
COST DISCIPLINE
═══════════════════════════════════════════════════════════════════════════════
P1 has already cost ~2.4M tokens for 4 of 29 points. Before dispatching an expensive Opus reviewer,
run a focused ~30k-token Sonnet fail-open / layer-below sweep over the changed surface; escalate to
the full lens only for what survives. This is an addition to the gates, never a replacement.

═══════════════════════════════════════════════════════════════════════════════
DEFINITION OF DONE
═══════════════════════════════════════════════════════════════════════════════
[ ] All six blocking findings marked `fixed` in the ledger, each with a real (not fabricated) test
    that fails when the fix is reverted.
[ ] NEW-15/16/17/24/25 re-derived, recorded with real detail, and each fixed or explicitly deferred
    with a stated reason.
[ ] Consolidated security + validation gate re-run on the FINAL exact tree and reported clean.
[ ] Karen run with all three queued adjudications, each with an explicit verdict.
[ ] OPM-1.G recorded as APPROVED (or, if it still fails, a new FIND-P1-R4 section with the same
    rigor — a partial pass is not a pass).
[ ] Findings ledger and .claude/progress/research-foundry-operator-mcp/phase-1-progress.md updated
    to match reality.
[ ] Committed to worktree-operator-mcp-v1. NOT merged to main. P2 NOT started.

Report at the end: which findings closed, what the gate and Karen actually said (quote them), what
you could not close and why. If you disagree with a finding, say so and argue it — do not silently
skip it and do not mark it fixed.
```
