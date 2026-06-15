---
schema_version: '0.1'
type: research_report
report_id: report_20260615_sensitivity_aware_ai_routing_tier_policy
title: Sensitivity-aware AI routing & tier policy for RF writeback targets
intent_id: intent_research_20260614_sensitivity_aware_ai_routing_tier_policy
evidence_bundle_id: pending
created_at: '2026-06-15T00:21:24-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# Sensitivity-aware AI routing & tier policy for RF writeback targets

## Executive summary

This memo specifies a sensitivity-tier policy for Research Foundry (RF) writeback targets, derived from external data-classification standards and agentic-security guidance, and presented for a technical audience implementing the routing boundary.

**Inference:** Every cited enterprise classification scheme is fundamentally ordinal and monotonic (FIPS 199 LOW<MODERATE<HIGH; Purview Personal<Public<General<Confidential<Highly Confidential; Google DLP LOW<MODERATE<HIGH), so RF's three-tier model personal<work_approved<client_approved is a well-formed ordinal sensitivity lattice and a writeback target can be expressed as a single max-permitted-tier ceiling per edge. [claim:clm_inf01]
**Inference:** The decisive variable across every client_approved edge is deployment topology, not the target's identity: a target running as a local-only process carries no network egress and can hold the top tier, whereas the same target as a networked service inherits an exfiltration channel that warrants default-deny -- so RF's matrix must be parameterized by a per-target local-vs-networked flag. [claim:clm_inf08]
**Inference:** RF should enforce sensitivity at the writeback boundary as a default-deny gate that reads only a small decision header (run sensitivity tier, target id, target topology flag, override token) -- mirroring Purview's model where Copilot releases data only if the EXTRACT usage right is present -- so a misclassified or unlabeled run is denied rather than silently escalated. [claim:clm_inf09]
**Inference:** The complete enforcement stack RF needs has four documented analogues stitched together: content-derived classification (Google DLP infoTypes -> run sensitivity), label-binding to eligibility (Purview Copilot label gate -> tier-to-target ceiling), default-deny request-time gate (Cloudflare Dynamic Routes + Firewall DLP -> writeback boundary), and human-in-the-loop override with audit (OWASP HITL + Purview justification -> override path). [claim:clm_inf17]

## External taxonomy mapping onto RF tiers

| RF tier | Microsoft Purview label | Mapping basis | Evidence |
|---------|------------------------|---------------|----------|
| personal | Personal | Purview's least-restrictive label, top of the ordered list | [claim:clm_050] |
| work_approved | General / internal | Mid-tier of the customizable five-tier set | [claim:clm_049] |
| client_approved | Confidential / Highly Confidential | Most-restrictive Purview labels, bottom of the ordered list | [claim:clm_050] |

**Inference:** The cleanest external taxonomy mapping is Microsoft Purview onto RF: Personal->personal, General/internal->work_approved, and Confidential/Highly Confidential->client_approved, because Purview labels are persistent clear-text metadata that travel with content and form the enforcement basis -- exactly the role RF's per-run sensitivity field plays at the writeback boundary. [claim:clm_inf03]

Microsoft's recommended example label taxonomy is the customizable five-tier set Personal, Public, General, Confidential, and Highly Confidential. [claim:clm_049]
Label ordinality is set by list order: the most restrictive label (e.g., Highly Confidential) goes at the bottom and the least restrictive (Personal/Public) at the top, and only one label may be applied per item. [claim:clm_050]
Labels are persistent clear-text metadata that travel with content wherever it is stored, forming the basis for enforcing configured policies; Copilot Chat surfaces the highest-priority (most restrictive) label. [claim:clm_054]
FIPS 199 supplies the parallel federal ordinal scale: potential impact is LOW when loss of confidentiality, integrity, or availability could be expected to have a limited adverse effect on organizational operations, assets, or individuals. [claim:clm_064]
Potential impact is MODERATE when the loss could be expected to have a serious adverse effect, defining the middle of the three ordinal levels. [claim:clm_065]
Potential impact is HIGH when the loss could be expected to have a severe or catastrophic adverse effect, the top of the LOW < MODERATE < HIGH ordinal scale. [claim:clm_066]
Google Cloud Sensitive Data Protection supplies the content-derived analog: the HIGH sensitivity level is defined by the presence of highly sensitive data such as credit-card numbers and certain national identifiers. [claim:clm_060]
The MODERATE level is defined by sensitive-but-not-highly-sensitive PII such as email addresses and phone numbers. [claim:clm_061]
The LOW level corresponds to data where no sensitive information was detected and no freeform/unstructured text is present. [claim:clm_062]

