---
schema_version: '0.1'
type: technical_memo
report_id: report_20260614_what_governance_criteria_evaluation_frameworks_a
title: 'SkillBOM Promotion Governance: Gates, Prior Art & Anti-Patterns'
intent_id: intent_research_20260614_what_governance_criteria_evaluation_frameworks_a
evidence_bundle_id: pending
created_at: '2026-06-14T16:54:38-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# SkillBOM Promotion Governance: Gates, Prior Art & Anti-Patterns

## Executive summary

**Inference:** This memo derives a promotion-governance design for Research Foundry SkillBOMs from a survey of six production model/prompt registries; every surveyed registry separates an immutable versioned artifact from a mutable promotion pointer, so the RF SkillBOM lifecycle should likewise treat the candidate file as immutable and model candidate->evaluated->human-reviewed->promoted as movable pointer state rather than as edits to the artifact. [claim:clm_inf01]

**Inference:** The RF SkillBOM stages map cleanly onto prior-art pointer states: candidate equals SageMaker PendingManualApproval / MLflow validation_status:pending / Databricks Staging; evaluated equals validation_status:passed after automated checks; human-reviewed equals a Databricks-style pending transition request acted on by a reviewer; promoted equals SageMaker Approved / MLflow Production alias / Langfuse protected production label / LangSmith Production environment. [claim:clm_inf02]

**Inference:** Passing claim_verifier and governance_guard is necessary but not sufficient to leave candidate, because every prior-art system that gates production requires an explicit human Approve action in addition to automated condition-step evaluation, whereas RF's current single 'validation: report_reviewed' flag conflates the automated and human checks into one unattributed boolean. [claim:clm_inf03]

**Inference:** Because RF candidates currently carry quality_score: pending and rework_count: 0 with no human sign-off, none of the existing skill_research_swarm_v0 candidates meet a defensible promotion bar; the immediate fix is to add an approval_status enum (pending->evaluated->approved/rejected), a reviewer field, and an append-only transitions log to the frontmatter before any candidate is reused. [claim:clm_rec08]

## Promotion-gate matrix

**Inference:** The lifecycle stage mapping in the matrix below is established by the prior-art correspondence, and each criterion row carries the evidence backing it. [claim:clm_inf02]

| Transition | Necessary criterion | Sufficient criterion | Evidence |
|------------|--------------------|--------------------|----------|
| candidate -> evaluated | claim_verifier_passed AND governance_guard_passed are true and rework_count equals 0 for the originating run | Automated condition-step pass alone advances the pointer; no human action required at this edge | **Speculation:** [claim:clm_rec07] |
| candidate -> evaluated | Automated pass is necessary but does not by itself authorize production; an explicit human Approve is additionally required downstream | Not sufficient for promotion | **Inference:** [claim:clm_inf03] |
| evaluated -> human-reviewed | quality_score is at least 0.8 on a 0-1 scale across at least 2 independent runs | A Databricks-style pending transition request is opened and acted on by a reviewer | **Speculation:** [claim:clm_rec07] |
| human-reviewed -> promoted | An attributed human Approve with zero open known_failure_modes classified severity high or above | Reviewer clicks Approve on the pending request, recording the actor | **Speculation:** [claim:clm_rec07] |
| any -> stay candidate (no-go) | quality_score is still pending | Default no-go; the candidate does not advance | **Speculation:** [claim:clm_rec07] |
| promoted -> evaluated (demotion) | tools_used or prompts drift, or a new run records rework_count greater than 0 | Auto-demote loses the protected promotion pointer; re-review on a fixed quarterly cadence | **Speculation:** [claim:clm_spec10] |

**Speculation:** The numeric thresholds in this matrix are a forward-looking design proposal synthesizing RF's own validation flags and performance_evidence fields, defaulting to no-go whenever quality_score is still pending. [claim:clm_rec07]

**Speculation:** The demotion edge mirrors SageMaker's Approved->Rejected rollback that automatically redeploys the last still-Approved version. [claim:clm_spec10]

## Prior-art comparison

### Stage-to-pointer correspondence across surveyed systems

**Inference:** Each named prior-art state has a direct functional analogue to one RF lifecycle stage. [claim:clm_inf02]

