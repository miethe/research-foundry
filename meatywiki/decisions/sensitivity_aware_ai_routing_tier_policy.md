---
id: mwb_20260622_dr_sensitivity_aware_ai_routing_tier
evidence_bundle_id: bundle_20260615_intent_research_20260614_sensitivity_aware_ai
target_page: meatywiki/decisions/sensitivity_aware_ai_routing_tier_policy.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_sensitivity_aware_ai_routing_tier_policy: OWASP least-privilege
  (clm_026) and the directive to limit which external sinks a task can reach (clm_027), plus NIST''s '
key_claims:
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
- claim_id: clm_inf17
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_026
  - clm_027
  - clm_072
  - clm_010
  - clm_025
  - clm_008
  - clm_053
  - clm_012
  - clm_031
  - clm_035
  - clm_054
  - clm_055
  - clm_052
  - clm_002
  - clm_005
  - clm_021
  - clm_022
  - clm_049
  - clm_050
  - clm_060
  - clm_061
  - clm_062
  - clm_064
  - clm_065
  - clm_066
  - clm_068
  - clm_067
  - clm_007
  - clm_003
  - clm_043
  - clm_048
  - clm_014
  - clm_015
  - clm_020
  - clm_016
  - clm_058
  - clm_045
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Sensitivity-aware AI routing & tier policy for RF writeback targets

## Context