### Run-level classification rule

**Inference:** FIPS 199's high-water-mark rule implies RF must classify a run's sensitivity as the maximum sensitivity of any input source card or evidence item it touches, not the topic label, so a personal-topic run that ingests a client_approved source card is itself client_approved for routing purposes. [claim:clm_inf02]

The security category SC is expressed as a triple over confidentiality, integrity, and availability, each taking an impact value of LOW, MODERATE, HIGH, or NOT APPLICABLE. [claim:clm_067]
For an information system, each security objective's impact value is set to the highest (high-water-mark) value among the information types resident on the system. [claim:clm_068]
FIPS 199 is a mandatory standard applying to all federal information and information systems except classified information and designated national security systems. [claim:clm_069]

## Sensitivity-tier x writeback-target allow/deny matrix

| Target | personal | work_approved | client_approved (networked) | Evidence |
|--------|----------|---------------|-----------------------------|----------|
| ARC | ALLOW | ALLOW | DENY (override only) | [claim:clm_inf04] |
| IntentTree | ALLOW | ALLOW (with audit) | DENY | [claim:clm_inf05] |
| MeatyWiki | ALLOW | ALLOW | DENY unless vault is local/personal-scoped | [claim:clm_inf06] |
| SkillMeat | ALLOW | ALLOW | DENY | [claim:clm_inf07] |
| CCDash | ALLOW | ALLOW | DENY | [claim:clm_inf07] |

**Inference:** Recommended writeback matrix -- ARC: personal ALLOW, work_approved ALLOW, client_approved DENY-by-default (allow only with explicit override) when ARC runs as a networked service; if ARC runs purely locally, client_approved may be ALLOWED, because residual exfiltration risk is what flips the edge. [claim:clm_inf04]
**Inference:** Recommended writeback matrix -- IntentTree: personal ALLOW, work_approved ALLOW with audit, client_approved DENY by default, because IntentTree is an idea/planning backlog whose entries are long-lived, broadly readable, and not access-scoped per source, making it a low-control sink unsuitable for client_approved content. [claim:clm_inf05]
**Inference:** Recommended writeback matrix -- MeatyWiki: personal ALLOW, work_approved ALLOW, client_approved ALLOW only when the MeatyWiki vault is local/personal-scoped (the source cards here are marked sensitivity:personal with allowed_for_personal_meatywiki:true), so a shared or published MeatyWiki must drop to work_approved as its ceiling. [claim:clm_inf06]
**Inference:** Recommended writeback matrix -- SkillMeat and CCDash: personal ALLOW and work_approved ALLOW, but client_approved DENY by default, because these are operational/skill-artifact and dashboard sinks where client-confidential research content has no business purpose and would only widen the leakage surface (OWASP least-purpose / least-privilege). [claim:clm_inf07]

### Threat-model basis per edge

The deny edges all trace to the same OWASP and NIST primitives, which justify least-privilege gating of which sinks a task may reach. [claim:clm_026] [claim:clm_027] [claim:clm_inf08]

OWASP recommends restricting access to sensitive data on a least-privilege basis, granting only the data necessary for the specific user or process. [claim:clm_026]
OWASP advises limiting model access to external data sources and securely managing runtime data orchestration to avoid unintended data leakage, providing the direct basis for gating which sinks a task may reach. [claim:clm_027]
OWASP scopes sensitive information disclosure in LLM apps to cover PII, financial details, health records, confidential business data, security credentials, legal documents, and proprietary models, training methods, and source code. [claim:clm_025]
OWASP recommends limiting both the extensions an LLM agent may call and the permissions those extensions hold on other systems to the minimum necessary. [claim:clm_010]
Excessive functionality occurs when an LLM agent has access to extension functions not needed for the system's intended operation. [claim:clm_008]
Excessive Agency is the vulnerability whereby damaging actions are performed in response to unexpected, ambiguous, or manipulated LLM outputs, regardless of the cause of the malfunction. [claim:clm_007]
Excessive permissions arise when an extension holds downstream access rights beyond its needs, and excessive autonomy arises when an application fails to independently verify and approve high-impact actions. [claim:clm_009]
The Data Privacy risk category is explicitly framed around data leakage and unauthorized disclosure of sensitive or personally identifiable information. [claim:clm_072]
Among suggested MANAGE actions, the profile directs documenting training data sources to trace provenance of AI-generated content, supporting the threat-model rationale for restricting sensitive data flows to external AI. [claim:clm_075]