| RF stage | SageMaker | MLflow | Databricks (Workspace) | Langfuse | LangSmith | Vertex AI | Evidence |
|----------|-----------|--------|------------------------|----------|-----------|-----------|----------|
| candidate | ModelApprovalStatus PendingManualApproval is set at registration as the default starting state | validation_status tag at pending | Staging stage meant for testing/validation | latest label points to most recent version | Staging environment assigned to a commit | first version auto-assigned default alias | [claim:clm_017] |
| candidate->evaluated | condition step in a pipeline evaluates model performance to set status | validation_status tag moves from pending to passed | (automated check) | per-version metrics tracked (latency, cost, tokens, eval) | (commit on Staging) | (alias still on first version) | [claim:clm_022] |
| human-reviewed | reviewer required before production deployment | (no built-in request gate) | user lacking permission requests a transition surfacing in Pending Requests | (RBAC on label move) | promote commit between environments | (manual alias assignment) | [claim:clm_024] |
| promoted | ModelApprovalStatus Approved can initiate CI/CD deployment | Production alias | reviewer clicks Approve on the pending request | production label served by default | Production environment | default alias marks the stable deployable version | [claim:clm_012] |

### Mechanism details by system

The SageMaker Model Registry lets users catalog models for production, manage model versions, manage approval status, and deploy models. [claim:clm_001]
The Model Registry supports defining a staging construct that models progress through across the model lifecycle, and automating deployment with CI/CD. [claim:clm_002]
Models are cataloged by creating Model (Package) Groups, and each trained model is registered into a Model Group as a new model version. [claim:clm_003]
Model Groups can be further organized into higher-level categories called Model Registry Collections. [claim:clm_004]
A typical Model Registry workflow integrates with SageMaker ML pipelines, registering a model version in the Model Group for each pipeline run. [claim:clm_005]
The Model Registry can associate metadata such as training metrics with a model and surface model lineage for traceability and reproducibility. [claim:clm_006]
A model version's approval status is evaluated after creation and updated to Approved if it meets requirements or Rejected if it does not, with Approved able to initiate CI/CD deployment. [claim:clm_012]
Under SageMaker provided project templates, PendingManualApproval->Approved and Rejected->Approved each initiate CI/CD deployment for the approved version, while PendingManualApproval->Rejected produces no action. [claim:clm_013]
An Approved->Rejected transition triggers CI/CD to deploy the latest model version that still has an Approved status (rolling back to the last approved version). [claim:clm_014]
Approval status is changed by calling the update_model_package API with a dict containing ModelPackageArn and ModelApprovalStatus (e.g., set to Approved). [claim:clm_015]
Approval status can be updated manually after registration (via Boto3 or SageMaker Studio) or automatically via a condition step in a SageMaker pipeline that evaluates model performance. [claim:clm_016]
At model-version registration the ModelApprovalStatus is set to PendingManualApproval, which serves as the default starting state before manual or automated approval. [claim:clm_017]

MLflow Model Registry historically governed lifecycle via discrete stages a model version can be transitioned to: Staging, Production, or Archived (plus None). [claim:clm_018]
Stage transitions are performed via the client method transition_model_version_stage, whose accepted stage values are Staging, Archived, Production, and None. [claim:clm_019]
As of MLflow 2.9.0, the Model Stages mechanism is deprecated and slated for removal in a future major release. [claim:clm_020]
The replacement deployment mechanism, model version aliases, are named references to specific model versions and, unlike stages, allow multiple aliases per version to support A/B testing and rollout. [claim:clm_021]
Model version tags are the second replacement mechanism, used to annotate a version's status (e.g., a validation_status tag moving from pending to passed). [claim:clm_022]

The Workspace Model Registry defines four model-version stages (None, Staging, Production, Archived), with Staging meant for testing/validation, Production for reviewed-and-deployed live-scoring versions, and Archived for inactive versions. [claim:clm_023]
A user who lacks stage-transition permission can still request a transition, which surfaces in the Pending Requests section of the model version page. [claim:clm_024]
Reviewers act on a pending stage-transition request by clicking Approve, Reject, or Cancel, and the request's creator can also cancel it. [claim:clm_025]
The Activities section records all requested, approved, pending, and applied transitions for a model version, providing a lifecycle lineage for auditing or inspection. [claim:clm_026]
Databricks marks this Workspace Model Registry as legacy and steers users with Unity Catalog enabled away from it toward Models in Unity Catalog. [claim:clm_027]

