---
type: findings
schema_version: 2
doc_type: findings
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: open
created: '2026-07-31'
updated: '2026-07-31'
---

# M1 remainder — consolidated pre-gate findings (tree `fcfcd89`)

Two independent cheap pre-gate lenses, run in parallel on the same tree:
**gpt-5.6-terra** (codex, high effort) and **ICA claude-sonnet-5[1m]**.
Raw ICA report: `m1-remainder-pregate-ica.md`.

**Lens-diversity result, again.** Both lenses independently confirmed F1 and F6. Each found
defects the other missed entirely: codex alone found F2, F3, F4, F5; ICA alone empirically
*strengthened* F1 (it does not raise — it silently succeeds) and independently reproduced F6
across a real workspace boundary. ICA refuted H3 while codex found a *different* defect in the
same file (F2). Neither lens is a superset of the other.

| ID | Sev | File | Found by |
|---|---|---|---|
| F1 | **BLOCKING** | `research_stages.py` | both |
| F2 | HIGH | `external_import.py` | codex |
| F3 | **BLOCKING** | `source_ingest.py` | codex |
| F4 | **BLOCKING** | `source_ingest.py` | codex |
| F5 | HIGH | `verify_bundle.py` | codex |
| F6 | HIGH | `verify_bundle.py` | both |
| F7 | LOW | `research_stages.py` | both |

## F1 — BLOCKING — missing secondary artifacts are treated as present

`research_stages.py:322` (and `synthesis.py:44`). `run.claim_map` / `run.synthesize` declare the
required secondary target kind (`extraction_card` / `claim_ledger`) but never check its on-disk
existence; preflight only compares target-kind *labels*.

Failure scenario (ICA reproduced it empirically): a valid, owned run with **zero extraction cards**
returns `ok=True, claims_total=0` from `run.claim_map`; a valid, owned run with **no claim ledger**
returns `ok=True` with a fully "completed" **placeholder report** from `run.synthesize` — because
`_load_ledger()` returns an empty ledger rather than failing. Neither denies with a reason code.

This violates the M1 AC ("missing-input cases deny with reason codes"). It is worse than the
original hypothesis, which predicted a raise: silent success is strictly more dangerous than a
crash, because a placeholder report is indistinguishable from a real one downstream.

`verify_bundle.py` in this same commit implements exactly this prerequisite-gate pattern for
`run.verify` / `run.bundle`. The pattern was known and simply not applied here.

## F2 — HIGH — external import can mutate a foreign run via `target_run_id`

`external_import.py:170,193`; `external_research_import.py:611`. Configured identity `ws-mine`;
caller supplies `workspace_id="ws-mine"` (which *is* correctly re-derived and checked) together
with a `target_run_id` owned by `ws-other`. Policy authorizes only the import-packet workspace;
the canonical service then records import activity on the foreign run. Tests cover a mismatched
`workspace_id` but never a foreign `target_run_id`.

Note the shape: the guard that exists is correct, and the bypass is via a *sibling parameter* the
guard does not cover — defect class 2 ("fix the layer below") in its detection form.

## F3 — BLOCKING — `source.ingest` trusts caller-selected sensitivity

`source_ingest.py:111,159`. The adapter resolves its effective sensitivity from a **caller-supplied**
`sensitivity` value (permissive default `"personal"`), and the service persists that same caller
label. A caller under a `public` ceiling can submit sensitive `content` labelled
`sensitivity="public"`; the ceiling guard compares against the caller's own claim and permits it.

This is defect class 1 verbatim: a security-relevant classification that is caller-controlled rather
than structurally derived. §D1 removed the `sensitivity_ceiling` parameter but left its *sibling*
input caller-controlled — the exact "check the producer, not the field" failure the checklist warns
about.

## F4 — BLOCKING — confirmation does not bind ingested content

`source_ingest.py:161,197`. `content`, `extra_limitations`, and `created_by_agent` are **omitted
from the canonical confirmation payload** but forwarded to the effect. A confirmation minted for
absent/benign content can therefore execute arbitrary replacement content — a confirmation-binding
bypass.

**The parity test pins the unsafe behavior** (defect class 3): it mints a context *without*
`content` (`test_operator_mcp_adapter_source_ingest.py:57`), then successfully invokes *with*
content (`:109`), and asserts success. The test must be inverted, not extended.

This finding sits on the P1 confirmation-binding surface and is **MUST-stay-claude-primary**.

## F5 — HIGH — `run.verify` authorizes only the run, not its explicit inputs

`verify_bundle.py:347,388`; `verification.py:788`. An authorized caller for run A supplies absolute
`report_path` / `claim_ledger_path` pointing under run B in another workspace. The adapter performs
no existence/ownership check on explicit inputs; the canonical verifier accepts absolute paths,
writes a verification record for A, and writes `verification_status` back into **B's** ledger. No
policy target represents or authorizes those inputs. No test covers foreign or absolute paths.

## F6 — HIGH — verify/bundle prerequisites leak target existence before authorization

`verify_bundle.py:388,552`. Prerequisite checks run **before** authorization, so reason codes
distinguish run states the caller is not entitled to observe: a foreign run that *has* the required
artifacts returns `not_found`, while a nonexistent/incomplete run returns `preflight_failed`. An
unauthorized caller can therefore probe whether a run they do not own has reached the report+ledger
stage, or has a passing verification. ICA confirmed this empirically across a real workspace
boundary.

This is also why the H7 ceiling tests had to substitute a wrong-workspace comparison for the
exemplar's missing-target comparison — the substitution was a *symptom* of this leak, not merely a
stylistic deviation.

## F7 — LOW — the second declared target is an inert duplicate

`research_stages.py`. The secondary target uses the run ID as its ref and resolves to the same
workspace as the primary `run` target, so its authorization check is a provable no-op. Not
independently exploitable (no caller can select a foreign extraction-card/ledger object), but it
provides none of the defense-in-depth its presence implies — and the redundancy is what let F1
through. Document it honestly or make it load-bearing; do not leave it looking like a check.

## Refuted (recorded — a refutation is a result)

- **H3** — `external_import`'s declared `workspace_id` is **not** self-attested: it is re-derived
  against fresh configured identity and mismatches deny (`operator_mcp_policy.py:1331`). Both
  lenses agree. (F2 is a different hole in the same file.)
- **H5** — the `sensitivity_ceiling` pattern is correctly reproduced at **all seven** new
  boundaries: resolved structurally, no caller parameter, fail-closed to `"public"`. Both lenses
  verified per-adapter rather than generalizing. (F3 is a *sibling* input, not the ceiling itself.)
- **H6** — `run.bundle` cannot report a false success: it requires literal `passed is True`, then
  re-verifies through `build_bundle`; a fresh failed verification yields an unapproved draft and an
  adapter failure.
- **H2** — no cross-workspace path via the secondary target (downgraded to F7).