## Analysis: why topology, not identity, sets the ceiling

**Inference:** RF should pick default-deny for the top tier on networked targets and default-allow only for the bottom tier, because every cited gateway/DLP control (Cloudflare Firewall DLP block, Purview block-with-override, OpenAI gated ZDR) implements 'block-the-sensitive, permit-the-benign' rather than the reverse, making default-allow-then-scan the documented anti-pattern for high-sensitivity flows. [claim:clm_inf13]

The cited DLP gateways all gate sensitive content downward at request time. AI Gateway's Firewall adds DLP scanning where admins select which DLP profiles to block or flag, and Cloudflare scans requests for matching content. [claim:clm_003]
The default DLP policy 'DSPM for AI - Block sensitive info from AI sites' uses Adaptive Protection to give a block-with-override to elevated-risk users attempting to paste or upload sensitive information to other AI apps in Edge, Chrome, and Firefox, scoped to all users in test mode. [claim:clm_043]
Endpoint DLP enforcement against third-party AI sites is risk-tier-aware: a user flagged as elevated risk in Adaptive Protection is blocked with an override option when pasting sensitive data into a site like ChatGPT, illustrating the per-user-risk-tier plus sensitive-info-type decision unit. [claim:clm_048]
The 'Block elevated risk users from submitting prompts' policy uses Adaptive Protection to block elevated, moderate, and minor risk users from putting information into AI apps in Edge, and forces use of protected browsers by treating others as unmanaged apps. [claim:clm_044]
The 'Protect sensitive data from Copilot processing' DLP policy blocks Microsoft 365 Copilot and agents from processing items carrying the sensitivity labels selected in the policy, binding model eligibility to a data label. [claim:clm_045]

### Provider data-retention posture as a routing input

**Inference:** Provider data-retention posture maps directly onto RF's tier-to-provider routing: client_approved/work_approved workloads should be routed only to providers under contractual Zero Data Retention (Anthropic Commercial-key/Claude Code Enterprise, OpenAI approved ZDR), while personal-tier work may use default-retention endpoints, because default endpoints keep up-to-30-day abuse logs that constitute residual exposure. [claim:clm_inf14]

By default, data sent to the OpenAI API is not used to train or improve OpenAI models unless the customer explicitly opts in, a policy in effect since March 1, 2023. [claim:clm_013]
By default OpenAI generates abuse-monitoring logs for all API feature usage and retains them for up to 30 days, unless a longer period is legally required. [claim:clm_014]
Zero Data Retention forces the `store` parameter for /v1/responses and /v1/chat/completions to be treated as false even if a request sets it to true. [claim:clm_015]
Zero Data Retention excludes customer content from abuse-monitoring logs in the same way that Modified Abuse Monitoring does. [claim:clm_016]
These abuse-monitoring retention controls are not self-serve; they require prior approval by OpenAI and acceptance of additional requirements. [claim:clm_017]
Zero data retention applies only to eligible Anthropic APIs, Anthropic products using a Commercial organization API key (including Claude Code via the API), and Claude Code for Enterprise plans. [claim:clm_020]
Under ZDR, Anthropic does not store user inputs or outputs except where needed to comply with law or combat misuse or harm. [claim:clm_021]

### Residual exposure and the offline_only ceiling

**Inference:** Even under Zero Data Retention a residual safety-retention channel persists -- Anthropic retains User Safety classifier results and OpenAI retains content for legally-required windows -- so ZDR reduces but does not eliminate provider-side exposure, meaning a strict offline_only requirement (no external provider at all) is the only posture that closes the channel for the most sensitive RF runs. [claim:clm_inf15]