In Langfuse, every prompt version is automatically assigned a version ID, and users can additionally attach labels to follow their own versioning scheme. [claim:clm_028]
Labels serve as deployment pointers that map prompt versions to environments (staging, production), tenants, or experiments. [claim:clm_029]
Deploying a prompt version in Langfuse is accomplished by assigning the production label (or another environment label) to that version. [claim:clm_030]
When a prompt is fetched without specifying a label, Langfuse serves the version carrying the production label by default. [claim:clm_031]
The reserved 'latest' label always points to the most recently created prompt version. [claim:clm_032]
Rollback is performed by reassigning the production label to a previous version in the Langfuse UI, after which the production-labeled version is served by default in the SDKs. [claim:clm_033]
Protected prompt labels let admins/owners prevent labels like production from being modified or deleted by viewer/member roles, governing prompt deployment via RBAC. [claim:clm_034]
Labels are assignable programmatically: on creation via the SDK 'labels' parameter, and on existing versions via update_prompt's 'new_labels' (Python) or update's 'newLabels' (JS/TS). [claim:clm_035]
Langfuse protected prompt labels let project admins and owners prevent labels from being modified or deleted to control prompt deployment. [claim:clm_036]
Once a label such as 'production' is protected, viewer and member roles cannot modify or delete it, preventing changes to the production prompt version. [claim:clm_037]
Admin and owner roles retain the ability to modify or delete a protected label, deliberately changing the production prompt version. [claim:clm_038]
A label's protection status is managed by admins and owners through the project settings. [claim:clm_039]
Released 2025-04-02 (author Hassieb), protected labels are available on all Team (Cloud) and Enterprise (Cloud and Self-Hosted) plans. [claim:clm_040]

Langfuse Prompt Management implements prompt A/B testing by labeling distinct versions of a prompt, for example prod-a and prod-b. [claim:clm_007]
The application randomly alternates between the labeled prompt versions while Langfuse tracks performance metrics for each. [claim:clm_008]
Langfuse monitors per-version metrics including response latency, cost, token usage, and evaluation metrics. [claim:clm_009]
The documented comparison metrics for A/B testing are response latency and token usage, cost per request, quality evaluation scores, and user-defined custom metrics. [claim:clm_010]
For benchmarking complete application behavior on datasets rather than just prompt selection, Langfuse points users to Experiments instead of A/B testing. [claim:clm_011]

A model alias is a mutable, user-named reference to a model version that is unique within a model resource; it is mutable because aliases can be moved between versions. [claim:clm_041]
Aliases let you fetch or deploy a particular model version by reference without needing to know that version's ID, operating similarly to Docker tags or Git branch references. [claim:clm_042]
When a new model is created in Model Registry, the first version is automatically assigned the default alias, which references the version used when a command runs without specifying a version. [claim:clm_043]
Exactly one version of a model must carry the default alias at all times; otherwise the default alias behaves like any other user-defined alias. [claim:clm_044]
The version alias must match the format [a-z][a-z0-9-]{0,126}[a-z0-9] to distinguish it from version_id, and there must be exactly one default version alias per model (created for the first version). [claim:clm_045]
Version aliases must be unique and can only be assigned to a single version per model at a time; applying an existing alias to a new version removes it from the prior version. [claim:clm_046]
The console alias marker helps stakeholders see at a glance which model version is the stable version ready for deployment, and users can create and assign custom aliases in addition to the default. [claim:clm_047]

LangSmith Environments are named deployment targets (Staging and Production) that are assigned to specific prompt commits. [claim:clm_048]
Environments let teams track which prompt version is active per environment and promote commits between them. [claim:clm_049]
Promoting a commit to Production does not remove it from Staging. [claim:clm_050]
The 'staging' and 'production' tag names are reserved for environment management and are not selectable in the freeform tag picker. [claim:clm_051]
Each freeform tag references exactly one commit but can be reassigned to point to a different commit. [claim:clm_052]
Prompts are pulled by tag in code (e.g. client.pull_prompt("joke-generator:production")), so version selection changes without code edits. [claim:clm_053]
Commit tags are labels referencing a specific commit, so changing the tagged version updates the active prompt without modifying code. [claim:clm_054]

