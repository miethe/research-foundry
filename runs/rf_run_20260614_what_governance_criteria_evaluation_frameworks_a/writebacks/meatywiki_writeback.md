---
id: mwb_20260614_skillbom_promotion_governance_gates_prior_art
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_governance_criteri
target_page: meatywiki/sources/skillbom_promotion_governance_gates_prior_art.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_governance_criteria_evaluation_frameworks_a:
  54 supported claim(s) across 9 source card(s).'
key_claims:
- claim_id: clm_001
  include: true
- claim_id: clm_002
  include: true
- claim_id: clm_003
  include: true
- claim_id: clm_004
  include: true
- claim_id: clm_005
  include: true
- claim_id: clm_006
  include: true
- claim_id: clm_007
  include: true
- claim_id: clm_008
  include: true
- claim_id: clm_009
  include: true
- claim_id: clm_010
  include: true
- claim_id: clm_011
  include: true
- claim_id: clm_012
  include: true
- claim_id: clm_013
  include: true
- claim_id: clm_014
  include: true
- claim_id: clm_015
  include: true
- claim_id: clm_016
  include: true
- claim_id: clm_017
  include: true
- claim_id: clm_018
  include: true
- claim_id: clm_019
  include: true
- claim_id: clm_020
  include: true
- claim_id: clm_021
  include: true
- claim_id: clm_022
  include: true
- claim_id: clm_023
  include: true
- claim_id: clm_024
  include: true
- claim_id: clm_025
  include: true
- claim_id: clm_026
  include: true
- claim_id: clm_027
  include: true
- claim_id: clm_028
  include: true
- claim_id: clm_029
  include: true
- claim_id: clm_030
  include: true
- claim_id: clm_031
  include: true
- claim_id: clm_032
  include: true
- claim_id: clm_033
  include: true
- claim_id: clm_034
  include: true
- claim_id: clm_035
  include: true
- claim_id: clm_036
  include: true
- claim_id: clm_037
  include: true
- claim_id: clm_038
  include: true
- claim_id: clm_039
  include: true
- claim_id: clm_040
  include: true
- claim_id: clm_041
  include: true
- claim_id: clm_042
  include: true
- claim_id: clm_043
  include: true
- claim_id: clm_044
  include: true
- claim_id: clm_045
  include: true
- claim_id: clm_046
  include: true
- claim_id: clm_047
  include: true
- claim_id: clm_048
  include: true
- claim_id: clm_049
  include: true
- claim_id: clm_050
  include: true
- claim_id: clm_051
  include: true
- claim_id: clm_052
  include: true
- claim_id: clm_053
  include: true
- claim_id: clm_054
  include: true
links:
  source_cards:
  - src_20260614_rib051_00
  - src_20260614_rib051_01
  - src_20260614_rib051_02
  - src_20260614_rib051_03
  - src_20260614_rib051_04
  - src_20260614_rib051_05
  - src_20260614_rib051_06
  - src_20260614_rib051_07
  - src_20260614_rib051_08
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# SkillBOM Promotion Governance: Gates, Prior Art & Anti-Patterns

## Summary

Source note distilled from research run rf_run_20260614_what_governance_criteria_evaluation_frameworks_a: 54 supported claim(s) across 9 source card(s).

## Key claims

