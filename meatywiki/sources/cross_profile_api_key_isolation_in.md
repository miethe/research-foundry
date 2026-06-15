---
id: mwb_20260614_cross_profile_api_key_isolation_in
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_published_security
target_page: meatywiki/sources/cross_profile_api_key_isolation_in.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_published_security_frameworks_threat_models:
  82 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_076
  include: true
- claim_id: clm_077
  include: true
- claim_id: clm_078
  include: true
- claim_id: clm_079
  include: true
- claim_id: clm_080
  include: true
- claim_id: clm_081
  include: true
- claim_id: clm_082
  include: true
links:
  source_cards:
  - src_20260614_rib018_00
  - src_20260614_rib018_01
  - src_20260614_rib018_02
  - src_20260614_rib018_03
  - src_20260614_rib018_04
  - src_20260614_rib018_05
  - src_20260614_rib018_06
  - src_20260614_rib018_07
  - src_20260614_rib018_08
  - src_20260614_rib018_09
  - src_20260614_rib018_10
  - src_20260614_rib018_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Cross-profile API-key isolation in multi-profile agentic systems

## Summary

Source note distilled from research run rf_run_20260614_what_published_security_frameworks_threat_models: 82 supported claim(s) across 12 source card(s).

## Key claims

- This document is the first guide from the OWASP Agentic Security Initiative (ASI), providing a threat-model-based reference of emerging agentic threats and their mitigations. [claim:clm_001]
- OWASP frames agentic AI capabilities around LLM-based reasoning/planning, memory that can be session-based short-term or persistent long-term, and action via tool use (including MCP-connected external tools). [claim:clm_002]
- OWASP defines the Confused Deputy vulnerability as an AI agent with higher privileges than the user being tricked into performing unauthorized actions on the user's behalf when it lacks privilege isolation. [claim:clm_003]
- OWASP threat T3 'Privilege Compromise' describes attackers exploiting weaknesses in permission management - often via dynamic role inheritance or misconfigurations - to perform unauthorized actions. [claim:clm_004]
- OWASP recommends clear identity flows, strict RBAC, and a zero-trust model for agent access to enterprise environments to counter implicit privilege escalation and tool-chaining data breaches. [claim:clm_005]
- Among authentication/identity mitigations, OWASP advises limiting AI credential persistence so that AI-generated credentials are temporary and expire after short timeframes. [claim:clm_006]
- OWASP recommends granular RBAC and ABAC and blocking cross-agent privilege delegation unless explicitly authorized through predefined workflows. [claim:clm_007]
- To isolate agent context, OWASP advises segmenting memory access using session isolation so the AI does not carry over unintended knowledge across different user sessions. [claim:clm_008]
- Each dynamic database credential is bound to a lease with an explicit TTL and a structured lease ID; the example shows a 768h lease_duration with lease_id format database/creds/readonly/<unique-id>. [claim:clm_009]
- A dynamic credential's validity is governed by its lease: it remains valid for the lease TTL, can be renewed up to a maximum TTL, or persists until revoked. [claim:clm_010]
- Leases are renewed before expiry by passing the lease ID to `vault lease renew`, which resets the credential's TTL (example renewed to 1h). [claim:clm_011]
- A single lease can be revoked immediately by its lease ID without waiting for expiration, using `vault lease revoke <lease_id>`. [claim:clm_012]
- Multiple leases can be revoked at once using the -prefix flag, which matches all valid leases sharing a path prefix (e.g., database/creds/readonly). [claim:clm_013]
- Once a lease is revoked the underlying credential is immediately invalidated and no longer usable. [claim:clm_014]
- After revocation the lease ceases to exist as a valid lease and disappears from the lease listing, confirming immediate invalidation. [claim:clm_015]
- The OWASP Multi-Agentic System Threat Modelling Guide is Version 1.0, was released on April 22, 2025, and is published by the OWASP GenAI Security Project's Agentic Security Initiative. [claim:clm_016]
- The guide does not propose a new taxonomy but applies the OWASP 'Agentic AI - Threats and Mitigations' master agentic threat taxonomy to real-world multi-agent systems. [claim:clm_017]
- The guide's objective is to apply the MAESTRO (Multi-Agent Environment, Security, Threat, Risk, and Outcome) layered, architectural methodology as a companion to the OWASP Agentic Security Initiative (ASI) threat taxonomy for structured threat modeling. [claim:clm_018]
- The guide focuses on previously OWASP-defined agentic threats - Tool Misuse, Intent Manipulation, and Privilege Compromise - and how they manifest within complex multi-agent deployments. [claim:clm_019]
- The guide identifies identity sprawl and access complexity as a novel MAS risk, where managing identity and access control becomes highly complex due to the large number of interacting agents. [claim:clm_020]
- Identity Spoofing is listed as a core MAS threat in which adversaries impersonate agents to inject false data or hijack decision-making. [claim:clm_021]
- MAESTRO outlines security threats across architectural layers of the agentic AI reference architecture (foundation models up to the agent ecosystem) plus cross-layer threats, and references the Cloud Security Alliance MAESTRO blog as its origin. [claim:clm_022]
- The guide is positioned as an extension of the ASI 'Agentic AI - Threats and Mitigations' document, intended to be used in tandem with it and the OWASP Top 10 for LLM Applications. [claim:clm_023]
- OWASP defines MCP scope creep as narrowly scoped agent/tool permissions expanding over time—via convenience or configuration drift—until the agent holds broad or administrative privileges. [claim:clm_024]
- The standard prescribes defining minimal per-agent permissions before deployment and mapping documented intended actions to explicit scopes. [claim:clm_025]
- The control requires unique per-agent identities with credentials bound to the agent and session context, explicitly disallowing shared global service accounts. [claim:clm_026]
- The standard recommends issuing time-limited scopes/tokens per session and requiring revalidation for long-running or recurring tasks. [claim:clm_027]
- The control prescribes encoding permission policies as code (Rego, OPA, Terraform IAM) and enforcing them in CI/CD pipelines. [claim:clm_028]
- The standard calls for periodic entitlement audits to detect scope expansions and alerting on permission increases. [claim:clm_029]
- The control separates the authority to grant permissions from the authority to deploy or change production, and requires human-in-the-loop approvals for non-routine privilege grants. [claim:clm_030]
- MCP servers must validate that access tokens were issued specifically for them as the intended audience per RFC 8707 Section 2, and invalid or expired tokens must receive an HTTP 401 response. [claim:clm_031]
- If an MCP server makes requests to upstream APIs, it must not pass through the token received from the MCP client; the upstream token must be a separate token issued by the upstream authorization server. [claim:clm_032]
- MCP clients must implement RFC 8707 Resource Indicators via the resource parameter, including it in both authorization and token requests and identifying the canonical URI of the target MCP server. [claim:clm_033]
- MCP servers must only accept tokens specifically intended for themselves and must reject tokens that do not include them in the audience claim. [claim:clm_034]
- Authorization servers should issue short-lived access tokens to reduce leaked-token impact, and for public clients they must rotate refresh tokens per OAuth 2.1 Section 4.3.1. [claim:clm_035]
- Implementations using an STDIO transport should not follow this authorization specification and instead retrieve credentials from the environment. [claim:clm_036]
- OWASP defines LLM02:2025 sensitive information as spanning PII, financial details, health records, confidential business data, security credentials, and legal documents. [claim:clm_037]
- OWASP states LLMs embedded in applications risk exposing sensitive data, proprietary algorithms, or confidential details through their output, leading to unauthorized data access, privacy violations, and IP breaches. [claim:clm_038]
- PII leakage is listed as a common vulnerability: PII may be disclosed during interactions with the LLM. [claim:clm_039]
- OWASP cites the Proof Pudding attack (CVE-2019-20634) as an example where revealing training data exposes models to inversion attacks. [claim:clm_040]
- OWASP recommends limiting model access to external data sources and securely managing runtime data orchestration, the closest mitigation addressing multi-source data chaining risk. [claim:clm_041]
- OWASP maps LLM02:2025 to MITRE ATLAS techniques for training-data membership inference and model inversion/extraction (AML.T0024.000/.001/.002). [claim:clm_042]
- OWASP's lead mitigation is data sanitization to prevent user data from entering the training model, plus strict input validation to filter sensitive inputs. [claim:clm_043]
- OWASP defines Excessive Agency as the vulnerability that enables damaging actions in response to unexpected, ambiguous, or manipulated LLM outputs, regardless of the cause of the malfunction. [claim:clm_044]
- OWASP attributes Excessive Agency to three root causes: excessive functionality, excessive permissions, and excessive autonomy. [claim:clm_045]
- OWASP recommends limiting the permissions that LLM extensions are granted to downstream systems to the minimum necessary to bound the scope of undesirable actions. [claim:clm_046]
- OWASP recommends tracking user authorization and security scope so that actions on downstream systems execute in that specific user's context with minimum privileges. [claim:clm_047]
- OWASP advises avoiding open-ended extensions such as run-a-shell-command or fetch-a-URL in favor of more granular, purpose-specific functionality. [claim:clm_048]
- OWASP recommends human-in-the-loop control requiring a human to approve high-impact actions before they are taken. [claim:clm_049]
- OWASP gives OAuth with minimum scope as the example pattern for an extension that reads a user's code repository. [claim:clm_050]
- AML.TA0013 Credential Access covers adversary efforts to steal account names, passwords, or API keys for AI systems. [claim:clm_051]
- AML.T0083 'Credentials from AI Agent Configuration' covers accessing the credentials of other tools or services on a system from an AI agent's configuration. [claim:clm_052]
- AML.T0082 'RAG Credential Harvesting' covers using access to a victim-system LLM to collect credentials (e.g., those ingested into a RAG database). [claim:clm_053]
- AML.T0098 'AI Agent Tool Credential Harvesting' covers using access to a victim-system AI agent to retrieve data from the agent's available tools. [claim:clm_054]
- AML.T0055 'Unsecured Credentials' covers searching compromised systems to find and obtain insecurely stored credentials. [claim:clm_055]
- AML.TA0013 also enumerates AML.T0090 'OS Credential Dumping' and AML.T0106 'Exploitation for Credential Access', extending credential theft beyond AI-specific vectors to traditional OS-level and exploit-based methods. [claim:clm_056]
- Each Vault Enterprise namespace behaves as an isolated Vault environment. [claim:clm_057]
- Once signed into a namespace there is no visibility into other namespaces regardless of hierarchical relationship. [claim:clm_058]
- Tokens, policies, and secrets engines are tied to their owning namespace, so a client must acquire a valid token per namespace to access its secrets, preventing cross-namespace credential reuse. [claim:clm_059]
- Each namespace maintains its own independent policies, auth methods, secrets engines, tokens, and identity entities/groups. [claim:clm_060]
- Namespaces address the multi-tenancy need where multiple organizations within a company must manage their secrets in a self-serving manner on a central Vault. [claim:clm_061]
- Namespaces are a paid Vault feature requiring a Vault Enterprise Standard license or an HCP Vault cluster. [claim:clm_062]
- Namespace creation should be performed by a highly privileged token such as root to set up isolated environments per organization, team, or application. [claim:clm_063]
- Token passthrough is explicitly forbidden: an MCP server must not accept tokens that were not issued for the MCP server itself. [claim:clm_064]
- The confused-deputy attack requires four concurrent conditions: a static client ID to the third-party AS, dynamic client registration, a consent cookie set by the third-party AS, and absence of per-client consent before forwarding. [claim:clm_065]
- MCP proxy servers must maintain a per-user registry of approved client_id values and check it before initiating the third-party authorization flow (per-client consent before forwarding). [claim:clm_066]
- The spec prescribes a progressive least-privilege scope model starting from a minimal set (e.g. mcp:tools-basic) elevated incrementally via WWW-Authenticate scope challenges, and lists wildcard/omnibus scopes (*, all, full-access) as a common mistake to avoid. [claim:clm_067]
- Token passthrough risks named by the spec include security-control circumvention, broken audit trails/accountability, and trust-boundary violations enabling lateral access if one service is compromised. [claim:clm_068]
- Local MCP servers should run sandboxed with minimal default privileges and restricted file-system/network access; local HTTP-transport servers should require an authorization token or use unix domain sockets / IPC with restricted access. [claim:clm_069]
- For locally-run MCP servers using an HTTP transport, the spec recommends requiring an authorization token or using unix domain sockets / other IPC mechanisms with restricted access. [claim:clm_070]
- A SPIFFE Verifiable Identity Document (SVID) is the document with which a workload proves its identity to a resource or caller, encoding a single SPIFFE ID. [claim:clm_071]
- An SVID encodes the SPIFFE ID in a cryptographically-verifiable document in one of two supported formats: an X.509 certificate (X509-SVID) or a JWT token (JWT-SVID). [claim:clm_072]
- Because JWT tokens are susceptible to replay attacks that let an interceptor impersonate a workload, SPIFFE advises using X.509-SVIDs whenever possible. [claim:clm_073]
- The Workload API issues identity to a workload without requiring the workload to know its own identity or present any authentication token when it calls the API. [claim:clm_074]
- Because the Workload API issues identity at runtime without prior credentials, applications need not co-deploy any authentication secrets alongside the workload, eliminating static secrets. [claim:clm_075]
- MAESTRO is a threat modeling framework designed specifically for Agentic AI, standing for Multi-Agent Environment, Security, Threat, Risk, and Outcome. [claim:clm_076]
- MAESTRO is built on a seven-layer reference architecture authored by Ken Huang to address risks at a granular level. [claim:clm_077]
- Layer 6, Security and Compliance, is an explicit vertical layer that cuts across all other layers to integrate security controls throughout AI agent operations. [claim:clm_078]
- Layer 7 threats include Agent Identity Attack, compromising identity/authorization mechanisms of AI agents and resulting in unauthorized access and control of the agent. [claim:clm_079]
- Layer 7 threats include Agent Impersonation, where malicious actors deceive users or other agents by impersonating legitimate AI agents. [claim:clm_080]
- Layer 4 threats include Privilege Escalation, where an agent or attacker gains unauthorized privileges in one layer and uses it to access or manipulate others. [claim:clm_081]
- Recommended mitigations for multi-agent systems include secure communication protocols, mutual authentication, and input validation. [claim:clm_082]