Even under ZDR, Anthropic still retains User Safety classifier results in order to enforce its Usage Policy. [claim:clm_022]
For Covered Models, Anthropic requires limited data retention and review as part of its safety work, separate from standard ZDR. [claim:clm_024]

**Inference:** offline_only sits one rung above client_approved in the four-profile key model and is the correct ceiling for any RF run that must never touch an external provider; it should be permitted to write to local-only targets (local ARC, personal MeatyWiki vault) but DENIED to every networked writeback target, making it the strictest row of the matrix. [claim:clm_inf16]

| Profile | External provider permitted | Networked writeback targets | Local-only targets | Evidence |
|---------|----------------------------|-----------------------------|--------------------|----------|
| personal | Default-retention OK | ALLOW | ALLOW | [claim:clm_inf14] |
| work_approved | ZDR-covered only | ALLOW | ALLOW | [claim:clm_inf14] |
| client_approved | ZDR-covered only | DENY (override) | ALLOW | [claim:clm_inf04] |
| offline_only | None | DENY | ALLOW | [claim:clm_inf16] |

## Enforcement mechanism at the routing boundary

**Inference:** The minimal decision metadata RF must attach to each run is a five-field tuple {run_sensitivity_tier, contributing_source_max_tier, target_id, target_topology, policy_version}, which lets the boundary decide deterministically without re-reading the report or evidence bundle -- analogous to Google DLP emitting compact findings (InfoType, Likelihood, Offset) for downstream label-then-route rather than reprocessing the document. [claim:clm_inf10]

Classification returns a list of findings organized by InfoType, Likelihood, and Offset (where in the string the potential InfoType was found). [claim:clm_031]
Classification scan results can be saved to a new BigQuery table or published to a Pub/Sub topic, enabling downstream label-then-route actions before transformation. [claim:clm_035]
Each infoType carries a default sensitivity score, presented in a per-infoType table that drives downstream treatment. [claim:clm_058]
Default sensitivity scores are configurable per infoType, so the content-derived tier is an editable default rather than a fixed value. [claim:clm_059]

The positive-permission gate construction follows Purview's release model. When labels apply encryption, Copilot and agents check usage rights and return data from an item only if the user holds the EXTRACT (copy) usage right, an enforcement gate analogous to writeback authorization. [claim:clm_053]
OWASP recommends a human-in-the-loop gate requiring approval of high-impact actions before they are taken, and enforcing authorization in downstream systems rather than relying on the LLM. [claim:clm_012]
Dynamic Routes let users define request-attribute-based actions (rate limits, A/B splits, model chaining), and a defined route is invoked by using it as the 'model' name in the form dynamic/<route-name>. [claim:clm_002]
Secure key storage integrates Cloudflare Secrets Store using a two-level AES-encrypted key hierarchy, with keys scoped to AI Gateway so no other service can access them. [claim:clm_005]

### Misclassification handling

**Inference:** Misclassification escalation is best blocked the way Purview blocks label downgrades: any attempt to write a run to a target whose ceiling is below the run's tier must hard-fail by default, and any override must be an explicit, justified, logged action (Purview's justification-on-downgrade prompt) rather than a silent config flag. [claim:clm_inf11]

Downgrading a label or replacing it with a lower-priority label triggers a required justification prompt by default for files, emails, and meetings. [claim:clm_055]
Labeling can be discretionary or enforced: mandatory labeling requires a label before users can save files, send emails/meeting invites, or create new groups or sites; policies can also set a default label. [claim:clm_052]

### Audit-trail record

**Inference:** The audit record proving a writeback was policy-permitted at the moment it occurred should be an append-only event capturing {run sensitivity tuple, target_id, decision (allow/deny/override), policy_version, who-approved-override, timestamp}, written before the write executes -- combining Cloudflare AI Gateway's request-attribute routing+logging with OWASP's downstream-authorization-with-record pattern. [claim:clm_inf12]

NIST's Generative AI Profile supplies the governance backing for a written provenance record. AI RMF 1.0 was released on January 26, 2023, and the Generative AI Profile (NIST.AI.600-1) was published on July 26, 2024. [claim:clm_070]
The profile organizes suggested actions around the four AI RMF Core functions: govern, map, measure, and manage. [claim:clm_073]
Organizations are directed to document intended purposes, users, impacts, and data sources, establishing data-source governance as a first-class control. [claim:clm_074]
The Generative AI Profile defines 12 risks unique to or exacerbated by generative AI, including Data Privacy, Information Integrity, Information Security, Intellectual Property, Confabulation, and Value Chain and Component Integration. [claim:clm_071]