- Cloudflare announced the AI Gateway refresh on August 27, 2025, adding unified billing, secure key storage, dynamic routing, and DLP security controls. [claim:clm_001]
- Dynamic Routes let users define request-attribute-based actions (rate limits, A/B splits, model chaining), and a defined route is invoked by using it as the 'model' name in the form dynamic/<route-name>. [claim:clm_002]
- AI Gateway's Firewall adds DLP scanning where admins select which DLP profiles to block or flag, and Cloudflare scans requests for matching content. [claim:clm_003]
- Standard DLP profiles such as 'Financial Information' and 'Social Security, Insurance, Tax and Identifier Numbers' are free with a Zero Trust account, while custom DLP profiles require an upgraded Zero Trust plan. [claim:clm_004]
- Secure key storage integrates Cloudflare Secrets Store using a two-level AES-encrypted key hierarchy, with keys scoped to AI Gateway so no other service can access them. [claim:clm_005]
- Unified billing (Closed Beta) connects to major providers (Anthropic, Google, Groq, OpenAI, xAI), giving access to over 350+ models across 6 providers via one Cloudflare account. [claim:clm_006]
- Excessive Agency is the vulnerability whereby damaging actions are performed in response to unexpected, ambiguous, or manipulated LLM outputs, regardless of the cause of the malfunction. [claim:clm_007]
- Excessive functionality occurs when an LLM agent has access to extension functions not needed for the system's intended operation. [claim:clm_008]
- Excessive permissions arise when an extension holds downstream access rights beyond its needs, and excessive autonomy arises when an application fails to independently verify and approve high-impact actions. [claim:clm_009]
- OWASP recommends limiting both the extensions an LLM agent may call and the permissions those extensions hold on other systems to the minimum necessary. [claim:clm_010]
- OWASP recommends avoiding open-ended extensions such as running shell commands or fetching arbitrary URLs in favor of more granular functionality. [claim:clm_011]
- OWASP recommends a human-in-the-loop gate requiring approval of high-impact actions before they are taken, and enforcing authorization in downstream systems rather than relying on the LLM. [claim:clm_012]
- By default, data sent to the OpenAI API is not used to train or improve OpenAI models unless the customer explicitly opts in, a policy in effect since March 1, 2023. [claim:clm_013]
- By default OpenAI generates abuse-monitoring logs for all API feature usage and retains them for up to 30 days, unless a longer period is legally required. [claim:clm_014]
- Zero Data Retention forces the `store` parameter for /v1/responses and /v1/chat/completions to be treated as false even if a request sets it to true. [claim:clm_015]
- Zero Data Retention excludes customer content from abuse-monitoring logs in the same way that Modified Abuse Monitoring does. [claim:clm_016]
- These abuse-monitoring retention controls are not self-serve; they require prior approval by OpenAI and acceptance of additional requirements. [claim:clm_017]
- Customers must contact OpenAI's sales team to learn about the offerings and inquire about eligibility for the data-retention controls. [claim:clm_018]
- Once approved, an organization configures retention via a Data Retention tab under Settings -> Organization -> Data controls. [claim:clm_019]
- Zero data retention applies only to eligible Anthropic APIs, Anthropic products using a Commercial organization API key (including Claude Code via the API), and Claude Code for Enterprise plans. [claim:clm_020]
- Under ZDR, Anthropic does not store user inputs or outputs except where needed to comply with law or combat misuse or harm. [claim:clm_021]
- Even under ZDR, Anthropic still retains User Safety classifier results in order to enforce its Usage Policy. [claim:clm_022]
- Claude Platform users can confirm ZDR is applied under Settings > Privacy Controls > Data retention period on their account. [claim:clm_023]
- For Covered Models, Anthropic requires limited data retention and review as part of its safety work, separate from standard ZDR. [claim:clm_024]
- OWASP scopes sensitive information disclosure in LLM apps to cover PII, financial details, health records, confidential business data, security credentials, legal documents, and proprietary models, training methods, and source code. [claim:clm_025]
- OWASP recommends restricting access to sensitive data on a least-privilege basis, granting only the data necessary for the specific user or process. [claim:clm_026]
- OWASP advises limiting model access to external data sources and securely managing runtime data orchestration to avoid unintended data leakage, providing the direct basis for gating which sinks a task may reach. [claim:clm_027]
- OWASP recommends data sanitization to prevent user data from entering the training model, including scrubbing or masking sensitive content before training, plus strict input validation. [claim:clm_028]
- OWASP names federated learning over decentralized data and differential privacy as privacy-preserving controls that reduce centralized-data exposure and resist reverse-engineering of individual data points. [claim:clm_029]
- OWASP lists homomorphic encryption for privacy-preserving analysis and tokenization with pattern-matching redaction to detect and redact confidential content before processing. [claim:clm_030]
- Classification returns a list of findings organized by InfoType, Likelihood, and Offset (where in the string the potential InfoType was found). [claim:clm_031]
- Findings carry a Likelihood/confidence rating, with values such as VERY_LIKELY, LIKELY, and VERY_UNLIKELY shown in the example output table. [claim:clm_032]
- Built-in infoType detectors span US and international identifiers, including US_HEALTHCARE_NPI, EMAIL_ADDRESS, US_DRIVERS_LICENSE_NUMBER, CANADA_BC_PHN, UK_TAXPAYER_REFERENCE, and CANADA_PASSPORT. [claim:clm_033]
- Automatic redaction produces output with sensitive matches replaced by a placeholder such as '***', removing the detected values from the text. [claim:clm_034]
- Classification scan results can be saved to a new BigQuery table or published to a Pub/Sub topic, enabling downstream label-then-route actions before transformation. [claim:clm_035]
- Beyond redaction, the product documents de-identification transformations including date shifting, generalization and bucketing, and pseudonymization, referenced via its transformation methods reference. [claim:clm_036]
- On May 14, 2024, NIST released the final SP 800-171 Revision 3 governing protection of Controlled Unclassified Information (CUI) in nonfederal systems and organizations, alongside the SP 800-171A Revision 3 assessment companion. [claim:clm_037]
- Rev 3 restructured its security requirements so they align directly with the SP 800-53 Revision 5 control catalog. [claim:clm_038]
- Rev 3 introduced organization-defined parameters (ODPs), allowing organizations to tailor handling thresholds within the requirements. [claim:clm_039]
- Rev 3 added new tailoring criteria and recategorized controls accordingly to reduce redundancy and improve clarity. [claim:clm_040]
- Rev 3 provides additional outcome-oriented guidance intended to reduce ambiguity and better support implementation by organizations handling CUI. [claim:clm_041]
- The companion SP 800-171A Revision 3 incorporates ODPs into its assessment procedures to support traceability and usability when verifying CUI protections. [claim:clm_042]
- The default DLP policy 'DSPM for AI - Block sensitive info from AI sites' uses Adaptive Protection to give a block-with-override to elevated-risk users attempting to paste or upload sensitive information to other AI apps in Edge, Chrome, and Firefox, scoped to all users in test mode. [claim:clm_043]
- The 'Block elevated risk users from submitting prompts' policy uses Adaptive Protection to block elevated, moderate, and minor risk users from putting information into AI apps in Edge, and forces use of protected browsers by treating others as unmanaged apps. [claim:clm_044]
- The 'Protect sensitive data from Copilot processing' DLP policy blocks Microsoft 365 Copilot and agents from processing items carrying the sensitivity labels selected in the policy, binding model eligibility to a data label. [claim:clm_045]
- The 'Detect sensitive info shared with AI via network' collection policy requires manually adding one or more SASE/SSE integrations, and detection of AI interactions depends on the network partner's implementation. [claim:clm_046]
- For default policies that use Adaptive Protection, the capability is turned on automatically if not already enabled, using default risk levels for all users and groups to dynamically enforce protection actions. [claim:clm_047]
- Endpoint DLP enforcement against third-party AI sites is risk-tier-aware: a user flagged as elevated risk in Adaptive Protection is blocked with an override option when pasting sensitive data into a site like ChatGPT, illustrating the per-user-risk-tier plus sensitive-info-type decision unit. [claim:clm_048]
- Microsoft's recommended example label taxonomy is the customizable five-tier set Personal, Public, General, Confidential, and Highly Confidential. [claim:clm_049]
- Label ordinality is set by list order: the most restrictive label (e.g., Highly Confidential) goes at the bottom and the least restrictive (Personal/Public) at the top, and only one label may be applied per item. [claim:clm_050]
- Labels support a two-tier hierarchy via sublabels/label groups (e.g., Confidential \ All Employees) where the second tier carries distinct settings and the parent text label cannot be applied by itself. [claim:clm_051]
- Labeling can be discretionary or enforced: mandatory labeling requires a label before users can save files, send emails/meeting invites, or create new groups or sites; policies can also set a default label. [claim:clm_052]
- When labels apply encryption, Copilot and agents check usage rights and return data from an item only if the user holds the EXTRACT (copy) usage right, an enforcement gate analogous to writeback authorization. [claim:clm_053]
- Labels are persistent clear-text metadata that travel with content wherever it is stored, forming the basis for enforcing configured policies; Copilot Chat surfaces the highest-priority (most restrictive) label. [claim:clm_054]
- Downgrading a label or replacing it with a lower-priority label triggers a required justification prompt by default for files, emails, and meetings. [claim:clm_055]
- InfoTypes are the unit of detection: Google Cloud Sensitive Data Protection uses information types (infoTypes) to define what it scans for. [claim:clm_056]
- Built-in detectors are organized into named categories spanning Finance, Health, Communications, PII, SPII, Demographic, Credential, Government ID, Document, and Contextual information. [claim:clm_057]
- Each infoType carries a default sensitivity score, presented in a per-infoType table that drives downstream treatment. [claim:clm_058]
- Default sensitivity scores are configurable per infoType, so the content-derived tier is an editable default rather than a fixed value. [claim:clm_059]
- The HIGH sensitivity level is defined by the presence of highly sensitive data such as credit-card numbers and certain national identifiers. [claim:clm_060]
- The MODERATE level is defined by sensitive-but-not-highly-sensitive PII such as email addresses and phone numbers. [claim:clm_061]
- The LOW level corresponds to data where no sensitive information was detected and no freeform/unstructured text is present. [claim:clm_062]
- The aggregate sensitivity score combines each infoType's default sensitivity (plus user overrides) with the likelihood that highly sensitive infoTypes are present, weighting HIGH-tier detectors most heavily. [claim:clm_063]
- Potential impact is LOW when loss of confidentiality, integrity, or availability could be expected to have a limited adverse effect on organizational operations, assets, or individuals. [claim:clm_064]
- Potential impact is MODERATE when the loss could be expected to have a serious adverse effect, defining the middle of the three ordinal levels. [claim:clm_065]
- Potential impact is HIGH when the loss could be expected to have a severe or catastrophic adverse effect, the top of the LOW < MODERATE < HIGH ordinal scale. [claim:clm_066]
- The security category SC is expressed as a triple over confidentiality, integrity, and availability, each taking an impact value of LOW, MODERATE, HIGH, or NOT APPLICABLE. [claim:clm_067]
- For an information system, each security objective's impact value is set to the highest (high-water-mark) value among the information types resident on the system. [claim:clm_068]
- FIPS 199 is a mandatory standard applying to all federal information and information systems except classified information and designated national security systems. [claim:clm_069]
- AI RMF 1.0 was released on January 26, 2023, and the Generative AI Profile (NIST.AI.600-1) was published on July 26, 2024. [claim:clm_070]
- The Generative AI Profile defines 12 risks unique to or exacerbated by generative AI, including Data Privacy, Information Integrity, Information Security, Intellectual Property, Confabulation, and Value Chain and Component Integration. [claim:clm_071]
- The Data Privacy risk category is explicitly framed around data leakage and unauthorized disclosure of sensitive or personally identifiable information. [claim:clm_072]
- The profile organizes suggested actions around the four AI RMF Core functions: govern, map, measure, and manage. [claim:clm_073]
- Organizations are directed to document intended purposes, users, impacts, and data sources, establishing data-source governance as a first-class control. [claim:clm_074]
- Among suggested MANAGE actions, the profile directs documenting training data sources to trace provenance of AI-generated content, supporting the threat-model rationale for restricting sensitive data flows to external AI. [claim:clm_075]

