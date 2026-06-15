---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_published_security_frameworks_threat_models
title: What published security frameworks, threat models, and runtime-enforcement
intent_id: intent_research_20260614_what_published_security_frameworks_threat_models
evidence_bundle_id: pending
created_at: '2026-06-14T14:40:31-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

This document is the first guide from the OWASP Agentic Security Initiative (ASI), providing a threat-model-based reference of emerging agentic threats and their mitigations. [claim:clm_001]
OWASP frames agentic AI capabilities around LLM-based reasoning/planning, memory that can be session-based short-term or persistent long-term, and action via tool use (including MCP-connected external tools). [claim:clm_002]
OWASP defines the Confused Deputy vulnerability as an AI agent with higher privileges than the user being tricked into performing unauthorized actions on the user's behalf when it lacks privilege isolation. [claim:clm_003]
OWASP threat T3 'Privilege Compromise' describes attackers exploiting weaknesses in permission management - often via dynamic role inheritance or misconfigurations - to perform unauthorized actions. [claim:clm_004]
OWASP recommends clear identity flows, strict RBAC, and a zero-trust model for agent access to enterprise environments to counter implicit privilege escalation and tool-chaining data breaches. [claim:clm_005]
Among authentication/identity mitigations, OWASP advises limiting AI credential persistence so that AI-generated credentials are temporary and expire after short timeframes. [claim:clm_006]
OWASP recommends granular RBAC and ABAC and blocking cross-agent privilege delegation unless explicitly authorized through predefined workflows. [claim:clm_007]
To isolate agent context, OWASP advises segmenting memory access using session isolation so the AI does not carry over unintended knowledge across different user sessions. [claim:clm_008]
Each dynamic database credential is bound to a lease with an explicit TTL and a structured lease ID; the example shows a 768h lease_duration with lease_id format database/creds/readonly/<unique-id>. [claim:clm_009]
A dynamic credential's validity is governed by its lease: it remains valid for the lease TTL, can be renewed up to a maximum TTL, or persists until revoked. [claim:clm_010]
Leases are renewed before expiry by passing the lease ID to `vault lease renew`, which resets the credential's TTL (example renewed to 1h). [claim:clm_011]
A single lease can be revoked immediately by its lease ID without waiting for expiration, using `vault lease revoke <lease_id>`. [claim:clm_012]
Multiple leases can be revoked at once using the -prefix flag, which matches all valid leases sharing a path prefix (e.g., database/creds/readonly). [claim:clm_013]
Once a lease is revoked the underlying credential is immediately invalidated and no longer usable. [claim:clm_014]
After revocation the lease ceases to exist as a valid lease and disappears from the lease listing, confirming immediate invalidation. [claim:clm_015]
The OWASP Multi-Agentic System Threat Modelling Guide is Version 1.0, was released on April 22, 2025, and is published by the OWASP GenAI Security Project's Agentic Security Initiative. [claim:clm_016]
The guide does not propose a new taxonomy but applies the OWASP 'Agentic AI - Threats and Mitigations' master agentic threat taxonomy to real-world multi-agent systems. [claim:clm_017]
The guide's objective is to apply the MAESTRO (Multi-Agent Environment, Security, Threat, Risk, and Outcome) layered, architectural methodology as a companion to the OWASP Agentic Security Initiative (ASI) threat taxonomy for structured threat modeling. [claim:clm_018]
The guide focuses on previously OWASP-defined agentic threats - Tool Misuse, Intent Manipulation, and Privilege Compromise - and how they manifest within complex multi-agent deployments. [claim:clm_019]
The guide identifies identity sprawl and access complexity as a novel MAS risk, where managing identity and access control becomes highly complex due to the large number of interacting agents. [claim:clm_020]
Identity Spoofing is listed as a core MAS threat in which adversaries impersonate agents to inject false data or hijack decision-making. [claim:clm_021]
MAESTRO outlines security threats across architectural layers of the agentic AI reference architecture (foundation models up to the agent ecosystem) plus cross-layer threats, and references the Cloud Security Alliance MAESTRO blog as its origin. [claim:clm_022]
The guide is positioned as an extension of the ASI 'Agentic AI - Threats and Mitigations' document, intended to be used in tandem with it and the OWASP Top 10 for LLM Applications. [claim:clm_023]
OWASP defines MCP scope creep as narrowly scoped agent/tool permissions expanding over time—via convenience or configuration drift—until the agent holds broad or administrative privileges. [claim:clm_024]
The standard prescribes defining minimal per-agent permissions before deployment and mapping documented intended actions to explicit scopes. [claim:clm_025]
The control requires unique per-agent identities with credentials bound to the agent and session context, explicitly disallowing shared global service accounts. [claim:clm_026]
The standard recommends issuing time-limited scopes/tokens per session and requiring revalidation for long-running or recurring tasks. [claim:clm_027]
The control prescribes encoding permission policies as code (Rego, OPA, Terraform IAM) and enforcing them in CI/CD pipelines. [claim:clm_028]
The standard calls for periodic entitlement audits to detect scope expansions and alerting on permission increases. [claim:clm_029]
The control separates the authority to grant permissions from the authority to deploy or change production, and requires human-in-the-loop approvals for non-routine privilege grants. [claim:clm_030]
MCP servers must validate that access tokens were issued specifically for them as the intended audience per RFC 8707 Section 2, and invalid or expired tokens must receive an HTTP 401 response. [claim:clm_031]
If an MCP server makes requests to upstream APIs, it must not pass through the token received from the MCP client; the upstream token must be a separate token issued by the upstream authorization server. [claim:clm_032]
MCP clients must implement RFC 8707 Resource Indicators via the resource parameter, including it in both authorization and token requests and identifying the canonical URI of the target MCP server. [claim:clm_033]
MCP servers must only accept tokens specifically intended for themselves and must reject tokens that do not include them in the audience claim. [claim:clm_034]
Authorization servers should issue short-lived access tokens to reduce leaked-token impact, and for public clients they must rotate refresh tokens per OAuth 2.1 Section 4.3.1. [claim:clm_035]
Implementations using an STDIO transport should not follow this authorization specification and instead retrieve credentials from the environment. [claim:clm_036]
OWASP defines LLM02:2025 sensitive information as spanning PII, financial details, health records, confidential business data, security credentials, and legal documents. [claim:clm_037]
OWASP states LLMs embedded in applications risk exposing sensitive data, proprietary algorithms, or confidential details through their output, leading to unauthorized data access, privacy violations, and IP breaches. [claim:clm_038]
PII leakage is listed as a common vulnerability: PII may be disclosed during interactions with the LLM. [claim:clm_039]
OWASP cites the Proof Pudding attack (CVE-2019-20634) as an example where revealing training data exposes models to inversion attacks. [claim:clm_040]
OWASP recommends limiting model access to external data sources and securely managing runtime data orchestration, the closest mitigation addressing multi-source data chaining risk. [claim:clm_041]
OWASP maps LLM02:2025 to MITRE ATLAS techniques for training-data membership inference and model inversion/extraction (AML.T0024.000/.001/.002). [claim:clm_042]
OWASP's lead mitigation is data sanitization to prevent user data from entering the training model, plus strict input validation to filter sensitive inputs. [claim:clm_043]
OWASP defines Excessive Agency as the vulnerability that enables damaging actions in response to unexpected, ambiguous, or manipulated LLM outputs, regardless of the cause of the malfunction. [claim:clm_044]
OWASP attributes Excessive Agency to three root causes: excessive functionality, excessive permissions, and excessive autonomy. [claim:clm_045]
OWASP recommends limiting the permissions that LLM extensions are granted to downstream systems to the minimum necessary to bound the scope of undesirable actions. [claim:clm_046]
OWASP recommends tracking user authorization and security scope so that actions on downstream systems execute in that specific user's context with minimum privileges. [claim:clm_047]
OWASP advises avoiding open-ended extensions such as run-a-shell-command or fetch-a-URL in favor of more granular, purpose-specific functionality. [claim:clm_048]
OWASP recommends human-in-the-loop control requiring a human to approve high-impact actions before they are taken. [claim:clm_049]
OWASP gives OAuth with minimum scope as the example pattern for an extension that reads a user's code repository. [claim:clm_050]
AML.TA0013 Credential Access covers adversary efforts to steal account names, passwords, or API keys for AI systems. [claim:clm_051]
AML.T0083 'Credentials from AI Agent Configuration' covers accessing the credentials of other tools or services on a system from an AI agent's configuration. [claim:clm_052]
AML.T0082 'RAG Credential Harvesting' covers using access to a victim-system LLM to collect credentials (e.g., those ingested into a RAG database). [claim:clm_053]
AML.T0098 'AI Agent Tool Credential Harvesting' covers using access to a victim-system AI agent to retrieve data from the agent's available tools. [claim:clm_054]
AML.T0055 'Unsecured Credentials' covers searching compromised systems to find and obtain insecurely stored credentials. [claim:clm_055]
AML.TA0013 also enumerates AML.T0090 'OS Credential Dumping' and AML.T0106 'Exploitation for Credential Access', extending credential theft beyond AI-specific vectors to traditional OS-level and exploit-based methods. [claim:clm_056]
Each Vault Enterprise namespace behaves as an isolated Vault environment. [claim:clm_057]
Once signed into a namespace there is no visibility into other namespaces regardless of hierarchical relationship. [claim:clm_058]
Tokens, policies, and secrets engines are tied to their owning namespace, so a client must acquire a valid token per namespace to access its secrets, preventing cross-namespace credential reuse. [claim:clm_059]
Each namespace maintains its own independent policies, auth methods, secrets engines, tokens, and identity entities/groups. [claim:clm_060]
Namespaces address the multi-tenancy need where multiple organizations within a company must manage their secrets in a self-serving manner on a central Vault. [claim:clm_061]
Namespaces are a paid Vault feature requiring a Vault Enterprise Standard license or an HCP Vault cluster. [claim:clm_062]
Namespace creation should be performed by a highly privileged token such as root to set up isolated environments per organization, team, or application. [claim:clm_063]
Token passthrough is explicitly forbidden: an MCP server must not accept tokens that were not issued for the MCP server itself. [claim:clm_064]
The confused-deputy attack requires four concurrent conditions: a static client ID to the third-party AS, dynamic client registration, a consent cookie set by the third-party AS, and absence of per-client consent before forwarding. [claim:clm_065]
MCP proxy servers must maintain a per-user registry of approved client_id values and check it before initiating the third-party authorization flow (per-client consent before forwarding). [claim:clm_066]
The spec prescribes a progressive least-privilege scope model starting from a minimal set (e.g. mcp:tools-basic) elevated incrementally via WWW-Authenticate scope challenges, and lists wildcard/omnibus scopes (*, all, full-access) as a common mistake to avoid. [claim:clm_067]
Token passthrough risks named by the spec include security-control circumvention, broken audit trails/accountability, and trust-boundary violations enabling lateral access if one service is compromised. [claim:clm_068]
Local MCP servers should run sandboxed with minimal default privileges and restricted file-system/network access; local HTTP-transport servers should require an authorization token or use unix domain sockets / IPC with restricted access. [claim:clm_069]
For locally-run MCP servers using an HTTP transport, the spec recommends requiring an authorization token or using unix domain sockets / other IPC mechanisms with restricted access. [claim:clm_070]
A SPIFFE Verifiable Identity Document (SVID) is the document with which a workload proves its identity to a resource or caller, encoding a single SPIFFE ID. [claim:clm_071]
An SVID encodes the SPIFFE ID in a cryptographically-verifiable document in one of two supported formats: an X.509 certificate (X509-SVID) or a JWT token (JWT-SVID). [claim:clm_072]
Because JWT tokens are susceptible to replay attacks that let an interceptor impersonate a workload, SPIFFE advises using X.509-SVIDs whenever possible. [claim:clm_073]
The Workload API issues identity to a workload without requiring the workload to know its own identity or present any authentication token when it calls the API. [claim:clm_074]
Because the Workload API issues identity at runtime without prior credentials, applications need not co-deploy any authentication secrets alongside the workload, eliminating static secrets. [claim:clm_075]
MAESTRO is a threat modeling framework designed specifically for Agentic AI, standing for Multi-Agent Environment, Security, Threat, Risk, and Outcome. [claim:clm_076]
MAESTRO is built on a seven-layer reference architecture authored by Ken Huang to address risks at a granular level. [claim:clm_077]
Layer 6, Security and Compliance, is an explicit vertical layer that cuts across all other layers to integrate security controls throughout AI agent operations. [claim:clm_078]
Layer 7 threats include Agent Identity Attack, compromising identity/authorization mechanisms of AI agents and resulting in unauthorized access and control of the agent. [claim:clm_079]
Layer 7 threats include Agent Impersonation, where malicious actors deceive users or other agents by impersonating legitimate AI agents. [claim:clm_080]
Layer 4 threats include Privilege Escalation, where an agent or attacker gains unauthorized privileges in one layer and uses it to access or manipulate others. [claim:clm_081]
Recommended mitigations for multi-agent systems include secure communication protocols, mutual authentication, and input validation. [claim:clm_082]

