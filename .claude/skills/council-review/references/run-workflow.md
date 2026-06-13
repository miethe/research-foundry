# Council Run Workflow

## 1. Confirm The Run Contract

Before review work begins, restate:

- Target artifacts or workflows.
- Objective and success criteria.
- Council definition from `councils/`.
- Constraints such as read-only mode, no network, time box, allowed commands, and excluded paths.
- Required outputs.

If the request is a review, do not modify source artifacts unless the user explicitly asks for implementation or remediation.

## 2. Build The Evidence Pack

Create `runs/<date>-<slug>/evidence_pack.md` from `templates/evidence_pack.md`.

Include:

- Source artifacts and source-of-truth files.
- Expected user or operator workflows.
- Constraints and assumptions.
- Deterministic checks already run.
- Open questions and evidence gaps.

Every material claim used later in the run should trace back to this pack or to a cited reviewer note.

## 3. Run Independent Reviewer Passes

Delegate to subagents when available and reasonable for the scope. Use the council definition to decide reviewers. Keep reviewer findings isolated until the independent pass is complete.

When subagents are unavailable, perform separate reviewer passes with isolated notes:

- Evidence scribe first.
- Specialist reviewers next.
- Skeptic/red-team after initial specialist passes.
- Adjudicator last.

Reviewer outputs should be high signal, not exhaustive commentary.

## 4. Adjudicate

The adjudicator should:

- Deduplicate overlapping findings.
- Preserve dissent and unresolved disputes.
- Assign severity and confidence using evidence quality.
- Reject findings that are unsupported, out of scope, or only stylistic.
- Move plausible but unproven observations to watchlist.
- Add validation steps for accepted and disputed findings.

## 5. Close The Run

Write the full artifact set under `runs/<date>-<slug>/`.

Run:

```bash
uv run arc validate runs/<date>-<slug>
```

Final responses should summarize the decision, top findings, validation result, and remaining risks without replacing the durable run artifacts.
