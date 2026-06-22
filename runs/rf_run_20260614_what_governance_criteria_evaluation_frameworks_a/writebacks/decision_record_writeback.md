---
id: mwb_20260622_dr_skillbom_promotion_governance_gates_prior
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_governance_criteri
target_page: meatywiki/decisions/skillbom_promotion_governance_gates_prior_art.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_governance_criteria_evaluation_frameworks_a: Langfuse
  deploys via a label assignment, MLflow/Vertex via an alias move, LangSmith via an environment tag; Vertex
  requi'
key_claims:
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_rec08
  include: true
- claim_id: clm_rec09
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_rec11
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_030
  - clm_021
  - clm_048
  - clm_044
  - clm_046
  - clm_034
  - clm_037
  - clm_038
  - clm_040
  - clm_024
  - clm_017
  - clm_012
  - clm_025
  - clm_026
  - clm_006
  - clm_016
  - clm_003
  - clm_022
  - clm_023
  - clm_029
  - clm_041
  - clm_052
  - clm_018
  - clm_014
  - clm_031
  - clm_032
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: SkillBOM Promotion Governance: Gates, Prior Art & Anti-Patterns

## Context

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

## Decision

The single most transferable anti-friction pattern is Langfuse/MLflow/LangSmith pointer-based promotion: because promotion is a label/alias reassignment and not a re-deploy, RF can let many candidates accumulate cheaply while a protected promoted pointer designates exactly one blessed SkillBOM version per proposed_skillbom_id, mirroring Vertex's rule that exactly one version carries the default alias at all times. [claim:clm_inf05]

## Rationale

- Langfuse deploys via a label assignment, MLflow/Vertex via an alias move, LangSmith via an environment tag; Vertex requires exactly one default alias. Combining low-friction pointer promotion with a single-blessed-version constraint yields a cheap-accumulation, controlled-promotion design. [claim:clm_inf05]
- Langfuse protected labels block viewer/member from touching production yet admins/owners retain control; Databricks lets unprivileged users request but not apply transitions. The pattern protects the promotion edge specifically, not the whole graph, minimizing friction. [claim:clm_inf06]
- SageMaker's PendingManualApproval default plus Databricks reviewer-actioned Activities log are the minimal additions needed to make a promotion decision auditable; observed RF candidates lack a populated quality_score and any reviewer attribution. Follows directly from the gap analysis in clm_inf04. [claim:clm_rec08]
- Databricks Activities records requested/approved/pending/applied transitions as auditable lineage; SageMaker surfaces model lineage for traceability and distinguishes manual versus automated (condition-step) status changes. An embedded append-only log captures both in RF's file-first model. [claim:clm_rec09]
- SageMaker registers each model as a new immutable version with a separate ModelApprovalStatus; MLflow replaced stages with aliases/tags that point at fixed versions; Databricks stages, Langfuse labels, LangSmith environment tags, and Vertex aliases are all mutable references to fixed versions. The shared pattern is artifact-immutable plus pointer-mutable. [claim:clm_inf01]
- Each named prior-art state has a direct functional analogue to one RF lifecycle stage: pending/default start equals candidate, automated tag flip equals evaluated, request-plus-approve equals human-reviewed, approved/production-label/environment equals promoted. [claim:clm_inf02]
- SageMaker allows an automated condition step to set status but production deployment still flows through Approved; Databricks requires a reviewer to click Approve on a pending request. RF's single report_reviewed flag does not distinguish automated pass (necessary) from human sign-off (sufficient). [claim:clm_inf03]
- Comparing the observed RF frontmatter (status, validation, known_failure_modes, performance_evidence) against SageMaker approval status, Databricks reviewer-actioned requests plus Activities log plus lineage, and SageMaker rollback transitions reveals these four missing capabilities. [claim:clm_inf04]
- Langfuse serves the production-labeled (not latest) version by default so reserved latest is never accidentally promoted, evidencing anti-pattern A; protected labels and Databricks request/approve gating exist to block unprivileged pointer changes, evidencing anti-pattern B as a real failure the vendors mitigated. [claim:clm_rec11]

## Consequences

