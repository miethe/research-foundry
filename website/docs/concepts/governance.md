---
title: Governance & Key Profiles
description: Runtime enforcement of sensitivity tiers, key isolation, and writeback targets
audience: developers, team leads, policy makers
tags: governance, security, policy
created: 2026-06-19
updated: 2026-06-19
category: concepts
status: published
related_documents: [concepts/pipeline.md, concepts/artifacts.md]
---

# Governance & Key Profiles

Research Foundry enforces governance deterministically at runtime, *before* any model, tool, or writeback runs. This means work and personal data never mix, confidential research is never leaked, and sensitive operations require explicit human review — all checked before execution, not after.

## Key Profiles

Every run executes under a named key profile that defines which keys, providers, and writeback targets are allowed. Profiles are configured in `config/governance.yaml`:

### `personal`

**Purpose:** Personal research, exploration, learning.

**Allowed:**
- Sensitivity levels: `public`, `personal`
- Model providers: personal (e.g., `PERSONAL_ANTHROPIC_KEY`)
- Writebacks: `meatywiki_personal`, `skillmeat_personal`, `ccdash_local`
- External tools: permitted if offline-capable

**Forbidden:**
- Employer or client confidential data
- Work-internal keys
- Writebacks to work systems

**Example:** `rf capture "How do LLMs handle long context?" --profile personal`

### `work_approved`

**Purpose:** Approved work-internal research using work-provided keys.

**Requirements:**
- Explicitly flag `--profile work_approved` (no default)
- `.env.work` file present with `WORK_ANTHROPIC_KEY` etc.

**Allowed:**
- Sensitivity levels: `public`, `work_internal`
- Model providers: work-provided keys
- Writebacks: `meatywiki_internal`, `skillmeat_internal`, `ccdash_work`
- External tools: work-approved only

**Forbidden:**
- Personal cost-avoidance research using work keys
- Unreviewed personal publication
- Personal sensitivity data

**Example:** `rf plan intent_2026_knitwit_research --profile work_approved`

### `client_approved`

**Purpose:** Explicit client-authorized research only.

**Requirements:**
- Requires human review before writeback
- Client explicitly approved in `governance.yaml` under the run's `client_id`
- Requires `--profile client_approved`

**Allowed:**
- Sensitivity levels: `public`, `client_internal`
- Model providers: client-approved tools (e.g., specialized LLM)
- Writebacks: `client_portal` only

**Forbidden:**
- Cross-client reuse of research or data
- Personal publication or redistribution
- Mixing client research with work/personal runs

**Example:** `rf triage inbox/raw_ideas/raw_acme_research.md --profile client_approved --client-id acme_2026_q3`

### `offline_only`

**Purpose:** No external API calls; local documents and models only.

**Allowed:**
- Local PDFs, documents, notebooks
- Local embeddings and search
- Offline LLMs (e.g., Ollama)

**Forbidden:**
- Network calls to external APIs
- Cloud models (Claude, GPT, etc.)
- Online search or web scraping

**Example:** `rf ingest ./local-paper.pdf --profile offline_only && rf extract run_id --profile offline_only`

## Governance Rules

Non-negotiable rules enforced deterministically (no LLM required):

| Rule | Enforcement | Impact |
|------|-------------|--------|
| **No key mixing** | Work keys forbidden in personal runs; personal keys forbidden in work runs | `rf guard` rejects command before execution (exit 3) |
| **Sensitivity tiers respected** | `work_sensitive` / `client_sensitive` data never written to personal outputs | Validation rejects writebacks; run fails (exit 3) |
| **Writeback targets gated** | Personal research must use personal writebacks; work uses work targets | `rf writeback` checks profile + target before each action |
| **Review gates** | `client_sensitive` and `work_sensitive` require human review before writeback | `rf writeback --require-review` enforces approval workflow |
| **Cross-client isolation** | Client data never reused or linked in other client runs | Ledger/bundle validation checks `client_id` tags |

## Runtime Workflow

### Check Before Running

```bash
# Verify your profile is configured
rf guard check --profile personal
rf guard check --profile work_approved
rf guard check --profile client_approved

# Diagnose all profiles, keys, and reachability
rf doctor
```

Output example:

