# Research Foundry

**The problem with AI-assisted research is not the research — it's the claims.**

Every synthesis tool, agent swarm, and deep-research pipeline today produces compelling text. None of them guarantee that the claims inside that text trace back to a real source. You get polished output and then spend hours trying to figure out what is actually true.

Research Foundry is an evidence-first, Markdown/YAML-first research control plane that solves this at the mechanism level. It captures raw ideas, runs governed research swarms, and builds an auditable **claim ledger** — a per-claim register that every material sentence in a report must resolve against before `rf verify` will exit 0. Nothing unprovable passes. Nothing untracked publishes.

---

!!! success "Headline result"
    **18/18 HIGH-priority research questions → verified-green evidence bundles.**
    ~1,677 material claims. 0 unsupported. 0 contradicted.
    Two dependency-ordered waves, 18 sequential deep swarms, all confirmed by authoritative `rf verify` — not by the workflow's self-report.

---

## Why it's different

- **The claim ledger is the authority, not the model.** The synthesis step can only cite claim IDs that already exist in `claims/claim_ledger.yaml`, or it must label a sentence as inference or speculation. `rf verify` fails the build on any unsupported material claim.
- **Cheap models extract; expensive models synthesize.** Extraction, source-card creation, and formatting run on cheap profiles. Deep reasoning is reserved for synthesis — controlled by named model profiles.
- **Governance is a runtime gate, not a memo.** Key profiles (`personal`, `work_approved`, `client_approved`, `offline_only`) are enforced by `rf guard` before any model or tool runs. Work/personal key mixing is blocked deterministically.
- **Everything is human-readable on disk.** Every intent, source card, extraction, claim, report, writeback, and telemetry event is plain Markdown/YAML — no database required, deterministic, and diff-friendly.

---

## Start here

<div class="grid cards" markdown>

- **[Case Study](case-study/index.md)**

    18 real research questions. Two dependency-ordered waves. Verified-green evidence bundles with zero unsupported claims. See what the pipeline actually produced.

- **[Quickstart](quickstart.md)**

    `rf init`, `rf capture`, `rf plan`, `rf verify` — the full demo loop end to end in under 10 commands.

- **[The Pipeline](concepts/pipeline.md)**

    How a raw idea becomes a governed evidence bundle: capture → triage → plan → swarm → verify → bundle → writeback.

- **[Why Research Foundry](why.md)**

    The specific failure modes in AI-assisted research that RF is designed to eliminate, and how the claim ledger addresses each one.

</div>