## Recommendations and decision rules

**Inference:** RF should enforce sensitivity at the writeback boundary as a default-deny gate that reads only a small decision header (run sensitivity tier, target id, target topology flag, override token) -- mirroring Purview's model where Copilot releases data only if the EXTRACT usage right is present -- so a misclassified or unlabeled run is denied rather than silently escalated. [claim:clm_inf09]
**Inference:** The decisive variable across every client_approved edge is deployment topology, not the target's identity: a target running as a local-only process carries no network egress and can hold the top tier, whereas the same target as a networked service inherits an exfiltration channel that warrants default-deny -- so RF's matrix must be parameterized by a per-target local-vs-networked flag. [claim:clm_inf08]
**Inference:** Provider data-retention posture maps directly onto RF's tier-to-provider routing: client_approved/work_approved workloads should be routed only to providers under contractual Zero Data Retention (Anthropic Commercial-key/Claude Code Enterprise, OpenAI approved ZDR), while personal-tier work may use default-retention endpoints, because default endpoints keep up-to-30-day abuse logs that constitute residual exposure. [claim:clm_inf14]
OWASP recommends avoiding open-ended extensions such as running shell commands or fetching arbitrary URLs in favor of more granular functionality. [claim:clm_011]
Confirmation of provider posture is operator-checkable: Claude Platform users can confirm ZDR is applied under Settings > Privacy Controls > Data retention period on their account. [claim:clm_023]
Customers must contact OpenAI's sales team to learn about the offerings and inquire about eligibility for the data-retention controls. [claim:clm_018]
Once approved, an organization configures retention via a Data Retention tab under Settings -> Organization -> Data controls. [claim:clm_019]

**Speculation:** As ARC and IntentTree integrations have not yet been validated against a live server, the safest launch posture is to ship the matrix with client_approved DENY for both targets regardless of topology, then relax ARC's local-mode edge to ALLOW only after a verified local-only deployment is confirmed -- treating unverified topology as networked-by-default. [claim:clm_spec01]
**Speculation:** If RF adds a content-derived classifier (e.g., a Google-DLP-style infoType scan over source cards), it will likely surface runs whose declared tier understates their true sensitivity, so RF should plan for a reconciliation step that raises a run to the high-water-mark of detected infoTypes and logs the mismatch -- otherwise self-declared tiers will drift below actual content sensitivity over time. [claim:clm_spec02]

## Open questions

- For a content-derived classifier over source cards, which infoType detectors and likelihood thresholds should map to each RF tier given that built-in infoType detectors span US and international identifiers and findings carry a Likelihood/confidence rating?
- Should RF adopt any of the de-identification transformations (date shifting, generalization and bucketing, pseudonymization, tokenization) as a downgrade path rather than a hard deny for over-ceiling writes?
- Does the unified-billing multi-provider model affect whether a single routing policy version can cover all providers, or must policy_version be provider-scoped?
- Should the offline_only profile require federated-learning or differential-privacy controls for any local model that itself learns from RF content?

## Appendix: supporting standard details

