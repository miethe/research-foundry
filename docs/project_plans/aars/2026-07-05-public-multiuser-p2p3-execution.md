---
doc_type: aar
title: "AAR — Public Multi-User Release P2+P3 Execution"
date: 2026-07-05
feature_slug: public-multiuser-release
outcome: shipped
---

# AAR — Public Multi-User Release P2+P3 Execution

## Outcome
Phase 2 (Granular Report Audit) + Phase 3 (Report Builder) executed via wave-driven
orchestration (Opus 4.8 orchestrator; Sonnet subagents; ICA Sonnet 4.6 for bounded backend
waves; Fable for visual-fidelity review) and squash-merged to `main` — PR #2 (`8b9d8be`),
PR #3 (`cb6af8b`). Both adversarially reviewed; **R2 caught two critical security bugs
pre-merge that would otherwise have shipped to a public multi-user release.**

## What worked
- **Adversarial review is non-negotiable — it earns its cost.** R2's in-session reviewer
  found (a) a path-traversal primitive — the draft-id guard was a *prefix* check
  (`report_id.startswith("rpt_")`), so `rpt_../../..` sailed through → arbitrary file read
  (bypassing sensitivity redaction) + arbitrary `rmtree`; and (b) a **fail-OPEN** sensitivity
  gate — `check_report_body_sensitivity` only scanned *linked* quotes, so an unlinked pasted
  sensitive quote passed publish-preview. Opus's own crown-jewel adjudication verified the
  fail-closed *mechanism* but missed *what it scanned*. Both fixed + regression-tested.
- **A dedicated visual-fidelity gate (Fable) is worth it for UI deliverables.** It took the
  builder from a 2.5/5 "wireframe-grade" render to a faithful mockup match (clipped textareas,
  detached outline, generic inspector → fixed). Behavioral/unit gates cannot catch this.
- **Trust-but-verify every delegate, always re-run authoritative gates.** Re-running caught an
  ICA cross-tree collision, a schema-registry test regression, and the E↔F DELETE shape mismatch.

## Process lessons (fix next time)
1. **Scope bounded/ICA waves STRICTLY to their file tree.** Handing backend Wave B a "D4 parity
   directive" made it edit *frontend* files, colliding with the parallel frontend Wave C. A
   shared-contract directive that implies cross-tree edits breaks the disjoint-file guarantee
   that makes parallel waves safe. Fix: enumerate the exact files a delegate may touch; assign
   shared-contract artifacts a single explicit owner.
2. **`codex exec` hung repeatedly (~3h) in this environment — unusable.** Fall back to in-session
   reviewers promptly; hard-timeout external CLIs and don't burn hours retrying a hang.
3. **Integration reconciliation must diff response SHAPES, not just paths.** The `reorder`
   method mismatch was caught by a path diff; the DELETE `204`-vs-`ReportDraft` mismatch was only
   caught by the reviewer. Diff both, and prefer a live loopback smoke.
4. **A "fail-closed" gate that checks the wrong thing is fail-open.** Verify the *scope* of a
   security check, not just that it returns 422.
5. **Prefix-check guards on caller-controlled ids are a recurring security trap.** Use full-string
   `fullmatch` regex + `resolve()`/containment for any id joined to a filesystem path.

## Deferred to P5 (tracked)
- Runs-read API endpoints lack run-level sensitivity existence-gating (pre-existing).
- P3 blank-origin-draft body-sensitivity residual: an unlinked quote from a run the draft can't
  reach isn't scanned (needs a global source index).
- Draft→run/claim reverse catalog links; anchor-hash-match is warning-severity (non-blocking).