## Inferences

**Inference:** RF's four-profile model (personal | work_approved | client_approved | offline_only) is functionally a file-first analogue of Vault Enterprise namespaces: each profile should behave as an isolated credential environment where a personal-profile task cannot see or reuse work/client keys, mirroring the namespace property that signing into one namespace gives zero visibility into others. [claim:clm_inf01]
**Inference:** Because Vault namespaces are a paid Enterprise/HCP feature requiring a long-running server (clm_062) while RF is daemonless and file-first, RF cannot inherit Vault's runtime broker/revocation guarantees and must instead enforce isolation at load time through process-level env scoping plus a policy gate, accepting weaker live-revocation than a server-backed broker. [claim:clm_inf02]
**Inference:** Cross-profile leakage vector #1 (environment-variable bleed): a personal-profile task can acquire work/client keys whenever a parent process exports all profiles' keys into a shared environment; the MCP authorization spec's STDIO rule that servers retrieve credentials 'from the environment' (clm_036) makes this the highest-risk default path in a daemonless model, and RF must construct a minimal per-profile env containing only that profile's keys rather than inheriting the operator's full shell environment. [claim:clm_inf03]
**Inference:** Cross-profile leakage vector #2 (subagent / tool-credential inheritance): when an RF orchestrator spawns subagents or MCP tools, a personal-profile subagent that inherits the parent's tool credentials maps directly to MITRE ATLAS AML.T0098 (AI Agent Tool Credential Harvesting) and AML.T0083 (Credentials from AI Agent Configuration), so RF must re-derive a profile-scoped credential set at each spawn boundary rather than passing the parent's credentials down. [claim:clm_inf04]
**Inference:** Cross-profile leakage vector #3 (log / telemetry capture): because OWASP classifies security credentials as sensitive information that LLM applications can expose through output (clm_037, clm_038), RF's profile-tagged telemetry (run_trace.jsonl) is itself a leakage surface, and RF must redact/fingerprint keys before they enter telemetry rather than logging raw key material or raw tool I/O. [claim:clm_inf05]
**Inference:** Cross-profile leakage vector #4 (prompt-injection exfiltration / confused deputy): an over-privileged RF orchestrator holding multiple profiles' keys is the textbook OWASP Confused Deputy (clm_003) and Excessive Agency (clm_044) case, where a manipulated prompt in a personal task induces the agent to emit work/client keys; the controlling mitigation is to never load more than one profile's keys into a single reasoning context, bounding the blast radius to a single profile. [claim:clm_inf06]
**Inference:** Cross-profile leakage vector #5 (scope creep / cache and key reuse over time): MCP02:2025 scope creep (clm_024) maps onto RF as a profile's key set silently broadening through reuse or copied .env files until offline_only or personal effectively holds work/client keys; the controlling mitigation is periodic entitlement/drift audits (clm_029) over the per-profile key manifests with alerting on any key appearing under more than one profile. [claim:clm_inf07]
**Inference:** Cross-profile leakage vector #6 (token passthrough / lateral movement across profiles): the MCP spec's hard prohibition on token passthrough (clm_064) and its warning that a token accepted by multiple services lets a single compromise reach all of them (clm_068) translate directly to RF — a credential valid across multiple profiles is a passthrough token, so each profile's keys must be audience-bound to that profile and rejected if presented under another. [claim:clm_inf08]
**Inference:** Across the six leakage vectors, the failure modes cluster into three families — (a) ambient inheritance (env bleed, subagent inheritance), (b) observability capture (log/telemetry, prompt echo), and (c) temporal/scope drift (scope creep, cross-profile token reuse) — and a single control, 'construct a minimal single-profile credential context at every process/spawn boundary and never persist it to a shared surface,' addresses family (a) and most of (b). [claim:clm_inf09]
**Inference:** Mapping RF's four profiles against three published frameworks: (1) Vault namespaces validate the isolation goal (per-profile token, no cross-visibility, clm_057-060) but RF lacks the server-backed revocation; (2) MCP authorization validates audience-binding and short-lived-token guidance (clm_031, clm_034, clm_035) that RF only partially meets because file-based keys are typically long-lived; (3) SPIFFE sets the aspirational bar of zero static secrets via runtime-issued SVIDs (clm_074, clm_075) that a file-first .env model structurally cannot reach without a broker. [claim:clm_inf10]
**Inference:** The single largest gap between RF's file-first model and every server-backed framework is credential lifetime: Vault leases (clm_010), MCP short-lived access tokens (clm_035), OWASP's 'limit AI credential persistence' (clm_006), and SPIFFE runtime-issued SVIDs (clm_075) all assume ephemeral credentials, whereas a static per-profile .env key is long-lived by default, so RF's compensating control must be rotation cadence and revocation tooling rather than TTL expiry. [claim:clm_inf11]
**Inference:** Concrete tightening #1 (one-profile-per-process env construction): RF should never inherit the operator's ambient shell environment; instead each run loads exactly one profile's keys into a freshly constructed, minimal environment and strips all others, operationalizing OWASP per-user/least-privilege execution context (clm_047) and MCP scope minimization (clm_067) and directly closing the env-bleed and subagent-inheritance vectors. [claim:clm_inf12]
**Inference:** Concrete tightening #2 (key fingerprinting + profile-tagged telemetry for after-the-fact proof): RF should record a non-reversible fingerprint (e.g., salted hash prefix) of each key tagged with the profile it was loaded under, never the raw key, so that run_trace telemetry can later prove which profile's credentials a run touched and flag any run where a key fingerprint appears under a profile it does not belong to — combining OWASP entitlement/drift auditing (clm_029) with MCP audit-trail integrity (clm_068) without writing sensitive data (clm_037). [claim:clm_inf13]
**Inference:** Concrete tightening #3 (file-first revocation/rotation playbook substituting for Vault leases): since RF cannot revoke a leaked key mid-run, it should ship a documented per-profile revocation runbook and a key-manifest that records issue date and required rotation interval, approximating Vault's revoke-by-id and lease-TTL semantics (clm_011, clm_012, clm_014) at human cadence and satisfying OWASP's short-credential-persistence guidance (clm_006) for a daemonless system. [claim:clm_inf14]
**Inference:** Concrete tightening #4 (human-in-the-loop gate on cross-profile elevation): any RF action that would load a second profile's keys, or promote a task from offline_only/personal to work_approved/client_approved, should require an explicit human approval, applying OWASP human-in-the-loop for high-impact actions (clm_049) and MCP/OWASP separation of grant-vs-deploy authority (clm_030) to the one operation that breaks the isolation boundary. [claim:clm_inf15]
**Inference:** For the single-operator threat model (one person legitimately holding personal + work + client key sets at once), the dominant residual risk is not external theft but accidental same-context co-loading and prompt-injection-driven cross-profile echo, so RF's offline_only profile should be the default and the system should treat 'which profile am I in' as an explicit, single-valued, logged run parameter rather than an implicit ambient state. [claim:clm_inf16]
**Inference:** RF's offline_only profile is the strongest isolation guarantee in the model because a profile that holds no live API keys is immune to all six credential-leakage vectors by construction, making 'route to offline_only unless a network-key is provably required' a high-value default decision rule that no server-backed framework offers as cleanly. [claim:clm_inf17]