## Decision

Recommended writeback matrix -- ARC: personal ALLOW, work_approved ALLOW, client_approved DENY-by-default (allow only with explicit override) when ARC runs as a networked service; if ARC runs purely locally, client_approved may be ALLOWED, because residual exfiltration risk is what flips the edge. [claim:clm_inf04]

## Rationale

- OWASP least-privilege (clm_026) and the directive to limit which external sinks a task can reach (clm_027), plus NIST's Data-Privacy-as-leakage framing (clm_072), justify denying client_approved data to a networked ARC by default while permitting it to a local-only ARC where no network egress occurs. [claim:clm_inf04]
- OWASP least-privilege data access (clm_026), limiting reachable sinks (clm_027), and minimizing downstream permissions (clm_010) argue that a low-access-control planning sink should default-deny the highest tier; work_approved is permitted but logged. [claim:clm_inf05]
- OWASP's scope of sensitive information (clm_025) and least-privilege access (clm_026) make the vault's audience the deciding factor; the source-card usage flags (allowed_for_personal_meatywiki true, allowed_for_public_output false) imply a personal vault tolerates client_approved but a shared vault should not. [claim:clm_inf06]
- Least-privilege data access (clm_026), limiting reachable sinks (clm_027), and OWASP's excessive-functionality root cause (clm_008 -- granting access not needed for intended operation) imply skill/dashboard sinks should not receive the highest-sensitivity tier they were never designed to hold. [claim:clm_inf07]
- Purview gates data release on a positive usage right (clm_053) and OWASP says authorization must be enforced in the downstream system not the LLM (clm_012); combined with reachable-sink limiting (clm_027), the safe construction is a positive-permission, default-deny check at the boundary keyed on a minimal header. [claim:clm_inf09]
- Google DLP produces compact structured findings (clm_031) routed to a downstream sink for label-then-route (clm_035), and Purview labels are compact travelling metadata (clm_054); RF can likewise carry a small tuple so the gate never re-scans the payload. [claim:clm_inf10]
- Purview forces a required justification when a label is lowered (clm_055) and supports mandatory labeling before save/send (clm_052); OWASP requires downstream authorization (clm_012). Together they imply RF should refuse below-ceiling writes and demand a justified override, not a silent bypass. [claim:clm_inf11]
- Cloudflare Dynamic Routes act on request attributes and the gateway logs/secures requests (clm_002, clm_005); OWASP requires downstream authorization (clm_012). The deterministic, replayable proof is a pre-write append-only decision event carrying the same tuple the gate evaluated. [claim:clm_inf12]
- Because ZDR still leaves residual provider retention (clm_021, clm_022) and OWASP requires limiting reachable sinks (clm_027), an offline_only profile that forbids external providers must also forbid networked sinks to remain consistent, while local sinks remain permissible. [claim:clm_inf16]
- Purview (clm_049/050), Google DLP (clm_060-062), and FIPS 199 (clm_064-066) all define totally-ordered sensitivity scales; mapping RF's three labels onto the same ordinal structure lets each target be policed by a single ceiling value rather than an arbitrary allow-set. [claim:clm_inf01]
- FIPS 199 sets a system's per-objective impact to the highest value among resident information types (clm_068) over the SC triple (clm_067); applying that aggregation rule to an RF run means the run inherits the highest source-card sensitivity, preventing a low label from masking high-sensitivity inputs. [claim:clm_inf02]
- Purview's five-tier example taxonomy (clm_049) collapses naturally to three RF tiers, and Purview labels as travelling clear-text metadata that gate data release via EXTRACT rights (clm_053, clm_054) are the structural analog of an RF run carrying a sensitivity label that gates writeback. [claim:clm_inf03]
- OWASP's runtime-data-orchestration / reachable-sink control (clm_027) and NIST Data-Privacy leakage framing (clm_072) make egress the threat; Excessive Agency (clm_007) shows that the harm is a function of what downstream action is reachable, which a network sink enlarges relative to a local one. [claim:clm_inf08]
- Cloudflare blocks/flags matching sensitive content (clm_003), and Purview DSPM-for-AI blocks elevated-risk users with override on sensitive paste (clm_043, clm_048); all gate sensitive content downward, supporting default-deny at the top tier with explicit override. [claim:clm_inf13]
- OpenAI default keeps 30-day abuse logs (clm_014) unless ZDR forces store=false (clm_015); Anthropic ZDR stores no inputs/outputs (clm_021) but only for commercial-key/Enterprise scope (clm_020). The retention delta justifies binding higher tiers to ZDR-covered providers. [claim:clm_inf14]
- Anthropic still retains User Safety classifier results under ZDR (clm_022) and stores data where legally required (clm_021); OpenAI ZDR/MAM still operate within legal-retention carve-outs (clm_016). A non-zero residual remains, so only offline_only fully eliminates provider-side retention. [claim:clm_inf15]
- Google DLP scores content (clm_058); Purview binds model eligibility to a data label (clm_045); Cloudflare routes/gates by request attribute (clm_002); OWASP requires HITL approval and downstream authorization (clm_012). Composing these four yields RF's full classify->bind->gate->override pipeline. [claim:clm_inf17]