- The SageMaker Model Registry lets users catalog models for production, manage model versions, manage approval status, and deploy models. [claim:clm_001]
- The Model Registry supports defining a staging construct that models progress through across the model lifecycle, and automating deployment with CI/CD. [claim:clm_002]
- Models are cataloged by creating Model (Package) Groups, and each trained model is registered into a Model Group as a new model version. [claim:clm_003]
- Model Groups can be further organized into higher-level categories called Model Registry Collections. [claim:clm_004]
- A typical Model Registry workflow integrates with SageMaker ML pipelines, registering a model version in the Model Group for each pipeline run. [claim:clm_005]
- The Model Registry can associate metadata such as training metrics with a model and surface model lineage for traceability and reproducibility. [claim:clm_006]
- Langfuse Prompt Management implements prompt A/B testing by labeling distinct versions of a prompt, for example prod-a and prod-b. [claim:clm_007]
- The application randomly alternates between the labeled prompt versions while Langfuse tracks performance metrics for each. [claim:clm_008]
- Langfuse monitors per-version metrics including response latency, cost, token usage, and evaluation metrics. [claim:clm_009]
- The documented comparison metrics for A/B testing are response latency and token usage, cost per request, quality evaluation scores, and user-defined custom metrics. [claim:clm_010]
- For benchmarking complete application behavior on datasets rather than just prompt selection, Langfuse points users to Experiments instead of A/B testing. [claim:clm_011]
- A model version's approval status is evaluated after creation and updated to Approved if it meets requirements or Rejected if it does not, with Approved able to initiate CI/CD deployment. [claim:clm_012]
- Under SageMaker provided project templates, PendingManualApproval->Approved and Rejected->Approved each initiate CI/CD deployment for the approved version, while PendingManualApproval->Rejected produces no action. [claim:clm_013]
- An Approved->Rejected transition triggers CI/CD to deploy the latest model version that still has an Approved status (rolling back to the last approved version). [claim:clm_014]
- Approval status is changed by calling the update_model_package API with a dict containing ModelPackageArn and ModelApprovalStatus (e.g., set to Approved). [claim:clm_015]
- Approval status can be updated manually after registration (via Boto3 or SageMaker Studio) or automatically via a condition step in a SageMaker pipeline that evaluates model performance. [claim:clm_016]
- At model-version registration the ModelApprovalStatus is set to PendingManualApproval, which serves as the default starting state before manual or automated approval. [claim:clm_017]
- MLflow Model Registry historically governed lifecycle via discrete stages a model version can be transitioned to: Staging, Production, or Archived (plus None). [claim:clm_018]
- Stage transitions are performed via the client method transition_model_version_stage, whose accepted stage values are Staging, Archived, Production, and None. [claim:clm_019]
- As of MLflow 2.9.0, the Model Stages mechanism is deprecated and slated for removal in a future major release. [claim:clm_020]
- The replacement deployment mechanism, model version aliases, are named references to specific model versions and, unlike stages, allow multiple aliases per version to support A/B testing and rollout. [claim:clm_021]
- Model version tags are the second replacement mechanism, used to annotate a version's status (e.g., a validation_status tag moving from pending to passed). [claim:clm_022]
- The Workspace Model Registry defines four model-version stages (None, Staging, Production, Archived), with Staging meant for testing/validation, Production for reviewed-and-deployed live-scoring versions, and Archived for inactive versions. [claim:clm_023]
- A user who lacks stage-transition permission can still request a transition, which surfaces in the Pending Requests section of the model version page. [claim:clm_024]
- Reviewers act on a pending stage-transition request by clicking Approve, Reject, or Cancel, and the request's creator can also cancel it. [claim:clm_025]
- The Activities section records all requested, approved, pending, and applied transitions for a model version, providing a lifecycle lineage for auditing or inspection. [claim:clm_026]
- Databricks marks this Workspace Model Registry as legacy and steers users with Unity Catalog enabled away from it toward Models in Unity Catalog. [claim:clm_027]
- In Langfuse, every prompt version is automatically assigned a version ID, and users can additionally attach labels to follow their own versioning scheme. [claim:clm_028]
- Labels serve as deployment pointers that map prompt versions to environments (staging, production), tenants, or experiments. [claim:clm_029]
- Deploying a prompt version in Langfuse is accomplished by assigning the production label (or another environment label) to that version. [claim:clm_030]
- When a prompt is fetched without specifying a label, Langfuse serves the version carrying the production label by default. [claim:clm_031]
- The reserved 'latest' label always points to the most recently created prompt version. [claim:clm_032]
- Rollback is performed by reassigning the production label to a previous version in the Langfuse UI, after which the production-labeled version is served by default in the SDKs. [claim:clm_033]
- Protected prompt labels let admins/owners prevent labels like production from being modified or deleted by viewer/member roles, governing prompt deployment via RBAC. [claim:clm_034]
- Labels are assignable programmatically: on creation via the SDK 'labels' parameter, and on existing versions via update_prompt's 'new_labels' (Python) or update's 'newLabels' (JS/TS). [claim:clm_035]
- Langfuse protected prompt labels let project admins and owners prevent labels from being modified or deleted to control prompt deployment. [claim:clm_036]
- Once a label such as 'production' is protected, viewer and member roles cannot modify or delete it, preventing changes to the production prompt version. [claim:clm_037]
- Admin and owner roles retain the ability to modify or delete a protected label, deliberately changing the production prompt version. [claim:clm_038]
- A label's protection status is managed by admins and owners through the project settings. [claim:clm_039]
- Released 2025-04-02 (author Hassieb), protected labels are available on all Team (Cloud) and Enterprise (Cloud and Self-Hosted) plans. [claim:clm_040]
- A model alias is a mutable, user-named reference to a model version that is unique within a model resource; it is mutable because aliases can be moved between versions. [claim:clm_041]
- Aliases let you fetch or deploy a particular model version by reference without needing to know that version's ID, operating similarly to Docker tags or Git branch references. [claim:clm_042]
- When a new model is created in Model Registry, the first version is automatically assigned the default alias, which references the version used when a command runs without specifying a version. [claim:clm_043]
- Exactly one version of a model must carry the default alias at all times; otherwise the default alias behaves like any other user-defined alias. [claim:clm_044]
- The version alias must match the format [a-z][a-z0-9-]{0,126}[a-z0-9] to distinguish it from version_id, and there must be exactly one default version alias per model (created for the first version). [claim:clm_045]
- Version aliases must be unique and can only be assigned to a single version per model at a time; applying an existing alias to a new version removes it from the prior version. [claim:clm_046]
- The console alias marker helps stakeholders see at a glance which model version is the stable version ready for deployment, and users can create and assign custom aliases in addition to the default. [claim:clm_047]
- LangSmith Environments are named deployment targets (Staging and Production) that are assigned to specific prompt commits. [claim:clm_048]
- Environments let teams track which prompt version is active per environment and promote commits between them. [claim:clm_049]
- Promoting a commit to Production does not remove it from Staging. [claim:clm_050]
- The 'staging' and 'production' tag names are reserved for environment management and are not selectable in the freeform tag picker. [claim:clm_051]
- Each freeform tag references exactly one commit but can be reassigned to point to a different commit. [claim:clm_052]
- Prompts are pulled by tag in code (e.g. client.pull_prompt("joke-generator:production")), so version selection changes without code edits. [claim:clm_053]
- Commit tags are labels referencing a specific commit, so changing the tagged version updates the active prompt without modifying code. [claim:clm_054]

## Sources

- src_20260614_rib051_00 — Prompt Version Control - Langfuse Docs
- src_20260614_rib051_01 — Protected prompt labels - Langfuse Changelog
- src_20260614_rib051_02 — A/B Testing (Prompt Management) - Langfuse Docs
- src_20260614_rib051_03 — Manage prompts - LangChain / LangSmith Docs
- src_20260614_rib051_04 — Model Registry Workflows | MLflow AI Platform
- src_20260614_rib051_05 — Manage model lifecycle using the Workspace Model Registry (legacy)
- src_20260614_rib051_06 — Model Registration Deployment with Model Registry - Amazon SageMaker AI
- src_20260614_rib051_07 — Update the Approval Status of a Model - amazon-sagemaker-developer-guide (GitHub)
- src_20260614_rib051_08 — How to use model version aliases - Vertex AI Model Registry

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