- Premature reuse is prevented less by adding friction than by RBAC-protecting the promotion pointer: Langfuse protected prompt labels (released 2025-04-02) let only admin/owner roles move production while viewer/member roles can still create and label candidates, so RF should protect the promoted transition while leaving candidate->evaluated transitions open to any contributor, gating reuse rather than authorship. [claim:clm_inf06]
- Because RF candidates currently carry quality_score: pending and rework_count: 0 with no human sign-off, none of the existing skill_research_swarm_v0 candidates meet a defensible promotion bar; the immediate fix is to add an approval_status enum (pending->evaluated->approved/rejected), a reviewer field, and an append-only transitions log to the frontmatter before any candidate is reused. [claim:clm_rec08]
- Provenance and auditability should be recorded as an append-only transitions list embedded in the SkillBOM frontmatter, each entry carrying timestamp, from_state, to_state, actor, automated-versus-manual, and evidence_ref, directly porting the Databricks Activities lineage and SageMaker model-lineage patterns so any promotion decision can be reconstructed after the fact without an external system. [claim:clm_rec09]
- Across SageMaker, MLflow, Databricks, Langfuse, LangSmith, and Vertex AI, every surveyed registry separates an immutable versioned artifact from a mutable promotion pointer (approval status, stage, environment label, or alias), so the RF SkillBOM lifecycle should likewise treat the candidate file as immutable and model candidate->evaluated->human-reviewed->promoted as movable pointer state rather than as edits to the artifact. [claim:clm_inf01]
- The RF SkillBOM stages map cleanly onto prior-art pointer states: candidate equals SageMaker PendingManualApproval / MLflow validation_status:pending / Databricks Staging; evaluated equals validation_status:passed after automated checks; human-reviewed equals a Databricks-style pending transition request acted on by a reviewer; promoted equals SageMaker Approved / MLflow Production alias / Langfuse protected production label / LangSmith Production environment. [claim:clm_inf02]
- Necessary versus sufficient signals diverge by gate: passing claim_verifier and governance_guard is NECESSARY but not SUFFICIENT to leave candidate, because every prior-art system that gates production (SageMaker, Databricks) requires an explicit human Approve action in addition to automated condition-step evaluation, whereas RF's current single 'validation: report_reviewed' flag conflates the automated and human checks into one unattributed boolean. [claim:clm_inf03]
- RF's skillbom_candidate frontmatter has four governance gaps relative to the surveyed prior art: no explicit approval-status enum distinct from the lifecycle status field (cf. SageMaker ModelApprovalStatus); no reviewer-identity/accountability field (cf. Databricks recording the actor on Approve/Reject); no append-only transition/activity log for auditability (cf. Databricks Activities and SageMaker lineage); and no demotion or deprecation transition (cf. SageMaker Approved->Rejected rollback and the Databricks Archived stage). [claim:clm_inf04]
- Two documented premature-reuse anti-patterns for SkillBOMs: reuse-of-latest, where consumers pull the newest candidate by default instead of the blessed version (the failure Langfuse explicitly prevents by serving the production-labeled version, not latest, when no label is given); and unguarded-pointer-flip, where an unprivileged actor moves the promotion pointer (the failure Langfuse protected labels and the Databricks request/approve gate were built to stop). [claim:clm_rec11]

## Links

- [[claim:clm_030]]
- [[claim:clm_021]]
- [[claim:clm_048]]
- [[claim:clm_044]]
- [[claim:clm_046]]
- [[claim:clm_034]]
- [[claim:clm_037]]
- [[claim:clm_038]]
- [[claim:clm_040]]
- [[claim:clm_024]]
- [[claim:clm_017]]
- [[claim:clm_012]]
- [[claim:clm_025]]
- [[claim:clm_026]]
- [[claim:clm_006]]
- [[claim:clm_016]]
- [[claim:clm_003]]
- [[claim:clm_022]]
- [[claim:clm_023]]
- [[claim:clm_029]]
- [[claim:clm_041]]
- [[claim:clm_052]]
- [[claim:clm_018]]
- [[claim:clm_014]]
- [[claim:clm_031]]
- [[claim:clm_032]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