### Gaps in RF skillbom_candidate frontmatter

**Inference:** RF's skillbom_candidate frontmatter has four governance gaps relative to the surveyed prior art: no explicit approval-status enum distinct from the lifecycle status field (cf. SageMaker ModelApprovalStatus); no reviewer-identity/accountability field (cf. Databricks recording the actor on Approve/Reject); no append-only transition/activity log for auditability (cf. Databricks Activities and SageMaker lineage); and no demotion or deprecation transition (cf. SageMaker Approved->Rejected rollback and the Databricks Archived stage). [claim:clm_inf04]

| Gap | RF current behavior | Prior-art analogue that closes the gap | Evidence |
|-----|------------------|-----------------------------------|----------|
| No approval-status enum distinct from lifecycle status | single status field | SageMaker ModelApprovalStatus separate from version state | **Inference:** [claim:clm_inf04] |
| No reviewer-identity / accountability field | unattributed validation boolean | Databricks records the actor on Approve/Reject | **Inference:** [claim:clm_inf04] |
| No append-only transition/activity log | no audit trail | Databricks Activities log and SageMaker model lineage | **Inference:** [claim:clm_inf04] |
| No demotion or deprecation transition | promotion is terminal | SageMaker Approved->Rejected rollback and Databricks Archived stage | **Inference:** [claim:clm_inf04] |

## Analysis and derivation

**Inference:** The artifact-immutable / pointer-mutable invariant holds across all six systems: SageMaker registers each model as a new immutable version with a separate ModelApprovalStatus, MLflow replaced stages with aliases and tags that point at fixed versions, and Databricks stages, Langfuse labels, LangSmith environment tags, and Vertex aliases are all mutable references to fixed versions. [claim:clm_inf01]

**Inference:** The necessary-versus-sufficient split is the load-bearing distinction: SageMaker allows an automated condition step to set status, but production deployment still flows through an Approved state, and Databricks requires a reviewer to click Approve on a pending request, so RF's single report_reviewed flag fails to separate the automated pass (necessary) from the human sign-off (sufficient). [claim:clm_inf03]

**Inference:** The single most transferable anti-friction pattern is Langfuse/MLflow/LangSmith pointer-based promotion: because promotion is a label/alias reassignment and not a re-deploy, RF can let many candidates accumulate cheaply while a protected promoted pointer designates exactly one blessed SkillBOM version per proposed_skillbom_id, mirroring Vertex's rule that exactly one version carries the default alias at all times. [claim:clm_inf05]

**Inference:** Premature reuse is prevented less by adding friction than by RBAC-protecting the promotion pointer: Langfuse protected prompt labels (released 2025-04-02) let only admin/owner roles move production while viewer/member roles can still create and label candidates, so RF should protect the promoted transition while leaving candidate->evaluated transitions open to any contributor, gating reuse rather than authorship. [claim:clm_inf06]

**Speculation:** The minimal viable RF promotion-gate matrix is three gates over four states using only fields RF already has plus three additions (approval_status, reviewer, transitions list); this is lighter-weight than SageMaker's CI/CD-template-coupled approval graph yet strictly more auditable than MLflow's deprecated direct stage transition, positioning RF between the two and likely sufficient for a file-first control plane without a hosted registry service. [claim:clm_spec12]

## Recommendations and decision rules

**Speculation:** Recommended go/no-go promotion rule: advance candidate->evaluated only when claim_verifier_passed AND governance_guard_passed are true and rework_count equals 0 for the originating run; advance evaluated->human-reviewed only when quality_score is at least 0.8 on a 0-1 scale across at least 2 independent runs; advance human-reviewed->promoted only on an attributed human Approve with zero open known_failure_modes classified severity high or above; and default to no-go (stay candidate) whenever quality_score is still pending. [claim:clm_rec07]

**Inference:** Because RF candidates currently carry quality_score: pending and rework_count: 0 with no human sign-off, none of the existing skill_research_swarm_v0 candidates meet a defensible promotion bar; the immediate fix is to add an approval_status enum (pending->evaluated->approved/rejected), a reviewer field, and an append-only transitions log to the frontmatter before any candidate is reused. [claim:clm_rec08]