## Consequences

- Recommended writeback matrix -- IntentTree: personal ALLOW, work_approved ALLOW with audit, client_approved DENY by default, because IntentTree is an idea/planning backlog whose entries are long-lived, broadly readable, and not access-scoped per source, making it a low-control sink unsuitable for client_approved content. [claim:clm_inf05]
- Recommended writeback matrix -- MeatyWiki: personal ALLOW, work_approved ALLOW, client_approved ALLOW only when the MeatyWiki vault is local/personal-scoped (the source cards here are marked sensitivity:personal with allowed_for_personal_meatywiki:true), so a shared or published MeatyWiki must drop to work_approved as its ceiling. [claim:clm_inf06]
- Recommended writeback matrix -- SkillMeat and CCDash: personal ALLOW and work_approved ALLOW, but client_approved DENY by default, because these are operational/skill-artifact and dashboard sinks where client-confidential research content has no business purpose and would only widen the leakage surface (OWASP least-purpose / least-privilege). [claim:clm_inf07]
- RF should enforce sensitivity at the writeback boundary as a default-deny gate that reads only a small decision header (run sensitivity tier, target id, target topology flag, override token) -- mirroring Purview's model where Copilot releases data only if the EXTRACT usage right is present -- so a misclassified or unlabeled run is denied rather than silently escalated. [claim:clm_inf09]
- The minimal decision metadata RF must attach to each run is a five-field tuple {run_sensitivity_tier, contributing_source_max_tier, target_id, target_topology, policy_version}, which lets the boundary decide deterministically without re-reading the report or evidence bundle -- analogous to Google DLP emitting compact findings (InfoType, Likelihood, Offset) for downstream label-then-route rather than reprocessing the document. [claim:clm_inf10]
- Misclassification escalation is best blocked the way Purview blocks label downgrades: any attempt to write a run to a target whose ceiling is below the run's tier must hard-fail by default, and any override must be an explicit, justified, logged action (Purview's justification-on-downgrade prompt) rather than a silent config flag. [claim:clm_inf11]
- The audit record proving a writeback was policy-permitted at the moment it occurred should be an append-only event capturing {run sensitivity tuple, target_id, decision (allow/deny/override), policy_version, who-approved-override, timestamp}, written before the write executes -- combining Cloudflare AI Gateway's request-attribute routing+logging with OWASP's downstream-authorization-with-record pattern. [claim:clm_inf12]
- offline_only sits one rung above client_approved in the four-profile key model and is the correct ceiling for any RF run that must never touch an external provider; it should be permitted to write to local-only targets (local ARC, personal MeatyWiki vault) but DENIED to every networked writeback target, making it the strictest row of the matrix. [claim:clm_inf16]
- Every cited enterprise classification scheme is fundamentally ordinal and monotonic (FIPS 199 LOW<MODERATE<HIGH; Purview Personal<Public<General<Confidential<Highly Confidential; Google DLP LOW<MODERATE<HIGH), so RF's three-tier model personal<work_approved<client_approved is a well-formed ordinal sensitivity lattice and a writeback target can be expressed as a single max-permitted-tier ceiling per edge. [claim:clm_inf01]
- FIPS 199's high-water-mark rule implies RF must classify a run's sensitivity as the maximum sensitivity of any input source card or evidence item it touches, not the topic label, so a personal-topic run that ingests a client_approved source card is itself client_approved for routing purposes. [claim:clm_inf02]
- The cleanest external taxonomy mapping is Microsoft Purview onto RF: Personal->personal, General/internal->work_approved, and Confidential/Highly Confidential->client_approved, because Purview labels are persistent clear-text metadata that travel with content and form the enforcement basis -- exactly the role RF's per-run sensitivity field plays at the writeback boundary. [claim:clm_inf03]
- The decisive variable across every client_approved edge is deployment topology, not the target's identity: a target running as a local-only process carries no network egress and can hold the top tier, whereas the same target as a networked service inherits an exfiltration channel that warrants default-deny -- so RF's matrix must be parameterized by a per-target local-vs-networked flag. [claim:clm_inf08]
- RF should pick default-deny for the top tier on networked targets and default-allow only for the bottom tier, because every cited gateway/DLP control (Cloudflare Firewall DLP block, Purview block-with-override, OpenAI gated ZDR) implements 'block-the-sensitive, permit-the-benign' rather than the reverse, making default-allow-then-scan the documented anti-pattern for high-sensitivity flows. [claim:clm_inf13]
- Provider data-retention posture maps directly onto RF's tier-to-provider routing: client_approved/work_approved workloads should be routed only to providers under contractual Zero Data Retention (Anthropic Commercial-key/Claude Code Enterprise, OpenAI approved ZDR), while personal-tier work may use default-retention endpoints, because default endpoints keep up-to-30-day abuse logs that constitute residual exposure. [claim:clm_inf14]
- Even under Zero Data Retention a residual safety-retention channel persists -- Anthropic retains User Safety classifier results and OpenAI retains content for legally-required windows -- so ZDR reduces but does not eliminate provider-side exposure, meaning a strict offline_only requirement (no external provider at all) is the only posture that closes the channel for the most sensitive RF runs. [claim:clm_inf15]
- The complete enforcement stack RF needs has four documented analogues stitched together: content-derived classification (Google DLP infoTypes -> run sensitivity), label-binding to eligibility (Purview Copilot label gate -> tier-to-target ceiling), default-deny request-time gate (Cloudflare Dynamic Routes + Firewall DLP -> writeback boundary), and human-in-the-loop override with audit (OWASP HITL + Purview justification -> override path). [claim:clm_inf17]

## Links

- [[claim:clm_026]]
- [[claim:clm_027]]
- [[claim:clm_072]]
- [[claim:clm_010]]
- [[claim:clm_025]]
- [[claim:clm_008]]
- [[claim:clm_053]]
- [[claim:clm_012]]
- [[claim:clm_031]]
- [[claim:clm_035]]
- [[claim:clm_054]]
- [[claim:clm_055]]
- [[claim:clm_052]]
- [[claim:clm_002]]
- [[claim:clm_005]]
- [[claim:clm_021]]
- [[claim:clm_022]]
- [[claim:clm_049]]
- [[claim:clm_050]]
- [[claim:clm_060]]
- [[claim:clm_061]]
- [[claim:clm_062]]
- [[claim:clm_064]]
- [[claim:clm_065]]
- [[claim:clm_066]]
- [[claim:clm_068]]
- [[claim:clm_067]]
- [[claim:clm_007]]
- [[claim:clm_003]]
- [[claim:clm_043]]
- [[claim:clm_048]]
- [[claim:clm_014]]
- [[claim:clm_015]]
- [[claim:clm_020]]
- [[claim:clm_016]]
- [[claim:clm_058]]
- [[claim:clm_045]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