## Sources

- src_20260614_rib018_00 — LLM06:2025 Excessive Agency — OWASP Top 10 for LLM Applications
- src_20260614_rib018_01 — Agentic AI - Threats and Mitigations (OWASP Agentic Security Initiative)
- src_20260614_rib018_02 — MCP02:2025 – Privilege Escalation via Scope Creep (OWASP MCP Top 10)
- src_20260614_rib018_03 — MITRE ATLAS Credential Access (AML.TA0013) — tactic and techniques
- src_20260614_rib018_04 — Agentic AI Threat Modeling Framework: MAESTRO
- src_20260614_rib018_05 — Multi-Agentic System Threat Modelling Guide (OWASP GenAI Security Project - Agentic Security Initiative) Version 1.0
- src_20260614_rib018_06 — LLM02:2025 Sensitive Information Disclosure — OWASP Top 10 for LLM Applications
- src_20260614_rib018_07 — MCP Authorization Specification (2025-11-25)
- src_20260614_rib018_08 — MCP Security Best Practices (2025-11-25)
- src_20260614_rib018_09 — Manage dynamic credential leases | HashiCorp Vault
- src_20260614_rib018_10 — Secure multi-tenancy with namespaces | HashiCorp Vault
- src_20260614_rib018_11 — SPIFFE Concepts

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