Standard DLP profiles such as 'Financial Information' and 'Social Security, Insurance, Tax and Identifier Numbers' are free with a Zero Trust account, while custom DLP profiles require an upgraded Zero Trust plan. [claim:clm_004]
Unified billing (Closed Beta) connects to major providers (Anthropic, Google, Groq, OpenAI, xAI), giving access to over 350+ models across 6 providers via one Cloudflare account. [claim:clm_006]
Cloudflare announced the AI Gateway refresh on August 27, 2025, adding unified billing, secure key storage, dynamic routing, and DLP security controls. [claim:clm_001]
Findings carry a Likelihood/confidence rating, with values such as VERY_LIKELY, LIKELY, and VERY_UNLIKELY shown in the example output table. [claim:clm_032]
Built-in infoType detectors span US and international identifiers, including US_HEALTHCARE_NPI, EMAIL_ADDRESS, US_DRIVERS_LICENSE_NUMBER, CANADA_BC_PHN, UK_TAXPAYER_REFERENCE, and CANADA_PASSPORT. [claim:clm_033]
Automatic redaction produces output with sensitive matches replaced by a placeholder such as '***', removing the detected values from the text. [claim:clm_034]
Beyond redaction, the product documents de-identification transformations including date shifting, generalization and bucketing, and pseudonymization, referenced via its transformation methods reference. [claim:clm_036]
InfoTypes are the unit of detection: Google Cloud Sensitive Data Protection uses information types (infoTypes) to define what it scans for. [claim:clm_056]
Built-in detectors are organized into named categories spanning Finance, Health, Communications, PII, SPII, Demographic, Credential, Government ID, Document, and Contextual information. [claim:clm_057]
The aggregate sensitivity score combines each infoType's default sensitivity (plus user overrides) with the likelihood that highly sensitive infoTypes are present, weighting HIGH-tier detectors most heavily. [claim:clm_063]
On May 14, 2024, NIST released the final SP 800-171 Revision 3 governing protection of Controlled Unclassified Information (CUI) in nonfederal systems and organizations, alongside the SP 800-171A Revision 3 assessment companion. [claim:clm_037]
Rev 3 restructured its security requirements so they align directly with the SP 800-53 Revision 5 control catalog. [claim:clm_038]
Rev 3 introduced organization-defined parameters (ODPs), allowing organizations to tailor handling thresholds within the requirements. [claim:clm_039]
Rev 3 added new tailoring criteria and recategorized controls accordingly to reduce redundancy and improve clarity. [claim:clm_040]
Rev 3 provides additional outcome-oriented guidance intended to reduce ambiguity and better support implementation by organizations handling CUI. [claim:clm_041]
The companion SP 800-171A Revision 3 incorporates ODPs into its assessment procedures to support traceability and usability when verifying CUI protections. [claim:clm_042]
The 'Detect sensitive info shared with AI via network' collection policy requires manually adding one or more SASE/SSE integrations, and detection of AI interactions depends on the network partner's implementation. [claim:clm_046]
For default policies that use Adaptive Protection, the capability is turned on automatically if not already enabled, using default risk levels for all users and groups to dynamically enforce protection actions. [claim:clm_047]
Labels support a two-tier hierarchy via sublabels/label groups (e.g., Confidential \ All Employees) where the second tier carries distinct settings and the parent text label cannot be applied by itself. [claim:clm_051]
OWASP recommends data sanitization to prevent user data from entering the training model, including scrubbing or masking sensitive content before training, plus strict input validation. [claim:clm_028]
OWASP names federated learning over decentralized data and differential privacy as privacy-preserving controls that reduce centralized-data exposure and resist reverse-engineering of individual data points. [claim:clm_029]
OWASP lists homomorphic encryption for privacy-preserving analysis and tokenization with pattern-matching redaction to detect and redact confidential content before processing. [claim:clm_030]

## Sources

- src_20260614_rib017_08: AI Gateway now gives you access to your favorite AI models, dynamic routing and more — through just one endpoint
- src_20260614_rib017_07: LLM06:2025 Excessive Agency
- src_20260614_rib017_09: Data controls in the OpenAI platform
- src_20260614_rib017_10: I have a zero data retention agreement with Anthropic. What products does it apply to?
- src_20260614_rib017_06: LLM02:2025 Sensitive Information Disclosure
- src_20260614_rib017_11: Classification, redaction, and de-identification | Sensitive Data Protection | Google Cloud
- src_20260614_rib017_01: NIST Issues Updated Security Requirements and Assessment Procedures for Protecting Controlled Unclassified Information (CUI)
- src_20260614_rib017_05: Considerations for deploying Microsoft Purview Data Security Posture Management (DSPM) for AI
- src_20260614_rib017_02: Learn about sensitivity labels (Microsoft Purview Information Protection)
- src_20260614_rib017_03: InfoType detector reference — Sensitive Data Protection (Google Cloud DLP)
- src_20260614_rib017_00: FIPS PUB 199 — Standards for Security Categorization of Federal Information and Information Systems
- src_20260614_rib017_04: AI Risk Management Framework (AI RMF 1.0) and Generative AI Profile (NIST AI 600-1)
