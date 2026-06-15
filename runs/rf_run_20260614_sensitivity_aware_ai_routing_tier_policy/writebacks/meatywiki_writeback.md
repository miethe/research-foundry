---
id: mwb_20260615_sensitivity_aware_ai_routing_tier_policy
evidence_bundle_id: bundle_20260615_intent_research_20260614_sensitivity_aware_ai
target_page: meatywiki/sources/sensitivity_aware_ai_routing_tier_policy.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_sensitivity_aware_ai_routing_tier_policy:
  75 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_055
  include: true
- claim_id: clm_056
  include: true
- claim_id: clm_057
  include: true
- claim_id: clm_058
  include: true
- claim_id: clm_059
  include: true
- claim_id: clm_060
  include: true
- claim_id: clm_061
  include: true
- claim_id: clm_062
  include: true
- claim_id: clm_063
  include: true
- claim_id: clm_064
  include: true
- claim_id: clm_065
  include: true
- claim_id: clm_066
  include: true
- claim_id: clm_067
  include: true
- claim_id: clm_068
  include: true
- claim_id: clm_069
  include: true
- claim_id: clm_070
  include: true
- claim_id: clm_071
  include: true
- claim_id: clm_072
  include: true
- claim_id: clm_073
  include: true
- claim_id: clm_074
  include: true
- claim_id: clm_075
  include: true
links:
  source_cards:
  - src_20260614_rib017_00
  - src_20260614_rib017_01
  - src_20260614_rib017_02
  - src_20260614_rib017_03
  - src_20260614_rib017_04
  - src_20260614_rib017_05
  - src_20260614_rib017_06
  - src_20260614_rib017_07
  - src_20260614_rib017_08
  - src_20260614_rib017_09
  - src_20260614_rib017_10
  - src_20260614_rib017_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Sensitivity-aware AI routing & tier policy for RF writeback targets

## Summary

Source note distilled from research run rf_run_20260614_sensitivity_aware_ai_routing_tier_policy: 75 supported claim(s) across 12 source card(s).

## Key claims

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

## Sources

- src_20260614_rib017_00 — FIPS PUB 199 — Standards for Security Categorization of Federal Information and Information Systems
- src_20260614_rib017_01 — NIST Issues Updated Security Requirements and Assessment Procedures for Protecting Controlled Unclassified Information (CUI)
- src_20260614_rib017_02 — Learn about sensitivity labels (Microsoft Purview Information Protection)
- src_20260614_rib017_03 — InfoType detector reference — Sensitive Data Protection (Google Cloud DLP)
- src_20260614_rib017_04 — AI Risk Management Framework (AI RMF 1.0) and Generative AI Profile (NIST AI 600-1)
- src_20260614_rib017_05 — Considerations for deploying Microsoft Purview Data Security Posture Management (DSPM) for AI
- src_20260614_rib017_06 — LLM02:2025 Sensitive Information Disclosure
- src_20260614_rib017_07 — LLM06:2025 Excessive Agency
- src_20260614_rib017_08 — AI Gateway now gives you access to your favorite AI models, dynamic routing and more — through just one endpoint
- src_20260614_rib017_09 — Data controls in the OpenAI platform
- src_20260614_rib017_10 — I have a zero data retention agreement with Anthropic. What products does it apply to?
- src_20260614_rib017_11 — Classification, redaction, and de-identification | Sensitive Data Protection | Google Cloud

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