## Speculation

**Speculation:** As MITRE ATLAS continues adding AI-agent-specific credential techniques (it already added AML.T0083/T0098 for agent-config and agent-tool harvesting, clm_052/054), file-first per-profile .env models like RF's will likely become an explicitly named anti-pattern within 1-2 framework revisions unless they add fingerprint-based audit trails, because a plaintext multi-profile key store on disk is the canonical AML.T0055 'unsecured credentials' target. [claim:clm_spec01]
**Speculation:** If RF later needs the ephemeral-credential guarantees the file model cannot provide, the lowest-friction upgrade path is a thin local credential-broker shim that speaks the SPIFFE Workload API pattern (runtime-issued, no co-deployed secrets, clm_074/075) and exposes per-profile short-lived tokens, rather than adopting full Vault Enterprise namespaces (clm_062) whose licensing and always-on daemon contradict RF's daemonless design. [claim:clm_spec02]

## Open questions

- None recorded.

## Sources

- src_20260614_rib018_01: Agentic AI - Threats and Mitigations (OWASP Agentic Security Initiative)
- src_20260614_rib018_09: Manage dynamic credential leases | HashiCorp Vault
- src_20260614_rib018_05: Multi-Agentic System Threat Modelling Guide (OWASP GenAI Security Project - Agentic Security Initiative) Version 1.0
- src_20260614_rib018_02: MCP02:2025 – Privilege Escalation via Scope Creep (OWASP MCP Top 10)
- src_20260614_rib018_07: MCP Authorization Specification (2025-11-25)
- src_20260614_rib018_06: LLM02:2025 Sensitive Information Disclosure — OWASP Top 10 for LLM Applications
- src_20260614_rib018_00: LLM06:2025 Excessive Agency — OWASP Top 10 for LLM Applications
- src_20260614_rib018_03: MITRE ATLAS Credential Access (AML.TA0013) — tactic and techniques
- src_20260614_rib018_10: Secure multi-tenancy with namespaces | HashiCorp Vault
- src_20260614_rib018_08: MCP Security Best Practices (2025-11-25)
- src_20260614_rib018_11: SPIFFE Concepts
- src_20260614_rib018_04: Agentic AI Threat Modeling Framework: MAESTRO