**Inference:** Provenance and auditability should be recorded as an append-only transitions list embedded in the SkillBOM frontmatter, each entry carrying timestamp, from_state, to_state, actor, automated-versus-manual, and evidence_ref, directly porting the Databricks Activities lineage and SageMaker model-lineage patterns so any promotion decision can be reconstructed after the fact without an external system. [claim:clm_rec09]

**Speculation:** Re-evaluation and demotion should be event-and-cadence driven: a promoted SkillBOM should auto-demote toward evaluated (losing the protected promotion pointer) when its tools_used or prompts drift or when a new run records rework_count greater than 0, and should be re-reviewed on a fixed cadence such as quarterly, mirroring SageMaker's Approved->Rejected rollback that automatically redeploys the last still-Approved version. [claim:clm_spec10]

### Go/no-go decision thresholds

| Field | Threshold to advance | Action if unmet | Evidence |
|-------|----------------------|-----------------|----------|
| claim_verifier_passed + governance_guard_passed | both true | stay candidate | **Speculation:** [claim:clm_rec07] |
| rework_count | equals 0 for originating run to leave candidate; greater than 0 on a new run triggers demotion of a promoted SkillBOM | hold / auto-demote | **Speculation:** [claim:clm_rec07] |
| quality_score | at least 0.8 on 0-1 scale across at least 2 independent runs; pending defaults to no-go | stay candidate | **Speculation:** [claim:clm_rec07] |
| known_failure_modes | zero open at severity high or above for human-reviewed->promoted | block promotion | **Speculation:** [claim:clm_rec07] |

## Anti-patterns for premature reuse

**Inference:** Two documented premature-reuse anti-patterns for SkillBOMs: reuse-of-latest, where consumers pull the newest candidate by default instead of the blessed version (the failure Langfuse explicitly prevents by serving the production-labeled version, not latest, when no label is given); and unguarded-pointer-flip, where an unprivileged actor moves the promotion pointer (the failure Langfuse protected labels and the Databricks request/approve gate were built to stop). [claim:clm_rec11]

The reuse-of-latest anti-pattern is grounded in a real mitigation: when a prompt is fetched without specifying a label, Langfuse serves the version carrying the production label by default rather than the most recent version. [claim:clm_031]
The reserved 'latest' label always points to the most recently created prompt version, so a consumer that pulls 'latest' gets an unvetted version. [claim:clm_032]
The unguarded-pointer-flip anti-pattern is grounded in the Databricks mitigation: a user who lacks stage-transition permission can still request a transition, which surfaces in the Pending Requests section rather than taking effect immediately. [claim:clm_024]
It is further grounded in the Langfuse mitigation: protected prompt labels let admins/owners prevent labels like production from being modified or deleted by viewer/member roles. [claim:clm_034]

## Open questions

- What concrete quality_score scale and per-run scoring rubric should RF adopt so that the 0.8 / 2-run threshold is measurable rather than nominal?
- Should the demotion cadence be fixed quarterly, or driven purely by drift and rework signals?
- Does a file-first control plane need an explicit Archived/deprecated terminal state distinct from demotion-to-evaluated?
- Which RF role boundary (contributor versus reviewer/owner) should hold the protected promotion pointer once RBAC is introduced?

## Sources

- src_20260614_rib051_06: Model Registration Deployment with Model Registry - Amazon SageMaker AI
- src_20260614_rib051_02: A/B Testing (Prompt Management) - Langfuse Docs
- src_20260614_rib051_07: Update the Approval Status of a Model - amazon-sagemaker-developer-guide (GitHub)
- src_20260614_rib051_04: Model Registry Workflows | MLflow AI Platform
- src_20260614_rib051_05: Manage model lifecycle using the Workspace Model Registry (legacy)
- src_20260614_rib051_00: Prompt Version Control - Langfuse Docs
- src_20260614_rib051_01: Protected prompt labels - Langfuse Changelog
- src_20260614_rib051_08: How to use model version aliases - Vertex AI Model Registry
- src_20260614_rib051_03: Manage prompts - LangChain / LangSmith Docs