```
Profile: personal
  Status: OK
  Keys: PERSONAL_ANTHROPIC_KEY loaded
  Providers: Anthropic (free), offline models available
  Writebacks: meatywiki_personal, skillmeat_personal, ccdash_local

Profile: work_approved
  Status: ERROR
  Keys: WORK_ANTHROPIC_KEY missing (.env.work not found)
  Providers: (none; keys required)
  Writebacks: blocked (no keys)

IntentTree: reachable (10.42.10.76:8032)
ARC: reachable (10.42.10.76:9119)
MeatyWiki: reachable (10.42.10.76:8765)
SkillMeat: reachable (10.42.10.76:8080)
NotebookLM: offline (run `notebooklm login` to enable)
```

### Explicit Profile Flag

Always specify `--profile` for non-default runs:

```bash
# Personal (default, can omit)
rf triage inbox/raw_ideas/raw_*.md

# Work (explicit, required)
rf triage inbox/raw_ideas/raw_*.md --profile work_approved

# Client (explicit, required)
rf writeback run_id --profile client_approved --client-id acme_2026
```

### Review Gate for Sensitive Operations

For `work_sensitive` or `client_sensitive` data:

```bash
rf writeback run_id --require-review
```

This:

1. Renders the intended writebacks to files in `writebacks/`.
2. Exits before pushing (exit 7: human review required).
3. Operator reviews files, confirms safety.
4. Operator runs: `rf writeback run_id --confirm-approved`

## Sensitivity Tiers

Every artifact carries a sensitivity level:

| Level | Definition | Allowed Profiles | Writebacks |
|-------|-----------|-----------------|-----------|
| `public` | No confidentiality requirement | personal, work, client, offline | all targets |
| `personal` | Personal research; never share work systems | personal only | personal writebacks |
| `work_internal` | Work-internal only; employee confidential | work_approved only | work writebacks |
| `work_sensitive` | Approval required before publishing | work_approved + review gate | work writebacks (gated) |
| `client_internal` | Client-specific; never cross-client | client_approved only | client writebacks |
| `client_sensitive` | Client approval + review gate required | client_approved + review gate | client writebacks (gated) |

## Secret Scanning

The system detects and redacts accidentally captured secrets before they leak:

```bash
# Redact sensitive data from a run
rf redact runs/rf_run_*/ --target public
```

This scans for API keys, tokens, email addresses (matching `miethe.dev@gmail.com` patterns), and other PII, then produces a redacted version safe for public sharing.

## Writeback Target Governance

Each writeback target is tied to a set of allowed profiles:

```yaml
# config/governance.yaml
writeback_targets:
  meatywiki_personal:
    profiles: [personal]
    sensitivity_allowed: [public, personal]
    
  meatywiki_internal:
    profiles: [work_approved]
    sensitivity_allowed: [public, work_internal, work_sensitive]
    requires_review_if: [work_sensitive]

  ccdash_work:
    profiles: [work_approved]
    sensitivity_allowed: [public, work_internal]
    
  client_portal:
    profiles: [client_approved]
    sensitivity_allowed: [public, client_internal, client_sensitive]
    requires_review_if: [client_sensitive]
```

## Policy Customization

Governance policies live in `config/governance.yaml` and can be customized:

```yaml
key_profiles:
  personal:
    env_file: .env.personal
    allowed_providers: [personal_anthropic]
    forbidden_data: [work_data, client_data]
    
  my_custom_profile:
    env_file: .env.custom
    allowed_providers: [custom_llm]
    sensitivity_tiers: [public, internal]
```

Reload policies: `rf guard reload`

## Validation

Governance is validated at every stage:

1. **Capture:** Sensitivity assigned, recorded in raw idea.
2. **Triage:** Intent inherits sensitivity; rejects if profile mismatch.
3. **Ingest:** Source cards tagged with sensitivity.
4. **Extract/Synthesize:** Models run only if profile allows.
5. **Writeback:** Profile + target + sensitivity checked before action.

## See Also

- [Pipeline](pipeline.md) — where governance gates run
- [Artifacts](artifacts.md) — how sensitivity is stored
- [Reference: CLI](../reference/cli.md) — `rf guard`, `rf doctor` commands
